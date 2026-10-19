import Foundation
internal import ParzrEngineFFI

/// Parzr's Rust rules engine, linked statically from ios/Engine/ParzrEngine.xcframework (built by
/// ios/scripts/build-engine-xcframework.sh, rules only). Calls run one at a time on a private
/// queue: the engine keeps per-thread caches, and typing must never block the main thread.
///
/// Memory: the engine's spelling and word-pair tables are compiled into the binary and read in
/// place, so a check peaks at about 20 MB and a long session stays near 30 MB (measured on
/// macOS, see ios/README.md). The keyboard still asks `MemoryBudget` before it loads the engine.
public final class ParzrEngine: @unchecked Sendable {
    public static let shared = ParzrEngine()
    /// Words the system spell checker accepts in a text (lowercase, shaped as `WordShape.shaped`).
    public typealias KnownWords = @Sendable (String) -> Set<String>
    private let queue = DispatchQueue(label: "app.parzr.engine", qos: .userInitiated)
    private let lock = NSLock()
    private var knownWords: KnownWords?
    private var used = false

    public init() {}

    /// True once any request has run (and so the engine's tables are built in this process).
    public var isLoaded: Bool { lock.withLock { used } }

    public func setKnownWords(_ provider: KnownWords?) { lock.withLock { knownWords = provider } }

    public func check(_ request: EngineRequest) async throws -> RewriteResult {
        try await withCheckedThrowingContinuation { continuation in
            queue.async { continuation.resume(with: Result { try self.checkNow(request) }) }
        }
    }

    /// Runs a request on the calling thread. Prefer `check(_:)` from UI code.
    public func checkNow(_ request: EngineRequest) throws -> RewriteResult {
        guard request.text.utf8.count <= 65_536 else { throw ParzrError.message("Select at most 64 KB of text.") }
        var tokens = request.tokens
        if tokens.isEmpty, !request.text.isEmpty {
            let known = lock.withLock { knownWords }?(request.text) ?? []
            tokens = LinguisticHints.hints(for: request.text, known: known)
        }
        let enriched = EngineRequest(text: request.text, mode: request.mode, dictionary: request.dictionary, names: request.names, capitalizeNames: request.capitalize_names, dialect: request.dialect, protectedRanges: request.protected_ranges, tokens: tokens, sentenceStart: request.sentence_start, sentenceEnd: request.sentence_end, deep: request.deep, gec: false, casual: request.casual)
        let data = try Self.call(try JSONEncoder().encode(enriched)) { parzr_rewrite_json($0) }
        lock.withLock { used = true }
        struct Failure: Decodable { let error: String }
        if let failure = try? JSONDecoder().decode(Failure.self, from: data) { throw ParzrError.message(failure.error) }
        let result = try JSONDecoder().decode(RewriteResult.self, from: data)
        try EditPlan.validate(result.edits, in: request.text)
        guard try EditPlan.apply(result.edits, to: request.text) == result.text else { throw ParzrError.message("The engine returned an inconsistent edit plan.") }
        return result
    }

    /// The engine's verdict on a rewrite written elsewhere (Apple Foundation Models).
    public struct GuardVerdict: Decodable, Sendable, Equatable {
        public let ok: Bool
        /// The rewrite without an announcing preamble ("Here is the edited text:").
        public let output: String
        public let reason: String?
    }

    /// Checks that `output`, a `mode` rewrite of `source`, keeps its meaning: the same guard the
    /// engine's own tone rewrites pass (names, numbers, negation, content words).
    public func guardRewrite(mode: RewriteMode, source: String, output: String) async throws -> GuardVerdict {
        try await withCheckedThrowingContinuation { continuation in
            queue.async { continuation.resume(with: Result { try self.guardNow(mode: mode, source: source, output: output) }) }
        }
    }

    public func guardNow(mode: RewriteMode, source: String, output: String) throws -> GuardVerdict {
        struct Request: Encodable { let mode: RewriteMode, source: String, output: String, source_tokens: [TokenHint], output_tokens: [TokenHint] }
        let known = lock.withLock { knownWords }
        let request = Request(mode: mode, source: source, output: output,
                              source_tokens: LinguisticHints.hints(for: source, known: known?(source) ?? []),
                              output_tokens: LinguisticHints.hints(for: output, known: known?(output) ?? []))
        let data = try Self.call(try JSONEncoder().encode(request)) { parzr_tone_guard_json($0) }
        lock.withLock { used = true }
        struct Failure: Decodable { let error: String }
        if let failure = try? JSONDecoder().decode(Failure.self, from: data) { throw ParzrError.message(failure.error) }
        return try JSONDecoder().decode(GuardVerdict.self, from: data)
    }

    /// A reviewed misspelling (teh, recieved, alot) that must never be learned as a name.
    public static func isKnownMisspelling(_ word: String) -> Bool { word.withCString { parzr_is_known_misspelling($0) } == 1 }

    private static func call(_ json: Data, _ function: (UnsafePointer<CChar>) -> UnsafeMutablePointer<CChar>?) throws -> Data {
        guard let input = String(data: json, encoding: .utf8) else { throw ParzrError.message("The writing engine could not respond.") }
        guard let output = input.withCString(function) else { throw ParzrError.message("The writing engine could not respond.") }
        defer { parzr_string_free(output) }
        return Data(String(cString: output).utf8)
    }
}
