import AppKit
import Contacts
import ParzrCore

/// Name tokens from Contacts (given, family, nickname, organization). Tokens only: no identifiers, numbers or addresses are read or kept.
enum ContactNames {
    nonisolated static func tokens(person: [String], organization: String) -> [String] {
        person.flatMap { $0.split(whereSeparator: \.isWhitespace) }.compactMap { WritingEdit.nameToken(String($0)) } + [WritingEdit.nameToken(organization)].compactMap { $0 }
    }
    nonisolated static func read() -> [String] {
        let keys = [CNContactGivenNameKey, CNContactFamilyNameKey, CNContactNicknameKey, CNContactOrganizationNameKey] as [CNKeyDescriptor]
        var out: [String] = []
        try? CNContactStore().enumerateContacts(with: CNContactFetchRequest(keysToFetch: keys)) { contact, stop in
            out += tokens(person: [contact.givenName, contact.familyName, contact.nickname], organization: contact.organizationName)
            if out.count > 8000 { stop.pointee = true }
        }
        return KnownNames.merge(out, limit: 1500)
    }
}

extension Preferences {
    var contactsChoice: Bool { get { useContactNames } set { setContacts(newValue) } }
    /// Launch: rebuild Contacts names while access is still granted; otherwise switch the option off and purge.
    func syncContacts() {
        guard useContactNames else { contactNames = []; return }
        guard CNContactStore.authorizationStatus(for: .contacts) == .authorized else { useContactNames = false; contactNames = []; return }
        loadContacts()
    }
    private func loadContacts() {
        Task { @MainActor in
            let tokens = await Task.detached(priority: .utility) { ContactNames.read() }.value
            if useContactNames { contactNames = tokens }
        }
    }
    /// Opt-in. macOS is asked for Contacts only when this is turned on.
    func setContacts(_ on: Bool) {
        contactsNote = nil
        guard on else { useContactNames = false; contactNames = []; return }
        guard Bundle.main.object(forInfoDictionaryKey: "NSContactsUsageDescription") != nil else { contactsNote = "Contacts access needs the installed Parzr app."; return }
        Task { @MainActor in
            let granted = (try? await CNContactStore().requestAccess(for: .contacts)) ?? false
            useContactNames = granted
            if granted { loadContacts() } else { contactsNote = "Allow Contacts for Parzr in System Settings, Privacy & Security, then turn this on again." }
        }
    }
}

/// `~/Library/Application Support/Parzr/known-words.json`, shared with the browser native host, the language server and VS Code.
/// Names are the user's own, learned and (if enabled) Contacts names. Names found in a document are session-only and never written.
enum KnownWordsFile {
    static var url: URL { FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0].appendingPathComponent("Parzr/known-words.json") }
    nonisolated static func data(dictionary: [String], names: [String]) throws -> Data {
        try JSONSerialization.data(withJSONObject: ["version": 1, "dictionary": dictionary, "names": names] as [String: Any], options: [.sortedKeys])
    }
    nonisolated static func write(dictionary: [String], names: [String], to url: URL) throws {
        try FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
        try data(dictionary: dictionary, names: names).write(to: url, options: .atomic)
    }
    @MainActor static func writeCurrent() { try? write(dictionary: KnownNames.dictionary(), names: KnownNames.persistentNames(), to: url) }
}

/// A fix Parzr just applied to one word. If the original comes back at the same spot within a minute, the user undid it: the word is a name.
@MainActor
enum FixLearning {
    struct Fix { let pid: pid_t; let element: CFHashCode; let original: String, replacement: String; let location: Int; let time: Date }
    enum State { case pending, reverted, gone }
    nonisolated static let window: TimeInterval = 60
    private static var recent: [Fix] = []
    nonisolated static func state(of fix: Fix, in text: String, now: Date) -> State {
        guard now.timeIntervalSince(fix.time) <= window else { return .gone }
        let ns = text as NSString
        func present(_ word: String) -> Bool { fix.location >= 0 && fix.location + word.utf16.count <= ns.length && ns.substring(with: NSRange(location: fix.location, length: word.utf16.count)) == word }
        return present(fix.replacement) ? .pending : present(fix.original) ? .reverted : .gone
    }
    /// Only edits that changed letters of a single word count (not capitalization, spacing or phrases).
    nonisolated static func tracks(_ edit: WritingEdit) -> Bool {
        edit.original.count >= 2 && !edit.replacement.isEmpty && edit.original.allSatisfy { $0.isLetter || "'\u{2019}".contains($0) } && edit.original.lowercased() != edit.replacement.lowercased()
    }
    /// `edits` are in text order; `selection` is where their text sits in the editor.
    static func record(_ edits: [WritingEdit], in snapshot: SelectionSnapshot) {
        var shift = 0
        let now = Date(), pid = snapshot.app.processIdentifier, element = CFHash(snapshot.element)
        recent = recent.filter { now.timeIntervalSince($0.time) <= window }
        for edit in edits {
            if edit.category == "Spelling" { Preferences.shared.noteApplied(edit.original) }
            if tracks(edit) { recent.append(Fix(pid: pid, element: element, original: edit.original, replacement: edit.replacement, location: snapshot.selection.location + edit.start_utf16 + shift, time: now)) }
            shift += edit.replacement.utf16.count - edit.range.length
        }
        if recent.count > 16 { recent.removeFirst(recent.count - 16) }
    }
    /// Called on every passive capture of an editor.
    static func observe(_ snapshot: SelectionSnapshot) {
        guard !recent.isEmpty, let full = snapshot.fullText else { return }
        let now = Date(), pid = snapshot.app.processIdentifier, element = CFHash(snapshot.element)
        recent = recent.filter { fix in
            guard fix.pid == pid, fix.element == element else { return now.timeIntervalSince(fix.time) <= window }
            switch state(of: fix, in: full, now: now) {
            case .pending: return true
            case .reverted: Preferences.shared.learnName(fix.original); return false
            case .gone: return false
            }
        }
    }
}

/// Apple-style "typed it again and again, never fixed it": words and counts only (no text), per (app, day). Persisted by Preferences.
struct RepetitionLedger: Codable, Equatable {
    struct Entry: Codable, Equatable { var keys: [String: Int] = [:]; var last = 0; var blocked = false }
    static let capacity = 2000, sightingsToLearn = 3, perKey = 3, maxKeys = 8
    private(set) var entries: [String: Entry] = [:]
    /// Records one sighting; true when the word should now be learned (3 sightings over 2 or more distinct app and day pairs). A learned word leaves the ledger.
    mutating func sight(_ word: String, app: String, day: Int) -> Bool {
        let word = word.lowercased(), key = "\(app)|\(day)"
        var entry = entries[word] ?? Entry()
        guard !entry.blocked else { return false }
        if entry.keys[key] != nil || entry.keys.count < Self.maxKeys { entry.keys[key] = min(Self.perKey, (entry.keys[key] ?? 0) + 1) }
        entry.last = day
        if entry.keys.count >= 2, entry.keys.values.reduce(0, +) >= Self.sightingsToLearn { entries[word] = nil; return true }
        entries[word] = entry; trim(); return false
    }
    /// The user applied a correction to this word: it is a typo for them, never learn it.
    mutating func applied(_ word: String, day: Int) {
        entries[word.lowercased()] = Entry(keys: [:], last: day, blocked: true); trim()
    }
    private mutating func trim() {
        while entries.count > Self.capacity, let oldest = entries.min(by: { $0.value.last < $1.value.last })?.key { entries[oldest] = nil }
    }
}

/// Feeds the ledger from passive checks: a lowercase single word the engine flags as Spelling and the user moves past counts as one sighting per appearance in a field.
@MainActor
enum RepetitionLearning {
    private static var present: [String: Set<String>] = [:]
    /// Lowercase single-word Spelling edits the user has typed past (text continues after the word), lowercased.
    nonisolated static func candidates(in edits: [WritingEdit], text: String) -> Set<String> {
        Set(edits.compactMap { edit in
            guard edit.category == "Spelling", edit.end_utf16 < text.utf16.count, let word = NameGate.shaped(edit.original), word == edit.original, !word.contains("-") else { return nil }
            return word
        })
    }
    /// Words newly present in this field since its last check; a word that left the field's text can count again when typed again.
    nonisolated static func fresh(_ words: Set<String>, previous: Set<String>, fullText: String) -> (fresh: Set<String>, present: Set<String>) {
        let lower = fullText.lowercased()
        let kept = previous.filter { lower.contains($0) }
        return (words.subtracting(kept), kept.union(words))
    }
    static func observe(_ edits: [WritingEdit], in snapshot: SelectionSnapshot) {
        let field = "\(snapshot.app.processIdentifier):\(CFHash(snapshot.element))"
        let (new, now) = fresh(candidates(in: edits, text: snapshot.text), previous: present[field] ?? [], fullText: snapshot.fullText ?? snapshot.text)
        if present.count > 16, present[field] == nil { present.removeAll() }
        present[field] = now
        let app = snapshot.app.bundleIdentifier ?? "?", day = Int(Date().timeIntervalSince1970 / 86_400)
        for word in new { Preferences.shared.noteSighting(word, app: app, day: day) }
    }
}
