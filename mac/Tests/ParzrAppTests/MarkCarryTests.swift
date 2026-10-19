import XCTest
import ParzrCore
@testable import Parzr

/// Marks carried over typing in another app's editor (pure: no AX, windows or engine).
final class MarkCarryTests: XCTestCase {
    /// Two paragraphs; the second is the one checked, with "recieved" and "mesage" flagged.
    private let old = "Hello there.\nI recieved your mesage.\nBye."
    private var paragraph: NSRange { NSRange(location: 13, length: 24) }
    private var edits: [WritingEdit] { [WritingEdit(start: 2, end: 10, replacement: "received", original: "recieved"), WritingEdit(start: 16, end: 22, replacement: "message", original: "mesage")] }
    private func carry(to new: String, breaks: [Int] = []) -> MarkCarry.Carried? { MarkCarry.remap(edits: edits, selection: paragraph, inlineBreaks: breaks, from: old, to: new) }
    private func spans(_ carried: MarkCarry.Carried?) -> [[Int]] { carried?.edits.map { [$0.start_utf16, $0.end_utf16] } ?? [] }

    func testTypingAfterTheMarksKeepsThemWhereTheyAre() throws {
        let carried = try XCTUnwrap(carry(to: "Hello there.\nI recieved your mesage. Thanks\nBye."))
        XCTAssertEqual(carried.selection, NSRange(location: 13, length: 31), "the paragraph grows with the typing")
        XCTAssertEqual(spans(carried), [[2, 10], [16, 22]])
    }
    func testTypingBetweenMarksShiftsOnlyTheLaterOne() {
        XCTAssertEqual(spans(carry(to: "Hello there.\nI recieved all your mesage.\nBye.")), [[2, 10], [20, 26]])
    }
    func testTypingInAnEarlierParagraphMovesTheParagraphAndKeepsLocalOffsets() throws {
        let carried = try XCTUnwrap(carry(to: "Hello there, friend.\nI recieved your mesage.\nBye."))
        XCTAssertEqual(carried.selection, NSRange(location: 21, length: 24))
        XCTAssertEqual(spans(carried), [[2, 10], [16, 22]])
    }
    func testTypingInALaterParagraphChangesNothing() throws {
        let carried = try XCTUnwrap(carry(to: "Hello there.\nI recieved your mesage.\nBye now."))
        XCTAssertEqual(carried.selection, paragraph)
        XCTAssertEqual(spans(carried), [[2, 10], [16, 22]])
    }
    func testEditingAFlaggedWordDropsOnlyThatMark() {
        XCTAssertEqual(spans(carry(to: "Hello there.\nI received your mesage.\nBye.")), [[16, 22]], "the fixed word loses its mark")
        XCTAssertEqual(spans(carry(to: "Hello there.\nI recieved your mesages.\nBye.")), [[2, 10]], "typing into the word drops its mark")
    }
    func testASpaceTypedRightAfterOrBeforeAFlaggedWordKeepsItsMark() {
        let after = MarkCarry.remap(edits: [WritingEdit(start: 0, end: 3, replacement: "the", original: "teh")], selection: NSRange(location: 0, length: 3), from: "teh", to: "teh ")
        XCTAssertEqual(spans(after), [[0, 3]])
        let before = MarkCarry.remap(edits: [WritingEdit(start: 0, end: 3, replacement: "the", original: "teh")], selection: NSRange(location: 0, length: 3), from: "teh", to: "I teh")
        XCTAssertEqual(spans(before), [[2, 5]])
        let letter = MarkCarry.remap(edits: [WritingEdit(start: 0, end: 3, replacement: "the", original: "teh")], selection: NSRange(location: 0, length: 3), from: "teh", to: "tehn")
        XCTAssertEqual(spans(letter), [], "a letter extends the word, so the mark goes")
    }
    func testAChangeAcrossTheParagraphEdgeCarriesNothing() {
        XCTAssertNil(carry(to: "Hello there! i recieved your mesage.\nBye."), "one change across the paragraph's start")
        XCTAssertNil(carry(to: "Hello there.\nI recieved your mesage. bye."), "one change across the paragraph's end")
        XCTAssertEqual(spans(carry(to: "Hello there.I recieved your mesage.\nBye.")), [[2, 10], [16, 22]], "deleting the break before it moves the paragraph whole")
        XCTAssertNil(carry(to: old), "unchanged text is not a carry")
    }
    func testEveryCarriedMarkStillReadsItsOriginalWords() throws {
        let new = "Hello there.\nOh, I recieved your mesage.\nBye."
        let carried = try XCTUnwrap(carry(to: new))
        let text = (new as NSString).substring(with: carried.selection) as NSString
        for edit in carried.edits { XCTAssertEqual(text.substring(with: edit.range), edit.original) }
    }
    func testInlineImageBreaksMoveWithTheTextAndAnEditedBreakStopsTheCarry() throws {
        let carried = try XCTUnwrap(carry(to: "Hello there, hi.\nI recieved your mesage.\nBye.", breaks: [23]))
        XCTAssertEqual(carried.inlineBreaks, [27])
        XCTAssertNil(carry(to: "Hello there.\nI recieved yur mesage.\nBye.", breaks: [25]))
    }
}
