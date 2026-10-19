import XCTest
@testable import ParzrCore

/// Answers each send from a script (then `.accepted`) and records what was sent.
actor FakeReportTransport: ReportTransport {
    var script: [ReportSendResult]
    private(set) var sent: [(key: String, batch: ReportBatch)] = []
    var during: (@Sendable () async -> Void)?
    let fallback: ReportSendResult
    init(_ script: [ReportSendResult] = [], fallback: ReportSendResult = .accepted) { self.script = script; self.fallback = fallback }
    func setDuring(_ action: @escaping @Sendable () async -> Void) { during = action }
    func send(_ body: Data, key: String) async -> ReportSendResult {
        sent.append((key, try! JSONDecoder().decode(ReportBatch.self, from: body)))
        if let during { self.during = nil; await during() }
        return script.isEmpty ? fallback : script.removeFirst()
    }
}

final class ReportQueueTests: XCTestCase {
    private func report(_ n: Int, action: ReportAction = .dismissed) -> SuggestionReport { Self.report(n, action: action) }
    static func report(_ n: Int, action: ReportAction = .dismissed) -> SuggestionReport {
        SuggestionReport(sentence: "sentence \(String(repeating: "x", count: n))", suggestion: .init(start: 0, end: 8, original: "sentence", replacement: "Sentence"), rule: "grammar.test", model: "rules", action: action, app: "com.apple.TextEdit", version: "0.5.0")
    }
    private func queue(_ transport: FakeReportTransport, store: ReportStore = ReportStore(url: nil), enabled: Bool = true, policy: ReportQueue.Policy = ReportQueue.Policy()) -> ReportQueue {
        ReportQueue(transport: transport, store: store, gate: ReportGate(enabled: enabled), policy: policy, sleep: { _ in }, jitter: { 1 })
    }
    private func temporaryStore() -> ReportStore {
        ReportStore(url: FileManager.default.temporaryDirectory.appendingPathComponent("parzr-report-tests-\(UUID().uuidString)/queue.json"))
    }

    func testReportsAreSentTogetherInOneBatch() async {
        let transport = FakeReportTransport(), q = queue(transport)
        await q.enqueue([report(1), report(2), report(3)])
        await q.drain()
        let sent = await transport.sent
        XCTAssertEqual(sent.count, 1)
        XCTAssertEqual(sent.first?.batch.reports, [report(1), report(2), report(3)])
        XCTAssertEqual(sent.first?.key.count, 36, "a random UUID, nothing else")
        let left = await q.count, waits = await q.waits
        XCTAssertEqual(left, 0)
        XCTAssertEqual(waits, [30], "the first send waits for others to join it")
    }
    func testLargeQueuesGoOutInSeveralBatchesWithinTheSizeLimits() async {
        var policy = ReportQueue.Policy(); policy.batchSize = 2
        let transport = FakeReportTransport(), q = queue(transport, policy: policy)
        await q.enqueue((1...5).map { report($0) })
        await q.drain()
        let sizes = await transport.sent.map(\.batch.reports.count)
        XCTAssertEqual(sizes, [2, 2, 1])
        var small = ReportQueue.Policy(); small.batchBytes = 700
        let bytes = FakeReportTransport(), q2 = queue(bytes, policy: small)
        await q2.enqueue((1...6).map { report(100 + $0) })
        await q2.drain()
        for (_, batch) in await bytes.sent { XCTAssertLessThanOrEqual(try! JSONEncoder().encode(batch).count, 700) }
        let total = await bytes.sent.map(\.batch.reports.count).reduce(0, +)
        XCTAssertEqual(total, 6)
    }
    func testAFailedBatchIsRetriedWithBackoffAsTheSameBatch() async {
        let transport = FakeReportTransport([.retry(after: nil), .retry(after: nil), .retry(after: nil), .accepted])
        let q = queue(transport)
        await q.enqueue([report(1), report(2)])
        // A report written while the first attempt is out waits for the next batch instead of joining the retry.
        let third = report(3)
        await transport.setDuring { await q.enqueue([third]) }
        await q.drain()
        let sent = await transport.sent, waits = await q.waits
        XCTAssertEqual(sent.count, 5)
        XCTAssertEqual(Set(sent.prefix(4).map(\.key)).count, 1, "every retry carries the same key")
        XCTAssertTrue(sent.prefix(4).allSatisfy { $0.batch.reports == [report(1), report(2)] })
        XCTAssertEqual(sent.last?.batch.reports, [report(3)])
        XCTAssertNotEqual(sent.last?.key, sent.first?.key)
        XCTAssertEqual(waits, [30, 30, 60, 120], "exponential backoff after the first wait")
    }
    func testRetryAfterIsHonouredAndBackoffIsCapped() async {
        var policy = ReportQueue.Policy(); policy.maxBackoff = 600
        let transport = FakeReportTransport([.retry(after: 300), .retry(after: 99_999), .retry(after: nil), .accepted])
        let q = queue(transport, policy: policy)
        await q.enqueue([report(1)])
        await q.drain()
        let waits = await q.waits
        XCTAssertEqual(waits, [30, 300, 600, 120])
    }
    func testARejectedBatchIsDroppedNotRetried() async {
        let transport = FakeReportTransport([.rejected])
        let q = queue(transport)
        await q.enqueue([report(1)])
        await q.drain()
        let sent = await transport.sent.count, left = await q.count
        XCTAssertEqual(sent, 1); XCTAssertEqual(left, 0)
    }
    func testOfflineReportsWaitOnDiskAndAreSentNextLaunch() async throws {
        let store = temporaryStore()
        defer { store.erase() }
        // Offline: every attempt fails, and the worker then sits in its backoff.
        let offline = FakeReportTransport(fallback: .retry(after: nil))
        var policy = ReportQueue.Policy(); policy.delay = 0
        let first = ReportQueue(transport: offline, store: store, gate: ReportGate(enabled: true), policy: policy, sleep: { _ in try await Task.sleep(nanoseconds: 10_000_000_000) }, jitter: { 1 })
        await first.enqueue([report(1), report(2)])
        for _ in 0..<200 where await offline.sent.isEmpty { try await Task.sleep(nanoseconds: 10_000_000) }
        XCTAssertTrue(FileManager.default.fileExists(atPath: store.url!.path))
        // The next launch finds them and sends them, with the key the failed attempts used.
        let online = FakeReportTransport()
        let second = queue(online, store: store)
        let waiting = await second.count
        XCTAssertEqual(waiting, 2)
        await second.resume(); await second.drain()
        let sent = await online.sent, tried = await offline.sent
        XCTAssertEqual(sent.first?.batch.reports, [report(1), report(2)])
        XCTAssertEqual(sent.first?.key, tried.first?.key)
        XCTAssertFalse(FileManager.default.fileExists(atPath: store.url!.path), "an empty queue leaves no file behind")
        await first.purge()
    }
    func testTheQueueKeepsOnlyTheNewestReportsWhileOffline() async {
        var policy = ReportQueue.Policy(); policy.capacity = 3
        let transport = FakeReportTransport(), q = ReportQueue(transport: transport, gate: ReportGate(enabled: true), policy: policy, sleep: { _ in try await Task.sleep(nanoseconds: 10_000_000_000) })
        await q.enqueue((1...5).map { report($0) })
        let count = await q.count
        XCTAssertEqual(count, 3)
        await q.purge()
    }
    func testOptingOutDropsNewReportsAndErasesTheQueue() async throws {
        let store = temporaryStore()
        let gate = ReportGate(enabled: true)
        let transport = FakeReportTransport()
        let q = ReportQueue(transport: transport, store: store, gate: gate, sleep: { _ in try await Task.sleep(nanoseconds: 10_000_000_000) })
        await q.enqueue([report(1)])
        XCTAssertTrue(FileManager.default.fileExists(atPath: store.url!.path))
        let center = ReportCenter(queue: q)
        center.setEnabled(false)
        XCTAssertFalse(gate.enabled, "off at once, before the queue hears about it")
        await q.enqueue([report(2)])
        await q.purge()
        let count = await q.count, sent = await transport.sent.count
        XCTAssertEqual(count, 0); XCTAssertEqual(sent, 0)
        XCTAssertFalse(FileManager.default.fileExists(atPath: store.url!.path))
    }
    func testOptingOutDuringASendKeepsNothing() async {
        let gate = ReportGate(enabled: true)
        let transport = FakeReportTransport([.retry(after: nil)])
        let q = ReportQueue(transport: transport, gate: gate, sleep: { _ in }, jitter: { 1 })
        await q.enqueue([report(1)])
        await transport.setDuring { gate.set(false); await q.purge() }
        await q.drain()
        let count = await q.count, sent = await transport.sent.count
        XCTAssertEqual(count, 0); XCTAssertEqual(sent, 1, "no retry after the switch went off")
    }
    func testALaunchWithReportsOffErasesWhatAnEarlierLaunchQueued() async {
        let store = temporaryStore()
        store.save([ReportQueue.Item(id: UUID(), report: report(1), batch: nil)])
        let q = queue(FakeReportTransport(), store: store, enabled: false)
        let count = await q.count
        XCTAssertEqual(count, 0)
        XCTAssertFalse(FileManager.default.fileExists(atPath: store.url!.path))
    }
    func testTheCenterQueuesNothingWhileOff() async {
        let q = queue(FakeReportTransport(), enabled: false)
        let center = ReportCenter(queue: q)
        let edit = WritingEdit(start: 2, end: 5, replacement: "has", original: "hav", ruleID: "spelling.typo")
        XCTAssertNil(center.submit([edit], source: "I hav it.", action: .dismissed, mode: .fix, app: "com.apple.Notes", version: "0.5.0"))
        let count = await q.count
        XCTAssertEqual(count, 0)
    }
    func testTheCenterRedactsAndQueuesInTheBackground() async {
        let transport = FakeReportTransport()
        let q = ReportQueue(transport: transport, gate: ReportGate(enabled: true), sleep: { _ in try await Task.sleep(nanoseconds: 10_000_000_000) })
        let center = ReportCenter(queue: q)
        let source = "Hi Rahul. I hav 3 cats at aman@example.com."
        let edit = WritingEdit(start: 12, end: 15, replacement: "have", original: "hav", ruleID: "spelling.typo")
        await center.submit([edit], source: source, action: .reported, mode: .fix, app: "com.apple.Notes", version: "0.5.0")?.value
        let count = await q.count
        XCTAssertEqual(count, 1)
        await q.purge()
        // Only the sentence the edit is in, redacted.
        let other = FakeReportTransport(), q2 = queue(other)
        await ReportCenter(queue: q2).submit([edit], source: source, action: .reported, mode: .fix, app: "com.apple.Notes", version: "0.5.0")?.value
        await q2.drain()
        let sentence = await other.sent.first?.batch.reports.first?.sentence
        XCTAssertEqual(sentence, "I hav [number] cats at [email].")
    }
    func testHTTPStatusesMapToSendResults() {
        XCTAssertEqual(URLSessionReportTransport.classify(status: 202, retryAfter: nil), .accepted)
        XCTAssertEqual(URLSessionReportTransport.classify(status: 409, retryAfter: nil), .accepted)
        XCTAssertEqual(URLSessionReportTransport.classify(status: 400, retryAfter: nil), .rejected)
        XCTAssertEqual(URLSessionReportTransport.classify(status: 413, retryAfter: nil), .rejected)
        XCTAssertEqual(URLSessionReportTransport.classify(status: 429, retryAfter: "120"), .retry(after: 120))
        XCTAssertEqual(URLSessionReportTransport.classify(status: 503, retryAfter: nil), .retry(after: nil))
        XCTAssertEqual(URLSessionReportTransport.classify(status: 404, retryAfter: nil), .retry(after: nil), "an endpoint not deployed yet keeps the queue")
    }
}

final class ReportBuilderTests: XCTestCase {
    func testAReportHoldsTheRedactedSentenceAndNothingElse() throws {
        let source = "First line here.\nThanks Rahul, I has 2 questions about https://x.io/a. Bye."
        let start = (source as NSString).range(of: "has")
        let edit = WritingEdit(start: start.location, end: NSMaxRange(start), replacement: "have", original: "has", category: "Grammar", ruleID: "grammar.i_agreement", explanation: "Use have with I.")
        let report = try XCTUnwrap(ReportBuilder.report(edit: edit, source: source, action: .reported, mode: .fix, app: "com.tinyspeck.slackmacgap", version: "0.5.0"))
        XCTAssertEqual(report.sentence, "Thanks [name], I has [number] questions about [link].")
        XCTAssertEqual(report.suggestion.original, "has"); XCTAssertEqual(report.suggestion.replacement, "have")
        XCTAssertEqual((report.sentence as NSString).substring(with: NSRange(location: report.suggestion.start, length: report.suggestion.end - report.suggestion.start)), "has")
        XCTAssertEqual(report.rule, "grammar.i_agreement"); XCTAssertEqual(report.model, "rules")
        XCTAssertEqual(report.action, .reported); XCTAssertEqual(report.app, "com.tinyspeck.slackmacgap"); XCTAssertEqual(report.version, "0.5.0")
        // The wire format: these keys only. No explanation, category, confidence, time, or anything about the Mac.
        let json = try XCTUnwrap(JSONSerialization.jsonObject(with: JSONEncoder().encode(report)) as? [String: Any])
        XCTAssertEqual(Set(json.keys), ["sentence", "suggestion", "rule", "model", "action", "app", "version"])
        XCTAssertEqual(Set((json["suggestion"] as? [String: Any])?.keys ?? [:].keys), ["start", "end", "original", "replacement"])
    }
    func testTheModelIsNamedFromTheRule() {
        XCTAssertEqual(ReportBuilder.model(rule: "gector.verb_form", mode: .fix), "gector")
        XCTAssertEqual(ReportBuilder.model(rule: "local-model", mode: .fix), "qwen")
        XCTAssertEqual(ReportBuilder.model(rule: "local-model", mode: .professional), "qwen:professional")
        XCTAssertEqual(ReportBuilder.model(rule: "context.sentence_swap", mode: .fix), "qwen")
        XCTAssertEqual(ReportBuilder.model(rule: "spelling.typo", mode: .friendly), "rules")
    }
    func testIdentifiersCannotCarryFreeText() throws {
        let edit = WritingEdit(start: 0, end: 3, replacement: "The", original: "teh", ruleID: "spelling typo with words")
        let report = try XCTUnwrap(ReportBuilder.report(edit: edit, source: "teh cat", action: .accepted, mode: .fix, app: "my secret app name", version: "1.0 (my build)"))
        XCTAssertEqual(report.rule, "unknown"); XCTAssertEqual(report.app, "unknown"); XCTAssertEqual(report.version, "unknown")
        let none = try XCTUnwrap(ReportBuilder.report(edit: edit, source: "teh cat", action: .accepted, mode: .fix, app: nil, version: "0.5.0"))
        XCTAssertEqual(none.app, "unknown")
    }
    func testAnEditThatNoLongerMatchesTheTextIsNotReported() {
        let edit = WritingEdit(start: 0, end: 3, replacement: "The", original: "teh")
        XCTAssertNil(ReportBuilder.report(edit: edit, source: "the cat", action: .dismissed, mode: .fix, app: "a.b", version: "1"))
        XCTAssertNil(ReportBuilder.report(edit: WritingEdit(start: 5, end: 20, replacement: "x", original: "y"), source: "short", action: .dismissed, mode: .fix, app: "a.b", version: "1"))
    }
    func testALongSentenceIsCutAtWordsAroundTheSuggestion() throws {
        let filler = Array(repeating: "word", count: 150).joined(separator: " ")
        let source = "\(filler) teh \(filler)"
        let range = (source as NSString).range(of: "teh")
        let edit = WritingEdit(start: range.location, end: NSMaxRange(range), replacement: "the", original: "teh")
        let report = try XCTUnwrap(ReportBuilder.report(edit: edit, source: source, action: .dismissed, mode: .fix, app: "a.b", version: "1"))
        XCTAssertLessThanOrEqual(report.sentence.utf16.count, 2 * ReportBuilder.context + 3)
        XCTAssertTrue(report.sentence.hasPrefix("word ")); XCTAssertTrue(report.sentence.hasSuffix(" word"))
        XCTAssertEqual((report.sentence as NSString).substring(with: NSRange(location: report.suggestion.start, length: 3)), "teh")
    }
    func testAReportOnANumberIsRedactedOnBothSides() throws {
        let source = "Pay 5O0 dollars."
        let range = (source as NSString).range(of: "5O0")
        let edit = WritingEdit(start: range.location, end: NSMaxRange(range), replacement: "500", original: "5O0")
        let report = try XCTUnwrap(ReportBuilder.report(edit: edit, source: source, action: .reported, mode: .fix, app: "a.b", version: "1"))
        XCTAssertEqual(report.sentence, "Pay [number] dollars.")
        XCTAssertEqual(report.suggestion.original, "[number]"); XCTAssertEqual(report.suggestion.replacement, "[number]")
    }
}
