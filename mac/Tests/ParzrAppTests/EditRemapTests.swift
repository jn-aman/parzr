import XCTest
import ParzrCore
@testable import Parzr

@MainActor
final class EditRemapTests: XCTestCase {
    /// "recieved" and "mesage" in "I recieved your mesage." as the engine would flag them.
    private let source = "I recieved your mesage."
    private var edits: [WritingEdit] { [WritingEdit(start: 2, end: 10, replacement: "received", original: "recieved"), WritingEdit(start: 16, end: 22, replacement: "message", original: "mesage")] }
    private func moved(to new: String, from old: String? = nil, _ list: [WritingEdit]? = nil) -> [WritingEdit] {
        let change = EditRemap.Change(from: old ?? source, to: new)
        return (list ?? edits).compactMap { change.shift($0) }
    }
    private func spans(_ list: [WritingEdit]) -> [[Int]] { list.map { [$0.start_utf16, $0.end_utf16] } }

    func testUnchangedTextKeepsEveryEdit() {
        XCTAssertEqual(spans(moved(to: source)), [[2, 10], [16, 22]])
    }
    func testTypingAfterAllEditsKeepsThemInPlace() {
        XCTAssertEqual(spans(moved(to: source + " Thanks")), [[2, 10], [16, 22]])
    }
    func testInsertBeforeAnEditShiftsIt() {
        XCTAssertEqual(spans(moved(to: "Hi. " + source)), [[6, 14], [20, 26]])
        XCTAssertEqual(spans(moved(to: "Ix recieved your mesage.")), [[3, 11], [17, 23]])
    }
    func testInsertBetweenEditsShiftsOnlyTheLaterOne() {
        XCTAssertEqual(spans(moved(to: "I recieved all your mesage.")), [[2, 10], [20, 26]])
    }
    func testTypingInsideAnEditDropsIt() {
        XCTAssertEqual(spans(moved(to: "I reciieved your mesage.")), [[17, 23]])
    }
    func testTypingAtTheEdgesOfAnEditDropsIt() {
        // A word grown at its end, or text typed right in front of it, is no longer the span the engine judged.
        XCTAssertEqual(spans(moved(to: "I recievedd your mesage.")), [[17, 23]])
        XCTAssertEqual(spans(moved(to: "I xrecieved your mesage.")), [[17, 23]])
    }
    func testDeleteBeforeShiftsBack() {
        XCTAssertEqual(spans(moved(to: " recieved your mesage.")), [[1, 9], [15, 21]])
    }
    func testDeleteAcrossAnEditDropsOnlyTheOverlappedOnes() {
        // "ed your mes" removed: both words are touched.
        XCTAssertEqual(spans(moved(to: "I reciage.")), [])
        // "your" removed: the first edit is before it, the second after.
        XCTAssertEqual(spans(moved(to: "I recieved  mesage.")), [[2, 10], [12, 18]])
    }
    func testPasteReplacingARangeDropsOverlapsAndShiftsTheRest() {
        // The first sentence's word is replaced by a longer paste; the later edit moves by the length change.
        XCTAssertEqual(spans(moved(to: "I got your mesage.", from: source, edits)), [[11, 17]])
        XCTAssertEqual(spans(moved(to: "Hello there, I recieved your mesage.")), [[15, 23], [29, 35]])
    }
    func testEmptyingTheTextDropsEverything() {
        XCTAssertEqual(moved(to: "").count, 0)
    }
    func testSurrogatePairsAreNeverSplit() {
        // Lengths are UTF-16: the emoji is 2 units. Replacing one emoji with another shares the lead surrogate; the whole pair counts as changed.
        let old = "a 🙂 mesage 🙂 b", new = "a 🙃 mesage 🙂 b"
        let flagged = [WritingEdit(start: 5, end: 11, replacement: "message", original: "mesage"), WritingEdit(start: 2, end: 4, replacement: "", original: "🙂")]
        let change = EditRemap.Change(from: old, to: new)
        XCTAssertEqual(change.start, 2); XCTAssertEqual(change.oldEnd, 4)
        XCTAssertEqual(flagged.compactMap { change.shift($0) }.map(\.start_utf16), [5])
        XCTAssertEqual(flagged.compactMap { change.shift($0) }.first?.original, "mesage")
        // Typing an emoji before an edit moves it by 2 units.
        XCTAssertEqual(spans(moved(to: "🙂" + source)), [[4, 12], [18, 24]])
        // Deleting an emoji before an edit moves it back by 2.
        XCTAssertEqual(spans(moved(to: "😀 I recieved", from: "😀😀 I recieved", [WritingEdit(start: 7, end: 15, replacement: "received", original: "recieved")])), [[5, 13]])
    }
    func testMovedEditsKeepTheirContent() throws {
        let edit = try XCTUnwrap(moved(to: "Hi. " + source).first)
        XCTAssertEqual([edit.replacement, edit.original, edit.category, edit.rule_id], ["received", "recieved", "Grammar", "test"])
    }

    // MARK: the model keeps its marks while typing but never applies them

    private func result(_ edits: [WritingEdit]) throws -> RewriteResult {
        let object: [String: Any] = ["version": "t", "text": source, "edits": try JSONSerialization.jsonObject(with: JSONEncoder().encode(edits)), "source_map": [], "elapsed_ms": 1.0, "protected_count": 0]
        return try JSONDecoder().decode(RewriteResult.self, from: JSONSerialization.data(withJSONObject: object))
    }
    func testTypingKeepsShiftedMarksProvisionalAndNotApplicable() throws {
        let model = AppModel()
        model.source = source; model.result = try result(edits); model.selectedEdits = Set(edits.map(\.id))
        model.playground("Hi. " + source, debounce: true)
        defer { model.clearSession() }
        XCTAssertTrue(model.provisional)
        XCTAssertFalse(model.busy, "A keystroke alone is not a wait.")
        XCTAssertEqual(spans(model.chosenEdits), [[6, 14], [20, 26]])
        XCTAssertFalse(model.canApply)
        XCTAssertEqual(spans(model.marks(for: "Hi. " + source)), [[6, 14], [20, 26]])
        // One keystroke ahead of the model: the view asks before the model is told.
        XCTAssertEqual(spans(model.marks(for: "Hi. " + source + "!")), [[6, 14], [20, 26]])
    }
    func testAnExplicitCheckStillClearsAndShowsChecking() throws {
        let model = AppModel()
        model.source = source; model.result = try result(edits); model.selectedEdits = Set(edits.map(\.id))
        model.playground(source)
        defer { model.clearSession() }
        XCTAssertNil(model.result); XCTAssertTrue(model.busy); XCTAssertFalse(model.provisional)
    }
}
