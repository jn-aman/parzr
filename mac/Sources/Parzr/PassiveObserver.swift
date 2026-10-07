import AppKit
import Combine
import ParzrCore

@MainActor
final class PassiveObserver {
    var onSuggestion: ((SelectionSnapshot, RewriteResult) -> Void)?
    var onDismiss: (() -> Void)?
    private var observer: AXObserver?
    private var observed: [(AXUIElement, String)] = []
    private var work: Task<Void, Never>?
    private var pacer = CheckPacer()
    /// A check is waiting out its delay; false once it has started reading the editor.
    private var pending = false
    private var activationToken: NSObjectProtocol?
    private var inputMonitor: Any?
    private var clickMonitor: Any?
    private var attachedPID: pid_t?
    private var subscriptions: Set<AnyCancellable> = []
    private var stopped = false
    private var focusRetry: Task<Void, Never>?
    private var firefoxKeystrokes = 0, docsKeystrokes = 0
    /// Counts monitor (re)installs; a grant after launch must install fresh ones, since monitors made before the grant never deliver.
    private(set) var monitorInstalls = 0
    private let excluded = ["com.apple.Terminal", "com.googlecode.iterm2", "dev.zed.Zed", "com.jetbrains"]
    /// VS Code and Cursor are checked only after the user opts in (Apps settings).
    private func isExcluded(_ bundle: String) -> Bool {
        excluded.contains { bundle.hasPrefix($0) } || (Compat.isVSCode(bundle) && !Preferences.shared.checkVSCode)
    }
    func installMonitors() {
        if let inputMonitor { NSEvent.removeMonitor(inputMonitor) }
        if let clickMonitor { NSEvent.removeMonitor(clickMonitor) }
        // Some editors omit AX value notifications after paste. Native input events
        // schedule the same bounded check; event text is never stored, and only used to tell whether the key ended a word.
        inputMonitor = NSEvent.addGlobalMonitorForEvents(matching: .keyDown) { [weak self] event in
            let wordEnd = CheckPacer.endsWord(event.characters)
            MainActor.assumeIsolated { self?.noteKeystroke(); self?.keyPressed(wordEnd: wordEnd) }
        }
        clickMonitor = NSEvent.addGlobalMonitorForEvents(matching: .leftMouseUp) { [weak self] _ in
            MainActor.assumeIsolated { self?.inputChanged() }
        }
        monitorInstalls += 1
    }
    init() {
        installMonitors()
        activationToken = NSWorkspace.shared.notificationCenter.addObserver(forName: NSWorkspace.didActivateApplicationNotification, object: nil, queue: .main) { [weak self] _ in
            MainActor.assumeIsolated { if SelfTestTarget.app == nil { self?.attach() } }
        }
        Preferences.shared.$passive.combineLatest(Preferences.shared.$paused, Preferences.shared.$disabledApps)
            .sink { [weak self] _ in Task { @MainActor in self?.attach() } }.store(in: &subscriptions)
        Preferences.shared.$permissionGranted.removeDuplicates().sink { [weak self] granted in
            if granted { MainActor.assumeIsolated { self?.installMonitors() } }
            Task { @MainActor in self?.attach() }
        }.store(in: &subscriptions)
        Preferences.shared.$checkVSCode.dropFirst().removeDuplicates().sink { [weak self] _ in Task { @MainActor in self?.attach() } }.store(in: &subscriptions)
    }
    func attach() {
        guard !stopped else { return }
        work?.cancel(); pending = false; focusRetry?.cancel(); firefoxKeystrokes = 0; docsKeystrokes = 0; AX.forgetFocus(); onDismiss?()
        if let observer {
            for (element, notification) in observed { AXObserverRemoveNotification(observer, element, notification as CFString) }
            CFRunLoopRemoveSource(CFRunLoopGetMain(), AXObserverGetRunLoopSource(observer), .commonModes)
        }
        observer = nil; observed = []; attachedPID = nil
        guard Preferences.shared.passive, !Preferences.shared.paused, AXIsProcessTrusted(),
              let app = SelfTestTarget.watched, let bundle = app.bundleIdentifier,
              bundle != Bundle.main.bundleIdentifier, Preferences.shared.enabled(for: bundle),
              !isExcluded(bundle) else { return }
        AX.prepare(app, force: true)
        var created: AXObserver?
        let result = AXObserverCreate(app.processIdentifier, { _, _, notification, context in
            guard let context else { return }
            MainActor.assumeIsolated {
                let owner = Unmanaged<PassiveObserver>.fromOpaque(context).takeUnretainedValue()
                if notification as String == kAXFocusedUIElementChangedNotification {
                    AX.forgetFocus()
                    if let app = SelfTestTarget.watched { AX.prepare(app, force: true) }
                    owner.attachFocused()
                }
                owner.changed(value: notification as String == kAXValueChangedNotification)
            }
        }, &created)
        guard result == .success, let created else { return }
        observer = created
        attachedPID = app.processIdentifier
        let appElement = AXUIElementCreateApplication(app.processIdentifier)
        add(appElement, kAXFocusedUIElementChangedNotification)
        CFRunLoopAddSource(CFRunLoopGetMain(), AXObserverGetRunLoopSource(created), .commonModes)
        attachFocused()
        changed()
    }
    private func inputChanged() {
        guard !stopped, let attachedPID, SelfTestTarget.watched?.processIdentifier == attachedPID else { return }
        changed()
    }
    /// A key went down in the attached editor. The text has not changed yet, so nothing is dismissed.
    func keyPressed(wordEnd: Bool) {
        guard !stopped, let attachedPID, SelfTestTarget.watched?.processIdentifier == attachedPID else { return }
        pacer.ceiling = Preferences.shared.boundedCheckingDelay
        schedule(pacer.key(at: ProcessInfo.processInfo.systemUptime, wordEnd: wordEnd))
    }
    private func add(_ element: AXUIElement, _ notification: String) {
        guard let observer else { return }
        if AXObserverAddNotification(observer, element, notification as CFString, Unmanaged.passUnretained(self).toOpaque()) == .success { observed.append((element, notification)) }
    }
    /// Firefox stays silent when the user blocked accessibility services: after several keystrokes with no text field resolved, offer the hint.
    private func noteKeystroke() {
        noteDocsKeystroke()
        guard !stopped, let app = SelfTestTarget.watched, Compat.isFirefox(app.bundleIdentifier), !Preferences.shared.firefoxHintDismissed, !Preferences.shared.firefoxHint else { return }
        firefoxKeystrokes += 1
        guard firefoxKeystrokes >= Compat.firefoxHintKeystrokes else { return }
        firefoxKeystrokes = 0
        let role = AX.focused(app).flatMap { AX.string($0, kAXRoleAttribute) }
        if Compat.firefoxHintNeeded(bundle: app.bundleIdentifier, focusedRole: role, hasText: AX.focusedText(app) != nil, keystrokes: Compat.firefoxHintKeystrokes, dismissed: Preferences.shared.firefoxHintDismissed) { Preferences.shared.firefoxHint = true }
    }
    /// Google Docs shows nothing to read until its "braille support" is on: after several keystrokes with no text, offer the one-time setup hint.
    private func noteDocsKeystroke() {
        let prefs = Preferences.shared
        guard !stopped, !prefs.docsHintDismissed, !prefs.docsHint, let app = SelfTestTarget.watched, Compat.isChromium(app.bundleIdentifier) else { return }
        docsKeystrokes += 1
        guard docsKeystrokes >= Compat.docsHintKeystrokes else { return }
        docsKeystrokes = 0
        guard let focused = AX.focusedText(app) else { return }
        if Compat.docsHintNeeded(isDocs: AX.isDocsText(focused), value: AX.string(focused, kAXValueAttribute), keystrokes: Compat.docsHintKeystrokes, dismissed: prefs.docsHintDismissed) { prefs.docsHint = true }
    }
    private func attachFocused(retry: Bool = true) {
        // Focus changes detach old text observers so inactive fields are never analyzed.
        if let observer {
            for (element, notification) in observed where notification != kAXFocusedUIElementChangedNotification {
                AXObserverRemoveNotification(observer, element, notification as CFString)
            }
        }
        observed.removeAll { $0.1 != kAXFocusedUIElementChangedNotification }
        guard let app = SelfTestTarget.watched else { return }
        guard let focused = AX.focusedText(app), !AX.isSecure(focused) else {
            // The first queries after activation can see only the menu bar while Firefox or VS Code switch accessibility on; look once more.
            if retry, Compat.needsFocusRetry(bundle: app.bundleIdentifier, vscodeEnabled: Preferences.shared.checkVSCode) {
                focusRetry?.cancel()
                focusRetry = Task { @MainActor [weak self] in
                    try? await Task.sleep(for: .milliseconds(1500))
                    guard !Task.isCancelled, let self, !self.stopped, SelfTestTarget.watched?.processIdentifier == self.attachedPID else { return }
                    self.attachFocused(retry: false); self.changed()
                }
            }
            return
        }
        add(focused, kAXValueChangedNotification); add(focused, kAXSelectedTextChangedNotification)
        if let window = AX.get(focused, kAXWindowAttribute), CFGetTypeID(window) == AXUIElementGetTypeID() {
            add(window as! AXUIElement, kAXMovedNotification); add(window as! AXUIElement, kAXResizedNotification)
        }
    }
    /// An editor trigger (AX notification, click, focus). `value`: the text itself changed.
    private func changed(value: Bool = false) {
        pacer.ceiling = Preferences.shared.boundedCheckingDelay
        let plan = pacer.changed(at: ProcessInfo.processInfo.systemUptime)
        if value || plan != .keep { onDismiss?() }
        schedule(plan)
    }
    private func schedule(_ plan: CheckPacer.Plan) {
        guard Preferences.shared.passive, !Preferences.shared.paused else { work?.cancel(); pending = false; return }
        let delay: Double
        switch plan {
        case .restart(let ms): delay = ms
        // The check that is already waiting covers it; one that has started may have read a stale caret, so run again.
        case .keep: if pending { return }; delay = pacer.quiet
        }
        work?.cancel(); pending = true
        work = Task { @MainActor [weak self] in
            do {
                if delay > 0 { try await Task.sleep(for: .milliseconds(Int(delay.rounded()))) }
                try Task.checkCancellation()
                self?.pending = false
                self?.onDismiss?()
                let snapshot = try SelectionSnapshot.capture(passive: true)
                FixLearning.observe(snapshot)
                let request = EngineRequest(text: snapshot.text, dictionary: KnownNames.dictionary(), names: await KnownNames.names(for: snapshot.fullText ?? snapshot.text, request: snapshot.text), capitalizeNames: Preferences.shared.capitalizeNames(for: snapshot.app.bundleIdentifier),
                                            dialect: Preferences.shared.dialect, protectedRanges: snapshot.protectedRanges(), sentenceStart: snapshot.startsSentence, sentenceEnd: snapshot.endsSentence, gec: Preferences.shared.smartGrammar)
                // Automatic checks (typing and plain selection) never wait for the GPU model. With Smart grammar on,
                // the engine scores short-word swaps with it only when it is already loaded and free, within a small
                // budget; a cold model starts loading in the background and stays loaded while the person keeps typing.
                // Rewrites run only for explicit checks and tone changes.
                let engine = WritingEngine.typing
                let result = KnownNames.dropMacLearned(try await engine.rewrite(request), from: request.text)
                try Task.checkCancellation(); try snapshot.validate()
                RepetitionLearning.observe(result.edits, in: snapshot)
                guard !result.edits.isEmpty else { return }
                self?.onSuggestion?(snapshot, result)
            } catch { /* Passive failures are quiet and never log writing text. */ }
        }
    }
    func suspend() { work?.cancel(); pending = false; onDismiss?() }
    func stop() {
        stopped = true; suspend(); focusRetry?.cancel()
        if let observer {
            for (element, notification) in observed { AXObserverRemoveNotification(observer, element, notification as CFString) }
            CFRunLoopRemoveSource(CFRunLoopGetMain(), AXObserverGetRunLoopSource(observer), .commonModes)
        }
        observer = nil; observed = []
        if let activationToken { NSWorkspace.shared.notificationCenter.removeObserver(activationToken); self.activationToken = nil }
        if let inputMonitor { NSEvent.removeMonitor(inputMonitor); self.inputMonitor = nil }
        if let clickMonitor { NSEvent.removeMonitor(clickMonitor); self.clickMonitor = nil }
        subscriptions.removeAll()
    }
}
