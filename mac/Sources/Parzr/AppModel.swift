import AppKit
import SwiftUI
import ParzrCore

@MainActor
final class AppModel: ObservableObject {
    @Published var studioRoute: StudioRoute = .playground
    @Published var mode: RewriteMode = .fix
    @Published var result: RewriteResult?
    @Published var busy = false
    /// The shown edits come from an earlier version of the text, carried over typing. They are drawn but never applied.
    @Published private(set) var provisional = false
    @Published var error: String?
    @Published var status: String?
    @Published var source = ""
    @Published var sourceApp = "Playground"
    @Published var selectedEdits: Set<String> = []
    @Published var focusedEditID: String?
    @Published var inspector = "Select text in an editor and use Option+Space. The compatibility report contains capabilities only."
    @Published var engineReady = false
    @Published var shortcutConflict = false
    @Published var selectionHint = false
    /// The rewrite offered after a Fix check (the selection card only), in the tone that fits the app; written in the background.
    @Published var suggestion: SuggestedVersion?
    /// Set for the selection card: a Fix check of a few words or more also offers one rewrite.
    var offersRewrite = false
    /// What the writer does with this model's suggestions is reported (when reports are on). The welcome guide's sample turns it off.
    var reports = true
    var snapshot: SelectionSnapshot?
    var dismiss: (() -> Void)?
    var didAnalyze: (() -> Void)?
    var clearDraftUndo: (() -> Void)?
    /// Where Copy puts the corrected text; tests give it a private pasteboard so a run never touches the owner's clipboard.
    var pasteboard = NSPasteboard.general
    private var analysisTask: Task<Void, Never>?
    private var suggestionTask: Task<Void, Never>?
    private var generation = 0
    private var clipboard: ClipboardTransaction?
    var chosenEdits: [WritingEdit] { result?.edits.filter { selectedEdits.contains($0.id) } ?? [] }
    var preview: String { (try? EditPlan.apply(chosenEdits, to: source)) ?? source }
    var canApply: Bool { !busy && !provisional && !chosenEdits.isEmpty && snapshot?.checkingEnabled == true && (snapshot?.canPatch == true || snapshot?.copied == true) }
    var focusedEdit: WritingEdit? { chosenEdits.first { $0.id == focusedEditID } ?? chosenEdits.first }
    var sentenceEdits: [WritingEdit] { focusedEdit.map { SentencePreview.edits(source: source, edits: chosenEdits, focused: $0) } ?? [] }
    var fixesSentence: Bool { (snapshot?.expectedSelection.length ?? 0) == 0 && sentenceEdits.count > 1 }
    /// The offered rewrite is written, changes more than the fixes, and still belongs to this text.
    var suggestionReady: Bool { snapshot?.checkingEnabled != false && (suggestion.map { $0.source == source && SuggestedRewrite.worthOffering($0.result, fixed: result?.text ?? source) } ?? false) }
    /// Shown while it is written, and once written when it is worth offering; hidden when it came back empty or failed.
    var showsSuggestion: Bool { snapshot?.checkingEnabled != false && (mode == .fix && result != nil && suggestion.map { $0.source == source && (!$0.done || suggestionReady) } ?? false) }
    var canUseSuggestion: Bool { !busy && suggestionReady && (snapshot?.canPatch == true || snapshot?.copied == true) }
    /// The engine's warnings as the card shows them: a missing model reads as "Smart grammar is downloading" (or how to get it).
    static func statusText(_ warnings: [String]?) -> String? {
        let shown = ModelCenter.app.explain(warnings) ?? []
        return shown.isEmpty ? nil : shown.joined(separator: " ")
    }
    func navigate(_ direction: Int) {
        let edits = chosenEdits
        guard !edits.isEmpty else { return }
        let index = edits.firstIndex { $0.id == focusedEdit?.id } ?? 0
        focusedEditID = edits[(index + direction + edits.count) % edits.count].id
    }
    func warm() {
        // The engine tokenizes on its own; this tells it which words macOS already accepts, from the same pass the name gate uses.
        Task { for engine in [WritingEngine.typing, WritingEngine.shared] { await engine.setKnownWords { await SystemLexicon.shared.scan($0).accepted } } }
        Task.detached(priority: .utility) { _ = await SystemLexicon.shared.names(in: "warm up the spelling server") } // the first lookup after launch can take 0.4 s
        Task { do { _ = try await WritingEngine.typing.rewrite(EngineRequest(text: "A clear message.", deep: false)); engineReady = true }
            catch { self.error = error.localizedDescription } }
    }
    func select(_ snapshot: SelectionSnapshot) {
        guard snapshot.checkingEnabled else { clearSession(); return }
        selectionHint = false; self.snapshot = snapshot; source = snapshot.text; sourceApp = snapshot.app.localizedName ?? "Your editor"
        inspector = snapshot.metadata(); mode = Preferences.shared.defaultMode; status = nil; analyze()
    }
    func select(_ snapshot: SelectionSnapshot, result: RewriteResult, focused: WritingEdit?) {
        guard snapshot.checkingEnabled else { clearSession(); return }
        analysisTask?.cancel(); suggestionTask?.cancel(); suggestion = nil; generation += 1
        selectionHint = false; self.snapshot = snapshot; source = snapshot.text; sourceApp = snapshot.app.localizedName ?? "Your editor"
        inspector = snapshot.metadata(); mode = .fix; self.result = result
        selectedEdits = Set(result.edits.map(\.id)); focusedEditID = focused?.id
        provisional = false; busy = false; engineReady = true; error = nil; status = nil
        status = Self.statusText(result.warnings)
    }
    func playground(_ text: String, debounce: Bool = false) {
        let old = source
        snapshot = nil; source = text; sourceApp = "Playground"; status = nil
        if debounce, text != old { carryOver(from: old) }
        analyze(debounce: debounce)
    }
    /// Typing keeps the marks that the keystroke did not touch, shifted to where the text now is, so nothing flashes while the next check runs.
    private func carryOver(from old: String) {
        guard let result else { return }
        let change = EditRemap.Change(from: old, to: source)
        var moved: [WritingEdit] = [], ids: [String: String] = [:]
        for edit in result.edits { if let shifted = change.shift(edit) { moved.append(shifted); ids[edit.id] = shifted.id } }
        selectedEdits = Set(selectedEdits.compactMap { ids[$0] }); focusedEditID = focusedEditID.flatMap { ids[$0] }
        self.result = result.replacingEdits(moved); provisional = true
    }
    /// The edits to draw over `text`, which may be one keystroke ahead of the model.
    func marks(for text: String) -> [WritingEdit] {
        guard text != source else { return chosenEdits }
        let change = EditRemap.Change(from: source, to: text)
        return chosenEdits.compactMap { change.shift($0) }
    }
    func analyze(debounce: Bool = false) {
        do { try snapshot?.validateCheckingEligibility() } catch { clearSession(); self.error = error.localizedDescription; return }
        analysisTask?.cancel(); suggestionTask?.cancel(); suggestion = nil; generation += 1
        let current = generation; let original = source; let checkingSnapshot = snapshot
        error = nil; status = nil
        // An explicit check clears the old answer and shows Checking at once; typing keeps its marks and only shows Checking if the wait is long.
        if !debounce { result = nil; selectedEdits = []; provisional = false; busy = true }
        // Typing always takes the fast grammar path. Tone and passage review are explicit.
        let requestMode: RewriteMode = debounce ? .fix : mode
        let (dialect, fullText, protected) = (Preferences.shared.dialect, snapshot?.fullText ?? original, snapshot?.protectedRanges() ?? [])
        let capitalize = Preferences.shared.capitalizeNames(for: snapshot?.app.bundleIdentifier)
        // A tone rewrite starts with the same correction pass as Fix, so Smart grammar applies to it too; a chat app's Friendly rewrite may end with an emoji.
        let (gec, casual) = (Preferences.shared.smartGrammar, SuggestedRewrite.isChat(snapshot?.app.bundleIdentifier))
        let (starts, ends, deep) = (snapshot?.startsSentence ?? true, snapshot?.endsSentence ?? true, !debounce && (mode != .fix || Preferences.shared.contextRefinement))
        analysisTask = Task { @MainActor in
            var slow: Task<Void, Never>?
            defer { slow?.cancel() }
            do {
                if debounce { try await Task.sleep(for: .milliseconds(Int(Preferences.shared.boundedCheckingDelay))) }
                try Task.checkCancellation(); try checkingSnapshot?.validateCheckingEligibility()
                if debounce { slow = Task { @MainActor in try? await Task.sleep(for: .milliseconds(400)); if !Task.isCancelled, current == generation { busy = true } } }
                let request = EngineRequest(text: original, mode: requestMode, dictionary: KnownNames.dictionary(), names: await KnownNames.names(for: fullText, request: original), capitalizeNames: capitalize,
                                            dialect: dialect, protectedRanges: protected, sentenceStart: starts, sentenceEnd: ends, deep: deep, gec: gec, casual: casual)
                try Task.checkCancellation(); try checkingSnapshot?.validateCheckingEligibility()
                let engine = request.deep || request.mode != .fix ? WritingEngine.shared : WritingEngine.typing
                let result = KnownNames.screened(try await engine.rewrite(request), from: original)
                guard !Task.isCancelled, current == generation, source == original else { return }
                try checkingSnapshot?.validateCheckingEligibility()
                self.result = result; selectedEdits = Set(result.edits.map(\.id)); provisional = false; busy = false; engineReady = true
                self.status = Self.statusText(result.warnings)
                if !debounce, requestMode == .fix, offersRewrite, SuggestedRewrite.offered(for: original) { suggest(original, generation: current) }
                didAnalyze?()
            } catch {
                guard !Task.isCancelled, current == generation else { return }
                self.error = error.localizedDescription; result = nil; selectedEdits = []; provisional = false; busy = false
            }
        }
    }
    /// Writes the offered rewrite of `original` in the background, after the Fix result is already on the card; a new check or tone cancels it.
    private func suggest(_ original: String, generation current: Int) {
        guard snapshot?.checkingEnabled != false else { return }
        let checkingSnapshot = snapshot
        let bundle = snapshot?.app.bundleIdentifier, tone = SuggestedRewrite.tone(for: bundle, text: original)
        suggestion = SuggestedVersion(tone: tone, source: original)
        let (dialect, fullText, protected) = (Preferences.shared.dialect, snapshot?.fullText ?? original, snapshot?.protectedRanges() ?? [])
        let (capitalize, gec, casual) = (Preferences.shared.capitalizeNames(for: bundle), Preferences.shared.smartGrammar, SuggestedRewrite.isChat(bundle))
        let (starts, ends) = (snapshot?.startsSentence ?? true, snapshot?.endsSentence ?? true)
        suggestionTask = Task { @MainActor in
            var written: RewriteResult?
            do {
                try checkingSnapshot?.validateCheckingEligibility()
                let request = EngineRequest(text: original, mode: tone, dictionary: KnownNames.dictionary(), names: await KnownNames.names(for: fullText, request: original), capitalizeNames: capitalize,
                                            dialect: dialect, protectedRanges: protected, sentenceStart: starts, sentenceEnd: ends, deep: true, gec: gec, casual: casual)
                try Task.checkCancellation(); try checkingSnapshot?.validateCheckingEligibility()
                written = KnownNames.screened(try await WritingEngine.shared.rewrite(request), from: original)
            } catch {}
            guard !Task.isCancelled, current == generation, source == original, suggestion?.source == original, checkingSnapshot?.checkingEnabled != false else { return }
            suggestion?.result = written; suggestion?.done = true
        }
    }
    /// Puts the offered rewrite on the card as that tone's result and applies all of it.
    func useSuggestion() {
        guard suggestionReady, !busy, let offered = suggestion, let written = offered.result else { return }
        show(written, as: offered.tone)
        if canApply { apply() }
    }
    /// A tone's finished result shown without a new check.
    private func show(_ written: RewriteResult, as tone: RewriteMode) {
        guard snapshot?.checkingEnabled != false else { return }
        analysisTask?.cancel(); suggestionTask?.cancel(); generation += 1
        mode = tone; result = written; suggestion = nil
        selectedEdits = Set(written.edits.map(\.id)); focusedEditID = written.edits.first?.id
        provisional = false; busy = false; error = nil
        status = Self.statusText(written.warnings)
    }
    /// Mode pickers bind here; a key-path binding avoids a Swift 6.3 IRGen crash in closure-built Bindings.
    var modeChoice: RewriteMode { get { mode } set { changeMode(newValue) } }
    /// Picking the tone the card already wrote shows that rewrite at once.
    func changeMode(_ mode: RewriteMode) {
        guard self.mode != mode else { return }
        if suggestionReady, let offered = suggestion, offered.tone == mode, let written = offered.result { show(written, as: mode); return }
        self.mode = mode; analyze()
    }
    func toggle(_ edit: WritingEdit) {
        let ids = Set(EditPlan.related(to: edit, in: result?.edits ?? [edit]).map(\.id))
        if selectedEdits.contains(edit.id) { selectedEdits.subtract(ids) } else { selectedEdits.formUnion(ids) }
    }
    /// The app the text belongs to: the editor's, or Parzr's own for its writing space.
    private var reportApp: String? { snapshot?.app.bundleIdentifier ?? Bundle.main.bundleIdentifier }
    /// Reports what the writer did with `edits` of the current text. `text` overrides the source (the writing space's draft can be a keystroke ahead).
    func report(_ edits: [WritingEdit], _ action: ReportAction, text: String? = nil) {
        guard reports else { return }
        Reports.record(edits, source: text ?? source, action: action, mode: mode, app: reportApp)
    }
    var canReport: Bool { reports && Reports.available }
    func copy() { guard !busy, !provisional, result != nil, snapshot?.checkingEnabled != false else { return }; pasteboard.clearContents(); pasteboard.setString(preview, forType: .string); status = "Copied to clipboard" }
    func applyCurrent() { if let edit = focusedEdit { apply(edits: EditPlan.related(to: edit, in: chosenEdits)) } }
    func applySentence() { apply(edits: sentenceEdits) }
    func applyBest() { if focusedEdit == nil, suggestionReady { useSuggestion() } else if fixesSentence { applySentence() } else { applyCurrent() } }
    func apply() { apply(edits: chosenEdits) }
    private func apply(edits: [WritingEdit]) {
        guard canApply, let snapshot else { return }
        guard !edits.isEmpty, edits.allSatisfy({ chosenEdits.contains($0) }) else { return }
        do { try snapshot.validate() } catch { self.error = error.localizedDescription; return }
        busy = true
        if !snapshot.own { SelfTestTarget.bringForward(snapshot.app) }   // Parzr's own writing space is already in front
        if snapshot.copied { applyCopied(snapshot, edits); return }
        Task { @MainActor in
            do {
                try await Task.sleep(for: .milliseconds(80))
                try await snapshot.apply(edits)
                self.snapshot = nil; busy = false; dismiss?()
            } catch { self.error = error.localizedDescription; busy = false }
        }
    }
    /// Canvas editors (Google Docs): re-copy to prove the selection is unchanged, then paste the whole replacement over it.
    /// Independent of `clipboardFallback`: the user explicitly ran a copy-based check.
    private func applyCopied(_ snapshot: SelectionSnapshot, _ edits: [WritingEdit]) {
        Task { @MainActor in
            let transaction = ClipboardTransaction()
            do {
                let replacement = try EditPlan.apply(edits, to: source)
                try await Task.sleep(for: .milliseconds(80))
                guard let again = try await ClipboardTransaction.copySelection(from: snapshot.app.processIdentifier), SelectionSnapshot.sameCopiedText(again, snapshot.text) else {
                    throw ParzrError.message("Your selection changed. Select the text again.")
                }
                try snapshot.validate()
                try transaction.stage(replacement); self.clipboard = transaction
                try ClipboardTransaction.paste(to: snapshot.app.processIdentifier)
                FixLearning.record(edits, in: snapshot)
                try await Task.sleep(for: .milliseconds(800)); transaction.restore(); self.clipboard = nil
                self.snapshot = nil; busy = false; dismiss?()
            } catch { transaction.restore(); self.clipboard = nil; self.error = error.localizedDescription; busy = false }
        }
    }
    func pasteFallback() {
        guard Preferences.shared.clipboardFallback, !chosenEdits.isEmpty, !busy, let snapshot else { return }
        let replacement = preview, edits = chosenEdits
        let attributed = snapshot.richText.flatMap { try? EditPlan.apply(chosenEdits, to: $0) }
        do { try snapshot.validate() } catch { self.error = error.localizedDescription; return }
        busy = true; SelfTestTarget.bringForward(snapshot.app)
        Task { @MainActor in
            let transaction = ClipboardTransaction()
            do {
                try await Task.sleep(for: .milliseconds(100)); try snapshot.validate()
                guard AX.select(snapshot.element, snapshot.selection) || snapshot.selection == snapshot.expectedSelection else { throw ParzrError.message("The editor cannot select this range safely.") }
                try transaction.stage(replacement, attributed: attributed); self.clipboard = transaction
                try ClipboardTransaction.paste(to: snapshot.app.processIdentifier)
                FixLearning.record(edits, in: snapshot)
                try await Task.sleep(for: .milliseconds(800)); transaction.restore(); self.clipboard = nil
                busy = false; self.snapshot = nil; dismiss?()
            } catch { transaction.restore(); self.clipboard = nil; self.error = error.localizedDescription; busy = false }
        }
    }
    func clearSession() { analysisTask?.cancel(); suggestionTask?.cancel(); suggestion = nil; generation += 1; result = nil; source = ""; snapshot = nil; error = nil; selectionHint = false; status = nil; selectedEdits = []; focusedEditID = nil; provisional = false; busy = false; clearDraftUndo?(); inspector = "Session cleared. No writing history is stored." }
}

/// The rewrite a Fix check offers: its tone, the text it was written for, and the result once written (nil when it failed).
struct SuggestedVersion {
    let tone: RewriteMode
    let source: String
    var result: RewriteResult?
    var done = false
}

/// Carries edit offsets across a text change (UTF-16, the engine's unit) so marks can stay put while a new check runs.
enum EditRemap {
    struct Change {
        let start: Int, oldEnd: Int, delta: Int, unchanged: Bool
        /// The span of `old` that became `new`, found from the common prefix and suffix and never cutting a surrogate pair.
        init(from old: String, to new: String) {
            let (a, b) = (Array(old.utf16), Array(new.utf16)), shared = min(a.count, b.count)
            var prefix = 0, suffix = 0
            while prefix < shared, a[prefix] == b[prefix] { prefix += 1 }
            if prefix > 0, UTF16.isLeadSurrogate(a[prefix - 1]) { prefix -= 1 }
            while suffix < shared - prefix, a[a.count - 1 - suffix] == b[b.count - 1 - suffix] { suffix += 1 }
            if suffix > 0, UTF16.isTrailSurrogate(a[a.count - suffix]) { suffix -= 1 }
            (start, oldEnd, delta, unchanged) = (prefix, a.count - suffix, b.count - a.count, old == new)
        }
        /// Kept as is when wholly before the change, moved by the length change when wholly after, dropped when it overlaps or touches it.
        func shift(_ edit: WritingEdit) -> WritingEdit? {
            if unchanged || edit.end_utf16 < start { return edit }
            guard edit.start_utf16 > oldEnd else { return nil }
            return WritingEdit(start: edit.start_utf16 + delta, end: edit.end_utf16 + delta, replacement: edit.replacement, original: edit.original, category: edit.category, ruleID: edit.rule_id, explanation: edit.explanation, confidence: edit.confidence, groupID: edit.group_id)
        }
    }
}
