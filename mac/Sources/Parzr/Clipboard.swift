import AppKit
import ParzrCore

@MainActor
final class ClipboardTransaction {
    private struct StoredItem { let values: [(NSPasteboard.PasteboardType, Data)] }
    private var stored: [StoredItem] = []
    private var ownedChange: Int?
    /// Snapshots every pasteboard item so `restoreUnconditionally` can put the user's clipboard back.
    func save() throws {
        // Promised data can fail to materialize. Refuse rather than lose the clipboard.
        stored = try (NSPasteboard.general.pasteboardItems ?? []).map { item in
            let values = try item.types.map { type -> (NSPasteboard.PasteboardType, Data) in
                guard let data = item.data(forType: type) else { throw ParzrError.message("Your clipboard could not be saved safely. Copy the result manually.") }
                return (type, data)
            }
            return StoredItem(values: values)
        }
        guard stored.reduce(0, { $0 + $1.values.reduce(0, { $0 + $1.1.count }) }) <= 16_777_216 else { throw ParzrError.message("Your clipboard is too large to preserve safely. Copy the result manually.") }
    }
    func stage(_ string: String, attributed: NSAttributedString? = nil) throws {
        let board = NSPasteboard.general
        try save()
        let item = NSPasteboardItem(); item.setString(string, forType: .string)
        if let attributed, let rtf = try? attributed.data(from: NSRange(location: 0, length: attributed.length), documentAttributes: [.documentType: NSAttributedString.DocumentType.rtf]) { item.setData(rtf, forType: .rtf) }
        board.clearContents()
        guard board.writeObjects([item]) else { restoreUnconditionally(); throw ParzrError.message("macOS could not stage the paste.") }
        ownedChange = board.changeCount
    }
    func restore() {
        guard NSPasteboard.general.changeCount == ownedChange else { stored.removeAll(); ownedChange = nil; return }
        restoreUnconditionally()
    }
    func restoreUnconditionally() {
        let items = stored.map { entry in
            let item = NSPasteboardItem()
            for (type, data) in entry.values { item.setData(data, forType: type) }
            return item
        }
        let board = NSPasteboard.general; board.clearContents(); board.writeObjects(items)
        stored.removeAll(); ownedChange = nil
    }
    static func paste(to pid: pid_t) throws { try key(9, to: pid, failure: "macOS could not send the paste shortcut.") }
    private static func key(_ code: CGKeyCode, to pid: pid_t, failure: String) throws {
        guard let source = CGEventSource(stateID: .combinedSessionState),
              let down = CGEvent(keyboardEventSource: source, virtualKey: code, keyDown: true),
              let up = CGEvent(keyboardEventSource: source, virtualKey: code, keyDown: false) else { throw ParzrError.message(failure) }
        down.flags = .maskCommand; up.flags = .maskCommand
        down.postToPid(pid); up.postToPid(pid)
    }
    /// Copies the app's current selection with Cmd+C and returns it, or nil if the clipboard never changed.
    /// The user's clipboard is always restored. Canvas editors such as Google Docs expose no AX text.
    static func copySelection(from pid: pid_t) async throws -> String? {
        let transaction = ClipboardTransaction()
        try transaction.save()
        defer { transaction.restoreUnconditionally() }
        let board = NSPasteboard.general, before = board.changeCount
        try key(8, to: pid, failure: "macOS could not send the copy shortcut.")
        for _ in 0..<25 {
            try await Task.sleep(for: .milliseconds(20))
            if board.changeCount != before { return board.string(forType: .string) }
        }
        return nil
    }
}
