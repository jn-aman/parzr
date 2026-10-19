import Foundation

/// One correction the keyboard bar or the scratchpad offers: an engine edit, or two linked edits
/// that only make sense together (a moved word), shown as one.
public struct Suggestion: Identifiable, Equatable, Sendable {
    public let edits: [WritingEdit]
    public init(edits: [WritingEdit]) { precondition(!edits.isEmpty); self.edits = edits }
    public var id: String { edits.map(\.id).joined(separator: "|") }
    public var category: String { edits[0].category }
    public var explanation: String { edits[0].explanation }

    /// What the bar shows: the corrected word(s), or what is added or removed.
    public var title: String {
        if edits.count > 1 { return edits.map(\.replacement).filter { !$0.isEmpty }.joined(separator: " … ") }
        let edit = edits[0]
        let replacement = edit.replacement.trimmingCharacters(in: .whitespaces)
        let original = edit.original.trimmingCharacters(in: .whitespaces)
        if replacement.isEmpty { return "Remove “\(original.isEmpty ? edit.original : original)”" }
        if original.isEmpty { return "Add “\(replacement)”" }
        return replacement
    }

    /// "teh → the", for VoiceOver and the scratchpad list.
    public var detail: String {
        edits.map { "\($0.original.isEmpty ? "∅" : $0.original) → \($0.replacement.isEmpty ? "∅" : $0.replacement)" }.joined(separator: ", ")
    }

    /// The result's edits as suggestions (linked edits together), nearest the cursor first.
    public static func from(_ result: RewriteResult, limit: Int = .max) -> [Suggestion] {
        var seen = Set<String>()
        var out: [Suggestion] = []
        for edit in result.edits where !seen.contains(edit.id) {
            let related = EditPlan.related(to: edit, in: result.edits)
            related.forEach { seen.insert($0.id) }
            out.append(Suggestion(edits: related.sorted { $0.start_utf16 < $1.start_utf16 }))
        }
        return Array(out.sorted { $0.edits[0].start_utf16 > $1.edits[0].start_utf16 }.prefix(limit))
    }
}
