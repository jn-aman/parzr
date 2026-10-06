import XCTest
import AppKit
import SwiftUI
import ParzrCore
@testable import Parzr

/// The Option+Space path inside Parzr's own writing space (`--own-editor-test`), headless. Accessibility needs an on-screen, key window, so the snapshot is read from the writing space directly (as `SelectionSnapshot.capture` decides: only the view
/// with the writing-space identifier is readable); everything after it is the real flow: `openSelection`, the card model and its engine check, the card's key handling, the fix, Undo and the Studio's marks. The end-to-end Accessibility read and write stay in the flag.
final class OwnEditorWindowTests: OwnWindowCase {
    /// What `capture` does for Parzr's own process, without Accessibility.
    func snapshot(in window: NSWindow) throws -> SelectionSnapshot {
        let pid = ProcessInfo.processInfo.processIdentifier
        guard let editor = window.firstResponder as? NSTextView, Compat.allowsCapture(appPID: pid, ownPID: pid, identifier: editor.accessibilityIdentifier()) else { throw ParzrError.message("Select text in an editor, then press your Parzr shortcut.") }
        let range = editor.selectedRange(), full = editor.string
        guard range.length > 0 else { throw ParzrError.message("Select the words you want to improve, then try again.") }
        let text = (full as NSString).substring(with: range)
        return SelectionSnapshot(app: NSRunningApplication.current, element: AXUIElementCreateSystemWide(), selection: range, expectedSelection: range, text: text, fullText: full, bounds: editor.firstRect(forCharacterRange: range, actualRange: nil), richText: nil, copied: false, canPatch: true, docs: false, headlessEditor: editor)
    }
    func testShortcutInTheWritingSpaceChecksAppliesAndUndoes() async throws {
        try requireEngine()
        guard !NSScreen.screens.isEmpty else { throw XCTSkip("The card anchors to a screen.") }
        let app: AppDelegate = self.app, (window, host) = try openStudio()
        let editor = try await draft(in: window, host)
        XCTAssertEqual(editor.accessibilityIdentifier(), Compat.draftEditorIdentifier, "the writing space has no accessibility identifier")
        app.capture = { [unowned self] in try self.snapshot(in: window) }
        let studio = app.studioModel, card = app.panelModel
        func state() -> String { "draft \"\(editor.string)\", studio source \"\(studio.source)\", busy \(studio.busy), edits \(studio.chosenEdits.map(\.original)), error \(studio.error ?? "none"), card error \(card.error ?? "none")" }
        func marked(_ text: String) -> Bool { studio.source == editor.string && !studio.busy && studio.chosenEdits.contains { $0.replacement == text } }
        let original = "this os do bad."
        editor.insertText(original, replacementRange: NSRange(location: 0, length: editor.string.utf16.count))
        try await until("the Studio's own marks (\(state()))", seconds: 60) { marked("T") }

        // 1. Selected text: the card opens on it, anchored at the selection.
        editor.setSelectedRange(NSRange(location: 0, length: editor.string.utf16.count))
        app.openSelection()
        try await until("the card (\(state()), card error \(card.error ?? "none"))", seconds: 60) { card.snapshot != nil && !card.busy && !card.chosenEdits.isEmpty }
        let panel = try XCTUnwrap(app.panel, "no card was built")
        XCTAssertTrue(app.isShown(panel)); XCTAssertFalse(panel.isVisible, "the card must stay off screen")
        XCTAssertEqual(card.source, original, "the card shows the wrong text"); XCTAssertEqual(card.snapshot?.own, true)
        let bounds = try XCTUnwrap(card.snapshot?.bounds, "the selection has no bounds, so the card cannot anchor to it")
        let gap = min(abs(panel.frame.maxY - bounds.minY), abs(panel.frame.minY - bounds.maxY))
        XCTAssertLessThan(gap, 24, "the card is not anchored at the selection"); XCTAssertLessThanOrEqual(panel.frame.minX, bounds.maxX); XCTAssertGreaterThanOrEqual(panel.frame.maxX, bounds.minX)
        // The card's own content, laid out in its never-shown panel: it offers the whole fix.
        let content = try XCTUnwrap(panel.contentView); content.layoutSubtreeIfNeeded()
        XCTAssertNotNil(NativeControls.find(label: "Fix all corrections", in: content), "a selection card offers Fix all")

        // 2. Return applies to the editor (a key event sent to the card).
        try key(36, "\r", to: panel)
        try await until("the fix to land in the editor (\(state()))") { editor.string != original }
        let fixed = editor.string
        try await until("the card to close") { !app.isShown(panel) }
        XCTAssertTrue(fixed.hasPrefix("This"), "Return did not apply the fix and close the card: \"\(fixed)\"")
        try await until("the Studio's marks to refresh (\(state()))", seconds: 60) { studio.source == fixed && !studio.busy && studio.result != nil }
        XCTAssertFalse(marked("T"), "the stale capitalisation mark survived the fix")

        // 3. Undo reverts the whole fix, and the marks follow.
        window.makeFirstResponder(editor)
        editor.undoManager?.undo()
        XCTAssertEqual(editor.string, original, "Undo did not restore the original text")
        try await until("the marks to come back after Undo (\(state()))", seconds: 60) { marked("T") }

        // 4. No selection: the same hint as in any other app.
        editor.setSelectedRange(NSRange(location: 4, length: 0))
        app.openSelection()
        try await until("the hint") { card.selectionHint }
        XCTAssertNil(card.snapshot, "an empty selection produced a snapshot")
        app.closePanel()

        // 5. Outside the writing space Parzr still reads nothing of its own: no focus, and a text view without the identifier.
        let other = NSTextView(frame: NSRect(x: 0, y: 0, width: 100, height: 40)); other.string = "settings field"
        host.addSubview(other); defer { other.removeFromSuperview() }
        for responder in [nil, other] as [NSResponder?] {
            window.makeFirstResponder(responder)
            app.openSelection()
            try await until("the refusal") { card.error != nil }
            XCTAssertNil(card.snapshot); XCTAssertTrue(card.source.isEmpty, "Parzr read its own window outside the writing space")
            app.closePanel()
        }
    }
}
