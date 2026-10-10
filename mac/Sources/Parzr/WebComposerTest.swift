import AppKit
import ApplicationServices
import ParzrCore

/// Explicit QA for Chromium contenteditable composers (`parzr --web-composer-test <dir> <pid> <dom-id>...`). A Chromium host you started for the test
/// (Chrome for Testing, a bare Electron) shows `tests/fixtures/web-composers.html` and is frontmost, since Chromium reports focus only then. For each DOM id
/// the composer is focused through Accessibility, captured as an automatic check would be, run through the typing engine and marked; the run fails unless
/// every edit gets a mark. Nothing is typed and nothing is applied, and the host is never one the owner uses.
@MainActor
func runWebComposerTest(reportDirectory: String, pid: pid_t, ids: [String]) async throws {
    guard AXIsProcessTrusted() else { throw ParzrError.message("Composer QA needs Accessibility.") }
    guard let app = NSRunningApplication(processIdentifier: pid), let screen = NSScreen.screens.first else { throw ParzrError.message("No app with pid \(pid).") }
    guard NSWorkspace.shared.frontmostApplication?.processIdentifier == pid else { throw ParzrError.message("Bring the composer page to the front first: Chromium reports focus only for the frontmost app.") }
    SelfTestTarget.watch(app, stage: screen.frame)
    defer { SelfTestTarget.clear() }
    AX.prepare(app, force: true)
    // Chrome for Testing is not on Parzr's browser list, so the test host gets Chrome's switch here (an Electron host already took AXManualAccessibility).
    _ = AXUIElementSetAttributeValue(AXUIElementCreateApplication(pid), "AXEnhancedUserInterface" as CFString, kCFBooleanTrue)
    try await Task.sleep(for: .milliseconds(1200))
    func find(_ id: String) -> AXUIElement? {
        var hit: AXUIElement?
        func walk(_ node: AXUIElement, _ depth: Int) {
            if AX.string(node, "AXDOMIdentifier") == id { hit = node; return }
            guard depth < 60 else { return }
            for child in AX.get(node, kAXChildrenAttribute) as? [AXUIElement] ?? [] where hit == nil { walk(child, depth + 1) }
        }
        walk(AXUIElementCreateApplication(pid), 0)
        return hit
    }
    // Chromium builds its tree a moment after the switch, and only while a client keeps asking.
    for _ in 0..<20 where ids.first.flatMap(find) == nil { try await Task.sleep(for: .milliseconds(250)) }
    let inline = InlineSuggestions(headless: false)
    defer { inline.stop() }
    var failures: [String] = [], lines: [String] = []
    for id in ids {
        guard let element = find(id), let value = AX.text(element) else { failures.append("\(id): not found"); continue }
        AX.forgetFocus()
        _ = AXUIElementSetAttributeValue(element, kAXFocusedAttribute as CFString, kCFBooleanTrue)
        _ = AX.setRange(element, NSRange(location: (value as NSString).length, length: 0))
        try await Task.sleep(for: .milliseconds(250))
        let snapshot: SelectionSnapshot
        do { snapshot = try SelectionSnapshot.capture(passive: true) } catch { failures.append("\(id): capture failed: \(error.localizedDescription)"); continue }
        let request = EngineRequest(text: snapshot.text, dictionary: [], names: [], capitalizeNames: false, dialect: Preferences.shared.dialect, protectedRanges: snapshot.protectedRanges(),
                                    sentenceStart: snapshot.startsSentence, sentenceEnd: snapshot.endsSentence, gec: false)
        let result = try await WritingEngine.typing.rewrite(request)
        let shown = inline.show(snapshot: snapshot, result: result)
        let marked = result.edits.filter { inline.markedView(for: $0) != nil }
        let rects = result.edits.map { edit in AX.bounds(snapshot.element, NSRange(location: snapshot.selection.location + edit.start_utf16, length: max(1, edit.end_utf16 - edit.start_utf16))).map { "\(Int($0.minX)),\(Int($0.minY)) \(Int($0.width))x\(Int($0.height))" } ?? "none" }
        lines.append("\(id): role=\(AX.string(snapshot.element, kAXRoleAttribute) ?? "?") chromium=\(AX.isChromiumText(snapshot.element)) edits=\(result.edits.map(\.original)) marked=\(marked.count)/\(result.edits.count) shown=\(shown) snapshotBounds=\(snapshot.bounds != nil) lines=\(AX.lineRects(snapshot.element, snapshot.selection).count) rects=\(rects)")
        if result.edits.isEmpty || marked.count != result.edits.count || snapshot.bounds == nil { failures.append("\(id): \(marked.count) of \(result.edits.count) edits marked") }
        inline.dismiss()
    }
    lines.forEach { print($0) }
    let directory = URL(fileURLWithPath: reportDirectory)
    try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
    try (lines + failures).joined(separator: "\n").write(to: directory.appendingPathComponent("web-composers.txt"), atomically: true, encoding: .utf8)
    guard failures.isEmpty else { throw ParzrError.message(failures.joined(separator: "; ")) }
}
