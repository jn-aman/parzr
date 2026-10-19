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
