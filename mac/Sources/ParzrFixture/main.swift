import AppKit

/// Test-only stand-in for a text editor, launched by Parzr's self tests (`--paste-test` and the others) so they never touch TextEdit or any app the owner uses.
/// It is an `.accessory` app (no Dock icon, no menu bar, never activated) whose one window is a non-activating panel placed outside every screen,
/// so nothing is ever drawn where a person looks, and the frontmost app and keyboard focus never change. It exits on its own when its parent test process ends.
///
/// ParzrFixture --parent <pid> --file <text.rtf|text.txt> [--pasteboard <name>] [--caret <utf16 offset>]
///   .rtf opens as a rich-text field, anything else as plain text.
///   --pasteboard: Cmd+V reads this private pasteboard instead of the owner's clipboard.
let arguments = CommandLine.arguments
func argument(_ flag: String) -> String? { arguments.firstIndex(of: flag).flatMap { arguments.indices.contains($0 + 1) ? arguments[$0 + 1] : nil } }
guard let parentPID = argument("--parent").flatMap({ pid_t($0) }), let filePath = argument("--file") else {
    FileHandle.standardError.write(Data("usage: ParzrFixture --parent <pid> --file <text> [--pasteboard <name>] [--caret <offset>]\n".utf8)); exit(2)
}

/// Reads a paste from the named private pasteboard when one is given.
final class FixtureTextView: NSTextView {
    var board: NSPasteboard?
    override func paste(_ sender: Any?) {
        guard let board else { return super.paste(sender) }
        _ = readSelection(from: board)
    }
}

/// A panel that can take keyboard focus without activating the app.
final class FixturePanel: NSPanel {
    override var canBecomeKey: Bool { true }
    override var canBecomeMain: Bool { false }
    /// Never pulled back onto a screen.
    override func constrainFrameRect(_ frameRect: NSRect, to screen: NSScreen?) -> NSRect { frameRect }
}

@MainActor
final class Fixture: NSObject, NSApplicationDelegate {
    var panel: FixturePanel?
    let parent: pid_t, path: String
    init(parent: pid_t, path: String) { self.parent = parent; self.path = path }
    func applicationDidFinishLaunching(_ notification: Notification) {
        let rich = path.hasSuffix(".rtf")
        let url = URL(fileURLWithPath: path)
        // Entirely right of the union of every screen, level with its bottom edge.
        let union = NSScreen.screens.map(\.frame).reduce(CGRect.null) { $0.union($1) }
        let frame = CGRect(x: union.maxX + 4000, y: union.minY, width: 600, height: 300)
        let panel = FixturePanel(contentRect: frame, styleMask: [.borderless, .nonactivatingPanel], backing: .buffered, defer: true)
        panel.isReleasedWhenClosed = false; panel.hidesOnDeactivate = false; panel.title = "Parzr fixture"
        panel.setFrame(frame, display: false)
        let scroll = NSScrollView(frame: CGRect(origin: .zero, size: frame.size))
        let text = FixtureTextView(frame: scroll.bounds)
        text.board = argument("--pasteboard").map { NSPasteboard(name: NSPasteboard.Name($0)) }
        text.isRichText = rich; text.allowsUndo = true; text.isEditable = true; text.isSelectable = true
        text.isAutomaticSpellingCorrectionEnabled = false; text.isContinuousSpellCheckingEnabled = false; text.isGrammarCheckingEnabled = false
        text.isAutomaticQuoteSubstitutionEnabled = false; text.isAutomaticDashSubstitutionEnabled = false; text.isAutomaticTextReplacementEnabled = false
        text.isAutomaticTextCompletionEnabled = false; text.isAutomaticLinkDetectionEnabled = false; text.isAutomaticDataDetectionEnabled = false
        text.autoresizingMask = [.width]; text.isVerticallyResizable = true; text.textContainer?.widthTracksTextView = true
        if rich, let attributed = try? NSAttributedString(url: url, options: [.documentType: NSAttributedString.DocumentType.rtf], documentAttributes: nil) {
            text.textStorage?.setAttributedString(attributed)
        } else {
            text.font = .systemFont(ofSize: 16); text.string = (try? String(contentsOf: url, encoding: .utf8)) ?? ""
        }
        scroll.documentView = text; scroll.hasVerticalScroller = false
        panel.contentView = scroll
        NSApp.mainMenu = menu()
        self.panel = panel
        // Key without activating: the window gets the keyboard focus inside this process only.
        panel.orderFront(nil); panel.makeKey(); panel.makeFirstResponder(text)
        (NSApp as? FixtureApplication)?.refocus = { [weak panel, weak text] in panel?.makeKey(); panel?.makeFirstResponder(text) }
        let caret = argument("--caret").flatMap { Int($0) } ?? text.string.utf16.count
        text.setSelectedRange(NSRange(location: min(caret, text.string.utf16.count), length: 0))
        Timer.scheduledTimer(withTimeInterval: 0.25, repeats: true) { _ in if getppid() != self.parent { exit(0) } }
        // A runaway fixture can never outlive a long session.
        DispatchQueue.main.asyncAfter(deadline: .now() + 900) { exit(0) }
    }
    /// Cmd+V, Cmd+C, Cmd+X and Cmd+Z reach the text view through key equivalents, as in any editor.
    func menu() -> NSMenu {
        let main = NSMenu(), item = NSMenuItem(), edit = NSMenu(title: "Edit")
        for (title, action, key) in [("Undo", Selector(("undo:")), "z"), ("Cut", #selector(NSText.cut(_:)), "x"), ("Copy", #selector(NSText.copy(_:)), "c"), ("Paste", #selector(NSText.paste(_:)), "v"), ("Select All", #selector(NSText.selectAll(_:)), "a")] {
            edit.addItem(NSMenuItem(title: title, action: action, keyEquivalent: key))
        }
        item.submenu = edit; main.addItem(item)
        return main
    }
}

/// The fixture is never the active app, so another process's panel (Parzr's correction card) can take the system key window from it. A keystroke aimed at this process
/// puts the keyboard focus back on the text field first, as the active editor of a real session would have it.
final class FixtureApplication: NSApplication {
    var refocus: (() -> Void)?
    override func sendEvent(_ event: NSEvent) {
        if event.type == .keyDown || event.type == .keyUp, keyWindow == nil { refocus?() }
        super.sendEvent(event)
    }
}
let app = FixtureApplication.shared as! FixtureApplication
let delegate = Fixture(parent: parentPID, path: filePath)
app.delegate = delegate
app.setActivationPolicy(.accessory)
app.run()
