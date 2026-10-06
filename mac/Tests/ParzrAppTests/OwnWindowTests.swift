import XCTest
import AppKit
import SwiftUI
import ParzrCore
@testable import Parzr

@MainActor func find<T: NSView>(_ type: T.Type, in view: NSView) -> T? { (view as? T) ?? view.subviews.lazy.compactMap { find(type, in: $0) }.first }

/// Parzr's checks of its own windows (typing in the Studio, the shortcut inside the writing space, clicks on marks, the controls), run headless: every window is built and laid out but never ordered on screen,
/// events go to the window directly (`sendEvent`, `insertText`) and never through the window server, and nothing is activated. The old `--*-test` flags still do the same end to end on a real screen.
@MainActor
class OwnWindowCase: XCTestCase {
    var app: AppDelegate!
    var pasteboard: NSPasteboard!
    override func setUp() async throws {
        _ = NSApplication.shared
        app = AppDelegate(); app.showsWindows = false
        app.panelModel.dismiss = { [weak app] in app?.closePanel() }
        pasteboard = NSPasteboard.withUniqueName(); app.studioModel.pasteboard = pasteboard
        let prefs = Preferences.shared
        prefs.learnedNames = []; prefs.dictionary = []; prefs.showInDock = false; prefs.onboardingCompleted = true; prefs.checkingDelay = 90
    }
    override func tearDown() async throws {
        let visible = NSApp.windows.filter(\.isVisible)
        app.studio?.close(); app.onboarding?.close(); app.closePanel()
        pasteboard.releaseGlobally()
        XCTAssertTrue(visible.isEmpty, "a test window became visible: \(visible.map(\.title))")
    }
    func requireEngine() throws { guard ProcessInfo.processInfo.environment["PARZR_ENGINE_PATH"] != nil else { throw XCTSkip("Supply the built engine library.") } }
    func until(_ what: String, seconds: Double = 12, _ ok: @escaping @MainActor () -> Bool) async throws {
        let end = Date().addingTimeInterval(seconds)
        while !ok() {
            guard Date() < end else { XCTFail("Timed out waiting for \(what)"); throw CancellationError() }
            try await Task.sleep(for: .milliseconds(20))
            // SwiftUI applies state to an unshown window's views only when the window lays out (nothing displays it).
            for window in NSApp.windows { window.layoutIfNeeded(); window.contentView?.layoutSubtreeIfNeeded() }
        }
    }
    func openStudio(_ route: StudioRoute = .playground) throws -> (window: NSWindow, host: NSView) {
        app.studioModel.engineReady = true; app.showStudio(route: route)
        let window = try XCTUnwrap(app.studio), host = try XCTUnwrap(window.contentView)
        XCTAssertFalse(window.isVisible, "the studio must stay off screen")
        window.layoutIfNeeded(); host.layoutSubtreeIfNeeded()
        return (window, host)
    }
    /// The writing space of a window, set up the way a user's click would: focused, and its correction cards built but never shown.
    func draft(in window: NSWindow, _ host: NSView) async throws -> CorrectionTextView {
        try await until("the writing space") { find(CorrectionTextView.self, in: host) != nil }
        let editor = try XCTUnwrap(find(CorrectionTextView.self, in: host))
        editor.presentsPopover = false; window.makeFirstResponder(editor)
        return editor
    }
    /// A mouse press and release delivered straight to the view under the point, never through the window server (`NSWindow.sendEvent` drops mouse events for a window that is not on screen).
    func click(_ editor: NSView, at point: NSPoint, in window: NSWindow, serial: Int) {
        let location = editor.convert(point, to: nil)
        func event(_ type: NSEvent.EventType) -> NSEvent? { NSEvent.mouseEvent(with: type, location: location, modifierFlags: [], timestamp: ProcessInfo.processInfo.systemUptime, windowNumber: window.windowNumber, context: nil, eventNumber: serial, clickCount: 1, pressure: type == .leftMouseDown ? 1 : 0) }
        // NSTextView tracks the mouse inside mouseDown until the button is up, so the up event is queued first.
        if let up = event(.leftMouseUp) { NSApp.postEvent(up, atStart: false) }
        if let down = event(.leftMouseDown) { (window.contentView?.hitTest(down.locationInWindow) ?? editor).mouseDown(with: down) }
    }
    func key(_ code: UInt16, _ characters: String, to window: NSWindow) throws {
        let event = try XCTUnwrap(NSEvent.keyEvent(with: .keyDown, location: .zero, modifierFlags: [], timestamp: ProcessInfo.processInfo.systemUptime, windowNumber: window.windowNumber, context: nil, characters: characters, charactersIgnoringModifiers: characters, isARepeat: false, keyCode: code))
        NSApp.sendEvent(event)
    }
}

final class EditorTypingWindowTests: OwnWindowCase {
    /// Typing into the Studio writing space faster than the checking delay: the marks before the caret stay, nothing shows Checking, the buttons stay enabled, the text view is never rewritten and the caret never jumps.
    func testTypingKeepsMarksAndNeverFlickers() async throws {
        try requireEngine()
        let model = app.studioModel
        let (window, host) = try openStudio()
        let editor = try await draft(in: window, host)
        let layout = try XCTUnwrap(editor.layoutManager), storage = try XCTUnwrap(editor.textStorage)
        func type(_ text: String) { editor.insertText(text, replacementRange: editor.selectedRange()) }
        func settled(_ count: Int) async throws { try await until("a check with \(count) suggestions", seconds: 60) { !model.busy && model.result != nil && model.source == editor.string && model.chosenEdits.count >= count } }
        type("I recieved your mesage. "); try await settled(2)
        func marksPresent() -> Bool { ["recieved", "mesage"].allSatisfy { layout.temporaryAttribute(.underlineStyle, atCharacterIndex: (editor.string as NSString).range(of: $0).location, effectiveRange: nil) != nil } }
        XCTAssertTrue(marksPresent(), "the baseline marks are not drawn")
        var edits = 0
        nonisolated(unsafe) let watched = storage
        let observer = NotificationCenter.default.addObserver(forName: NSTextStorage.didProcessEditingNotification, object: watched, queue: .main) { _ in MainActor.assumeIsolated { if watched.editedMask.contains(.editedCharacters) { edits += 1 } } }
        defer { NotificationCenter.default.removeObserver(observer) }
        var samples = 0, missingMarks = 0, busy = 0, checkDisabled = 0, copyDisabled = 0
        let check = NativeControls.find(label: "Check passage", in: host), copy = NativeControls.find(label: "Copy", in: host)
        XCTAssertNotNil(check); XCTAssertNotNil(copy)
        let sampler = Task { @MainActor in
            while !Task.isCancelled {
                samples += 1
                if !marksPresent() { missingMarks += 1 }
                if model.busy { busy += 1 }
                if check?.isAccessibilityEnabled() == false { checkDisabled += 1 }
                if copy?.isAccessibilityEnabled() == false { copyDisabled += 1 }
                try? await Task.sleep(for: .milliseconds(4))
            }
        }
        let typed = "Can you chek this and tel me?", expected = "Hi! " + editor.string + typed
        var frame = 1, caretMoved = 0
        let delays = [70, 110, 60, 140, 90] // realistic cadence, mostly inside the checking delay
        for character in typed {
            type(String(character))
            if editor.selectedRange().location != editor.string.utf16.count { caretMoved += 1 }
            try await Task.sleep(for: .milliseconds(delays[frame % delays.count])); frame += 1
        }
        // Typing in front of the marks moves them; they must travel with the text.
        editor.setSelectedRange(NSRange(location: 0, length: 0))
        for character in "Hi! " { type(String(character)); try await Task.sleep(for: .milliseconds(delays[frame % delays.count])); frame += 1 }
        sampler.cancel()
        let rewrites = edits - typed.count - 4
        try await settled(2)
        XCTAssertGreaterThan(samples, 100, "the sampler barely ran")
        XCTAssertEqual(editor.string, expected); XCTAssertEqual(caretMoved, 0, "the caret moved while typing"); XCTAssertEqual(rewrites, 0, "the text view was rewritten")
        XCTAssertEqual(missingMarks, 0, "marks vanished while typing"); XCTAssertEqual(busy, 0, "Checking showed while typing")
        XCTAssertEqual(checkDisabled, 0, "Check passage was disabled while typing"); XCTAssertEqual(copyDisabled, 0, "Copy was disabled while typing")
    }
}
