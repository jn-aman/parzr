import XCTest
@testable import Parzr

/// Values and runs as Chrome 149 and Electron 37 expose them for contenteditable composers (Slack, Teams, Gmail and Outlook shapes).
final class WebGeometryTests: XCTestCase {
    func testRunsAlignAcrossTheBreaksChromiumPutsAroundChipsAndImages() {
        let value = "Hey\n@Priya Shah\ni hope your doing well \n\n teh report is redy"
        let runs = ["Hey", "@Priya Shah", "i ", "hope", " your doing ", "well", " ", " teh ", "report", " is redy"]
        let starts = WebGeometry.offsets(runs: runs, in: value)
        XCTAssertEqual(starts.count, runs.count)
        for (run, start) in zip(runs, starts) { XCTAssertEqual((value as NSString).substring(with: NSRange(location: start, length: (run as NSString).length)), run) }
        XCTAssertEqual(starts[7], (value as NSString).range(of: " teh ").location)
    }
    func testBlockBreaksAndATrailingBreakAreGaps() {
        XCTAssertEqual(WebGeometry.offsets(runs: ["i hope your doing well.", "teh report is redy"], in: "i hope your doing well.\nteh report is redy"), [0, 24])
        XCTAssertEqual(WebGeometry.offsets(runs: ["i hope your doing well. teh report is redy"], in: "i hope your doing well. teh report is redy\n"), [0])
    }
    func testARunThatSkipsTextStopsTheAlignmentRatherThanGuessing() {
        // The second run is missing from the value: nothing after it is placed, so no word gets a wrong rect.
        XCTAssertEqual(WebGeometry.offsets(runs: ["one ", "lost", "two"], in: "one two three"), [0])
        // A short run must not match inside text that no run accounted for.
        XCTAssertEqual(WebGeometry.offsets(runs: ["a", "e"], in: "a hidden e"), [0])
        XCTAssertNil(WebGeometry.next("e", in: "a hidden e" as NSString, from: 1))
    }
    func testZeroWidthAndObjectReplacementCharactersAreGaps() {
        XCTAssertEqual(WebGeometry.offsets(runs: ["start", "end"], in: "start\u{FFFC}\u{200B}\u{FEFF} end"), [0, 9])
        XCTAssertTrue(WebGeometry.isGap(0x0A)); XCTAssertTrue(WebGeometry.isGap(0x20)); XCTAssertFalse(WebGeometry.isGap(0x61))
    }
    /// Chromium's value for "Hey @Priya Shah i hope your doing well <emoji> teh report is redy": the image reads as two line breaks.
    func testAnImageBreakInsideALineJoinsTheSentenceAroundIt() {
        let value = "Hey @Priya Shah i hope your doing well \n\n teh report is redy" as NSString
        let image = NSRange(location: 39, length: 2)
        XCTAssertEqual(value.substring(with: image), "\n\n")
        var asked: [NSRange] = []
        let caret = NSRange(location: value.length - 2, length: 0)
        let joined = WebGeometry.paragraph(around: caret, in: value) { asked.append($0); return $0 == image }
        XCTAssertEqual(joined.range, NSRange(location: 0, length: value.length))
        XCTAssertEqual(joined.inlineBreaks, [39, 40])
        XCTAssertEqual(asked, [image])
        XCTAssertEqual(WebGeometry.joining(value as String, origin: 0, breaks: joined.inlineBreaks), "Hey @Priya Shah i hope your doing well    teh report is redy")
        // From the other side of the image too.
        XCTAssertEqual(WebGeometry.paragraph(around: NSRange(location: 2, length: 0), in: value) { $0 == image }.range, NSRange(location: 0, length: value.length))
    }
    func testRealBreaksStillSeparateParagraphs() {
        // Enter (a new block) and Shift+Enter (a line break) move to the next line, so the caret's paragraph is exactly what paragraphRange gives.
        let value = "i hope your doing well\nteh report is redy" as NSString
        let caret = NSRange(location: 30, length: 0)
        let joined = WebGeometry.paragraph(around: caret, in: value) { _ in false }
        XCTAssertEqual(joined.range, value.paragraphRange(for: caret))
        XCTAssertEqual(joined.inlineBreaks, [])
        // An image on one line and a real break on the next: only the image joins.
        let mixed = "one \n\n two\nthree" as NSString
        let result = WebGeometry.paragraph(around: NSRange(location: 1, length: 0), in: mixed) { $0 == NSRange(location: 4, length: 2) }
        XCTAssertEqual(mixed.substring(with: result.range), "one \n\n two\n")
        XCTAssertEqual(result.inlineBreaks, [4, 5])
    }
}
