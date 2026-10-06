import XCTest
import AppKit
@testable import Parzr

final class DocsTests: XCTestCase {
    func testDetectionNeedsADocumentPageAndZeroWidthTextIsHidden() {
        XCTAssertTrue(Compat.isGoogleDocsURL("https://docs.google.com/document/d/abc/edit?tab=t.0"))
        XCTAssertFalse(Compat.isGoogleDocsURL("https://docs.google.com/spreadsheets/d/abc/edit"), "Sheets is a different surface")
        XCTAssertFalse(Compat.isGoogleDocsURL("https://evil.example/docs.google.com/document/d/x"))
        XCTAssertFalse(Compat.isGoogleDocsURL("about:blank"))
        XCTAssertFalse(Compat.isGoogleDocsURL(nil))
        XCTAssertTrue(Compat.docsTextHidden("\u{200B}\u{200B}"), "braille support off: two zero-width characters")
        XCTAssertTrue(Compat.docsTextHidden(""))
        XCTAssertFalse(Compat.docsTextHidden("Hello"))
        XCTAssertFalse(Compat.docsTextHidden(nil), "unreadable is not the same as hidden")
    }
    func testSetupHintNeedsTypingInDocsWithNothingToRead() {
        let hidden = "\u{200B}\u{200B}"
        XCTAssertTrue(Compat.docsHintNeeded(isDocs: true, value: hidden, keystrokes: Compat.docsHintKeystrokes, dismissed: false))
        XCTAssertFalse(Compat.docsHintNeeded(isDocs: true, value: hidden, keystrokes: Compat.docsHintKeystrokes - 1, dismissed: false), "a few keys in an empty document are not enough")
        XCTAssertFalse(Compat.docsHintNeeded(isDocs: true, value: hidden, keystrokes: 20, dismissed: true), "Don't show again")
        XCTAssertFalse(Compat.docsHintNeeded(isDocs: true, value: "Typed text", keystrokes: 20, dismissed: false), "text is readable: nothing to set up")
        XCTAssertFalse(Compat.docsHintNeeded(isDocs: false, value: hidden, keystrokes: 20, dismissed: false))
    }
    func testDocsIsAlwaysTypedNeverWrittenThroughSelectedText() {
        XCTAssertEqual(ReplacePlan.first(textSettable: true, rangeSettable: true, docs: true), .typed, "Docs accepts the AXSelectedText write and ignores it")
        XCTAssertEqual(ReplacePlan.first(textSettable: true, rangeSettable: true, docs: false), .axText)
        XCTAssertNil(ReplacePlan.first(textSettable: true, rangeSettable: false, docs: true), "no settable selection, no patch")
    }
    func testRunsAlignToTheValueAcrossParagraphBreaks() {
        let value = "One two.\nThree four."
        XCTAssertEqual(DocsGeometry.offsets(runs: ["One ", "two", ".", "Three four."], in: value), [0, 4, 7, 9])
        XCTAssertNil(DocsGeometry.offsets(runs: ["One ", "tow"], in: value), "a run that is not in the value means no geometry")
        XCTAssertNil(DocsGeometry.offsets(runs: ["One two.", "Three four.", "extra"], in: value))
    }
    func testSelectionOffsetsSkipParagraphBreaks() {
        let value = "ab\ncd\n\nef" as NSString
        XCTAssertEqual(DocsGeometry.selectionIndex(valueIndex: 4, in: value), 3, "one break before 'd'")
        XCTAssertEqual(DocsGeometry.selectionIndex(valueIndex: 8, in: value), 5, "three breaks before the last letter")
        XCTAssertEqual(DocsGeometry.valueCandidates(selectionIndex: 1, in: value), [1])
        XCTAssertEqual(DocsGeometry.valueCandidates(selectionIndex: 2, in: value), [2, 3], "the end of 'ab' and the start of 'cd' read the same")
        XCTAssertEqual(DocsGeometry.valueCandidates(selectionIndex: 4, in: value), [5, 6, 7], "a blank paragraph adds a position")
        XCTAssertEqual(DocsGeometry.valueCandidates(selectionIndex: 5, in: value), [8])
        for index in [0, 1, 3, 4, 8] { XCTAssertTrue(DocsGeometry.valueCandidates(selectionIndex: DocsGeometry.selectionIndex(valueIndex: index, in: value), in: value).contains(index), "round trip \(index)") }
    }
    func testScreenRectsAreTheCaretPlusTheHiddenOffset() {
        let anchor = CGRect(x: 610, y: 532, width: 9, height: 17)      // hidden rect of the character under the caret
        let caret = CGPoint(x: 609, y: 533)                              // where the caret really is
        let sameLine = DocsGeometry.screen(CGRect(x: 700, y: 532, width: 30, height: 17), anchor: anchor, caret: caret)
        XCTAssertEqual(sameLine.minX, 699, accuracy: 0.01); XCTAssertEqual(sameLine.minY, 533, accuracy: 0.01)
        XCTAssertEqual(sameLine.width, 30); XCTAssertEqual(sameLine.height, 17)
        // Three hidden lines up (20 pt pitch) is three real lines up at the real, slightly smaller pitch.
        let up = DocsGeometry.screen(CGRect(x: 425, y: 472, width: 40, height: 17), anchor: anchor, caret: caret)
        XCTAssertEqual(up.minY, 533 - 60 * DocsGeometry.pitchScale, accuracy: 0.01)
        XCTAssertEqual(up.minX, 424, accuracy: 0.01)
    }
    func testTheCaretsXPicksTheAnchorAndRejectsAStaleOne() {
        let atEnd = (position: 10, rect: CGRect(x: 1030, y: 400, width: 0, height: 17))
        let atStart = (position: 11, rect: CGRect(x: 425, y: 420, width: 9, height: 17))
        XCTAssertEqual(DocsGeometry.nearest([atEnd, atStart], caretX: 426)?.position, 11)
        XCTAssertEqual(DocsGeometry.nearest([atEnd, atStart], caretX: 1031)?.position, 10, "end of a paragraph versus the start of the next")
        XCTAssertNil(DocsGeometry.nearest([atEnd, atStart], caretX: 700), "a caret that matches no character is stale")
        XCTAssertNil(DocsGeometry.nearest([], caretX: 1))
    }
    func testWrappedRunsMergeIntoOneRectPerLine() {
        let lines = DocsGeometry.lines([CGRect(x: 425, y: 100, width: 100, height: 17), CGRect(x: 525, y: 100, width: 60, height: 17), CGRect(x: 425, y: 119, width: 80, height: 17)])
        XCTAssertEqual(lines, [CGRect(x: 425, y: 100, width: 160, height: 17), CGRect(x: 425, y: 119, width: 80, height: 17)])
    }
}
