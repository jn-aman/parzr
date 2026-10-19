import Foundation
import NaturalLanguage

/// The text a keyboard checks: the sentence being typed (and the one just finished), taken from
/// the text before the cursor (`textDocumentProxy.documentContextBeforeInput`).
///
/// `before == prefix + text + pending`: `pending` is the word still being typed, which is never
/// checked (half a word reads as a misspelling).
public struct SentenceContext: Equatable, Sendable {
    public let text: String
    public let pending: String
    /// The span starts a sentence (false when the host cut the context off mid-sentence).
    public let sentenceStart: Bool
    /// The span ends with sentence punctuation, so the engine may expect a finished sentence.
    public let sentenceEnd: Bool

    public init(text: String, pending: String = "", sentenceStart: Bool = true, sentenceEnd: Bool = false) {
        self.text = text; self.pending = pending; self.sentenceStart = sentenceStart; self.sentenceEnd = sentenceEnd
    }

    /// Hosts usually pass a few hundred characters; a span starting this far back at the very
    /// beginning of the context was probably cut off, not the start of a sentence.
    public static let truncatedContextLength = 400
    static let enders: Set<Character> = [".", "!", "?", "\u{2026}"]

    /// Nil when there is nothing worth checking (no letters before the cursor).
    public static func current(before: String?, sentences: Int = 2) -> SentenceContext? {
        guard var before, !before.isEmpty else { return nil }
        // Only the current paragraph.
        if let newline = before.lastIndex(where: \.isNewline) { before = String(before[before.index(after: newline)...]) }
        // The word being typed: letters right before the cursor with no space after them.
        var pending = ""
        if let last = before.last, last.isLetter || last.isNumber || last == "'" || last == "\u{2019}" {
            let start = before.lastIndex(where: { !($0.isLetter || $0.isNumber || $0 == "'" || $0 == "\u{2019}") }).map { before.index(after: $0) } ?? before.startIndex
            pending = String(before[start...])
            before = String(before[..<start])
        }
        guard before.contains(where: \.isLetter) else { return nil }
        let tokenizer = NLTokenizer(unit: .sentence)
        tokenizer.string = before
        var starts: [String.Index] = []
        tokenizer.enumerateTokens(in: before.startIndex..<before.endIndex) { range, _ in
            if before[range].contains(where: \.isLetter) { starts.append(range.lowerBound) }
            return true
        }
        guard let first = starts.suffix(max(1, sentences)).first else { return nil }
        let text = String(before[first...])
        let trimmed = text.trimmingCharacters(in: .whitespaces).trimmingCharacters(in: CharacterSet(charactersIn: "\"'\u{201D}\u{2019})"))
        let cutOff = first == before.startIndex && before.utf16.count >= truncatedContextLength
        return SentenceContext(text: text, pending: pending, sentenceStart: !cutOff, sentenceEnd: pending.isEmpty && trimmed.last.map(enders.contains) == true)
    }

    public func request(settings: KeyboardSettings) -> EngineRequest {
        EngineRequest(text: text, dictionary: settings.dictionary, names: settings.names, dialect: settings.dialect, sentenceStart: sentenceStart, sentenceEnd: sentenceEnd)
    }
}
