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
    private func report(_ n: Int) -> SuggestionReport { Self.report(n) }
    static func report(_ n: Int) -> SuggestionReport {
        SuggestionReport(sentence: "sentence \(String(repeating: "x", count: n))", suggestion: .init(start: 0, end: 8, original: "sentence", replacement: "Sentence"), rule: "grammar.test", model: "rules", action: .reported, app: "com.apple.TextEdit", version: "0.5.0")
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
        XCTAssertNil(center.submit([edit], source: "I hav it.", mode: .fix, app: "com.apple.Notes", version: "0.5.0"))
        let count = await q.count
        XCTAssertEqual(count, 0)
    }
    func testTheCenterRedactsAndQueuesInTheBackground() async {
        let transport = FakeReportTransport()
        let q = ReportQueue(transport: transport, gate: ReportGate(enabled: true), sleep: { _ in try await Task.sleep(nanoseconds: 10_000_000_000) })
        let center = ReportCenter(queue: q)
        let source = "Hi Rahul. I hav 3 cats at aman@example.com."
        let edit = WritingEdit(start: 12, end: 15, replacement: "have", original: "hav", ruleID: "spelling.typo")
        await center.submit([edit], source: source, mode: .fix, app: "com.apple.Notes", version: "0.5.0")?.value
        let count = await q.count
        XCTAssertEqual(count, 1)
        await q.purge()
        // Only the sentence the edit is in, redacted.
        let other = FakeReportTransport(), q2 = queue(other)
        await ReportCenter(queue: q2).submit([edit], source: source, mode: .fix, app: "com.apple.Notes", version: "0.5.0")?.value
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
        XCTAssertEqual(URLSessionReportTransport.classify(status: 500, retryAfter: "60"), .retry(after: 60))
        XCTAssertEqual(URLSessionReportTransport.classify(status: 408, retryAfter: nil), .retry(after: nil))
        for status in [401, 403, 404, 405, 410, 422, 451] { XCTAssertEqual(URLSessionReportTransport.classify(status: status, retryAfter: nil), .rejected, "\(status) is refused for good, never retried forever") }
        for status in [301, 302, 307, 308] { XCTAssertEqual(URLSessionReportTransport.classify(status: status, retryAfter: nil), .rejected, "a redirect is refused, and the batch dropped") }
    }
    func testRedirectsAreRefused() async {
        let delegate = RefuseRedirects()
        let response = HTTPURLResponse(url: URL(string: "https://reports.parzr.app/v1/reports")!, statusCode: 307, httpVersion: nil, headerFields: ["Location": "https://elsewhere.example/"])!
        let session = URLSession(configuration: .ephemeral)
        let task = session.dataTask(with: URL(string: "https://reports.parzr.app/v1/reports")!)
        let next = await delegate.urlSession(session, task: task, willPerformHTTPRedirection: response, newRequest: URLRequest(url: URL(string: "https://elsewhere.example/")!))
        XCTAssertNil(next)
        task.cancel()
    }
    func testReportsQueuedLongerThanTheBatchKeyIsKeptAreDropped() async {
        let clock = Clock(Date(timeIntervalSince1970: 1_800_000_000))
        let transport = FakeReportTransport(fallback: .retry(after: nil))
        var policy = ReportQueue.Policy(); policy.delay = 0; policy.backoff = 1; policy.maxBackoff = 1
        let q = ReportQueue(transport: transport, gate: ReportGate(enabled: true), policy: policy, sleep: { _ in clock.advance(86_400) }, jitter: { 1 }, now: { clock.now })
        await q.enqueue([report(1)])
        await q.drain()
        let sent = await transport.sent.count, left = await q.count
        XCTAssertEqual(left, 0, "offline for over 14 days: the report is dropped, not retried with a key the server forgot")
        XCTAssertLessThanOrEqual(sent, 15)
        XCTAssertGreaterThanOrEqual(sent, 13)
    }
    func testOldAndInvalidReportsOnDiskAreDroppedAtLaunch() async throws {
        let store = temporaryStore()
        defer { store.erase() }
        let now = Date()
        let leaky = SuggestionReport(sentence: "call 555 0100 now", suggestion: .init(start: 0, end: 4, original: "call", replacement: "Call"), rule: "r", model: "rules", action: .reported, app: "a.b", version: "1")
        let badOffsets = SuggestionReport(sentence: "I has it", suggestion: .init(start: 0, end: 4, original: "has", replacement: "have"), rule: "r", model: "rules", action: .reported, app: "a.b", version: "1")
        let bidi = SuggestionReport(sentence: "I has \u{202E}it", suggestion: .init(start: 2, end: 5, original: "has", replacement: "have"), rule: "r", model: "rules", action: .reported, app: "a.b", version: "1")
        store.save([
            ReportQueue.Item(id: UUID(), report: report(1), queued: now.addingTimeInterval(-15 * 86_400)),
            ReportQueue.Item(id: UUID(), report: report(2), queued: now.addingTimeInterval(-86_400)),
            ReportQueue.Item(id: UUID(), report: report(3)),
            ReportQueue.Item(id: UUID(), report: leaky, queued: now), ReportQueue.Item(id: UUID(), report: badOffsets, queued: now), ReportQueue.Item(id: UUID(), report: bidi, queued: now),
        ])
        let q = ReportQueue(transport: FakeReportTransport(), store: store, gate: ReportGate(enabled: true), sleep: { _ in try await Task.sleep(nanoseconds: 10_000_000_000) })
        let count = await q.count
        XCTAssertEqual(count, 2, "the 15-day-old report and the three that fail today's checks are gone; one without a date counts from now")
        XCTAssertEqual(store.load().map(\.report), [report(2), report(3)])
        XCTAssertNotNil(store.load().last?.queued)
        await q.purge()
    }
    func testAQueueFileFromBeforeIgnoreStoppedSendingIsErased() async throws {
        let store = temporaryStore()
        try FileManager.default.createDirectory(at: store.url!.deletingLastPathComponent(), withIntermediateDirectories: true)
        let old = #"{"items":[{"id":"0F8FAD5B-D9CB-469F-A165-70867728950E","report":{"sentence":"I has it","suggestion":{"start":2,"end":5,"original":"has","replacement":"have"},"rule":"r","model":"rules","action":"dismissed","app":"a.b","version":"0.5.0"}}]}"#
        try Data(old.utf8).write(to: store.url!)
        let q = queue(FakeReportTransport(), store: store)
        let count = await q.count
        XCTAssertEqual(count, 0)
        XCTAssertFalse(FileManager.default.fileExists(atPath: store.url!.path))
    }
    func testTheQueueFileIsPrivateAndNotBackedUp() throws {
        let store = temporaryStore()
        defer { store.erase() }
        store.save([ReportQueue.Item(id: UUID(), report: report(1), queued: Date())])
        let attributes = try FileManager.default.attributesOfItem(atPath: store.url!.path)
        XCTAssertEqual((attributes[.posixPermissions] as? NSNumber)?.intValue, 0o600)
        XCTAssertEqual(try store.url!.resourceValues(forKeys: [.isExcludedFromBackupKey]).isExcludedFromBackup, true)
        store.save([ReportQueue.Item(id: UUID(), report: report(2), queued: Date())])
        XCTAssertEqual((try FileManager.default.attributesOfItem(atPath: store.url!.path)[.posixPermissions] as? NSNumber)?.intValue, 0o600, "every rewrite stays private")
        let leftovers = try FileManager.default.contentsOfDirectory(atPath: store.url!.deletingLastPathComponent().path)
        XCTAssertEqual(leftovers, [store.url!.lastPathComponent], "no temporary files left behind")
    }
}

/// A clock tests move by hand.
final class Clock: @unchecked Sendable {
    private let lock = NSLock()
    private var current: Date
    init(_ start: Date) { current = start }
    var now: Date { lock.lock(); defer { lock.unlock() }; return current }
    func advance(_ seconds: TimeInterval) { lock.lock(); current += seconds; lock.unlock() }
}

final class ReportBuilderTests: XCTestCase {
    func testAReportHoldsTheRedactedSentenceAndNothingElse() throws {
        let source = "First line here.\nThanks Rahul, I has 2 questions about https://x.io/a. Bye."
        let start = (source as NSString).range(of: "has")
        let edit = WritingEdit(start: start.location, end: NSMaxRange(start), replacement: "have", original: "has", category: "Grammar", ruleID: "grammar.i_agreement", explanation: "Use have with I.")
        let report = try XCTUnwrap(ReportBuilder.report(edit: edit, source: source, mode: .fix, app: "com.tinyspeck.slackmacgap", version: "0.5.0"))
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
    func testOnlyReportWrongSuggestionMakesAReport() throws {
        XCTAssertEqual(ReportAction.allCases, [.reported], "Ignore sends nothing, and accepted suggestions are never sent")
        XCTAssertNil(try? JSONDecoder().decode(ReportAction.self, from: Data(#""accepted""#.utf8)))
        XCTAssertNil(try? JSONDecoder().decode(ReportAction.self, from: Data(#""dismissed""#.utf8)))
    }

    // MARK: The audit's probes: each is redacted, or the report is not made.
    private func probe(_ source: String, _ original: String, _ replacement: String, names: [String] = []) -> SuggestionReport? {
        let range = (source as NSString).range(of: original)
        let edit = WritingEdit(start: range.location, end: NSMaxRange(range), replacement: replacement, original: original, ruleID: "grammar.test")
        return ReportBuilder.report(edit: edit, source: source, mode: .fix, app: "com.apple.Notes", version: "0.6.0", names: names)
    }
    func testTheAuditProbesAreRedactedOrNotReported() {
        let cases: [(source: String, original: String, replacement: String, secrets: [String])] = [
            ("hi rahul, i has told priya about it", "has", "have", ["rahul", "priya"]),
            ("rahul has the keys", "has", "have", ["rahul"]),
            ("pin is four four two one", "is", "was", ["four four", "two one"]),
            ("aman at gmail dot com", "at", "@", ["aman", "gmail"]),
            ("ping #rahulsharma now", "now", "today", ["rahulsharma"]),
            ("token " + "sk_" + "live_abcdefghijk", "token", "Token", ["sk_" + "live", "abcdefghijk"]),
            ("ok " + "gh" + "p_abcdefghijklmnopqrstuvwxyz0123 is set", "is", "was", ["gh" + "p_"]),
            ("the key AbCdEfGhIjKlMnOpQrStUvWx is set", "is", "was", ["AbCdEf"]),
            ("[name] [name] said my HIV test came back positive", "came", "come", ["HIV"]),
        ]
        for c in cases {
            guard let report = probe(c.source, c.original, c.replacement) else { continue } // not reported at all: fine
            let sent = [report.sentence, report.suggestion.original, report.suggestion.replacement].joined(separator: " | ")
            for secret in c.secrets { XCTAssertFalse(sent.lowercased().contains(secret.lowercased()), "\(c.source) → \(sent)") }
        }
        XCTAssertNil(probe("[name] [name] said my HIV test came back positive", "came", "come"), "health terms stop the report")
        XCTAssertEqual(probe("hi rahul, i has told priya about it", "has", "have")?.sentence, "hi [name], i has told [name] about it")
        XCTAssertEqual(probe("pin is four four two one", "is", "was")?.sentence, "pin is [number]")
        XCTAssertEqual(probe("aman at gmail dot com", "at", "@")?.sentence, "[email]")
    }
    func testATypoBeingCorrectedSurvivesButOtherUnknownWordsAreRedacted() throws {
        let report = try XCTUnwrap(probe("see you tomorow with neha", "tomorow", "tomorrow"))
        XCTAssertEqual(report.sentence, "see you tomorow with [name]")
        XCTAssertEqual(report.suggestion.original, "tomorow"); XCTAssertEqual(report.suggestion.replacement, "tomorrow")
        let recased = try XCTUnwrap(probe("thanks to neha for this", "neha", "Neha"))
        XCTAssertEqual(recased.suggestion.original, "[name]", "re-casing an unknown word is how a name gets capitalized: it stays redacted")
        XCTAssertEqual(recased.suggestion.replacement, "[name]")
    }
    func testNamesFromEveryCheckSourceAreRedacted() throws {
        // The app passes KnownNames.names(for:): learned, Contacts, document and lexicon names.
        let report = try XCTUnwrap(probe("ask will about it, she has it", "has", "have", names: ["Will"]))
        XCTAssertTrue(report.sentence.contains("will"), "a known name that is a common word stays lowercase: \(report.sentence)")
        let named = try XCTUnwrap(probe("ask zorblat about it, she has it", "has", "have", names: ["Zorblat"]))
        XCTAssertFalse(named.sentence.lowercased().contains("zorblat"))
    }
    func testABuiltReportIsValidAndAReportThatIsNotIsRefused() throws {
        let report = try XCTUnwrap(probe("I has it.", "has", "have"))
        XCTAssertTrue(ReportBuilder.isValid(report))
        let control = SuggestionReport(sentence: "I has\u{0007} it", suggestion: .init(start: 2, end: 5, original: "has", replacement: "have"), rule: "r", model: "rules", action: .reported, app: "a.b", version: "1")
        XCTAssertFalse(ReportBuilder.isValid(control))
        let identifiers = SuggestionReport(sentence: "I has it", suggestion: .init(start: 2, end: 5, original: "has", replacement: "have"), rule: "r", model: "rules", action: .reported, app: "my app", version: "1")
        XCTAssertFalse(ReportBuilder.isValid(identifiers))
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
        let report = try XCTUnwrap(ReportBuilder.report(edit: edit, source: "teh cat", mode: .fix, app: "my secret app name", version: "1.0 (my build)"))
        XCTAssertEqual(report.rule, "unknown"); XCTAssertEqual(report.app, "unknown"); XCTAssertEqual(report.version, "unknown")
        let none = try XCTUnwrap(ReportBuilder.report(edit: edit, source: "teh cat", mode: .fix, app: nil, version: "0.5.0"))
        XCTAssertEqual(none.app, "unknown")
    }
    func testAnEditThatNoLongerMatchesTheTextIsNotReported() {
        let edit = WritingEdit(start: 0, end: 3, replacement: "The", original: "teh")
        XCTAssertNil(ReportBuilder.report(edit: edit, source: "the cat", mode: .fix, app: "a.b", version: "1"))
        XCTAssertNil(ReportBuilder.report(edit: WritingEdit(start: 5, end: 20, replacement: "x", original: "y"), source: "short", mode: .fix, app: "a.b", version: "1"))
    }
    func testALongSentenceIsCutAtWordsAroundTheSuggestion() throws {
        let filler = Array(repeating: "word", count: 150).joined(separator: " ")
        let source = "\(filler) teh \(filler)"
        let range = (source as NSString).range(of: "teh")
        let edit = WritingEdit(start: range.location, end: NSMaxRange(range), replacement: "the", original: "teh")
        let report = try XCTUnwrap(ReportBuilder.report(edit: edit, source: source, mode: .fix, app: "a.b", version: "1"))
        XCTAssertLessThanOrEqual(report.sentence.utf16.count, 2 * ReportBuilder.context + 3)
        XCTAssertTrue(report.sentence.hasPrefix("word ")); XCTAssertTrue(report.sentence.hasSuffix(" word"))
        XCTAssertEqual((report.sentence as NSString).substring(with: NSRange(location: report.suggestion.start, length: 3)), "teh")
    }
    func testAReportOnANumberIsRedactedOnBothSides() throws {
        let source = "Pay 5O0 dollars."
        let range = (source as NSString).range(of: "5O0")
        let edit = WritingEdit(start: range.location, end: NSMaxRange(range), replacement: "500", original: "5O0")
        let report = try XCTUnwrap(ReportBuilder.report(edit: edit, source: source, mode: .fix, app: "a.b", version: "1"))
        XCTAssertEqual(report.sentence, "Pay [number] dollars.")
        XCTAssertEqual(report.suggestion.original, "[number]"); XCTAssertEqual(report.suggestion.replacement, "[number]")
    }
}
