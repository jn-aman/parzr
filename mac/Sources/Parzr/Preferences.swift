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
    func enabled(for bundle: String) -> Bool { !disabledApps.contains(bundle) }
    func saveWord(_ word: String) {
        guard !word.isEmpty, word.utf8.count <= 128, dictionary.count < 1000, !dictionary.contains(where: { $0.caseInsensitiveCompare(word) == .orderedSame }) else { return }
        dictionary.append(word)
    }
    // Key-path bindings for toggles (see AppModel.modeChoice).
    var automaticHighlights: Bool { get { passive && !paused } set { passive = newValue; paused = false } }
    var launchAtLoginChoice: Bool { get { launchAtLogin } set { setLogin(newValue) } }
    subscript(appEnabled bundle: String) -> Bool { get { enabled(for: bundle) } set { if newValue != enabled(for: bundle) { toggleApp(bundle) } } }
    func toggleApp(_ bundle: String) { if let i = disabledApps.firstIndex(of: bundle) { disabledApps.remove(at: i) } else { disabledApps.append(bundle) } }
}

/// Session-only names the engine must never "correct" (engine dictionary matching is ASCII case-insensitive, whole tokens, multi-word entries by phrase). Never persisted.
enum KnownNames {
    static let user = names(full: NSFullUserName(), short: NSUserName())
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
            tagger.enumerateTags(in: sentence.startIndex..<sentence.endIndex, unit: .word, scheme: .nameType, options: [.omitWhitespace, .omitPunctuation, .omitOther]) { tag, range in
                guard let tag, [.personalName, .placeName, .organizationName].contains(tag) else { return true }
                var word = String(sentence[range])
                for suffix in ["'s", "\u{2019}s"] where word.hasSuffix(suffix) { word.removeLast(suffix.count) }
                if word.count >= 2, word.contains(where: \.isUppercase) { found.append(word) }
                return true
            }
        }
        return Array(merge(found).prefix(200))
    }
    /// Order-preserving, case-insensitive dedupe within the engine limits (1000 entries, 128 bytes each); earlier lists win.
    nonisolated static func merge(_ lists: [String]...) -> [String] {
        var seen = Set<String>(), out: [String] = []
        for word in lists.joined() where !word.isEmpty && word.utf8.count <= 128 && out.count < 1000 && seen.insert(word.lowercased()).inserted { out.append(word) }
        return out
    }
    /// Saved dictionary, then the user's name, then names found in `text`; the scan runs off the main actor.
    @MainActor static func dictionary(for text: String) async -> [String] {
        let saved = Preferences.shared.dictionary
        let document = await Task.detached(priority: .utility) { documentNames(in: text) }.value
        return merge(saved, user, document)
    }
}
