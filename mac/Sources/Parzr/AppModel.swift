import AppKit
import SwiftUI
import ParzrCore

@MainActor
final class AppModel: ObservableObject {
    @Published var studioRoute: StudioRoute = .playground
    @Published var mode: RewriteMode = .fix
    @Published var result: RewriteResult?
    @Published var busy = false
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
    var snapshot: SelectionSnapshot?
    var dismiss: (() -> Void)?
    var showOnboarding: (() -> Void)?
    var didAnalyze: (() -> Void)?
    var clearDraftUndo: (() -> Void)?
    private var analysisTask: Task<Void, Never>?
    private var generation = 0
    private var clipboard: ClipboardTransaction?
    var chosenEdits: [WritingEdit] { result?.edits.filter { selectedEdits.contains($0.id) } ?? [] }
    var preview: String { (try? EditPlan.apply(chosenEdits, to: source)) ?? source }
    var canApply: Bool { !busy && !chosenEdits.isEmpty && (snapshot?.canPatch == true || snapshot?.copied == true) }
    var focusedEdit: WritingEdit? { chosenEdits.first { $0.id == focusedEditID } ?? chosenEdits.first }
    var sentenceEdits: [WritingEdit] { focusedEdit.map { SentencePreview.edits(source: source, edits: chosenEdits, focused: $0) } ?? [] }
    var fixesSentence: Bool { (snapshot?.expectedSelection.length ?? 0) == 0 && sentenceEdits.count > 1 }
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
        selectionHint = false; self.snapshot = snapshot; source = snapshot.text; sourceApp = snapshot.app.localizedName ?? "Your editor"
        inspector = snapshot.metadata(); mode = Preferences.shared.defaultMode; status = nil; analyze()
    }
    func select(_ snapshot: SelectionSnapshot, result: RewriteResult, focused: WritingEdit?) {
        analysisTask?.cancel(); generation += 1
        selectionHint = false; self.snapshot = snapshot; source = snapshot.text; sourceApp = snapshot.app.localizedName ?? "Your editor"
        inspector = snapshot.metadata(); mode = .fix; self.result = result
        selectedEdits = Set(result.edits.map(\.id)); focusedEditID = focused?.id
        busy = false; engineReady = true; error = nil; status = nil
        status = result.warnings?.isEmpty == false ? result.warnings?.joined(separator: " ") : nil
    }
    func playground(_ text: String, debounce: Bool = false) { snapshot = nil; source = text; sourceApp = "Playground"; status = nil; analyze(debounce: debounce) }
    func analyze(debounce: Bool = false) {
        analysisTask?.cancel(); generation += 1
        let current = generation; let original = source
        result = nil; selectedEdits = []; error = nil; status = nil; busy = true
        // Typing always takes the fast grammar path. Tone and passage review are explicit.
        let requestMode: RewriteMode = debounce ? .fix : mode
        let (dialect, fullText, protected) = (Preferences.shared.dialect, snapshot?.fullText ?? original, snapshot?.protectedRanges() ?? [])
        let capitalize = Preferences.shared.capitalizeNames(for: snapshot?.app.bundleIdentifier)
        let gec = Preferences.shared.smartGrammar && requestMode == .fix
        let (starts, ends, deep) = (snapshot?.startsSentence ?? true, snapshot?.endsSentence ?? true, !debounce && (mode != .fix || Preferences.shared.contextRefinement))
        analysisTask = Task { @MainActor in
            do {
                if debounce { try await Task.sleep(for: .milliseconds(Int(Preferences.shared.boundedCheckingDelay))) }
                try Task.checkCancellation()
                let request = EngineRequest(text: original, mode: requestMode, dictionary: KnownNames.dictionary(), names: await KnownNames.names(for: fullText, request: original), capitalizeNames: capitalize,
                                            dialect: dialect, protectedRanges: protected, sentenceStart: starts, sentenceEnd: ends, deep: deep, gec: gec)
                try Task.checkCancellation()
                let engine = request.deep || request.mode != .fix ? WritingEngine.shared : WritingEngine.typing
                let result = KnownNames.dropMacLearned(try await engine.rewrite(request), from: original)
                guard !Task.isCancelled, current == generation, source == original else { return }
                self.result = result; selectedEdits = Set(result.edits.map(\.id)); busy = false; engineReady = true
                self.status = result.warnings?.isEmpty == false ? result.warnings?.joined(separator: " ") : nil
                didAnalyze?()
            } catch {
                guard !Task.isCancelled, current == generation else { return }
                self.error = error.localizedDescription; busy = false
            }
        }
    }
    /// Mode pickers bind here; a key-path binding avoids a Swift 6.3 IRGen crash in closure-built Bindings.
    var modeChoice: RewriteMode { get { mode } set { changeMode(newValue) } }
    func changeMode(_ mode: RewriteMode) { guard self.mode != mode else { return }; self.mode = mode; analyze() }
    func toggle(_ edit: WritingEdit) {
        let ids = Set(EditPlan.related(to: edit, in: result?.edits ?? [edit]).map(\.id))
        if selectedEdits.contains(edit.id) { selectedEdits.subtract(ids) } else { selectedEdits.formUnion(ids) }
    }
    func copy() { guard !busy, result != nil else { return }; NSPasteboard.general.clearContents(); NSPasteboard.general.setString(preview, forType: .string); status = "Copied to clipboard" }
    func applyCurrent() { if let edit = focusedEdit { apply(edits: EditPlan.related(to: edit, in: chosenEdits)) } }
    func applySentence() { apply(edits: sentenceEdits) }
    func applyBest() { if fixesSentence { applySentence() } else { applyCurrent() } }
    func apply() { apply(edits: chosenEdits) }
    private func apply(edits: [WritingEdit]) {
        guard canApply, let snapshot else { return }
        guard !edits.isEmpty, edits.allSatisfy({ chosenEdits.contains($0) }) else { return }
        do { try snapshot.validate() } catch { self.error = error.localizedDescription; return }
        busy = true
        snapshot.app.activate(options: [])
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
        busy = true; snapshot.app.activate(options: [])
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
    func clearSession() { analysisTask?.cancel(); generation += 1; result = nil; source = ""; snapshot = nil; error = nil; selectionHint = false; status = nil; selectedEdits = []; focusedEditID = nil; busy = false; clearDraftUndo?(); inspector = "Session cleared. No writing history is stored." }
}
