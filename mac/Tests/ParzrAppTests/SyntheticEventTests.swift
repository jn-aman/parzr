import XCTest
import AppKit
@testable import Parzr

/// Parzr's own key events are tagged and told apart from the writer's. Events are built, never posted.
@MainActor
final class SyntheticEventTests: XCTestCase {
    func testTypedReplacementEventsAreTagged() {
        for event in TypedReplacement.events(for: "received") + [.delete] {
            let keys = TypedReplacement.keyEvents(for: event)
            XCTAssertEqual(keys.count, 2, "a key down and a key up")
            XCTAssertTrue(keys.allSatisfy { SyntheticEvent.isParzr($0) })
            XCTAssertTrue(keys.allSatisfy { $0.flags.intersection([.maskCommand, .maskAlternate, .maskShift, .maskControl]).isEmpty })
        }
    }
    func testPasteAndCopyShortcutsAreTagged() throws {
        for code: CGKeyCode in [8, 9] {
            let (down, up) = try XCTUnwrap(ClipboardTransaction.shortcut(code))
            XCTAssertTrue(SyntheticEvent.isParzr(down) && SyntheticEvent.isParzr(up))
            XCTAssertTrue(down.flags.contains(.maskCommand))
        }
    }
    func testDocsCaretArrowsAreTaggedAndPlain() {
        for key: CGKeyCode in [123, 124] {
            let events = AX.docsArrow(key)
            XCTAssertEqual(events.count, 2, "a key down and a key up")
            XCTAssertTrue(events.allSatisfy { SyntheticEvent.isParzr($0) }, "Parzr's caret moves never count as the writer typing")
            XCTAssertTrue(events.allSatisfy { $0.flags.intersection([.maskCommand, .maskAlternate, .maskShift, .maskControl]).isEmpty })
            XCTAssertEqual(events.map { $0.getIntegerValueField(.keyboardEventKeycode) }, [Int64(key), Int64(key)])
        }
    }
    func testTypingStopsBetweenChunksWhenTheWriterMovesOn() {
        var reads = 0
        let focused = { reads += 1; return true }, elsewhere = { reads += 1; return false }
        XCTAssertNil(ReplacePlan.typingInterrupted(inFront: true, secureInput: false, focusMatches: focused))
        XCTAssertEqual(ReplacePlan.typingInterrupted(inFront: false, secureInput: false, focusMatches: focused), .editorNotInFront)
        XCTAssertEqual(ReplacePlan.typingInterrupted(inFront: true, secureInput: true, focusMatches: focused), .secureInput, "a password prompt opened mid-fix")
        XCTAssertEqual(ReplacePlan.typingInterrupted(inFront: true, secureInput: false, focusMatches: elsewhere), .focusElsewhere)
        reads = 0
        _ = ReplacePlan.typingInterrupted(inFront: false, secureInput: true, focusMatches: focused)
        XCTAssertEqual(reads, 0, "Accessibility is read only when the cheap checks pass")
    }
    func testTheWritersKeysAreNotParzrs() throws {
        let key = try XCTUnwrap(CGEvent(keyboardEventSource: nil, virtualKey: 0, keyDown: true))
        XCTAssertFalse(SyntheticEvent.isParzr(key))
        key.setIntegerValueField(.eventSourceUserData, value: 42)
        XCTAssertFalse(SyntheticEvent.isParzr(key), "another tool's tag is not Parzr's")
        XCTAssertFalse(SyntheticEvent.isParzr(nil))
    }
    func testTheTagSurvivesTheTripIntoAnAppKitEvent() throws {
        let key = try XCTUnwrap(TypedReplacement.keyEvents(for: .text(Array("a".utf16))).first)
        let event = try XCTUnwrap(NSEvent(cgEvent: key))
        XCTAssertTrue(SyntheticEvent.isParzr(event.cgEvent), "the key monitor reads it from the NSEvent it is given")
    }
}
