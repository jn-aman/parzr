import XCTest
import AppKit
import SwiftUI
import ParzrCore
@testable import Parzr

/// `--ui-test`, headless: the controls are pressed as accessibility actions on windows that are never shown, the menu actions run through `NSApp.sendAction`, and the Dock policy is checked as the decision the app would apply
/// (`AppDelegate.policy`) instead of flipping the real one. Only what needs a real screen stays in the flag: `NSWorkspace.menuBarOwningApplication` taking the menu bar, the real `activationPolicy()`, and a miniaturized window coming back.
final class UIControlsWindowTests: OwnWindowCase {
    func press(_ label: String, in host: NSView, file: StaticString = #filePath, line: UInt = #line) throws {
        let control = try XCTUnwrap(NativeControls.find(label: label, in: host), "no \"\(label)\" button", file: file, line: line)
        XCTAssertTrue(control.accessibilityPerformPress(), "the \"\(label)\" button did not activate", file: file, line: line)
    }
    /// What AppKit tells the delegate when a window closes. A window that was never on screen only reports it the first time (`close()` is then a no-op), so a second close is sent by hand.
    func close(_ window: NSWindow?) { app.windowWillClose(Notification(name: NSWindow.willCloseNotification, object: window)) }
    func testActivationPolicyDecision() {
        XCTAssertEqual(ActivationPolicy.decide(showInDock: false, windowOpen: false), .accessory, "menu-bar-only when nothing is open")
        XCTAssertEqual(ActivationPolicy.decide(showInDock: false, windowOpen: true), .regular, "an open window gives the app its menus and menu bar")
        XCTAssertEqual(ActivationPolicy.decide(showInDock: true, windowOpen: false), .regular)
        XCTAssertEqual(ActivationPolicy.decide(showInDock: true, windowOpen: true), .regular)
    }
    /// Show in Dock off: opening the editor makes the app regular and gives it its menus, closing the last window returns it to menu-bar-only, reopening brings both back.
    func testAnOpenWindowGivesMenusAndClosingTheLastReturnsToMenuBarOnly() throws {
        Preferences.shared.showInDock = false
        XCTAssertEqual(app.policy, .accessory, "the test did not start menu-bar-only")
        app.showStudio(route: .playground)
        let studio = try XCTUnwrap(app.studio)
        XCTAssertEqual(app.policy, .regular, "opening the editor with Show in Dock off did not make the app regular")
        XCTAssertTrue(app.makeMenu().items.map(\.title).contains("Window"), "no Window menu for an open Parzr window")
        XCTAssertTrue(app.isShown(studio)); XCTAssertFalse(studio.isVisible, "the editor must stay off screen")
        studio.close()
        XCTAssertEqual(app.policy, .accessory, "closing the editor with Show in Dock off did not return Parzr to the menu bar")
        XCTAssertFalse(app.isShown(studio))
        XCTAssertTrue(app.applicationShouldHandleReopen(NSApp, hasVisibleWindows: false))
        XCTAssertEqual(app.policy, .regular, "reopening the editor did not bring back Parzr's menus")
        XCTAssertTrue(app.isShown(app.studio), "reopening did not restore the closed window")
        // A second window keeps the app regular until the last one closes; Show in Dock on keeps it regular always.
        app.showOnboarding(step: .welcome)
        let welcome = try XCTUnwrap(app.onboarding)
        close(app.studio); XCTAssertEqual(app.policy, .regular, "the welcome window is still open")
        close(welcome); XCTAssertEqual(app.policy, .accessory)
        Preferences.shared.showInDock = true
        app.showStudio(route: .playground); close(app.studio)
        XCTAssertEqual(app.policy, .regular, "Show in Dock keeps the Dock icon")
    }
    /// Setup is mandatory: before Start writing, the Dock, menus, popover and shortcut lead to the welcome guide, closing it is refused and does not count as finishing, and nothing checks text.
    func testSetupIsMandatoryUntilStartWriting() throws {
        let prefs = Preferences.shared
        prefs.onboardingCompleted = false; defer { prefs.onboardingCompleted = true }
        XCTAssertFalse(prefs.setupFinished)
        XCTAssertTrue(app.applicationShouldHandleReopen(NSApp, hasVisibleWindows: false))
        let welcome = try XCTUnwrap(app.onboarding, "reopening before setup did not open the welcome guide")
        XCTAssertNil(app.studio, "the Studio opened before setup was finished")
        app.openSelection(); XCTAssertNil(app.panel, "the shortcut opened the card before setup was finished")
        let menu = NSMenu(); app.menuNeedsUpdate(menu)
        XCTAssertEqual(menu.items.filter { !$0.isSeparatorItem }.map(\.title), ["Finish setting up Parzr…", "Quit Parzr"])
        XCTAssertFalse(app.windowShouldClose(welcome), "the close button closed the welcome guide before setup was finished")
        close(welcome)
        XCTAssertFalse(prefs.onboardingCompleted, "closing the welcome guide marked setup finished")
        app.showOnboarding(step: .done)
        let model = try XCTUnwrap(app.onboardingModel); model.complete()
        XCTAssertTrue(prefs.setupFinished)
        XCTAssertTrue(app.windowShouldClose(try XCTUnwrap(app.onboarding)), "a finished setup could not close the welcome guide")
        close(app.onboarding)
        XCTAssertTrue(app.applicationShouldHandleReopen(NSApp, hasVisibleWindows: false)); XCTAssertNotNil(app.studio)
    }
    func testMenuSettingsActionAndReopenShowTheWindow() throws {
        app.showStudio(route: .playground)
        let menu = NSMenu(); app.menuNeedsUpdate(menu)
        let settings = try XCTUnwrap(menu.items.first { $0.title == "Settings…" }), action = try XCTUnwrap(settings.action)
        XCTAssertTrue(NSApp.sendAction(action, to: settings.target, from: settings))
        XCTAssertEqual(app.studioModel.studioRoute, .general, "the menu Settings action did not open settings")
        XCTAssertTrue(app.applicationShouldHandleReopen(NSApp, hasVisibleWindows: true))
        XCTAssertTrue(app.isShown(app.studio), "reopening did not bring the window forward")
    }
    /// The menu-bar popover's buttons, in the same view the popover shows, mounted in a window that is never shown.
    func testStatusPopoverButtonsOpenTheirDestinations() async throws {
        let host = NSHostingView(rootView: app.statusPopoverView())
        let window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 318, height: 420), styleMask: [.borderless], backing: .buffered, defer: false)
        window.isReleasedWhenClosed = false; window.contentView = host; window.layoutIfNeeded(); host.layoutSubtreeIfNeeded()
        defer { window.close() }
        try await Task.sleep(for: .milliseconds(100))
        for (label, route) in [("Settings", StudioRoute.general), ("About Parzr", .about), ("Open Parzr", .playground)] {
            try press(label, in: host)
            XCTAssertEqual(app.studioModel.studioRoute, route, "the menu-panel \(label) button did not open its destination")
        }
        XCTAssertNotNil(NativeControls.find(label: "Quit Parzr", in: host), "the menu panel has no Quit button")   // found, never pressed
        XCTAssertNil(NativeControls.find(label: "Welcome and permissions", in: host), "setup is mandatory; the menu panel no longer reopens it")
    }
    /// Sample, Apply all, native Undo, Copy, Settings, Done and Clear session on the Studio's own window.
    func testStudioControlsWork() async throws {
        try requireEngine()
        let model = app.studioModel
        let (window, host) = try openStudio()
        let draft = try await draft(in: window, host)
        let sampleSource = "I recieved your mesage.\n\nCan you chek this?", fixedSource = "I received your message.\n\nCan you check this?"
        try await until("the sample button") { NativeControls.find(label: "Try a sample", in: host) != nil }
        try press("Try a sample", in: host)
        try await until("the sample check (\(model.source), busy \(model.busy), \(model.chosenEdits.count) edits)", seconds: 60) { !model.busy && model.source == sampleSource && model.chosenEdits.count == 3 }
        // The authored sample is the fixture baseline: Undo history starts here.
        draft.breakUndoCoalescing(); draft.undoManager?.removeAllActions()
        try await until("Apply all to be enabled") { NativeControls.find(label: "Apply all", in: host)?.isAccessibilityEnabled() == true }
        try press("Apply all", in: host)
        try await until("Apply all to update the draft (\(model.source), \(draft.string))", seconds: 60) { !model.busy && model.source == fixedSource && draft.string == fixedSource }
        XCTAssertTrue(draft.undoManager?.canUndo == true, "Apply all did not preserve native Undo")
        draft.undoManager?.undo()
        try await until("Undo to restore the draft (\(model.source), draft \(draft.string))", seconds: 60) { !model.busy && !model.provisional && model.source == sampleSource }
        draft.setSelectedRange(NSRange(location: 0, length: 0))
        // Copy uses the corrected draft; the test's pasteboard is private, never the owner's.
        try await until("the check before Copy", seconds: 60) { model.result != nil && !model.busy }
        try press("Copy", in: host)
        XCTAssertEqual(pasteboard.string(forType: .string), fixedSource, "Copy did not use the corrected draft")
        // Settings, then back.
        try press("Settings", in: host)
        XCTAssertEqual(model.studioRoute, .general, "the Settings button did not open settings")
        try await until("the Settings page") { NativeControls.find(label: "Return to editor", in: host) != nil }
        XCTAssertNotNil(NativeControls.find(label: "Quit Parzr", in: host), "Settings has no Quit Parzr button")   // found, never pressed
        try press("Return to editor", in: host)
        XCTAssertEqual(model.studioRoute, .playground, "the Done button did not return to the editor")
        // Privacy: clearing the session leaves no text and no Undo history.
        model.studioRoute = .privacy
        try await until("the Privacy page") { NativeControls.find(label: "Clear this writing session", in: host) != nil }
        try press("Clear this writing session", in: host)
        model.studioRoute = .playground
        try await until("the editor to come back empty") { find(CorrectionTextView.self, in: host).map { $0.string.isEmpty && $0.undoManager?.canUndo != true } == true }
        XCTAssertTrue(model.source.isEmpty, "session clear left text behind")
    }
}
