import AppKit
import ParzrCore

/// `--click-test <dir>`: delivers real mouse clicks (down and up through the window's own event path, never HID) to the marked words of a CorrectionTextView
/// and fails when the correction card does not open for the clicked word. Run for both the onboarding "Try it" field and the Studio editor.
@MainActor
func runCardClickTest(host: NSView, window: NSWindow, surface: String, typing: String?, directory: String) async throws {
    let target = URL(fileURLWithPath: directory)
    try FileManager.default.createDirectory(at: target, withIntermediateDirectories: true)
    func textView(_ view: NSView) -> CorrectionTextView? { (view as? CorrectionTextView) ?? view.subviews.lazy.compactMap(textView).first }
    guard let editor = textView(host), let layout = editor.layoutManager, let container = editor.textContainer else { throw ParzrError.message("\(surface): the draft text view is unavailable.") }
    if let typing { window.makeFirstResponder(editor); editor.insertText(typing, replacementRange: editor.selectedRange()) }
    func ready(_ count: Int) async throws {
        for _ in 0..<160 { try await Task.sleep(for: .milliseconds(50)); if editor.suggestions.count >= count { return } }
        throw ParzrError.message("\(surface): the check did not settle with \(count) marks (\(editor.suggestions.count) drawn).")
    }
    try await ready(2)
    var serial = 0, failures: [String] = [], probes = 0
    func click(at point: NSPoint) {
        serial += 1
        let location = editor.convert(point, to: nil)
        func event(_ type: NSEvent.EventType) -> NSEvent? { NSEvent.mouseEvent(with: type, location: location, modifierFlags: [], timestamp: ProcessInfo.processInfo.systemUptime, windowNumber: window.windowNumber, context: nil, eventNumber: serial, clickCount: 1, pressure: type == .leftMouseDown ? 1 : 0) }
        // NSTextView tracks the mouse inside mouseDown until the button is up, so the up event is queued first.
        if let up = event(.leftMouseUp) { NSApp.postEvent(up, atStart: false) }
        if let down = event(.leftMouseDown) { window.sendEvent(down) }
    }
    func rect(of edit: WritingEdit) -> NSRect? {
        guard let range = editor.displayRange(for: edit) else { return nil }
        return layout.boundingRect(forGlyphRange: layout.glyphRange(forCharacterRange: range, actualCharacterRange: nil), in: container).offsetBy(dx: editor.textContainerOrigin.x, dy: editor.textContainerOrigin.y)
    }
    /// Clicks each mark at the middle, near the underline, and near its left edge; the card must open for exactly that edit.
    func probeAll(_ stage: String) async throws {
        for edit in editor.suggestions {
            guard let box = rect(of: edit) else { continue }
            let spots = [("middle", NSPoint(x: box.midX, y: box.midY)), ("underline", NSPoint(x: box.midX, y: box.maxY - 3)), ("left edge", NSPoint(x: box.minX + 1.5, y: box.midY))]
            for (name, point) in spots {
                probes += 1
                click(at: point)
                try await Task.sleep(for: .milliseconds(120))
                let shown = editor.shownCorrection == edit
                if !shown { failures.append("\(surface) \(stage): clicking the \(name) of \"\(edit.original)\" at \(point) (box \(box)) did not open its card (shown: \(editor.shownCorrection?.original ?? "none"), caret \(editor.selectedRange().location))") }
                else if name == "middle", let view = editor.correctionView { try NativeControls.snapshot(view, to: target.appendingPathComponent("\(surface)-\(stage)-\(edit.original.filter(\.isLetter)).png")) }
                editor.dismissCorrection()
            }
        }
    }
    try await probeAll("fresh")
    // Outside a word nothing may open: the space after it, and the margin above its line.
    if let edit = editor.suggestions.first(where: { $0.original.first?.isLetter == true && $0.original.count > 1 }), let box = rect(of: edit) {
        for (name, point) in [("space after", NSPoint(x: box.maxX + 2, y: box.midY)), ("margin above", NSPoint(x: box.midX, y: box.minY - 6))] {
            probes += 1
            click(at: point)
            try await Task.sleep(for: .milliseconds(120))
            if let wrong = editor.shownCorrection { failures.append("\(surface): clicking the \(name) \"\(edit.original)\" opened a card for \"\(wrong.original)\"") }
            editor.dismissCorrection()
        }
    }
    // After one fix is applied the remaining marks must still open their cards.
    if let first = editor.suggestions.last {
        let before = editor.suggestions.count
        editor.accept(first)
        for _ in 0..<160 { try await Task.sleep(for: .milliseconds(50)); if editor.suggestions.count == before - 1, !editor.string.contains(first.original) { break } }
        try await Task.sleep(for: .milliseconds(300))
        try await probeAll("after-apply")
    }
    let report: [String: Any] = ["surface": surface, "probes": probes, "failures": failures, "final_text": editor.string]
    let data = try JSONSerialization.data(withJSONObject: report, options: [.prettyPrinted, .sortedKeys])
    try data.write(to: target.appendingPathComponent("\(surface)-click-results.json"))
    print(String(decoding: data, as: UTF8.self))
    try NativeControls.snapshot(host, to: target.appendingPathComponent("\(surface)-after.png"))
    guard probes > 0, failures.isEmpty else { throw ParzrError.message(failures.first ?? "\(surface): no marks were probed.") }
}
