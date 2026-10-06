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
final class AppDelegate: NSObject, NSApplicationDelegate, NSMenuDelegate, NSWindowDelegate {
    private let panelModel = AppModel()
    private let studioModel = AppModel()
    private var statusItem: NSStatusItem?
    private var statusPopover: NSPopover?
    private var statusSourceApp: NSRunningApplication?
    private var panel: FloatingPanel?
    private var marker: NSPanel?
    private var studio: NSWindow?
    private var onboarding: NSWindow?
    private var onboardingModel: OnboardingModel?
    private var hotkey: GlobalHotkey?
    private var passive: PassiveObserver?
    private let inline = InlineSuggestions()
    private var subscriptions: Set<AnyCancellable> = []
    private var keyMonitor: Any?
    private var outsideMonitor: Any?
    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
        showStudio()
        return true
    }
    func applicationShouldOpenUntitledFile(_ sender: NSApplication) -> Bool { showStudio(); return false }
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
                do { try await runAutomaticPasteTest(reportDirectory: CommandLine.arguments[index + 1]); print("Automatic TextEdit paste regression passed."); NSApp.terminate(nil) }
                catch { fputs("Automatic paste regression failed: \(error.localizedDescription)\n", stderr); exit(1) }
            }
            return
        }
        if let index = CommandLine.arguments.firstIndex(of: "--typing-test"), CommandLine.arguments.indices.contains(index + 1) {
            Task { @MainActor in
                do { try await runAutomaticTypingTest(reportDirectory: CommandLine.arguments[index + 1]); print("Automatic TextEdit typing regression passed."); NSApp.terminate(nil) }
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
                do { try await runGrammarTypingTest(reportDirectory: CommandLine.arguments[index + 1]); print("Automatic TextEdit grammar regression passed."); NSApp.terminate(nil) }
                catch { fputs("Automatic grammar regression failed: \(error.localizedDescription)\n", stderr); exit(1) }
            }
            return
        }
        if let index = CommandLine.arguments.firstIndex(of: "--integration-test"), CommandLine.arguments.indices.contains(index + 1) {
            Task { @MainActor in
                do { try await runNativeIntegrationTest(reportDirectory: CommandLine.arguments[index + 1]); print("Native TextEdit integration passed."); NSApp.terminate(nil) }
                catch { fputs("Native integration failed: \(error.localizedDescription)\n", stderr); exit(1) }
            }
            return
        }
        if let index = CommandLine.arguments.firstIndex(of: "--ui-test"), CommandLine.arguments.indices.contains(index + 1) {
            Task { @MainActor in
                do { try await runUIControlsTest(directory: CommandLine.arguments[index + 1]); print("Native UI controls passed."); NSApp.terminate(nil) }
                catch { fputs("Native UI controls failed: \(error.localizedDescription)\n", stderr); exit(1) }
            }
            return
        }
        if let index = CommandLine.arguments.firstIndex(of: "--snapshot"), CommandLine.arguments.indices.contains(index + 1) {
            snapshot(to: CommandLine.arguments[index + 1]); return
        }
        panelModel.warm(); studioModel.warm()
        studioModel.showOnboarding = { [weak self] in self?.showOnboarding() }
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
        Preferences.shared.$paused.combineLatest(Preferences.shared.$passive).sink { [weak self] paused, automatic in
            let inactive = paused || !automatic
            self?.statusItem?.button?.image = ParzrMark.menuImage(paused: inactive)
            self?.statusItem?.button?.setAccessibilityLabel(inactive ? "Parzr, highlights paused" : "Parzr, automatic highlights enabled")
        }.store(in: &subscriptions)
        Preferences.shared.$appearance.removeDuplicates().sink { [weak self] value in
            let appearance = value == "system" ? nil : NSAppearance(named: value == "paper" ? .aqua : .darkAqua)
            NSApp.appearance = appearance; self?.studio?.appearance = appearance; self?.onboarding?.appearance = appearance
        }.store(in: &subscriptions)
        Preferences.shared.$showInDock.dropFirst().removeDuplicates().sink { [weak self] show in
            // Changing policy can deactivate the app; keep an open Parzr window in front.
            guard let self, self.studio?.isVisible == true else { return }
            NSApp.setActivationPolicy(show ? .regular : .accessory)
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
            guard let self, self.panel?.isVisible != true, !self.inline.isPresenting else { return }
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
    }
    @objc private func toggleStatusPopover() {
        guard let button = statusItem?.button else { return }
        if statusPopover?.isShown == true { statusPopover?.close(); return }
        Preferences.shared.refreshPermission()
        let frontmost = NSWorkspace.shared.frontmostApplication
        if frontmost?.bundleIdentifier != Bundle.main.bundleIdentifier { statusSourceApp = frontmost }
        let popover = NSPopover(); popover.behavior = .transient
        popover.animates = !Preferences.shared.reduceMotion && !NSWorkspace.shared.accessibilityDisplayShouldReduceMotion
        popover.contentViewController = NSHostingController(rootView: StatusPopover(engineReady: studioModel.engineReady, sourceApp: statusSourceApp,
            check: { [weak self] in
                self?.statusPopover?.close()
                self?.statusSourceApp?.activate(options: [])
                Task { @MainActor in try? await Task.sleep(for: .milliseconds(60)); self?.openSelection() }
            }, editor: { [weak self] in self?.statusPopover?.close(); self?.showStudio(route: .playground) },
            settings: { [weak self] in self?.statusPopover?.close(); self?.showStudio(route: .general) },
            about: { [weak self] in self?.statusPopover?.close(); self?.showStudio(route: .about) },
            welcome: { [weak self] in self?.statusPopover?.close(); self?.showOnboarding() },
            quit: { NSApp.terminate(nil) }))
        statusPopover = popover
        popover.show(relativeTo: button.bounds, of: button, preferredEdge: .minY)
        popover.contentViewController?.view.layoutSubtreeIfNeeded()
    }
    private func makeMenu() -> NSMenu {
        let main = NSMenu(); let app = NSMenu(); let appItem = NSMenuItem(); appItem.submenu = app; main.addItem(appItem)
        let about = app.addItem(withTitle: "About Parzr", action: #selector(openAbout), keyEquivalent: ""); about.target = self
        app.addItem(.separator())
        let settings = app.addItem(withTitle: "Settings…", action: #selector(openSettings), keyEquivalent: ","); settings.target = self
        let welcome = app.addItem(withTitle: "Welcome and permissions…", action: #selector(openWelcome), keyEquivalent: ""); welcome.target = self
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
        add("Welcome and permissions…", action: #selector(openWelcome)).image = NSImage(systemSymbolName: "hand.raised", accessibilityDescription: nil)
        menu.addItem(.separator())
        let quit = add("Quit Parzr", action: #selector(NSApplication.terminate(_:)), key: "q"); quit.target = NSApp
    }
    @objc private func checkSelection() { openSelection() }
    @objc private func togglePaused() { Preferences.shared.paused.toggle() }
    @objc private func toggleAutomatic() { Preferences.shared.passive.toggle() }
    @objc private func toggleCurrentApp(_ item: NSMenuItem) { if let id = item.representedObject as? String { Preferences.shared.toggleApp(id) } }
    @objc private func enableEditorAccess() { Preferences.shared.requestPermission() }
    @objc private func openEditor() { showStudio(route: .playground) }
    @objc private func openAbout() { showStudio(route: .about) }
    @objc private func openSettings() { showStudio(route: .general) }
    @objc private func openWelcome() { showOnboarding() }
    /// The guided setup. Opens at the Accessibility step when that is still missing for a returning user; closing it by any route marks it completed.
    func showOnboarding(step: OnboardingStep? = nil) {
        closePanel()
        if let window = onboarding, window.isVisible { if let step { onboardingModel?.step = step }; NSApp.activate(ignoringOtherApps: true); window.makeKeyAndOrderFront(nil); return }
        Preferences.shared.refreshPermission()
        let model = OnboardingModel(step: step); onboardingModel = model
        let view = OnboardingView(model: model, settings: { [weak self] in self?.showStudio(route: .general) },
                                  finish: { [weak self] in self?.onboarding?.close(); self?.showStudio(route: .playground) })
        let window = NSWindow(contentRect: NSRect(origin: .zero, size: OnboardingView.size), styleMask: [.titled, .closable], backing: .buffered, defer: false)
        window.appearance = Preferences.shared.appearance == "system" ? nil : NSAppearance(named: Preferences.shared.appearance == "paper" ? .aqua : .darkAqua)
        window.title = "Welcome to Parzr"; window.titlebarAppearsTransparent = true; window.isReleasedWhenClosed = false; window.delegate = self
        window.contentView = NSHostingView(rootView: view); window.collectionBehavior = [.moveToActiveSpace]
        window.center(); onboarding = window
        if Preferences.shared.showInDock { NSApp.setActivationPolicy(.regular) }
        NSApp.unhide(nil); NSApp.activate(ignoringOtherApps: true); window.makeKeyAndOrderFront(nil); window.orderFrontRegardless()
    }
    func windowWillClose(_ notification: Notification) {
        guard let window = notification.object as? NSWindow, window === onboarding else { return }
        onboardingModel?.complete(); onboarding = nil; onboardingModel = nil
    }
    func showStudio(route: StudioRoute? = nil) {
        studioModel.clearDraftUndo = { [weak self] in self?.studio?.undoManager?.removeAllActions() }
        if let route { studioModel.studioRoute = route }
        if Preferences.shared.showInDock { NSApp.setActivationPolicy(.regular) }
        closePanel()
        if studio == nil {
            let window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 920, height: 680), styleMask: [.titled, .closable, .miniaturizable, .resizable, .fullSizeContentView], backing: .buffered, defer: false)
            window.appearance = Preferences.shared.appearance == "system" ? nil : NSAppearance(named: Preferences.shared.appearance == "paper" ? .aqua : .darkAqua)
            window.title = "Parzr"; window.titlebarAppearsTransparent = true; window.titleVisibility = .hidden
            window.contentView = NSHostingView(rootView: StudioView(model: studioModel)); window.minSize = NSSize(width: 760, height: 540); window.isReleasedWhenClosed = false
            window.collectionBehavior = [.moveToActiveSpace]
            window.center(); studio = window
        }
        if studio?.isMiniaturized == true { studio?.deminiaturize(nil) }
        NSApp.unhide(nil); NSApp.activate(ignoringOtherApps: true); studio?.makeKeyAndOrderFront(nil); studio?.orderFrontRegardless()
    }
    private var capturing = false
    private func openSelection() {
        passive?.suspend(); inline.dismiss()
        if panel?.isVisible == true { closePanel(); return }
        // A copy-based capture owns the clipboard for up to half a second; ignore repeat presses meanwhile.
        guard !capturing else { return }
        capturing = true
        Task { @MainActor in
            defer { capturing = false }
            do {
                let snapshot: SelectionSnapshot
                do { snapshot = try SelectionSnapshot.capture() }
                catch {
                    // AX cannot read canvas editors such as Google Docs; fall back to copying the selection.
                    let message = error.localizedDescription
                    guard message.hasPrefix("Select ") || message.hasPrefix("This editor hides"), let copied = try? await SelectionSnapshot.captureByCopy() else { throw error }
                    snapshot = copied
                }
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
        }
        guard let panel else { return }
        let screen = NSScreen.screens.first(where: { $0.frame.contains(anchor?.origin ?? NSEvent.mouseLocation) }) ?? NSScreen.main ?? NSScreen.screens[0]
        let visible = screen.visibleFrame
        let anchor = anchor ?? CGRect(origin: NSEvent.mouseLocation, size: .zero)
        let size = panelModel.selectionHint ? RewritePanel.hintSize : RewritePanel.size
        panel.setContentSize(size)
        panel.setFrameOrigin(CorrectionPlacement.origin(anchor: anchor, size: size, visible: visible))
        panel.makeKeyAndOrderFront(nil)
        keyMonitor = NSEvent.addLocalMonitorForEvents(matching: .keyDown) { [weak self] event in
            let handled = MainActor.assumeIsolated { () -> Bool in
                guard let self, self.panel?.isVisible == true, event.window == self.panel else { return false }
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
        outsideMonitor = NSEvent.addGlobalMonitorForEvents(matching: [.leftMouseDown, .rightMouseDown]) { [weak self] _ in MainActor.assumeIsolated { self?.closePanel() } }
    }
    private func closePanel() {
        panel?.orderOut(nil)
        if let keyMonitor { NSEvent.removeMonitor(keyMonitor); self.keyMonitor = nil }
        if let outsideMonitor { NSEvent.removeMonitor(outsideMonitor); self.outsideMonitor = nil }
        panelModel.clearSession()
    }
    private func showMarker(snapshot: SelectionSnapshot, result: RewriteResult) {
        guard panel?.isVisible != true, let bounds = snapshot.bounds, let screen = NSScreen.screens.first(where: { $0.frame.intersects(bounds) }) else { return }
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
    private func snapshot(to directory: String) {
        Task { @MainActor in
            do {
                try FileManager.default.createDirectory(atPath: directory, withIntermediateDirectories: true)
                // Widest footer: Fix sentence, This word, the name button and Ignore must all fit the 340 pt card. Needs no engine.
                let nameSource = "i met Aman Jain yestarday."
                let nameEdits = [WritingEdit(start: 6, end: 10, replacement: "Amen", original: "Aman", category: "Spelling", ruleID: "spelling", explanation: "Possible misspelling."), WritingEdit(start: 16, end: 25, replacement: "yesterday", original: "yestarday", category: "Spelling", ruleID: "spelling", explanation: "Possible misspelling.")]
                try render(InlineCorrection(edit: nameEdits[0], source: nameSource, edits: nameEdits, canApply: true, apply: {}, applySentence: {}, ignore: {}, close: {}), size: InlineCorrection.size, to: URL(fileURLWithPath: directory).appendingPathComponent("name-card.png"))
                studioModel.engineReady = true; studioModel.playground("I recieved your mesage.\n\nCan you chek this?", debounce: true)
                for _ in 0..<300 where studioModel.busy { try await Task.sleep(for: .milliseconds(50)) }
                guard !studioModel.busy, studioModel.chosenEdits.count == 3 else { throw ParzrError.message("The snapshot's real draft check did not complete.") }
                try render(StudioView(model: studioModel, renderingSnapshot: true), size: NSSize(width: 920, height: 680), to: URL(fileURLWithPath: directory).appendingPathComponent("playground.png"))
                if let edit = studioModel.chosenEdits.first { try render(InlineCorrection(edit: edit, source: studioModel.source, edits: studioModel.chosenEdits, canApply: true, apply: {}, applySentence: {}, ignore: {}, close: {}), size: InlineCorrection.size, to: URL(fileURLWithPath: directory).appendingPathComponent("draft-card.png")) }
                panelModel.engineReady = true; panelModel.playground("i hope your doing well. can you chek this once?")
                for _ in 0..<300 where panelModel.busy { try await Task.sleep(for: .milliseconds(50)) }
                guard !panelModel.busy, !panelModel.chosenEdits.isEmpty else { throw ParzrError.message("The snapshot's real passage check did not complete.") }
                try render(RewritePanel(model: panelModel), size: RewritePanel.size, to: URL(fileURLWithPath: directory).appendingPathComponent("rewrite.png"))
                try render(RewritePanel(model: panelModel, showsModes: false), size: RewritePanel.size, to: URL(fileURLWithPath: directory).appendingPathComponent("inline.png"))
                for route in [StudioRoute.general, .writing, .appearance, .privacy, .about] {
                    try render(StudioView(model: studioModel, route: route, renderingSnapshot: true), size: NSSize(width: 920, height: 680), to: URL(fileURLWithPath: directory).appendingPathComponent("\(route.rawValue.lowercased()).png"))
                }
                try render(StudioView(model: studioModel, route: .writing, renderingSnapshot: true), size: NSSize(width: 920, height: 1240), to: URL(fileURLWithPath: directory).appendingPathComponent("writing-tall.png"))
                try render(StatusPopover(engineReady: true, sourceApp: nil, check: {}, editor: {}, settings: {}, about: {}, welcome: {}, quit: {}), size: NSSize(width: 318, height: 334), to: URL(fileURLWithPath: directory).appendingPathComponent("menu.png"))
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
    private func runUIControlsTest(directory: String) async throws {
        guard !IsSecureEventInputEnabled() else { throw ParzrError.message("UI QA stopped while secure input is active.") }
        let target = URL(fileURLWithPath: directory)
        try FileManager.default.createDirectory(at: target, withIntermediateDirectories: true)
        showStudio(route: .playground)
        guard let studio, let host = studio.contentView else { throw ParzrError.message("The editor window did not open.") }
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
        for _ in 0..<80 { try await Task.sleep(for: .milliseconds(50)); if !studioModel.busy && studioModel.source == sampleSource { break } }
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
        _ = applicationShouldHandleReopen(NSApp, hasVisibleWindows: false)
        guard studio.isVisible else { throw ParzrError.message("Reopening did not restore the closed window.") }
        let reviewStatusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.squareLength)
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
        let report: [String: Any] = ["sample_button": true, "apply_all_button": true, "copy_button": true, "settings_button": true, "done_button": true, "clear_session_button": true, "draft_native_undo": true, "menu_settings_action": true, "status_panel_settings": true, "status_panel_about": true, "status_panel_editor": true, "reopen_visible": true, "reopen_minimized": true, "reopen_closed": true, "status": "passed"]
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
