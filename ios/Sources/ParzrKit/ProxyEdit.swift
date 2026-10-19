import Foundation

/// How to apply engine edits through a keyboard's `textDocumentProxy`, which can only delete
/// backward from the cursor and insert at it: delete back to the first changed character, then
/// type the corrected text and whatever the user typed after the checked span.
public struct ProxyEdit: Equatable, Sendable {
    /// `deleteBackward()` calls; each removes one character (grapheme cluster).
    public let deleteCount: Int
    public let insert: String

    public init(deleteCount: Int, insert: String) { self.deleteCount = deleteCount; self.insert = insert }

    /// The longest run typed after a check that a suggestion still applies over.
    public static let maximumTail = 80

    /// The plan for applying `edits` (UTF-16 offsets into `checked`) when the text before the
    /// cursor is now `before`. Nil when `checked` is no longer there, the user typed past the
    /// paragraph, or the edits no longer fit the text.
    public static func plan(_ edits: [WritingEdit], checked: String, before: String) -> ProxyEdit? {
        guard !edits.isEmpty, !checked.isEmpty, let found = before.range(of: checked, options: .backwards) else { return nil }
        let tail = String(before[found.upperBound...])
        guard tail.utf16.count <= maximumTail, !tail.contains(where: \.isNewline) else { return nil }
        guard let corrected = try? EditPlan.apply(edits.sorted { $0.start_utf16 < $1.start_utf16 }, to: checked) else { return nil }
        // The first character that differs, on a grapheme boundary so a split emoji or accent
        // is retyped whole.
        let old = Array(checked.utf16), new = Array(corrected.utf16)
        var common = 0
        while common < min(old.count, new.count), old[common] == new[common] { common += 1 }
        func boundary(_ offset: Int, _ text: String) -> String.Index? { String.Index(utf16Offset: offset, in: text).samePosition(in: text) }
        while common > 0, boundary(common, checked) == nil || boundary(common, corrected) == nil { common -= 1 }
        guard let oldIndex = boundary(common, checked), let newIndex = boundary(common, corrected) else { return nil }
        let removed = String(checked[oldIndex...]) + tail
        return ProxyEdit(deleteCount: removed.count, insert: String(corrected[newIndex...]) + tail)
    }

    /// Replaces the whole checked span (a tone rewrite).
    public static func replacing(_ checked: String, with rewritten: String, before: String) -> ProxyEdit? {
        let ns = checked as NSString
        let edit = WritingEdit(start: 0, end: ns.length, replacement: rewritten, original: checked, category: "Tone", ruleID: "tone.rewrite")
        return plan([edit], checked: checked, before: before)
    }

    /// The text before the cursor after this plan runs, for tests and for checking the result.
    public func applied(to before: String) -> String {
        String(before.dropLast(deleteCount)) + insert
    }
}
