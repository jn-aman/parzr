import AppKit
import ParzrCore

/// `--editor-typing-test <dir>`: types into the Studio writing space through the NSTextView (no HID events) faster than the checking delay,
/// samples the view every few ms, and fails if marks before the caret vanish, the UI shows a busy state, or the text view is rewritten.
@MainActor
func runEditorTypingTest(model: AppModel, host: NSView, window: NSWindow, directory: String) async throws {
    let target = URL(fileURLWithPath: directory)
    try FileManager.default.createDirectory(at: target, withIntermediateDirectories: true)
    func textView(_ view: NSView) -> NSTextView? { (view as? NSTextView) ?? view.subviews.lazy.compactMap(textView).first }
    guard let editor = textView(host), let layout = editor.layoutManager, let storage = editor.textStorage else { throw ParzrError.message("The draft text view is unavailable.") }
    window.makeFirstResponder(editor)
    func type(_ text: String) { editor.insertText(text, replacementRange: editor.selectedRange()) }
    func settled(_ count: Int) async throws {
        for _ in 0..<120 { try await Task.sleep(for: .milliseconds(50)); if !model.busy, model.result != nil, model.source == editor.string, model.chosenEdits.count >= count { return } }
        throw ParzrError.message("The check did not settle with \(count) suggestions.")
    }
    type("I recieved your mesage. "); try await settled(2)
    let marked = ["recieved", "mesage"].map { (editor.string as NSString).range(of: $0).location }
    func marksPresent() -> Bool { marked.allSatisfy { layout.temporaryAttribute(.underlineStyle, atCharacterIndex: $0, effectiveRange: nil) != nil } }
    guard marksPresent() else { throw ParzrError.message("The baseline marks are not drawn.") }
    try NativeControls.snapshot(host, to: target.appendingPathComponent("typing-0-before.png"))
    var edits = 0
    nonisolated(unsafe) let watched = storage
    let observer = NotificationCenter.default.addObserver(forName: NSTextStorage.didProcessEditingNotification, object: watched, queue: .main) { _ in MainActor.assumeIsolated { if watched.editedMask.contains(.editedCharacters) { edits += 1 } } }
    defer { NotificationCenter.default.removeObserver(observer) }
    var samples = 0, missingMarks = 0, busy = 0, checkDisabled = 0, copyDisabled = 0
    let sampler = Task { @MainActor in
        let check = NativeControls.find(label: "Check passage", in: host), copy = NativeControls.find(label: "Copy", in: host)
        while !Task.isCancelled {
            samples += 1
            if !marksPresent() { missingMarks += 1 }
            if model.busy { busy += 1 }
            if check?.isAccessibilityEnabled() == false { checkDisabled += 1 }
            if copy?.isAccessibilityEnabled() == false { copyDisabled += 1 }
            try? await Task.sleep(for: .milliseconds(4))
        }
    }
    let typed = "Can you chek this and tel me?", expected = editor.string + typed
    var frame = 1, caretMoved = 0
    let delays = [70, 110, 60, 140, 90] // realistic cadence, mostly inside the checking delay
    for character in typed {
        type(String(character))
        if editor.selectedRange().location != editor.string.utf16.count { caretMoved += 1 }
        // Frames mid-burst, a moment after a key.
        try await Task.sleep(for: .milliseconds(delays[frame % delays.count]))
        if [3, 9, 17, 24].contains(frame) { try NativeControls.snapshot(host, to: target.appendingPathComponent("typing-\(frame)-mid.png")) }
        frame += 1
    }
    sampler.cancel()
    let rewrites = edits - typed.count
    try await settled(2)
    try NativeControls.snapshot(host, to: target.appendingPathComponent("typing-9-after.png"))
    let report: [String: Any] = ["samples": samples, "samples_missing_marks": missingMarks, "samples_busy": busy, "samples_check_disabled": checkDisabled, "samples_copy_disabled": copyDisabled,
                                 "extra_text_storage_edits": rewrites, "caret_moved": caretMoved, "text_intact": editor.string == expected, "final_text": editor.string, "final_suggestions": model.chosenEdits.count]
    let data = try JSONSerialization.data(withJSONObject: report, options: [.prettyPrinted, .sortedKeys])
    try data.write(to: target.appendingPathComponent("editor-typing-results.json"))
    print(String(decoding: data, as: UTF8.self))
    guard editor.string == expected, caretMoved == 0, rewrites == 0 else { throw ParzrError.message("The text view was rewritten or the caret moved while typing.") }
    guard missingMarks == 0, busy == 0, checkDisabled == 0, copyDisabled == 0 else { throw ParzrError.message("The editor flickered while typing: marks vanished, Checking showed or buttons were disabled.") }
}
