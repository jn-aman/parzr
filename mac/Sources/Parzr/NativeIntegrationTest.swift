import AppKit
import ApplicationServices
import Carbon
import ParzrCore

/// Real typing, range marks, inline acceptance, rich-text patching and editor Undo
/// for the reported grammar failures. Only these authored fixtures are touched.
@MainActor
func runGrammarTypingTest(reportDirectory: String) async throws {
    guard AXIsProcessTrusted(), !IsSecureEventInputEnabled() else { throw ParzrError.message("Grammar typing QA needs Accessibility with secure input off.") }
    let directory = URL(fileURLWithPath: reportDirectory)
    try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
    guard let textEdit = NSWorkspace.shared.urlForApplication(withBundleIdentifier: "com.apple.TextEdit") else { throw ParzrError.message("TextEdit is unavailable.") }
    let cases = [
        ("supposed", "This is not how it is suppose to be donme.", "This is not how it is supposed to be done.", "donme"),
        ("narrative", "Yesterday I goes to the market and buyer some vegetables but the shopkeeper was not there so I was waiting for him many times. Then my friend come and tell me that he don’t works there anymore. We was confused because nobody was knowing where he went, so we just goes back home without buying nothing.", "Yesterday, I went to the market and bought some vegetables, but the shopkeeper was not there, so I waited for him for a long time. Then my friend came and told me that he did not work there anymore. We were confused because nobody knew where he had gone, so we just went back home without buying anything.", "works"),
    ]
    var reports: [[String: Any]] = []
    for (name, phrase, expected, selectedWord) in cases {
        let initial = String(phrase.dropLast())
        let font = NSFont.systemFont(ofSize: 16)
        let fixture = NSMutableAttributedString(string: initial, attributes: [.font: font])
        let anchor = NSRange(location: 0, length: (initial as NSString).range(of: " ").location)
        fixture.addAttribute(.font, value: NSFontManager.shared.convert(font, toHaveTrait: .boldFontMask), range: anchor)
        let url = directory.appendingPathComponent("grammar-\(name)-\(UUID().uuidString).rtf")
        try fixture.data(from: NSRange(location: 0, length: fixture.length), documentAttributes: [.documentType: NSAttributedString.DocumentType.rtf]).write(to: url)
        _ = try await NSWorkspace.shared.open([url], withApplicationAt: textEdit, configuration: NSWorkspace.OpenConfiguration())
        var editor: NSRunningApplication?; var element: AXUIElement?
        for _ in 0..<50 {
            try await Task.sleep(for: .milliseconds(100))
            if let app = NSWorkspace.shared.frontmostApplication, app.bundleIdentifier == "com.apple.TextEdit", let focused = AX.focusedText(app), AX.string(focused, kAXValueAttribute) == initial { editor = app; element = focused; break }
        }
        guard let editor, let element, AX.setRange(element, NSRange(location: initial.utf16.count, length: 0)) else { throw ParzrError.message("The authored \(name) grammar fixture was not focused.") }
        let inline = InlineSuggestions(); let observer = PassiveObserver()
        defer { observer.stop(); inline.stop() }
        var analysis: RewriteResult?; var highlighted = false; var remaining = false
        var intermediate: String?
        observer.onDismiss = { inline.dismissIfStale() }
        observer.onSuggestion = { snapshot, result in
            guard snapshot.app.processIdentifier == editor.processIdentifier else { return }
            if snapshot.text == phrase, result.text == expected {
                analysis = result
                highlighted = !result.edits.isEmpty && inline.show(snapshot: snapshot, result: result) && result.edits.allSatisfy { inline.markedView(for: $0) != nil }
            } else if snapshot.text == intermediate, result.text == expected {
                remaining = !result.edits.isEmpty && inline.show(snapshot: snapshot, result: result) && result.edits.allSatisfy { inline.markedView(for: $0) != nil }
            }
        }
        observer.attach()
        try await Task.sleep(for: .milliseconds(400))
        guard !IsSecureEventInputEnabled(), AX.string(element, kAXValueAttribute) == initial, AX.focusedText(editor).map({ CFEqual($0, element) }) == true, AX.range(element) == NSRange(location: initial.utf16.count, length: 0) else { throw ParzrError.message("The grammar fixture changed before typing.") }
        let down = CGEvent(keyboardEventSource: nil, virtualKey: 47, keyDown: true), up = CGEvent(keyboardEventSource: nil, virtualKey: 47, keyDown: false)
        down?.keyboardSetUnicodeString(stringLength: 1, unicodeString: [46]); up?.keyboardSetUnicodeString(stringLength: 1, unicodeString: [46])
        down?.postToPid(editor.processIdentifier); up?.postToPid(editor.processIdentifier)
        for _ in 0..<100 { try await Task.sleep(for: .milliseconds(50)); if highlighted { break } }
        guard highlighted, let result = analysis, AX.string(element, kAXValueAttribute) == phrase,
              let edit = result.edits.first(where: { $0.original == selectedWord }), let mark = inline.markedView(for: edit),
              let button = NativeControls.find(label: "Review \(edit.category.lowercased()) correction", in: mark) else { throw ParzrError.message("Automatic grammar range marks were missing for \(name).") }
        intermediate = try EditPlan.apply(EditPlan.related(to: edit, in: result.edits), to: phrase)
        guard button.accessibilityPerformPress() else { throw ParzrError.message("The grammar underline button failed.") }
        try await Task.sleep(for: .milliseconds(100))
        guard let view = inline.correctionView, inline.correctionSize == RewritePanel.size else { throw ParzrError.message("The compact grammar popup did not open.") }
        try NativeControls.snapshot(view, to: directory.appendingPathComponent("grammar-\(name)-inline.png"))
        guard let apply = NativeControls.find(label: "Apply correction: \(edit.replacementLabel)", in: view), apply.accessibilityPerformPress() else { throw ParzrError.message("The grammar correction button failed.") }
        for _ in 0..<100 { try await Task.sleep(for: .milliseconds(50)); if remaining { break } }
        guard remaining, AX.string(element, kAXValueAttribute) == intermediate, AX.range(element) == NSRange(location: intermediate!.utf16.count, length: 0) else { throw ParzrError.message("Grammar acceptance did not restore remaining highlights and the typing caret.") }
        observer.stop(); inline.dismiss()
        func undo(maximumSteps: Int, allowed: Set<String>) async throws -> Int {
            for step in 1...maximumSteps {
                guard !IsSecureEventInputEnabled(), AX.focusedText(editor).map({ CFEqual($0, element) }) == true,
                      let current = AX.string(element, kAXValueAttribute), allowed.contains(current) else { throw ParzrError.message("The authored grammar fixture changed before Undo.") }
                let d = CGEvent(keyboardEventSource: nil, virtualKey: 6, keyDown: true), u = CGEvent(keyboardEventSource: nil, virtualKey: 6, keyDown: false)
                d?.flags = .maskCommand; u?.flags = .maskCommand
                d?.postToPid(editor.processIdentifier); u?.postToPid(editor.processIdentifier)
                for _ in 0..<20 {
                    try await Task.sleep(for: .milliseconds(50))
                    if AX.string(element, kAXValueAttribute) != current { break }
                }
                if AX.string(element, kAXValueAttribute) == phrase { return step }
            }
            throw ParzrError.message("TextEdit could not undo the authored grammar correction in \(maximumSteps) steps.")
        }
        let inlineUndoSteps = try await undo(maximumSteps: 1, allowed: [intermediate!])
        guard AX.setRange(element, NSRange(location: phrase.utf16.count, length: 0)) else { throw ParzrError.message("TextEdit refused the grammar fixture caret.") }
        let snapshot = try SelectionSnapshot.capture(passive: true)
        guard snapshot.text == phrase, let before = snapshot.richText else { throw ParzrError.message("The grammar fixture could not be captured safely.") }
        try await snapshot.apply(result.edits)
        guard AX.string(element, kAXValueAttribute) == expected,
              let after = AX.attributed(element, NSRange(location: 0, length: expected.utf16.count)),
              NSDictionary(dictionary: before.attributes(at: 0, effectiveRange: nil)).isEqual(to: after.attributes(at: 0, effectiveRange: nil)) else { throw ParzrError.message("Grammar patching changed text or rich-text formatting unexpectedly.") }
        // AX supplies individual host edits, not an Undo grouping API. Verify
        // every native undo state and stop at the fixture's original sentence.
        let patched = NSMutableString(string: phrase)
        var undoStates: Set<String> = [phrase]
        for item in result.edits.reversed() {
            patched.replaceCharacters(in: item.range, with: item.replacement)
            undoStates.insert(patched as String)
        }
        let fullUndoSteps = try await undo(maximumSteps: result.edits.count, allowed: undoStates)
        reports.append(["fixture": name, "actual_typing": true, "automatic_range_marks": result.edits.count, "compact_inline_apply": true, "remaining_highlights_return": true, "caret_preserved": true, "full_plan_apply": true, "bold_preserved": true, "native_undo": true, "inline_undo_steps": inlineUndoSteps, "full_plan_undo_steps": fullUndoSteps, "expected": expected, "status": "passed"])
    }
    let report: [String: Any] = ["status": "passed", "synthetic_fixtures_only": true, "editor": "com.apple.TextEdit", "cases": reports]
    try JSONSerialization.data(withJSONObject: report, options: [.prettyPrinted, .sortedKeys]).write(to: directory.appendingPathComponent("grammar-typing-results.json"))
}

/// Explicit QA command. It opens and edits only an authored temporary TextEdit fixture.
@MainActor
func runNativeIntegrationTest(reportDirectory: String) async throws {
    guard AXIsProcessTrusted() else { throw ParzrError.message("Native QA requires Accessibility permission for this executable.") }
    guard !IsSecureEventInputEnabled() else { throw ParzrError.message("Native QA stopped while secure input is active.") }
    let directory = URL(fileURLWithPath: reportDirectory)
    try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
    let source = "Hello John, can you chek this document?\n\nThanks."
    let fixture = NSMutableAttributedString(string: source)
    let font = NSFont.systemFont(ofSize: 15)
    fixture.addAttribute(.font, value: font, range: NSRange(location: 0, length: fixture.length))
    fixture.addAttribute(.font, value: NSFontManager.shared.convert(font, toHaveTrait: .boldFontMask), range: NSRange(location: 6, length: 4))
    fixture.addAttribute(.font, value: NSFontManager.shared.convert(font, toHaveTrait: .italicFontMask), range: NSRange(location: 19, length: 4))
    let url = directory.appendingPathComponent("parzr-qa-\(UUID().uuidString).rtf")
    try fixture.data(from: NSRange(location: 0, length: fixture.length), documentAttributes: [.documentType: NSAttributedString.DocumentType.rtf]).write(to: url)
    guard let textEdit = NSWorkspace.shared.urlForApplication(withBundleIdentifier: "com.apple.TextEdit") else { throw ParzrError.message("TextEdit is unavailable.") }
    _ = try await NSWorkspace.shared.open([url], withApplicationAt: textEdit, configuration: NSWorkspace.OpenConfiguration())
    var editor: NSRunningApplication?; var element: AXUIElement?
    for _ in 0..<50 {
        try await Task.sleep(for: .milliseconds(100))
        if let app = NSWorkspace.shared.frontmostApplication, app.bundleIdentifier == "com.apple.TextEdit", let focused = AX.focusedText(app), AX.string(focused, kAXValueAttribute) == source { editor = app; element = focused; break }
    }
    guard let editor, let element, AX.setRange(element, NSRange(location: 0, length: fixture.length)) else { throw ParzrError.message("The authored fixture was not focused. QA stopped without editing.") }
    let snapshot = try SelectionSnapshot.capture()
    guard snapshot.text == source, snapshot.canPatch, let before = snapshot.richText else { throw ParzrError.message("TextEdit did not expose the required rich-text capabilities.") }
    let result = try await WritingEngine.shared.rewrite(EngineRequest(text: source, protectedRanges: snapshot.protectedRanges()))
    guard result.text == "Hello John, can you check this document?\n\nThanks.", result.edits.count == 1 else { throw ParzrError.message("The fixture's correction plan was unexpected.") }
    guard AX.setRange(element, NSRange(location: 0, length: 0)) else { throw ParzrError.message("TextEdit refused the fixture caret.") }
    let passiveSnapshot = try SelectionSnapshot.capture(passive: true)
    let passiveResult = try await WritingEngine.shared.rewrite(EngineRequest(text: passiveSnapshot.text, protectedRanges: passiveSnapshot.protectedRanges()))
    guard passiveResult.edits.count == 1 else { throw ParzrError.message("The passive fixture did not detect its typo.") }
    let inline = InlineSuggestions()
    defer { inline.stop() }
    let rangeOverlay = inline.show(snapshot: passiveSnapshot, result: passiveResult)
    inline.dismiss()
    guard rangeOverlay else { throw ParzrError.message("TextEdit's correction range did not produce an inline overlay.") }
    // Exercise a real typing notification through the observer, rather than calling analysis directly.
    let caret = (source as NSString).range(of: "?").location + 1
    let typed = NSMutableString(string: source); typed.insert(" ", at: caret)
    let typedParagraph = typed.substring(with: typed.paragraphRange(for: NSRange(location: caret, length: 0)))
    var automaticHighlight = false
    let observer = PassiveObserver()
    observer.onDismiss = { inline.dismissIfStale() }
    observer.onSuggestion = { captured, checked in
        guard captured.app.processIdentifier == editor.processIdentifier, captured.text == typedParagraph else { return }
        automaticHighlight = inline.show(snapshot: captured, result: checked)
    }
    defer { observer.stop() }
    observer.attach()
    guard AX.setRange(element, NSRange(location: caret, length: 0)) else { throw ParzrError.message("TextEdit refused the typing fixture caret.") }
    CGEvent(keyboardEventSource: nil, virtualKey: 49, keyDown: true)?.postToPid(editor.processIdentifier)
    CGEvent(keyboardEventSource: nil, virtualKey: 49, keyDown: false)?.postToPid(editor.processIdentifier)
    for _ in 0..<80 { try await Task.sleep(for: .milliseconds(50)); if automaticHighlight { break } }
    observer.stop()
    guard automaticHighlight, AX.string(element, kAXValueAttribute) == typed as String else { throw ParzrError.message("Typing did not produce an automatic inline highlight in the authored fixture.") }
    let undoTypingDown = CGEvent(keyboardEventSource: nil, virtualKey: 6, keyDown: true)
    let undoTypingUp = CGEvent(keyboardEventSource: nil, virtualKey: 6, keyDown: false)
    undoTypingDown?.flags = .maskCommand; undoTypingUp?.flags = .maskCommand
    undoTypingDown?.postToPid(editor.processIdentifier); undoTypingUp?.postToPid(editor.processIdentifier)
    for _ in 0..<20 { try await Task.sleep(for: .milliseconds(50)); if AX.string(element, kAXValueAttribute) == source { break } }
    guard AX.string(element, kAXValueAttribute) == source else { throw ParzrError.message("The typing fixture did not undo safely.") }
    guard AX.setRange(element, passiveSnapshot.expectedSelection) else { throw ParzrError.message("TextEdit refused the inline fixture caret.") }
    guard inline.show(snapshot: passiveSnapshot, result: passiveResult), let mark = inline.markedView(for: passiveResult.edits[0]),
          let markedButton = NativeControls.find(label: "Review spelling correction", in: mark), markedButton.accessibilityPerformPress() else { throw ParzrError.message("The marked word's native button did not open a correction.") }
    try await Task.sleep(for: .milliseconds(100))
    guard inline.isPresenting, inline.correctionSize == RewritePanel.size, let correctionView = inline.correctionView else { throw ParzrError.message("The compact correction view did not open.") }
    try NativeControls.snapshot(correctionView, to: directory.appendingPathComponent("compact-inline.png"))
    guard let apply = NativeControls.find(label: "Apply correction: check", in: correctionView), apply.accessibilityPerformPress() else { throw ParzrError.message("The compact correction button did not apply its action.") }
    for _ in 0..<30 { try await Task.sleep(for: .milliseconds(50)); if AX.string(element, kAXValueAttribute) == result.text { break } }
    guard AX.string(element, kAXValueAttribute) == result.text else { throw ParzrError.message("The inline correction did not update its authored editor text.") }
    let compactApply = true
    guard let after = AX.attributed(element, NSRange(location: 0, length: result.text.utf16.count)), after.string == result.text else { throw ParzrError.message("The editor did not expose the corrected rich text.") }
    let boldPreserved = NSDictionary(dictionary: before.attributes(at: 6, effectiveRange: nil)).isEqual(to: after.attributes(at: 6, effectiveRange: nil))
    let italicPreserved = NSDictionary(dictionary: before.attributes(at: 19, effectiveRange: nil)).isEqual(to: after.attributes(at: 19, effectiveRange: nil))
    guard boldPreserved, italicPreserved else { throw ParzrError.message("Native editing changed the fixture's formatting.") }
    // Verify real editor undo, not only attributed-string manipulation in unit tests.
    let down = CGEvent(keyboardEventSource: nil, virtualKey: 6, keyDown: true)
    let up = CGEvent(keyboardEventSource: nil, virtualKey: 6, keyDown: false)
    down?.flags = .maskCommand; up?.flags = .maskCommand
    down?.postToPid(editor.processIdentifier); up?.postToPid(editor.processIdentifier)
    var undone = false
    for _ in 0..<20 { try await Task.sleep(for: .milliseconds(100)); if AX.string(element, kAXValueAttribute) == source { undone = true; break } }
    let report: [String: Any] = ["editor": "com.apple.TextEdit", "synthetic_fixture": true, "capture": true, "passive_capture": true, "automatic_typing_highlight": automaticHighlight, "inline_range_overlay": rangeOverlay, "compact_button_apply": compactApply, "minimal_apply": true, "bold_preserved": boldPreserved, "italic_preserved": italicPreserved, "paragraphs_preserved": true, "native_undo": undone, "status": undone ? "passed" : "failed", "os": ProcessInfo.processInfo.operatingSystemVersionString]
    try JSONSerialization.data(withJSONObject: report, options: [.prettyPrinted, .sortedKeys]).write(to: directory.appendingPathComponent("native-editor-results.json"))
    guard undone else { throw ParzrError.message("TextEdit did not undo the fixture edit. See native-editor-results.json.") }
}

/// Type into an authored incomplete sentence, check every mark, and accept one
/// correction through its actual button. Remaining marks must return automatically.
@MainActor
func runAutomaticTypingTest(reportDirectory: String) async throws {
    guard AXIsProcessTrusted(), !IsSecureEventInputEnabled() else { throw ParzrError.message("Typing QA needs Accessibility with secure input off.") }
    let directory = URL(fileURLWithPath: reportDirectory)
    try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
    let initial = "this si too bo", phrase = "this si too bod", intermediate = "this is too bod"
    let fixture = NSAttributedString(string: initial, attributes: [.font: NSFont.systemFont(ofSize: 16)])
    let url = directory.appendingPathComponent("typing-\(UUID().uuidString).rtf")
    try fixture.data(from: NSRange(location: 0, length: fixture.length), documentAttributes: [.documentType: NSAttributedString.DocumentType.rtf]).write(to: url)
    guard let textEdit = NSWorkspace.shared.urlForApplication(withBundleIdentifier: "com.apple.TextEdit") else { throw ParzrError.message("TextEdit is unavailable.") }
    _ = try await NSWorkspace.shared.open([url], withApplicationAt: textEdit, configuration: NSWorkspace.OpenConfiguration())
    var editor: NSRunningApplication?; var element: AXUIElement?
    for _ in 0..<50 {
        try await Task.sleep(for: .milliseconds(100))
        if let app = NSWorkspace.shared.frontmostApplication, app.bundleIdentifier == "com.apple.TextEdit", let focused = AX.focusedText(app), AX.string(focused, kAXValueAttribute) == initial { editor = app; element = focused; break }
    }
    guard let editor, let element, AX.setRange(element, NSRange(location: initial.utf16.count, length: 0)) else { throw ParzrError.message("The authored typing fixture was not focused.") }
    let inline = InlineSuggestions(); let observer = PassiveObserver()
    defer { observer.stop(); inline.stop() }
    var highlighted = false, remainingHighlighted = false
    var analysis: RewriteResult?
    observer.onDismiss = { inline.dismissIfStale() }
    observer.onSuggestion = { snapshot, result in
        guard snapshot.app.processIdentifier == editor.processIdentifier else { return }
        if snapshot.text == phrase, result.text == "This is too bad", result.edits.count == 3 {
            analysis = result
            highlighted = inline.show(snapshot: snapshot, result: result) && result.edits.allSatisfy { inline.markedView(for: $0) != nil }
        } else if snapshot.text == intermediate, result.text == "This is too bad", result.edits.count == 2 {
            remainingHighlighted = inline.show(snapshot: snapshot, result: result) && result.edits.allSatisfy { inline.markedView(for: $0) != nil }
        }
    }
    observer.attach()
    try await Task.sleep(for: .milliseconds(400))
    guard AX.string(element, kAXValueAttribute) == initial, AX.range(element) == NSRange(location: initial.utf16.count, length: 0), AX.focusedText(editor).map({ CFEqual($0, element) }) == true else { throw ParzrError.message("The typing fixture changed before QA could type.") }
    let down = CGEvent(keyboardEventSource: nil, virtualKey: 2, keyDown: true)
    let up = CGEvent(keyboardEventSource: nil, virtualKey: 2, keyDown: false)
    down?.keyboardSetUnicodeString(stringLength: 1, unicodeString: [100])
    up?.keyboardSetUnicodeString(stringLength: 1, unicodeString: [100])
    down?.postToPid(editor.processIdentifier); up?.postToPid(editor.processIdentifier)
    for _ in 0..<100 { try await Task.sleep(for: .milliseconds(50)); if highlighted { break } }
    guard highlighted, AX.string(element, kAXValueAttribute) == phrase, let edit = analysis?.edits.first(where: { $0.original == "si" }), let mark = inline.markedView(for: edit), let button = NativeControls.find(label: "Review spelling correction", in: mark), button.accessibilityPerformPress() else { throw ParzrError.message("The typed sentence did not produce three usable automatic marks.") }
    try await Task.sleep(for: .milliseconds(100))
    guard let view = inline.correctionView else { throw ParzrError.message("The spelling popover did not open.") }
    try NativeControls.snapshot(view, to: directory.appendingPathComponent("typed-correction.png"))
    guard let apply = NativeControls.find(label: "Apply correction: is", in: view), apply.accessibilityPerformPress() else { throw ParzrError.message("The inline spelling correction button did not activate.") }
    for _ in 0..<100 { try await Task.sleep(for: .milliseconds(50)); if remainingHighlighted { break } }
    guard remainingHighlighted, AX.string(element, kAXValueAttribute) == intermediate, AX.range(element) == NSRange(location: phrase.utf16.count, length: 0) else { throw ParzrError.message("Accepting one correction did not preserve the caret and restore remaining highlights.") }
    observer.stop()
    let undoDown = CGEvent(keyboardEventSource: nil, virtualKey: 6, keyDown: true), undoUp = CGEvent(keyboardEventSource: nil, virtualKey: 6, keyDown: false)
    undoDown?.flags = .maskCommand; undoUp?.flags = .maskCommand
    undoDown?.postToPid(editor.processIdentifier); undoUp?.postToPid(editor.processIdentifier)
    for _ in 0..<30 { try await Task.sleep(for: .milliseconds(50)); if AX.string(element, kAXValueAttribute) == phrase { break } }
    guard AX.string(element, kAXValueAttribute) == phrase else { throw ParzrError.message("The typed correction did not undo in TextEdit.") }
    let report: [String: Any] = ["status": "passed", "synthetic_fixture": true, "editor": "com.apple.TextEdit", "actual_typing": true, "before_terminal_punctuation": true, "three_automatic_highlights": true, "inline_apply": true, "typing_caret_preserved": true, "remaining_highlights_return": true, "native_undo": true]
    try JSONSerialization.data(withJSONObject: report, options: [.prettyPrinted, .sortedKeys]).write(to: directory.appendingPathComponent("typing-results.json"))
}

/// The owner of the frontmost on-screen window that contains `point` (global top-left coordinates).
func frontWindowOwner(at point: CGPoint) -> (pid: pid_t, name: String)? {
    let list = (CGWindowListCopyWindowInfo([.optionOnScreenOnly], kCGNullWindowID) as? [[String: Any]]) ?? []
    for window in list {
        guard let bounds = window[kCGWindowBounds as String] as? [String: CGFloat], CGRect(x: bounds["X"] ?? 0, y: bounds["Y"] ?? 0, width: bounds["Width"] ?? 0, height: bounds["Height"] ?? 0).contains(point), (window[kCGWindowAlpha as String] as? Double ?? 1) > 0 else { continue }
        return ((window[kCGWindowOwnerPID as String] as? pid_t) ?? 0, (window[kCGWindowOwnerName as String] as? String) ?? "?")
    }
    return nil
}

/// A real Cmd+V into an authored document, including the trailing-newline case.
@MainActor
func runAutomaticPasteTest(reportDirectory: String) async throws {
    guard AXIsProcessTrusted(), !IsSecureEventInputEnabled() else { throw ParzrError.message("Paste QA needs Accessibility with secure input off.") }
    let directory = URL(fileURLWithPath: reportDirectory)
    try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
    guard let textEdit = NSWorkspace.shared.urlForApplication(withBundleIdentifier: "com.apple.TextEdit") else { throw ParzrError.message("TextEdit is unavailable.") }
    let phrase = "This is not how it is suppose to be Done.\n"
    let prefix = "Parzr paste fixture\n"
    let url = directory.appendingPathComponent("paste-\(UUID().uuidString).rtf")
    let initial = NSAttributedString(string: prefix, attributes: [.font: NSFont.systemFont(ofSize: 16)])
    try initial.data(from: NSRange(location: 0, length: initial.length), documentAttributes: [.documentType: NSAttributedString.DocumentType.rtf]).write(to: url)
    _ = try await NSWorkspace.shared.open([url], withApplicationAt: textEdit, configuration: NSWorkspace.OpenConfiguration())
    var target: NSRunningApplication?; var element: AXUIElement?
    for _ in 0..<50 {
        try await Task.sleep(for: .milliseconds(100))
        if let app = NSWorkspace.shared.frontmostApplication, app.bundleIdentifier == "com.apple.TextEdit", let focused = AX.focusedText(app), AX.string(focused, kAXValueAttribute) == prefix { target = app; element = focused; break }
    }
    guard let target, let element, AX.setRange(element, NSRange(location: prefix.utf16.count, length: 0)) else { throw ParzrError.message("The authored paste fixture was not focused.") }
    _ = try await WritingEngine.typing.rewrite(EngineRequest(text: "A clear message."))
    let inline = InlineSuggestions(); let observer = PassiveObserver()
    defer { observer.stop(); inline.stop() }
    var checked: RewriteResult?; var snapshot: SelectionSnapshot?; var marked = false
    observer.onDismiss = { inline.dismissIfStale() }
    var seen: [String] = []
    observer.onSuggestion = { captured, result in
        seen.append("\(captured.app.localizedName ?? "?") \(captured.text.debugDescription) edits \(result.edits.count)")
        guard captured.app.processIdentifier == target.processIdentifier, captured.text == phrase else { return }
        guard !inline.isPresenting else { return }
        checked = result; snapshot = captured
        marked = inline.show(snapshot: captured, result: result) && result.edits.allSatisfy { inline.markedView(for: $0) != nil }
    }
    observer.attach()
    let clipboard = ClipboardTransaction(); defer { clipboard.restore() }
    try clipboard.stage(phrase, attributed: nil)
    guard AX.string(element, kAXValueAttribute) == prefix, AX.range(element) == NSRange(location: prefix.utf16.count, length: 0), AX.focusedText(target).map({ CFEqual($0, element) }) == true else { throw ParzrError.message("The paste fixture changed before Cmd+V; no paste was sent.") }
    let start = ContinuousClock.now
    try ClipboardTransaction.paste(to: target.processIdentifier)
    for _ in 0..<60 { try await Task.sleep(for: .milliseconds(50)); if marked { break } }
    guard marked, let checked, let snapshot, checked.text == "This is not how it is supposed to be done.\n", checked.edits.count >= 2,
          AX.string(element, kAXValueAttribute) == prefix + phrase else { throw ParzrError.message("Paste did not return automatic lowercase corrections and visible marks (marked \(marked), checked \(checked?.text.debugDescription ?? "none"), field \(AX.string(element, kAXValueAttribute).debugDescription), captures: \(seen.joined(separator: " | "))).") }
    let elapsed = start.duration(to: .now)
    guard let edit = checked.edits.first(where: { $0.original == "Done" }),
          let bounds = AX.bounds(element, NSRange(location: prefix.utf16.count + edit.start_utf16, length: edit.range.length)) else { throw ParzrError.message("The pasted word has no visible range.") }
    try snapshot.validate()
    let point = CGPoint(x: bounds.midX, y: (NSScreen.screens.first?.frame.maxY ?? 0) - bounds.midY)
    // Another Parzr watching the same fixture (an installed copy) draws its own overlay over the word, and the frontmost one takes the click: put ours in front first.
    let overlayWindow = inline.markedView(for: edit).flatMap { ($0.accessibilityParent() as? NSView)?.window }
    // A real pointer moves onto the word before it clicks; the mark overlay takes clicks only while the pointer is on an underline.
    CGEvent(mouseEventSource: nil, mouseType: .mouseMoved, mouseCursorPosition: point, mouseButton: .left)?.post(tap: .cghidEventTap)
    try await Task.sleep(for: .milliseconds(60))
    for _ in 0..<10 where frontWindowOwner(at: point)?.pid != getpid() { overlayWindow?.orderFrontRegardless(); try await Task.sleep(for: .milliseconds(30)) }
    if let front = frontWindowOwner(at: point), front.pid != getpid() { throw ParzrError.message("The pasted word is covered by \(front.name) (pid \(front.pid)), so the click cannot reach the mark overlay.") }
    let down = CGEvent(mouseEventSource: nil, mouseType: .leftMouseDown, mouseCursorPosition: point, mouseButton: .left)
    let up = CGEvent(mouseEventSource: nil, mouseType: .leftMouseUp, mouseCursorPosition: point, mouseButton: .left)
    down?.post(tap: .cghidEventTap)
    try await Task.sleep(for: .milliseconds(40))
    up?.post(tap: .cghidEventTap)
    for _ in 0..<40 { try await Task.sleep(for: .milliseconds(25)); if inline.isPresenting { break } }
    guard let view = inline.correctionView else { throw ParzrError.message("The pasted correction card did not open.") }
    try NativeControls.snapshot(view, to: directory.appendingPathComponent("paste-inline.png"))
    guard AX.string(element, kAXValueAttribute) == prefix + phrase, NSWorkspace.shared.frontmostApplication == target,
          SentencePreview.text(source: snapshot.text, edits: checked.edits, focused: edit) == "This is not how it is supposed to be done." else { throw ParzrError.message("The word click changed the fixture or its sentence preview.") }
    guard let sentence = NativeControls.find(label: "Fix sentence", in: view), sentence.accessibilityPerformPress() else { throw ParzrError.message("The inline Fix sentence action was unavailable.") }
    let expected = prefix + "This is not how it is supposed to be done.\n"
    for _ in 0..<40 { try await Task.sleep(for: .milliseconds(50)); if AX.string(element, kAXValueAttribute) == expected { break } }
    guard AX.string(element, kAXValueAttribute) == expected else { throw ParzrError.message("Fix sentence did not apply both corrections.") }
    let report: [String: Any] = ["status": "passed", "synthetic_fixture_only": true, "real_cmd_v": true, "real_word_click": true, "trailing_newline": true, "automatic_marks": checked.edits.count, "lowercase_done": true, "corrected_sentence_preview": true, "fix_sentence_applied": true, "warm_engine": true, "elapsed_ms": Double(elapsed.components.seconds) * 1000 + Double(elapsed.components.attoseconds) / 1e15]
    try JSONSerialization.data(withJSONObject: report, options: [.prettyPrinted, .sortedKeys]).write(to: directory.appendingPathComponent("paste-results.json"))
}
