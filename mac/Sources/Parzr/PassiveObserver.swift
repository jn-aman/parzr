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
    private var activationToken: NSObjectProtocol?
    private var inputMonitor: Any?
    private var clickMonitor: Any?
    private var attachedPID: pid_t?
    private var subscriptions: Set<AnyCancellable> = []
    private var stopped = false
    private let excluded = ["com.apple.Terminal", "com.googlecode.iterm2", "com.microsoft.VSCode", "com.todesktop.230313mzl4w4u92", "dev.zed.Zed", "com.jetbrains"]
    init() {
        // Some editors omit AX value notifications after paste. Native input events
        // schedule the same bounded check; event text is never inspected or stored.
        inputMonitor = NSEvent.addGlobalMonitorForEvents(matching: .keyDown) { [weak self] _ in
            MainActor.assumeIsolated { self?.inputChanged() }
        }
        clickMonitor = NSEvent.addGlobalMonitorForEvents(matching: .leftMouseUp) { [weak self] _ in
            MainActor.assumeIsolated { self?.inputChanged() }
        }
        activationToken = NSWorkspace.shared.notificationCenter.addObserver(forName: NSWorkspace.didActivateApplicationNotification, object: nil, queue: .main) { [weak self] _ in
            MainActor.assumeIsolated { self?.attach() }
        }
        Preferences.shared.$passive.combineLatest(Preferences.shared.$paused, Preferences.shared.$disabledApps)
            .sink { [weak self] _ in Task { @MainActor in self?.attach() } }.store(in: &subscriptions)
        Preferences.shared.$permissionGranted.removeDuplicates().sink { [weak self] _ in Task { @MainActor in self?.attach() } }.store(in: &subscriptions)
    }
    func attach() {
        guard !stopped else { return }
        work?.cancel(); onDismiss?()
        if let observer {
            for (element, notification) in observed { AXObserverRemoveNotification(observer, element, notification as CFString) }
            CFRunLoopRemoveSource(CFRunLoopGetMain(), AXObserverGetRunLoopSource(observer), .commonModes)
        }
        observer = nil; observed = []; attachedPID = nil
        guard Preferences.shared.passive, !Preferences.shared.paused, AXIsProcessTrusted(),
              let app = NSWorkspace.shared.frontmostApplication, let bundle = app.bundleIdentifier,
              bundle != Bundle.main.bundleIdentifier, Preferences.shared.enabled(for: bundle),
              !excluded.contains(where: { bundle.hasPrefix($0) }) else { return }
        var created: AXObserver?
        let result = AXObserverCreate(app.processIdentifier, { _, _, notification, context in
            guard let context else { return }
            MainActor.assumeIsolated {
                let owner = Unmanaged<PassiveObserver>.fromOpaque(context).takeUnretainedValue()
                if notification as String == kAXFocusedUIElementChangedNotification { owner.attachFocused() }
                owner.changed()
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
        guard !stopped, let attachedPID, NSWorkspace.shared.frontmostApplication?.processIdentifier == attachedPID else { return }
        changed()
    }
    private func add(_ element: AXUIElement, _ notification: String) {
        guard let observer else { return }
        if AXObserverAddNotification(observer, element, notification as CFString, Unmanaged.passUnretained(self).toOpaque()) == .success { observed.append((element, notification)) }
    }
    private func attachFocused() {
        // Focus changes detach old text observers so inactive fields are never analyzed.
        if let observer {
            for (element, notification) in observed where notification != kAXFocusedUIElementChangedNotification {
                AXObserverRemoveNotification(observer, element, notification as CFString)
            }
        }
        observed.removeAll { $0.1 != kAXFocusedUIElementChangedNotification }
        guard let app = NSWorkspace.shared.frontmostApplication, let focused = AX.focusedText(app), !AX.isSecure(focused) else { return }
        add(focused, kAXValueChangedNotification); add(focused, kAXSelectedTextChangedNotification)
        if let window = AX.get(focused, kAXWindowAttribute), CFGetTypeID(window) == AXUIElementGetTypeID() {
            add(window as! AXUIElement, kAXMovedNotification); add(window as! AXUIElement, kAXResizedNotification)
        }
    }
    private func changed() {
        work?.cancel(); onDismiss?()
        guard Preferences.shared.passive, !Preferences.shared.paused else { return }
        work = Task { @MainActor [weak self] in
            do {
                try await Task.sleep(for: .milliseconds(Int(Preferences.shared.boundedCheckingDelay)))
                try Task.checkCancellation()
                self?.onDismiss?()
                let snapshot = try SelectionSnapshot.capture(passive: true)
                let request = EngineRequest(text: snapshot.text, dictionary: Preferences.shared.dictionary,
                                            dialect: Preferences.shared.dialect, protectedRanges: snapshot.protectedRanges(), sentenceStart: snapshot.startsSentence, sentenceEnd: snapshot.endsSentence)
                // Automatic checks (typing and plain selection) never load the GPU model;
                // it runs only for explicit checks and tone changes.
                let engine = WritingEngine.typing
                let result = try await engine.rewrite(request)
                try Task.checkCancellation(); try snapshot.validate()
                guard !result.edits.isEmpty else { return }
                self?.onSuggestion?(snapshot, result)
            } catch { /* Passive failures are quiet and never log writing text. */ }
        }
    }
    func suspend() { work?.cancel(); onDismiss?() }
    func stop() {
        stopped = true; suspend()
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
