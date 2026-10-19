import XCTest
import AppKit
import SwiftUI
import ParzrCore
@testable import Parzr

/// The tone check on the selection card: a flagged Fix result says how it may read and offers Soften in place of the
/// usual rewrite; Soften runs the tone rewrite that fits the flag. Headless: the card is laid out in a window never shown.
@MainActor
final class ToneCardTests: XCTestCase {
    let source = "Thanks for finally getting back to me."
    private func result(_ edits: [WritingEdit]) throws -> RewriteResult {
        let object: [String: Any] = ["version": "t", "text": try EditPlan.apply(edits, to: source), "edits": try JSONSerialization.jsonObject(with: JSONEncoder().encode(edits)), "source_map": [], "elapsed_ms": 1.0, "protected_count": 0]
        return try JSONDecoder().decode(RewriteResult.self, from: JSONSerialization.data(withJSONObject: object))
    }
    private func flagged(_ category: ToneCategory = .passiveAggressive, fixes: [WritingEdit] = []) throws -> AppModel {
        let model = AppModel(); model.offersRewrite = true; model.mode = .fix; model.source = source
        let fixed = try result(fixes); model.result = fixed; model.selectedEdits = Set(fixed.edits.map(\.id)); model.focusedEditID = fixed.edits.first?.id
        model.suggestion = SuggestedVersion(tone: .friendly, source: source)
        model.toneFlag = ToneFlag(category: category, score: 0.97, range: NSRange(location: 0, length: (source as NSString).length))
        return model
    }
    private func mount(_ model: AppModel) -> (NSWindow, NSHostingView<RewritePanel>) {
        let host = NSHostingView(rootView: RewritePanel(model: model))
        let window = NSWindow(contentRect: NSRect(origin: .zero, size: RewritePanel.size), styleMask: [.borderless], backing: .buffered, defer: false)
        window.isReleasedWhenClosed = false; window.contentView = host
        window.layoutIfNeeded(); host.layoutSubtreeIfNeeded()
        return (window, host)
    }

    func testAFlaggedMessageWithNothingToFixOffersSoftenAsTheMainAction() throws {
        let model = try flagged()
        XCTAssertFalse(RewritePanel(model: model).isCompact, "the flag keeps the full card")
        XCTAssertEqual(model.softenTone, .friendly, "a short message outside a known app softens as Friendly")
        let card = mount(model)
        RunLoop.current.run(until: Date().addingTimeInterval(0.1))
        XCTAssertNotNil(NativeControls.find(label: "Soften: rewrite as Friendly", in: card.1))
        XCTAssertNil(NativeControls.find(label: "Use Friendly version", in: card.1), "Soften takes the place of the offered rewrite")
        XCTAssertFalse(card.0.isVisible)
        card.0.close()
    }

    func testBesideFixesTheFlagIsOneRowAndTheFixesKeepTheirActions() throws {
        let space = WritingEdit(start: 6, end: 7, replacement: "  ", original: " ", category: "Punctuation", ruleID: "spacing")
        let model = try flagged(fixes: [space])
        let card = mount(model)
        RunLoop.current.run(until: Date().addingTimeInterval(0.1))
        XCTAssertNotNil(NativeControls.find(label: "Soften: rewrite as Friendly", in: card.1))
        XCTAssertNotNil(NativeControls.find(label: "Ignore", in: card.1))
        card.0.close()
    }

    func testSoftenRunsTheToneThatFitsTheFlag() throws {
        for (category, tone) in [(ToneCategory.curt, RewriteMode.friendly), (.overApologetic, .direct), (.rude, .friendly)] {
            let model = try flagged(category)
            XCTAssertEqual(model.softenTone, tone)
            model.soften()
            XCTAssertEqual(model.mode, tone, "\(category) softens as \(tone)")
            XCTAssertNil(model.toneFlag, "the flag goes once the rewrite starts")
            model.clearSession()
        }
    }

    func testNoFlagMeansTheUsualCard() throws {
        let model = try flagged(); model.toneFlag = nil
        XCTAssertNil(model.softenTone)
        model.soften()
        XCTAssertEqual(model.mode, .fix, "Soften without a flag does nothing")
    }
}
