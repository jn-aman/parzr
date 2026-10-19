import AppKit
import XCTest
@testable import Parzr
import ParzrCore

/// The decisions behind applying a fix from an inline mark (pure: no Accessibility, no other app). The scripted runs follow
/// `SelectionSnapshot.prepareToApply`: one focus reading per poll, a restore only when the step says so.
@MainActor
final class ApplyGuardTests: XCTestCase {
    private let captured = 1, another = 2, rebuilt = 3

    /// Drives `ApplyFocus.step` over `focus(poll, restoredYet)` the way `prepareToApply` does. Returns the final step, how often focus was put back
    /// (and into which element), and how many polls it took.
    private func run(field: ApplyFocus.Field = .usable, standIns: Set<Int> = [], _ focus: (Int, Bool) -> Int?) -> (step: ApplyFocus.Step, restoredInto: [Int], polls: Int) {
        var restored = false, others = 0, restoredInto: [Int] = []
        for attempt in 0..<ApplyFocus.attempts {
            let seen = ApplyFocus.seen(captured: captured, focus: focus(attempt, restored), same: { $0 == $1 }, isStandIn: { standIns.contains($0) })
            others = seen == .other ? others + 1 : 0
            let step = ApplyFocus.step(seen: seen, attempt: attempt, others: others, restored: restored, field: seen == .none ? field : .usable)
            switch step {
            case .proceed, .fail: return (step, restoredInto, attempt + 1)
            case .restore: restored = true; restoredInto.append(captured)
            case .wait: break
            }
        }
        return (.fail(.focusLost), restoredInto, ApplyFocus.attempts)
    }

    func testAFocusedEditorProceedsAtOnceWithoutWaitingOrRestoring() {
        let result = run { _, _ in self.captured }
        XCTAssertEqual(result.step, .proceed); XCTAssertEqual(result.polls, 1, "native editors pay no extra latency"); XCTAssertEqual(result.restoredInto, [])
    }
    func testTheKeyboardComingBackAfterTheCardStepsAsideProceeds() {
        // Brave after the card orders out: no focused field for a few polls, then the same contenteditable.
        let result = run { poll, _ in poll < 4 ? nil : self.captured }
        XCTAssertEqual(result.step, .proceed); XCTAssertEqual(result.restoredInto, [], "focus came back on its own, so nothing was moved")
    }
    func testNoFocusedFieldPutsFocusBackIntoTheMarksOwnFieldOnce() {
        let result = run { _, restored in restored ? self.captured : nil }
        XCTAssertEqual(result.step, .proceed)
        XCTAssertEqual(result.restoredInto, [captured], "focus goes back once, and only into the field the fix belongs to")
        XCTAssertEqual(result.polls, ApplyFocus.restoreAfter + 2)
    }
    func testFocusThatNeverComesBackFailsAsLostAfterOneRestore() {
        let result = run { _, _ in nil }
        XCTAssertEqual(result.step, .fail(.focusLost)); XCTAssertEqual(result.restoredInto.count, 1, "focus is never set twice")
        XCTAssertEqual(result.polls, ApplyFocus.attempts)
    }
    func testAnotherFieldWithFocusIsNeverTakenOverAndNeverTypedInto() {
        let result = run { _, _ in self.another }
        XCTAssertEqual(result.step, .fail(.focusElsewhere)); XCTAssertEqual(result.restoredInto, [], "the writer moved to that field: Parzr never moves focus away from it")
        XCTAssertEqual(result.polls, ApplyFocus.otherSettles)
        // Even after an empty read first.
        let later = run { poll, _ in poll < 2 ? nil : self.another }
        XCTAssertEqual(later.step, .fail(.focusElsewhere)); XCTAssertEqual(later.restoredInto, [])
    }
    func testOneTransientReadOfAnotherFieldIsIgnored() {
        let result = run { poll, _ in poll == 0 ? self.another : self.captured }
        XCTAssertEqual(result.step, .proceed)
    }
    func testARebuiltFieldWithTheSameTextInTheSamePlaceIsAccepted() {
        XCTAssertEqual(run(standIns: [rebuilt]) { _, _ in self.rebuilt }.step, .proceed)
        XCTAssertEqual(ApplyFocus.seen(captured: captured, focus: rebuilt, same: { $0 == $1 }, isStandIn: { $0 == self.rebuilt }), .standIn)
        // The old field is gone and nothing has focus yet: wait for the rebuilt one rather than restoring into a dead element.
        let waited = run(field: .gone, standIns: [rebuilt]) { poll, _ in poll < 8 ? nil : self.rebuilt }
        XCTAssertEqual(waited.step, .proceed); XCTAssertEqual(waited.restoredInto, [])
        XCTAssertEqual(run(field: .gone) { _, _ in nil }.step, .fail(.editorUnavailable))
    }
    func testChangedOrReadOnlyFieldsStopAtOnceWithTheirOwnReason() {
        XCTAssertEqual(run(field: .changed) { _, _ in nil }.step, .fail(.textChanged))
        XCTAssertEqual(run(field: .changed) { _, _ in nil }.restoredInto, [], "focus is never put back into text that changed")
        XCTAssertEqual(run(field: .readOnly) { _, _ in nil }.step, .fail(.notEditable))
    }
    func testAStandInNeedsTheSameTextAndTheSamePlace() {
        let rect = CGRect(x: 100, y: 200, width: 80, height: 18)
        XCTAssertTrue(ApplyFocus.isStandIn(text: "Written for: you", expected: "Written for: you", bounds: rect.offsetBy(dx: 1, dy: -1), captured: rect))
        XCTAssertFalse(ApplyFocus.isStandIn(text: "Written for: your", expected: "Written for: you", bounds: rect, captured: rect), "different text is a different field")
        XCTAssertFalse(ApplyFocus.isStandIn(text: "Written for: you", expected: "Written for: you", bounds: rect.offsetBy(dx: 0, dy: 40), captured: rect), "same text elsewhere on the page")
        XCTAssertFalse(ApplyFocus.isStandIn(text: "Written for: you", expected: "Written for: you", bounds: nil, captured: rect), "no geometry, no proof")
        XCTAssertFalse(ApplyFocus.isStandIn(text: "x", expected: "x", bounds: rect, captured: nil))
        XCTAssertFalse(ApplyFocus.isStandIn(text: nil, expected: "x", bounds: rect, captured: rect))
    }
    func testTheTypedFallbackAndValidationNameWhereFocusWent() {
        XCTAssertEqual(ApplyFocus.focusFailure(editable: true, focusResolves: true), .focusElsewhere)
        XCTAssertEqual(ApplyFocus.focusFailure(editable: true, focusResolves: false), .focusLost)
        XCTAssertEqual(ApplyFocus.focusFailure(editable: false, focusResolves: true), .notEditable)
    }
    func testInlineMarksAreNeverToldTheirSelectionChanged() {
        for failure in ApplyFailure.allCases {
            let message = failure.message(automatic: true)
            XCTAssertFalse(message.lowercased().contains("selection"), "\(failure): \"\(message)\" talks about a selection the writer never made")
            XCTAssertFalse(message.lowercased().contains("select the text"), "\(failure): \"\(message)\"")
        }
        XCTAssertTrue(ApplyFailure.selectionChanged.message(automatic: false).contains("selection"), "an explicit selection still says so")
    }
    func testTextChangeEditorRefusalAndFocusMoveReadDifferently() {
        let reasons: [ApplyFailure] = [.textChanged, .notAccepted, .focusElsewhere, .focusLost, .rangeRefused, .selectionNotHeld, .editorNotInFront, .changedDuring]
        for automatic in [true, false] {
            let messages = reasons.map { $0.message(automatic: automatic) }
            XCTAssertEqual(Set(messages).count, reasons.count, "every reason reads differently: \(messages)")
        }
        XCTAssertTrue(ApplyFailure.focusElsewhere.message(automatic: true).contains("different field"))
        XCTAssertTrue(ApplyFailure.textChanged.message(automatic: true).contains("text changed"))
        XCTAssertTrue(ApplyFailure.notAccepted.message(automatic: true).contains("didn’t accept"))
        XCTAssertEqual(Set(ApplyFailure.allCases.map(\.rawValue)).count, ApplyFailure.allCases.count, "the log names every guard uniquely")
    }
    func testTheClosingSentenceSaysWhetherAnythingChanged() {
        XCTAssertEqual(ApplyFocus.outcome(applied: 0, untouched: true), "Nothing was changed.")
        XCTAssertEqual(ApplyFocus.outcome(applied: 0, untouched: false), "0 edits applied; use the editor’s Undo if needed.", "a partial write is never called nothing")
        XCTAssertEqual(ApplyFocus.outcome(applied: 1, untouched: false), "1 edit applied; use the editor’s Undo if needed.")
        let error = ApplyError(.notAccepted, automatic: true).adding("Nothing was changed.")
        XCTAssertEqual(error.failure, .notAccepted, "the guard survives the extra sentence, for the log")
        XCTAssertEqual(error.localizedDescription, "The editor didn’t accept the change. Nothing was changed.")
        XCTAssertEqual(ApplyError(.textChanged, automatic: false).adding("").localizedDescription, "Your text changed. Select it again.")
    }

    // MARK: Headless snapshots (an NSTextView stands in for the editor)

    private func preferences() throws -> (Preferences, () -> Void) {
        let suite = "app.parzr.tests.ApplyGuard.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        defaults.set(true, forKey: "onboardingCompleted"); defaults.set(true, forKey: "passive"); defaults.set(false, forKey: "paused")
        defaults.set([String](), forKey: "disabledApps"); defaults.set([String: Date](), forKey: "automaticAppPauses")
        return (Preferences(defaults: defaults, permissionGranted: false), { defaults.removePersistentDomain(forName: suite) })
    }
    private func snapshot(_ editor: NSTextView, automatic: Bool) -> SelectionSnapshot {
        let caret = editor.selectedRange()
        let range = automatic ? NSRange(location: 0, length: editor.string.utf16.count) : caret
        return SelectionSnapshot(app: .current, element: AXUIElementCreateSystemWide(), selection: range, expectedSelection: caret, text: (editor.string as NSString).substring(with: range),
                                 fullText: editor.string, bounds: nil, richText: nil, copied: false, canPatch: true, docs: false, automatic: automatic, headlessEditor: editor)
    }
    func testApplyingAnInlineFixIgnoresWhereTheCaretWentButNeverChangedText() throws {
        let (prefs, cleanup) = try preferences(); defer { cleanup() }
        let editor = NSTextView(frame: .zero); editor.string = "Written for: your team."
        editor.setSelectedRange(NSRange(location: 23, length: 0))
        let inline = snapshot(editor, automatic: true)
        // Clicking the card moved the caret (or Chromium reports another one): the fix is placed by offsets in verified text, so it still applies.
        editor.setSelectedRange(NSRange(location: 3, length: 5))
        XCTAssertNoThrow(try inline.validate(preferences: prefs, applying: true))
        XCTAssertThrowsError(try inline.validate(preferences: prefs), "outside an apply, a moved caret still retires a pending result") { error in
            XCTAssertFalse(error.localizedDescription.lowercased().contains("selection"), error.localizedDescription)
        }
        editor.string = "Written for: your teams."
        XCTAssertThrowsError(try inline.validate(preferences: prefs, applying: true)) { error in
            XCTAssertEqual((error as? ApplyError)?.failure, .textChanged)
            XCTAssertEqual(error.localizedDescription, ApplyFailure.textChanged.message(automatic: true))
        }
        editor.string = "Written for: your team."; editor.isEditable = false
        XCTAssertThrowsError(try inline.validate(preferences: prefs, applying: true)) { error in XCTAssertEqual((error as? ApplyError)?.failure, .notEditable) }
    }
    func testAnExplicitSelectionMustStillBeExactlyWhereItWas() throws {
        let (prefs, cleanup) = try preferences(); defer { cleanup() }
        let editor = NSTextView(frame: .zero); editor.string = "i hope your doing well."
        editor.setSelectedRange(NSRange(location: 0, length: editor.string.utf16.count))
        let explicit = snapshot(editor, automatic: false)
        XCTAssertNoThrow(try explicit.validate(preferences: prefs, applying: true))
        editor.setSelectedRange(NSRange(location: 2, length: 4))
        XCTAssertThrowsError(try explicit.validate(preferences: prefs, applying: true)) { error in
            XCTAssertEqual((error as? ApplyError)?.failure, .selectionChanged)
            XCTAssertEqual(error.localizedDescription, "Your selection changed. Select the text again.")
        }
    }
    func testAHeadlessInlineFixAppliesAfterTheCaretMoved() async throws {
        // The throwaway test suite behind Preferences.shared (never the owner's defaults), set for automatic checking and put back afterwards.
        let prefs = Preferences.shared
        let saved = (prefs.paused, prefs.passive, prefs.onboardingCompleted)
        defer { prefs.paused = saved.0; prefs.passive = saved.1; prefs.onboardingCompleted = saved.2 }
        prefs.paused = false; prefs.passive = true; prefs.onboardingCompleted = true
        let editor = NSTextView(frame: .zero); editor.string = "Written for: your team."
        editor.setSelectedRange(NSRange(location: 23, length: 0))
        let inline = snapshot(editor, automatic: true)
        editor.setSelectedRange(NSRange(location: 0, length: 0))
        let edit = WritingEdit(start: 11, end: 12, replacement: "", original: ":", category: "Punctuation", ruleID: "punct.colon")
        let prepared = try await inline.prepareToApply()
        try await prepared.apply([edit])
        XCTAssertEqual(editor.string, "Written for your team.")
    }
}
