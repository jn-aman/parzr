import AppKit
import ApplicationServices
import Carbon
import ParzrCore

/// Explicit QA for Google Docs in a Chromium browser, run from a terminal that has Accessibility (`parzr --docs-test <dir>`).
/// The browser's frontmost window must be an authored test document with "screen reader support" and "braille support" on and one paragraph whose caret
/// can be placed at its end. It types one space (the automatic check), screenshots the marks, clicks one, applies it, then undoes it.
@MainActor
func runGoogleDocsTest(reportDirectory: String) async throws {
    guard AXIsProcessTrusted(), !IsSecureEventInputEnabled() else { throw ParzrError.message("Docs QA needs Accessibility with secure input off.") }
    let directory = URL(fileURLWithPath: reportDirectory)
    try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
    // Chromium builds its accessibility tree only while an assistive client asks; the running app does this, the test must too.
    if let front = NSWorkspace.shared.frontmostApplication, Compat.isChromium(front.bundleIdentifier) { AX.prepare(front, force: true); try await Task.sleep(for: .milliseconds(1200)) }
    guard let app = NSWorkspace.shared.frontmostApplication, Compat.isChromium(app.bundleIdentifier), let element = AX.focusedText(app), AX.isDocsText(element) else {
        throw ParzrError.message("Bring the authored Google Docs test document to the front of a Chromium browser first.")
    }
    guard let value = AX.string(element, kAXValueAttribute), !Compat.docsTextHidden(value) else { throw ParzrError.message("The document exposes no text: turn on screen reader and braille support in Docs.") }
    // The paragraph under test is the last one; the caret goes to its end.
    let text = value as NSString
    var end = text.length
    while end > 0, text.character(at: end - 1) == 10 { end -= 1 }
    guard AX.setRange(element, NSRange(location: end, length: 0)) else { throw ParzrError.message("Docs refused the caret.") }
    try await Task.sleep(for: .milliseconds(500))
    let screenTop = NSScreen.screens.first?.frame.maxY ?? 0
    func axRect(_ cocoa: CGRect) -> CGRect { CGRect(x: cocoa.minX, y: screenTop - cocoa.maxY, width: cocoa.width, height: cocoa.height) }
    func rectJSON(_ r: CGRect) -> [Double] { [r.minX, r.minY, r.width, r.height].map { Double($0 * 10).rounded() / 10 } }
    func shot(_ name: String) throws {
        let process = Process(); process.executableURL = URL(fileURLWithPath: "/usr/sbin/screencapture"); process.arguments = ["-x", directory.appendingPathComponent(name).path]
        try process.run(); process.waitUntilExit()
    }
    /// Keys go to the browser's pid only, and only while it is frontmost on the test document; anything else stops the run.
    func guardTarget() throws {
        guard NSWorkspace.shared.frontmostApplication?.processIdentifier == app.processIdentifier else { throw ParzrError.message("The browser is no longer frontmost; stopping.") }
        let process = Process(); process.executableURL = URL(fileURLWithPath: "/usr/bin/osascript")
        process.arguments = ["-e", "tell application id \"\(app.bundleIdentifier ?? "com.google.Chrome")\" to get URL of active tab of front window"]
        let pipe = Pipe(); process.standardOutput = pipe; process.standardError = Pipe()
        try process.run(); process.waitUntilExit()
        let url = String(decoding: pipe.fileHandleForReading.readDataToEndOfFile(), as: UTF8.self)
        guard url.contains("docs.google.com/document/d/1TG-RFFVPvJzoB6y6nqyRTHjAoN98iZV2bdaEhtRsLCs") else { throw ParzrError.message("The active tab is not the test document; stopping.") }
    }
    func press(_ key: CGKeyCode, flags: CGEventFlags = [], unicode: [UInt16]? = nil) {
        for down in [true, false] {
            guard let event = CGEvent(keyboardEventSource: nil, virtualKey: key, keyDown: down) else { continue }
            event.flags = flags
            if let unicode { event.keyboardSetUnicodeString(stringLength: unicode.count, unicodeString: unicode) }
            event.postToPid(app.processIdentifier)
        }
    }
    try shot("docs-before.png")
    let inline = InlineSuggestions(); let observer = PassiveObserver()
    defer { observer.stop(); inline.stop() }
    var captured: (SelectionSnapshot, RewriteResult)?
    var marked = false
    observer.onDismiss = { inline.dismissIfStale() }
    observer.onSuggestion = { snapshot, result in
        guard snapshot.app.processIdentifier == app.processIdentifier, snapshot.docs else { return }
        captured = (snapshot, result)
        if ProcessInfo.processInfo.environment["PARZR_DOCS_DEBUG"] != nil {
            fputs("snapshot sel=\(snapshot.selection) paragraph=\(snapshot.text.count) edits=\(result.edits.map { "\($0.original)>\($0.replacement)@\($0.start_utf16)" })\n", stderr)
            for edit in result.edits { fputs("  \(edit.original): bounds=\(String(describing: AX.bounds(snapshot.element, NSRange(location: snapshot.selection.location + edit.start_utf16, length: max(1, edit.end_utf16 - edit.start_utf16)))))\n", stderr) }
        }
        let shown = inline.show(snapshot: snapshot, result: result)
        marked = shown && result.edits.allSatisfy { inline.markedView(for: $0) != nil }
        if ProcessInfo.processInfo.environment["PARZR_DOCS_DEBUG"] != nil { fputs("show=\(shown) marked=\(marked) hasMarks=\(inline.hasMarks)\n", stderr) }
    }
    observer.attach()
    try await Task.sleep(for: .milliseconds(400))
    // Type one space after the last word: the same automatic check a writer triggers.
    guard AX.focusedText(app).map({ CFEqual($0, element) }) == true, AX.range(element) == NSRange(location: end, length: 0) else { throw ParzrError.message("The document changed before QA could type.") }
    // Attaching checks the paragraph once at once; only marks that arrive after the typed space count.
    inline.dismiss(); marked = false; captured = nil
    try guardTarget()
    press(49, unicode: [32])
    for _ in 0..<60 { try await Task.sleep(for: .milliseconds(50)); if AX.string(element, kAXValueAttribute) != value { break } }
    marked = false; captured = nil
    for _ in 0..<160 { try await Task.sleep(for: .milliseconds(50)); if marked { break } }
    if ProcessInfo.processInfo.environment["PARZR_DOCS_DEBUG"] != nil { fputs("marked=\(marked) captured=\(captured != nil) len now=\((AX.string(element, kAXValueAttribute) ?? "").utf16.count) before=\(value.utf16.count) end=\(end)\n", stderr) }
    guard marked, let (snapshot, result) = captured, (AX.string(element, kAXValueAttribute) ?? "").utf16.count == value.utf16.count + 1 else { // Docs turns repeated spaces into no-break spaces, so only the length is compared
        throw ParzrError.message("Typing in Docs did not produce automatic marks.")
    }
    try await Task.sleep(for: .milliseconds(300))
    try shot("docs-marks.png")
    var placed: [[String: Any]] = []
    for edit in result.edits {
        let global = NSRange(location: snapshot.selection.location + edit.start_utf16, length: max(1, edit.end_utf16 - edit.start_utf16))
        guard let rect = AX.bounds(element, global) else { continue }
        placed.append(["original": edit.original, "replacement": edit.replacement, "rect": rectJSON(axRect(rect))])
    }
    // Click the first spelling mark with a real pointer.
    guard let edit = result.edits.first(where: { $0.category == "Spelling" }) ?? result.edits.first, let rect = AX.bounds(element, NSRange(location: snapshot.selection.location + edit.start_utf16, length: max(1, edit.end_utf16 - edit.start_utf16))) else {
        throw ParzrError.message("No mark to click.")
    }
    _ = rect
    try guardTarget()
    // The mark's own accessibility button opens the card, as for any assistive client (no pointer events are posted).
    guard let mark = inline.markedView(for: edit), let markButton = NativeControls.find(label: "Review \(edit.category.lowercased()) correction", in: mark), markButton.accessibilityPerformPress() else { throw ParzrError.message("The Docs mark has no button.") }
    for _ in 0..<60 { try await Task.sleep(for: .milliseconds(25)); if inline.isPresenting { break } }
    guard let card = inline.correctionView else { throw ParzrError.message("The Docs mark did not open its card.") }
    try await Task.sleep(for: .milliseconds(300))
    try shot("docs-card.png")
    let before = AX.string(element, kAXValueAttribute) ?? ""
    let related = EditPlan.related(to: edit, in: result.edits)
    let expected = try EditPlan.apply(related, to: snapshot.text)
    let expectedFull = (before as NSString).replacingCharacters(in: snapshot.selection, with: expected)
    guard let button = NativeControls.find(label: "Apply correction: \(edit.replacementLabel)", in: card) ?? NativeControls.find(label: "Fix sentence", in: card), button.accessibilityPerformPress() else { throw ParzrError.message("The card has no apply button.") }
    var applied = false
    for _ in 0..<100 { try await Task.sleep(for: .milliseconds(50)); if AX.string(element, kAXValueAttribute) != before { applied = true; break } }
    // The apply also walks the caret back to where the writer was typing; wait for the selection to hold still before looking.
    var lastSelection = AX.rawRange(element), still = 0, selectionLog: [String] = []
    for tick in 0..<240 { try await Task.sleep(for: .milliseconds(50)); let now = AX.rawRange(element); if now != lastSelection { selectionLog.append("\(tick * 50) ms: \(now.map { "\($0.location),\($0.length)" } ?? "nil")") }; still = now == lastSelection ? still + 1 : 0; lastSelection = now; if still >= 20, !selectionLog.isEmpty { break } }
    if ProcessInfo.processInfo.environment["PARZR_DOCS_DEBUG"] != nil { fputs("selection after apply: \(selectionLog)\n", stderr) }
    let after = AX.string(element, kAXValueAttribute) ?? ""
    if ProcessInfo.processInfo.environment["PARZR_DOCS_DEBUG"] != nil {
        let fresh = AX.focusedText(app)
        fputs("word range now: \((after as NSString).substring(with: NSRange(location: snapshot.selection.location + edit.start_utf16, length: 10)).debugDescription), expected \(edit.replacement)\n", stderr)
        fputs("fresh focus same element: \(fresh.map { CFEqual($0, element) } ?? false) fresh raw range: \(String(describing: fresh.flatMap { AX.rawRange($0) })) old raw range: \(String(describing: AX.rawRange(element)))\n", stderr)
    }
    let caretAfter = AX.range(element)
    try shot("docs-applied.png")
    // Undo: one Cmd+Z per step until the text is back (at most four).
    var undoSteps = 0
    inline.dismiss(); observer.stop()
    var trail: [String] = []
    let wordRange = NSRange(location: snapshot.selection.location + edit.start_utf16, length: edit.end_utf16 - edit.start_utf16)
    func wordIsBack() -> Bool {
        let now = (AX.string(element, kAXValueAttribute) ?? "") as NSString
        return NSMaxRange(wordRange) <= now.length && now.substring(with: wordRange) == edit.original
    }
    var wordBackAt = 0
    for step in 1...4 {
        let current = AX.string(element, kAXValueAttribute)
        try guardTarget()
        press(6, flags: .maskCommand)
        for _ in 0..<30 { try await Task.sleep(for: .milliseconds(50)); if AX.string(element, kAXValueAttribute) != current { break } }
        try await Task.sleep(for: .milliseconds(400))
        undoSteps = step
        let value = AX.string(element, kAXValueAttribute) ?? ""
        trail.append("step \(step): length \(value.utf16.count), original word back: \(wordIsBack()), equals the text before apply: \(value == before)")
        if wordIsBack() { wordBackAt = step; break }
    }
    let restored = wordBackAt > 0
    try shot("docs-undone.png")
    let report: [String: Any] = ["status": applied && restored && after == expectedFull ? "passed" : "failed", "editor": app.bundleIdentifier ?? "", "edits": result.edits.count, "marks": placed, "clicked": edit.original, "replacement": edit.replacement,
                                 "applied": applied, "expected_text_match": after == expectedFull, "undo_steps": undoSteps, "undo_word_back_at_step": wordBackAt, "undo_restored": restored, "text_after": after.count, "text_before": before.count, "caret_after_apply": caretAfter.map { [$0.location, $0.length] } ?? [], "undo_trail": trail]
    try JSONSerialization.data(withJSONObject: report, options: [.prettyPrinted, .sortedKeys]).write(to: directory.appendingPathComponent("docs-results.json"))
    guard applied, restored, after == expectedFull else { throw ParzrError.message("Docs apply or undo failed. See docs-results.json.") }
}
