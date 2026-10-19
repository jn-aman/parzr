import XCTest
@testable import Parzr

/// Post-replacement verification that tolerates what editors change on their own (pure: strings only).
final class TolerantVerifyTests: XCTestCase {
    private let before = "I recieved \"your\" mesage.\nThanks"
    private let expected = "I received \"your\" mesage.\nThanks"

    func testExactTextStillDecidesFirst() {
        XCTAssertEqual(ReplacePlan.verdict(before: before, after: expected, expected: expected), .applied)
        XCTAssertEqual(ReplacePlan.verdict(before: before, after: before, expected: expected), .unchanged)
        XCTAssertEqual(ReplacePlan.verdict(before: before, after: nil, expected: expected), .diverged)
        XCTAssertEqual(ReplacePlan.verdict(before: before, after: "I relieved \"your\" mesage.\nThanks", expected: expected), .diverged)
    }
    func testSmartQuotesAppliedByTheEditorStillCountAsApplied() {
        XCTAssertEqual(ReplacePlan.verdict(before: before, after: "I received \u{201C}your\u{201D} mesage.\nThanks", expected: expected), .applied)
        XCTAssertEqual(ReplacePlan.verdict(before: "It\u{2019}s teh one", after: "It's the one", expected: "It\u{2019}s the one"), .applied)
    }
    func testNoBreakSpacesLineBreaksAndTrailingBreaksAreTolerated() {
        XCTAssertEqual(ReplacePlan.verdict(before: before, after: "I received\u{00A0}\"your\" mesage.\r\nThanks", expected: expected), .applied)
        XCTAssertEqual(ReplacePlan.verdict(before: before, after: "I received \"your\" mesage.\u{2028}Thanks\n\n", expected: expected), .applied)
        XCTAssertEqual(ReplacePlan.verdict(before: before, after: "I received  \"your\"\u{202F}mesage.\nThanks", expected: expected), .applied)
    }
    func testAnEditorRestyleWithoutTheWriteIsStillUnchanged() {
        XCTAssertEqual(ReplacePlan.verdict(before: before, after: "I recieved \u{201C}your\u{201D} mesage.\nThanks", expected: expected), .unchanged,
                       "only unchanged may fall back to typing, and the replacement has not landed")
    }
    func testAQuoteOrSpacingFixMustLandExactly() {
        let quoteBefore = "He said \"hi\".", quoteFix = "He said \u{201C}hi\u{201D}."
        XCTAssertEqual(ReplacePlan.verdict(before: quoteBefore, after: quoteFix, expected: quoteFix), .applied)
        XCTAssertEqual(ReplacePlan.verdict(before: quoteBefore, after: "He said \u{201C}hi\".", expected: quoteFix), .diverged, "tolerance cannot tell this fix from no fix")
        XCTAssertEqual(ReplacePlan.verdict(before: "Two  spaces", after: "Two\u{00A0} spaces", expected: "Two spaces"), .diverged)
    }
    func testWhitespaceIsNotIgnoredInsideWords() {
        XCTAssertEqual(ReplacePlan.verdict(before: "alot of", after: "a lot of", expected: "alot of!"), .diverged)
        XCTAssertFalse(ReplacePlan.sameText("a lot", "alot"))
        XCTAssertTrue(ReplacePlan.sameText("it\u{2019}s fine\n", "it's fine"))
    }
    func testBetweenPatchesOnlyOffsetPreservingDifferencesAreAdopted() {
        XCTAssertEqual(ReplacePlan.adopt(expected, expected: expected), expected)
        let curled = "I received \u{201C}your\u{201D} mesage.\nThanks"
        XCTAssertEqual(ReplacePlan.adopt(curled, expected: expected), curled, "same length: every later offset still holds")
        XCTAssertNil(ReplacePlan.adopt("I received \"your\" mesage.\r\nThanks", expected: expected), "a CRLF moves every later offset")
        XCTAssertNil(ReplacePlan.adopt("I received \"your\" message.\nThanks", expected: expected), "a real change")
        XCTAssertNil(ReplacePlan.adopt(nil, expected: expected))
    }
}
