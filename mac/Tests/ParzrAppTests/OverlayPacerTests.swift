import XCTest
@testable import Parzr

final class OverlayPacerTests: XCTestCase {
    private func underline(_ x: CGFloat, w: CGFloat = 40, style: Bool = false) -> MarkShape { MarkShape(kind: .underline, rect: CGRect(x: x, y: 100, width: w, height: 16), style: style) }

    func testDiffKeepsUnchangedShapesAndOnlyTouchesTheRest() {
        let a = underline(10), b = underline(60), c = underline(110)
        let diff = MarkDiff.diff(old: [a, b], new: [b, c])
        XCTAssertEqual(diff.added, [c])
        XCTAssertEqual(diff.removed, [a])
        let same = MarkDiff.diff(old: [a, b], new: [a, b])
        XCTAssertTrue(same.added.isEmpty && same.removed.isEmpty)
    }
    func testDiffTreatsInkAndKindAsPartOfTheShape() {
        let red = underline(10), blue = underline(10, style: true)
        let wash = MarkShape(kind: .wash, rect: red.rect)
        let diff = MarkDiff.diff(old: [red], new: [blue, wash, wash])
        XCTAssertEqual(Set(diff.added), [blue, wash])
        XCTAssertEqual(diff.added.count, 2, "a repeated shape is added once")
        XCTAssertEqual(diff.removed, [red])
    }
    func testNarrowUnderlinesKeepA16PointClickArea() {
        let narrow = underline(10, w: 6)
        XCTAssertEqual(narrow.hit, CGRect(x: 10, y: 95, width: 16, height: 21))
        XCTAssertEqual(narrow.extent, narrow.hit)
        XCTAssertEqual(MarkShape(kind: .highlight, rect: narrow.rect).extent, narrow.rect)
    }

    func testAPauseInTypingChecksAfterAThirdOfTheCeiling() {
        var pacer = CheckPacer(ceiling: 90)
        XCTAssertEqual(pacer.key(at: 10, wordEnd: false), .restart(ms: 35))
        XCTAssertEqual(CheckPacer(ceiling: 700).quiet, 272.22222222222223, accuracy: 0.001)
        XCTAssertEqual(CheckPacer(ceiling: 40).quiet, 20, "never below 20 ms")
    }
    func testVeryFastBurstsWaitTheFullCeiling() {
        var pacer = CheckPacer(ceiling: 90)
        _ = pacer.key(at: 10, wordEnd: false)
        XCTAssertEqual(pacer.key(at: 10.05, wordEnd: false), .restart(ms: 90))
        XCTAssertEqual(pacer.key(at: 10.30, wordEnd: false), .restart(ms: 35))
    }
    func testOneKeystrokeMovesTheTimerOnce() {
        var pacer = CheckPacer(ceiling: 90)
        _ = pacer.key(at: 10, wordEnd: false)
        XCTAssertEqual(pacer.changed(at: 10.004), .keep, "value change of the same keystroke")
        XCTAssertEqual(pacer.changed(at: 10.006), .keep, "selection change of the same keystroke")
        XCTAssertEqual(pacer.changed(at: 11), .restart(ms: 35), "a change with no key behind it (paste, programmatic)")
    }
    func testSpaceAndPunctuationCheckAsSoonAsTheEditorReportsTheText() {
        var pacer = CheckPacer(ceiling: 90)
        XCTAssertEqual(pacer.key(at: 20, wordEnd: true), .restart(ms: 35), "fallback when the editor sends no notification")
        XCTAssertEqual(pacer.changed(at: 20.004), .restart(ms: 0))
        XCTAssertEqual(pacer.changed(at: 20.006), .keep)
        _ = pacer.key(at: 30, wordEnd: true)
        XCTAssertEqual(pacer.changed(at: 30.5), .restart(ms: 35), "a late change is no longer the word end")
    }
    func testWordEndsAreJudgedFromTheTypedCharacterOnly() {
        for ended in [" ", "\r", "\n", "\t", ".", ",", "!", "?", ";", ")", "\u{201D}"] { XCTAssertTrue(CheckPacer.endsWord(ended), ended) }
        for inside in ["a", "Z", "7", "é", "", nil] { XCTAssertFalse(CheckPacer.endsWord(inside), inside ?? "nil") }
    }

    func testScanMemoRunsEachDistinctTextOnce() {
        let memo = ScanMemo(capacity: 8)
        var runs = 0
        XCTAssertEqual(memo.value(for: Substring("alpha beta")) { runs += 1; return ["x"] }, ["x"])
        XCTAssertEqual(memo.value(for: Substring("alpha beta")) { runs += 1; return ["y"] }, ["x"], "the second ask is answered from memory")
        XCTAssertEqual(runs, 1)
        _ = memo.value(for: Substring("gamma")) { runs += 1; return [] }
        XCTAssertEqual(runs, 2)
    }
    func testDocumentNamesAreStableAcrossRescansAndFollowEdits() {
        let text = "Hi Aman, welcome.\nYesterday Priya Nair met Satya Nadella in London.\nNothing else."
        let first = KnownNames.documentNames(in: text)
        XCTAssertEqual(KnownNames.documentNames(in: text), first, "a rescan answered from memory is the same")
        let edited = KnownNames.documentNames(in: text.replacingOccurrences(of: "Nothing else.", with: "Ask Maria."))
        XCTAssertTrue(edited.contains("Maria"), "a changed line is scanned afresh")
        XCTAssertTrue(first.allSatisfy { edited.contains($0) }, "the unchanged lines keep their names")
    }
}
