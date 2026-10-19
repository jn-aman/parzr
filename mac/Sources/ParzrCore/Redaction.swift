import Foundation
import NaturalLanguage

/// On-device redaction for wrong-suggestion reports. Nothing reaches the network until it has passed through here.
///
/// Links, email addresses, phone numbers, every other number (any token with a digit) and names are replaced by
/// placeholders (`[link]`, `[email]`, `[phone]`, `[number]`, `[name]`). It errs towards redacting too much: a capitalized
/// word in the middle of a sentence is treated as a name, and so is an `@handle`.
public enum Redactor {
    public enum Kind: String, Sendable, CaseIterable, Comparable {
        // Declared in priority order: when two findings overlap, the earlier kind names the merged span.
        case email, link, phone, number, name
        public var placeholder: String { "[\(rawValue)]" }
        var priority: Int { Self.allCases.firstIndex(of: self)! }
        public static func < (a: Kind, b: Kind) -> Bool { a.priority < b.priority }
    }
    public struct Span: Equatable, Sendable {
        public let range: NSRange
        public let kind: Kind
        public init(_ range: NSRange, _ kind: Kind) { self.range = range; self.kind = kind }
    }
    /// The placeholders, so a report can be checked for them (and the server can tell redaction from raw text).
    public static let placeholders = Set(Kind.allCases.map(\.placeholder))

    // MARK: Detectors

    private static func regex(_ pattern: String, _ options: NSRegularExpression.Options = []) -> NSRegularExpression {
        // The patterns are constants; a typo is a programming error caught by the tests.
        try! NSRegularExpression(pattern: pattern, options: options)
    }
    static let email = regex(#"[\p{L}\p{N}._%+\-]+@[\p{L}\p{N}\-]+(?:\.[\p{L}\p{N}\-]+)+"#)
    /// Anything with a scheme (https://, ftp://, slack://), mailto: and www.
    static let schemeLink = regex(#"(?:\b[A-Za-z][A-Za-z0-9+.\-]{1,20}://|\bwww\.|\bmailto:)[^\s<>"'`]+"#, [.caseInsensitive])
    /// Bare domains ("parzr.app", "docs.google.com/x"). The top-level domain must be lowercase and from a list, so a
    /// missing space after a full stop ("home.So tired") is not taken for a link.
    static let bareDomain = regex(#"(?<![\p{L}\p{N}@.\-])(?:[\p{L}\p{N}](?:[\p{L}\p{N}\-]{0,61}[\p{L}\p{N}])?\.)+(?:com|org|net|edu|gov|mil|int|io|ai|app|dev|info|biz|xyz|ly|gg|tv|fm|uk|de|fr|ca|au|nz|jp|cn|ru|br|es|nl|se|no|fi|dk|pl|ch|at|eu|sh|page|site|online|tech|cloud|link|news|blog|shop|store|art|club|live|today|zone|wiki|email|pro|cc|ws)(?![\p{L}\p{N}\-])(?:[/?#:][^\s<>"'`]*)?"#)
    /// "@aman", "@team.alpha": a handle names a person or a group.
    static let handle = regex(#"(?<![\p{L}\p{N}_@.])@[\p{L}\p{N}_][\p{L}\p{N}_.\-]*"#)
    /// Seven or more digits written as a phone number: "+1 (415) 555-0100", "98765 43210".
    static let phone = regex(#"(?<![\p{L}\p{N}])\+?\(?\p{N}[\p{N}\s().\-]{5,}\p{N}(?![\p{L}\p{N}])"#)
    /// Any token holding a digit, with its separators: "42", "3.5", "1,200", "10:30", "2026-10-19", "4th", "B12", "v2".
    static let number = regex(#"[\p{L}\p{N}_]*\p{N}[\p{L}\p{N}_]*(?:[.,:/\-][\p{L}\p{N}_]*\p{N}[\p{L}\p{N}_]*)*"#)
    static let word = regex(#"\p{L}[\p{L}\p{M}'’\-]*"#)
    private static let detector: NSDataDetector? = try? NSDataDetector(types: NSTextCheckingResult.CheckingType.link.rawValue | NSTextCheckingResult.CheckingType.phoneNumber.rawValue)
    /// Weekdays and months are not names, and the capitalization rules need them intact.
    static let calendarWords: Set<String> = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]
    /// Lowercase words that are also common first names ("will", "may", "mark"): a known name redacts them only when capitalized, so "I will go" survives a contact called Will.
    static let lowercaseWords: Set<String> = [
        "a", "an", "the", "and", "or", "but", "if", "so", "to", "of", "in", "on", "at", "by", "for", "with", "from", "as", "is", "am", "are", "was", "were", "be", "been", "it", "its", "my", "me", "we", "us", "you", "he", "she", "they", "them", "his", "her", "our", "your", "their", "this", "that", "not", "no", "yes", "do", "did", "can", "will", "may", "might", "must", "shall", "should", "would", "could", "have", "has", "had", "go", "get", "got", "see", "say", "all", "any", "one", "new", "now", "out", "up", "down", "over", "just", "very", "here", "there", "when", "then", "than", "who", "what", "how", "why",
        "mark", "bill", "art", "rose", "grace", "hope", "faith", "joy", "sky", "rich", "frank", "jack", "bob", "sue", "pat", "don", "ken", "ray", "dawn", "eve", "iris", "lily", "ruby", "amber", "autumn", "summer", "winter", "max", "rob", "guy", "drew", "chase", "hunter", "cliff", "gene", "earl", "sandy", "rusty", "chip", "penny", "holly", "ivy", "jade", "pearl", "violet", "daisy", "heather", "angel", "baby", "honey", "sunny", "storm", "river", "brook", "glen", "dale", "wood", "page", "case", "major", "young", "king", "wade", "lane", "miles", "rex", "sterling", "carter", "mason", "cook", "baker", "smith", "price", "bell", "hall", "long", "short", "white", "black", "brown", "green", "gray", "grey", "golden", "love", "star", "else"
    ]

    /// Words that open a sentence before a name, which Apple's tagger reads as part of it.
    static let openers: Set<String> = ["hi", "hello", "hey", "dear", "call", "ask", "tell", "thanks", "thank", "email", "mail", "text", "message", "ping", "meet", "see", "cc", "welcome", "congrats", "congratulations", "sorry", "please", "and", "but", "so", "yes", "no", "ok", "okay", "good", "morning", "evening", "bye", "cheers", "regards", "with", "from", "to", "for", "via", "team", "folks", "all", "dm", "invite", "remind", "send", "loop", "update", "fyi", "re", "attn", "per", "like", "when", "if", "after", "before", "then", "also", "maybe", "let", "tag", "add", "only"]

    // MARK: Finding

    /// Sensitive spans in `text`, sorted and non-overlapping. `names` are known names (the writer's own, learned names, Contacts).
    public static func spans(in text: String, names: [String] = []) -> [Span] {
        guard !text.isEmpty else { return [] }
        let ns = text as NSString, all = NSRange(location: 0, length: ns.length)
        var found: [Span] = []
        func add(_ re: NSRegularExpression, _ kind: Kind, trimTrailing: Bool = false) {
            for match in re.matches(in: text, range: all) {
                var range = match.range
                if trimTrailing { range = trimmed(range, in: ns) }
                if range.length > 0 { found.append(Span(range, kind)) }
            }
        }
        add(email, .email)
        add(schemeLink, .link, trimTrailing: true)
        add(bareDomain, .link, trimTrailing: true)
        add(handle, .name)
        add(phone, .phone)
        add(number, .number)
        if let detector {
            for match in detector.matches(in: text, range: all) {
                let kind: Kind = match.resultType == .phoneNumber ? .phone : match.url?.scheme?.lowercased() == "mailto" ? .email : .link
                found.append(Span(trimmed(match.range, in: ns), kind))
            }
        }
        found += nameSpans(in: text, names: names)
        return merge(found)
    }
    /// Trailing sentence punctuation is not part of a link: "see parzr.app." keeps its full stop.
    private static func trimmed(_ range: NSRange, in ns: NSString) -> NSRange {
        var range = range
        let trailing = CharacterSet(charactersIn: ".,;:!?)]}'\"’”")
        while range.length > 0, let scalar = Unicode.Scalar(ns.character(at: NSMaxRange(range) - 1)), trailing.contains(scalar) { range.length -= 1 }
        return range
    }
    /// Overlapping findings become one span (their union) named by the highest-priority kind.
    static func merge(_ spans: [Span]) -> [Span] {
        let sorted = spans.filter { $0.range.length > 0 }.sorted { $0.range.location != $1.range.location ? $0.range.location < $1.range.location : $0.range.length > $1.range.length }
        var out: [Span] = []
        for span in sorted {
            if let last = out.last, span.range.location < NSMaxRange(last.range) {
                let end = max(NSMaxRange(last.range), NSMaxRange(span.range))
                out[out.count - 1] = Span(NSRange(location: last.range.location, length: end - last.range.location), min(last.kind, span.kind))
            } else { out.append(span) }
        }
        return out
    }
    /// Known names (any capitalization, except common words, which only count capitalized), names Apple's tagger finds,
    /// and capitalized words in the middle of a sentence.
    static func nameSpans(in text: String, names: [String]) -> [Span] {
        let ns = text as NSString, all = NSRange(location: 0, length: ns.length)
        let known = Set(names.flatMap { $0.split { !$0.isLetter && $0 != "'" && $0 != "’" } }.map { stripPossessive(String($0)).lowercased() }.filter { $0.count >= 2 })
        var out: [Span] = []
        for match in word.matches(in: text, range: all) {
            let token = ns.substring(with: match.range)
            let bare = stripPossessive(token.trimmingCharacters(in: CharacterSet(charactersIn: "-'’")))
            let lower = bare.lowercased()
            guard bare.count >= 2, !isFirstPerson(lower) else { continue }
            let capitalized = bare.first?.isUppercase == true
            let allCaps = bare.allSatisfy { !$0.isLowercase }
            if known.contains(lower), capitalized || !lowercaseWords.contains(lower) { out.append(Span(match.range, .name)); continue }
            if capitalized, !allCaps, !calendarWords.contains(lower), !startsSentence(at: match.range.location, in: ns) { out.append(Span(match.range, .name)) }
        }
        // Apple's tagger catches names at the start of a sentence, where capitals say nothing.
        let tagger = NLTagger(tagSchemes: [.nameType])
        tagger.string = text
        tagger.setLanguage(.english, range: text.startIndex..<text.endIndex)
        tagger.enumerateTags(in: text.startIndex..<text.endIndex, unit: .word, scheme: .nameType, options: [.omitWhitespace, .omitPunctuation]) { tag, range in
            guard let tag, [.personalName, .organizationName, .placeName].contains(tag) else { return true }
            let token = String(text[range]), lower = token.lowercased(), span = NSRange(range, in: text)
            // The tagger folds the word before a name into it ("Hi Rahul", "Call Rahul"); a greeting or verb that opens the sentence stays.
            if startsSentence(at: span.location, in: ns), openers.contains(lower) { return true }
            // "OK", "US": short all-caps words are abbreviations far more often than names.
            if token.count <= 3, token.allSatisfy({ !$0.isLowercase }) { return true }
            if token.contains(where: \.isUppercase), !calendarWords.contains(lower), !isFirstPerson(lower) { out.append(Span(span, .name)) }
            return true
        }
        return out
    }
    private static func isFirstPerson(_ lower: String) -> Bool { ["i", "i'm", "i’m", "i'll", "i’ll", "i've", "i’ve", "i'd", "i’d"].contains(lower) }
    static func stripPossessive(_ word: String) -> String {
        var word = word
        for suffix in ["'s", "’s"] where word.lowercased().hasSuffix(suffix) && word.count > 2 { word.removeLast(suffix.count) }
        return word
    }
    /// The first word of the text, of a line, of a sentence, or of a quotation.
    static func startsSentence(at location: Int, in ns: NSString) -> Bool {
        var i = location - 1
        while i >= 0 {
            guard let scalar = Unicode.Scalar(ns.character(at: i)) else { return false }
            if CharacterSet.newlines.contains(scalar) { return true }
            if CharacterSet.whitespaces.contains(scalar) { i -= 1; continue }
            return ".!?:…\"“‘'([{•*-–—>".unicodeScalars.contains(scalar)
        }
        return true
    }

    // MARK: Redacting

    /// `text` with every sensitive span replaced by its placeholder.
    public static func redact(_ text: String, names: [String] = []) -> String { apply(spans(in: text, names: names), to: text) }
    static func apply(_ spans: [Span], to text: String) -> String {
        let out = NSMutableString(string: text)
        for span in spans.reversed() { out.replaceCharacters(in: span.range, with: span.kind.placeholder) }
        return out as String
    }

    /// One suggestion, redacted together with its sentence: the edit's offsets point into the redacted sentence, and a
    /// suggestion that touches a redacted span covers the whole placeholder (so no half of a number or name survives).
    public struct Suggestion: Equatable, Sendable {
        public let sentence: String
        public let start: Int, end: Int
        public let original: String, replacement: String
    }
    /// `edit` is a UTF-16 range of `sentence`; `replacement` is what the suggestion puts there.
    public static func redact(sentence: String, edit: NSRange, replacement: String, names: [String] = []) -> Suggestion? {
        let ns = sentence as NSString
        guard edit.location >= 0, NSMaxRange(edit) <= ns.length else { return nil }
        let found = spans(in: sentence, names: names)
        // Grow the edit over every span it touches.
        var (a, b) = (edit.location, NSMaxRange(edit))
        var touchesName = false
        for span in found {
            let (s, e) = (span.range.location, NSMaxRange(span.range))
            let hit = edit.length > 0 ? s < NSMaxRange(edit) && e > edit.location : s < edit.location && e > edit.location
            guard hit else { continue }
            a = min(a, s); b = max(b, e)
            if span.kind == .name { touchesName = true }
        }
        let grown = ns.substring(with: NSRange(location: a, length: edit.location - a)) + replacement + ns.substring(with: NSRange(location: NSMaxRange(edit), length: b - NSMaxRange(edit)))
        let out = apply(found, to: sentence)
        // [a, b) lies on span edges, so it maps by the length change of the spans before each end.
        let (start, end) = (mapped(a, spans: found), mapped(b, spans: found))
        let redactedOriginal = (out as NSString).substring(with: NSRange(location: start, length: end - start))
        // The replacement is redacted with every name the sentence revealed; when it rewrites a name, any capitalized or
        // name-like word in it is a name too ("Jhon" to "John").
        let sentenceNames = found.filter { $0.kind == .name }.map { ns.substring(with: $0.range) }
        var redactedReplacement = redact(grown, names: names + sentenceNames)
        if touchesName { redactedReplacement = redactNameLike(redactedReplacement, near: sentenceNames) }
        return Suggestion(sentence: out, start: start, end: end, original: redactedOriginal, replacement: redactedReplacement)
    }
    /// Where a position of the source lands in the redacted text. Positions inside a span never occur (the edit was grown to span edges).
    private static func mapped(_ position: Int, spans: [Span]) -> Int {
        var shift = 0
        for span in spans where NSMaxRange(span.range) <= position { shift += span.kind.placeholder.utf16.count - span.range.length }
        return position + shift
    }
    static func redactNameLike(_ text: String, near names: [String]) -> String {
        let ns = text as NSString, all = NSRange(location: 0, length: ns.length)
        let targets = names.map { stripPossessive($0).lowercased() }
        let kept = placeholderPattern.matches(in: text, range: all).map(\.range)
        let out = NSMutableString(string: text)
        for match in word.matches(in: text, range: all).reversed() where !kept.contains(where: { NSIntersectionRange($0, match.range).length > 0 }) {
            let token = ns.substring(with: match.range), lower = stripPossessive(token).lowercased()
            if isFirstPerson(lower) || token.count < 2 { continue }
            if token.first?.isUppercase == true || targets.contains(where: { distance($0, lower) <= 2 }) { out.replaceCharacters(in: match.range, with: Kind.name.placeholder) }
        }
        return out as String
    }
    static let placeholderPattern = regex(#"\[(?:email|link|phone|number|name)\]"#)
    static func distance(_ a: String, _ b: String) -> Int {
        let (a, b) = (Array(a), Array(b))
        if a.isEmpty || b.isEmpty { return max(a.count, b.count) }
        var row = Array(0...b.count)
        for i in a.indices {
            var diagonal = row[0]; row[0] = i + 1
            for j in b.indices { let up = row[j + 1]; row[j + 1] = min(row[j + 1] + 1, row[j] + 1, diagonal + (a[i] == b[j] ? 0 : 1)); diagonal = up }
        }
        return row[b.count]
    }
    /// True when `text` still holds something redaction removes: a check run on every report before it is queued.
    public static func isClean(_ text: String) -> Bool {
        let stripped = placeholders.reduce(text) { $0.replacingOccurrences(of: $1, with: " ") }
        let ns = stripped as NSString, all = NSRange(location: 0, length: ns.length)
        return [email, schemeLink, bareDomain, number].allSatisfy { $0.firstMatch(in: stripped, range: all) == nil }
    }
}
