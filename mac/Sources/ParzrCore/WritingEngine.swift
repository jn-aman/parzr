import Foundation
import Darwin
import NaturalLanguage

/// The engine actor isolates Rust's per-thread state and keeps analysis off the UI actor.
public actor WritingEngine {
    public static let shared = WritingEngine()
    /// Typing cannot wait behind a long tone rewrite on the model actor.
    public static let typing = WritingEngine()
    private var library: UnsafeMutableRawPointer?
    private var rewriteFunction: (@convention(c) (UnsafePointer<CChar>?) -> UnsafeMutablePointer<CChar>?)?
    private var freeFunction: (@convention(c) (UnsafeMutablePointer<CChar>?) -> Void)?
    private final class Cancellation: @unchecked Sendable {
        let function: @convention(c) () -> Void
        init(_ function: @escaping @convention(c) () -> Void) { self.function = function }
    }
    private var cancellation: Cancellation?
    static func libraryPaths(bundle: URL, workingDirectory: URL, supplied: String?) -> [String] {
        var paths = [supplied, bundle.appendingPathComponent("Contents/Frameworks/libparzr_engine.dylib").path].compactMap { $0 }
        // An installed app must use its bundled engine. Swift package launches can start
        // from either the repository root or mac/, including an IDE's working directory.
        if bundle.pathExtension != "app" {
            var directory = workingDirectory.standardizedFileURL
            for _ in 0..<8 {
                if FileManager.default.fileExists(atPath: directory.appendingPathComponent("engine/Cargo.toml").path) {
                    paths.append(directory.appendingPathComponent("engine/target/release/libparzr_engine.dylib").path)
                    break
                }
                let parent = directory.deletingLastPathComponent()
                if parent == directory { break }
                directory = parent
            }
        }
        return paths
    }
    private func load() throws {
        if rewriteFunction != nil { return }
        let supplied = ProcessInfo.processInfo.environment["PARZR_ENGINE_PATH"]
        let paths = Self.libraryPaths(bundle: Bundle.main.bundleURL, workingDirectory: URL(fileURLWithPath: FileManager.default.currentDirectoryPath), supplied: supplied)
        for path in paths {
            guard let handle = dlopen(path, RTLD_NOW | RTLD_LOCAL) else { continue }
            guard let rewrite = dlsym(handle, "parzr_rewrite_json"), let free = dlsym(handle, "parzr_string_free"), let cancel = dlsym(handle, "parzr_cancel_rewrite") else { dlclose(handle); continue }
            library = handle
            rewriteFunction = unsafeBitCast(rewrite, to: (@convention(c) (UnsafePointer<CChar>?) -> UnsafeMutablePointer<CChar>?).self)
            freeFunction = unsafeBitCast(free, to: (@convention(c) (UnsafeMutablePointer<CChar>?) -> Void).self)
            cancellation = Cancellation(unsafeBitCast(cancel, to: (@convention(c) () -> Void).self))
            return
        }
        throw ParzrError.message(Bundle.main.bundleURL.pathExtension == "app" ? "The bundled writing engine could not load. Reinstall Parzr." : "Build the local engine with cargo build --release, or set PARZR_ENGINE_PATH to its library.")
    }
    private static func linguisticHints(for text: String) -> [TokenHint] {
        // Per-call tagger; NLTagger mutable state never crosses worker boundaries.
        let tagger = NLTagger(tagSchemes: [.lexicalClass, .lemma, .nameType])
        tagger.string = text
        // Without a language, short texts get no tags and "aman jain" is detected as Indonesian.
        tagger.setLanguage(.english, range: text.startIndex..<text.endIndex)
        var hints: [TokenHint] = []
        tagger.enumerateTags(in: text.startIndex..<text.endIndex, unit: .word, scheme: .lexicalClass, options: [.omitWhitespace, .omitPunctuation]) { tag, range in
            let lemma = tagger.tag(at: range.lowerBound, unit: .word, scheme: .lemma).0?.rawValue ?? String(text[range]).lowercased()
            let name = tagger.tag(at: range.lowerBound, unit: .word, scheme: .nameType).0
            // A lower-case typo next to a name must not become a protected last name.
            let named = (name == .personalName || name == .placeName || name == .organizationName)
                && text[range].contains(where: \.isUppercase)
            hints.append(TokenHint(range: NSRange(range, in: text), pos: tag?.rawValue ?? "Other", lemma: lemma, name: named))
            return true
        }
        return mergePossessives(hints, in: text)
    }
    /// NLTagger splits "Aman's" into "Aman" and "'s"; fold the clitic into the name's range so the hint matches the engine's token.
    static func mergePossessives(_ hints: [TokenHint], in text: String) -> [TokenHint] {
        let ns = text as NSString
        var out: [TokenHint] = []
        for hint in hints {
            if let last = out.last, last.name, last.end_utf16 == hint.start_utf16, hint.end_utf16 <= ns.length, ["'s", "\u{2019}s"].contains(ns.substring(with: NSRange(location: hint.start_utf16, length: hint.end_utf16 - hint.start_utf16))) {
                out[out.count - 1] = TokenHint(range: NSRange(location: last.start_utf16, length: hint.end_utf16 - last.start_utf16), pos: last.pos, lemma: last.lemma, name: true)
            } else { out.append(hint) }
        }
        return out
    }
    public func rewrite(_ request: EngineRequest) async throws -> RewriteResult {
        try Task.checkCancellation()
        try load()
        guard request.text.utf8.count <= 65_536 else { throw ParzrError.message("Select at most 64 KB of text.") }
        let tokens = request.tokens.isEmpty ? Self.linguisticHints(for: request.text) : request.tokens
        let enriched = EngineRequest(text: request.text, mode: request.mode, dictionary: request.dictionary, names: request.names, capitalizeNames: request.capitalize_names, dialect: request.dialect, protectedRanges: request.protected_ranges, tokens: tokens, sentenceStart: request.sentence_start, sentenceEnd: request.sentence_end, deep: request.deep)
        let input = try JSONEncoder().encode(enriched)
        guard let string = String(data: input, encoding: .utf8), let function = rewriteFunction, let cancellation else { throw ParzrError.message("The writing engine could not respond.") }
        let output = try await withTaskCancellationHandler {
            try Task.checkCancellation()
            return string.withCString { function($0) }
        } onCancel: { if request.deep || request.mode != .fix { cancellation.function() } }
        guard let output else { throw ParzrError.message("The writing engine could not respond.") }
        defer { freeFunction?(output) }
        try Task.checkCancellation()
        let data = Data(String(cString: output).utf8)
        struct Failure: Decodable { let error: String }
        if let error = try? JSONDecoder().decode(Failure.self, from: data) { throw ParzrError.message(error.error) }
        let result = try JSONDecoder().decode(RewriteResult.self, from: data)
        try EditPlan.validate(result.edits, in: request.text)
        guard try EditPlan.apply(result.edits, to: request.text) == result.text else { throw ParzrError.message("The engine returned an inconsistent edit plan.") }
        return result
    }
}
