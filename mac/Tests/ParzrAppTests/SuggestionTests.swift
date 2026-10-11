import XCTest
import AppKit
import SwiftUI
import ParzrCore
@testable import Parzr

/// The rewrite the selection card offers after a Fix check: shown while it is written, offered when it changes more than the fixes, and one action away.
@MainActor
final class SuggestionTests: XCTestCase {
    let source = "This is so bad. I hat it."
    private func result(_ edits: [WritingEdit], on text: String? = nil) throws -> RewriteResult {
        let base = text ?? source
        let object: [String: Any] = ["version": "t", "text": try EditPlan.apply(edits, to: base), "edits": try JSONSerialization.jsonObject(with: JSONEncoder().encode(edits)), "source_map": [], "elapsed_ms": 1.0, "protected_count": 0]
        return try JSONDecoder().decode(RewriteResult.self, from: JSONSerialization.data(withJSONObject: object))
    }
    private var hate: WritingEdit { WritingEdit(start: 18, end: 21, replacement: "hate", original: "hat", category: "Style", ruleID: "local-model", explanation: "Suggested rewrite") }
    /// A finished Fix check of `source` with nothing to fix, and a Friendly rewrite being written.
    private func checked(fixes: [WritingEdit] = []) throws -> AppModel {
        let model = AppModel(); model.offersRewrite = true; model.mode = .fix; model.source = source
        let fixed = try result(fixes); model.result = fixed; model.selectedEdits = Set(fixed.edits.map(\.id)); model.focusedEditID = fixed.edits.first?.id
        model.suggestion = SuggestedVersion(tone: .friendly, source: source)
        return model
    }
    private func mount(_ model: AppModel) -> (NSWindow, NSHostingView<RewritePanel>) {
        let host = NSHostingView(rootView: RewritePanel(model: model))
        let window = NSWindow(contentRect: NSRect(origin: .zero, size: RewritePanel.size), styleMask: [.borderless], backing: .buffered, defer: false)
        window.isReleasedWhenClosed = false; window.contentView = host
        window.layoutIfNeeded(); host.layoutSubtreeIfNeeded()
        return (window, host)
    }

    func testTheRewriteShowsWhileItIsWrittenAndOnlyWhenItAddsSomething() throws {
        let model = try checked()
        XCTAssertTrue(model.showsSuggestion, "A spinner shows while the rewrite is written.")
        XCTAssertFalse(model.suggestionReady)
        XCTAssertFalse(RewritePanel(model: model).isCompact, "The card keeps its full size so it does not jump when the rewrite arrives.")
        model.suggestion?.done = true
        XCTAssertFalse(model.showsSuggestion, "A failed rewrite disappears, leaving the tone hint.")
        model.suggestion?.result = try result([])
        XCTAssertFalse(model.showsSuggestion, "An unchanged rewrite is not offered.")
        model.suggestion?.result = try result([hate])
        XCTAssertTrue(model.suggestionReady); XCTAssertTrue(model.showsSuggestion)
        model.source = "Something else entirely."
        XCTAssertFalse(model.showsSuggestion, "A rewrite of other text is never offered.")
    }
    func testTheCardOffersTheRewriteWithOneActionBesideTheFixesAndAlone() throws {
        // Synchronous on purpose: an optional-chained `try` assignment inside an async test aborts the runner ("freed pointer was not the last allocation").
        let model = try checked(); model.suggestion?.result = try result([hate]); model.suggestion?.done = true
        let alone = mount(model)
        RunLoop.current.run(until: Date().addingTimeInterval(0.1))
        XCTAssertNotNil(NativeControls.find(label: "Use Friendly version", in: alone.1), "With nothing to fix, the rewrite is the primary action.")
        alone.0.close()
        let space = WritingEdit(start: 15, end: 16, replacement: "  ", original: " ", category: "Punctuation", ruleID: "spacing")
        let fixes = try checked(fixes: [space]); fixes.suggestion?.result = try result([hate]); fixes.suggestion?.done = true
        let beside = mount(fixes)
        RunLoop.current.run(until: Date().addingTimeInterval(0.1))
        XCTAssertNotNil(NativeControls.find(label: "Use Friendly version", in: beside.1), "Beside the fixes, the rewrite has its own Use button.")
        XCTAssertNotNil(NativeControls.find(label: "Ignore", in: beside.1), "The fixes keep their actions.")
        beside.0.close()
    }
    func testUsingTheRewriteShowsItAsTheToneResultWithoutANewCheck() throws {
        let model = try checked(); let written = try result([hate])
        model.suggestion?.result = written; model.suggestion?.done = true
        // No editor selection here, so nothing can be applied: the card shows the rewrite as Friendly's result, ready to copy.
        model.applyBest()
        XCTAssertEqual(model.mode, .friendly)
        XCTAssertFalse(model.busy, "No new check runs.")
        XCTAssertEqual(model.preview, "This is so bad. I hate it.")
        XCTAssertNil(model.suggestion)
    }
    func testPickingTheOfferedToneReusesTheRewrite() throws {
        let model = try checked(); model.suggestion?.result = try result([hate]); model.suggestion?.done = true
        model.changeMode(.friendly)
        XCTAssertEqual(model.mode, .friendly); XCTAssertFalse(model.busy)
        XCTAssertEqual(model.preview, "This is so bad. I hate it.")
    }
    func testANewCheckOrTheEndOfTheSessionDropsTheRewrite() throws {
        let model = try checked()
        model.clearSession()
        XCTAssertNil(model.suggestion)
        let again = try checked()
        again.changeMode(.concise)
        XCTAssertNil(again.suggestion, "Another tone starts its own rewrite; the offer goes.")
        again.clearSession()
    }
    func testAFixCheckOfAFewWordsOffersARewriteFromTheEngine() async throws {
        guard ProcessInfo.processInfo.environment["PARZR_ENGINE_PATH"] != nil else { throw XCTSkip("Supply the built engine library.") }
        let model = AppModel(); model.offersRewrite = true
        model.playground(source)
        defer { model.clearSession() }
        for _ in 0..<3000 where model.busy { try await Task.sleep(for: .milliseconds(20)) }
        XCTAssertNotNil(model.suggestion, "A Fix check of a few words starts a rewrite.")
        XCTAssertEqual(model.suggestion?.tone, .friendly)
        for _ in 0..<3000 where model.suggestion?.done == false { try await Task.sleep(for: .milliseconds(20)) }
        XCTAssertFalse(model.busy, "The fixes were never blocked by the rewrite.")
        let short = AppModel(); short.offersRewrite = true
        short.playground("teh")
        defer { short.clearSession() }
        for _ in 0..<3000 where short.busy { try await Task.sleep(for: .milliseconds(20)) }
        XCTAssertNil(short.suggestion, "One word gets no rewrite.")
    }
}
