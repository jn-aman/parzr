import Foundation
import ParzrKit

/// Checks the sentence before the cursor while the user types: with the Rust engine when it fits
/// the keyboard's memory, else with the system spell checker. One check at a time; a newer
/// keystroke cancels the older check.
@MainActor
final class KeyboardChecker {
    enum Checker: String { case engine = "engine", system = "system spelling" }

    private(set) var checker: Checker
    private(set) var context: SentenceContext?
    private(set) var suggestions: [Suggestion] = []
    /// Every edit of the last check (the bar shows at most three suggestions).
    private(set) var edits: [WritingEdit] = []
    var onChange: (() -> Void)?

    private var task: Task<Void, Never>?
    private let engine = ParzrEngine.shared
    /// How long typing pauses before a check, in milliseconds.
    static let debounce: Duration = .milliseconds(250)

    init() {
        checker = MemoryBudget.engineFits() ? .engine : .system
        engine.setKnownWords { SystemSpelling.knownWordsFromAnyThread(in: $0) }
    }

    private var inFlight: String?

    func schedule(before: String?, settings: KeyboardSettings) {
        guard let context = SentenceContext.current(before: before) else {
            task?.cancel(); inFlight = nil
            self.context = nil
            if !suggestions.isEmpty { suggestions = []; edits = []; onChange?() }
            return
        }
        // Typing inside the pending word, or moving the cursor, keeps the current check.
        if context.text == self.context?.text || context.text == inFlight { return }
        task?.cancel()
        inFlight = context.text
        let checker = self.checker
        let engine = self.engine
        task = Task { [weak self] in
            try? await Task.sleep(for: Self.debounce)
            guard !Task.isCancelled else { return }
            let result: RewriteResult?
            switch checker {
            case .engine: result = try? await engine.check(context.request(settings: settings))
            case .system: result = SystemSpelling.edits(in: context.text, dictionary: settings.dictionary)
            }
            guard !Task.isCancelled, let self else { return }
            self.inFlight = nil
            self.context = context
            self.edits = result?.edits ?? []
            self.suggestions = result.map { Suggestion.from($0, limit: 3) } ?? []
            self.onChange?()
        }
    }

    /// The plan for applying a suggestion to the text now before the cursor.
    func plan(_ suggestion: Suggestion, before: String?) -> ProxyEdit? {
        guard let context, let before else { return nil }
        return ProxyEdit.plan(suggestion.edits, checked: context.text, before: before)
    }

    /// The plan for applying every suggestion at once.
    func planAll(before: String?) -> ProxyEdit? {
        guard let context, let before, !edits.isEmpty else { return nil }
        return ProxyEdit.plan(edits, checked: context.text, before: before)
    }

    func reset() {
        task?.cancel()
        inFlight = nil
        context = nil
        suggestions = []
        edits = []
        onChange?()
    }
}
