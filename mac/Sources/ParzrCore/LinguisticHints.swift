import Foundation
import NaturalLanguage

public enum WordShape {
    /// A lowercase letters-only token (inner apostrophes and hyphens allowed, possessive and outer quotes dropped), else nil.
    public static func shaped(_ raw: String) -> String? {
        var word = raw.trimmingCharacters(in: CharacterSet(charactersIn: "'\u{2019}-"))
        for suffix in ["'s", "\u{2019}s"] where word.hasSuffix(suffix) { word.removeLast(suffix.count) }
        guard word.count >= 2, word.utf8.count <= 128, word.contains(where: \.isLetter), word.allSatisfy({ $0.isLowercase || "'\u{2019}-".contains($0) }) else { return nil }
        return word
    }
}

/// The engine's linguistic hints (part of speech, lemma, names, words the system spell checker
/// accepts) from Apple's NaturalLanguage tagger. Shared by the Mac app and the iOS app and keyboard
/// (ios/project.yml compiles this file into ParzrKit).
public enum LinguisticHints {
    public static func hints(for text: String, known: Set<String> = []) -> [TokenHint] {
        // Per-call tagger; NLTagger mutable state never crosses worker boundaries.
        let tagger = NLTagger(tagSchemes: [.lexicalClass, .lemma, .nameType])
        tagger.string = text
        // Without a language, short texts get no tags and "aman jain" is detected as Indonesian.
        tagger.setLanguage(.english, range: text.startIndex..<text.endIndex)
        var hints: [TokenHint] = []
        tagger.enumerateTags(in: text.startIndex..<text.endIndex, unit: .word, scheme: .lexicalClass, options: [.omitWhitespace, .omitPunctuation]) { tag, range in
            let lemma = tagger.tag(at: range.lowerBound, unit: .word, scheme: .lemma).0?.rawValue ?? String(text[range]).lowercased()
            let name = tagger.tag(at: range.lowerBound, unit: .word, scheme: .nameType).0
            // A lower-case typo next to a name must not become a protected last name.
            let named = (name == .personalName || name == .placeName || name == .organizationName)
                && text[range].contains(where: \.isUppercase)
            let accepted = WordShape.shaped(String(text[range])).map(known.contains) ?? false
            hints.append(TokenHint(range: NSRange(range, in: text), pos: tag?.rawValue ?? "Other", lemma: lemma, name: named, known: accepted))
            return true
        }
        return mergePossessives(hints, in: text)
    }
    /// NLTagger splits "Aman's" into "Aman" and "'s"; fold the clitic into the name's range so the hint matches the engine's token.
    public static func mergePossessives(_ hints: [TokenHint], in text: String) -> [TokenHint] {
        let ns = text as NSString
        var out: [TokenHint] = []
        for hint in hints {
            if let last = out.last, last.name, last.end_utf16 == hint.start_utf16, hint.end_utf16 <= ns.length, ["'s", "\u{2019}s"].contains(ns.substring(with: NSRange(location: hint.start_utf16, length: hint.end_utf16 - hint.start_utf16))) {
                out[out.count - 1] = TokenHint(range: NSRange(location: last.start_utf16, length: hint.end_utf16 - last.start_utf16), pos: last.pos, lemma: last.lemma, name: true)
            } else { out.append(hint) }
        }
        return out
    }
}
