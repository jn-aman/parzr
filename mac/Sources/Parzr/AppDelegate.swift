import AppKit
import SwiftUI
import Combine
import ParzrCore
import Carbon

final class FloatingPanel: NSPanel {
    override var canBecomeKey: Bool { true }
    override var canBecomeMain: Bool { false }
}
@MainActor
final class AppDelegate: NSObject, NSApplicationDelegate, NSMenuDelegate, NSWindowDelegate, NSPopoverDelegate {
    let panelModel = AppModel()
    let studioModel = AppModel()
    private var statusItem: NSStatusItem?
    private var statusPopover: NSPopover?
    private var statusSourceApp: NSRunningApplication?
    /// Tests set this to false: windows are built, laid out and sent events, but never ordered on screen, and the app is never activated or given a Dock policy (`policy` records what would apply).
    var showsWindows = true
    private(set) var policy = NSApplication.ActivationPolicy.accessory
    /// Headless tests only: what a run would have on screen (an unshown window is never `isVisible`).
    private var headlessShown: Set<ObjectIdentifier> = []
    /// Tests replace the whole capture (Accessibility, then the copy fallback, which sends Cmd+C to the frontmost app) with a read of the writing space.
    var capture: (() async throws -> SelectionSnapshot)?
    private(set) var panel: FloatingPanel?
    private var panelFit: AnyCancellable?
    private var marker: NSPanel?
    private(set) var studio: NSWindow?
    private(set) var onboarding: NSWindow?
    private(set) var onboardingModel: OnboardingModel?
    private var hotkey: GlobalHotkey?
    private var passive: PassiveObserver?
    private lazy var inline = InlineSuggestions(headless: !showsWindows)
    private var subscriptions: Set<AnyCancellable> = []
    private var keyMonitor: Any?
    private var outsideMonitor: Any?
    private var popoverOutsideMonitor: Any?
    private var ownClickMonitor: Any?
    private var updates: UpdateController?
    private var updatePresenter: UpdatePresenter?
    private var updateDot: NSView?
    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
        openStudio()
        return true
    }
    /// AppKit asks this once after launch; the Studio (or, before setup is finished, the welcome guide) opens then, except under a fixture editor test, which must never put a Parzr window or the app's focus on the owner's screen.
    func applicationShouldOpenUntitledFile(_ sender: NSApplication) -> Bool { if !Preferences.isFixtureTest { openStudio() }; return false }
    func applicationWillTerminate(_ notification: Notification) { passive?.stop(); inline.stop() }
    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.accessory)
        NSApp.mainMenu = makeMenu()
        if CommandLine.arguments.contains("--health-check") {
            Task { @MainActor in
                do {
                    let result = try await WritingEngine.shared.rewrite(EngineRequest(text: "He go to school every day."))
                    guard result.text == "He goes to school every day." else { throw ParzrError.message("The bundled engine failed its startup fixture.") }
                    let report: [String: Any] = ["engine": "ready", "accessibility": AXIsProcessTrusted(), "automatic_suggestions": Preferences.shared.passive, "paused": Preferences.shared.paused]
                    let data = try JSONSerialization.data(withJSONObject: report, options: [.sortedKeys])
                    print(String(decoding: data, as: UTF8.self)); NSApp.terminate(nil)
                } catch { fputs("Bundled app health check failed: \(error.localizedDescription)\n", stderr); exit(1) }
            }
            return
        }
        if let index = CommandLine.arguments.firstIndex(of: "--paste-test"), CommandLine.arguments.indices.contains(index + 1) {
            Task { @MainActor in
                do { try await runAutomaticPasteTest(reportDirectory: CommandLine.arguments[index + 1]); print("Automatic fixture paste regression passed."); NSApp.terminate(nil) }
                catch { fputs("Automatic paste regression failed: \(error.localizedDescription)\n", stderr); exit(1) }
            }
            return
        }
        if let index = CommandLine.arguments.firstIndex(of: "--typing-test"), CommandLine.arguments.indices.contains(index + 1) {
            Task { @MainActor in
                do { try await runAutomaticTypingTest(reportDirectory: CommandLine.arguments[index + 1]); print("Automatic fixture typing regression passed."); NSApp.terminate(nil) }
                catch { fputs("Automatic typing regression failed: \(error.localizedDescription)\n", stderr); exit(1) }
            }
            return
        }
        if let index = CommandLine.arguments.firstIndex(of: "--docs-test"), CommandLine.arguments.indices.contains(index + 1) {
            Task { @MainActor in
                do { try await runGoogleDocsTest(reportDirectory: CommandLine.arguments[index + 1]); print("Google Docs regression passed."); NSApp.terminate(nil) }
                catch { fputs("Google Docs regression failed: \(error.localizedDescription)\n", stderr); exit(1) }
            }
            return
        }
        if let index = CommandLine.arguments.firstIndex(of: "--grammar-typing-test"),CommandLine.arguments.indices.contains(index + 1) {
            Task { @MainActor in
                do { try await runGrammarTypingTest(reportDirectory: CommandLine.arguments[index + 1]); print("Automatic fixture grammar regression passed."); NSApp.terminate(nil) }
                catch { fputs("Automatic grammar regression failed: \(error.localizedDescription)\n", stderr); exit(1) }
            }
            return
        }
        if let index = CommandLine.arguments.firstIndex(of: "--integration-test"), CommandLine.arguments.indices.contains(index + 1) {
            Task { @MainActor in
                do { try await runNativeIntegrationTest(reportDirectory: CommandLine.arguments[index + 1]); print("Native fixture integration passed."); NSApp.terminate(nil) }
                catch { fputs("Native integration failed: \(error.localizedDescription)\n", stderr); exit(1) }
            }
            return
        }
        // The Parzr-window flags (--ui-test, --editor-typing-test, --own-editor-test, --click-test) put real windows on the screen and take focus, so they are no longer part of the local release routine: their checks run headless in `swift test` (UIControlsWindowTests, EditorTypingWindowTests, OwnEditorWindowTests, CardClickWindowTests).
        // They stay for a VM or a spare Mac, where the end-to-end parts only a real screen can show still apply: menu-bar ownership, the real activation policy, a minimized window returning, the card as the key window and Accessibility reading and writing the editor.
        if let index = CommandLine.arguments.firstIndex(of: "--ui-test"), CommandLine.arguments.indices.contains(index + 1) {
            Task { @MainActor in
                do { try await runUIControlsTest(directory: CommandLine.arguments[index + 1]); print("Native UI controls passed."); NSApp.terminate(nil) }
                catch { fputs("Native UI controls failed: \(error.localizedDescription)\n", stderr); exit(1) }
            }
            return
        }
        if let index = CommandLine.arguments.firstIndex(of: "--editor-typing-test"), CommandLine.arguments.indices.contains(index + 1) {
            Task { @MainActor in
                do {
                    studioModel.engineReady = true; showStudio(route: .playground)
                    guard let studio, let host = studio.contentView else { throw ParzrError.message("The editor window did not open.") }
                    try await Task.sleep(for: .milliseconds(300))
                    try await runEditorTypingTest(model: studioModel, host: host, window: studio, directory: CommandLine.arguments[index + 1]); print("Editor typing regression passed."); NSApp.terminate(nil)
                } catch { fputs("Editor typing regression failed: \(error.localizedDescription)\n", stderr); exit(1) }
            }
            return
        }
        if let index = CommandLine.arguments.firstIndex(of: "--own-editor-test"), CommandLine.arguments.indices.contains(index + 1) {
            Task { @MainActor in
                do {
                    panelModel.dismiss = { [weak self] in self?.closePanel() }
                    studioModel.engineReady = true; showStudio(route: .playground)
                    guard let studio, let host = studio.contentView else { throw ParzrError.message("The editor window did not open.") }
                    try await Task.sleep(for: .milliseconds(300))
                    try await runOwnEditorTest(app: self, host: host, window: studio, directory: CommandLine.arguments[index + 1]); print("Own editor shortcut regression passed."); NSApp.terminate(nil)
                } catch { fputs("Own editor shortcut regression failed: \(error.localizedDescription)\n", stderr); exit(1) }
            }
            return
        }
        if let index = CommandLine.arguments.firstIndex(of: "--click-test"), CommandLine.arguments.indices.contains(index + 1) {
            let directory = CommandLine.arguments[index + 1]
            Task { @MainActor in
                do {
                    var problems: [String] = []
                    showOnboarding(step: .tryIt)
                    guard let onboarding, let host = onboarding.contentView else { throw ParzrError.message("The onboarding window did not open.") }
                    try await Task.sleep(for: .milliseconds(500))
                    do { try await runCardClickTest(host: host, window: onboarding, surface: "onboarding", typing: nil, directory: directory) } catch { problems.append(error.localizedDescription) }
                    onboarding.close()
                    studioModel.engineReady = true; showStudio(route: .playground)
                    guard let studio, let host = studio.contentView else { throw ParzrError.message("The editor window did not open.") }
                    try await Task.sleep(for: .milliseconds(500))
                    do { try await runCardClickTest(host: host, window: studio, surface: "studio", typing: "i recieved your mesage, can you chek it?", directory: directory) } catch { problems.append(error.localizedDescription) }
                    guard problems.isEmpty else { throw ParzrError.message(problems.joined(separator: "\n")) }
                    print("Card click regression passed."); NSApp.terminate(nil)
                } catch { fputs("Card click regression failed: \(error.localizedDescription)\n", stderr); exit(1) }
            }
            return
        }
        if let index = CommandLine.arguments.firstIndex(of: "--snapshot"), CommandLine.arguments.indices.contains(index + 1) {
            snapshot(to: CommandLine.arguments[index + 1]); return
        }
        #if DEBUG
        // Dev only: the updater alone, against the feed this build's Info.plist names. No onboarding, no Accessibility, no observers, no hotkey. The defaults flag lets the copy Sparkle relaunches (it gets no arguments) do the same.
        if CommandLine.arguments.contains("--update-test") || UserDefaults.standard.bool(forKey: "updateTestMode") {
            startUpdates(); updates?.start(); updatePresenter?.allowsFocus = false
            let arguments = CommandLine.arguments, index = arguments.firstIndex(of: "--update-test")
            let directory = index.flatMap { arguments.indices.contains($0 + 1) ? arguments[$0 + 1] : nil } ?? UserDefaults.standard.string(forKey: "updateTestDirectory") ?? NSTemporaryDirectory()
            let scenario = index.flatMap { arguments.indices.contains($0 + 2) ? arguments[$0 + 2] : nil } ?? "relaunched"
            Task { @MainActor in do { try await runUpdateTest(directory: directory, scenario: scenario) } catch { fputs("Update test failed: \(error.localizedDescription)\n", stderr); exit(1) } }
            return
        }
        #endif
        panelModel.warm(); studioModel.warm()
        Preferences.shared.purgeMisspelledNames()
        Preferences.shared.syncContacts()
        // known-words.json mirrors the saved dictionary and persistent names for the browser host, LSP and VS Code; it fires once at launch, then on any change.
        let prefs = Preferences.shared
        Publishers.CombineLatest4(prefs.$dictionary, prefs.$learnedNames, prefs.$contactNames, prefs.$useContactNames).debounce(for: .milliseconds(300), scheduler: RunLoop.main)
            .sink { _ in KnownWordsFile.writeCurrent() }.store(in: &subscriptions)
        let item = NSStatusBar.system.statusItem(withLength: NSStatusItem.squareLength)
        statusItem = item
        if let button = item.button {
            button.image = ParzrMark.menuImage(); button.toolTip = "Parzr · Option+Space"
            button.setAccessibilityLabel("Parzr writing assistant")
        }
        item.button?.target = self; item.button?.action = #selector(toggleStatusPopover)
        Preferences.shared.$paused.combineLatest(Preferences.shared.$passive, UpdateModel.shared.$pending.combineLatest(UpdateModel.shared.$available)).sink { [weak self] paused, automatic, update in
            let inactive = paused || !automatic, badge = update.0 != nil || update.1 != nil
            self?.statusItem?.button?.image = ParzrMark.menuImage(paused: inactive)
            self?.statusItem?.button?.setAccessibilityLabel((inactive ? "Parzr, highlights paused" : "Parzr, automatic highlights enabled") + (badge ? ", update ready" : ""))
            self?.showUpdateDot(badge)
        }.store(in: &subscriptions)
        Preferences.shared.$appearance.removeDuplicates().sink { [weak self] value in
            let appearance = value == "system" ? nil : NSAppearance(named: value == "paper" ? .aqua : .darkAqua)
            NSApp.appearance = appearance; self?.studio?.appearance = appearance; self?.onboarding?.appearance = appearance
        }.store(in: &subscriptions)
        Preferences.shared.$showInDock.dropFirst().removeDuplicates().sink { [weak self] show in
            // Changing policy can deactivate the app; keep an open Parzr window in front.
            guard let self else { return }
            self.updateActivationPolicy()
            guard self.studio?.isVisible == true else { return }
            Task { @MainActor in NSApp.activate(ignoringOtherApps: true); self.studio?.makeKeyAndOrderFront(nil) }
        }.store(in: &subscriptions)
        let hotkey = GlobalHotkey(); self.hotkey = hotkey
        hotkey.action = { [weak self] in self?.openSelection() }
        Publishers.CombineLatest3(Preferences.shared.$shortcutModifiers, Preferences.shared.$shortcutKey, Preferences.shared.$recordingShortcut).sink { [weak self] modifiers, key, recording in
            if recording { self?.hotkey?.unregister(); return }
            self?.studioModel.shortcutConflict = !(self?.hotkey?.register(key: key, modifiers: modifiers) ?? false)
            self?.statusItem?.button?.toolTip = "Parzr · \(Preferences.shared.shortcutDisplay)"
        }.store(in: &subscriptions)
        let passive = PassiveObserver(); self.passive = passive
        passive.onDismiss = { [weak self] in
            self?.inline.dismissIfStale()
            if let self, self.inline.hasMarks, self.inline.overflow > 0 { return }
            self?.marker?.orderOut(nil); self?.marker?.contentView = nil
        }
        passive.onSuggestion = { [weak self] snapshot, result in
            guard let self, !self.isShown(self.panel), !self.inline.isPresenting else { return }
            if Preferences.shared.selectedTextPopover, snapshot.expectedSelection.length > 0, let anchor = snapshot.bounds {
                _ = self.inline.present(snapshot: snapshot, result: result, anchor: anchor, activate: false)
                return
            }
            if !self.inline.show(snapshot: snapshot, result: result) || self.inline.overflow > 0 { self.showMarker(snapshot: snapshot, result: result) }
        }
        panelModel.dismiss = { [weak self] in self?.closePanel() }
        NSWorkspace.shared.notificationCenter.addObserver(self, selector: #selector(activated), name: NSWorkspace.didActivateApplicationNotification, object: nil)
        // A grant made in System Settings flips permissionGranted (watcher or trust notification); the monitors and observers re-attach from that, so no restart. Bring the welcome window back to show the check.
        Preferences.shared.$permissionGranted.removeDuplicates().sink { [weak self] granted in
            guard granted, let self, self.onboarding?.isVisible == true, self.onboardingModel?.step == .accessibility else { return }
            NSApp.activate(ignoringOtherApps: true); self.onboarding?.makeKeyAndOrderFront(nil)
        }.store(in: &subscriptions)
        // The grammar model compiles for the Neural Engine on first use (seconds): do it in the background once setup is finished, never during launch.
        Preferences.shared.$permissionGranted.combineLatest(Preferences.shared.$onboardingCompleted, Preferences.shared.$smartGrammar).filter { $0 && $1 && $2 }.first()
            .sink { _ in Task { try? await Task.sleep(for: .seconds(3)); await WritingEngine.warmGrammar() } }.store(in: &subscriptions)
        Preferences.shared.watchTrustChanges()
        Preferences.shared.refreshPermission()
        // First launch, or Accessibility missing: guided setup instead of a bare system prompt (its button triggers the prompt).
        if OnboardingFlow.shouldShow(completed: Preferences.shared.onboardingCompleted, granted: Preferences.shared.permissionGranted) { showOnboarding() }
        else if !CommandLine.arguments.contains("--background") { showStudio() }
        startUpdates()
    }
    /// Sparkle's updater and Parzr's own update panel. Only reached in a normal launch (every test and snapshot mode returns above), and it checks nothing until the welcome flow is done.
    private func startUpdates() {
        let anchor: () -> NSRect? = { [weak self] in self?.statusItem?.button?.window?.frame }
        guard let controller = UpdateController(isBusy: { [weak self] in
            guard let self else { return false }
            return self.panel?.isVisible == true || self.inline.isPresenting || self.studio?.isKeyWindow == true || self.onboarding?.isVisible == true || self.panelModel.busy || self.studioModel.busy
        }) else { return }
        updates = controller; updatePresenter = UpdatePresenter(anchor: anchor)
        if Preferences.shared.onboardingCompleted { controller.start() }
        else { Preferences.shared.$onboardingCompleted.filter { $0 }.first().sink { [weak controller] _ in controller?.start() }.store(in: &subscriptions) }
    }
    /// A small mint dot on the menu-bar icon while an update is waiting.
    private func showUpdateDot(_ visible: Bool) {
        guard let button = statusItem?.button else { return }
        if !visible { updateDot?.removeFromSuperview(); updateDot = nil; return }
        guard updateDot == nil else { return }
        let dot = NSView(frame: NSRect(x: button.bounds.maxX - 9, y: 4, width: 7, height: 7))
        dot.wantsLayer = true; dot.layer?.backgroundColor = NSColor(red: 0.22, green: 0.80, blue: 0.54, alpha: 1).cgColor; dot.layer?.cornerRadius = 3.5
        dot.layer?.borderWidth = 1; dot.layer?.borderColor = NSColor.black.withAlphaComponent(0.35).cgColor
        dot.autoresizingMask = [.minXMargin, .maxYMargin]; dot.setAccessibilityElement(false)
        button.addSubview(dot); updateDot = dot
    }
    func isShown(_ window: NSWindow?) -> Bool { window.map { showsWindows ? $0.isVisible : headlessShown.contains(ObjectIdentifier($0)) } ?? false }
    private func isOpen(_ window: NSWindow?) -> Bool { isShown(window) || (showsWindows && window?.isMiniaturized == true) }
    private func setPolicy(_ policy: NSApplication.ActivationPolicy) { self.policy = policy; if showsWindows { NSApp.setActivationPolicy(policy) } }
    /// The menu-bar popover's content, wired to the app; its buttons close the popover, then act.
    func statusPopoverView() -> StatusPopover {
        StatusPopover(engineReady: studioModel.engineReady, sourceApp: statusSourceApp,
            check: { [weak self] in
                self?.statusPopover?.close()
                self?.statusSourceApp?.activate(options: [])
                Task { @MainActor in try? await Task.sleep(for: .milliseconds(60)); self?.openSelection() }
            }, editor: { [weak self] in self?.statusPopover?.close(); self?.openStudio(route: .playground) },
            settings: { [weak self] in self?.statusPopover?.close(); self?.openStudio(route: .general) },
            about: { [weak self] in self?.statusPopover?.close(); self?.openStudio(route: .about) },
            quit: { NSApp.terminate(nil) })
    }
    func popoverDidClose(_ notification: Notification) {
        if let popoverOutsideMonitor { NSEvent.removeMonitor(popoverOutsideMonitor); self.popoverOutsideMonitor = nil }
    }
    @objc private func toggleStatusPopover() {
        guard let button = statusItem?.button else { return }
        if statusPopover?.isShown == true { statusPopover?.close(); return }
        guard Preferences.shared.setupFinished else { showOnboarding(); return }
        Preferences.shared.refreshPermission()
        let frontmost = NSWorkspace.shared.frontmostApplication
        if frontmost?.bundleIdentifier != Bundle.main.bundleIdentifier { statusSourceApp = frontmost }
        let popover = NSPopover(); popover.behavior = .transient
        popover.animates = !Preferences.shared.reduceMotion && !NSWorkspace.shared.accessibilityDisplayShouldReduceMotion
        popover.contentViewController = NSHostingController(rootView: statusPopoverView())
        statusPopover = popover; popover.delegate = self
        // Parzr stays an accessory app and never takes focus from the writer's app, so a transient popover only sees clicks inside Parzr. A click anywhere else closes it.
        if showsWindows, popoverOutsideMonitor == nil {
            popoverOutsideMonitor = NSEvent.addGlobalMonitorForEvents(matching: [.leftMouseDown, .rightMouseDown, .otherMouseDown]) { [weak self] _ in MainActor.assumeIsolated { self?.statusPopover?.close() } }
        }
        popover.show(relativeTo: button.bounds, of: button, preferredEdge: .minY)
        popover.contentViewController?.view.layoutSubtreeIfNeeded()
    }
    func makeMenu() -> NSMenu {
        let main = NSMenu(); let app = NSMenu(); let appItem = NSMenuItem(); appItem.submenu = app; main.addItem(appItem)
        let about = app.addItem(withTitle: "About Parzr", action: #selector(openAbout), keyEquivalent: ""); about.target = self
        let check = app.addItem(withTitle: "Check for Updates…", action: #selector(checkForUpdates), keyEquivalent: ""); check.target = self
        app.addItem(.separator())
        let settings = app.addItem(withTitle: "Settings…", action: #selector(openSettings), keyEquivalent: ","); settings.target = self
        app.addItem(.separator())
        app.addItem(withTitle: "Hide Parzr", action: #selector(NSApplication.hide(_:)), keyEquivalent: "h")
        app.addItem(withTitle: "Quit Parzr", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        let editItem = NSMenuItem(title: "Edit", action: nil, keyEquivalent: ""); let edit = NSMenu(title: "Edit"); editItem.submenu = edit; main.addItem(editItem)
        for (title, selector, key) in [("Undo", Selector(("undo:")), "z"), ("Cut", #selector(NSText.cut(_:)), "x"), ("Copy", #selector(NSText.copy(_:)), "c"), ("Paste", #selector(NSText.paste(_:)), "v"), ("Select All", #selector(NSText.selectAll(_:)), "a")] { edit.addItem(withTitle: title, action: selector, keyEquivalent: key) }
        let windowItem = NSMenuItem(title: "Window", action: nil, keyEquivalent: ""); let window = NSMenu(title: "Window"); windowItem.submenu = window; main.addItem(windowItem)
        window.addItem(withTitle: "Close", action: #selector(NSWindow.performClose(_:)), keyEquivalent: "w")
        window.addItem(withTitle: "Minimize", action: #selector(NSWindow.performMiniaturize(_:)), keyEquivalent: "m")
        NSApp.windowsMenu = window
        return main
    }
    @objc private func activated() {
        Preferences.shared.refreshPermission()
        if let app = NSWorkspace.shared.frontmostApplication, let snapshot = panelModel.snapshot, app.processIdentifier != snapshot.app.processIdentifier && app.bundleIdentifier != Bundle.main.bundleIdentifier { closePanel() }
        passive?.attach()
    }
    func menuNeedsUpdate(_ menu: NSMenu) {
        Preferences.shared.refreshPermission()
        menu.removeAllItems(); menu.autoenablesItems = false
        func add(_ title: String, action: Selector?, key: String = "", enabled: Bool = true) -> NSMenuItem {
            let item = NSMenuItem(title: title, action: action, keyEquivalent: key)
            item.target = self; item.isEnabled = enabled; menu.addItem(item); return item
        }
        guard Preferences.shared.setupFinished else {
            add("Finish setting up Parzr…", action: #selector(openWelcome)).image = NSImage(systemSymbolName: "hand.raised", accessibilityDescription: nil)
            menu.addItem(.separator())
            let quit = add("Quit Parzr", action: #selector(NSApplication.terminate(_:)), key: "q"); quit.target = NSApp
            return
        }
        _ = add(studioModel.engineReady ? "Parzr · Running locally" : studioModel.error == nil ? "Parzr · Starting locally…" : "Parzr · Engine unavailable", action: nil, enabled: false)
        menu.addItem(.separator())
        add("Check selected text", action: #selector(checkSelection)).image = NSImage(systemSymbolName: "text.cursor", accessibilityDescription: nil)
        add("Pause suggestions", action: #selector(togglePaused)).state = Preferences.shared.paused ? .on : .off
        add("Automatic highlights", action: #selector(toggleAutomatic)).state = Preferences.shared.passive ? .on : .off
        if let app = NSWorkspace.shared.frontmostApplication, let id = app.bundleIdentifier, id != Bundle.main.bundleIdentifier {
            let item = add("Enable in \(app.localizedName ?? "this app")", action: #selector(toggleCurrentApp(_:)))
            item.representedObject = id; item.state = Preferences.shared.enabled(for: id) ? .on : .off
        }
        if !Preferences.shared.permissionGranted { _ = add("Enable editor access…", action: #selector(enableEditorAccess)) }
        menu.addItem(.separator())
        add("Open Parzr", action: #selector(openEditor)).image = NSImage(systemSymbolName: "square.and.pencil", accessibilityDescription: nil)
        add("Settings…", action: #selector(openSettings), key: ",").image = NSImage(systemSymbolName: "gearshape", accessibilityDescription: nil)
        menu.addItem(.separator())
        let quit = add("Quit Parzr", action: #selector(NSApplication.terminate(_:)), key: "q"); quit.target = NSApp
    }
    @objc private func checkSelection() { openSelection() }
    @objc private func togglePaused() { Preferences.shared.paused.toggle() }
    @objc private func toggleAutomatic() { Preferences.shared.passive.toggle() }
    @objc private func toggleCurrentApp(_ item: NSMenuItem) { if let id = item.representedObject as? String { Preferences.shared.toggleApp(id) } }
    @objc private func enableEditorAccess() { Preferences.shared.requestPermission() }
    @objc private func openEditor() { openStudio(route: .playground) }
    @objc private func openAbout() { openStudio(route: .about) }
    @objc private func checkForUpdates() { UpdateModel.shared.perform(.check) }
    @objc private func openSettings() { openStudio(route: .general) }
    @objc private func openWelcome() { showOnboarding() }
    /// The Studio from the Dock, menus and popover; before setup is finished, the welcome guide instead.
    func openStudio(route: StudioRoute? = nil) { Preferences.shared.setupFinished ? showStudio(route: route) : showOnboarding() }
    /// The guided setup. Opens at the Accessibility step when that is still missing for a returning user. Only Start writing completes it.
    func showOnboarding(step: OnboardingStep? = nil) {
        closePanel()
        if let window = onboarding, isShown(window) { if let step { onboardingModel?.step = step }; if showsWindows { NSApp.activate(ignoringOtherApps: true); window.makeKeyAndOrderFront(nil) }; return }
        Preferences.shared.refreshPermission()
        let model = OnboardingModel(step: step); onboardingModel = model
        let view = OnboardingView(model: model, settings: { [weak self] in self?.showStudio(route: .general) },
                                  finish: { [weak self] in self?.onboardingModel?.complete(); self?.onboarding?.close(); self?.showStudio(route: .playground) })
        let window = NSWindow(contentRect: NSRect(origin: .zero, size: OnboardingView.size), styleMask: [.titled, .closable], backing: .buffered, defer: false)
        window.appearance = Preferences.shared.appearance == "system" ? nil : NSAppearance(named: Preferences.shared.appearance == "paper" ? .aqua : .darkAqua)
        window.title = "Welcome to Parzr"; window.titlebarAppearsTransparent = true; window.isReleasedWhenClosed = false; window.delegate = self
        window.contentView = NSHostingView(rootView: view); window.collectionBehavior = [.moveToActiveSpace]
        window.center(); onboarding = window
        setPolicy(.regular)
        guard showsWindows else { headlessShown.insert(ObjectIdentifier(window)); return }
        NSApp.unhide(nil); NSApp.activate(ignoringOtherApps: true); window.makeKeyAndOrderFront(nil); window.orderFrontRegardless()
    }
    /// Setup is mandatory: before it is finished, the close button and Cmd+W on the welcome guide ask to continue or quit instead of closing.
    func windowShouldClose(_ sender: NSWindow) -> Bool {
        guard sender === onboarding, !Preferences.shared.setupFinished else { return true }
        guard showsWindows else { return false }
        let alert = NSAlert()
        alert.messageText = "Finish setting up Parzr"
        alert.informativeText = "Parzr needs these steps before it can check your writing. You can quit now and finish setup the next time you open Parzr."
        alert.addButton(withTitle: "Continue Setup"); alert.addButton(withTitle: "Quit Parzr")
        alert.beginSheetModal(for: sender) { if $0 == .alertSecondButtonReturn { NSApp.terminate(nil) } }
        return false
    }
    func windowWillClose(_ notification: Notification) {
        guard let window = notification.object as? NSWindow else { return }
        headlessShown.remove(ObjectIdentifier(window))
        if window === onboarding { onboarding = nil; onboardingModel = nil }
        updateActivationPolicy(closing: window)
    }
    /// An accessory app never owns the menu bar, so a Parzr window the user works in (the editor, the welcome guide) makes the app regular whatever Show in Dock says; with it off, the last one closing goes back to menu-bar-only. A minimized window counts as open.
    private func updateActivationPolicy(closing: NSWindow? = nil) {
        setPolicy(ActivationPolicy.decide(showInDock: Preferences.shared.showInDock, windowOpen: [studio, onboarding].contains { $0 !== closing && isOpen($0) }))
    }
    func showStudio(route: StudioRoute? = nil) {
        studioModel.clearDraftUndo = { [weak self] in self?.studio?.undoManager?.removeAllActions() }
        if let route { studioModel.studioRoute = route }
        setPolicy(.regular)
        closePanel()
        if studio == nil {
            let window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 920, height: 680), styleMask: [.titled, .closable, .miniaturizable, .resizable, .fullSizeContentView], backing: .buffered, defer: false)
            window.appearance = Preferences.shared.appearance == "system" ? nil : NSAppearance(named: Preferences.shared.appearance == "paper" ? .aqua : .darkAqua)
            window.title = "Parzr"; window.titlebarAppearsTransparent = true; window.titleVisibility = .hidden
            window.contentView = NSHostingView(rootView: StudioView(model: studioModel)); window.minSize = NSSize(width: 760, height: 540); window.isReleasedWhenClosed = false
            window.collectionBehavior = [.moveToActiveSpace]; window.delegate = self
            window.center(); studio = window
        }
        guard showsWindows else { studio.map { _ = headlessShown.insert(ObjectIdentifier($0)) }; return }
        if studio?.isMiniaturized == true { studio?.deminiaturize(nil) }
        NSApp.unhide(nil); NSApp.activate(ignoringOtherApps: true); studio?.makeKeyAndOrderFront(nil); studio?.orderFrontRegardless()
    }
    private var capturing = false
    func openSelection() {
        guard Preferences.shared.setupFinished else { showOnboarding(); return }
        passive?.suspend(); inline.dismiss()
        if isShown(panel) { closePanel(); return }
        // A copy-based capture owns the clipboard for up to half a second; ignore repeat presses meanwhile.
        guard !capturing else { return }
        capturing = true
        Task { @MainActor in
            defer { capturing = false }
            do {
                let snapshot: SelectionSnapshot
                if let capture { snapshot = try await capture() }
                else { do { snapshot = try SelectionSnapshot.capture() }
                catch {
                    // AX cannot read canvas editors such as Google Docs; fall back to copying the selection.
                    let message = error.localizedDescription
                    guard message.hasPrefix("Select ") || message.hasPrefix("This editor hides"), let copied = try? await SelectionSnapshot.captureByCopy() else { throw error }
                    snapshot = copied
                } }
                panelModel.select(snapshot); studioModel.inspector = snapshot.metadata()
                showPanel(anchor: snapshot.bounds)
            } catch {
                panelModel.clearSession(); panelModel.error = error.localizedDescription; panelModel.sourceApp = "Your editor"
                panelModel.selectionHint = error.localizedDescription.hasPrefix("Select ")
                showPanel(anchor: nil)
            }
        }
    }
    private func showPanel(anchor: CGRect?) {
        if panel == nil {
            let panel = FloatingPanel(contentRect: NSRect(origin: .zero, size: RewritePanel.size), styleMask: [.borderless, .nonactivatingPanel], backing: .buffered, defer: false)
            panel.level = .floating; panel.isOpaque = false; panel.backgroundColor = .clear; panel.hasShadow = true
            panel.isReleasedWhenClosed = false; panel.hidesOnDeactivate = false; panel.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
            let host = NSHostingView(rootView: RewritePanel(model: panelModel)); host.wantsLayer = true; host.layer?.cornerRadius = 10; host.layer?.masksToBounds = true; panel.contentView = host
            self.panel = panel
            // An empty or failed check shrinks the card to its content; a result or a running check restores the full size. The top-left corner stays put.
            panelFit = panelModel.objectWillChange.receive(on: DispatchQueue.main).sink { [weak self] _ in DispatchQueue.main.async { self?.fitPanel() } }
        }
        guard let panel else { return }
        let screen = NSScreen.screens.first(where: { $0.frame.contains(anchor?.origin ?? NSEvent.mouseLocation) }) ?? NSScreen.main ?? NSScreen.screens[0]
        let visible = screen.visibleFrame
        let anchor = anchor ?? CGRect(origin: NSEvent.mouseLocation, size: .zero)
        let size = fittedPanelSize()
        panel.setContentSize(size)
        panel.setFrameOrigin(CorrectionPlacement.origin(anchor: anchor, size: size, visible: visible))
        if showsWindows { panel.makeKeyAndOrderFront(nil) } else { headlessShown.insert(ObjectIdentifier(panel)) }
        keyMonitor = NSEvent.addLocalMonitorForEvents(matching: .keyDown) { [weak self] event in
            let handled = MainActor.assumeIsolated { () -> Bool in
                guard let self, self.isShown(self.panel), event.window == self.panel else { return false }
                if event.keyCode == 53 || (event.modifierFlags.intersection([.command, .option, .control, .shift]) == .command && event.charactersIgnoringModifiers == "w") { self.closePanel(); return true }
                if event.keyCode == 36 && event.modifierFlags.intersection([.command, .option, .control, .shift]).isEmpty { self.panelModel.applyBest(); return true }
                if event.keyCode == 36 && event.modifierFlags.intersection([.command, .option, .control, .shift]) == .command { self.panelModel.apply(); return true }
                if event.modifierFlags.contains(.command), event.charactersIgnoringModifiers?.lowercased() == "c" { self.panelModel.copy(); return true }
                if [123,124].contains(event.keyCode) {
                    self.panelModel.navigate(event.keyCode == 124 ? 1 : -1); return true
                }
                return false
            }
            return handled ? nil : event
        }
        if showsWindows { outsideMonitor = NSEvent.addGlobalMonitorForEvents(matching: [.leftMouseDown, .rightMouseDown]) { [weak self] _ in MainActor.assumeIsolated { self?.closePanel() } } }
        // The global monitor never sees clicks in Parzr's own windows (the writing space the card was opened from).
        ownClickMonitor = NSEvent.addLocalMonitorForEvents(matching: [.leftMouseDown, .rightMouseDown]) { [weak self] event in
            MainActor.assumeIsolated { if let self, event.window != self.panel { self.closePanel() } }
            return event
        }
    }
    private func fittedPanelSize() -> CGSize {
        guard let host = panel?.contentView as? NSHostingView<RewritePanel> else { return RewritePanel.size }
        host.layoutSubtreeIfNeeded()
        return CGSize(width: RewritePanel.size.width, height: min(RewritePanel.size.height, ceil(host.fittingSize.height)))
    }
    private func fitPanel() {
        guard let panel, isShown(panel) else { return }
        let size = fittedPanelSize()
        guard abs(panel.contentLayoutRect.height - size.height) > 0.5 else { return }
        var frame = panel.frame
        let height = panel.frameRect(forContentRect: NSRect(origin: .zero, size: size)).height
        frame.origin.y += frame.height - height; frame.size.height = height
        if let visible = panel.screen?.visibleFrame { frame.origin.y = max(frame.origin.y, visible.minY) }
        panel.setFrame(frame, display: true)
    }
    func closePanel() {
        panel?.orderOut(nil); panel.map { _ = headlessShown.remove(ObjectIdentifier($0)) }
        if let keyMonitor { NSEvent.removeMonitor(keyMonitor); self.keyMonitor = nil }
        if let outsideMonitor { NSEvent.removeMonitor(outsideMonitor); self.outsideMonitor = nil }
        if let ownClickMonitor { NSEvent.removeMonitor(ownClickMonitor); self.ownClickMonitor = nil }
        panelModel.clearSession()
    }
    private func showMarker(snapshot: SelectionSnapshot, result: RewriteResult) {
        guard !isShown(panel), let bounds = snapshot.bounds, let screen = NSScreen.screens.first(where: { $0.frame.intersects(bounds) }) else { return }
        let more = inline.overflow
        let size = more > 0 ? NSSize(width: 40, height: 22) : NSSize(width: 26, height: 26)
        if marker == nil {
            marker = NSPanel(contentRect: NSRect(origin: .zero, size: size), styleMask: [.borderless, .nonactivatingPanel], backing: .buffered, defer: false)
            marker?.level = .floating; marker?.isOpaque = false; marker?.backgroundColor = .clear; marker?.hasShadow = false; marker?.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
        }
        marker?.contentView = NSHostingView(rootView: Button { [weak self] in
            do { try snapshot.validate(); self?.marker?.orderOut(nil); _ = self?.inline.present(snapshot: snapshot, result: result, anchor: bounds) } catch { self?.marker?.orderOut(nil); self?.marker?.contentView = nil }
        } label: {
            if more > 0 { Text("+\(more)").font(.system(size: 11, weight: .semibold)).foregroundStyle(Color.onAccent).padding(.horizontal, 7).frame(height: 20).background(Color.mintAccent, in: Capsule()) }
            else { Image(systemName: "pencil.circle.fill").font(.system(size: 21)).foregroundStyle(Color.mintAccent).background(Color.canvas, in: Circle()) }
        }.buttonStyle(.plain).help(more > 0 ? "\(more) more suggestions in this paragraph" : "Review local writing suggestions").accessibilityLabel(more > 0 ? "Review \(more) more writing suggestions" : "Review writing suggestions"))
        let x = bounds.maxX + 7
        // Hide when there's no margin; a marker must never cover the user's words.
        guard x + size.width <= screen.visibleFrame.maxX else { return }
        marker?.setContentSize(size); marker?.setFrameOrigin(NSPoint(x: x, y: bounds.minY)); marker?.orderFrontRegardless()
    }
    /// The explicit check card in every state, dark (`card-<state>.png`) and light (`-light`). Results are built by hand, so no engine is needed.
    private func cardSnapshots(to directory: URL) throws {
        let text = "i hope your doing well. can you chek this once?"
        let long = "I recieved your mesage about the quarterly planning review and wanted to follow up before the team meets on Thursday. The draft covers the budget, the hiring plan, the product roadmap and the open risks, and I think it would help if everyone read it first, so that we can spend the meeting deciding things instead of explaining them. If you have any thoughts on the timeline, please send them to me by Wednesday evening and I will fold them in."
        func edits(_ source: String, _ pairs: [(String, String)]) -> [WritingEdit] {
            pairs.compactMap { pair in
                let range = (source as NSString).range(of: pair.0)
                return range.location == NSNotFound ? nil : WritingEdit(start: range.location, end: range.location + range.length, replacement: pair.1, original: pair.0, category: "Spelling", ruleID: "spelling", explanation: "Possible misspelling.")
            }
        }
        func result(_ source: String, _ edits: [WritingEdit]) throws -> RewriteResult {
            let object: [String: Any] = ["version": "", "text": source, "edits": try JSONSerialization.jsonObject(with: JSONEncoder().encode(edits)), "source_map": [], "elapsed_ms": 0, "protected_count": 0]
            return try JSONDecoder().decode(RewriteResult.self, from: JSONSerialization.data(withJSONObject: object))
        }
        let found = edits(text, [("i", "I"), ("your", "you're"), ("chek", "check")]), longFound = edits(long, [("recieved", "received"), ("mesage", "message")])
        let grammar = [WritingEdit(start: 7, end: 11, replacement: "you're", original: "your", category: "Grammar", ruleID: "grammar", explanation: "Use the contraction.")]
        // (name, mode, source, edits or nil for none, busy, error, hint, status)
        typealias Card = (String, RewriteMode, String, [WritingEdit]?, Bool, String?, Bool, String?)
        var cards: [Card] = RewriteMode.allCases.map { ("mode-\($0.rawValue)", $0, text, found, false, nil, false, nil) }
        cards += [("empty-fix", .fix, text, [], false, nil, false, nil), ("empty-professional", .professional, text, [], false, nil, false, nil), ("empty-direct", .direct, text, [], false, nil, false, nil),
                  ("empty-warning", .fix, text, [], false, nil, false, "Context refinement is unavailable."),
                  ("busy-fix", .fix, text, nil, true, nil, false, nil), ("busy-concise", .concise, text, nil, true, nil, false, nil),
                  ("error", .fix, text, nil, false, "The writing engine did not answer. Try again in a moment.", false, nil), ("hint", .fix, "", nil, false, "Select text to check.", true, nil),
                  ("long", .fix, long, longFound, false, nil, false, nil), ("copy-labelled", .fix, text, grammar, false, nil, false, nil), ("copied", .fix, text, found, false, nil, false, "Copied to clipboard")]
        let saved = Preferences.shared.appearance
        defer { Preferences.shared.appearance = saved }
        for (name, mode, source, found, busy, error, hint, status) in cards {
            let model = AppModel()
            model.mode = mode; model.source = source; model.busy = busy; model.error = error; model.selectionHint = hint; model.status = status
            if let found { let r = try result(source, found); model.result = r; model.selectedEdits = Set(r.edits.map(\.id)); model.focusedEditID = r.edits.first?.id }
            let view = RewritePanel(model: model)
            let size = view.isCompact ? NSHostingView(rootView: view).fittingSize : RewritePanel.size
            for (suffix, look) in [("", "graphite"), ("-light", "paper")] {
                Preferences.shared.appearance = look
                try render(view, size: size, to: directory.appendingPathComponent("card-\(name)\(suffix).png"))
            }
        }
    }
    private func snapshot(to directory: String) {
        Task { @MainActor in
            do {
                try FileManager.default.createDirectory(atPath: directory, withIntermediateDirectories: true)
                // Widest footer: Fix sentence, This word, the name button and Ignore must all fit the 360 pt card. Needs no engine.
                let nameSource = "i met Aman Jain yestarday."
                let nameEdits = [WritingEdit(start: 6, end: 10, replacement: "Amen", original: "Aman", category: "Spelling", ruleID: "spelling", explanation: "Possible misspelling."), WritingEdit(start: 16, end: 25, replacement: "yesterday", original: "yestarday", category: "Spelling", ruleID: "spelling", explanation: "Possible misspelling.")]
                try render(InlineCorrection(edit: nameEdits[0], source: nameSource, edits: nameEdits, canApply: true, apply: {}, applySentence: {}, ignore: {}, close: {}), size: InlineCorrection.size, to: URL(fileURLWithPath: directory).appendingPathComponent("name-card.png"))
                UpdateModel.shared.canCheck = true; UpdateModel.shared.lastChecked = Date().addingTimeInterval(-7200)
                studioModel.engineReady = true; studioModel.playground("I recieved your mesage.\n\nCan you chek this?", debounce: true)
                for _ in 0..<300 where studioModel.busy || studioModel.result == nil { try await Task.sleep(for: .milliseconds(50)) }
                guard !studioModel.busy, studioModel.chosenEdits.count == 3 else { throw ParzrError.message("The snapshot's real draft check did not complete.") }
                try render(StudioView(model: studioModel, renderingSnapshot: true), size: NSSize(width: 920, height: 680), to: URL(fileURLWithPath: directory).appendingPathComponent("playground.png"))
                if let edit = studioModel.chosenEdits.first { try render(InlineCorrection(edit: edit, source: studioModel.source, edits: studioModel.chosenEdits, canApply: true, apply: {}, applySentence: {}, ignore: {}, close: {}), size: InlineCorrection.size, to: URL(fileURLWithPath: directory).appendingPathComponent("draft-card.png")) }
                panelModel.engineReady = true; panelModel.playground("i hope your doing well. can you chek this once?")
                for _ in 0..<300 where panelModel.busy { try await Task.sleep(for: .milliseconds(50)) }
                guard !panelModel.busy, !panelModel.chosenEdits.isEmpty else { throw ParzrError.message("The snapshot's real passage check did not complete.") }
                try render(RewritePanel(model: panelModel), size: RewritePanel.size, to: URL(fileURLWithPath: directory).appendingPathComponent("rewrite.png"))
                try render(RewritePanel(model: panelModel, showsModes: false), size: RewritePanel.size, to: URL(fileURLWithPath: directory).appendingPathComponent("inline.png"))
                try cardSnapshots(to: URL(fileURLWithPath: directory))
                for route in [StudioRoute.general, .writing, .appearance, .privacy, .about] {
                    try render(StudioView(model: studioModel, route: route, renderingSnapshot: true), size: NSSize(width: 920, height: 680), to: URL(fileURLWithPath: directory).appendingPathComponent("\(route.rawValue.lowercased()).png"))
                }
                try render(StudioView(model: studioModel, route: .writing, renderingSnapshot: true), size: NSSize(width: 920, height: 1240), to: URL(fileURLWithPath: directory).appendingPathComponent("writing-tall.png"))
                try render(StatusPopover(engineReady: true, sourceApp: nil, check: {}, editor: {}, settings: {}, about: {}, quit: {}), size: NSSize(width: 318, height: 334), to: URL(fileURLWithPath: directory).appendingPathComponent("menu.png"))
                // Update surfaces: one PNG per state, from a bare model (no Sparkle, no network).
                let notes = "## What's new\n- **Smarter names:** fewer wrong fixes on names and places.\n- Updates arrive quietly now, and you can read what changed first.\n- Fixed a rare stall when switching apps mid-sentence.\n\nFull notes on the [releases page](https://github.com/jn-aman/parzr/releases)."
                let release = UpdateInfo(version: "0.3.0", build: "7", bytes: 14_800_000, notes: notes, notesFormat: "markdown")
                let phases: [(String, UpdatePhase)] = [("checking", .checking), ("found", .found(release)), ("found-critical", .found({ var r = release; r.critical = true; return r }())),
                    ("downloading", .downloading(release, received: 6_100_000, total: 14_800_000)), ("extracting", .extracting(release, progress: 0.4)), ("ready", .ready(release)), ("installing", .installing(release)),
                    ("countdown", .countdown(release, seconds: 7)), ("uptodate", .upToDate("Parzr 0.3.0 is the latest version.")), ("failed", .failed(UpdateText.friendly(NSError(domain: NSURLErrorDomain, code: NSURLErrorNotConnectedToInternet)))), ("updated", .updated("0.3.0"))]
                for (name, phase) in phases {
                    let model = UpdateModel(); model.phase = phase
                    let view = UpdatePanelView(model: model, renderingSnapshot: true)
                    try render(view, size: NSHostingView(rootView: view).fittingSize, to: URL(fileURLWithPath: directory).appendingPathComponent("update-\(name).png"))
                }
                let rowModel = UpdateModel(); rowModel.pending = release
                UpdateModel.shared.pending = release
                try render(StatusPopover(engineReady: true, sourceApp: nil, check: {}, editor: {}, settings: {}, about: {}, quit: {}), size: NSSize(width: 318, height: 408), to: URL(fileURLWithPath: directory).appendingPathComponent("menu-update.png"))
                UpdateModel.shared.pending = nil
                try render(UpdateRow(model: rowModel).padding(18).frame(width: 318).background(Color.canvas), size: NSSize(width: 318, height: 92), to: URL(fileURLWithPath: directory).appendingPathComponent("update-row.png"))
                try render(StudioView(model: studioModel, route: .about, renderingSnapshot: true), size: NSSize(width: 760, height: 540), to: URL(fileURLWithPath: directory).appendingPathComponent("about-small.png"))
                // Onboarding: one PNG per step; the Accessibility step in both states. Previews never touch macOS permissions.
                let welcome = OnboardingModel(step: .welcome)
                welcome.editor.playground(welcome.draft, debounce: true)
                for _ in 0..<300 where welcome.editor.busy || welcome.editor.result == nil { try await Task.sleep(for: .milliseconds(50)) }
                guard welcome.editor.chosenEdits.count >= 3 else { throw ParzrError.message("The onboarding sample did not produce its suggestions.") }
                for step in OnboardingStep.allCases {
                    welcome.step = step; welcome.previewGranted = step == .done
                    try render(OnboardingView(model: welcome, renderingSnapshot: true), size: OnboardingView.size, to: URL(fileURLWithPath: directory).appendingPathComponent("onboarding-\(step.rawValue + 1).png"))
                }
                welcome.step = .accessibility; welcome.previewGranted = true
                try render(OnboardingView(model: welcome, renderingSnapshot: true), size: OnboardingView.size, to: URL(fileURLWithPath: directory).appendingPathComponent("onboarding-2-granted.png"))
                welcome.step = .done; welcome.previewGranted = false
                try render(OnboardingView(model: welcome, renderingSnapshot: true), size: OnboardingView.size, to: URL(fileURLWithPath: directory).appendingPathComponent("onboarding-6-skipped.png"))
                print("Saved native UI snapshots to \(directory)"); NSApp.terminate(nil)
            } catch { fputs("Native snapshots failed: \(error.localizedDescription)\n", stderr); exit(1) }
        }
    }
    #if DEBUG
    /// Scenarios: install (found, download, extract, ready, restart), fail (same, but the update must be rejected), skip (Skip this version holds for scheduled checks), check (a manual check with nothing new), relaunched (the copy Sparkle starts after an update, or a manual copy: the Updated toast must show only after an install by the updater), quit (waits for a background download, then quits so Sparkle installs on quit). Writes update-test-<scenario>.json and one PNG per new panel state.
    private func runUpdateTest(directory: String, scenario: String) async throws {
        guard let updates else { throw ParzrError.message("This build has no update feed.") }
        let model = UpdateModel.shared, target = URL(fileURLWithPath: directory), start = Date()
        try FileManager.default.createDirectory(at: target, withIntermediateDirectories: true)
        var timeline: [[String: Any]] = [], seen = Set<String>(), last = ""
        // A download or extraction after the quick update failed to apply carries "-full".
        func name(_ phase: UpdatePhase) -> String {
            let kind = String(describing: phase).split(separator: "(").first.map(String.init) ?? "idle"
            switch phase { case .downloading(let info, _, _), .extracting(let info, _): return info.fullInstead ? kind + "-full" : kind; default: return kind }
        }
        // Every phase change as it happens (the polled timeline can miss quick ones), with the panel's frame. Written as it goes: an install ends with Sparkle quitting this process.
        var trace: [[String: Any]] = [], traced = "", subscriptions = Set<AnyCancellable>()
        func record(_ phase: UpdatePhase, shown: Bool) {
            let kind = name(phase), panel = updatePresenter?.debugPanel
            var detail: [String: Any] = ["shown": shown, "panel": panel.map { $0.isVisible ? NSStringFromRect($0.frame) : "hidden" } ?? "none"]
            switch phase {
            case .downloading(_, let received, let total): detail["received"] = received; detail["total"] = total; traced = "\(kind) \(total > 0 ? received * 10 / total : 99) \(shown)"
            case .extracting(_, let progress): detail["progress"] = progress; traced = "\(kind) \(Int(progress * 10)) \(shown)"
            default: traced = "\(kind) \(shown)"
            }
            if trace.last?["key"] as? String == traced { return }
            trace.append(["key": traced, "t": (Date().timeIntervalSince(start) * 10).rounded() / 10, "phase": kind].merging(detail) { $1 })
            try? JSONSerialization.data(withJSONObject: trace, options: [.prettyPrinted, .sortedKeys]).write(to: target.appendingPathComponent("update-trace-\(scenario).json"))
        }
        Publishers.CombineLatest(model.$phase, model.$shown).receive(on: RunLoop.main).sink { record($0, shown: $1) }.store(in: &subscriptions)
        defer { subscriptions.removeAll() }
        func note() throws {
            let kind = name(model.phase)
            if kind != last { last = kind; timeline.append(["t": (Date().timeIntervalSince(start) * 10).rounded() / 10, "phase": kind, "shown": model.shown, "pending": model.pending?.version ?? "", "available": model.available?.version ?? ""]) }
            if kind != "idle", seen.insert(kind).inserted {
                let view = UpdatePanelView(model: model, renderingSnapshot: true)
                try render(view, size: NSHostingView(rootView: view).fittingSize, to: target.appendingPathComponent("\(scenario)-\(kind).png"))
            }
        }
        func wait(_ seconds: Double, until done: () -> Bool) async throws -> Bool {
            for _ in 0..<Int(seconds * 5) { try note(); if done() { return true }; try await Task.sleep(for: .milliseconds(200)) }
            return false
        }
        func finish(_ result: [String: Any]) throws {
            try JSONSerialization.data(withJSONObject: ["scenario": scenario, "version": Support.version, "timeline": timeline, "result": result], options: [.prettyPrinted, .sortedKeys]).write(to: target.appendingPathComponent("update-test-\(scenario).json"))
        }
        func foundVersion() -> String? { if case .found(let info) = model.phase { info.version } else { nil } }
        let panel = { [self] in updatePresenter?.debugPanel }
        func visible() -> Bool { panel()?.isVisible == true && model.shown }
        func fullDownload(minPercent: UInt64) -> Bool { if case .downloading(let info, let received, let total) = model.phase, info.fullInstead, total > 0 { received * 100 / total >= minPercent } else { false } }
        // A real click: the mouse events go through the panel's own event path while it is not the key window (an update test never takes focus).
        func click(_ label: String) -> Bool {
            guard let panel = panel(), let button = panel.contentView.flatMap({ NativeControls.find(label: label, in: $0) }) as? NSView, button.window === panel else { return false }
            let point = button.convert(NSPoint(x: button.bounds.midX, y: button.bounds.midY), to: nil)
            func event(_ type: NSEvent.EventType) -> NSEvent { NSEvent.mouseEvent(with: type, location: point, modifierFlags: [], timestamp: ProcessInfo.processInfo.systemUptime, windowNumber: panel.windowNumber, context: nil, eventNumber: 0, clickCount: 1, pressure: 1)! }
            NSApp.postEvent(event(.leftMouseUp), atStart: false); panel.sendEvent(event(.leftMouseDown))
            return true
        }
        // A drag by the background (the padding right of the title), as events: reports whether the window moved by itself.
        func drag(by delta: NSPoint) -> Bool {
            guard let panel = panel() else { return false }
            let origin = panel.frame.origin, grab = NSPoint(x: panel.frame.width - 6, y: panel.frame.height - 8)
            func event(_ type: NSEvent.EventType, _ point: NSPoint) -> NSEvent { NSEvent.mouseEvent(with: type, location: point, modifierFlags: [], timestamp: ProcessInfo.processInfo.systemUptime, windowNumber: panel.windowNumber, context: nil, eventNumber: 0, clickCount: 1, pressure: 1)! }
            NSApp.postEvent(event(.leftMouseUp, NSPoint(x: grab.x + delta.x, y: grab.y + delta.y)), atStart: false)
            panel.sendEvent(event(.leftMouseDown, grab))
            return panel.frame.origin != origin
        }
        switch scenario {
        case "relaunched":
            let shown = try await wait(20) { if case .updated = model.phase { true } else { false } }
            try await Task.sleep(for: .seconds(8))
            try finish(["updated_toast": shown]); NSApp.terminate(nil)
        case "quit":
            guard try await wait(150, until: { model.pending != nil }) else { throw ParzrError.message("No update was downloaded.") }
            try finish(["pending": model.pending?.version ?? ""]); NSApp.terminate(nil)
        case "install", "fail":
            guard try await wait(150, until: { foundVersion() != nil }) else { throw ParzrError.message("No update was offered.") }
            try await Task.sleep(for: .milliseconds(800)); try note(); model.perform(.install)
            let outcome = try await wait(120) { switch model.phase { case .installing, .ready, .failed: true; default: false } }
            try note()
            if case .failed(let message) = model.phase { try finish(["outcome": "failed", "message": message]); print("Update rejected: \(message)"); NSApp.terminate(nil); return }
            guard outcome else { throw ParzrError.message("The update never finished downloading.") }
            // One click: the download goes straight to installing and Sparkle relaunches the new version.
            try finish(["outcome": name(model.phase)])
            try await Task.sleep(for: .seconds(20)); throw ParzrError.message("The app did not relaunch.")
        case "hide", "cancel", "move":
            // The delta cannot apply to this copy, so Sparkle falls back to the full download: Hide in the extraction, Cancel in the fallback download, a dragged panel through every phase.
            var result: [String: Any] = [:]
            guard try await wait(150, until: { foundVersion() != nil }) else { throw ParzrError.message("No update was offered.") }
            try await Task.sleep(for: .milliseconds(800)); try note()
            result["key_window_at_found"] = panel()?.isKeyWindow ?? false
            if scenario == "move" {
                let home = panel()?.frame ?? .zero
                result["drag_by_events_moved"] = drag(by: NSPoint(x: -200, y: -120))
                if panel()?.frame.origin == home.origin { panel()?.setFrameOrigin(NSPoint(x: home.minX - 200, y: home.minY - 120)) }   // the window server does the move for a real drag
                result["home"] = NSStringFromRect(home); result["dragged"] = panel().map { NSStringFromRect($0.frame) } ?? ""
                if let panel = panel(), let host = panel.contentView { result["background_can_move_window"] = host.hitTest(NSPoint(x: panel.frame.width - 6, y: panel.frame.height - 8)).map { $0.mouseDownCanMoveWindow } ?? false }
            }
            model.perform(.install)
            if scenario == "cancel" {
                guard try await wait(120, until: { fullDownload(minPercent: 15) }) else { throw ParzrError.message("The fallback download never progressed.") }
                result["key_window_before_click"] = panel()?.isKeyWindow ?? false; result["cancel_clicked"] = click("Cancel")
                result["idle_after_cancel"] = try await wait(5) { model.phase == .idle && !visible() }
                try await Task.sleep(for: .seconds(4)); result["still_idle_4s_later"] = model.phase == .idle && !visible()
                model.perform(.check); result["offered_again_after_cancel"] = try await wait(40) { foundVersion() != nil }
                model.perform(.later); try finish(result); NSApp.terminate(nil); return
            }
            if scenario == "move" {
                guard try await wait(120, until: { fullDownload(minPercent: 10) }) else { throw ParzrError.message("The fallback download never progressed.") }
                result["frame_in_full_download"] = panel().map { NSStringFromRect($0.frame) } ?? ""
                result["hide_clicked_in_download"] = click("Hide the update panel")
                result["hidden_in_download"] = try await wait(3) { !visible() }
                let before = model.phase; try await Task.sleep(for: .seconds(2))
                if case .downloading(_, let a, _) = before, case .downloading(_, let b, _) = model.phase { result["download_continued_while_hidden"] = b > a } else { result["download_continued_while_hidden"] = "\(name(before)) to \(name(model.phase))" }
                result["still_hidden_after_progress"] = !visible()
                model.perform(.check); _ = try await wait(3) { visible() }
                result["reshown_frame"] = panel().map { NSStringFromRect($0.frame) } ?? ""
                try finish(result)
                _ = try await wait(120) { if case .installing = model.phase { true } else { false } }
                try await Task.sleep(for: .seconds(20)); throw ParzrError.message("The app did not relaunch.")
            }
            // hide: wait for the full download's extraction and hide there.
            guard try await wait(150, until: { if case .extracting(let info, _) = model.phase { info.fullInstead } else { false } }) else { throw ParzrError.message("No extraction after the full download.") }
            result["key_window_before_click"] = panel()?.isKeyWindow ?? false; result["hide_clicked_in_extraction"] = click("Hide the update panel")
            result["hidden_in_extraction"] = try await wait(3) { !visible() }
            try finish(result)
            _ = try await wait(120) { if case .installing = model.phase { true } else { false } }
            result["panel_visible_while_installing"] = visible(); try finish(result)
            try await Task.sleep(for: .seconds(20)); throw ParzrError.message("The app did not relaunch.")
        case "skip":
            guard try await wait(150, until: { foundVersion() != nil }) else { throw ParzrError.message("No update was offered.") }
            model.perform(.skip); _ = try await wait(3) { false }
            updates.checkInBackground(); let again = try await wait(15) { foundVersion() != nil }
            model.perform(.check); let manual = try await wait(15) { foundVersion() != nil }
            try finish(["offered_again_after_skip_by_scheduled_check": again, "offered_by_manual_check": manual]); model.perform(.later); NSApp.terminate(nil)
        default:
            // The launch-time scheduled check may still be running (Sparkle drops a manual check then), so retry.
            var done = false
            for _ in 0..<4 where !done { model.perform(.check); done = try await wait(8) { if case .upToDate = model.phase { true } else { false } } }
            try finish(["up_to_date": done]); NSApp.terminate(nil)
        }
    }
    #endif
    /// `--ui-test`. Not part of the local release routine (it opens and activates real windows); the same controls are checked headless by UIControlsWindowTests, and this stays for the parts that need a real screen.
    private func runUIControlsTest(directory: String) async throws {
        guard !IsSecureEventInputEnabled() else { throw ParzrError.message("UI QA stopped while secure input is active.") }
        let target = URL(fileURLWithPath: directory)
        try FileManager.default.createDirectory(at: target, withIntermediateDirectories: true)
        // Menu-bar-only mode: an open Parzr window still brings the app menus and takes the menu bar; closing it gives both back.
        Preferences.shared.showInDock = false
        guard NSApp.activationPolicy() == .accessory else { throw ParzrError.message("The test did not start menu-bar-only.") }
        showStudio(route: .playground)
        guard let studio, let host = studio.contentView else { throw ParzrError.message("The editor window did not open.") }
        guard NSApp.activationPolicy() == .regular, NSApp.mainMenu?.items.map(\.title).contains("Window") == true else { throw ParzrError.message("Opening the editor with Show in Dock off did not give Parzr its menus.") }
        for _ in 0..<40 where NSWorkspace.shared.menuBarOwningApplication?.processIdentifier != getpid() { try await Task.sleep(for: .milliseconds(50)) }
        guard NSWorkspace.shared.menuBarOwningApplication?.processIdentifier == getpid() else { throw ParzrError.message("Parzr did not take the menu bar while its editor is open.") }
        try await Task.sleep(for: .milliseconds(200))
        guard let sample = NativeControls.find(label: "Try a sample", in: host), sample.accessibilityPerformPress() else { throw ParzrError.message("The sample button did not activate.") }
        for _ in 0..<80 { try await Task.sleep(for: .milliseconds(50)); if !studioModel.busy && studioModel.chosenEdits.count == 3 { break } }
        let sampleSource = "I recieved your mesage.\n\nCan you chek this?"
        func textView(_ view: NSView) -> NSTextView? { if let text = view as? NSTextView { return text }; return view.subviews.compactMap(textView).first }
        guard let draft = textView(host) else { throw ParzrError.message("The draft text view is unavailable.") }
        // The authored sample is the fixture baseline. Accessibility actions
        // share this QA task rather than separate AppKit mouse events.
        draft.breakUndoCoalescing()
        draft.undoManager?.removeAllActions()
        guard studioModel.source == sampleSource, studioModel.chosenEdits.count == 3,
              let apply = NativeControls.find(label: "Apply all", in: host), apply.accessibilityPerformPress() else { throw ParzrError.message("The editor Apply all button did not activate.") }
        for _ in 0..<80 { try await Task.sleep(for: .milliseconds(50)); if !studioModel.busy && studioModel.source == "I received your message.\n\nCan you check this?" { break } }
        guard studioModel.source == "I received your message.\n\nCan you check this?" else { throw ParzrError.message("Apply all did not update the native draft.") }
        guard draft.undoManager?.canUndo == true else { throw ParzrError.message("Apply all did not preserve native Undo.") }
        draft.undoManager?.undo()
        for _ in 0..<80 { try await Task.sleep(for: .milliseconds(50)); if !studioModel.busy && !studioModel.provisional && studioModel.source == sampleSource { break } }
        guard studioModel.source == sampleSource else {
            let diagnostics: [String: Any] = ["fixture_only": true, "model": studioModel.source, "draft": draft.string, "undo_action": draft.undoManager?.undoActionName ?? "", "can_undo": draft.undoManager?.canUndo == true]
            try JSONSerialization.data(withJSONObject: diagnostics, options: [.prettyPrinted, .sortedKeys]).write(to: target.appendingPathComponent("undo-failure.json"))
            throw ParzrError.message("Native Undo did not restore the draft.")
        }
        draft.setSelectedRange(NSRange(location: 0, length: 0))
        try NativeControls.snapshot(host, to: target.appendingPathComponent("playground-live.png"))
        let pasteboard = NSPasteboard.general
        let savedClipboard = (pasteboard.pasteboardItems ?? []).map { item in item.types.compactMap { type in item.data(forType: type).map { (type, $0) } } }
        var fixtureClipboardCount: Int?
        defer {
            if let fixtureClipboardCount, pasteboard.changeCount == fixtureClipboardCount {
                pasteboard.clearContents()
                let items = savedClipboard.map { entries in let item = NSPasteboardItem(); for (type, data) in entries { item.setData(data, forType: type) }; return item }
                pasteboard.writeObjects(items)
            }
        }
        guard let copy = NativeControls.find(label: "Copy", in: host), copy.accessibilityPerformPress() else { throw ParzrError.message("The Copy button did not activate.") }
        fixtureClipboardCount = pasteboard.changeCount
        guard pasteboard.string(forType: .string) == "I received your message.\n\nCan you check this?" else { throw ParzrError.message("Copy did not use the corrected draft.") }
        guard let gear = NativeControls.find(label: "Settings", in: host), gear.accessibilityPerformPress(), studioModel.studioRoute == .general else { throw ParzrError.message("The Settings button did not open settings.") }
        try await Task.sleep(for: .milliseconds(300))
        guard NativeControls.find(label: "Quit Parzr", in: host) != nil else { throw ParzrError.message("Settings has no Quit Parzr button.") }   // found, never pressed
        guard let done = NativeControls.find(label: "Return to editor", in: host), done.accessibilityPerformPress(), studioModel.studioRoute == .playground else { throw ParzrError.message("The Done button did not return to the editor.") }
        let menu = NSMenu(); menuNeedsUpdate(menu)
        guard let settings = menu.items.first(where: { $0.title == "Settings…" }), let action = settings.action, NSApp.sendAction(action, to: settings.target, from: settings), studioModel.studioRoute == .general else { throw ParzrError.message("The menu Settings action did not open settings.") }
        _ = applicationShouldHandleReopen(NSApp, hasVisibleWindows: true)
        guard studio.isVisible else { throw ParzrError.message("Reopening did not bring the window forward.") }
        studio.miniaturize(nil)
        try await Task.sleep(for: .milliseconds(200))
        _ = applicationShouldHandleReopen(NSApp, hasVisibleWindows: false)
        try await Task.sleep(for: .milliseconds(200))
        guard studio.isVisible, !studio.isMiniaturized else { throw ParzrError.message("Reopening did not restore the minimized window.") }
        studio.close()
        guard NSApp.activationPolicy() == .accessory else { throw ParzrError.message("Closing the editor with Show in Dock off did not return Parzr to the menu bar.") }
        _ = applicationShouldHandleReopen(NSApp, hasVisibleWindows: false)
        guard NSApp.activationPolicy() == .regular else { throw ParzrError.message("Reopening the editor did not bring back Parzr's menus.") }
        guard studio.isVisible else { throw ParzrError.message("Reopening did not restore the closed window.") }
        let reviewStatusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.squareLength)
        reviewStatusItem.autosaveName = "parzr.selftest"   // removing it forgets its own spot, never the real icon's ("Item-0" lives in the app's real defaults)
        reviewStatusItem.button?.image = ParzrMark.menuImage()
        statusItem = reviewStatusItem
        defer { statusPopover?.close(); NSStatusBar.system.removeStatusItem(reviewStatusItem); statusItem = nil }
        for (label, route) in [("Settings", StudioRoute.general), ("About Parzr", .about), ("Open Parzr", .playground)] {
            toggleStatusPopover()
            try await Task.sleep(for: .milliseconds(250))
            guard let menuHost = statusPopover?.contentViewController?.view else { throw ParzrError.message("The new menu panel has no content view.") }
            menuHost.layoutSubtreeIfNeeded()
            guard let button = NativeControls.find(label: label, in: menuHost) else {
                func buttons(_ view: NSView) -> [String] { (view as? NSButton).map { [$0.accessibilityLabel() ?? $0.title] } ?? view.subviews.flatMap(buttons) }
                let diagnostics: [String: Any] = ["shown": statusPopover?.isShown == true, "labels": buttons(menuHost), "width": menuHost.frame.width, "height": menuHost.frame.height]
                try JSONSerialization.data(withJSONObject: diagnostics, options: [.prettyPrinted, .sortedKeys]).write(to: target.appendingPathComponent("menu-failure.json"))
                throw ParzrError.message("The new menu-panel \(label) button was not mounted.")
            }
            guard button.accessibilityPerformPress() else { throw ParzrError.message("The new menu-panel \(label) button was disabled.") }
            guard studioModel.studioRoute == route else { throw ParzrError.message("The new menu-panel \(label) button did not open its destination.") }
        }
        studioModel.studioRoute = .privacy
        try await Task.sleep(for: .milliseconds(300))
        guard let clear = NativeControls.find(label: "Clear this writing session", in: host), clear.accessibilityPerformPress() else { throw ParzrError.message("The session-clear button did not activate.") }
        studioModel.studioRoute = .playground
        try await Task.sleep(for: .milliseconds(300))
        guard studioModel.source.isEmpty, let clearedDraft = textView(host), clearedDraft.string.isEmpty, clearedDraft.undoManager?.canUndo != true else { throw ParzrError.message("Session clear left text or Undo history behind.") }
        let report: [String: Any] = ["sample_button": true, "apply_all_button": true, "copy_button": true, "settings_button": true, "done_button": true, "clear_session_button": true, "draft_native_undo": true, "menu_settings_action": true, "status_panel_settings": true, "status_panel_about": true, "status_panel_editor": true, "reopen_visible": true, "reopen_minimized": true, "reopen_closed": true, "menus_while_open": true, "menu_bar_only_after_close": true, "quit_button": true, "status": "passed"]
        try JSONSerialization.data(withJSONObject: report, options: [.prettyPrinted, .sortedKeys]).write(to: target.appendingPathComponent("ui-controls-results.json"))
        studio.close()
    }
    private func render<V: View>(_ view: V, size: NSSize, to url: URL) throws {
        let host = NSHostingView(rootView: view); host.frame = NSRect(origin: .zero, size: size)
        let window = NSWindow(contentRect: host.frame, styleMask: [.borderless], backing: .buffered, defer: false)
        window.appearance = Preferences.shared.appearance == "system" ? nil : NSAppearance(named: Preferences.shared.appearance == "paper" ? .aqua : .darkAqua)
        window.isReleasedWhenClosed = false; window.contentView = host; window.layoutIfNeeded(); host.layoutSubtreeIfNeeded()
        guard let bitmap = host.bitmapImageRepForCachingDisplay(in: host.bounds) else { throw ParzrError.message("Could not create a UI snapshot.") }
        host.cacheDisplay(in: host.bounds, to: bitmap)
        guard let png = bitmap.representation(using: .png, properties: [:]) else { throw ParzrError.message("Could not encode the UI snapshot.") }
        try png.write(to: url); window.close()
    }
}

/// Which Dock policy the app needs: an accessory app never owns the menu bar, so an open Parzr window makes it regular whatever Show in Dock says. Pure so tests can check it without activating anything.
enum ActivationPolicy {
    static func decide(showInDock: Bool, windowOpen: Bool) -> NSApplication.ActivationPolicy { showInDock || windowOpen ? .regular : .accessory }
}
