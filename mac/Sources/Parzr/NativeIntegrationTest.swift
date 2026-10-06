import AppKit
import ApplicationServices
import Carbon
import ParzrCore

/// Real typing, range marks, inline acceptance, rich-text patching and editor Undo
/// for the reported grammar failures. Only these authored fixtures are touched, in a `ParzrFixture` editor process (see `FixtureEditor`), never in an app the owner uses.
@MainActor
func runGrammarTypingTest(reportDirectory: String) async throws {
    guard AXIsProcessTrusted(), !IsSecureEventInputEnabled() else { throw ParzrError.message("Grammar typing QA needs Accessibility with secure input off.") }
    let directory = URL(fileURLWithPath: reportDirectory)
    try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
    let cases = [
        ("supposed", "This is not how it is suppose to be donme.", "This is not how it is supposed to be done.", "donme"),
        ("narrative", "Yesterday I goes to the market and buyer some vegetables but the shopkeeper was not there so I was waiting for him many times. Then my friend come and tell me that he don’t works there anymore. We was confused because nobody was knowing where he went, so we just goes back home without buying nothing.", "Yesterday, I went to the market and bought some vegetables, but the shopkeeper was not there, so I waited for him for a long time. Then my friend came and told me that he did not work there anymore. We were confused because nobody knew where he had gone, so we just went back home without buying anything.", "works"),
    ]
    var reports: [[String: Any]] = []
    var windows: [String] = []
    for (name, phrase, expected, selectedWord) in cases {
        let initial = String(phrase.dropLast())
        let font = NSFont.systemFont(ofSize: 16)
        let fixture = NSMutableAttributedString(string: initial, attributes: [.font: font])
        let anchor = NSRange(location: 0, length: (initial as NSString).range(of: " ").location)
        fixture.addAttribute(.font, value: NSFontManager.shared.convert(font, toHaveTrait: .boldFontMask), range: anchor)
        let fixtureEditor = try await FixtureEditor.launch(fixture, in: directory)
        defer { fixtureEditor.close() }
        let editor = fixtureEditor.app, element = fixtureEditor.element
        guard AX.setRange(element, NSRange(location: initial.utf16.count, length: 0)) else { throw ParzrError.message("The authored \(name) grammar fixture was not focused.") }
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
        fixtureEditor.key(47, unicode: 46)
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
                fixtureEditor.undo()
                for _ in 0..<20 {
                    try await Task.sleep(for: .milliseconds(50))
                    if AX.string(element, kAXValueAttribute) != current { break }
                }
                if AX.string(element, kAXValueAttribute) == phrase { return step }
            }
            throw ParzrError.message("The fixture editor could not undo the authored grammar correction in \(maximumSteps) steps.")
        }
        let inlineUndoSteps = try await undo(maximumSteps: 1, allowed: [intermediate!])
        guard AX.setRange(element, NSRange(location: phrase.utf16.count, length: 0)) else { throw ParzrError.message("The fixture editor refused the grammar fixture caret.") }
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
        try fixtureEditor.assertSafe(); windows.append(fixtureEditor.window)
        reports.append(["fixture": name, "actual_typing": true, "automatic_range_marks": result.edits.count, "compact_inline_apply": true, "remaining_highlights_return": true, "caret_preserved": true, "full_plan_apply": true, "bold_preserved": true, "native_undo": true, "inline_undo_steps": inlineUndoSteps, "full_plan_undo_steps": fullUndoSteps, "expected": expected, "status": "passed"])
    }
    let report: [String: Any] = ["status": "passed", "synthetic_fixtures_only": true, "editor": FixtureEditor.bundleIdentifier, "fixture_windows": windows, "cases": reports]
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
    let fixtureEditor = try await FixtureEditor.launch(fixture, caret: 0, in: directory)
    defer { fixtureEditor.close() }
    let editor = fixtureEditor.app, element = fixtureEditor.element
    guard AX.setRange(element, NSRange(location: 0, length: fixture.length)) else { throw ParzrError.message("The authored fixture was not focused. QA stopped without editing.") }
    let snapshot = try SelectionSnapshot.capture()
    guard snapshot.text == source, snapshot.canPatch, let before = snapshot.richText else { throw ParzrError.message("The fixture editor did not expose the required rich-text capabilities.") }
    let result = try await WritingEngine.shared.rewrite(EngineRequest(text: source, protectedRanges: snapshot.protectedRanges()))
    guard result.text == "Hello John, can you check this document?\n\nThanks.", result.edits.count == 1 else { throw ParzrError.message("The fixture's correction plan was unexpected.") }
    guard AX.setRange(element, NSRange(location: 0, length: 0)) else { throw ParzrError.message("The fixture editor refused the fixture caret.") }
    let passiveSnapshot = try SelectionSnapshot.capture(passive: true)
    let passiveResult = try await WritingEngine.shared.rewrite(EngineRequest(text: passiveSnapshot.text, protectedRanges: passiveSnapshot.protectedRanges()))
    guard passiveResult.edits.count == 1 else { throw ParzrError.message("The passive fixture did not detect its typo.") }
    let inline = InlineSuggestions()
    defer { inline.stop() }
    let rangeOverlay = inline.show(snapshot: passiveSnapshot, result: passiveResult)
    inline.dismiss()
    guard rangeOverlay else { throw ParzrError.message("The correction range did not produce an inline overlay.") }
    // Exercise a real typing notification through the observer, rather than calling analysis directly.
    let caret = (source as NSString).range(of: "?").location + 1
    let typed = NSMutableString(string: source); typed.insert(" ", at: caret)
    let typedParagraph = typed.substring(with: typed.paragraphRange(for: NSRange(location: caret, length: 0)))
    var automaticHighlight = false
    var seen: [String] = []
    let observer = PassiveObserver()
    observer.onDismiss = { inline.dismissIfStale() }
    observer.onSuggestion = { captured, checked in
        seen.append("pid \(captured.app.processIdentifier) \(captured.text.debugDescription) edits \(checked.edits.count)")
        guard captured.app.processIdentifier == editor.processIdentifier, captured.text == typedParagraph else { return }
        automaticHighlight = inline.show(snapshot: captured, result: checked)
    }
    defer { observer.stop() }
    observer.attach()
    guard AX.setRange(element, NSRange(location: caret, length: 0)) else { throw ParzrError.message("The fixture editor refused the typing fixture caret.") }
    fixtureEditor.key(49)
    for _ in 0..<80 { try await Task.sleep(for: .milliseconds(50)); if automaticHighlight { break } }
    observer.stop()
    guard automaticHighlight, AX.string(element, kAXValueAttribute) == typed as String else { throw ParzrError.message("Typing did not produce an automatic inline highlight in the authored fixture (highlighted \(automaticHighlight), field \(AX.string(element, kAXValueAttribute).debugDescription), expected paragraph \(typedParagraph.debugDescription), captures: \(seen.joined(separator: " | ")))") }
    fixtureEditor.undo()
    for _ in 0..<20 { try await Task.sleep(for: .milliseconds(50)); if AX.string(element, kAXValueAttribute) == source { break } }
    guard AX.string(element, kAXValueAttribute) == source else { throw ParzrError.message("The typing fixture did not undo safely.") }
    guard AX.setRange(element, passiveSnapshot.expectedSelection) else { throw ParzrError.message("The fixture editor refused the inline fixture caret.") }
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
    fixtureEditor.undo()
    var undone = false
    for _ in 0..<20 { try await Task.sleep(for: .milliseconds(100)); if AX.string(element, kAXValueAttribute) == source { undone = true; break } }
    try fixtureEditor.assertSafe()
    let report: [String: Any] = ["editor": FixtureEditor.bundleIdentifier, "fixture_window": fixtureEditor.window, "synthetic_fixture": true, "capture": true, "passive_capture": true, "automatic_typing_highlight": automaticHighlight, "inline_range_overlay": rangeOverlay, "compact_button_apply": compactApply, "minimal_apply": true, "bold_preserved": boldPreserved, "italic_preserved": italicPreserved, "paragraphs_preserved": true, "native_undo": undone, "status": undone ? "passed" : "failed", "os": ProcessInfo.processInfo.operatingSystemVersionString]
    try JSONSerialization.data(withJSONObject: report, options: [.prettyPrinted, .sortedKeys]).write(to: directory.appendingPathComponent("native-editor-results.json"))
    guard undone else { throw ParzrError.message("The fixture editor did not undo the edit (field now \(AX.string(element, kAXValueAttribute).debugDescription), wanted \(source.debugDescription)). See native-editor-results.json.") }
}

/// Type into an authored incomplete sentence, check every mark, and accept one
/// correction through its actual button. Remaining marks must return automatically.
@MainActor
func runAutomaticTypingTest(reportDirectory: String) async throws {
    guard AXIsProcessTrusted(), !IsSecureEventInputEnabled() else { throw ParzrError.message("Typing QA needs Accessibility with secure input off.") }
    let directory = URL(fileURLWithPath: reportDirectory)
    try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
    let initial = "this si too bo", phrase = "this si too bod", intermediate = "this is too bod"
    // A plain-text fixture here (the other tests use rich text).
    let fixtureEditor = try await FixtureEditor.launch(NSAttributedString(string: initial), rich: false, in: directory)
    defer { fixtureEditor.close() }
    let editor = fixtureEditor.app, element = fixtureEditor.element
    guard AX.setRange(element, NSRange(location: initial.utf16.count, length: 0)) else { throw ParzrError.message("The authored typing fixture was not focused.") }
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
    fixtureEditor.key(2, unicode: 100)
    for _ in 0..<100 { try await Task.sleep(for: .milliseconds(50)); if highlighted { break } }
    guard highlighted, AX.string(element, kAXValueAttribute) == phrase, let edit = analysis?.edits.first(where: { $0.original == "si" }), let mark = inline.markedView(for: edit), let button = NativeControls.find(label: "Review spelling correction", in: mark), button.accessibilityPerformPress() else { throw ParzrError.message("The typed sentence did not produce three usable automatic marks.") }
    try await Task.sleep(for: .milliseconds(100))
    guard let view = inline.correctionView else { throw ParzrError.message("The spelling popover did not open.") }
    try NativeControls.snapshot(view, to: directory.appendingPathComponent("typed-correction.png"))
    guard let apply = NativeControls.find(label: "Apply correction: is", in: view), apply.accessibilityPerformPress() else { throw ParzrError.message("The inline spelling correction button did not activate.") }
    for _ in 0..<100 { try await Task.sleep(for: .milliseconds(50)); if remainingHighlighted { break } }
    guard remainingHighlighted, AX.string(element, kAXValueAttribute) == intermediate, AX.range(element) == NSRange(location: phrase.utf16.count, length: 0) else { throw ParzrError.message("Accepting one correction did not preserve the caret and restore remaining highlights.") }
    observer.stop()
    fixtureEditor.undo()
    for _ in 0..<30 { try await Task.sleep(for: .milliseconds(50)); if AX.string(element, kAXValueAttribute) == phrase { break } }
    guard AX.string(element, kAXValueAttribute) == phrase else { throw ParzrError.message("The typed correction did not undo in the fixture editor.") }
    try fixtureEditor.assertSafe()
    let report: [String: Any] = ["status": "passed", "synthetic_fixture": true, "editor": FixtureEditor.bundleIdentifier, "fixture_window": fixtureEditor.window, "actual_typing": true, "before_terminal_punctuation": true, "three_automatic_highlights": true, "inline_apply": true, "typing_caret_preserved": true, "remaining_highlights_return": true, "native_undo": true]
    try JSONSerialization.data(withJSONObject: report, options: [.prettyPrinted, .sortedKeys]).write(to: directory.appendingPathComponent("typing-results.json"))
}

/// A real Cmd+V into an authored document, including the trailing-newline case.
@MainActor
func runAutomaticPasteTest(reportDirectory: String) async throws {
    guard AXIsProcessTrusted(), !IsSecureEventInputEnabled() else { throw ParzrError.message("Paste QA needs Accessibility with secure input off.") }
    let directory = URL(fileURLWithPath: reportDirectory)
    try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
    let phrase = "This is not how it is suppose to be Done.\n"
    let prefix = "Parzr paste fixture\n"
    let initial = NSAttributedString(string: prefix, attributes: [.font: NSFont.systemFont(ofSize: 16)])
    // Cmd+V reads the fixture's own pasteboard, so the owner's clipboard is never touched.
    let fixtureEditor = try await FixtureEditor.launch(initial, pasteboard: true, in: directory)
    defer { fixtureEditor.close() }
    let target = fixtureEditor.app, element = fixtureEditor.element
    guard AX.setRange(element, NSRange(location: prefix.utf16.count, length: 0)) else { throw ParzrError.message("The authored paste fixture was not focused.") }
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
    fixtureEditor.stagePaste(phrase)
    guard AX.string(element, kAXValueAttribute) == prefix, AX.range(element) == NSRange(location: prefix.utf16.count, length: 0), fixtureEditor.isFocused else { throw ParzrError.message("The paste fixture changed before Cmd+V; no paste was sent.") }
    let start = ContinuousClock.now
    try ClipboardTransaction.paste(to: target.processIdentifier)
    for _ in 0..<60 { try await Task.sleep(for: .milliseconds(50)); if marked { break } }
    guard marked, let checked, let snapshot, checked.text == "This is not how it is supposed to be done.\n", checked.edits.count >= 2,
          AX.string(element, kAXValueAttribute) == prefix + phrase else { throw ParzrError.message("Paste did not return automatic lowercase corrections and visible marks (marked \(marked), checked \(checked?.text.debugDescription ?? "none"), field \(AX.string(element, kAXValueAttribute).debugDescription), captures: \(seen.joined(separator: " | "))).") }
    let elapsed = start.duration(to: .now)
    guard let edit = checked.edits.first(where: { $0.original == "Done" }),
          let bounds = AX.bounds(element, NSRange(location: prefix.utf16.count + edit.start_utf16, length: edit.range.length)) else { throw ParzrError.message("The pasted word has no visible range.") }
    try snapshot.validate()
    // A real click on the word, delivered straight to Parzr's own overlay window (never through the system's event stream, so it cannot reach another app or move the pointer).
    // The overlay's hit test runs on the event's own location, exactly as for a pointer on that underline.
    guard let overlayWindow = inline.markedView(for: edit).flatMap({ ($0.accessibilityParent() as? NSView)?.window }) else { throw ParzrError.message("The pasted word's mark has no overlay window.") }
    try fixtureEditor.requireOffScreen(overlayWindow.frame, "The mark overlay")
    let location = overlayWindow.convertPoint(fromScreen: CGPoint(x: bounds.midX, y: bounds.midY))
    func click(_ type: NSEvent.EventType, number: Int) -> NSEvent? {
        NSEvent.mouseEvent(with: type, location: location, modifierFlags: [], timestamp: ProcessInfo.processInfo.systemUptime, windowNumber: overlayWindow.windowNumber, context: nil, eventNumber: number, clickCount: 1, pressure: type == .leftMouseDown ? 1 : 0)
    }
    guard let down = click(.leftMouseDown, number: 1), let up = click(.leftMouseUp, number: 2) else { throw ParzrError.message("The word click could not be built.") }
    overlayWindow.sendEvent(down)
    try await Task.sleep(for: .milliseconds(40))
    overlayWindow.sendEvent(up)
    for _ in 0..<40 { try await Task.sleep(for: .milliseconds(25)); if inline.isPresenting { break } }
    guard let view = inline.correctionView else { throw ParzrError.message("The pasted correction card did not open.") }
    if let card = view.window { try fixtureEditor.requireOffScreen(card.frame, "The correction card") }
    try NativeControls.snapshot(view, to: directory.appendingPathComponent("paste-inline.png"))
    try fixtureEditor.assertSafe()
    guard AX.string(element, kAXValueAttribute) == prefix + phrase,
          SentencePreview.text(source: snapshot.text, edits: checked.edits, focused: edit) == "This is not how it is supposed to be done." else { throw ParzrError.message("The word click changed the fixture or its sentence preview.") }
    guard let sentence = NativeControls.find(label: "Fix sentence", in: view), sentence.accessibilityPerformPress() else { throw ParzrError.message("The inline Fix sentence action was unavailable.") }
    let expected = prefix + "This is not how it is supposed to be done.\n"
    for _ in 0..<40 { try await Task.sleep(for: .milliseconds(50)); if AX.string(element, kAXValueAttribute) == expected { break } }
    guard AX.string(element, kAXValueAttribute) == expected else { throw ParzrError.message("Fix sentence did not apply both corrections.") }
    try fixtureEditor.assertSafe()
    let report: [String: Any] = ["status": "passed", "synthetic_fixture_only": true, "editor": FixtureEditor.bundleIdentifier, "fixture_window": fixtureEditor.window, "real_cmd_v": true, "real_word_click": true, "trailing_newline": true, "automatic_marks": checked.edits.count, "lowercase_done": true, "corrected_sentence_preview": true, "fix_sentence_applied": true, "warm_engine": true, "elapsed_ms": Double(elapsed.components.seconds) * 1000 + Double(elapsed.components.attoseconds) / 1e15]
    try JSONSerialization.data(withJSONObject: report, options: [.prettyPrinted, .sortedKeys]).write(to: directory.appendingPathComponent("paste-results.json"))
}

/// The editor the self tests type into: a `ParzrFixture` process (see Sources/ParzrFixture), never TextEdit or any app the owner uses.
/// It is an accessory app whose one window is a non-activating panel outside every screen, so nothing appears on a display, the frontmost app and keyboard focus never change,
/// and it exits by itself when this process ends. Keystrokes reach it only through `CGEvent.postToPid(its pid)`; nothing is posted to the HID or session tap.
/// While it is open `SelfTestTarget` points Parzr at it, and a monitor records any moment the fixture or this process shows a window on a screen or becomes frontmost.
@MainActor
final class FixtureEditor {
    static let bundleIdentifier = "app.parzr.fixture"
    let app: NSRunningApplication
    let element: AXUIElement
    /// The fixture window in Cocoa coordinates.
    let stage: CGRect
    /// The same frame as text, for the reports.
    let window: String
    private let process: Process
    private let directory: URL
    private let board: NSPasteboard?
    private var monitor: Task<Void, Never>?
    private var activation: NSObjectProtocol?
    private(set) var violations: [String] = []

    private init(app: NSRunningApplication, element: AXUIElement, stage: CGRect, process: Process, directory: URL, board: NSPasteboard?) {
        self.app = app; self.element = element; self.stage = stage; self.process = process; self.directory = directory; self.board = board
        window = "\(Int(stage.minX)),\(Int(stage.minY)) \(Int(stage.width))x\(Int(stage.height))"
    }

    /// ParzrFixture sits beside this executable in a build folder; PARZR_FIXTURE_PATH overrides (an installed app does not carry it).
    private static func executable() -> URL? {
        let candidates = [ProcessInfo.processInfo.environment["PARZR_FIXTURE_PATH"].map { URL(fileURLWithPath: $0) }, Bundle.main.executableURL?.deletingLastPathComponent().appendingPathComponent("ParzrFixture")]
        return candidates.compactMap { $0 }.first { FileManager.default.isExecutableFile(atPath: $0.path) }
    }
    private static let infoPlist = """
    <?xml version="1.0" encoding="UTF-8"?>
    <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
    <plist version="1.0"><dict><key>CFBundleIdentifier</key><string>\(bundleIdentifier)</string><key>CFBundleName</key><string>ParzrFixture</string><key>CFBundleExecutable</key><string>ParzrFixture</string><key>CFBundlePackageType</key><string>APPL</string><key>LSUIElement</key><true/></dict></plist>
    """

    /// Starts the fixture with `initial` as its text (rich text opens an RTF, plain a .txt) and the caret at `caret` (default: the end).
    /// `pasteboard`: Cmd+V reads a private pasteboard that `stagePaste` fills, not the owner's clipboard.
    static func launch(_ initial: NSAttributedString, rich: Bool = true, caret: Int? = nil, pasteboard: Bool = false, in reports: URL) async throws -> FixtureEditor {
        guard let executable = executable() else { throw ParzrError.message("ParzrFixture was not found next to this executable. Build it (`swift build --package-path mac` builds it) and run the test from that build folder, or set PARZR_FIXTURE_PATH.") }
        let directory = reports.appendingPathComponent("fixture-\(UUID().uuidString)", isDirectory: true)
        // A tiny .app wrapper gives the process a bundle identifier, which Parzr needs to treat it as an editor.
        let contents = directory.appendingPathComponent("ParzrFixture.app/Contents", isDirectory: true)
        try FileManager.default.createDirectory(at: contents.appendingPathComponent("MacOS"), withIntermediateDirectories: true)
        let process = Process()
        var board: NSPasteboard?
        func stop() { terminate(process); board?.releaseGlobally(); try? FileManager.default.removeItem(at: directory) }
        do {
            let binary = contents.appendingPathComponent("MacOS/ParzrFixture")
            try FileManager.default.copyItem(at: executable, to: binary)
            try Data(infoPlist.utf8).write(to: contents.appendingPathComponent("Info.plist"))
            let file = directory.appendingPathComponent(rich ? "fixture.rtf" : "fixture.txt")
            if rich { try initial.data(from: NSRange(location: 0, length: initial.length), documentAttributes: [.documentType: NSAttributedString.DocumentType.rtf]).write(to: file) }
            else { try Data(initial.string.utf8).write(to: file) }
            var arguments = ["--parent", "\(getpid())", "--file", file.path]
            if pasteboard {
                let name = "\(bundleIdentifier).\(UUID().uuidString)"
                board = NSPasteboard(name: NSPasteboard.Name(name)); arguments += ["--pasteboard", name]
            }
            if let caret { arguments += ["--caret", "\(caret)"] }
            process.executableURL = binary; process.arguments = arguments
            process.standardInput = FileHandle.nullDevice; process.standardOutput = FileHandle.nullDevice; process.standardError = FileHandle.nullDevice
            try process.run()
            for _ in 0..<80 {
                try await Task.sleep(for: .milliseconds(100))
                guard process.isRunning else { throw ParzrError.message("The fixture editor exited at once (status \(process.terminationStatus)).") }
                let seen = visibleWindows(of: [process.processIdentifier, getpid()])
                guard seen.isEmpty else { throw ParzrError.message("Stopped: \(seen.joined(separator: "; ")) is on a screen.") }
                guard let found = NSRunningApplication(processIdentifier: process.processIdentifier), found.bundleIdentifier == bundleIdentifier, let focused = AX.focusedText(found),
                      AX.string(focused, kAXValueAttribute) == initial.string, let stage = stageFrame(of: found) else { continue }
                let fixture = FixtureEditor(app: found, element: focused, stage: stage, process: process, directory: directory, board: board)
                try fixture.requireOffScreen(stage, "The fixture window")
                print("Fixture editor pid \(found.processIdentifier), window \(fixture.window) (Cocoa coordinates, off every screen).")
                SelfTestTarget.watch(found, stage: stage)
                // Every activation, not just what a sample happens to catch: the fixture or this test coming to the front is a failure.
                fixture.activation = NSWorkspace.shared.notificationCenter.addObserver(forName: NSWorkspace.didActivateApplicationNotification, object: nil, queue: .main) { [weak fixture] note in
                    guard let active = note.userInfo?[NSWorkspace.applicationUserInfoKey] as? NSRunningApplication else { return }
                    MainActor.assumeIsolated { fixture?.activated(active) }
                }
                fixture.monitor = Task { @MainActor [weak fixture] in
                    while !Task.isCancelled { fixture?.sample(); try? await Task.sleep(for: .milliseconds(100)) }
                }
                return fixture
            }
            throw ParzrError.message("The fixture editor did not expose its text field.")
        } catch { stop(); throw error }
    }

    private static func stageFrame(of app: NSRunningApplication) -> CGRect? {
        let element = AXUIElementCreateApplication(app.processIdentifier)
        guard let window = (AX.get(element, kAXWindowsAttribute) as? [AXUIElement])?.first, let p = AX.get(window, kAXPositionAttribute), let s = AX.get(window, kAXSizeAttribute) else { return nil }
        var origin = CGPoint.zero, size = CGSize.zero
        guard AXValueGetValue(p as! AXValue, .cgPoint, &origin), AXValueGetValue(s as! AXValue, .cgSize, &size), size.width > 0 else { return nil }
        return AX.cocoa(CGRect(origin: origin, size: size))
    }
    private static func terminate(_ process: Process) {
        guard process.isRunning else { return }
        process.terminate()
        for _ in 0..<40 where process.isRunning { RunLoop.current.run(until: Date().addingTimeInterval(0.05)) }
        if process.isRunning { kill(process.processIdentifier, SIGKILL); process.waitUntilExit() }
    }
    /// Windows of these processes that the window server lists as shown and that touch a display (CG coordinates, as listed).
    private static func visibleWindows(of pids: [pid_t]) -> [String] {
        let displays = NSScreen.screens.map(\.frame)
        let list = (CGWindowListCopyWindowInfo([.optionOnScreenOnly], kCGNullWindowID) as? [[String: Any]]) ?? []
        return list.compactMap { window in
            guard let pid = window[kCGWindowOwnerPID as String] as? pid_t, pids.contains(pid), (window[kCGWindowAlpha as String] as? Double ?? 1) > 0,
                  let b = window[kCGWindowBounds as String] as? [String: CGFloat], (b["Width"] ?? 0) > 0, (b["Height"] ?? 0) > 0 else { return nil }
            let rect = AX.cocoa(CGRect(x: b["X"] ?? 0, y: b["Y"] ?? 0, width: b["Width"] ?? 0, height: b["Height"] ?? 0))
            guard displays.contains(where: { $0.intersects(rect) }) else { return nil }
            return "\(window[kCGWindowOwnerName as String] as? String ?? "?") window \(rect)"
        }
    }
    private func sample() {
        let pids = [app.processIdentifier, getpid()]
        for seen in Self.visibleWindows(of: pids) where !violations.contains(seen) { violations.append("\(seen) is on a screen") }
        // Only the fixture or this test becoming frontmost counts: the owner may switch apps themselves.
        if let front = NSWorkspace.shared.frontmostApplication, pids.contains(front.processIdentifier) { activated(front) }
    }
    private func activated(_ active: NSRunningApplication) {
        guard [app.processIdentifier, getpid()].contains(active.processIdentifier) else { return }
        let note = "\(active.localizedName ?? "pid \(active.processIdentifier)") (pid \(active.processIdentifier)) became the frontmost app"
        if !violations.contains(note) { violations.append(note) }
    }
    /// Fails if the fixture or this test ever showed a window on a screen or took the front.
    func assertSafe() throws {
        sample()
        guard violations.isEmpty else { throw ParzrError.message("Not safe for the person using this Mac: \(violations.joined(separator: "; ")).") }
    }
    /// A window frame (Cocoa coordinates) must not touch any screen.
    func requireOffScreen(_ frame: CGRect, _ what: String) throws {
        if let screen = NSScreen.screens.first(where: { $0.frame.intersects(frame) }) { throw ParzrError.message("\(what) (\(frame)) touches a screen (\(screen.frame)).") }
    }
    /// The fixture's text field has this editor's keyboard focus.
    var isFocused: Bool { AX.focusedText(app).map { CFEqual($0, element) } == true }

    /// A key down and up delivered to the fixture's process only.
    func key(_ code: CGKeyCode, flags: CGEventFlags = [], unicode: UniChar? = nil) {
        for down in [true, false] {
            guard let event = CGEvent(keyboardEventSource: nil, virtualKey: code, keyDown: down) else { continue }
            event.flags = flags
            if let unicode { event.keyboardSetUnicodeString(stringLength: 1, unicodeString: [unicode]) }
            event.postToPid(app.processIdentifier)
        }
    }
    func undo() { key(6, flags: .maskCommand) }
    /// Puts `text` where the fixture's Cmd+V reads it.
    func stagePaste(_ text: String) { board?.clearContents(); board?.setString(text, forType: .string) }

    func close() {
        monitor?.cancel(); SelfTestTarget.clear()
        if let activation { NSWorkspace.shared.notificationCenter.removeObserver(activation) }
        Self.terminate(process)
        board?.releaseGlobally()
        try? FileManager.default.removeItem(at: directory)
    }
}
