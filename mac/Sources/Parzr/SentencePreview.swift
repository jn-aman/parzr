import Foundation
import SwiftUI
import NaturalLanguage
import ParzrCore

enum SentencePreview {
    static func edits(source: String, edits: [WritingEdit], focused: WritingEdit) -> [WritingEdit] {
        guard !source.isEmpty, (try? EditPlan.validate(edits, in: source)) != nil else { return [] }
        let offset = min(focused.start_utf16, max(0, source.utf16.count - 1))
        let tokenizer = NLTokenizer(unit: .sentence); tokenizer.string = source
        let range = NSRange(tokenizer.tokenRange(at: String.Index(utf16Offset: offset, in: source)), in: source)
        let contained = edits.filter { $0.start_utf16 >= range.location && $0.end_utf16 <= NSMaxRange(range) }
        return contained.filter { edit in EditPlan.related(to: edit, in: edits).allSatisfy { contained.contains($0) } }
    }
    static func sentenceRanges(in source: String, containing edits: [WritingEdit]) -> [NSRange] {
        guard !source.isEmpty, !edits.isEmpty else { return [] }
        let tokenizer = NLTokenizer(unit: .sentence); tokenizer.string = source
        let value = source as NSString
        var out: [NSRange] = []
        tokenizer.enumerateTokens(in: source.startIndex..<source.endIndex) { token, _ in
            let full = NSRange(token, in: source)
            guard edits.contains(where: { $0.end_utf16 > $0.start_utf16 ? $0.start_utf16 < NSMaxRange(full) && $0.end_utf16 > full.location : $0.start_utf16 >= full.location && $0.start_utf16 <= NSMaxRange(full) }) else { return true }
            var range = full
            while range.length > 0, let scalar = Unicode.Scalar(value.character(at: NSMaxRange(range) - 1)), CharacterSet.whitespacesAndNewlines.contains(scalar) { range.length -= 1 }
            if range.length > 0, !out.contains(range) { out.append(range) }
            return true
        }
        return out
    }
    static func text(source: String, edits: [WritingEdit], focused: WritingEdit) -> String {
        guard !source.isEmpty, let corrected = try? EditPlan.apply(edits, to: source) else { return "" }
        let offset = min(focused.start_utf16, max(0, source.utf16.count - 1))
        let tokenizer = NLTokenizer(unit: .sentence); tokenizer.string = source
        let token = tokenizer.tokenRange(at: String.Index(utf16Offset: offset, in: source))
        let range = NSRange(token, in: source)
        let begin = range.location + edits.filter { $0.end_utf16 <= range.location }.reduce(0) { $0 + $1.replacement.utf16.count - $1.range.length }
        let end = NSMaxRange(range) + edits.filter { $0.end_utf16 <= NSMaxRange(range) }.reduce(0) { $0 + $1.replacement.utf16.count - $1.range.length }
        let value = corrected as NSString
        guard begin >= 0, end >= begin, end <= value.length else { return corrected }
        return value.substring(with: NSRange(location: begin, length: end - begin)).trimmingCharacters(in: .whitespacesAndNewlines)
    }
    static func diff(source: String, edits: [WritingEdit], focused: WritingEdit, whole: Bool = false) -> AttributedString {
        guard !source.isEmpty, (try? EditPlan.validate(edits, in: source)) != nil else { return AttributedString(text(source: source, edits: edits, focused: focused)) }
        let offset = min(focused.start_utf16, max(0, source.utf16.count - 1))
        let tokenizer = NLTokenizer(unit: .sentence); tokenizer.string = source
        let token = whole ? NSRange(location: 0, length: source.utf16.count) : NSRange(tokenizer.tokenRange(at: String.Index(utf16Offset: offset, in: source)), in: source)
        var begin = token.location, end = NSMaxRange(token)
        let sorted = edits.sorted { $0.start_utf16 < $1.start_utf16 }
        let hits = sorted.filter { $0.range.length == 0 ? $0.start_utf16 >= token.location && $0.start_utf16 <= NSMaxRange(token) : $0.start_utf16 < NSMaxRange(token) && $0.end_utf16 > token.location }
        for edit in hits { begin = min(begin, edit.start_utf16); end = max(end, edit.end_utf16) }
        let group = EditPlan.related(to: focused, in: edits), value = source as NSString
        var out = AttributedString(), cursor = begin
        func wordy(_ i: Int) -> Bool { Unicode.Scalar(value.character(at: i)).map { CharacterSet.alphanumerics.contains($0) || $0 == "'" || $0 == "’" } ?? false }
        for (index, edit) in hits.enumerated() {
            // Show partial-word edits ("c" -> "C" inside "can") as whole words.
            let limit = index + 1 < hits.count ? hits[index + 1].start_utf16 : value.length
            var start = edit.start_utf16, stop = edit.end_utf16
            if !edit.original.isEmpty || !edit.replacement.allSatisfy(\.isWhitespace) {
                while start > cursor, wordy(start - 1) { start -= 1 }
                while stop < limit, wordy(stop) { stop += 1 }
            }
            let head = value.substring(with: NSRange(location: start, length: edit.start_utf16 - start)), tail = value.substring(with: NSRange(location: edit.end_utf16, length: stop - edit.end_utf16))
            let original = head + edit.original + tail, replacement = edit.replacement.isEmpty && head.isEmpty && tail.isEmpty ? "" : head + edit.replacement + tail
            out += AttributedString(value.substring(with: NSRange(location: cursor, length: start - cursor)))
            if !edit.original.isEmpty {
                var old = AttributedString(original.allSatisfy(\.isWhitespace) ? "␣" : original)
                old.strikethroughStyle = .single; old.foregroundColor = Color.textSecondary; out += old
            }
            if !edit.original.isEmpty, !replacement.isEmpty { out += AttributedString(" ") }
            if !replacement.isEmpty {
                var new = AttributedString("\u{200A}" + replacement + "\u{200A}")
                new.foregroundColor = Color.correctionInk; new.font = .system(size: 14, weight: .semibold); new.backgroundColor = Color.accentWash
                if group.contains(edit) { new.underlineStyle = .single }
                out += new
            }
            cursor = stop
        }
        out += AttributedString(value.substring(with: NSRange(location: cursor, length: end - cursor)))
        while let c = out.characters.first, c.isWhitespace { out.characters.removeFirst() }
        while let c = out.characters.last, c.isWhitespace { out.characters.removeLast() }
        return out
    }
}

struct SentenceDiffView: View {
    let source: String
    let edits: [WritingEdit]
    let focused: WritingEdit
    var note: String
    var whole = false
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            ScrollView {
                Text(SentencePreview.diff(source: source, edits: edits, focused: focused, whole: whole)).font(.system(size: 14)).foregroundStyle(Color.textPrimary).lineSpacing(4).frame(maxWidth: .infinity, alignment: .leading).textSelection(.enabled)
            }.accessibilityLabel("Corrected sentence preview")
            // The explanation names the word it belongs to, so a multi-fix sentence stays legible.
            HStack(alignment: .firstTextBaseline, spacing: 6) {
                Text("\(focused.originalLabel) → \(focused.replacementLabel)").font(.system(size: 10, weight: .semibold)).foregroundStyle(Color.correctionInk).lineLimit(1).fixedSize()
                Text(note).font(.system(size: 11)).foregroundStyle(Color.textSecondary).lineLimit(2).frame(maxWidth: .infinity, alignment: .leading).help(note)
            }
        }.padding(10).frame(maxWidth: .infinity, maxHeight: .infinity).background(Color.writingSurface, in: RoundedRectangle(cornerRadius: 9))
    }
}
