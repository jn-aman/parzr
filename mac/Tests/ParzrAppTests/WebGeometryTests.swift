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
}
