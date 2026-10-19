import Foundation
#if canImport(UIKit)
import UIKit

/// The system spell checker (UITextChecker): the words it accepts feed the engine's `known`
/// hints (as on the Mac), and its corrections are the keyboard's light checker when the engine
/// does not fit the keyboard's memory. UITextChecker belongs to the main actor; it takes
/// microseconds per word.
@MainActor
public enum SystemSpelling {
    public nonisolated static let language = "en_US"

    /// `knownWords(in:)` from any thread (the engine's queue): hops to the main thread.
    public nonisolated static func knownWordsFromAnyThread(in text: String) -> Set<String> {
        if Thread.isMainThread { return MainActor.assumeIsolated { knownWords(in: text) } }
        return DispatchQueue.main.sync { MainActor.assumeIsolated { knownWords(in: text) } }
    }

    /// Lowercase words in `text` the system spell checker accepts.
    public static func knownWords(in text: String) -> Set<String> {
        let checker = UITextChecker()
        var known = Set<String>()
        let ns = text as NSString
        ns.enumerateSubstrings(in: NSRange(location: 0, length: ns.length), options: .byWords) { word, _, _, _ in
            guard let word, let shaped = WordShape.shaped(word), !known.contains(shaped) else { return }
            let length = (shaped as NSString).length
            if checker.rangeOfMisspelledWord(in: shaped, range: NSRange(location: 0, length: length), startingAt: 0, wrap: false, language: language).location == NSNotFound {
                known.insert(shaped)
            }
        }
        return known
    }

    /// Spelling corrections from the system checker, as engine edits. Capitalized words after
    /// the first are left alone (names), as are words in `dictionary`.
    public static func edits(in text: String, dictionary: [String] = []) -> RewriteResult {
        let checker = UITextChecker()
        let ns = text as NSString
        let allowed = Set(dictionary.map { $0.lowercased() })
        var edits: [WritingEdit] = []
        var offset = 0
        while offset < ns.length {
            let range = checker.rangeOfMisspelledWord(in: text, range: NSRange(location: 0, length: ns.length), startingAt: offset, wrap: false, language: language)
            guard range.location != NSNotFound, range.length > 0 else { break }
            offset = range.location + range.length
            let word = ns.substring(with: range)
            if allowed.contains(word.lowercased()) { continue }
            if range.location > 0, word.first?.isUppercase == true { continue }
            guard let guess = checker.guesses(forWordRange: range, in: text, language: language)?.first, guess != word else { continue }
            edits.append(WritingEdit(start: range.location, end: range.location + range.length, replacement: guess, original: word, category: "Spelling", ruleID: "system.spelling", explanation: "Spelling suggested by iOS.", confidence: 0.6))
        }
        let corrected = (try? EditPlan.apply(edits, to: text)) ?? text
        return RewriteResult(version: "system-spelling", text: corrected, edits: edits, source_map: [], elapsed_ms: 0, protected_count: 0, warnings: nil)
    }
}
#endif
