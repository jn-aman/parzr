import SwiftUI
import AppKit
import Carbon

struct ShortcutRecorder: NSViewRepresentable {
    @ObservedObject var preferences = Preferences.shared
    func makeNSView(context: Context) -> ShortcutButton { ShortcutButton() }
    func updateNSView(_ button: ShortcutButton, context: Context) {
        button.title = preferences.recordingShortcut ? "Press your shortcut…" : preferences.shortcutDisplay
        button.setAccessibilityLabel("Global shortcut: \(preferences.shortcutDisplay). Click to record a shortcut.")
        if preferences.recordingShortcut { button.window?.makeFirstResponder(button) }
    }
}
@MainActor
final class ShortcutButton: NSButton {
    override var acceptsFirstResponder: Bool { true }
    init() {
        super.init(frame: .zero); bezelStyle = .rounded; target = self; action = #selector(record)
        font = .monospacedSystemFont(ofSize: 13, weight: .medium)
    }
    required init?(coder: NSCoder) { fatalError("Created programmatically") }
    @objc private func record() { Preferences.shared.recordingShortcut.toggle(); window?.makeFirstResponder(self) }
    override func keyDown(with event: NSEvent) {
        let prefs = Preferences.shared
        guard prefs.recordingShortcut else { super.keyDown(with: event); return }
        if event.keyCode == 53 { prefs.recordingShortcut = false; return }
        let flags = event.modifierFlags.intersection([.command, .option, .control, .shift])
        guard !flags.intersection([.command, .option, .control]).isEmpty else { NSSound.beep(); return }
        var modifiers = 0
        if flags.contains(.command) { modifiers |= Int(cmdKey) }
        if flags.contains(.option) { modifiers |= Int(optionKey) }
        if flags.contains(.control) { modifiers |= Int(controlKey) }
        if flags.contains(.shift) { modifiers |= Int(shiftKey) }
        let names: [UInt16: String] = [49: "Space", 36: "Return", 48: "Tab", 51: "Delete", 123: "←", 124: "→", 125: "↓", 126: "↑"]
        prefs.shortcutLabel = names[event.keyCode] ?? event.charactersIgnoringModifiers?.uppercased() ?? "Key \(event.keyCode)"
        prefs.shortcutKey = Int(event.keyCode); prefs.shortcutModifiers = modifiers
        prefs.recordingShortcut = false
    }
    override func resignFirstResponder() -> Bool { Preferences.shared.recordingShortcut = false; return super.resignFirstResponder() }
}
