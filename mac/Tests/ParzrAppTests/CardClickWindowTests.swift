import XCTest
import AppKit
import SwiftUI
import ParzrCore
@testable import Parzr

/// The click regression of `--click-test`, headless: real mouse down and up events go to the view under the point on a Studio and an onboarding window that are never shown.
final class CardClickWindowTests: OwnWindowCase {
    /// Mounts a mark's card (built, never shown) in a window of its own that is never shown, so its layout and buttons can be inspected.
    func mount(_ card: NSView) -> NSWindow {
        let window = NSWindow(contentRect: NSRect(origin: .zero, size: InlineCorrection.size), styleMask: [.borderless], backing: .buffered, defer: false)
        window.isReleasedWhenClosed = false; window.contentView = card; window.layoutIfNeeded()
        return window
    }
    func box(of edit: WritingEdit, in editor: CorrectionTextView) -> NSRect? {
        guard let layout = editor.layoutManager, let container = editor.textContainer, let range = editor.displayRange(for: edit) else { return nil }
        return layout.boundingRect(forGlyphRange: layout.glyphRange(forCharacterRange: range, actualCharacterRange: nil), in: container).offsetBy(dx: editor.textContainerOrigin.x, dy: editor.textContainerOrigin.y)
    }
    /// Clicks each mark of `editor` at the middle, near the underline and near its left edge; the card must open for exactly that edit. Then clicks outside every word (nothing may open), applies one fix and probes the rest again.
    func probe(_ editor: CorrectionTextView, in window: NSWindow, surface: String, expecting: Int) async throws {
        var serial = 0, probes = 0
        func press(_ point: NSPoint) async throws {
            // The caret starts at the end of the text: a delivered click always moves it, so a click that never reached the view cannot pass as "nothing opened".
            serial += 1; editor.setSelectedRange(NSRange(location: editor.string.utf16.count, length: 0))
            click(editor, at: point, in: window, serial: serial)
            XCTAssertNotEqual(editor.selectedRange().location, editor.string.utf16.count, "\(surface): the click at \(point) never reached the writing space")
            try await Task.sleep(for: .milliseconds(30))
        }
        func probeAll(_ stage: String) async throws {
            for edit in editor.suggestions {
                guard let box = box(of: edit, in: editor) else { continue }
                for (name, point) in [("middle", NSPoint(x: box.midX, y: box.midY)), ("underline", NSPoint(x: box.midX, y: box.maxY - 3)), ("left edge", NSPoint(x: box.minX + 1.5, y: box.midY))] {
                    probes += 1
                    try await press(point)
                    XCTAssertEqual(editor.shownCorrection, edit, "\(surface) \(stage): clicking the \(name) of \"\(edit.original)\" at \(point) (box \(box)) did not open its card (shown: \(editor.shownCorrection?.original ?? "none"), caret \(editor.selectedRange().location))")
                    if name == "middle", let card = editor.correctionView {
                        let cardWindow = mount(card)
                        XCTAssertNotNil(NativeControls.find(label: "Apply correction: \(edit.replacementLabel)", in: card), "\(surface) \(stage): the card for \"\(edit.original)\" has no apply button")
                        cardWindow.contentView = nil; cardWindow.close()
                    }
                    editor.dismissCorrection()
                }
            }
        }
        try await until("\(surface): \(expecting) marks (\(editor.suggestions.count) drawn)", seconds: 60) { editor.suggestions.count >= expecting }
        try await probeAll("fresh")
        // Outside a word nothing may open: the space after it, and the margin above its line.
        let word = try XCTUnwrap(editor.suggestions.first { $0.original.first?.isLetter == true && $0.original.count > 1 }), area = try XCTUnwrap(box(of: word, in: editor))
        for (name, point) in [("space after", NSPoint(x: area.maxX + 2, y: area.midY)), ("margin above", NSPoint(x: area.midX, y: area.minY - 6))] {
            probes += 1
            try await press(point)
            XCTAssertNil(editor.shownCorrection, "\(surface): clicking the \(name) \"\(word.original)\" opened a card for \"\(editor.shownCorrection?.original ?? "")\"")
            editor.dismissCorrection()
        }
        // After one fix is applied the remaining marks must still open their cards.
        let first = try XCTUnwrap(editor.suggestions.last), before = editor.suggestions.count
        editor.accept(first)
        try await until("\(surface): the fix to land", seconds: 60) { !editor.string.contains(first.original) }
        // The re-check may find a different number of marks; whichever it draws must open.
        for _ in 0..<160 where editor.suggestions.count != before - 1 { try await Task.sleep(for: .milliseconds(50)) }
        try await Task.sleep(for: .milliseconds(300))
        XCTAssertFalse(editor.suggestions.isEmpty, "\(surface): no marks left after the fix")
        try await probeAll("after-apply")
        XCTAssertGreaterThan(probes, 10, "\(surface): too few probes ran")
    }
    /// No engine needed: a marked word at the end of a line, with blank space beside and below it. The nearest glyph there is the marked word, so only the hit rectangle keeps these clicks from opening a card.
    func testBlankSpaceBesideAndBelowAMarkedWordOpensNothing() async throws {
        let window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 480, height: 240), styleMask: [.borderless], backing: .buffered, defer: false)
        window.isReleasedWhenClosed = false
        let editor = CorrectionTextView(frame: NSRect(x: 0, y: 0, width: 480, height: 240))
        editor.isRichText = false; editor.allowsUndo = true; editor.textContainerInset = NSSize(width: 18, height: 18); editor.string = "Please chek"
        editor.presentsPopover = false; window.contentView = editor; window.makeFirstResponder(editor)
        defer { window.close() }
        let edit = WritingEdit(start: 7, end: 11, replacement: "check", original: "chek")
        editor.suggestions = [edit]
        let area = try XCTUnwrap(box(of: edit, in: editor))
        for (name, point, opens) in [("middle", NSPoint(x: area.midX, y: area.midY), true), ("far right of the line", NSPoint(x: area.maxX + 150, y: area.midY), false), ("far below the last letter", NSPoint(x: area.maxX - 2, y: area.maxY + 120), false), ("margin above", NSPoint(x: area.midX, y: area.minY - 6), false)] {
            editor.setSelectedRange(NSRange(location: 0, length: 0))
            click(editor, at: point, in: window, serial: 1)
            XCTAssertEqual(editor.shownCorrection, opens ? edit : nil, "clicking the \(name) at \(point)")
            editor.dismissCorrection()
        }
    }
    func testStudioMarksOpenTheirCards() async throws {
        try requireEngine()
        let (window, host) = try openStudio()
        let editor = try await draft(in: window, host)
        editor.insertText("i recieved your mesage, can you chek it?", replacementRange: editor.selectedRange())
        try await probe(editor, in: window, surface: "studio", expecting: 2)
    }
    func testOnboardingTryItMarksOpenTheirCards() async throws {
        try requireEngine()
        app.showOnboarding(step: .tryIt)
        let window = try XCTUnwrap(app.onboarding), host = try XCTUnwrap(window.contentView)
        window.layoutIfNeeded(); host.layoutSubtreeIfNeeded()
        let editor = try await draft(in: window, host)
        try await probe(editor, in: window, surface: "onboarding", expecting: 2)
    }
    /// The card's own button, pressed as an accessibility action: the fix lands in the text and the whole fix undoes.
    func testCardButtonAppliesThroughNativeUndo() async throws {
        try requireEngine()
        let (window, host) = try openStudio()
        let editor = try await draft(in: window, host)
        let original = "i recieved your mesage."
        editor.insertText(original, replacementRange: editor.selectedRange())
        try await until("marks", seconds: 60) { editor.suggestions.count >= 2 }
        let edit = try XCTUnwrap(editor.suggestions.first { $0.original == "recieved" }), area = try XCTUnwrap(box(of: edit, in: editor))
        click(editor, at: NSPoint(x: area.midX, y: area.midY), in: window, serial: 1)
        try await Task.sleep(for: .milliseconds(30))
        XCTAssertEqual(editor.shownCorrection, edit)
        let card = try XCTUnwrap(editor.correctionView), cardWindow = mount(card)
        defer { cardWindow.contentView = nil; cardWindow.close() }
        let apply = try XCTUnwrap(NativeControls.find(label: "Apply correction: \(edit.replacementLabel)", in: card))
        XCTAssertTrue(apply.accessibilityPerformPress())
        XCTAssertTrue(editor.string.hasPrefix("i received"), editor.string)
        XCTAssertNil(editor.shownCorrection, "applying closes the card")
        editor.undoManager?.undo()
        XCTAssertEqual(editor.string, original)
    }
}
