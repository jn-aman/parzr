import Foundation
import ParzrCore

/// A kind of suggestion the user ignored often enough that Parzr stopped showing it. Settings, Learning lists these and can bring them back.
struct MutedSuggestion: Codable, Equatable, Identifiable {
    /// `SuggestionMutes.key(for:)` of the edits it hides.
    let key: String
    let category: String
    let explanation: String
    /// The last suggestion ignored before muting, as "original → replacement" (at most a few words), so the user can recognise it.
    let example: String
    /// Days since 1970 when it was muted.
    let day: Int
    var id: String { key }
}

/// Ignores counted per suggestion kind, and the kinds muted after `ignoresToMute` of them. Rule ids and counts only, plus one short example per muted kind.
/// Spelling flags are not muted here: an ignored spelling teaches the word instead (`Preferences.noteIgnored`).
struct SuggestionMutes: Codable, Equatable {
    static let ignoresToMute = 3, capacity = 500, maxMuted = 200
    private(set) var counts: [String: Int] = [:]
    private(set) var muted: [MutedSuggestion] = []
    /// Rules that judge a word (a model's edit, a name's or product's capital) are muted for that word only ("jira → Jira"); every other rule is muted as a whole ("grammar.sentence_capitalization").
    nonisolated static func wordScoped(_ rule: String) -> Bool {
        rule.split(separator: "+").contains { part in
            ["gector", "context.", "names.", "local-model"].contains { part.hasPrefix($0) } || part.contains("proper_noun") || part.contains("calendar_capitalization")
        }
    }
    /// What an Ignore of `edit` counts toward; nil for spelling flags, tone rewrites and empty rule ids.
    nonisolated static func key(for edit: WritingEdit) -> String? {
        guard edit.category != "Spelling", edit.category != "Tone", !edit.rule_id.isEmpty, edit.rule_id != "local-model" else { return nil }
        guard wordScoped(edit.rule_id) else { return edit.rule_id }
        let pair = "\(edit.original.lowercased())→\(edit.replacement.lowercased())".trimmingCharacters(in: .whitespacesAndNewlines)
        return "\(edit.rule_id):\(pair.prefix(48))"
    }
    nonisolated static func example(_ edit: WritingEdit) -> String {
        func clip(_ s: String) -> String { s.count > 24 ? String(s.prefix(23)) + "…" : s }
        return "\(clip(edit.originalLabel)) → \(clip(edit.replacementLabel))"
    }
    func mutes(_ edit: WritingEdit) -> Bool {
        guard !muted.isEmpty, let key = Self.key(for: edit) else { return false }
        return muted.contains { $0.key == key }
    }
    /// Counts one Ignore; returns the suggestion kind when this Ignore mutes it.
    @discardableResult
    mutating func ignored(_ edit: WritingEdit, day: Int) -> MutedSuggestion? {
        guard let key = Self.key(for: edit), !muted.contains(where: { $0.key == key }) else { return nil }
        guard counts[key] != nil || counts.count < Self.capacity else { return nil }
        let count = (counts[key] ?? 0) + 1
        guard count >= Self.ignoresToMute, muted.count < Self.maxMuted else { counts[key] = count; return nil }
        counts[key] = nil
        let mute = MutedSuggestion(key: key, category: edit.category, explanation: edit.explanation, example: Self.example(edit), day: day)
        muted.append(mute)
        return mute
    }
    /// The user applied a suggestion of this kind: its Ignores start over.
    mutating func applied(_ edit: WritingEdit) { if let key = Self.key(for: edit), counts[key] != nil { counts[key] = nil } }
    mutating func unmute(_ key: String) { muted.removeAll { $0.key == key } }
    mutating func reset() { counts = [:]; muted = [] }
}

/// Words Parzr learned to leave alone: jargon, acronyms and product names ("gector", "K8s", "pgvector"). Kept exactly as typed (sent as dictionary words, never re-cased like names).
enum LearnedWord {
    static let maxWords = 1000
    /// One token of letters, digits, apostrophes, hyphens, dots, underscores or plus signs (2 to 64 characters, a letter among them); nil for anything else.
    nonisolated static func token(_ raw: String) -> String? {
        var word = raw.trimmingCharacters(in: .whitespacesAndNewlines.union(CharacterSet(charactersIn: "\"“”‘’()[]{}<>,;:!?")))
        for suffix in ["'s", "\u{2019}s"] where word.hasSuffix(suffix) && word.count > suffix.count + 1 { word.removeLast(suffix.count) }
        while let last = word.last, ".-".contains(last) { word.removeLast() }
        guard (2...64).contains(word.count), word.utf8.count <= 128, word.contains(where: \.isLetter),
              word.allSatisfy({ $0.isLetter || $0.isNumber || "'\u{2019}-._+".contains($0) }) else { return nil }
        return word
    }
    /// Learned as a name (re-cased, shared as a name) when it is written with a capital and is letters only; otherwise as a word kept as typed.
    nonisolated static func isNameShaped(_ word: String) -> Bool {
        word.first?.isUppercase == true && WritingEdit.nameToken(word) != nil
    }
}

/// A private tally of the fixes the user applied, per day: categories and single-word spelling slips, never sentences or where they were written.
/// Kept on this Mac (in Parzr's preferences) for the last four weeks, shown only in Settings, Learning.
struct WritingStats: Codable, Equatable {
    struct Day: Codable, Equatable {
        var fixes: [String: Int] = [:]
        var slips: [String: Int] = [:]
        var ignored = 0
    }
    static let keepDays = 28, slipsPerDay = 60
    private(set) var days: [Int: Day] = [:]
    var isEmpty: Bool { days.isEmpty }
    /// The summary's groups: the engine's finer categories folded into five.
    nonisolated static func group(_ category: String) -> String {
        switch category {
        case "Spelling": "Spelling"
        case "Punctuation": "Punctuation"
        case "Capitalization": "Capitalization"
        case "Style", "Clarity", "Tone", "Wording": "Style"
        default: "Grammar"
        }
    }
    /// "recieved → received" for a single-word spelling fix (letters only, at most 32 each), else nil.
    nonisolated static func slip(_ edit: WritingEdit) -> String? {
        let (a, b) = (edit.original.lowercased(), edit.replacement.lowercased())
        guard edit.category == "Spelling", a != b, (2...32).contains(a.count), (1...32).contains(b.count),
              a.allSatisfy({ $0.isLetter || "'\u{2019}".contains($0) }), b.allSatisfy({ $0.isLetter || "'\u{2019}".contains($0) }) else { return nil }
        return "\(a) → \(b)"
    }
    mutating func recordFixes(_ edits: [WritingEdit], day: Int) {
        guard !edits.isEmpty else { return }
        var entry = days[day] ?? Day()
        for edit in edits {
            entry.fixes[Self.group(edit.category), default: 0] += 1
            if let slip = Self.slip(edit), entry.slips[slip] != nil || entry.slips.count < Self.slipsPerDay { entry.slips[slip, default: 0] += 1 }
        }
        days[day] = entry; trim(today: day)
    }
    mutating func recordIgnore(day: Int) { days[day, default: Day()].ignored += 1; trim(today: day) }
    /// Keeps the newest four weeks of days (also when a day is recorded out of order).
    private mutating func trim(today: Int) { let newest = max(today, days.keys.max() ?? today); days = days.filter { $0.key > newest - Self.keepDays } }
    mutating func clear() { days = [:] }
    /// The seven days ending `today`, and the seven before them for comparison.
    func summary(today: Int) -> WeeklySummary {
        let week = days.filter { $0.key > today - 7 && $0.key <= today }
        let before = days.filter { $0.key > today - 14 && $0.key <= today - 7 }
        var categories: [String: Int] = [:], slips: [String: Int] = [:]
        for day in week.values {
            for (k, v) in day.fixes { categories[k, default: 0] += v }
            for (k, v) in day.slips { slips[k, default: 0] += v }
        }
        let ranked = { (counts: [String: Int]) in counts.sorted { $0.value != $1.value ? $0.value > $1.value : $0.key < $1.key }.map { WeeklySummary.Count(name: $0.key, count: $0.value) } }
        let total = { (days: [Int: Day]) in days.values.reduce(0) { $0 + $1.fixes.values.reduce(0, +) } }
        let busiest = week.filter { !$0.value.fixes.isEmpty }.max { a, b in
            let (x, y) = (a.value.fixes.values.reduce(0, +), b.value.fixes.values.reduce(0, +))
            return x != y ? x < y : a.key > b.key
        }?.key
        return WeeklySummary(fixes: total(week), previousFixes: total(before), categories: ranked(categories), slips: Array(ranked(slips).prefix(5)),
                             ignored: week.values.reduce(0) { $0 + $1.ignored }, activeDays: week.values.filter { !$0.fixes.isEmpty }.count, busiestDay: busiest)
    }
}

struct WeeklySummary: Equatable {
    struct Count: Equatable, Identifiable { let name: String; let count: Int; var id: String { name } }
    var fixes: Int, previousFixes: Int
    var categories: [Count], slips: [Count]
    var ignored: Int, activeDays: Int
    /// Days since 1970 of the day with the most fixes.
    var busiestDay: Int?
    /// "12 more than last week", "3 fewer than last week", or "Same as last week".
    var trend: String? {
        guard fixes > 0 || previousFixes > 0 else { return nil }
        if previousFixes == 0 { return "Your first week with fixes" }
        let delta = fixes - previousFixes
        return delta == 0 ? "Same as last week" : "\(abs(delta)) \(delta > 0 ? "more" : "fewer") than last week"
    }
    var busiestDayName: String? {
        busiestDay.map { day in
            let formatter = DateFormatter(); formatter.dateFormat = "EEEE"; formatter.timeZone = TimeZone(identifier: "UTC")
            return formatter.string(from: Date(timeIntervalSince1970: TimeInterval(day) * 86_400))
        }
    }
}

enum LearningDay {
    /// Days since 1970 in the user's time zone, so a week turns over at local midnight.
    static func today(_ now: Date = Date(), zone: TimeZone = .current) -> Int {
        Int((now.timeIntervalSince1970 + TimeInterval(zone.secondsFromGMT(for: now))) / 86_400)
    }
}
