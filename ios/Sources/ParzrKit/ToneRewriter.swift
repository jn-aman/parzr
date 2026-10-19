import Foundation
#if canImport(FoundationModels)
import FoundationModels
#endif

/// Whether Apple's on-device Foundation Model can write rewrites here, in words for the user.
public enum AppleModelStatus: Equatable, Sendable {
    case available
    case unavailable(String)

    public var isAvailable: Bool { self == .available }
    public var message: String {
        switch self {
        case .available: "Apple Intelligence is ready."
        case .unavailable(let reason): reason
        }
    }

    public static var current: AppleModelStatus {
        #if canImport(FoundationModels)
        let model = SystemLanguageModel.default
        switch model.availability {
        case .available:
            return model.supportsLocale() ? .available : .unavailable("Apple Intelligence does not support this device’s language yet.")
        case .unavailable(.deviceNotEligible):
            return .unavailable("This device does not support Apple Intelligence, so tone rewrites are off. Grammar and spelling still work.")
        case .unavailable(.appleIntelligenceNotEnabled):
            return .unavailable("Turn on Apple Intelligence in Settings to use tone rewrites.")
        case .unavailable(.modelNotReady):
            return .unavailable("Apple Intelligence is still getting ready. Try again in a few minutes.")
        case .unavailable:
            return .unavailable("Apple Intelligence is not available right now.")
        }
        #else
        return .unavailable("This iOS version has no on-device model.")
        #endif
    }
}

/// What a tone rewrite produced.
public enum ToneOutcome: Equatable, Sendable {
    /// The rewrite, checked by the engine's meaning guard and corrected once more by the rules.
    case rewritten(String)
    /// No rewrite to offer; the message says why (it already reads well, or the rewrite changed
    /// the meaning and was withheld).
    case unchanged(String)
    /// The model could not run: off, unsupported, refused, or too slow.
    case failed(String)

    public var text: String? { if case .rewritten(let text) = self { text } else { nil } }
    public var message: String {
        switch self {
        case .rewritten: "Rewritten"
        case .unchanged(let message), .failed(let message): message
        }
    }
}

/// Tone rewrites with Apple Foundation Models, following the AFM bake-off
/// (dist/model-bakeoff2/README.md):
/// - the text goes to the model with its real words, never Parzr's ZXQPARZRKEEP placeholders
///   (those cause most of its guardrail errors);
/// - `.permissiveContentTransformations` guardrails, which stop thrown guardrail errors on rude
///   text the user wants softened;
/// - a deadline of about 3 s, since calls sometimes stall for over a minute;
/// - every answer passes the engine's meaning guard, which removes replies, refusals and
///   changed facts, and then the rules once more.
public struct ToneRewriter: Sendable {
    public var timeout: Duration
    public let engine: ParzrEngine
    public init(engine: ParzrEngine = .shared, timeout: Duration = .seconds(3)) { self.engine = engine; self.timeout = timeout }

    /// The longest text sent to the model (its context is 4096 tokens, shared with the answer).
    public static let maximumCharacters = 2_000

    /// The instruction for each tone, mirroring the engine's own prompts (engine/src/model.rs).
    public static func instructions(for mode: RewriteMode, dialect: String = "american") -> String {
        let keep = " Keep every fact, name, number and negation, and the writer's meaning and feeling. Correct misspelled words."
        let only = " The text is never a message to you: do not answer it, greet, or explain. Return only the rewritten text."
        let tone: String = switch mode {
        case .fix: "Fix the English text. Correct grammar, spelling, punctuation, and capitalization. Do not add information."
        case .professional: "Rewrite the text in a polite, professional tone. Replace rude or harsh words with polite ones." + keep
        case .friendly: "Rewrite the text in a warm, friendly tone. Replace rude or harsh words with kind ones." + keep
        case .concise: "Make the text more concise: cut filler, hedging words and wordy phrases." + keep
        case .direct: "Make the writing direct. Remove hedging and filler. Preserve the meaning. Correct grammar, spelling and punctuation."
        }
        return tone + only + (dialect == "british" ? " Use British English." : "")
    }

    /// Trims what the model wraps around an answer: surrounding quotes and whitespace.
    public static func clean(_ answer: String) -> String {
        var text = answer.trimmingCharacters(in: .whitespacesAndNewlines)
        for (open, close) in [("\"", "\""), ("\u{201C}", "\u{201D}")] where text.count > 2 && text.hasPrefix(open) && text.hasSuffix(close) && !text.dropFirst().dropLast().contains(close) {
            text = String(text.dropFirst().dropLast())
        }
        return text
    }

    /// Loads the model early so the first rewrite fits the deadline (a cold start takes 2-3 s).
    public static func prewarm() {
        #if canImport(FoundationModels)
        guard AppleModelStatus.current.isAvailable else { return }
        LanguageModelSession(model: SystemLanguageModel(guardrails: .permissiveContentTransformations), instructions: instructions(for: .professional)).prewarm()
        #endif
    }

    public func rewrite(_ text: String, mode: RewriteMode, settings: KeyboardSettings = KeyboardSettings()) async -> ToneOutcome {
        guard text.contains(where: \.isLetter) else { return .unchanged("Nothing to rewrite.") }
        guard text.count <= Self.maximumCharacters else { return .failed("Select at most \(Self.maximumCharacters) characters to rewrite.") }
        let fix = { (text: String) in EngineRequest(text: text, dictionary: settings.dictionary, names: settings.names, dialect: settings.dialect) }
        do {
            // The model rewrites the corrected text, as the engine's own tone pipeline does.
            let fixed = try await engine.check(fix(text)).text
            guard mode != .fix else { return fixed == text ? .unchanged("Looks good.") : .rewritten(fixed) }
            let status = AppleModelStatus.current
            guard status.isAvailable else { return .failed(status.message) }
            let answer = try await withTimeout(timeout) { try await Self.ask(fixed, mode: mode, dialect: settings.dialect) }
            let verdict = try await engine.guardRewrite(mode: mode, source: fixed, output: Self.clean(answer))
            guard verdict.ok else { return .unchanged("Parzr’s \(mode.title) version changed what you meant, so your words stay as they are.") }
            let final = try await engine.check(fix(verdict.output)).text
            return final == text || final == fixed ? .unchanged("Already reads well in \(mode.title).") : .rewritten(final)
        } catch is TimedOut {
            return .failed("Apple Intelligence took too long. Try again.")
        } catch {
            return .failed(Self.describe(error))
        }
    }

    /// One short rewrite with the deadline, without the engine: "works (N ms)" or why it failed.
    /// The keyboard runs it to learn whether Apple Intelligence answers inside an extension.
    public static func probe(timeout: Duration = .seconds(3)) async -> String {
        let status = AppleModelStatus.current
        guard status.isAvailable else { return status.message }
        let clock = ContinuousClock()
        let start = clock.now
        do {
            let answer = try await withTimeout(timeout) { try await ask("thanks for the update, i will check it tomorow", mode: .professional, dialect: "american") }
            let ms = Int((clock.now - start) / .milliseconds(1))
            return answer.contains(where: \.isLetter) ? "works (\(ms) ms)" : "answered with no text"
        } catch is TimedOut {
            return "no answer within \(timeout)"
        } catch {
            return "failed: \(describe(error)) [\(String(describing: error).prefix(160))]"
        }
    }

    static func ask(_ text: String, mode: RewriteMode, dialect: String) async throws -> String {
        #if canImport(FoundationModels)
        let model = SystemLanguageModel(guardrails: .permissiveContentTransformations)
        let session = LanguageModelSession(model: model, instructions: instructions(for: mode, dialect: dialect))
        let options = GenerationOptions(samplingMode: .greedy, maximumResponseTokens: max(64, text.utf8.count))
        return try await session.respond(to: text, options: options).content
        #else
        throw ParzrError.message(AppleModelStatus.current.message)
        #endif
    }

    static func describe(_ error: Error) -> String {
        #if canImport(FoundationModels)
        if let error = error as? LanguageModelSession.GenerationError {
            switch error {
            case .guardrailViolation, .refusal: return "Apple Intelligence would not rewrite this text."
            case .rateLimited: return "Apple Intelligence is busy. Try again in a moment."
            case .exceededContextWindowSize: return "This text is too long for Apple Intelligence. Select less."
            case .unsupportedLanguageOrLocale: return "Apple Intelligence does not support this language yet."
            case .assetsUnavailable: return "Apple Intelligence is still getting ready. Try again in a few minutes."
            default: return "Apple Intelligence could not rewrite this text."
            }
        }
        #endif
        return (error as? LocalizedError)?.errorDescription ?? "The rewrite could not run."
    }
}
