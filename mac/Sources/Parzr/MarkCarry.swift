import Foundation
import ParzrCore

/// Moves the marks of a passive check through one edit of the editor's text, so typing does not wipe them while the next check runs.
/// Pure: the caller reads the editor and redraws. Uses the Studio's `EditRemap.Change` for the changed span.
enum MarkCarry {
    struct Carried: Equatable {
        /// The checked paragraph in the new text.
        let selection: NSRange
        let inlineBreaks: [Int]
        /// Edits local to `selection`, as a fresh check of the new text would report them.
        let edits: [WritingEdit]
    }
    /// nil when nothing can be carried: the text is the same, or the change crosses the paragraph's start or end, or edits an inline image break.
    /// `edits` are local to `selection` in `old`; each one kept still reads its `original` in `new`.
    static func remap(edits: [WritingEdit], selection: NSRange, inlineBreaks: [Int] = [], from old: String, to new: String) -> Carried? {
        let change = EditRemap.Change(from: old, to: new)
        guard !change.unchanged else { return nil }
        let start = selection.location, end = NSMaxRange(selection)
        let moved: NSRange
        if change.start >= start, change.oldEnd <= end { moved = NSRange(location: start, length: selection.length + change.delta) }
        else if change.oldEnd <= start { moved = NSRange(location: start + change.delta, length: selection.length) }
        else if change.start >= end { moved = selection }
        else { return nil }
        let newText = new as NSString
        guard moved.length > 0, NSMaxRange(moved) <= newText.length else { return nil }
        var breaks: [Int] = []
        for index in inlineBreaks {
            if index < change.start { breaks.append(index) } else if index >= change.oldEnd { breaks.append(index + change.delta) } else { return nil }
        }
        let inserted = change.oldEnd == change.start && change.delta > 0 ? newText.substring(with: NSRange(location: change.start, length: change.delta)) : ""
        let carried: [WritingEdit] = edits.compactMap { edit in
            let global = WritingEdit(start: start + edit.start_utf16, end: start + edit.end_utf16, replacement: edit.replacement, original: edit.original, category: edit.category,
                                     ruleID: edit.rule_id, explanation: edit.explanation, confidence: edit.confidence, groupID: edit.group_id)
            guard let shifted = change.shift(global) ?? keptBesideSpace(global, change: change, inserted: inserted) else { return nil }
            let range = NSRange(location: shifted.start_utf16, length: shifted.end_utf16 - shifted.start_utf16)
            guard NSMaxRange(range) <= NSMaxRange(moved), range.location >= moved.location, newText.substring(with: range) == edit.original else { return nil }
            return WritingEdit(start: range.location - moved.location, end: NSMaxRange(range) - moved.location, replacement: edit.replacement, original: edit.original, category: edit.category,
                               ruleID: edit.rule_id, explanation: edit.explanation, confidence: edit.confidence, groupID: edit.group_id)
        }
        return Carried(selection: moved, inlineBreaks: breaks, edits: carried)
    }
    /// `EditRemap` drops an edit the change touches. Typing a space straight after a flagged word (or straight before it) leaves the word as it was, so its mark stays.
    private static func keptBesideSpace(_ edit: WritingEdit, change: EditRemap.Change, inserted: String) -> WritingEdit? {
        guard !inserted.isEmpty else { return nil }
        if edit.end_utf16 == change.start, inserted.first?.isWhitespace == true { return edit }
        if edit.start_utf16 == change.start, inserted.last?.isWhitespace == true {
            return WritingEdit(start: edit.start_utf16 + change.delta, end: edit.end_utf16 + change.delta, replacement: edit.replacement, original: edit.original, category: edit.category,
                               ruleID: edit.rule_id, explanation: edit.explanation, confidence: edit.confidence, groupID: edit.group_id)
        }
        return nil
    }
}
/// Which marks of a new check are new to the writer. Marks already on screen (carried over typing or from the last check) show at once;
/// new ones wait out the typing-speed delay (`TypingMonitor`).
enum MarkReveal {
    /// What identifies a mark across checks of the same text: where it sits in the document and what it would change.
    struct Key: Hashable {
        let start: Int, end: Int, replacement: String, rule: String
        init(_ edit: WritingEdit, at origin: Int) { start = origin + edit.start_utf16; end = origin + edit.end_utf16; replacement = edit.replacement; rule = edit.rule_id }
    }
    /// Ids of the `edits` (local to a paragraph at `origin`) that were not already on screen.
    static func fresh(_ edits: [WritingEdit], at origin: Int, visible: Set<Key>) -> Set<String> {
        Set(edits.filter { !visible.contains(Key($0, at: origin)) }.map(\.id))
    }
}

/// Where an underline goes inside an edit: only the words the fix changes ("a" in "a apple" → "an apple", the second "the" in
/// "the the"), so the stroke says what will change while the highlight shows the whole edit.
enum MarkSpan {
    /// The changed part of `original` (UTF-16, local to it), widened to whole words and without edge spaces; all of it when nothing narrower fits.
    static func changed(original: String, replacement: String) -> NSRange {
        let a = Array(original.utf16), b = Array(replacement.utf16), shared = min(a.count, b.count)
        guard !a.isEmpty else { return NSRange(location: 0, length: 0) }
        var prefix = 0, suffix = 0
        while prefix < shared, a[prefix] == b[prefix] { prefix += 1 }
        while suffix < shared - prefix, a[a.count - 1 - suffix] == b[b.count - 1 - suffix] { suffix += 1 }
        var start = prefix, end = a.count - suffix
        // A cut inside a word takes the whole word: "teh" → "the" underlines "teh", not "eh".
        while start > 0, start < a.count, isWord(a[start]), isWord(a[start - 1]) { start -= 1 }
        while end > 0, end < a.count, isWord(a[end - 1]), isWord(a[end]) { end += 1 }
        // A pure insertion ("a" → "an", a missing comma) marks the word it attaches to.
        if start == end {
            if start > 0 { start -= 1; while start > 0, isWord(a[start - 1]), isWord(a[start]) { start -= 1 } }
            else { end += 1; while end < a.count, isWord(a[end - 1]), isWord(a[end]) { end += 1 } }
        }
        while start < end, isSpace(a[start]) { start += 1 }
        while end > start, isSpace(a[end - 1]) { end -= 1 }
        return start < end ? NSRange(location: start, length: end - start) : NSRange(location: 0, length: a.count)
    }
    /// Text that can break across lines: it has a space or a line break in it.
    static func mayWrap(_ text: String) -> Bool { text.unicodeScalars.contains { CharacterSet.whitespacesAndNewlines.contains($0) } }
    private static func isSpace(_ unit: UInt16) -> Bool { Unicode.Scalar(unit).map { CharacterSet.whitespacesAndNewlines.contains($0) } ?? false }
    private static func isWord(_ unit: UInt16) -> Bool {
        guard let scalar = Unicode.Scalar(unit) else { return true } // half of a surrogate pair: an emoji or a rare letter
        return CharacterSet.alphanumerics.contains(scalar) || scalar == "'" || scalar == "\u{2019}" || scalar == "-"
    }
}
