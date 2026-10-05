import XCTest
import AppKit
import SwiftUI
import ParzrCore
@testable import Parzr

@MainActor
final class PlaygroundTests: XCTestCase {
    /// Tests that press Ignore on "mesage" write to the shared preferences; after two runs Parzr would learn it as a name and stop fixing it.
    override func setUp() async throws { Preferences.shared.learnedNames = [] }
    func testCopiedSelectionComparisonIgnoresTrailingNewlinesOnly() {
        XCTAssertTrue(SelectionSnapshot.sameCopiedText("Hello world", "Hello world\n"))
        XCTAssertTrue(SelectionSnapshot.sameCopiedText("Hello world\r\n", "Hello world"))
        XCTAssertFalse(SelectionSnapshot.sameCopiedText("Hello world", "Hello there"))
        XCTAssertFalse(SelectionSnapshot.sameCopiedText("a\nb", "ab"))
    }

    func testWritingPreferencesPersistAndBoundRuntimeValues() throws {
        let name = "app.parzr.tests.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: name))
        defer { defaults.removePersistentDomain(forName: name) }
        let prefs = Preferences(defaults: defaults)
        XCTAssertTrue(prefs.selectedTextPopover)
        XCTAssertTrue(prefs.contextRefinement)
        prefs.selectedTextPopover = false; prefs.contextRefinement = false
        prefs.appearance = "paper"; prefs.reduceMotion = true
        prefs.checkingDelay = 10000; prefs.editorFontSize = -10; prefs.editorLineSpacing = .nan
        let restored = Preferences(defaults: defaults)
        XCTAssertFalse(restored.selectedTextPopover)
        XCTAssertFalse(restored.contextRefinement)
        XCTAssertEqual(restored.appearance, "paper")
        XCTAssertTrue(restored.reduceMotion)
        XCTAssertEqual(restored.boundedCheckingDelay, 700)
        XCTAssertEqual(restored.boundedFontSize, 15)
        XCTAssertEqual(restored.boundedLineSpacing, 6)
    }
    func testOneClickAppliesLinkedPartsAndUndoRestoresTheDraft() throws {
        _ = NSApplication.shared
        let editor = CorrectionTextView(); editor.allowsUndo = true
        let window = NSWindow(contentRect:NSRect(x:0,y:0,width:480,height:240),styleMask:[.borderless],backing:.buffered,defer:false)
        window.isReleasedWhenClosed = false; window.contentView = editor; window.makeFirstResponder(editor)
        defer { window.close() }
        editor.string = "Not only Mira did help."
        let edits = [WritingEdit(start:8,end:8,replacement:" did",original:"",groupID:"order:8"),WritingEdit(start:13,end:17,replacement:"",original:" did",groupID:"order:8")]
        editor.suggestions = edits; editor.accept(edits[0])
        XCTAssertEqual(editor.string,"Not only did Mira help.")
        editor.undoManager?.undo(); XCTAssertEqual(editor.string,"Not only Mira did help.")
    }
    func testInsertionCorrectionsHaveClickableCharacterAnchors() {
        let editor = CorrectionTextView()
        editor.string = "Hello🙂"
        let edit = WritingEdit(start: 7, end: 7, replacement: ".", original: "")
        XCTAssertEqual(editor.displayRange(for: edit), NSRange(location: 5, length: 2))
        editor.string = "Hello"
        XCTAssertNil(editor.displayRange(for: edit), "An insertion from a stale draft cannot keep its mark.")
    }
    func testSentenceRangesCoverOnlySentencesWithEditsTrimmed() {
        let source = "You are not doing good. This is fine. This si do bad."
        let ns = source as NSString
        let good = ns.range(of: "good"), si = ns.range(of: "si")
        let edits = [WritingEdit(start: good.location, end: NSMaxRange(good), replacement: "well", original: "good"), WritingEdit(start: si.location, end: NSMaxRange(si), replacement: "is", original: "si")]
        let ranges = SentencePreview.sentenceRanges(in: source, containing: edits)
        XCTAssertEqual(ranges.map { ns.substring(with: $0) }, ["You are not doing good.", "This si do bad."])
    }
    func testSentencePreviewShowsTheCompleteCorrectedSentenceWithUnicode() {
        let source = "Hi 🙂. Please chek this mesage. Thanks."
        let check = (source as NSString).range(of: "chek")
        let message = (source as NSString).range(of: "mesage")
        let edits = [WritingEdit(start: check.location, end: NSMaxRange(check), replacement: "check", original: "chek"), WritingEdit(start: message.location, end: NSMaxRange(message), replacement: "message", original: "mesage")]
        XCTAssertEqual(SentencePreview.text(source: source, edits: edits, focused: edits[0]), "Please check this message.")
        let thanks = (source as NSString).range(of: "Thanks")
        let outside = WritingEdit(start: thanks.location, end: NSMaxRange(thanks), replacement: "Thank you", original: "Thanks")
        XCTAssertEqual(SentencePreview.edits(source: source, edits: edits + [outside], focused: edits[0]), edits)
    }
    func testNativeMenuActionsAndCheckStates() throws {
        _ = NSApplication.shared
        let delegate = AppDelegate(); let menu = NSMenu()
        let paused = Preferences.shared.paused; let automatic = Preferences.shared.passive
        defer { Preferences.shared.paused = paused; Preferences.shared.passive = automatic }
        delegate.menuNeedsUpdate(menu)
        for item in menu.items where item.action != nil {
            XCTAssertTrue((item.target as? NSObject)?.responds(to: item.action!) == true, item.title)
        }
        let pause = try XCTUnwrap(menu.items.first { $0.title == "Pause suggestions" })
        XCTAssertTrue(NSApp.sendAction(pause.action!, to: pause.target, from: pause))
        XCTAssertEqual(Preferences.shared.paused, !paused)
        delegate.menuNeedsUpdate(menu)
        XCTAssertEqual(menu.items.first { $0.title == "Pause suggestions" }?.state, !paused ? .on : .off)
        let highlights = try XCTUnwrap(menu.items.first { $0.title == "Automatic highlights" })
        XCTAssertTrue(NSApp.sendAction(highlights.action!, to: highlights.target, from: highlights))
        XCTAssertEqual(Preferences.shared.passive, !automatic)
    }

    func testCompactControlsActuallyNavigateAndIgnore() async throws {
        guard ProcessInfo.processInfo.environment["PARZR_ENGINE_PATH"] != nil else { throw XCTSkip("Supply the built engine library.") }
        let model = AppModel(); model.playground("I recieved your mesage.")
        for _ in 0..<3000 where model.busy { try await Task.sleep(for: .milliseconds(20)) } // up to 60 s: CI runners load the model slowly
        XCTAssertEqual(model.chosenEdits.count, 2)
        let host = NSHostingView(rootView: RewritePanel(model: model))
        let window = NSWindow(contentRect: NSRect(origin: .zero, size: RewritePanel.size), styleMask: [.borderless], backing: .buffered, defer: false)
        window.isReleasedWhenClosed = false; window.contentView = host
        defer { window.close() }
        window.orderFront(nil)
        window.layoutIfNeeded(); host.layoutSubtreeIfNeeded()
        try await Task.sleep(for: .milliseconds(100))
        let next = try XCTUnwrap(NativeControls.find(label: "Next correction", in: host))
        XCTAssertTrue(next.accessibilityPerformPress())
        XCTAssertEqual(model.focusedEdit?.original, "mesage")
        try await Task.sleep(for: .milliseconds(50))
        let ignore = try XCTUnwrap(NativeControls.find(label: "Ignore", in: host))
        XCTAssertTrue(ignore.accessibilityPerformPress())
        XCTAssertEqual(model.chosenEdits.count, 1)
        XCTAssertEqual(model.focusedEdit?.original, "recieved")
    }

    func testCorrectionPopoverFitsTheScreenEdges() {
        let visible = CGRect(x: -1400, y: 0, width: 1400, height: 900)
        for anchor in [CGRect(x: -15, y: 10, width: 10, height: 20), CGRect(x: -1390, y: 850, width: 30, height: 20)] {
            let origin = CorrectionPlacement.origin(anchor: anchor, size: RewritePanel.size, visible: visible)
            XCTAssertTrue(visible.contains(CGRect(origin: origin, size: RewritePanel.size)))
        }
        XCTAssertLessThanOrEqual(RewritePanel.size.width, 360)
        XCTAssertLessThanOrEqual(RewritePanel.size.height, 240)
        let whitespace = WritingEdit(start: 0, end: 0, replacement: " ", original: "")
        XCTAssertEqual(whitespace.replacementLabel, "Add space")
    }
    func testNewDraftInvalidatesCorrectionsBeforeDebounce() async throws {
        guard ProcessInfo.processInfo.environment["PARZR_ENGINE_PATH"] != nil else { throw XCTSkip("Supply the built engine library.") }
        let model = AppModel()
        model.playground("I recieved your mesage.")
        for _ in 0..<3000 where model.busy { try await Task.sleep(for: .milliseconds(20)) } // up to 60 s: CI runners load the model slowly
        XCTAssertFalse(model.chosenEdits.isEmpty)
        model.playground("A completely different draft.", debounce: true)
        XCTAssertEqual(model.source, "A completely different draft.")
        XCTAssertTrue(model.busy)
        XCTAssertNil(model.result)
        XCTAssertTrue(model.chosenEdits.isEmpty)
        XCTAssertEqual(model.preview, "A completely different draft.")
        model.clearSession()
        try await Task.sleep(for: .milliseconds(400))
        XCTAssertEqual(model.source, "")
        XCTAssertNil(model.result, "A cancelled debounce must not resurrect a cleared session.")
    }

    func testMarkedCorrectionUsesNativeTypingAndUndo() async throws {
        let window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 420, height: 360), styleMask: [.titled], backing: .buffered, defer: false)
        window.isReleasedWhenClosed = false
        let editor = CorrectionTextView(frame: NSRect(x: 0, y: 0, width: 420, height: 360))
        editor.isRichText = false; editor.allowsUndo = true; editor.string = "Please chek this."
        window.contentView = editor
        window.makeFirstResponder(editor)
        defer { window.close() }
        let edit = WritingEdit(start: 7, end: 11, replacement: "check", original: "chek")
        editor.suggestions = [edit]
        editor.accept(edit)
        XCTAssertEqual(editor.string, "Please check this.")
        XCTAssertTrue(editor.undoManager?.canUndo == true)
        editor.undoManager?.undo()
        XCTAssertEqual(editor.string, "Please chek this.")
        editor.string = "Please chat this."
        editor.accept(edit)
        XCTAssertEqual(editor.string, "Please chat this.", "A stale correction must not replace a new word.")
    }
    func testEditorHasAnEditableViewportAfterLayout() async throws {
        let host = NSHostingView(rootView: DraftEditor(text: .constant("I recieved your mesage."), edits: []))
        let window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 420, height: 360), styleMask: [.borderless], backing: .buffered, defer: false)
        window.isReleasedWhenClosed = false
        window.contentView = host
        defer { window.close() }
        window.layoutIfNeeded(); host.layoutSubtreeIfNeeded()
        try await Task.sleep(for: .milliseconds(100))
        window.layoutIfNeeded(); host.layoutSubtreeIfNeeded()
        func findEditor(_ view: NSView) -> NSTextView? {
            if let editor = view as? NSTextView { return editor }
            return view.subviews.compactMap(findEditor).first
        }
        let editor = try XCTUnwrap(findEditor(host))
        XCTAssertGreaterThan(editor.bounds.width, 300)
        XCTAssertGreaterThan(editor.bounds.height, 200, "The text editor must accept clicks below the first line.")
        XCTAssertTrue(editor.isEditable)
        XCTAssertEqual(editor.string, "I recieved your mesage.")
    }

    func testPlaygroundAnalysisUsesThePackagedBridge() async throws {
        guard ProcessInfo.processInfo.environment["PARZR_ENGINE_PATH"] != nil else { throw XCTSkip("Supply the built engine library.") }
        let model = AppModel()
        model.playground("I recieved your mesage.")
        for _ in 0..<3000 where model.busy { try await Task.sleep(for: .milliseconds(20)) } // up to 60 s: CI runners load the model slowly
        XCTAssertNil(model.error)
        XCTAssertEqual(model.preview, "I received your message.")
        XCTAssertEqual(model.chosenEdits.count, 2)
    }

    func testCommonGrammarThroughNativeLinguisticHints() async throws {
        guard ProcessInfo.processInfo.environment["PARZR_ENGINE_PATH"] != nil else { throw XCTSkip("Supply the built engine library.") }
        for (input, expected) in [
            ("this si too bod", "This is too bad"),
            ("This is not how it is suppose to be donme.", "This is not how it is supposed to be done."),
            ("Maya cna finish the task.", "Maya can finish the task."),
            ("The invitation was deliver this morning.", "The invitation was delivered this morning."),
            ("He go to school every day.", "He goes to school every day."),
            ("She walk to work.", "She walks to work."),
            ("This are wrong.", "This is wrong."),
            ("I am agree with you.", "I agree with you."),
            ("She is more smarter than me.", "She is smarter than me."),
            ("I have a apple.", "I have an apple.")
        ] {
            let result = try await WritingEngine.shared.rewrite(EngineRequest(text: input))
            XCTAssertEqual(result.text, expected)
        }
    }
}

final class KnownNamesTests: XCTestCase {
    func testUserNameTokensAndFullName() {
        XCTAssertEqual(KnownNames.names(full: "Aman Jain", short: "ajain"), ["Aman", "Jain", "ajain", "Aman Jain"])
        XCTAssertEqual(KnownNames.names(full: "Madonna", short: "m"), ["Madonna"])
        XCTAssertEqual(KnownNames.names(full: "", short: ""), [])
    }
    func testMergeDedupesCaseInsensitivelyAndRespectsLimits() {
        XCTAssertEqual(KnownNames.merge(["Zed", "parzr"], ["aman", "Parzr"], ["Aman", "", String(repeating: "a", count: 129)]), ["Zed", "parzr", "aman"])
        XCTAssertEqual(KnownNames.merge((0..<1200).map { "w\($0)" }).count, 1000)
    }
    func testDocumentNamesFindCapitalizedNamesOnly() {
        let names = KnownNames.documentNames(in: "Yesterday Aman Jain met Satya Nadella in London. aman agreed that the table was fine.")
        XCTAssertTrue(names.contains("Aman"), "\(names)")
        XCTAssertTrue(names.contains("London"), "\(names)")
        XCTAssertFalse(names.contains("table"))
        XCTAssertTrue(names.allSatisfy { $0.contains(where: \.isUppercase) })
    }
}

@MainActor
final class NameHandlingTests: XCTestCase {
    private func prefs() throws -> (Preferences, () -> Void) {
        let name = "app.parzr.tests.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: name))
        return (Preferences(defaults: defaults), { defaults.removePersistentDomain(forName: name) })
    }
    func testNamesMergeAllSourcesWithinLimits() {
        let merged = KnownNames.merge(["Aman", "Jain"], ["aman", "Priya"], ["Acme Corp", String(repeating: "x", count: 129)], limit: KnownNames.maxNames)
        XCTAssertEqual(merged, ["Aman", "Jain", "Priya", "Acme Corp"])
        XCTAssertEqual(KnownNames.merge((0..<2500).map { "n\($0)" }, limit: KnownNames.maxNames).count, 2000)
    }
    func testCapitalizedMidSentenceWordsCountAsNames() {
        let found = KnownNames.capitalizedMidSentence(in: "Hi Aman,\nI met Priya's cousin. Then Maria left. NASA called I think.")
        XCTAssertEqual(found, ["Aman", "Priya", "Maria"], "\(found)")
    }
    func testDocumentNamesNeedNoTaggerHit() {
        XCTAssertTrue(KnownNames.documentNames(in: "Thanks, see you soon. Hi Aman, welcome.").contains("Aman"))
    }
    func testIgnoringTwiceLearnsAName() throws {
        let (prefs, cleanup) = try prefs(); defer { cleanup() }
        let edit = WritingEdit(start: 0, end: 5, replacement: "Amen", original: "Aman", category: "Spelling")
        prefs.noteIgnored(edit)
        XCTAssertTrue(prefs.learnedNames.isEmpty)
        prefs.noteIgnored(edit)
        XCTAssertEqual(prefs.learnedNames, ["Aman"])
        // Counts persist across launches and unrelated categories never count.
        let other = WritingEdit(start: 0, end: 3, replacement: "the", original: "teh", category: "Grammar")
        prefs.noteIgnored(other); prefs.noteIgnored(other)
        XCTAssertEqual(prefs.learnedNames, ["Aman"])
        XCTAssertEqual(Preferences.ignoresToLearn, 2)
    }
    func testLearnNameStripsPossessiveAndRejectsNonNames() throws {
        let (prefs, cleanup) = try prefs(); defer { cleanup() }
        XCTAssertTrue(prefs.learnName("Aman\u{2019}s")); XCTAssertEqual(prefs.learnedNames, ["Aman"])
        XCTAssertFalse(prefs.learnName("aman")); XCTAssertFalse(prefs.learnName("a1b")); XCTAssertFalse(prefs.learnName(String(repeating: "a", count: 129)))
        XCTAssertTrue(prefs.learnName("Jean-Luc Picard")); XCTAssertEqual(prefs.learnedNames.count, 2)
    }
    func testCapitalizeNamesMappingByBundle() throws {
        let (prefs, cleanup) = try prefs(); defer { cleanup() }
        XCTAssertEqual(prefs.nameCapitalization, "documents")
        XCTAssertTrue(prefs.capitalizeNames(for: nil)); XCTAssertTrue(prefs.capitalizeNames(for: "com.apple.mail"))
        XCTAssertFalse(prefs.capitalizeNames(for: "com.tinyspeck.slackmacgap"))
        prefs.nameCapitalization = "never"; XCTAssertFalse(prefs.capitalizeNames(for: "com.apple.mail")); XCTAssertFalse(prefs.capitalizeNames(for: nil))
        prefs.nameCapitalization = "everywhere"; XCTAssertTrue(prefs.capitalizeNames(for: "com.tinyspeck.slackmacgap"))
    }
    func testChatAppsStayQuietUnlessEverywhere() {
        XCTAssertEqual(NameCapitalization.chatApps, ["com.tinyspeck.slackmacgap", "com.microsoft.teams", "com.microsoft.teams2", "net.whatsapp.WhatsApp", "desktop.WhatsApp", "com.hnc.Discord", "ru.keepcoder.Telegram", "com.apple.MobileSMS", "com.facebook.archon"])
        for bundle in NameCapitalization.chatApps { XCTAssertFalse(NameCapitalization.documents.enabled(bundle: bundle), bundle); XCTAssertTrue(NameCapitalization.everywhere.enabled(bundle: bundle)) }
    }
    func testKnownWordsFileShapeAndAtomicWrite() throws {
        let data = try KnownWordsFile.data(dictionary: ["parzr"], names: ["Aman", "Jain"])
        let json = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
        XCTAssertEqual(Set(json.keys), ["version", "dictionary", "names"])
        XCTAssertEqual(json["version"] as? Int, 1); XCTAssertEqual(json["dictionary"] as? [String], ["parzr"]); XCTAssertEqual(json["names"] as? [String], ["Aman", "Jain"])
        let dir = FileManager.default.temporaryDirectory.appendingPathComponent("parzr-\(UUID().uuidString)/Parzr")
        defer { try? FileManager.default.removeItem(at: dir.deletingLastPathComponent()) }
        let url = dir.appendingPathComponent("known-words.json")
        try KnownWordsFile.write(dictionary: ["a"], names: ["B"], to: url); try KnownWordsFile.write(dictionary: ["c"], names: [], to: url)
        XCTAssertEqual(try JSONSerialization.jsonObject(with: Data(contentsOf: url)) as? [String: AnyHashable], ["version": 1, "dictionary": ["c"], "names": [String]()] as [String: AnyHashable])
        XCTAssertTrue(KnownWordsFile.url.path.hasSuffix("Application Support/Parzr/known-words.json"))
    }
    func testNameButtonRules() {
        func edit(_ original: String, _ replacement: String, _ category: String) -> WritingEdit { WritingEdit(start: 0, end: original.utf16.count, replacement: replacement, original: original, category: category) }
        let never: (String) -> Bool = { _ in false }
        XCTAssertEqual(edit("Aman", "Amen", "Spelling").nameCandidate(flagged: never), "Aman")
        XCTAssertEqual(edit("Aman\u{2019}s", "Amen's", "Spelling").nameCandidate(flagged: never), "Aman")
        XCTAssertEqual(edit("aman jain", "Amen Jain", "Spelling").nameCandidate(flagged: never), "aman jain")
        XCTAssertNil(edit("chek", "check", "Spelling").nameCandidate(flagged: never), "ordinary words keep the dictionary button")
        XCTAssertNil(edit("Aman", "aman", "Spelling").nameCandidate(flagged: never))
        XCTAssertEqual(edit("Aman", "A man", "Grammar").nameCandidate(flagged: never), "Aman")
        XCTAssertEqual(edit("aman", "A man", "Grammar").nameCandidate(flagged: { $0 == "aman" }), "aman")
        XCTAssertNil(edit("their", "there", "Grammar").nameCandidate(flagged: never))
        XCTAssertNil(edit("Your", "You're", "Grammar").nameCandidate(flagged: never), "grammar swaps of real words are not names")
        XCTAssertEqual(edit("Jain", "Jan", "Grammar").nameCandidate(flagged: { $0 == "Jain" }), "Jain")
        XCTAssertNil(edit("a1", "b", "Spelling").nameCandidate(flagged: never))
    }
    func testUndoRevertDetection() {
        let fix = FixLearning.Fix(pid: 1, element: 2, original: "Aman", replacement: "Amen", location: 7, time: Date(timeIntervalSince1970: 1000))
        let now = Date(timeIntervalSince1970: 1030)
        XCTAssertEqual(FixLearning.state(of: fix, in: "Hello, Amen Jain", now: now), .pending)
        XCTAssertEqual(FixLearning.state(of: fix, in: "Hello, Aman Jain", now: now), .reverted)
        XCTAssertEqual(FixLearning.state(of: fix, in: "Hello, Zed Jain", now: now), .gone)
        XCTAssertEqual(FixLearning.state(of: fix, in: "Hello, Aman Jain", now: Date(timeIntervalSince1970: 1061)), .gone)
        XCTAssertTrue(FixLearning.tracks(WritingEdit(start: 0, end: 3, replacement: "the", original: "teh")))
        XCTAssertFalse(FixLearning.tracks(WritingEdit(start: 0, end: 4, replacement: "Aman", original: "aman")), "case-only fixes are not learned")
        XCTAssertFalse(FixLearning.tracks(WritingEdit(start: 0, end: 9, replacement: "Amen Jain", original: "aman jain")))
    }
    func testAccessibilityLinkMentionAndAttachmentKeysAreProtected() {
        let text = NSMutableAttributedString(string: "see docs hello now")
        text.addAttribute(NSAttributedString.Key("AXLink"), value: URL(string: "https://x.test")!, range: NSRange(location: 4, length: 4))
        text.addAttribute(.link, value: URL(string: "https://y.test")!, range: NSRange(location: 0, length: 3))
        text.addAttribute(NSAttributedString.Key("AXAttachment"), value: 1, range: NSRange(location: 15, length: 3))
        text.addAttribute(NSAttributedString.Key("AXMarkedMisspelled"), value: 1, range: NSRange(location: 9, length: 5))
        let spans = SelectionSnapshot.protectedSpans(in: text).map { NSRange(location: $0.start_utf16, length: $0.end_utf16 - $0.start_utf16) }
        XCTAssertEqual(spans, [NSRange(location: 0, length: 3), NSRange(location: 4, length: 4), NSRange(location: 15, length: 3)])
        let mention = NSMutableAttributedString(string: "hi "); mention.append(NSAttributedString(string: "@priya", attributes: [.font: NSFont.boldSystemFont(ofSize: 12)])); mention.append(NSAttributedString(string: " ok"))
        XCTAssertEqual(SelectionSnapshot.protectedSpans(in: mention).map(\.start_utf16), [3])
    }
    func testContactTokensKeepNamesOnly() {
        XCTAssertEqual(ContactNames.tokens(person: ["Priya", "Rao Iyer", ""], organization: "Acme Corp"), ["Priya", "Rao", "Iyer", "Acme Corp"])
        XCTAssertEqual(ContactNames.tokens(person: ["x"], organization: "3M & Co"), [])
    }
}

final class NameGateTests: XCTestCase {
    final class Calls: @unchecked Sendable { var passes = 0, accepts = 0 }
    /// Stand-in lexicon: "jatin", "jean-luc", "recieve" and "teh" are misspelled when lowercase; only the Capitalized names are accepted.
    func gate(_ calls: Calls = Calls()) -> NameGate {
        let bad: Set<String> = ["jatin", "jean-luc", "recieve", "teh"], good: Set<String> = ["Jatin", "Jean-Luc"]
        return NameGate(probe: LexiconProbe(
            misspelled: { text in calls.passes += 1; return text.split(whereSeparator: { !($0.isLetter || "'\u{2019}-".contains($0)) }).map(String.init).filter { NameGate.shaped($0).map(bad.contains) == true } },
            accepts: { calls.accepts += 1; return good.contains($0) }))
    }
    func testShapeAndCapitalization() {
        XCTAssertEqual(NameGate.shaped("jatin"), "jatin")
        XCTAssertEqual(NameGate.shaped("jatin's"), "jatin")
        XCTAssertEqual(NameGate.shaped("jatin\u{2019}s"), "jatin")
        XCTAssertEqual(NameGate.shaped("jean-luc"), "jean-luc")
        XCTAssertEqual(NameGate.shaped("o'neil"), "o'neil")
        XCTAssertEqual(NameGate.shaped("'jatin'"), "jatin")
        XCTAssertNil(NameGate.shaped("Jatin")); XCTAssertNil(NameGate.shaped("jaTin")); XCTAssertNil(NameGate.shaped("j")); XCTAssertNil(NameGate.shaped("a1b")); XCTAssertNil(NameGate.shaped("--"))
        XCTAssertEqual(NameGate.capitalized("jatin"), "Jatin")
        XCTAssertEqual(NameGate.capitalized("jean-luc"), "Jean-Luc")
        XCTAssertEqual(NameGate.capitalized("mary-ann-lee"), "Mary-Ann-Lee")
        XCTAssertEqual(NameGate.capitalized("o'neil"), "O'neil")
    }
    func testNamesAreLowercaseWordsRejectedLowercaseButAcceptedCapitalized() {
        var gate = gate()
        XCTAssertEqual(gate.names(in: "Looping in jatin and jean-luc, please recieve teh plan. Jatin's idea, jatin's plan."), ["jatin", "jean-luc"])
        XCTAssertEqual(gate.names(in: "I recieve teh news"), [], "typos stay fixable")
        XCTAssertEqual(gate.names(in: "Looping in Jatin."), [], "already capitalized words are not lowercase names")
    }
    func testResultsAreCachedPerWord() {
        let calls = Calls(); var gate = gate(calls)
        XCTAssertEqual(gate.names(in: "ask jatin about teh plan"), ["jatin"])
        XCTAssertEqual(calls.passes, 1); XCTAssertEqual(calls.accepts, 2, "only the two lexicon-rejected words ask for the Capitalized form")
        XCTAssertEqual(gate.names(in: "teh jatin ask"), ["jatin"])
        XCTAssertEqual(calls.passes, 1, "every word was cached, so no spell-check pass"); XCTAssertEqual(calls.accepts, 2)
        XCTAssertEqual(gate.names(in: "ask jatin about jean-luc"), ["jatin", "jean-luc"])
        XCTAssertEqual(calls.passes, 2); XCTAssertEqual(calls.accepts, 3)
    }
    func testTokenCapAndCacheBound() {
        XCTAssertEqual(NameGate.candidates(in: "ask jatin ask jatin").count, 2)
        let words = (0..<500).map { i in String((0..<4).map { Character(UnicodeScalar(97 + (i / Int(pow(26.0, Double($0))) % 26))!) }) }
        XCTAssertEqual(NameGate.candidates(in: words.joined(separator: " ")).count, NameGate.maxTokens)
        var cache = LRUCache<Bool>(capacity: 16)
        for i in 0..<100 { cache.set(true, for: "k\(i)"); _ = cache.value(for: "k0") }
        XCTAssertLessThanOrEqual(cache.count, 16)
        XCTAssertNotNil(cache.value(for: "k0"), "recently used entries survive eviction"); XCTAssertNil(cache.value(for: "k1"))
    }
}

final class RepetitionLearningTests: XCTestCase {
    func testThreeSightingsOverTwoDaysLearn() {
        var ledger = RepetitionLedger()
        XCTAssertFalse(ledger.sight("jatin", app: "a", day: 1)); XCTAssertFalse(ledger.sight("jatin", app: "a", day: 1))
        XCTAssertFalse(ledger.sight("jatin", app: "a", day: 1), "three sightings on one day in one app are not enough")
        XCTAssertTrue(ledger.sight("jatin", app: "a", day: 2))
        XCTAssertNil(ledger.entries["jatin"], "a learned word leaves the ledger")
    }
    func testThreeSightingsOverTwoAppsLearnButTwoDoNot() {
        var ledger = RepetitionLedger()
        XCTAssertFalse(ledger.sight("Jatin", app: "a", day: 1)); XCTAssertFalse(ledger.sight("jatin", app: "b", day: 1))
        XCTAssertTrue(ledger.sight("jatin", app: "b", day: 1))
    }
    func testAppliedCorrectionBlocksLearningAndLedgerIsCapped() {
        var ledger = RepetitionLedger()
        _ = ledger.sight("teh", app: "a", day: 1); ledger.applied("teh", day: 1)
        for day in 2...6 { XCTAssertFalse(ledger.sight("teh", app: "b", day: day)) }
        for i in 0..<(RepetitionLedger.capacity + 50) { _ = ledger.sight("w\(i)", app: "a", day: i) }
        XCTAssertEqual(ledger.entries.count, RepetitionLedger.capacity)
        XCTAssertNil(ledger.entries["w0"], "oldest evicted"); XCTAssertNotNil(ledger.entries["w\(RepetitionLedger.capacity + 49)"])
        let data = try? JSONEncoder().encode(ledger)
        XCTAssertFalse(String(decoding: data ?? Data(), as: UTF8.self).contains("Looping"), "words and counts only")
    }
    func testOnlyLowercaseSingleWordSpellingEditsCount() {
        let text = "ask jatin about it, and Priya, teh jean-luc"
        func edit(_ word: String, _ category: String = "Spelling") -> WritingEdit { let s = (text as NSString).range(of: word); return WritingEdit(start: s.location, end: s.location + s.length, replacement: "x", original: word, category: category) }
        XCTAssertEqual(RepetitionLearning.candidates(in: [edit("jatin"), edit("Priya"), edit("jean-luc"), edit("about", "Grammar")], text: text), ["jatin"])
        XCTAssertTrue(RepetitionLearning.candidates(in: [WritingEdit(start: 0, end: 5, replacement: "x", original: "jatin", category: "Spelling")], text: "jatin").isEmpty, "a word still being typed (nothing after it) does not count")
    }
    func testASightingCountsOncePerAppearanceInAField() {
        let first = RepetitionLearning.fresh(["jatin"], previous: [], fullText: "ask jatin")
        XCTAssertEqual(first.fresh, ["jatin"])
        let again = RepetitionLearning.fresh(["jatin"], previous: first.present, fullText: "ask jatin now")
        XCTAssertTrue(again.fresh.isEmpty, "later checks of the same text are not new sightings")
        let cleared = RepetitionLearning.fresh([], previous: again.present, fullText: "")
        XCTAssertTrue(cleared.present.isEmpty)
        XCTAssertEqual(RepetitionLearning.fresh(["jatin"], previous: cleared.present, fullText: "jatin ok").fresh, ["jatin"], "typed again in an emptied field")
    }
    @MainActor func testPreferencesLearnsAfterSightingsAndNeverAfterApply() throws {
        let suite = "parzr-rep-\(UUID().uuidString)"; let defaults = UserDefaults(suiteName: suite)!; defer { defaults.removePersistentDomain(forName: suite) }
        let prefs = Preferences(defaults: defaults)
        prefs.noteSighting("jatin", app: "a", day: 1); prefs.noteSighting("jatin", app: "b", day: 1)
        XCTAssertTrue(prefs.learnedNames.isEmpty)
        XCTAssertEqual(Preferences(defaults: defaults).ledger.entries["jatin"]?.keys.count, 2, "the ledger persists")
        prefs.noteSighting("jatin", app: "b", day: 2)
        XCTAssertEqual(prefs.learnedNames, ["jatin"])
        prefs.noteApplied("teh")
        for day in 1...5 { prefs.noteSighting("teh", app: "a\(day)", day: day) }
        XCTAssertEqual(prefs.learnedNames, ["jatin"])
    }
}
