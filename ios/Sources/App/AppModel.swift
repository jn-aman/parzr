import SwiftUI
import UIKit
import ParzrKit

/// The containing app's state: the scratchpad, Apple Intelligence status, settings shared with
/// the keyboard, and the keyboard's rewrite handoffs (answered whenever the app is active).
@MainActor
@Observable
final class AppModel {
    static let keyboardBundleID = "app.parzr.ios.keyboard"

    var text = ""
    var suggestions: [Suggestion] = []
    var checking = false
    var checkError: String?
    var lastCheckedText: String?

    var rewriteMode: RewriteMode = .professional
    var rewriting = false
    var rewriteOutcome: ToneOutcome?
    var appleModel: AppleModelStatus = .current

    var settings: KeyboardSettings { didSet { store.settings = settings } }
    var keyboardReport: SharedStore.KeyboardReport?
    var handoffNotice: String?

    private let store = SharedStore.shared
    private let engine = ParzrEngine.shared
    private var checkTask: Task<Void, Never>?

    init() {
        settings = SharedStore.shared.settings
        engine.setKnownWords { SystemSpelling.knownWordsFromAnyThread(in: $0) }
    }

    /// Parzr's keyboard is in the user's keyboard list (Settings > General > Keyboard).
    var keyboardEnabled: Bool {
        (UserDefaults.standard.array(forKey: "AppleKeyboards") as? [String])?.contains(Self.keyboardBundleID) ?? false
    }

    func becameActive() {
        appleModel = .current
        keyboardReport = store.keyboardReport
        settings = store.settings
        if appleModel.isAvailable { ToneRewriter.prewarm() }
        Task { await answerHandoff() }
    }

    // MARK: Scratchpad

    func scheduleCheck() {
        checkTask?.cancel()
        let text = self.text
        guard text != lastCheckedText else { return }
        checkTask = Task {
            try? await Task.sleep(for: .milliseconds(300))
            guard !Task.isCancelled else { return }
            await check(text)
        }
    }

    func check(_ text: String) async {
        checking = true
        defer { checking = false }
        do {
            let result = try await engine.check(EngineRequest(text: text, dictionary: settings.dictionary, names: settings.names, dialect: settings.dialect))
            guard text == self.text else { return }
            suggestions = Suggestion.from(result).sorted { $0.edits[0].start_utf16 < $1.edits[0].start_utf16 }
            lastCheckedText = text
            checkError = nil
        } catch {
            checkError = error.localizedDescription
        }
    }

    func apply(_ suggestion: Suggestion) {
        guard let updated = try? EditPlan.apply(suggestion.edits, to: text) else { suggestions = []; return }
        let removed = Set(suggestion.edits.map(\.id))
        // Edits after the applied one move; checking again is simpler and exact.
        text = updated
        suggestions.removeAll { $0.edits.contains { removed.contains($0.id) } }
        lastCheckedText = nil
        scheduleCheck()
    }

    func applyAll() {
        let edits = suggestions.flatMap(\.edits).sorted { $0.start_utf16 < $1.start_utf16 }
        guard let updated = try? EditPlan.apply(edits, to: text) else { return }
        text = updated
        suggestions = []
        lastCheckedText = nil
        scheduleCheck()
    }

    func rewrite() async {
        rewriting = true
        rewriteOutcome = nil
        defer { rewriting = false }
        rewriteOutcome = await ToneRewriter().rewrite(text, mode: rewriteMode, settings: settings)
    }

    func useRewrite() {
        guard let rewritten = rewriteOutcome?.text else { return }
        text = rewritten
        rewriteOutcome = nil
        lastCheckedText = nil
        scheduleCheck()
    }

    // MARK: Keyboard handoff

    /// Writes the rewrite the keyboard asked for, for the keyboard to offer when the user returns.
    func answerHandoff() async {
        guard let handoff = store.pending() else { return }
        handoffNotice = "Writing the \(handoff.mode.title) version the keyboard asked for…"
        // The app has the whole budget: a cold model may take a few seconds more than the keyboard's deadline.
        let outcome = await ToneRewriter(timeout: .seconds(8)).rewrite(handoff.source, mode: handoff.mode, settings: settings)
        store.finish(handoff.id, result: outcome.text, note: outcome.text == nil ? outcome.message : nil)
        handoffNotice = outcome.text != nil
            ? "Your \(handoff.mode.title) version is ready. Go back to your app and tap it in the Parzr keyboard."
            : outcome.message
    }
}
