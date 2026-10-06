import Foundation

public enum RewriteMode: String, Codable, Sendable, CaseIterable, Identifiable {
    case fix, professional, friendly, concise, direct
    public var id: String { rawValue }
    public var title: String { rawValue.capitalized }
    public var symbol: String {
        switch self { case .fix: "checkmark.seal"; case .professional: "briefcase"; case .friendly: "face.smiling"; case .concise: "text.alignleft"; case .direct: "arrow.up.right" }
    }
    public var detail: String {
        switch self {
        case .fix: "Small fixes. Same voice."
        case .professional: "Clear, composed, considered."
        case .friendly: "A little warmer. Still you."
        case .concise: "Fewer words. Full meaning."
        case .direct: "Get straight to the point."
        }
    }
    /// A few words for the card header. Mirrors the engine's prompts (engine/src/model.rs), which every tone also runs through grammar again.
    public var summary: String {
        switch self {
        case .fix: "Grammar and spelling only"
        case .professional: "No slang or filler"
        case .friendly: "Warm and conversational"
        case .concise: "Fewer words, same meaning"
        case .direct: "No hedging or filler"
        }
    }
    /// The tooltip and VoiceOver hint: what the mode does to the selection.
    public var help: String {
        switch self {
        case .fix: "Grammar, spelling and punctuation only. Your wording is kept."
        case .professional: "Rewrites in professional English: slang and filler removed, meaning kept."
        case .friendly: "Rewrites in a friendly, conversational tone, meaning kept."
        case .concise: "Shortens the text by removing unnecessary words, all information kept."
        case .direct: "Removes hedging and filler so it gets to the point, meaning kept."
        }
    }
}

/// What the check card says when a finished check found nothing to change. `status` is an engine warning (for example context refinement being unavailable).
public struct EmptyCheck: Equatable, Sendable {
    public let title: String, detail: String, hint: String
    public let warning: Bool
    public init(mode: RewriteMode, status: String? = nil) {
        warning = status != nil
        title = mode == .fix ? (status == nil ? "Looks good" : "No changes found") : "Already reads well in \(mode.title)"
        detail = status ?? (mode == .fix ? "No grammar or spelling changes in this selection." : "No changes suggested.")
        hint = mode == .fix ? "Want it reworded? Pick a tone above." : "Try another tone above."
    }
}
public struct TextSpan: Codable, Sendable, Equatable {
    public var start_utf16: Int
    public var end_utf16: Int
    public init(_ range: NSRange) { start_utf16 = range.location; end_utf16 = range.location + range.length }
}
public struct WritingEdit: Codable, Sendable, Identifiable, Equatable {
    public let start_utf16: Int
    public let end_utf16: Int
    public let replacement: String
    public let original: String
    public let category: String
    public let rule_id: String
    public let explanation: String
    public let confidence: Float
    public let group_id: String?
    public var id: String { "\(start_utf16):\(end_utf16):\(rule_id)" }
    public var range: NSRange { NSRange(location: start_utf16, length: end_utf16 - start_utf16) }
    public init(start: Int, end: Int, replacement: String, original: String, category: String = "Grammar", ruleID: String = "test", explanation: String = "", confidence: Float = 1, groupID: String? = nil) {
        start_utf16 = start; end_utf16 = end; self.replacement = replacement; self.original = original
        self.category = category; rule_id = ruleID; self.explanation = explanation; self.confidence = confidence
        group_id = groupID
    }
}
public struct SourceMapping: Codable, Sendable {
    public let input_start_utf16: Int, input_end_utf16: Int, output_start_utf16: Int, output_end_utf16: Int
    public let changed: Bool
}
public struct RewriteResult: Codable, Sendable {
    public let version: String, text: String
    public let edits: [WritingEdit]
    public let source_map: [SourceMapping]
    public let elapsed_ms: Double
    public let protected_count: Int
    public let warnings: [String]?
    /// The same result with other edits: marks carried over typing keep the warnings and timing of the check they came from.
    public func replacingEdits(_ edits: [WritingEdit]) -> RewriteResult {
        RewriteResult(version: version, text: text, edits: edits, source_map: source_map, elapsed_ms: elapsed_ms, protected_count: protected_count, warnings: warnings)
    }
}
public struct TokenHint: Codable, Sendable {
    public let start_utf16: Int, end_utf16: Int
    public let pos: String, lemma: String
    public let name: Bool
    /// The system spell checker accepts the word as spelled, so the engine never respells it (older engines ignore the field).
    public let known: Bool
    public init(range: NSRange, pos: String, lemma: String, name: Bool, known: Bool = false) { start_utf16 = range.location; end_utf16 = range.location + range.length; self.pos = pos; self.lemma = lemma; self.name = name; self.known = known }
}
public struct EngineRequest: Codable, Sendable {
    public let text: String
    public let mode: RewriteMode
    public let dictionary: [String]
    /// Names the engine may only re-case, never respell or split. Case-insensitive.
    public let names: [String]
    public let capitalize_names: Bool
    public let dialect: String
    public let protected_ranges: [TextSpan]
    public let tokens: [TokenHint]
    public let sentence_start: Bool
    public let sentence_end: Bool
    public let deep: Bool
    /// Also run the on-device grammar model beside the rules (Fix mode only; the engine ignores it without the model).
    public let gec: Bool
    public init(text: String, mode: RewriteMode = .fix, dictionary: [String] = [], names: [String] = [], capitalizeNames: Bool = false, dialect: String = "american", protectedRanges: [TextSpan] = [], tokens: [TokenHint] = [], sentenceStart: Bool = true, sentenceEnd: Bool = true, deep: Bool = false, gec: Bool = false) {
        self.text = text; self.mode = mode; self.dictionary = dictionary; self.names = names; capitalize_names = capitalizeNames; self.dialect = dialect; protected_ranges = protectedRanges; self.tokens = tokens; sentence_start = sentenceStart
        self.deep = deep; self.gec = gec
        sentence_end = sentenceEnd
    }
}
public extension RewriteResult {
    /// Drops edits (and their linked partners) the caller rejects. `source` is the text the engine was given; `source_map` is not kept in step.
    func dropping(from source: String, where reject: (WritingEdit) -> Bool) -> RewriteResult {
        let gone = Set(edits.filter(reject).flatMap { EditPlan.related(to: $0, in: edits) }.map(\.id))
        guard !gone.isEmpty else { return self }
        let kept = edits.filter { !gone.contains($0.id) }
        return RewriteResult(version: version, text: (try? EditPlan.apply(kept, to: source)) ?? source, edits: kept, source_map: [], elapsed_ms: elapsed_ms, protected_count: protected_count, warnings: warnings)
    }
}
public enum ParzrError: LocalizedError, Sendable {
    case message(String)
    public var errorDescription: String? { switch self { case .message(let value): value } }
}

public enum EditPlan {
    public static func related(to edit: WritingEdit, in edits: [WritingEdit]) -> [WritingEdit] {
        guard let group = edit.group_id else { return [edit] }
        return edits.filter { $0.group_id == group }
    }
    public static func validate(_ edits: [WritingEdit], in text: String) throws {
        let groups = Dictionary(grouping: edits.filter { $0.group_id != nil }, by: { $0.group_id! })
        guard groups.values.allSatisfy({ $0.count == 2 }) else { throw ParzrError.message("Apply the linked parts of this correction together.") }
        var end = 0
        var previousStart: Int?
        for edit in edits {
            guard edit.start_utf16 >= end, edit.end_utf16 >= edit.start_utf16,
                  edit.end_utf16 <= text.utf16.count, previousStart != edit.start_utf16,
                  let range = Range(edit.range, in: text), String(text[range]) == edit.original else {
                throw ParzrError.message("This text changed. Select it again before applying.")
            }
            end = edit.end_utf16; previousStart = edit.start_utf16
        }
    }
    public static func apply(_ edits: [WritingEdit], to text: String) throws -> String {
        try validate(edits, in: text)
        let result = NSMutableString(string: text)
        for edit in edits.reversed() { result.replaceCharacters(in: edit.range, with: edit.replacement) }
        return result as String
    }
    /// Untouched runs retain all attributes; replacement text inherits only its host run.
    public static func apply(_ edits: [WritingEdit], to text: NSAttributedString) throws -> NSAttributedString {
        try validate(edits, in: text.string)
        let result = NSMutableAttributedString(attributedString: text)
        for edit in edits.reversed() {
            let index = min(edit.start_utf16, max(0, result.length - 1))
            let attributes = result.length > 0 ? result.attributes(at: index, effectiveRange: nil) : [:]
            result.replaceCharacters(in: edit.range, with: NSAttributedString(string: edit.replacement, attributes: attributes))
        }
        return result
    }
}
