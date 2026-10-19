import Foundation
import NaturalLanguage

/// On-device redaction for wrong-suggestion reports. Nothing reaches the network until it has passed through here.
///
/// Links, email addresses (also "name at host dot com"), keys and tokens, phone numbers, every other number (any token
/// with a digit, and three or more number words in a row) and names are replaced by placeholders (`[link]`, `[email]`,
/// `[key]`, `[phone]`, `[number]`, `[name]`). It errs towards redacting too much: a capitalized word in the middle of a
/// sentence is treated as a name, and so are an `@handle`, a `#hashtag`, a word after a greeting, a word the English
/// lexicon knows only as a proper noun ("rahul"), and a word it does not know at all ("priya").
///
/// What it cannot find: names that are also ordinary words ("will", "rose") and not in the writer's known names, and
/// sensitive content written in ordinary words (health, money, relationships). `isClean` refuses a few health terms
/// outright; the rest of the text around a suggestion is sent as written.
public enum Redactor {
    public enum Kind: String, Sendable, CaseIterable, Comparable {
        // Declared in priority order: when two findings overlap, the earlier kind names the merged span.
        case email, link, key, phone, number, name
        public var placeholder: String { "[\(rawValue)]" }
        var priority: Int { Self.allCases.firstIndex(of: self)! }
        public static func < (a: Kind, b: Kind) -> Bool { a.priority < b.priority }
    }
    public struct Span: Equatable, Sendable {
        public let range: NSRange
        public let kind: Kind
        /// A guess that yields to the suggestion itself: a word the lexicon does not know is redacted elsewhere in the
        /// sentence, but kept when it is the word being corrected (a typo is what a spelling report is about).
        public let weak: Bool
        public init(_ range: NSRange, _ kind: Kind, weak: Bool = false) { self.range = range; self.kind = kind; self.weak = weak }
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
    /// "aman at gmail dot com", "aman (at) gmail (dot) com".
    static let spelledEmail = regex(#"[\p{L}\p{N}._%+\-]{1,64}\s{0,3}(?:\bat\b|\(at\)|\[at\])\s{0,3}[\p{L}\p{N}\-]{1,63}(?:\s{0,3}(?:\bdot\b|\(dot\)|\[dot\])\s{0,3}[\p{L}\p{N}\-]{1,63})+"#, [.caseInsensitive])
    /// "#rahulsharma": a hashtag can name a person. "#42" and "#A12" are numbers.
    static let hashtag = regex(#"(?<![\p{L}\p{N}_&#])#[\p{L}_]+(?![\p{L}\p{N}_\-])"#)
    /// Keys and tokens with a well-known prefix: Stripe, GitHub, Slack, GitLab, AWS, Google, OpenAI-style, JWTs.
    static let keyPrefix = regex(#"\b(?:(?:sk|pk|rk)_(?:live|test)_|sk-(?:proj-|ant-)?|gh[pousr]_|github_pat_|xox[abposr]-|glpat-|AKIA|ASIA|AIza|eyJ)[A-Za-z0-9_\-]{4,}"#, [.caseInsensitive])
    /// Any unbroken run of 20 or more key characters; `isKeyLike` decides.
    static let longToken = regex(#"(?<![A-Za-z0-9_+/=\-])[A-Za-z0-9_+/=\-]{20,}(?![A-Za-z0-9_+/=\-])"#)
    /// A long run that mixes digits, underscores or cases is a key, not a word ("internationalization" is a word).
    static func isKeyLike(_ token: String) -> Bool {
        token.contains(where: \.isNumber) || token.contains("_") || (token.contains(where: \.isLowercase) && token.dropFirst().contains(where: \.isUppercase))
    }
    static let numberWord = "(?:zero|oh|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|million|double|triple)"
    /// Three or more number words in a row: a PIN, a phone or account number read out ("four four two one").
    static let spelledNumbers = regex(#"\b"# + numberWord + #"(?:[\s,\-]{1,3}(?:and\s{1,3})?"# + numberWord + #"){2,}\b"#, [.caseInsensitive])
    /// Words that open a greeting or a message to someone: the word after one is a name unless it is a common word.
    static let greetings: Set<String> = ["hi", "hello", "hey", "heya", "hiya", "yo", "dear", "thanks", "thx", "ty", "cheers", "bye", "congrats", "congratulations", "welcome", "cc", "dm", "ping", "attn"]
    /// Words that follow a greeting without naming anyone.
    static let greetingFollowers: Set<String> = ["there", "all", "everyone", "everybody", "guys", "team", "folks", "again", "so", "and", "you", "yall", "y'all", "both", "friends", "friend", "sir", "madam", "maam", "ma'am", "mate", "dude", "buddy", "bud", "man", "boss", "babe", "baby", "love", "dear", "honey", "the", "a", "an", "my", "your", "for", "to", "back", "i", "we", "me", "it", "how", "what", "much", "lot", "very", "people", "world", "gang", "fam", "bro", "sis", "ladies", "gents", "gentlemen", "colleagues", "class", "sweetie", "darling", "just", "please", "but", "in", "on", "from", "with", "about", "now", "today", "tomorrow", "tonight", "here", "y", "u", "ya", "pal", "chief", "captain", "doc", "doctor", "prof", "professor", "mr", "mrs", "ms", "miss", "dr", "anyway", "though", "up", "out"]
    /// Reports that mention one of these are not sent at all: health content cannot be redacted word by word, and
    /// these few are too sensitive to risk. (Most sensitive content cannot be detected; the copy says so.)
    static let sensitiveTerms: Set<String> = ["hiv", "aids", "std", "stds", "sti", "stis", "herpes", "hepatitis", "cancer", "tumor", "tumour", "chemo", "chemotherapy", "biopsy", "diagnosis", "diagnosed", "pregnant", "pregnancy", "miscarriage", "abortion", "ivf", "depression", "depressed", "anxiety", "bipolar", "schizophrenia", "adhd", "autism", "autistic", "suicide", "suicidal", "self-harm", "overdose", "rehab", "addiction", "therapist", "therapy", "psychiatrist", "antidepressant", "antidepressants", "medication", "medications", "prescription", "dementia", "alzheimer's", "alzheimers", "epilepsy", "seizure", "seizures", "diabetes", "disability", "transgender", "hiv-positive"]
    private static let detector: NSDataDetector? = try? NSDataDetector(types: NSTextCheckingResult.CheckingType.link.rawValue | NSTextCheckingResult.CheckingType.phoneNumber.rawValue)
    /// Weekdays and months are not names, and the capitalization rules need them intact.
    static let calendarWords: Set<String> = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]
    /// Lowercase words that are also common first names ("will", "may", "mark"): a known name redacts them only when capitalized, so "I will go" survives a contact called Will.
    static let lowercaseWords = functionWords.union(nameWords)
    /// Function words and very common verbs: never a name, not even after a greeting ("hey can you").
    static let functionWords: Set<String> = [
        "a", "an", "the", "and", "or", "but", "if", "so", "to", "of", "in", "on", "at", "by", "for", "with", "from", "as", "is", "am", "are", "was", "were", "be", "been", "it", "its", "my", "me", "we", "us", "you", "he", "she", "they", "them", "his", "her", "our", "your", "their", "this", "that", "not", "no", "yes", "do", "did", "can", "will", "may", "might", "must", "shall", "should", "would", "could", "have", "has", "had", "go", "get", "got", "see", "say", "all", "any", "one", "new", "now", "out", "up", "down", "over", "just", "very", "here", "there", "when", "then", "than", "who", "what", "how", "why"
    ]
    /// Ordinary words that are also first names: after a greeting ("hi mark") they are names.
    static let nameWords: Set<String> = [
        "mark", "bill", "art", "rose", "grace", "hope", "faith", "joy", "sky", "rich", "frank", "jack", "bob", "sue", "pat", "don", "ken", "ray", "dawn", "eve", "iris", "lily", "ruby", "amber", "autumn", "summer", "winter", "max", "rob", "guy", "drew", "chase", "hunter", "cliff", "gene", "earl", "sandy", "rusty", "chip", "penny", "holly", "ivy", "jade", "pearl", "violet", "daisy", "heather", "angel", "baby", "honey", "sunny", "storm", "river", "brook", "glen", "dale", "wood", "page", "case", "major", "young", "king", "wade", "lane", "miles", "rex", "sterling", "carter", "mason", "cook", "baker", "smith", "price", "bell", "hall", "long", "short", "white", "black", "brown", "green", "gray", "grey", "golden", "love", "star", "else"
    ]
    /// Lowercase words English's lemma lexicon does not know but that name no one: chat shorthand and common tech words.
    static let commonUnknownWords: Set<String> = ["api", "apis", "doc", "docs", "aws", "jwt", "json", "yaml", "csv", "pdf", "pdfs", "url", "urls", "wifi", "ok", "okay", "lol", "btw", "imo", "imho", "fyi", "asap", "tbh", "idk", "thx", "pls", "plz", "gonna", "wanna", "gotta", "kinda", "sorta", "yeah", "yep", "nope", "hmm", "uh", "um", "ui", "ux", "app", "apps", "repo", "repos", "config", "env", "dev", "devs", "prod", "auth", "login", "signup", "admin", "inbox", "emoji", "emojis", "online", "offline", "website", "webpage", "email", "emails", "blog", "vlog", "podcast", "laptop", "smartphone", "selfie", "hashtag", "username", "password", "screenshot", "ebook", "e-mail", "faq"]

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
        add(spelledEmail, .email)
        add(schemeLink, .link, trimTrailing: true)
        add(bareDomain, .link, trimTrailing: true)
        add(keyPrefix, .key)
        for match in longToken.matches(in: text, range: all) where isKeyLike(ns.substring(with: match.range)) { found.append(Span(match.range, .key)) }
        add(handle, .name)
        add(hashtag, .name)
        add(phone, .phone)
        add(number, .number)
        add(spelledNumbers, .number)
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
                out[out.count - 1] = Span(NSRange(location: last.range.location, length: end - last.range.location), min(last.kind, span.kind), weak: last.weak && span.weak)
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
        return out + lexiconNameSpans(in: text)
    }
    /// Lowercase names, which capitals cannot reveal. English's lemma lexicon answers for each word: a lemma that is a
    /// proper noun ("rahul" to "Rahul", "jain" to "Jain") is a name; no lemma at all ("priya", "sharma", or a typo) is
    /// treated as one too, but weakly, so the word being corrected survives. The word after a greeting ("hi mark") is a
    /// name unless it is a common follower ("hi there", "thanks so much").
    static func lexiconNameSpans(in text: String) -> [Span] {
        let ns = text as NSString
        let tagger = NLTagger(tagSchemes: [.lemma, .lexicalClass])
        tagger.string = text
        tagger.setLanguage(.english, range: text.startIndex..<text.endIndex)
        var out: [Span] = []
        var previous: String?
        tagger.enumerateTags(in: text.startIndex..<text.endIndex, unit: .word, scheme: .lemma, options: [.omitWhitespace, .omitPunctuation, .omitOther]) { lemma, range in
            let token = String(text[range]), lower = token.lowercased(), span = NSRange(range, in: text)
            defer { previous = lower }
            let letters = token.filter(\.isLetter)
            // Placeholders ("[name]") and their insides, the word "I", contractions' tails ("'s"), acronyms and single letters stay.
            let inPlaceholder = span.location > 0 && ns.character(at: span.location - 1) == UInt16(UInt8(ascii: "[")) && placeholders.contains("[\(lower)]")
            guard !inPlaceholder, letters.count >= 2, letters.count == token.count || token.contains("-") || token.contains("'") || token.contains("’"),
                  !isFirstPerson(lower), !calendarWords.contains(lower), !(token.count <= 5 && token.allSatisfy { !$0.isLowercase }) else { return true }
            if let lemma = lemma?.rawValue, !lemma.isEmpty {
                // A proper-noun lemma for a word written in lowercase.
                if token == lower, lemma.first?.isUppercase == true, lemma.lowercased() == lower { out.append(Span(span, .name)); return true }
                if let previous, greetings.contains(previous), token == lower, !greetingFollowers.contains(lower), !functionWords.contains(lower) || nameWords.contains(lower) {
                    let (lexical, _) = tagger.tag(at: range.lowerBound, unit: .word, scheme: .lexicalClass)
                    if ![.determiner, .pronoun, .preposition, .adverb, .conjunction, .particle, .interjection, .number].contains(lexical) { out.append(Span(span, .name)) }
                }
                return true
            }
            // Unknown to the lexicon: a name, a typo, slang. Strong after a greeting, weak anywhere else.
            if commonUnknownWords.contains(lower) { return true }
            out.append(Span(span, .name, weak: !(previous.map(greetings.contains) ?? false)))
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
        var found = spans(in: sentence, names: names)
        // A word the lexicon does not know stays when it is the word being corrected (the typo a report is about), unless
        // the fix only re-cases it: re-casing an unknown word is how a lowercase name gets capitalized.
        let original = ns.substring(with: edit)
        if original.lowercased() != replacement.lowercased() {
            found.removeAll { $0.weak && NSIntersectionRange($0.range, edit).length > 0 }
        }
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
    static let placeholderPattern = regex(#"\[(?:email|link|key|phone|number|name)\]"#)
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
    /// True when `text` still holds something redaction removes, or a sensitive term no report may carry: a check run on
    /// every report before it is queued, and again on every report loaded from disk.
    public static func isClean(_ text: String) -> Bool {
        let stripped = placeholders.reduce(text) { $0.replacingOccurrences(of: $1, with: " ") }
        let ns = stripped as NSString, all = NSRange(location: 0, length: ns.length)
        guard [email, spelledEmail, schemeLink, bareDomain, keyPrefix, handle, hashtag, number, spelledNumbers].allSatisfy({ $0.firstMatch(in: stripped, range: all) == nil }) else { return false }
        guard !longToken.matches(in: stripped, range: all).contains(where: { isKeyLike(ns.substring(with: $0.range)) }) else { return false }
        return !mentionsSensitiveTerm(stripped)
    }
    static func mentionsSensitiveTerm(_ text: String) -> Bool {
        let ns = text as NSString
        return word.matches(in: text, range: NSRange(location: 0, length: ns.length)).contains { match in
            let token = ns.substring(with: match.range).lowercased().trimmingCharacters(in: CharacterSet(charactersIn: "-'’"))
            return sensitiveTerms.contains(token) || sensitiveTerms.contains(stripPossessive(token))
        }
    }
}
