import AppKit
import NaturalLanguage
import SwiftUI
import ParzrCore
import ServiceManagement

@MainActor
final class Preferences: ObservableObject {
    static let shared = Preferences()
    private let defaults: UserDefaults
    @Published var passive: Bool { didSet { defaults.set(passive, forKey: "passive") } }
    @Published var paused: Bool { didSet { defaults.set(paused, forKey: "paused") } }
    @Published var dialect: String { didSet { defaults.set(dialect, forKey: "dialect") } }
    @Published var defaultMode: RewriteMode { didSet { defaults.set(defaultMode.rawValue, forKey: "defaultMode") } }
    @Published var dictionary: [String] { didSet { defaults.set(dictionary, forKey: "dictionary") } }
    @Published var disabledApps: [String] { didSet { defaults.set(disabledApps, forKey: "disabledApps") } }
    @Published var clipboardFallback: Bool { didSet { defaults.set(clipboardFallback, forKey: "clipboardFallback") } }
    @Published var shortcutKey: Int { didSet { defaults.set(shortcutKey, forKey: "shortcutKey") } }
    @Published var shortcutModifiers: Int { didSet { defaults.set(shortcutModifiers, forKey: "shortcutModifiers") } }
    @Published var shortcutLabel: String { didSet { defaults.set(shortcutLabel, forKey: "shortcutLabel") } }
    @Published var recordingShortcut = false
    @Published var checkingDelay: Double { didSet { defaults.set(checkingDelay, forKey: "checkingDelay") } }
    @Published var selectedTextPopover: Bool { didSet { defaults.set(selectedTextPopover, forKey: "selectedTextPopover") } }
    @Published var highlightFill: Bool { didSet { defaults.set(highlightFill, forKey: "highlightFill") } }
    @Published var editorFontSize: Double { didSet { defaults.set(editorFontSize, forKey: "editorFontSize") } }
    @Published var editorLineSpacing: Double { didSet { defaults.set(editorLineSpacing, forKey: "editorLineSpacing") } }
    @Published var appearance: String { didSet { defaults.set(appearance, forKey: "appearance") } }
    @Published var reduceMotion: Bool { didSet { defaults.set(reduceMotion, forKey: "reduceMotion") } }
    @Published var contextRefinement: Bool { didSet { defaults.set(contextRefinement, forKey: "contextRefinement") } }
    @Published var showWordCount: Bool { didSet { defaults.set(showWordCount, forKey: "showWordCount") } }
    @Published var showInDock: Bool { didSet { defaults.set(showInDock, forKey: "showInDock") } }
    /// Opt-in: VS Code and Cursor show a screen-reader notice when Parzr asks for accessibility, so they stay untouched until enabled.
    @Published var checkVSCode: Bool { didSet { defaults.set(checkVSCode, forKey: "checkVSCode") } }
    @Published var firefoxHintDismissed: Bool { didSet { defaults.set(firefoxHintDismissed, forKey: "firefoxHintDismissed") } }
    /// Shown in the menu-bar popover when Firefox blocks accessibility; not persisted, so it returns next launch until dismissed.
    @Published var firefoxHint = false
    /// Names Parzr learned (undone fixes, repeated Ignores, "This is a name"); persisted, shared with the browser host and LSP through known-words.json.
    @Published var learnedNames: [String] { didSet { defaults.set(learnedNames, forKey: "learnedNames") } }
    @Published var useContactNames: Bool { didSet { defaults.set(useContactNames, forKey: "useContactNames") } }
    @Published var nameCapitalization: String { didSet { defaults.set(nameCapitalization, forKey: "nameCapitalization") } }
    /// Name tokens from Contacts; memory only, rebuilt at launch while authorized and purged otherwise.
    @Published var contactNames: [String] = []
    @Published var contactsNote: String?
    private var ignoreCounts: [String: Int] { didSet { defaults.set(ignoreCounts, forKey: "ignoreCounts") } }
    private(set) var ledger: RepetitionLedger { didSet { defaults.set(try? JSONEncoder().encode(ledger), forKey: "repetitionLedger") } }
    var boundedCheckingDelay: Double { checkingDelay.isFinite ? min(700, max(40, checkingDelay)) : 90 }
    var boundedFontSize: Double { editorFontSize.isFinite ? min(24, max(15, editorFontSize)) : 18 }
    var boundedLineSpacing: Double { editorLineSpacing.isFinite ? min(12, max(2, editorLineSpacing)) : 6 }
    var shortcutDisplay: String {
        var label = ""
        if shortcutModifiers & 4096 != 0 { label += "⌃" }
        if shortcutModifiers & 2048 != 0 { label += "⌥" }
        if shortcutModifiers & 512 != 0 { label += "⇧" }
        if shortcutModifiers & 256 != 0 { label += "⌘" }
        return label + " " + shortcutLabel
    }
    @Published var permissionGranted = AXIsProcessTrusted()
    @Published var launchError: String?
    @Published var permissionRequested = false
    private var permissionWatch: Task<Void, Never>?
    var launchAtLogin: Bool { SMAppService.mainApp.status == .enabled }
    init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
        passive = defaults.object(forKey: "passive") as? Bool ?? true; paused = defaults.bool(forKey: "paused")
        dialect = defaults.string(forKey: "dialect") ?? "american"
        defaultMode = RewriteMode(rawValue: defaults.string(forKey: "defaultMode") ?? "fix") ?? .fix
        dictionary = defaults.stringArray(forKey: "dictionary") ?? ["parzr"]
        disabledApps = defaults.stringArray(forKey: "disabledApps") ?? []
        clipboardFallback = defaults.bool(forKey: "clipboardFallback")
        shortcutKey = defaults.object(forKey: "shortcutKey") as? Int ?? 49
        shortcutModifiers = defaults.object(forKey: "shortcutModifiers") as? Int ?? 2048
        shortcutLabel = defaults.string(forKey: "shortcutLabel") ?? "Space"
        checkingDelay = defaults.object(forKey: "checkingDelay") as? Double ?? 90
        selectedTextPopover = defaults.object(forKey: "selectedTextPopover") as? Bool ?? true
        highlightFill = defaults.object(forKey: "highlightFill") as? Bool ?? true
        editorFontSize = defaults.object(forKey: "editorFontSize") as? Double ?? 18
        editorLineSpacing = defaults.object(forKey: "editorLineSpacing") as? Double ?? 6
        appearance = defaults.string(forKey: "appearance") ?? "graphite"
        reduceMotion = defaults.bool(forKey: "reduceMotion")
        contextRefinement = defaults.object(forKey: "contextRefinement") as? Bool ?? true
        showWordCount = defaults.object(forKey: "showWordCount") as? Bool ?? true
        showInDock = defaults.object(forKey: "showInDock") as? Bool ?? true
        checkVSCode = defaults.bool(forKey: "checkVSCode"); firefoxHintDismissed = defaults.bool(forKey: "firefoxHintDismissed")
        learnedNames = defaults.stringArray(forKey: "learnedNames") ?? []
        useContactNames = defaults.bool(forKey: "useContactNames")
        nameCapitalization = defaults.string(forKey: "nameCapitalization") ?? NameCapitalization.documents.rawValue
        ignoreCounts = defaults.dictionary(forKey: "ignoreCounts") as? [String: Int] ?? [:]
        ledger = defaults.data(forKey: "repetitionLedger").flatMap { try? JSONDecoder().decode(RepetitionLedger.self, from: $0) } ?? RepetitionLedger()
    }
    func requestPermission() {
        permissionRequested = true
        let options = ["AXTrustedCheckOptionPrompt": true] as CFDictionary
        permissionGranted = AXIsProcessTrustedWithOptions(options)
        if !permissionGranted, let url = URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility") { NSWorkspace.shared.open(url) }
        watchPermission()
    }
    /// Launch-time ask: macOS shows its own dialog (with Open System Settings); we do not open Settings ourselves.
    func promptForPermission() {
        permissionGranted = AXIsProcessTrustedWithOptions(["AXTrustedCheckOptionPrompt": true] as CFDictionary)
        watchPermission()
    }
    /// macOS posts this when any app's Accessibility grant changes; refreshing here makes a new grant take effect without relaunching or opening Parzr.
    func watchTrustChanges() {
        DistributedNotificationCenter.default().addObserver(forName: NSNotification.Name("com.apple.accessibility.api"), object: nil, queue: .main) { [weak self] _ in
            Task { @MainActor in try? await Task.sleep(for: .milliseconds(300)); self?.refreshPermission() }
        }
    }
    func refreshPermission() {
        permissionGranted = AXIsProcessTrusted()
        if permissionGranted { permissionWatch?.cancel(); permissionWatch = nil; permissionRequested = false }
    }
    func watchPermission() {
        guard permissionWatch == nil, !permissionGranted else { return }
        permissionWatch = Task { @MainActor [weak self] in
            for _ in 0..<600 { // 10 minutes; app activation and the menu also refresh it
                do { try await Task.sleep(for: .seconds(1)); try Task.checkCancellation() } catch { break }
                guard let self else { return }
                self.refreshPermission()
                if self.permissionGranted { return }
            }
            self?.permissionWatch = nil
        }
    }
    func setLogin(_ enabled: Bool) {
        do { if enabled { try SMAppService.mainApp.register() } else { try SMAppService.mainApp.unregister() }; launchError = nil; objectWillChange.send() }
        catch { launchError = "macOS could not change login settings: \(error.localizedDescription)" }
    }
    func dismissFirefoxHint() { firefoxHint = false; firefoxHintDismissed = true }
    func enabled(for bundle: String) -> Bool { !disabledApps.contains(bundle) }
    func saveWord(_ word: String) {
        guard !word.isEmpty, word.utf8.count <= 128, dictionary.count < 1000, !dictionary.contains(where: { $0.caseInsensitiveCompare(word) == .orderedSame }) else { return }
        dictionary.append(word)
    }
    /// Adds a name (possessive stripped) once; false when it is not name-shaped, a duplicate, or the list is full.
    @discardableResult
    func learnName(_ raw: String) -> Bool {
        guard let name = WritingEdit.nameToken(raw), learnedNames.count < 2000, !learnedNames.contains(where: { $0.caseInsensitiveCompare(name) == .orderedSame }) else { return false }
        learnedNames.append(name); return true
    }
    /// A user Ignore on a spelling or name-like edit counts toward learning its word as a name.
    static let ignoresToLearn = 2
    func noteIgnored(_ edit: WritingEdit) {
        guard edit.category == "Spelling" || edit.nameCandidate != nil, let name = WritingEdit.nameToken(edit.original) else { return }
        let key = name.lowercased()
        guard ignoreCounts[key] != nil || ignoreCounts.count < 500 else { return }
        let count = (ignoreCounts[key] ?? 0) + 1
        if count >= Self.ignoresToLearn { learnName(name); ignoreCounts[key] = nil } else { ignoreCounts[key] = count }
    }
    /// A lowercase word kept through a passive check. Learned as a name after 3 sightings over 2 or more apps or days; see RepetitionLedger.
    func noteSighting(_ word: String, app: String, day: Int) {
        guard !learnedNames.contains(where: { $0.caseInsensitiveCompare(word) == .orderedSame }), ledger.sight(word, app: app, day: day) else { return }
        learnName(word)
    }
    /// The user applied a Parzr correction to this word, so repetition never learns it.
    func noteApplied(_ word: String) { ledger.applied(word, day: Int(Date().timeIntervalSince1970 / 86_400)) }
    var capitalizeNamesChoice: String { get { nameCapitalization } set { nameCapitalization = newValue } }
    /// Maps the picker to the engine's `capitalize_names` for the app being written in (nil: the playground).
    func capitalizeNames(for bundle: String?) -> Bool { (NameCapitalization(rawValue: nameCapitalization) ?? .documents).enabled(bundle: bundle) }
    // Key-path bindings for toggles (see AppModel.modeChoice).
    var automaticHighlights: Bool { get { passive && !paused } set { passive = newValue; paused = false } }
    var launchAtLoginChoice: Bool { get { launchAtLogin } set { setLogin(newValue) } }
    subscript(appEnabled bundle: String) -> Bool { get { enabled(for: bundle) } set { if newValue != enabled(for: bundle) { toggleApp(bundle) } } }
    func toggleApp(_ bundle: String) { if let i = disabledApps.firstIndex(of: bundle) { disabledApps.remove(at: i) } else { disabledApps.append(bundle) } }
}

/// Names the engine must never "correct" (it may only re-case them; matching is ASCII case-insensitive, whole tokens, multi-word entries by phrase).
/// Sources: the user's own name, learned names, Contacts (opt-in), and names in the current text (session only, never persisted or shared).
enum KnownNames {
    static let user = names(full: NSFullUserName(), short: NSUserName())
    static let maxNames = 2000
    nonisolated static func names(full: String, short: String) -> [String] {
        let tokens = (full + " " + short).split { !$0.isLetter }.map(String.init).filter { $0.count >= 2 }
        let phrase = full.split { !$0.isLetter }.count > 1 ? [full.trimmingCharacters(in: .whitespacesAndNewlines)] : []
        return merge(tokens, phrase)
    }
    /// Capitalized people, places and organizations already in the text (first 64 KB, at most 200), so a lowercase repeat is treated as the same name.
    nonisolated static func documentNames(in text: String) -> [String] {
        let tagger = NLTagger(tagSchemes: [.nameType])
        var found: [String] = []
        // Per sentence: one lowercase sentence start ("aman agreed") makes NLTagger tag a whole longer string as nothing.
        for sentence in String(text.prefix(65_536)).split(whereSeparator: { ".!?\n".contains($0) }) where found.count < 400 {
            let sentence = String(sentence)
            tagger.string = sentence
            // Without a language short texts get no tags at all.
            tagger.setLanguage(.english, range: sentence.startIndex..<sentence.endIndex)
            tagger.enumerateTags(in: sentence.startIndex..<sentence.endIndex, unit: .word, scheme: .nameType, options: [.omitWhitespace, .omitPunctuation, .omitOther]) { tag, range in
                guard let tag, [.personalName, .placeName, .organizationName].contains(tag) else { return true }
                var word = String(sentence[range])
                for suffix in ["'s", "\u{2019}s"] where word.hasSuffix(suffix) { word.removeLast(suffix.count) }
                if word.count >= 2, word.contains(where: \.isUppercase) { found.append(word) }
                return true
            }
        }
        return Array(merge(found, capitalizedMidSentence(in: text)).prefix(200))
    }
    /// Words capitalized in the middle of a sentence ("Hi Aman,"), which NLTagger can miss. Sentence starts, "I" and ALL CAPS words are skipped.
    nonisolated static func capitalizedMidSentence(in text: String) -> [String] {
        var found: [String] = []
        let trim = CharacterSet.letters.union(CharacterSet(charactersIn: "'\u{2019}-")).inverted
        for line in String(text.prefix(65_536)).split(whereSeparator: \.isNewline) {
            var atStart = true
            for token in line.split(whereSeparator: \.isWhitespace) {
                let word = token.trimmingCharacters(in: trim)
                if !atStart, word.count >= 2, word.first?.isUppercase == true, word.contains(where: \.isLowercase), found.count < 400 {
                    var name = word
                    for suffix in ["'s", "\u{2019}s"] where name.hasSuffix(suffix) { name.removeLast(suffix.count) }
                    if name.count >= 2 { found.append(name) }
                }
                atStart = token.last.map { ".!?:".contains($0) } == true
            }
        }
        return found
    }
    /// Order-preserving, case-insensitive dedupe within the engine limits (`limit` entries, 128 bytes each); earlier lists win.
    nonisolated static func merge(_ lists: [String]..., limit: Int = 1000) -> [String] {
        var seen = Set<String>(), out: [String] = []
        for word in lists.joined() where !word.isEmpty && word.utf8.count <= 128 && out.count < limit && seen.insert(word.lowercased()).inserted { out.append(word) }
        return out
    }
    /// Names that persist across sessions: the user's own, learned, and (when enabled) Contacts. Also what known-words.json shares.
    @MainActor static func persistentNames() -> [String] {
        let prefs = Preferences.shared
        return merge(user, prefs.learnedNames, prefs.useContactNames ? prefs.contactNames : [], limit: maxNames)
    }
    /// Persistent names plus names found in `text` and lowercase names the system lexicon knows in `request` (both scans run off the main actor). Session names rank above Contacts when the cap bites.
    @MainActor static func names(for text: String, request: String? = nil) async -> [String] {
        let prefs = Preferences.shared
        let document = await Task.detached(priority: .utility) { documentNames(in: text) }.value
        let lexicon = await SystemLexicon.shared.names(in: request ?? text)
        return merge(user, prefs.learnedNames, document, lexicon, prefs.useContactNames ? prefs.contactNames : [], limit: maxNames)
    }
    @MainActor static func dictionary() -> [String] { merge(Preferences.shared.dictionary) }
    /// Spelling edits for words the user taught macOS are not mistakes. Cheap: only flagged edits are asked.
    @MainActor static func dropMacLearned(_ result: RewriteResult, from source: String) -> RewriteResult {
        result.dropping(from: source) { $0.category == "Spelling" && NSSpellChecker.shared.hasLearnedWord($0.original) }
    }
}

enum NameCapitalization: String, CaseIterable {
    case never, documents, everywhere
    static let chatApps = ["com.tinyspeck.slackmacgap", "com.microsoft.teams", "com.microsoft.teams2", "net.whatsapp.WhatsApp", "desktop.WhatsApp", "com.hnc.Discord", "ru.keepcoder.Telegram", "com.apple.MobileSMS", "com.facebook.archon"]
    func enabled(bundle: String?) -> Bool {
        switch self {
        case .never: false
        case .everywhere: true
        case .documents: !Self.chatApps.contains { bundle?.hasPrefix($0) == true }
        }
    }
}
