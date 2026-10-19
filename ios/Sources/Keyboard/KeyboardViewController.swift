import UIKit
import os
import ParzrKit

/// `log stream --predicate 'subsystem == "app.parzr.ios"'` shows what the keyboard found.
let keyboardLog = Logger(subsystem: "app.parzr.ios", category: "keyboard")

/// Parzr's keyboard: a plain QWERTY layout with a suggestion bar that checks the sentence being
/// typed and applies fixes through `textDocumentProxy`.
///
/// Memory: the keyboard loads the Rust engine only when `MemoryBudget` says it fits (it does not
/// on current iPhones; see ios/README.md); otherwise the bar shows the system spell checker's
/// corrections. Tone rewrites run here only when the engine (needed for the meaning guard) and
/// Apple Intelligence are both usable; otherwise they are handed to the app through the App Group.
final class KeyboardViewController: UIInputViewController {
    private let bar = SuggestionBar()
    private let keys = KeysView()
    private let checker = KeyboardChecker()
    private let store = SharedStore.shared
    private var settings = KeyboardSettings()
    /// The rewrite the bar offers, and the text it replaces.
    private var offer: (source: String, rewritten: String, handoff: UUID?)?
    private var rewriting: Task<Void, Never>?

    override func viewDidLoad() {
        super.viewDidLoad()
        settings = store.settings
        let stack = UIStackView(arrangedSubviews: [bar, keys])
        stack.axis = .vertical
        stack.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(stack)
        NSLayoutConstraint.activate([
            stack.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            stack.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            stack.topAnchor.constraint(equalTo: view.topAnchor),
            stack.bottomAnchor.constraint(equalTo: view.bottomAnchor),
            bar.heightAnchor.constraint(equalToConstant: 44),
            keys.heightAnchor.constraint(equalToConstant: 216),
        ])
        keys.onText = { [weak self] text in self?.type(text) }
        keys.onDelete = { [weak self] in self?.textDocumentProxy.deleteBackward(); self?.changed() }
        keys.onReturn = { [weak self] in self?.type("\n") }
        keys.globe.addTarget(self, action: #selector(handleInputModeList(from:with:)), for: .allTouchEvents)
        bar.onSuggestion = { [weak self] suggestion in self?.apply(self?.checker.plan(suggestion, before: self?.textDocumentProxy.documentContextBeforeInput)) }
        bar.onFixAll = { [weak self] in self?.apply(self?.checker.planAll(before: self?.textDocumentProxy.documentContextBeforeInput)) }
        bar.onTone = { [weak self] mode in self?.rewrite(mode) }
        bar.onClose = { [weak self] in self?.dismissOffer() }
        checker.onChange = { [weak self] in self?.refreshBar() }
    }

    override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
        settings = store.settings
        offerFinishedHandoff()
        changed()
    }

    override func viewDidAppear(_ animated: Bool) {
        super.viewDidAppear(animated)
        report(appleModel: nil)
        probeAppleModel()
    }

    /// Whether Apple Intelligence answers inside this keyboard: one short on-device call at most
    /// once a day (with or without Full Access; nothing leaves the device), logged, and recorded
    /// for the app's setup screen when Full Access allows (ios/README.md).
    private static var probed = false
    private func probeAppleModel() {
        let status = AppleModelStatus.current
        keyboardLog.notice("keyboard appeared: fullAccess=\(self.hasFullAccess, privacy: .public) checker=\(self.checker.checker.rawValue, privacy: .public) headroomMB=\(MemoryBudget.headroomMB ?? -1, privacy: .public) appleModel=\(status.message, privacy: .public)")
        let key = "appleModelProbed"
        let last = UserDefaults.standard.object(forKey: key) as? Date ?? .distantPast
        guard !Self.probed, status.isAvailable, Date().timeIntervalSince(last) > 86_400 else { return }
        Self.probed = true
        UserDefaults.standard.set(Date(), forKey: key)
        Task { [weak self] in
            let result = await ToneRewriter.probe()
            keyboardLog.notice("apple model probe in keyboard: \(result, privacy: .public)")
            self?.report(appleModel: result)
        }
    }

    override func viewWillLayoutSubviews() {
        keys.showsGlobe = needsInputModeSwitchKey
        super.viewWillLayoutSubviews()
    }

    override func textDidChange(_ textInput: UITextInput?) {
        super.textDidChange(textInput)
        changed()
    }

    // MARK: Typing

    private func type(_ text: String) {
        textDocumentProxy.insertText(text)
        if text == " " || text == "\n" { keys.returnToLetters() }
        changed()
    }

    private func changed() {
        let before = textDocumentProxy.documentContextBeforeInput
        // Capitalize the next letter at the start of a sentence.
        if keys.shift != .locked {
            let text = before ?? ""
            let starts = text.isEmpty || text.hasSuffix("\n") || [". ", "! ", "? "].contains { text.hasSuffix($0) }
            keys.shift = starts ? .once : .off
        }
        if let source = offer?.source, before?.hasSuffix(source) != true { dismissOffer() }
        checker.schedule(before: before, settings: settings)
    }

    private func refreshBar() {
        guard offer == nil, rewriting == nil else { return }
        bar.show(suggestions: checker.suggestions, fixAll: checker.edits.count > 1)
    }

    private func apply(_ plan: ProxyEdit?) {
        guard let plan else { checker.reset(); return }
        for _ in 0..<plan.deleteCount { textDocumentProxy.deleteBackward() }
        textDocumentProxy.insertText(plan.insert)
        checker.reset()
        changed()
    }

    // MARK: Tone rewrites

    private func rewrite(_ mode: RewriteMode) {
        let before = textDocumentProxy.documentContextBeforeInput ?? ""
        guard let context = SentenceContext.current(before: before) else { bar.show(message: "Type a sentence to rewrite."); return }
        let source = context.text + context.pending
        let canRunHere = settings.rewriteInKeyboard && checker.checker == .engine && AppleModelStatus.current.isAvailable
        guard canRunHere else { handOff(source, mode: mode); return }
        bar.show(message: SuggestedRewrite.working(mode))
        rewriting = Task { [weak self] in
            let outcome = await ToneRewriter().rewrite(source, mode: mode, settings: self?.settings ?? KeyboardSettings())
            guard let self else { return }
            self.rewriting = nil
            switch outcome {
            case .rewritten(let text):
                self.report(appleModel: "works")
                self.offer = (source, text, nil)
                self.bar.onAction = { [weak self] in self?.useOffer() }
                self.bar.show(message: text, action: SuggestedRewrite.action(mode))
            case .unchanged(let message):
                self.report(appleModel: "works")
                self.bar.show(message: message)
            case .failed(let message):
                self.report(appleModel: message)
                // Apple Intelligence did not run here: let the app try.
                if self.hasFullAccess { self.handOff(source, mode: mode) } else { self.bar.show(message: message) }
            }
        }
    }

    private func handOff(_ source: String, mode: RewriteMode) {
        guard hasFullAccess else {
            bar.show(message: "Allow Full Access for Parzr in Settings to write rewrites in the Parzr app.")
            return
        }
        store.post(source: source, mode: mode)
        bar.show(message: "Open Parzr to write a \(mode.title) version. It will be here when you come back.")
    }

    private func offerFinishedHandoff() {
        guard let handoff = store.finished() else { return }
        let before = textDocumentProxy.documentContextBeforeInput ?? ""
        guard before.hasSuffix(handoff.source) else { return }
        if let result = handoff.result {
            offer = (handoff.source, result, handoff.id)
            bar.onAction = { [weak self] in self?.useOffer() }
            bar.show(message: result, action: SuggestedRewrite.action(handoff.mode))
        } else {
            store.clearHandoff()
            bar.show(message: handoff.note ?? "No \(handoff.mode.title) version this time.")
        }
    }

    private func useOffer() {
        guard let offer else { return }
        let plan = ProxyEdit.replacing(offer.source, with: offer.rewritten, before: textDocumentProxy.documentContextBeforeInput ?? "")
        if offer.handoff != nil { store.clearHandoff() }
        self.offer = nil
        bar.onAction = nil
        apply(plan)
    }

    private func dismissOffer() {
        if offer?.handoff != nil { store.clearHandoff() }
        offer = nil
        bar.onAction = nil
        refreshBar()
    }

    // MARK: Report for the app's setup screen

    private func report(appleModel: String?) {
        guard hasFullAccess else { return }
        let previous = store.keyboardReport
        let model = appleModel ?? previous?.appleModel ?? (AppleModelStatus.current.isAvailable ? "available, untested" : AppleModelStatus.current.message)
        store.keyboardReport = .init(fullAccess: true, checker: checker.checker.rawValue, memoryHeadroomMB: MemoryBudget.headroomMB, appleModel: model)
    }
}
