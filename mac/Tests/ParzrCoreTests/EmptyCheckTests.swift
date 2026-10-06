import XCTest
@testable import ParzrCore

final class EmptyCheckTests: XCTestCase {
    func testFixSaysNothingToChangeAndPointsAtTheTones() {
        let empty = EmptyCheck(mode: .fix)
        XCTAssertEqual(empty.title, "Looks good")
        XCTAssertEqual(empty.detail, "No grammar or spelling changes in this selection.")
        XCTAssertTrue(empty.hint.contains("tone"))
        XCTAssertFalse(empty.warning)
    }
    func testEveryToneNamesItselfAndSuggestsAnotherTone() {
        for mode in RewriteMode.allCases where mode != .fix {
            let empty = EmptyCheck(mode: mode)
            XCTAssertEqual(empty.title, "Already reads well in \(mode.title)")
            XCTAssertEqual(empty.detail, "No changes suggested.")
            XCTAssertEqual(empty.hint, "Try another tone above.")
        }
    }
    func testAnEngineWarningIsShownInsteadOfALooksGoodClaim() {
        let empty = EmptyCheck(mode: .fix, status: "Context refinement is unavailable.")
        XCTAssertEqual(empty.title, "No changes found")
        XCTAssertEqual(empty.detail, "Context refinement is unavailable.")
        XCTAssertTrue(empty.warning)
    }
    func testEveryModeHasADistinctSummaryAndHelp() {
        let modes = RewriteMode.allCases
        XCTAssertEqual(Set(modes.map(\.summary)).count, modes.count)
        XCTAssertEqual(Set(modes.map(\.help)).count, modes.count)
        for mode in modes { XCTAssertFalse(mode.summary.isEmpty); XCTAssertFalse(mode.help.isEmpty) }
    }
}
