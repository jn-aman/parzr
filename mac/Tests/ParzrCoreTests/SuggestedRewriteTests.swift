import XCTest
@testable import ParzrCore

final class SuggestedRewriteTests: XCTestCase {
    private func result(_ source: String, _ edits: [WritingEdit]) throws -> RewriteResult {
        let object: [String: Any] = ["version": "t", "text": try EditPlan.apply(edits, to: source), "edits": try JSONSerialization.jsonObject(with: JSONEncoder().encode(edits)), "source_map": [], "elapsed_ms": 1.0, "protected_count": 0]
        return try JSONDecoder().decode(RewriteResult.self, from: JSONSerialization.data(withJSONObject: object))
    }
    func testChatAppsGetFriendlyAndMailAndDocumentsGetProfessional() {
        for bundle in ["com.tinyspeck.slackmacgap", "com.microsoft.teams2", "com.hnc.Discord", "com.apple.MobileSMS", "net.whatsapp.WhatsApp"] {
            XCTAssertEqual(SuggestedRewrite.tone(for: bundle, text: String(repeating: "A long paragraph of text. ", count: 20)), .friendly, bundle)
            XCTAssertTrue(SuggestedRewrite.isChat(bundle), bundle)
        }
        for bundle in ["com.apple.mail", "com.microsoft.Outlook", "com.microsoft.Word", "com.apple.iWork.Pages"] {
            XCTAssertEqual(SuggestedRewrite.tone(for: bundle, text: "ok see you then"), .professional, bundle)
            XCTAssertFalse(SuggestedRewrite.isChat(bundle), bundle)
        }
        // Elsewhere a short line reads as chat and a longer or multi-line text as a document.
        XCTAssertEqual(SuggestedRewrite.tone(for: "com.example.editor", text: "can we move the call to friday"), .friendly)
        XCTAssertEqual(SuggestedRewrite.tone(for: nil, text: "Hi team,\nThe launch moves to Friday."), .professional)
        XCTAssertEqual(SuggestedRewrite.tone(for: nil, text: String(repeating: "word ", count: 40)), .professional)
        XCTAssertFalse(SuggestedRewrite.isChat(nil))
    }
    func testARewriteIsOfferedForAFewWordsOrMore() {
        XCTAssertFalse(SuggestedRewrite.offered(for: "teh"))
        XCTAssertFalse(SuggestedRewrite.offered(for: "hello there"))
        XCTAssertFalse(SuggestedRewrite.offered(for: "ok 12 34 !!"), "Numbers and marks are not words.")
        XCTAssertTrue(SuggestedRewrite.offered(for: "I hat it."))
        XCTAssertTrue(SuggestedRewrite.offered(for: "This is so bad. I hat it."))
        XCTAssertFalse(SuggestedRewrite.offered(for: String(repeating: "A long page. ", count: 400)))
    }
    func testOnlyARewriteThatChangesMoreThanTheFixesIsWorthOffering() throws {
        let source = "This is so bad. I hat it."
        let hate = WritingEdit(start: 18, end: 21, replacement: "hate", original: "hat", category: "Style", ruleID: "local-model")
        let written = try result(source, [hate])
        XCTAssertTrue(SuggestedRewrite.worthOffering(written, fixed: source))
        XCTAssertFalse(SuggestedRewrite.worthOffering(written, fixed: "This is so bad. I hate it."), "Nothing beyond the fixes already on the card.")
        XCTAssertFalse(SuggestedRewrite.worthOffering(try result(source, []), fixed: source))
        XCTAssertFalse(SuggestedRewrite.worthOffering(nil, fixed: source))
        XCTAssertEqual(SuggestedRewrite.action(.friendly), "Use Friendly version")
        XCTAssertEqual(SuggestedRewrite.working(.professional), "Writing a Professional version…")
    }
    func testRequestsSayWhetherTheTextIsFromAChatApp() throws {
        let encoded = try JSONSerialization.jsonObject(with: JSONEncoder().encode(EngineRequest(text: "thanks!", mode: .friendly, casual: true))) as? [String: Any]
        XCTAssertEqual(encoded?["casual"] as? Bool, true)
        let plain = try JSONSerialization.jsonObject(with: JSONEncoder().encode(EngineRequest(text: "thanks!"))) as? [String: Any]
        XCTAssertEqual(plain?["casual"] as? Bool, false)
    }
}
