import XCTest
@testable import ParzrKit

final class SentenceContextTests: XCTestCase {
    func testTakesTheLastTwoSentencesAndLeavesTheWordBeingTyped() throws {
        let context = try XCTUnwrap(SentenceContext.current(before: "First one. Second one here. I recieved teh rep"))
        XCTAssertEqual(context.text, "Second one here. I recieved teh ")
        XCTAssertEqual(context.pending, "rep")
        XCTAssertFalse(context.sentenceEnd)
        XCTAssertTrue(context.sentenceStart)
    }

    func testAFinishedSentenceEndsTheSpan() throws {
        let context = try XCTUnwrap(SentenceContext.current(before: "can u send it by friday?", sentences: 1))
        XCTAssertEqual(context.text, "can u send it by friday?")
        XCTAssertEqual(context.pending, "")
        XCTAssertTrue(context.sentenceEnd)
    }

    func testOnlyTheCurrentParagraph() throws {
        let context = try XCTUnwrap(SentenceContext.current(before: "Dear Sam,\nthe the plan is ready. "))
        XCTAssertEqual(context.text, "the the plan is ready. ")
    }

    func testNothingToCheck() {
        XCTAssertNil(SentenceContext.current(before: nil))
        XCTAssertNil(SentenceContext.current(before: "   "))
        // A single word still being typed is not checked yet.
        XCTAssertNil(SentenceContext.current(before: "Hel"))
    }

    func testALongContextCutOffAtItsStartIsNotASentenceStart() throws {
        let long = String(repeating: "word ", count: 100) + "and more"
        let context = try XCTUnwrap(SentenceContext.current(before: long))
        XCTAssertFalse(context.sentenceStart)
    }
}

final class ProxyEditTests: XCTestCase {
    private func edit(_ text: String, _ original: String, _ replacement: String, group: String? = nil) -> WritingEdit {
        let range = (text as NSString).range(of: original)
        return WritingEdit(start: range.location, end: range.location + range.length, replacement: replacement, original: original, groupID: group)
    }

    func testDeletesBackToTheEditAndRetypesTheRest() throws {
        let checked = "I recieved teh "
        let before = "Hi. " + checked
        let plan = try XCTUnwrap(ProxyEdit.plan([edit(checked, "teh", "the")], checked: checked, before: before))
        XCTAssertEqual(plan, ProxyEdit(deleteCount: 3, insert: "he "))
        XCTAssertEqual(plan.applied(to: before), "Hi. I recieved the ")
    }

    func testKeepsWhatWasTypedAfterTheCheck() throws {
        let checked = "I recieved teh "
        let before = "Hi. " + checked + "repo"
        let plan = try XCTUnwrap(ProxyEdit.plan([edit(checked, "recieved", "received"), edit(checked, "teh", "the")], checked: checked, before: before))
        XCTAssertEqual(plan.applied(to: before), "Hi. I received the repo")
        // Only from the first changed character: "I rec" stays.
        XCTAssertEqual(plan.deleteCount, "ieved teh repo".count)
    }

    func testCountsCharactersNotCodeUnits() throws {
        let checked = "teh 👍🏽 plan "
        let plan = try XCTUnwrap(ProxyEdit.plan([edit(checked, "teh", "the")], checked: checked, before: checked))
        XCTAssertEqual(plan.deleteCount, checked.count - 1)
        XCTAssertEqual(plan.applied(to: checked), "the 👍🏽 plan ")
        // An edit right after an emoji deletes the emoji whole and retypes it.
        let emoji = "ok 👍🏽teh "
        let after = try XCTUnwrap(ProxyEdit.plan([edit(emoji, "teh", "the")], checked: emoji, before: emoji))
        XCTAssertEqual(after.applied(to: emoji), "ok 👍🏽the ")
    }

    func testStaleTextIsNotEdited() {
        let checked = "I recieved teh "
        XCTAssertNil(ProxyEdit.plan([edit(checked, "teh", "the")], checked: checked, before: "Something else entirely"))
        XCTAssertNil(ProxyEdit.plan([edit(checked, "teh", "the")], checked: checked, before: checked + "\nnew paragraph"))
        XCTAssertNil(ProxyEdit.plan([], checked: checked, before: checked))
    }

    func testReplacingTheWholeSpan() throws {
        let plan = try XCTUnwrap(ProxyEdit.replacing("send it now", with: "Could you send it now?", before: "Hi. send it now"))
        XCTAssertEqual(plan.applied(to: "Hi. send it now"), "Hi. Could you send it now?")
    }
}

final class SuggestionTests: XCTestCase {
    func testLinkedEditsStayTogetherAndTheNearestComesFirst() {
        let edits = [
            WritingEdit(start: 0, end: 3, replacement: "The", original: "teh"),
            WritingEdit(start: 10, end: 14, replacement: "", original: "very", groupID: "g"),
            WritingEdit(start: 20, end: 20, replacement: " very", original: "", groupID: "g"),
        ]
        let result = RewriteResult(version: "t", text: "", edits: edits, source_map: [], elapsed_ms: 0, protected_count: 0, warnings: nil)
        let suggestions = Suggestion.from(result)
        XCTAssertEqual(suggestions.count, 2)
        XCTAssertEqual(suggestions[0].edits.count, 2)
        XCTAssertEqual(suggestions[1].title, "The")
        XCTAssertEqual(suggestions[1].detail, "teh → The")
        XCTAssertEqual(Suggestion(edits: [edits[1]]).title, "Remove “very”")
        XCTAssertEqual(Suggestion(edits: [WritingEdit(start: 3, end: 3, replacement: ",", original: "")]).title, "Add “,”")
        XCTAssertEqual(Suggestion.from(result, limit: 1).count, 1)
    }
}

final class SharedStoreTests: XCTestCase {
    private func store() -> SharedStore {
        let name = "parzr.tests.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: name)!
        addTeardownBlock { UserDefaults(suiteName: name)?.removePersistentDomain(forName: name) }
        return SharedStore(defaults: defaults)
    }

    func testHandoffRoundTrip() throws {
        let store = store()
        XCTAssertNil(store.pending())
        let posted = store.post(source: "send it now", mode: .professional)
        XCTAssertEqual(store.pending()?.id, posted.id)
        XCTAssertNil(store.finished())
        store.finish(posted.id, result: "Could you send it now?", note: nil)
        XCTAssertNil(store.pending())
        XCTAssertEqual(store.finished()?.result, "Could you send it now?")
        store.clearHandoff()
        XCTAssertNil(store.finished())
    }

    func testOldHandoffsExpireAndAnOtherIDIsIgnored() {
        let store = store()
        let posted = store.post(source: "a b c", mode: .friendly, now: Date(timeIntervalSinceNow: -SharedStore.handoffLifetime - 1))
        store.finish(UUID(), result: "x", note: nil)
        XCTAssertNil(store.pending())
        XCTAssertNil(store.finished())
        _ = posted
    }

    func testSettingsPersist() {
        let store = store()
        var settings = store.settings
        XCTAssertEqual(settings.dialect, "american")
        settings.dialect = "british"
        settings.names = ["Aman"]
        store.settings = settings
        XCTAssertEqual(store.settings, settings)
    }
}

final class EngineTests: XCTestCase {
    func testTheRustEngineFixesASentence() async throws {
        let result = try await ParzrEngine().check(EngineRequest(text: "i recieved teh report yesterday"))
        XCTAssertEqual(result.text, "I received the report yesterday")
        XCTAssertGreaterThanOrEqual(result.edits.count, 3)
    }

    func testTheMeaningGuardJudgesOutsideRewrites() async throws {
        let engine = ParzrEngine()
        let kept = try await engine.guardRewrite(mode: .professional, source: "can u send me the report by friday", output: "Here is the edited text: Could you send me the report by Friday?")
        XCTAssertTrue(kept.ok, kept.reason ?? "")
        XCTAssertEqual(kept.output, "Could you send me the report by Friday?")
        let changed = try await engine.guardRewrite(mode: .concise, source: "We need 12 chairs.", output: "We need 20 chairs.")
        XCTAssertFalse(changed.ok)
        XCTAssertTrue(ParzrEngine.isKnownMisspelling("teh"))
    }

    func testMemoryBudget() {
        XCTAssertTrue(MemoryBudget.engineFits(headroomMB: nil))
        XCTAssertFalse(MemoryBudget.engineFits(headroomMB: 60))
        XCTAssertTrue(MemoryBudget.engineFits(headroomMB: 2_000))
    }
}

final class ToneRewriterTests: XCTestCase {
    func testPromptsUseRealWordsAndNoPlaceholders() {
        for mode in RewriteMode.allCases {
            let prompt = ToneRewriter.instructions(for: mode)
            XCTAssertFalse(prompt.contains("ZXQPARZRKEEP"))
            XCTAssertTrue(prompt.contains("Return only the rewritten text"))
        }
        XCTAssertTrue(ToneRewriter.instructions(for: .friendly, dialect: "british").hasSuffix("Use British English."))
        XCTAssertEqual(ToneRewriter.clean("  \"Could you send it?\"\n"), "Could you send it?")
        XCTAssertEqual(ToneRewriter.clean("\"A\" and \"B\""), "\"A\" and \"B\"")
    }

    func testTheDeadlineReturnsEvenWhenTheWorkIgnoresCancellation() async {
        let clock = ContinuousClock()
        let start = clock.now
        do {
            _ = try await withTimeout(.milliseconds(100)) { () async throws -> Int in
                // Ignores cancellation, like a stalled system call.
                try? await Task.sleep(for: .seconds(5))
                return 1
            }
            XCTFail("expected a timeout")
        } catch {
            XCTAssertTrue(error is TimedOut)
        }
        XCTAssertLessThan(clock.now - start, .seconds(2))
        let value = try? await withTimeout(.seconds(2)) { 42 }
        XCTAssertEqual(value, 42)
    }

    func testRewriteWithoutTextOrModel() async {
        let outcome = await ToneRewriter().rewrite("   ", mode: .professional)
        XCTAssertEqual(outcome, .unchanged("Nothing to rewrite."))
        let fixed = await ToneRewriter().rewrite("i recieved teh report", mode: .fix)
        XCTAssertEqual(fixed, .rewritten("I received the report"))
    }
}
