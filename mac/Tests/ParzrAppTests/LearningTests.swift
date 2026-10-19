import XCTest
@testable import ParzrCore
@testable import Parzr

/// Learning from the user (muted suggestions, learned words), the private weekly summary, and Hinglish through the packaged engine.
/// Every Preferences here runs on its own throwaway suite, never the owner's defaults.
@MainActor
final class LearningTests: XCTestCase {
    private func prefs() throws -> (Preferences, () -> Void) {
        let name = "app.parzr.tests.learning"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: name)); defaults.removePersistentDomain(forName: name)
        return (Preferences(defaults: defaults), { defaults.removePersistentDomain(forName: name) })
    }
    private func edit(_ original: String, _ replacement: String, category: String = "Grammar", rule: String = "grammar.subject_third", explanation: String = "Use the verb form that matches the subject.") -> WritingEdit {
        WritingEdit(start: 0, end: original.utf16.count, replacement: replacement, original: original, category: category, ruleID: rule, explanation: explanation)
    }

    // MARK: Muted suggestions

    func testThreeIgnoresOfOneKindMuteItAndOnlyIt() {
        var mutes = SuggestionMutes()
        let review = edit("review", "reviews")
        XCTAssertNil(mutes.ignored(review, day: 1)); XCTAssertNil(mutes.ignored(review, day: 1))
        XCTAssertFalse(mutes.mutes(review), "two Ignores are not enough")
        let muted = mutes.ignored(edit("check", "checks"), day: 2)
        XCTAssertEqual(muted?.key, "grammar.subject_third", "a rule is muted as a whole, whatever the words")
        XCTAssertEqual(muted?.example, "check → checks")
        XCTAssertTrue(mutes.mutes(edit("go", "goes")))
        XCTAssertFalse(mutes.mutes(edit("its", "it's", rule: "punctuation.apostrophe")), "other rules still show")
        XCTAssertNil(mutes.ignored(review, day: 3), "a muted kind is not muted twice")
        XCTAssertEqual(mutes.muted.count, 1)
        mutes.unmute("grammar.subject_third")
        XCTAssertFalse(mutes.mutes(review))
    }
    func testModelAndNameRulesAreMutedForOneSuggestionOnly() {
        var mutes = SuggestionMutes()
        let article = edit("", "a ", rule: "gector.append")
        for _ in 0..<3 { mutes.ignored(article, day: 1) }
        XCTAssertTrue(mutes.mutes(article))
        XCTAssertFalse(mutes.mutes(edit("", ". ", category: "Punctuation", rule: "gector.append")), "a model rule is muted per suggestion, not as a whole")
        let jira = edit("jira", "Jira", category: "Capitalization", rule: "grammar.proper_noun_capitalization")
        for _ in 0..<3 { mutes.ignored(jira, day: 1) }
        XCTAssertTrue(mutes.mutes(jira))
        XCTAssertFalse(mutes.mutes(edit("figma", "Figma", category: "Capitalization", rule: "grammar.proper_noun_capitalization")))
    }
    func testSpellingAndToneAreNeverMutedAndApplyingResetsTheCount() {
        var mutes = SuggestionMutes()
        let typo = edit("recieved", "received", category: "Spelling", rule: "grammar.phrase.23")
        for _ in 0..<5 { XCTAssertNil(mutes.ignored(typo, day: 1)) }
        XCTAssertNil(SuggestionMutes.key(for: typo)); XCTAssertNil(SuggestionMutes.key(for: edit("a", "b", category: "Style", rule: "local-model")))
        let comma = edit(",", ".", category: "Punctuation", rule: "punctuation.comma_splice")
        mutes.ignored(comma, day: 1); mutes.ignored(comma, day: 1)
        mutes.applied(comma)
        XCTAssertNil(mutes.ignored(comma, day: 1), "an applied fix starts the count over")
        XCTAssertFalse(mutes.mutes(comma))
        mutes.reset(); XCTAssertEqual(mutes, SuggestionMutes())
    }
    func testPreferencesMutePersistsAndScreensResults() throws {
        let (prefs, cleanup) = try prefs(); defer { cleanup() }
        let review = edit("review", "reviews")
        for _ in 0..<Preferences.ignoresToMute { prefs.noteIgnored(review) }
        XCTAssertTrue(prefs.isMuted(review))
        let name = "app.parzr.tests.learning"
        let restored = Preferences(defaults: try XCTUnwrap(UserDefaults(suiteName: name)))
        XCTAssertTrue(restored.isMuted(review), "mutes persist across launches")
        XCTAssertEqual(restored.mutes.muted.first?.explanation, "Use the verb form that matches the subject.")
        restored.unmute("grammar.subject_third"); XCTAssertFalse(restored.isMuted(review))
    }
    func testScreenedDropsMutedEditsAndTheirLinkedPartners() throws {
        let text = "PR review kar lena"
        let a = WritingEdit(start: 3, end: 9, replacement: "reviews", original: "review", category: "Grammar", ruleID: "grammar.subject_third", groupID: "g")
        let b = WritingEdit(start: 0, end: 2, replacement: "The PR", original: "PR", category: "Grammar", ruleID: "grammar.article", groupID: "g")
        let result = RewriteResult(version: "t", text: try EditPlan.apply([b, a], to: text), edits: [b, a], source_map: [], elapsed_ms: 0, protected_count: 0, warnings: nil)
        var mutes = SuggestionMutes()
        for _ in 0..<3 { mutes.ignored(a, day: 1) }
        let kept = result.dropping(from: text) { mutes.mutes($0) }
        XCTAssertTrue(kept.edits.isEmpty); XCTAssertEqual(kept.text, text)
    }

    // MARK: Learned words

    func testWordTokensAcceptJargonAndRejectProse() {
        for (raw, word) in [("gector", "gector"), ("K8s", "K8s"), ("pgvector,", "pgvector"), ("“OKRs”", "OKRs"), ("e2e", "e2e"), ("Next.js", "Next.js"), ("C++", "C++"), ("GitHub's", "GitHub")] {
            XCTAssertEqual(LearnedWord.token(raw), word, raw)
        }
        for raw in ["a", "two words", "1234", "", String(repeating: "x", count: 65), "semi;colon"] { XCTAssertNil(LearnedWord.token(raw), raw) }
        XCTAssertTrue(LearnedWord.isNameShaped("Aman")); XCTAssertTrue(LearnedWord.isNameShaped("GitHub"))
        XCTAssertFalse(LearnedWord.isNameShaped("gector")); XCTAssertFalse(LearnedWord.isNameShaped("K8s"))
    }
    func testIgnoringALowercaseWordTwiceLearnsItAsAWordNotAName() throws {
        let (prefs, cleanup) = try prefs(); defer { cleanup() }
        let jargon = edit("gector", "sector", category: "Spelling", rule: "spelling.delete_index")
        prefs.noteIgnored(jargon); XCTAssertTrue(prefs.learnedWords.isEmpty)
        prefs.noteIgnored(jargon)
        XCTAssertEqual(prefs.learnedWords, ["gector"]); XCTAssertTrue(prefs.learnedNames.isEmpty, "a lowercase word is never re-cased as a name")
        let product = edit("K8s", "Kids", category: "Spelling", rule: "spelling.delete_index")
        prefs.noteIgnored(product); prefs.noteIgnored(product)
        XCTAssertEqual(prefs.learnedWords, ["gector", "K8s"])
        let person = edit("Aman", "Amen", category: "Spelling", rule: "spelling.delete_index")
        prefs.noteIgnored(person); prefs.noteIgnored(person)
        XCTAssertEqual(prefs.learnedNames, ["Aman"], "a capitalized word is still learned as a name")
        XCTAssertFalse(prefs.learnWord("GECTOR"), "case-insensitive duplicates are refused")
        XCTAssertFalse(prefs.learnWord("aman"), "a learned name is not learned again as a word")
    }
    func testLearnedWordsGoToTheEngineAsDictionaryWordsAfterTheUsersOwn() {
        XCTAssertEqual(KnownNames.merge(["parzr", "Gector"], ["gector", "pgvector"], limit: 1000), ["parzr", "Gector", "pgvector"])
        XCTAssertEqual(KnownNames.merge((0..<990).map { "u\($0)" }, (0..<50).map { "w\($0)" }, limit: 1000).count, 1000, "the engine's 1000-entry limit holds, the user's words first")
    }
    func testKnownWordsFileSharesLearnedWordsInItsDictionary() throws {
        let data = try KnownWordsFile.data(dictionary: KnownNames.merge(["parzr"], ["gector"]), names: ["Aman"])
        let object = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
        XCTAssertEqual(object["dictionary"] as? [String], ["parzr", "gector"])
    }

    // MARK: Weekly summary

    func testWeeklySummaryCountsByKindAndRanksSlips() {
        var stats = WritingStats()
        let typo = edit("recieved", "received", category: "Spelling", rule: "grammar.phrase.23")
        stats.recordFixes([typo, typo, edit("teh", "the", category: "Spelling", rule: "grammar.phrase.21"), edit("go", "goes", category: "Agreement"), edit(",", ".", category: "Punctuation", rule: "p")], day: 100)
        stats.recordFixes([edit("Hi", "Hi,", category: "Punctuation", rule: "p"), edit("i", "I", category: "Capitalization", rule: "c"), edit("very unique", "unique", category: "Clarity", rule: "s")], day: 102)
        stats.recordIgnore(day: 102)
        stats.recordFixes([edit("x", "y")], day: 95) // the week before
        let week = stats.summary(today: 102)
        XCTAssertEqual(week.fixes, 8); XCTAssertEqual(week.previousFixes, 1)
        XCTAssertEqual(week.categories.map(\.name), ["Spelling", "Punctuation", "Capitalization", "Grammar", "Style"], "most first, ties by name")
        XCTAssertEqual(week.categories.first?.count, 3)
        XCTAssertEqual(week.slips.map(\.name), ["recieved → received", "teh → the"])
        XCTAssertEqual(week.slips.first?.count, 2)
        XCTAssertEqual(week.ignored, 1); XCTAssertEqual(week.activeDays, 2); XCTAssertEqual(week.busiestDay, 100)
        XCTAssertEqual(week.trend, "7 more than last week")
        XCTAssertEqual(stats.summary(today: 120).fixes, 0, "a quiet week shows nothing")
        XCTAssertNil(stats.summary(today: 120).trend)
    }
    func testSummaryKeepsFourWeeksAndBoundsSlipsWithoutSentences() throws {
        var stats = WritingStats()
        for day in 0..<40 { stats.recordFixes([edit("teh", "the", category: "Spelling", rule: "r")], day: day) }
        XCTAssertEqual(stats.days.count, WritingStats.keepDays); XCTAssertNil(stats.days[11]); XCTAssertNotNil(stats.days[12])
        stats.recordFixes((0..<100).map { edit("wrd\($0)", "word\($0)x", category: "Spelling", rule: "r") }, day: 50)
        XCTAssertLessThanOrEqual(stats.days[50]?.slips.count ?? 0, WritingStats.slipsPerDay)
        XCTAssertNil(WritingStats.slip(edit("this is a long sentence", "something else", category: "Spelling")), "only single-word slips are kept")
        XCTAssertNil(WritingStats.slip(edit("its", "it's", category: "Grammar")))
        let json = String(decoding: try JSONEncoder().encode(stats), as: UTF8.self)
        XCTAssertFalse(json.contains("sentence"))
    }
    func testPreferencesRecordFixesOnlyWhileTheSummaryIsKept() throws {
        let (prefs, cleanup) = try prefs(); defer { cleanup() }
        XCTAssertTrue(prefs.keepsWritingSummary, "on by default: it never leaves the Mac")
        prefs.noteFixes([edit("teh", "the", category: "Spelling", rule: "r")])
        XCTAssertEqual(prefs.stats.summary(today: LearningDay.today()).fixes, 1)
        prefs.keepsWritingSummary = false
        XCTAssertTrue(prefs.stats.isEmpty, "turning it off forgets the counts")
        prefs.noteFixes([edit("teh", "the", category: "Spelling", rule: "r")]); prefs.noteIgnored(edit("go", "goes"))
        XCTAssertTrue(prefs.stats.isEmpty)
        prefs.keepsWritingSummary = true; prefs.noteFixes([edit("teh", "the", category: "Spelling", rule: "r")]); prefs.clearWritingSummary()
        XCTAssertTrue(prefs.stats.isEmpty)
    }
    func testTurningTheSummaryOffErasesItsStoredRecords() throws {
        let name = "app.parzr.tests.summary-off"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: name)); defaults.removePersistentDomain(forName: name); defer { defaults.removePersistentDomain(forName: name) }
        let prefs = Preferences(defaults: defaults)
        prefs.noteFixes([edit("teh", "the", category: "Spelling", rule: "r")]); prefs.noteIgnored(edit("go", "goes"))
        XCTAssertFalse(Preferences(defaults: defaults).stats.isEmpty, "kept between launches while on")
        prefs.keepsWritingSummary = false
        XCTAssertTrue(Preferences(defaults: defaults).stats.isEmpty, "off erases the stored tally, not just the one in memory")
    }
    func testEraseAllDataForgetsEverythingButSetupAndTheReportsChoice() throws {
        let name = "app.parzr.tests.erase"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: name)); defaults.removePersistentDomain(forName: name); defer { defaults.removePersistentDomain(forName: name) }
        let prefs = Preferences(defaults: defaults)
        prefs.onboardingCompleted = true; prefs.shareReports = false
        prefs.saveWord("kubectl"); _ = prefs.learnName("Anaya"); _ = prefs.learnWord("pgvector"); prefs.toggleApp("com.example.chat")
        prefs.appearance = "paper"; prefs.checkingDelay = 300; prefs.shortcutKey = 12; prefs.useContactNames = true; prefs.keepsWritingSummary = true
        prefs.pauseAutomaticChecking(for: "com.example.mail", duration: .oneHour)
        for _ in 0..<SuggestionMutes.ignoresToMute { prefs.noteIgnored(edit("go", "goes")) }
        prefs.noteFixes([edit("teh", "the", category: "Spelling", rule: "r")])
        prefs.noteSighting("zarkon", app: "com.example.a", day: 1)
        defaults.set(true, forKey: "someOtherKey")
        let known = FileManager.default.temporaryDirectory.appendingPathComponent("parzr-erase-\(UUID().uuidString)/known-words.json")
        try KnownWordsFile.write(dictionary: ["kubectl"], names: ["Anaya"], to: known)
        var purged = 0
        XCTAssertFalse(prefs.stats.isEmpty); XCTAssertFalse(prefs.mutes.muted.isEmpty)
        prefs.eraseAllData(knownWords: known, purgeReports: { purged += 1 })
        XCTAssertEqual(purged, 1, "queued reports are purged through the reports queue")
        XCTAssertFalse(FileManager.default.fileExists(atPath: known.path), "known-words.json is gone")
        XCTAssertNil(defaults.object(forKey: "someOtherKey"))
        XCTAssertTrue(prefs.onboardingCompleted, "setup stays finished")
        XCTAssertFalse(prefs.shareReports, "erasing never turns reports back on")
        // Everything else matches a first launch, in memory and on disk.
        let empty = try XCTUnwrap(UserDefaults(suiteName: name + ".fresh")); empty.removePersistentDomain(forName: name + ".fresh"); defer { empty.removePersistentDomain(forName: name + ".fresh") }
        for (label, current) in [("now", prefs), ("reloaded", Preferences(defaults: defaults))] {
            let fresh = Preferences(defaults: empty)
            XCTAssertEqual(current.dictionary, fresh.dictionary, label); XCTAssertEqual(current.learnedNames, fresh.learnedNames, label); XCTAssertEqual(current.learnedWords, fresh.learnedWords, label)
            XCTAssertEqual(current.disabledApps, fresh.disabledApps, label); XCTAssertEqual(current.automaticAppPauses, fresh.automaticAppPauses, label)
            XCTAssertEqual(current.mutes, fresh.mutes, label); XCTAssertEqual(current.stats, fresh.stats, label); XCTAssertEqual(current.ledger, fresh.ledger, label)
            XCTAssertEqual(current.passive, fresh.passive, label); XCTAssertEqual(current.paused, fresh.paused, label); XCTAssertEqual(current.dialect, fresh.dialect, label)
            XCTAssertEqual(current.defaultMode, fresh.defaultMode, label); XCTAssertEqual(current.clipboardFallback, fresh.clipboardFallback, label)
            XCTAssertEqual(current.shortcutKey, fresh.shortcutKey, label); XCTAssertEqual(current.shortcutModifiers, fresh.shortcutModifiers, label); XCTAssertEqual(current.shortcutLabel, fresh.shortcutLabel, label)
            XCTAssertEqual(current.checkingDelay, fresh.checkingDelay, label); XCTAssertEqual(current.selectedTextPopover, fresh.selectedTextPopover, label); XCTAssertEqual(current.highlightFill, fresh.highlightFill, label)
            XCTAssertEqual(current.editorFontSize, fresh.editorFontSize, label); XCTAssertEqual(current.editorLineSpacing, fresh.editorLineSpacing, label); XCTAssertEqual(current.appearance, fresh.appearance, label)
            XCTAssertEqual(current.reduceMotion, fresh.reduceMotion, label); XCTAssertEqual(current.contextRefinement, fresh.contextRefinement, label); XCTAssertEqual(current.smartGrammar, fresh.smartGrammar, label)
            XCTAssertEqual(current.toneCheck, fresh.toneCheck, label); XCTAssertEqual(current.slipCheck, fresh.slipCheck, label); XCTAssertEqual(current.showWordCount, fresh.showWordCount, label)
            XCTAssertEqual(current.showInDock, fresh.showInDock, label); XCTAssertEqual(current.checkVSCode, fresh.checkVSCode, label)
            XCTAssertEqual(current.firefoxHintDismissed, fresh.firefoxHintDismissed, label); XCTAssertEqual(current.docsHintDismissed, fresh.docsHintDismissed, label)
            XCTAssertEqual(current.useContactNames, fresh.useContactNames, label); XCTAssertEqual(current.nameCapitalization, fresh.nameCapitalization, label)
            XCTAssertEqual(current.keepsWritingSummary, fresh.keepsWritingSummary, label)
        }
    }
    func testLocalDaysTurnOverAtLocalMidnight() throws {
        let zone = try XCTUnwrap(TimeZone(identifier: "Asia/Kolkata"))
        // 2026-10-18 20:00 UTC is 01:30 on the 19th in India.
        let late = Date(timeIntervalSince1970: 1_792_353_600)
        XCTAssertEqual(LearningDay.today(late, zone: zone), LearningDay.today(late, zone: TimeZone(identifier: "UTC")!) + 1)
        XCTAssertEqual(WeeklySummary(fixes: 1, previousFixes: 0, categories: [], slips: [], ignored: 0, activeDays: 1, busiestDay: 20_745).busiestDayName, "Monday")
    }

    // MARK: Hinglish (the packaged engine; skipped without it)

    func testHinglishThroughTheAppsEngineWithNativeHints() async throws {
        guard ProcessInfo.processInfo.environment["PARZR_ENGINE_PATH"] != nil else { throw XCTSkip("Supply the built engine library with PARZR_ENGINE_PATH.") }
        for text in ["yaar kal meeting hai, theek hai?", "tum kaha ho, call karo", "client ko call karna hai", "please ek baar check kar lo", "PR review kar lena", "haan bhai, main aa raha hoon."] {
            let result = try await WritingEngine.typing.rewrite(EngineRequest(text: text))
            // Hindi words are never respelled; the sentence start takes a capital like any other.
            let expected = text.prefix(1).uppercased() + text.dropFirst()
            XCTAssertEqual(result.text, expected, "\(text): \(result.edits.map { "\($0.original)→\($0.replacement) \($0.rule_id)" })")
        }
        let mixed = try await WritingEngine.typing.rewrite(EngineRequest(text: "sab theek hai, dont worry"))
        XCTAssertEqual(mixed.text, "Sab theek hai, don't worry", "an English slip in Hinglish is still fixed")
    }
}
