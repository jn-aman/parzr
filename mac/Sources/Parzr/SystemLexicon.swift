import AppKit
import ParzrCore

/// Bounded recency cache: when full, the oldest eighth is dropped in one sweep.
struct LRUCache<Value> {
    let capacity: Int
    private var items: [String: (value: Value, tick: UInt64)] = [:]
    private var tick: UInt64 = 0
    var count: Int { items.count }
    init(capacity: Int) { self.capacity = capacity }
    mutating func value(for key: String) -> Value? {
        guard let item = items[key] else { return nil }
        tick += 1; items[key] = (item.value, tick); return item.value
    }
    mutating func set(_ value: Value, for key: String) {
        tick += 1; items[key] = (value, tick)
        if items.count > capacity { for (stale, _) in items.sorted(by: { $0.value.tick < $1.value.tick }).prefix(max(1, capacity / 8)) { items[stale] = nil } }
    }
}

/// Results of a text scan remembered by the hash of the text (the text itself is never kept), shared by detached scans.
final class ScanMemo: @unchecked Sendable {
    private let lock = NSLock()
    private var cache: LRUCache<[String]>
    init(capacity: Int) { cache = LRUCache(capacity: capacity) }
    func value(for text: Substring, make: () -> [String]) -> [String] {
        let key = String(text.hashValue)
        lock.lock(); let hit = cache.value(for: key); lock.unlock()
        if let hit { return hit }
        let made = make()
        lock.lock(); cache.set(made, for: key); lock.unlock()
        return made
    }
}

/// What the system spell checker says; injectable so the gate logic is testable without AppKit state.
struct LexiconProbe: Sendable {
    /// Misspelled words of `text`, in order, as written.
    var misspelled: @Sendable (String) -> [String]
    /// True when the system lexicon accepts `word` as written (so "Jatin" yes, "jatin" no).
    var accepts: @Sendable (String) -> Bool
    private static let tag = NSSpellChecker.uniqueSpellDocumentTag()
    static let system = LexiconProbe(
        misspelled: { text in
            let checker = NSSpellChecker.shared, ns = text as NSString
            var found: [String] = [], at = 0
            while at < ns.length, found.count < 2000 {
                let range = checker.checkSpelling(of: text, startingAt: at, language: "en", wrap: false, inSpellDocumentWithTag: tag, wordCount: nil)
                guard range.location != NSNotFound, range.length > 0 else { break }
                found.append(ns.substring(with: range)); at = NSMaxRange(range)
            }
            return found
        },
        accepts: { NSSpellChecker.shared.checkSpelling(of: $0, startingAt: 0, language: "en", wrap: false, inSpellDocumentWithTag: tag, wordCount: nil).location == NSNotFound })
}

/// macOS knows proper names only in their Capitalized form: "jatin" is flagged, "Jatin" is accepted, while a typo ("recieve") stays flagged either way.
/// So a lowercase word the lexicon rejects but accepts Capitalized is a name, and goes to the engine as one (session only, never stored).
struct NameGate {
    static let maxTokens = 1000, cacheSize = 2000
    /// What the lexicon says about one lowercase word.
    struct Info { var name: Bool, accepted: Bool }
    private var cache = LRUCache<Info>(capacity: cacheSize)
    private let probe: LexiconProbe
    init(probe: LexiconProbe = .system) { self.probe = probe }
    nonisolated static func shaped(_ raw: String) -> String? { WordShape.shaped(raw) }
    /// Each hyphen part capitalized ("jean-luc" to "Jean-Luc").
    nonisolated static func capitalized(_ word: String) -> String {
        word.split(separator: "-", omittingEmptySubsequences: false).map { $0.prefix(1).uppercased() + $0.dropFirst() }.joined(separator: "-")
    }
    /// Distinct shaped tokens in text order, at most `maxTokens`.
    nonisolated static func candidates(in text: String) -> [String] {
        var seen = Set<String>(), out: [String] = []
        for raw in String(text.prefix(65_536)).split(whereSeparator: { !($0.isLetter || "'\u{2019}-".contains($0)) }) where out.count < maxTokens {
            if let word = shaped(String(raw)), seen.insert(word).inserted { out.append(word) }
        }
        return out
    }
    /// Names among the lowercase words of `text`, and those the checker accepts as spelled. One spell-check pass, and only when some word is not cached yet.
    mutating func scan(_ text: String) -> (names: [String], accepted: Set<String>) {
        let tokens = Self.candidates(in: text)
        let fresh = tokens.filter { cache.value(for: $0) == nil }
        if !fresh.isEmpty {
            let found = probe.misspelled(String(text.prefix(65_536)))
            let flagged = Set(found.compactMap(Self.shaped))
            // Past the probe's scan cap nothing is known, so nothing is accepted.
            let capped = found.count >= 2000
            for word in fresh {
                let rejected = flagged.contains(word)
                cache.set(Info(name: rejected && probe.accepts(Self.capitalized(word)), accepted: !rejected && !capped), for: word)
            }
        }
        let infos = tokens.compactMap { word in cache.value(for: word).map { (word, $0) } }
        return (infos.filter { $0.1.name }.map(\.0), Set(infos.filter { $0.1.accepted }.map(\.0)))
    }
    mutating func names(in text: String) -> [String] { scan(text).names }
}

/// NSSpellChecker is not documented as thread-safe, so every lookup runs on this one serial queue, off the main actor (a 2 KB paragraph costs a few ms cold, near zero cached).
final class SystemLexicon: @unchecked Sendable {
    static let shared = SystemLexicon()
    private let queue = DispatchQueue(label: "app.parzr.lexicon", qos: .userInitiated)
    private var gate = NameGate()
    func scan(_ text: String) async -> (names: [String], accepted: Set<String>) {
        await withCheckedContinuation { continuation in queue.async { continuation.resume(returning: self.gate.scan(text)) } }
    }
    func names(in text: String) async -> [String] { await scan(text).names }
}
