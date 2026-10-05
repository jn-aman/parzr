import XCTest
import AppKit
import SwiftUI
import ParzrCore
@testable import Parzr

@MainActor
final class PlaygroundTests: XCTestCase {
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
