import AppKit
import ParzrCore

/// Not part of the local release routine (it shows a real window and takes focus): the same checks run headless in `swift test` as OwnEditorWindowTests, and this stays for a VM or a spare Mac.
/// `--own-editor-test <dir>`: the shortcut inside Parzr's own writing space. Selects text in the Studio editor, runs the hotkey's handler (no HID events),
/// and checks the card shows the selection next to it, Return applies through Accessibility, Undo reverts, and the Studio's marks refresh each time.
/// Also checks the exception stays narrow: no selection gives the usual hint, and a focus outside the editor is still refused.
@MainActor
func runOwnEditorTest(app: AppDelegate, host: NSView, window: NSWindow, directory: String) async throws {
    let target = URL(fileURLWithPath: directory)
    try FileManager.default.createDirectory(at: target, withIntermediateDirectories: true)
    guard AXIsProcessTrusted() else { throw ParzrError.message("Accessibility is not granted to this process, so Parzr cannot read its own editor.") }
    func textView(_ view: NSView) -> NSTextView? { (view as? NSTextView) ?? view.subviews.lazy.compactMap(textView).first }
    guard let editor = textView(host), editor.accessibilityIdentifier() == Compat.draftEditorIdentifier else { throw ParzrError.message("The writing space has no accessibility identifier.") }
    let studio = app.studioModel, card = app.panelModel
    func wait(_ what: String, _ ok: () -> Bool) async throws {
        for _ in 0..<160 { if ok() { return }; try await Task.sleep(for: .milliseconds(50)) }
        throw ParzrError.message("Timed out waiting for \(what) (draft \"\(editor.string)\", studio source \"\(studio.source)\", busy \(studio.busy), edits \(studio.chosenEdits.map(\.original)), error \(studio.error ?? "none"), card error \(card.error ?? "none")).")
    }
    func closeCard() { card.dismiss?() }
    func marked(_ text: String) -> Bool { studio.source == editor.string && !studio.busy && studio.chosenEdits.contains { $0.replacement == text } }
    let original = "this os do bad."
    window.makeKeyAndOrderFront(nil); window.makeFirstResponder(editor)
    editor.insertText(original, replacementRange: NSRange(location: 0, length: editor.string.utf16.count))
    try await wait("the Studio's own marks", { marked("T") })
    var report: [String: Any] = ["original": original]

    // 1. Selected text: the card opens on it, anchored at the selection.
    editor.setSelectedRange(NSRange(location: 0, length: editor.string.utf16.count))
    app.openSelection()
    try await wait("the card", { card.snapshot != nil && !card.busy && !card.chosenEdits.isEmpty })
    guard let panel = app.panel, panel.isVisible, panel.isKeyWindow else { throw ParzrError.message("The card is not the key window.") }
    guard card.source == original, card.snapshot?.own == true else { throw ParzrError.message("The card shows \"\(card.source)\" instead of the selection.") }
    guard let bounds = card.snapshot?.bounds else { throw ParzrError.message("The selection has no on-screen bounds, so the card cannot anchor to it.") }
    let gap = min(abs(panel.frame.maxY - bounds.minY), abs(panel.frame.minY - bounds.maxY))
    guard gap < 24, panel.frame.minX <= bounds.maxX, panel.frame.maxX >= bounds.minX else { throw ParzrError.message("The card is not anchored at the selection (gap \(gap)).") }
    try NativeControls.snapshot(host, to: target.appendingPathComponent("own-1-selection.png"))
    if let content = panel.contentView { try NativeControls.snapshot(content, to: target.appendingPathComponent("own-2-card.png")) }
    report["card_source"] = card.source; report["card_edits"] = card.chosenEdits.map(\.original); report["anchor_gap"] = gap

    // 2. Return applies to the editor (a key event sent to the card, not a HID event).
    guard let event = NSEvent.keyEvent(with: .keyDown, location: .zero, modifierFlags: [], timestamp: ProcessInfo.processInfo.systemUptime, windowNumber: panel.windowNumber, context: nil, characters: "\r", charactersIgnoringModifiers: "\r", isARepeat: false, keyCode: 36) else { throw ParzrError.message("Could not build the Return key event.") }
    NSApp.sendEvent(event)
    try await wait("the fix to land in the editor", { editor.string != original })
    let fixed = editor.string
    try await wait("the card to close", { !panel.isVisible })
    guard fixed.hasPrefix("This") else { throw ParzrError.message("Return did not apply the fix and close the card: \"\(fixed)\".") }
    try await wait("the Studio's marks to refresh", { studio.source == fixed && !studio.busy && studio.result != nil })
    guard !marked("T") else { throw ParzrError.message("The stale capitalisation mark survived the fix.") }
    try NativeControls.snapshot(host, to: target.appendingPathComponent("own-3-applied.png"))
    report["fixed"] = fixed

    // 3. Undo reverts the whole fix, and the marks follow.
    if !window.isKeyWindow { report["window_not_key_after_close"] = true; window.makeKeyAndOrderFront(nil) }
    window.makeFirstResponder(editor)
    editor.undoManager?.undo()
    guard editor.string == original else { throw ParzrError.message("Undo left \"\(editor.string)\" instead of the original text.") }
    try await wait("the marks to come back after Undo", { marked("T") })
    try NativeControls.snapshot(host, to: target.appendingPathComponent("own-4-undone.png"))

    // 4. No selection: the same hint as in any other app.
    editor.setSelectedRange(NSRange(location: 4, length: 0))
    app.openSelection()
    try await wait("the hint", { card.selectionHint })
    guard card.snapshot == nil else { throw ParzrError.message("An empty selection produced a snapshot.") }
    if let content = app.panel?.contentView { try NativeControls.snapshot(content, to: target.appendingPathComponent("own-5-no-selection.png")) }
    closeCard()

    // 5. Outside the writing space Parzr still reads nothing of its own.
    window.makeKeyAndOrderFront(nil); window.makeFirstResponder(nil)
    app.openSelection()
    try await wait("the refusal", { card.error != nil })
    guard card.snapshot == nil, card.source.isEmpty else { throw ParzrError.message("Parzr read its own window outside the writing space.") }
    closeCard()
    let data = try JSONSerialization.data(withJSONObject: report, options: [.prettyPrinted, .sortedKeys])
    try data.write(to: target.appendingPathComponent("own-editor-results.json"))
    print(String(decoding: data, as: UTF8.self))
}
