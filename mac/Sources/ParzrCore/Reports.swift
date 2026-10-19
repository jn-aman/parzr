import Foundation
import NaturalLanguage
import os

/// What the writer did with a suggestion. Only suggestions turned down are reported: Ignore (`dismissed`) and
/// "Report wrong suggestion" (`reported`). Accepted suggestions are never sent.
public enum ReportAction: String, Codable, Sendable, CaseIterable {
    case dismissed, reported
}

/// One anonymous wrong-suggestion report: exactly what is sent, and nothing else.
/// The sentence, original and replacement are redacted on this Mac (see `Redactor`) before a report exists.
public struct SuggestionReport: Codable, Equatable, Sendable {
    public struct Suggestion: Codable, Equatable, Sendable {
        /// UTF-16 offsets of the suggestion in the redacted `sentence`.
        public let start: Int, end: Int
        public let original: String, replacement: String
    }
    /// The redacted sentence the suggestion was made in.
    public let sentence: String
    public let suggestion: Suggestion
    /// The engine rule (`grammar.your_doing`, `gector.verb_form`, `local-model`).
    public let rule: String
    /// What produced it: `rules`, `gector`, or `qwen` (with the tone for a rewrite, `qwen:professional`).
    public let model: String
    public let action: ReportAction
    /// The bundle identifier of the app the writer was in.
    public let app: String
    /// The Parzr version.
    public let version: String

    /// Field limits, mirrored by the Worker (worker/src/validate.ts).
    public enum Limits {
        public static let sentence = 1000, text = 300, rule = 100, model = 40, app = 255, version = 32
    }
}

/// Builds a report from an edit the engine made: finds its sentence, trims it, redacts it, and checks the result.
public enum ReportBuilder {
    /// The longest stretch of a sentence kept on either side of the suggestion (UTF-16), before redaction.
    static let context = 240

    public static func model(rule: String, mode: RewriteMode) -> String {
        if rule.hasPrefix("gector.") { return "gector" }
        if rule == "local-model" || rule.hasPrefix("context.") { return mode == .fix ? "qwen" : "qwen:\(mode.rawValue)" }
        return "rules"
    }
    /// Keeps only characters a bundle identifier, rule or version may hold, so free text can never ride in these fields.
    static func identifier(_ value: String?, allowed: CharacterSet, limit: Int, fallback: String) -> String {
        guard let value, !value.isEmpty, value.unicodeScalars.allSatisfy(allowed.contains), value.utf8.count <= limit else { return fallback }
        return value
    }
    static let bundleCharacters = CharacterSet(charactersIn: "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-_")
    static let ruleCharacters = CharacterSet(charactersIn: "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._:-")
    static let versionCharacters = CharacterSet(charactersIn: "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.+-")

    /// The sentence (or sentences) holding `range`, trimmed of surrounding whitespace, as a UTF-16 range of `text`.
    static func sentenceRange(of range: NSRange, in text: String) -> NSRange {
        let ns = text as NSString
        guard ns.length > 0 else { return NSRange(location: 0, length: 0) }
        let tokenizer = NLTokenizer(unit: .sentence); tokenizer.string = text
        let lower = String.Index(utf16Offset: min(range.location, ns.length), in: text)
        let upper = String.Index(utf16Offset: min(NSMaxRange(range), ns.length), in: text)
        var sentence = NSRange(tokenizer.tokenRange(for: lower..<upper), in: text)
        // An insertion at the very end of a sentence can fall outside the tokenizer's answer.
        let union = NSUnionRange(sentence, range)
        sentence = NSRange(location: max(0, union.location), length: min(ns.length, NSMaxRange(union)) - max(0, union.location))
        let space = CharacterSet.whitespacesAndNewlines
        while sentence.length > 0, sentence.location < range.location, let s = Unicode.Scalar(ns.character(at: sentence.location)), space.contains(s) { sentence.location += 1; sentence.length -= 1 }
        while sentence.length > 0, NSMaxRange(sentence) > NSMaxRange(range), let s = Unicode.Scalar(ns.character(at: NSMaxRange(sentence) - 1)), space.contains(s) { sentence.length -= 1 }
        return sentence
    }
    /// Cuts `window` down to at most `limit` UTF-16 units on each side of `keep`, at whitespace only, so no token is cut in half
    /// (half an email address or number could slip past redaction).
    static func window(_ sentence: NSRange, around keep: NSRange, in ns: NSString, limit: Int) -> NSRange {
        var start = sentence.location, end = NSMaxRange(sentence)
        let space = CharacterSet.whitespacesAndNewlines
        func isSpace(_ i: Int) -> Bool { Unicode.Scalar(ns.character(at: i)).map(space.contains) ?? false }
        if keep.location - start > limit {
            var i = keep.location - limit
            while i < keep.location, !isSpace(i) { i += 1 }
            start = i < keep.location ? i + 1 : keep.location
        }
        if end - NSMaxRange(keep) > limit {
            var i = NSMaxRange(keep) + limit
            while i > NSMaxRange(keep), !isSpace(i - 1) { i -= 1 }
            end = i > NSMaxRange(keep) ? i - 1 : NSMaxRange(keep)
        }
        return NSRange(location: start, length: max(0, end - start))
    }
    /// A report for `edit`, made in `source`, or nil when the edit does not fit the text or the result would not be clean.
    public static func report(edit: WritingEdit, source: String, action: ReportAction, mode: RewriteMode, app: String?, version: String, names: [String] = []) -> SuggestionReport? {
        let ns = source as NSString
        guard edit.start_utf16 >= 0, edit.end_utf16 >= edit.start_utf16, edit.end_utf16 <= ns.length,
              ns.substring(with: edit.range) == edit.original else { return nil }
        let sentence = sentenceRange(of: edit.range, in: source)
        let cut = window(sentence, around: edit.range, in: ns, limit: context)
        guard cut.length > 0 || edit.range.length == 0 else { return nil }
        let text = ns.substring(with: cut)
        let local = NSRange(location: edit.start_utf16 - cut.location, length: edit.range.length)
        guard let redacted = Redactor.redact(sentence: text, edit: local, replacement: edit.replacement, names: names) else { return nil }
        guard !redacted.sentence.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty,
              redacted.sentence.utf16.count <= SuggestionReport.Limits.sentence,
              redacted.original.utf16.count <= SuggestionReport.Limits.text, redacted.replacement.utf16.count <= SuggestionReport.Limits.text,
              [redacted.sentence, redacted.original, redacted.replacement].allSatisfy(Redactor.isClean) else { return nil }
        let rule = identifier(edit.rule_id, allowed: ruleCharacters, limit: SuggestionReport.Limits.rule, fallback: "unknown")
        return SuggestionReport(sentence: redacted.sentence, suggestion: .init(start: redacted.start, end: redacted.end, original: redacted.original, replacement: redacted.replacement),
                                rule: rule, model: model(rule: rule, mode: mode), action: action,
                                app: identifier(app, allowed: bundleCharacters, limit: SuggestionReport.Limits.app, fallback: "unknown"),
                                version: identifier(version, allowed: versionCharacters, limit: SuggestionReport.Limits.version, fallback: "unknown"))
    }
}

// MARK: Sending

/// How one send went.
public enum ReportSendResult: Equatable, Sendable {
    /// Stored (or already stored: a retried batch the server has seen).
    case accepted
    /// The server refused the batch for good (malformed, too large): it is dropped, never retried.
    case rejected
    /// Offline, timed out, rate limited or a server error: try again later, after `after` when the server says.
    case retry(after: TimeInterval?)
}
public protocol ReportTransport: Sendable {
    /// POSTs one batch. `key` is a random identifier for the batch, the same on every retry, so the server stores it once.
    func send(_ body: Data, key: String) async -> ReportSendResult
}

/// Plain HTTPS POST: an ephemeral session (no cookies, cache or credentials) and a bare user agent, so the request says
/// nothing about this Mac beyond what the network itself carries.
public struct URLSessionReportTransport: ReportTransport {
    public let endpoint: URL
    private let session: URLSession
    public init(endpoint: URL) {
        self.endpoint = endpoint
        let configuration = URLSessionConfiguration.ephemeral
        configuration.httpCookieAcceptPolicy = .never; configuration.httpShouldSetCookies = false
        configuration.urlCache = nil; configuration.urlCredentialStorage = nil
        configuration.timeoutIntervalForRequest = 20; configuration.timeoutIntervalForResource = 40
        configuration.waitsForConnectivity = false
        configuration.httpAdditionalHeaders = ["User-Agent": "Parzr"]
        session = URLSession(configuration: configuration)
    }
    public func send(_ body: Data, key: String) async -> ReportSendResult {
        var request = URLRequest(url: endpoint)
        request.httpMethod = "POST"; request.httpBody = body
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue(key, forHTTPHeaderField: "Idempotency-Key")
        do {
            let (_, response) = try await session.data(for: request)
            guard let http = response as? HTTPURLResponse else { return .retry(after: nil) }
            return Self.classify(status: http.statusCode, retryAfter: http.value(forHTTPHeaderField: "Retry-After"))
        } catch { return .retry(after: nil) }
    }
    public static func classify(status: Int, retryAfter: String?) -> ReportSendResult {
        switch status {
        case 200..<300, 409: return .accepted
        case 400, 413, 415, 422: return .rejected
        default: return .retry(after: retryAfter.flatMap(TimeInterval.init))
        }
    }
}

/// The switch the writer controls. Read and written from any thread, so turning reports off takes effect at once,
/// even for a report being redacted or a batch being sent at that moment.
public final class ReportGate: Sendable {
    private let state: OSAllocatedUnfairLock<Bool>
    public init(enabled: Bool) { state = OSAllocatedUnfairLock(initialState: enabled) }
    public var enabled: Bool {
        get { state.withLock { $0 } }
    }
    public func set(_ enabled: Bool) { state.withLock { $0 = enabled } }
}

/// The on-disk queue: reports wait here until they are sent, across launches and while offline.
public struct ReportStore: Sendable {
    public let url: URL?
    public init(url: URL?) { self.url = url }
    struct Saved: Codable { var items: [ReportQueue.Item] }
    func load() -> [ReportQueue.Item] {
        guard let url, let data = try? Data(contentsOf: url), let saved = try? JSONDecoder().decode(Saved.self, from: data) else { return [] }
        return saved.items
    }
    func save(_ items: [ReportQueue.Item]) {
        guard let url else { return }
        if items.isEmpty { try? FileManager.default.removeItem(at: url); return }
        try? FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
        try? JSONEncoder().encode(Saved(items: items)).write(to: url, options: [.atomic])
    }
    func erase() { if let url { try? FileManager.default.removeItem(at: url) } }
}

/// Queues reports and sends them in batches, off the main actor, with exponential backoff. Typing never waits on it:
/// `enqueue` returns at once and every send happens on this actor's own task.
public actor ReportQueue {
    public struct Policy: Sendable {
        /// The most reports kept while offline; the oldest go first.
        public var capacity = 500
        public var batchSize = 25
        /// The most bytes in one request body (the Worker refuses more than 64 KB).
        public var batchBytes = 48_000
        /// How long a new report waits for others to share its request.
        public var delay: TimeInterval = 30
        public var backoff: TimeInterval = 30
        public var maxBackoff: TimeInterval = 6 * 3600
        public init() {}
    }
    struct Item: Codable, Equatable {
        let id: UUID
        let report: SuggestionReport
        /// Set when the item first goes into a request, and kept for its retries.
        var batch: String?
    }
    public let gate: ReportGate
    private let transport: ReportTransport
    private let store: ReportStore
    private let policy: Policy
    private let sleep: @Sendable (TimeInterval) async throws -> Void
    private let jitter: @Sendable () -> Double
    private var items: [Item] = []
    private var loaded = false
    private var worker: Task<Void, Never>?
    private var generation = 0
    private(set) var failures = 0
    /// Waits the worker made (seconds), for tests.
    private(set) var waits: [TimeInterval] = []
    public init(transport: ReportTransport, store: ReportStore = ReportStore(url: nil), gate: ReportGate, policy: Policy = Policy(),
                sleep: @escaping @Sendable (TimeInterval) async throws -> Void = { try await Task.sleep(nanoseconds: UInt64(max(0, $0) * 1_000_000_000)) },
                jitter: @escaping @Sendable () -> Double = { Double.random(in: 0.8...1.2) }) {
        self.transport = transport; self.store = store; self.gate = gate; self.policy = policy; self.sleep = sleep; self.jitter = jitter
    }
    public var count: Int { loadIfNeeded(); return items.count }
    private func loadIfNeeded() {
        guard !loaded else { return }
        loaded = true
        guard gate.enabled else { store.erase(); return }
        items = store.load() + items
    }
    /// Adds a report (dropped when reports are off) and schedules a send.
    public func enqueue(_ report: SuggestionReport) { enqueue([report]) }
    public func enqueue(_ reports: [SuggestionReport]) {
        guard gate.enabled, !reports.isEmpty else { return }
        loadIfNeeded()
        items += reports.map { Item(id: UUID(), report: $0) }
        if items.count > policy.capacity { items.removeFirst(items.count - policy.capacity) }
        store.save(items)
        schedule(after: policy.delay)
    }
    /// Sends whatever is waiting (at launch, for example) after the usual short delay.
    public func resume() { loadIfNeeded(); schedule(after: policy.delay) }
    /// Reports off: forget everything queued, on disk too, and stop any send in flight.
    public func purge() {
        generation += 1; worker?.cancel(); worker = nil
        items = []; failures = 0; loaded = true
        store.erase()
    }
    private func schedule(after delay: TimeInterval) {
        guard worker == nil, gate.enabled, !items.isEmpty else { return }
        let current = generation
        worker = Task { [weak self] in await self?.run(generation: current, delay: delay) }
    }
    /// Waits until the worker is idle (tests).
    public func drain() async { while let worker { await worker.value; if self.worker == worker { self.worker = nil } } }
    private func run(generation current: Int, delay: TimeInterval) async {
        var wait = delay
        while true {
            if wait > 0 {
                waits.append(wait)
                do { try await sleep(wait) } catch { break }
            }
            guard current == generation, gate.enabled, !Task.isCancelled, !items.isEmpty else { break }
            let (ids, key, body) = nextBatch()
            guard let body else {
                // Nothing that can be encoded: drop it rather than spin.
                items.removeAll { ids.contains($0.id) }; store.save(items); wait = 0; continue
            }
            let result = await transport.send(body, key: key)
            // Turned off (or purged) while the request was out: whatever happened, keep nothing.
            guard current == generation, gate.enabled, !Task.isCancelled else { break }
            switch result {
            case .accepted, .rejected:
                items.removeAll { ids.contains($0.id) }; failures = 0; store.save(items); wait = 0
            case .retry(let after):
                failures += 1
                wait = backoff(after: after)
            }
        }
        if current == generation { worker = nil }
    }
    func backoff(after: TimeInterval?) -> TimeInterval {
        let exponential = policy.backoff * pow(2, Double(max(0, failures - 1)))
        let base = min(policy.maxBackoff, max(exponential, after ?? 0))
        return min(policy.maxBackoff, base * jitter())
    }
    /// The oldest reports that fit one request. A batch that failed is retried exactly as it was (same reports, same key),
    /// so the server can tell a retry from a new batch; reports queued since then wait for the next one.
    private func nextBatch() -> (Set<UUID>, String, Data?) {
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        if let key = items.first?.batch {
            let chosen = items.filter { $0.batch == key }
            return (Set(chosen.map(\.id)), key, try? encoder.encode(ReportBatch(reports: chosen.map(\.report))))
        }
        let key = UUID().uuidString.lowercased()
        var chosen: [Item] = []
        for item in items where chosen.count < policy.batchSize && item.batch == nil {
            let trial = chosen + [item]
            guard let data = try? encoder.encode(ReportBatch(reports: trial.map(\.report))), data.count <= policy.batchBytes else { break }
            chosen = trial
        }
        if chosen.isEmpty {
            // A single report too large for any request can never be sent.
            if !items.isEmpty { items.removeFirst(); store.save(items) }
            return ([], key, nil)
        }
        let ids = Set(chosen.map(\.id))
        for i in items.indices where ids.contains(items[i].id) { items[i].batch = key }
        store.save(items)
        return (ids, key, try? encoder.encode(ReportBatch(reports: chosen.map(\.report))))
    }
}

/// The request body: `{"reports": [...]}`.
public struct ReportBatch: Codable, Equatable, Sendable {
    public let reports: [SuggestionReport]
}

/// Builds reports off the main actor and hands them to the queue; the one entry point the app uses.
public final class ReportCenter: Sendable {
    public let gate: ReportGate
    public let queue: ReportQueue
    public init(queue: ReportQueue) { self.queue = queue; gate = queue.gate }
    public convenience init(endpoint: URL, storeURL: URL?, enabled: Bool) {
        let gate = ReportGate(enabled: enabled)
        self.init(queue: ReportQueue(transport: URLSessionReportTransport(endpoint: endpoint), store: ReportStore(url: storeURL), gate: gate))
    }
    /// Reports on or off. Off takes effect immediately: nothing more is queued or sent, and the queue is erased.
    public func setEnabled(_ enabled: Bool) {
        gate.set(enabled)
        Task { [queue] in if enabled { await queue.resume() } else { await queue.purge() } }
    }
    /// Redacts and queues one report per edit, in the background. Returns at once.
    @discardableResult
    public func submit(_ edits: [WritingEdit], source: String, action: ReportAction, mode: RewriteMode, app: String?, version: String, names: @escaping @Sendable () -> [String] = { [] }) -> Task<Void, Never>? {
        guard gate.enabled, !edits.isEmpty else { return nil }
        return Task.detached(priority: .utility) { [gate, queue] in
            let known = names()
            var reports: [SuggestionReport] = []
            for edit in edits {
                guard gate.enabled else { return }
                if let report = ReportBuilder.report(edit: edit, source: source, action: action, mode: mode, app: app, version: version, names: known) { reports.append(report) }
            }
            await queue.enqueue(reports)
        }
    }
}
