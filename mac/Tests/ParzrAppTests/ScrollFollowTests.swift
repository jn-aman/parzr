import XCTest
@testable import Parzr

/// Marks that ride along with a scroll (pure geometry; no windows are shown and no editor is read).
final class ScrollFollowTests: XCTestCase {
    private let probe = CGRect(x: 100, y: 500, width: 60, height: 16)
    private let screen = CGRect(x: 0, y: 0, width: 1440, height: 900)

    func testTheOffsetIsHowFarTheProbeMarkMoved() {
        XCTAssertEqual(ScrollFollow.offset(from: probe, to: probe.offsetBy(dx: 0, dy: 120)), CGPoint(x: 0, y: 120))
        XCTAssertEqual(ScrollFollow.offset(from: probe, to: probe.offsetBy(dx: -30, dy: -8)), CGPoint(x: -30, y: -8))
        XCTAssertEqual(ScrollFollow.offset(from: probe, to: probe), .zero)
    }
    func testAnUnmeasurableOrReflowedProbeGivesNoOffset() {
        XCTAssertNil(ScrollFollow.offset(from: probe, to: nil), "the editor did not answer: hide instead")
        XCTAssertNil(ScrollFollow.offset(from: probe, to: CGRect(x: 100, y: 500, width: 0, height: 16)))
        XCTAssertNil(ScrollFollow.offset(from: probe, to: CGRect(x: 0, y: 480, width: 900, height: 36)), "the word now wraps: re-place rather than slide")
    }
    func testAWindowOfMarksMovesAndIsClippedToTheScrollArea() {
        let base = CGRect(x: 90, y: 400, width: 300, height: 140)
        let area = CGRect(x: 80, y: 300, width: 600, height: 300)
        XCTAssertEqual(ScrollFollow.frame(base: base, offset: CGPoint(x: 0, y: 40), clip: area, screen: screen), CGRect(x: 90, y: 440, width: 300, height: 140))
        XCTAssertEqual(ScrollFollow.frame(base: base, offset: CGPoint(x: 0, y: 100), clip: area, screen: screen), CGRect(x: 90, y: 500, width: 300, height: 100), "the part scrolled past the top is cut")
        XCTAssertNil(ScrollFollow.frame(base: base, offset: CGPoint(x: 0, y: 400), clip: area, screen: screen), "scrolled out of view: nothing left to show")
        XCTAssertEqual(ScrollFollow.frame(base: base, offset: CGPoint(x: 0, y: 450), clip: nil, screen: screen), CGRect(x: 90, y: 850, width: 300, height: 50), "no scroll area: still kept on its screen")
    }
    func testMarksDrawnInGlobalCoordinatesAppearMovedByTheOffset() {
        // A layer at global point P shows at window-local P - contentOrigin; after following it must sit at P + offset on screen.
        let window = CGPoint(x: 90, y: 500), offset = CGPoint(x: 0, y: 100), mark = CGPoint(x: 100, y: 420)
        let origin = ScrollFollow.contentOrigin(window: window, offset: offset)
        let local = CGPoint(x: mark.x - origin.x, y: mark.y - origin.y)
        XCTAssertEqual(CGPoint(x: window.x + local.x, y: window.y + local.y), CGPoint(x: 100, y: 520))
    }
}
