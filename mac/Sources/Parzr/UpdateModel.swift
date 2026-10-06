import AppKit
import Combine
import Sparkle

/// What the update UI needs to know about one release. Built from a Sparkle appcast item, or by hand in tests and snapshots.
struct UpdateInfo: Equatable {
    var version: String
    var build = ""
    /// Bytes that will actually be downloaded (the delta when Sparkle has one for this install).
    var bytes: UInt64 = 0
    /// The appcast description: short Markdown (see ReleaseNotes).
    var notes: String?
    var notesFormat: String?
    var critical = false
    var delta = false
    /// Where "What's new" goes.
    var releasePage: URL { URL(string: "https://github.com/jn-aman/parzr/releases/tag/v\(version)")! }
    var sizeText: String? { bytes > 0 ? ByteCountFormatter.string(fromByteCount: Int64(bytes), countStyle: .file) : nil }
}
extension UpdateInfo {
    init(item: SUAppcastItem, current: String) {
        let delta = item.deltaUpdates?[current]
        self.init(version: item.displayVersionString, build: item.versionString, bytes: (delta ?? item).contentLength, notes: item.itemDescription,
                  notesFormat: item.itemDescriptionFormat, critical: item.isCriticalUpdate, delta: delta != nil)
    }
}

enum UpdatePhase: Equatable {
    case idle
    case checking
    case found(UpdateInfo)
    case downloading(UpdateInfo, received: UInt64, total: UInt64)
    case extracting(UpdateInfo, progress: Double)
    case ready(UpdateInfo)
    case installing(UpdateInfo)
    /// The quiet install: a 10 second toast the user can cancel.
    case countdown(UpdateInfo, seconds: Int)
    case upToDate(String)
    case failed(String)
    case updated(String)
}

enum UpdateAction: Equatable { case check, install, later, skip, cancel, restartNow, cancelCountdown, dismiss, whatsNew, view }

/// The state every update surface (panel, popover row, menu-bar dot, Settings, About) reads. The controller owns the writes.
@MainActor
final class UpdateModel: ObservableObject {
    static let shared = UpdateModel()
    @Published var phase = UpdatePhase.idle
    /// A panel is on screen for `phase` (scheduled finds wait for a pause in typing); `focus` asks it to take the keyboard.
    @Published var shown = false
    @Published var focus = false
    /// Downloaded and waiting: installs when Parzr quits, or sooner when the user restarts.
    @Published var pending: UpdateInfo?
    /// Found by a scheduled check and not acted on yet.
    @Published var available: UpdateInfo?
    @Published var lastChecked: Date?
    @Published var canCheck = false
    @Published var automaticChecks = true { didSet { if !loading && oldValue != automaticChecks { onToggle?(automaticChecks, automaticDownloads) } } }
    @Published var automaticDownloads = true { didSet { if !loading && oldValue != automaticDownloads { onToggle?(automaticChecks, automaticDownloads) } } }
    var onToggle: ((Bool, Bool) -> Void)?
    var handler: (UpdateAction) -> Void = { _ in }
    private var loading = false
    func perform(_ action: UpdateAction) { handler(action) }
    func load(checks: Bool, downloads: Bool) { loading = true; automaticChecks = checks; automaticDownloads = downloads; loading = false }
    var inProgress: Bool { switch phase { case .checking, .downloading, .extracting, .installing: true; default: false } }
    /// The mint dot on the menu-bar icon.
    var badge: Bool { pending != nil || available != nil }
    enum Row: Equatable { case restart(String), view(String, size: String?) }
    /// The row at the top of the status popover.
    var row: Row? {
        if let pending { return .restart(pending.version) }
        if let available { return .view(available.version, size: available.sizeText) }
        return nil
    }
    /// One calm line for About and the popover.
    var statusLine: String {
        switch phase {
        case .checking: return "Checking for updates…"
        case .downloading(let info, _, _): return "Downloading Parzr \(info.version)…"
        case .extracting(let info, _): return "Preparing Parzr \(info.version)…"
        default: break
        }
        if let pending { return "Parzr \(pending.version) is ready to install." }
        if let available { return "Parzr \(available.version) is available." }
        guard let lastChecked else { return "Parzr \(Support.version)" }
        return "Parzr \(Support.version) · checked \(UpdateText.ago(lastChecked))"
    }
}

/// Decisions with no UI or Sparkle in them, so they can be tested.
enum UpdatePolicy {
    /// No keyboard or mouse for this long (and nothing of Parzr's open) before a downloaded update restarts Parzr.
    static let idleBeforeInstall: TimeInterval = 300
    /// A critical update skips most of that wait; the countdown still lets the user cancel.
    static let criticalIdleBeforeInstall: TimeInterval = 15
    static let countdown = 10
    static let retryAfterCancel: TimeInterval = 1800
    /// A scheduled update panel waits for a pause in typing, so it never lands in the middle of a sentence.
    static let typingPause: TimeInterval = 4
    static let criticalTypingPause: TimeInterval = 1.5
    static func mayPresent(idle: TimeInterval, critical: Bool) -> Bool { idle >= (critical ? criticalTypingPause : typingPause) }
    static func mayStartCountdown(idle: TimeInterval, busy: Bool, critical: Bool, now: Date, notBefore: Date) -> Bool {
        !busy && now >= notBefore && idle >= (critical ? criticalIdleBeforeInstall : idleBeforeInstall)
    }
    enum Step: Equatable { case tick(Int), install, cancel }
    /// One second of the countdown. Any input since it began (idle shorter than the time elapsed) or any Parzr card opening cancels it.
    static func step(remaining: Int, idle: TimeInterval, elapsed: TimeInterval, busy: Bool) -> Step {
        if busy || idle + 1.5 < elapsed { return .cancel }
        return remaining <= 1 ? .install : .tick(remaining - 1)
    }
    /// The "Updated to X" toast: the version changed to a newer one since the last run.
    static func shouldAnnounce(previous: String?, current: String) -> Bool {
        guard let previous, previous != current, current != "Development" else { return false }
        return SUStandardVersionComparator.default.compareVersion(previous, toVersion: current) == .orderedAscending
    }
}

enum UpdateText {
    static func ago(_ date: Date, now: Date = Date()) -> String {
        if now.timeIntervalSince(date) < 60 { return "just now" }
        let formatter = RelativeDateTimeFormatter(); formatter.unitsStyle = .full
        return formatter.localizedString(for: date, relativeTo: now)
    }
    static func megabytes(_ bytes: UInt64) -> String { ByteCountFormatter.string(fromByteCount: Int64(min(bytes, UInt64(Int64.max))), countStyle: .file) }
    /// "4.1 MB of 14.2 MB", or just what has arrived when the size is unknown.
    static func progress(received: UInt64, total: UInt64) -> String { total > 0 ? "\(megabytes(received)) of \(megabytes(max(total, received)))" : megabytes(received) }
    /// A message a person can read, never a raw error. Nothing here is modal: the next scheduled check tries again.
    static func friendly(_ error: NSError) -> String {
        if error.domain == NSURLErrorDomain {
            return "Parzr could not reach GitHub. Check your connection. It will try again later."
        }
        if error.domain == SUSparkleErrorDomain {
            switch SUError(rawValue: OSStatus(error.code)) {
            case .signatureError, .validationError, .insufficientSigningError, .notValidUpdateError:
                return "The update did not pass Parzr's security check, so it was not installed. Nothing on your Mac changed."
            case .downloadError, .appcastError, .appcastParseError, .resumeAppcastError:
                return "Parzr could not read the update from GitHub. It will try again later."
            case .installationWriteNoPermissionError, .authenticationFailure, .installationCanceledError, .installationAuthorizeLaterError:
                return "Parzr could not replace itself here. Move Parzr to your Applications folder, then try again."
            case .runningFromDiskImageError, .runningTranslocated:
                return "Move Parzr to your Applications folder first, then check for updates."
            default: break
            }
        }
        return "The update did not finish. Your current Parzr is untouched, and it will try again later."
    }
    /// What "no update" means for the user.
    @MainActor static func upToDate(_ error: NSError) -> String {
        switch (error.userInfo[SPUNoUpdateFoundReasonKey] as? NSNumber).flatMap({ SPUNoUpdateFoundReason(rawValue: $0.int32Value) }) {
        case .systemIsTooOld: return "A newer Parzr needs a newer macOS than this Mac runs."
        case .hardwareDoesNotSupportARM64: return "A newer Parzr needs an Apple Silicon Mac."
        default: return "Parzr \(Support.version) is the latest version."
        }
    }
}

/// The appcast description is short Markdown: bullets, a heading or two, bold and links inside lines. HTML (the Sparkle default) is flattened to the same blocks.
enum ReleaseNotes {
    enum Block: Equatable { case heading(String), bullet(String), paragraph(String) }
    static func blocks(_ raw: String, format: String?) -> [Block] {
        var text = raw
        if format == "html" || (format != "markdown" && text.range(of: "<[a-zA-Z/][^>]*>", options: .regularExpression) != nil) { text = flatten(html: text) }
        var blocks: [Block] = [], paragraph: [String] = []
        func flush() { if !paragraph.isEmpty { blocks.append(.paragraph(paragraph.joined(separator: " "))); paragraph = [] } }
        for line in text.split(whereSeparator: \.isNewline).map({ $0.trimmingCharacters(in: .whitespaces) }) {
            if line.isEmpty { flush() }
            else if line.hasPrefix("#") { flush(); blocks.append(.heading(line.drop { $0 == "#" }.trimmingCharacters(in: .whitespaces))) }
            else if line.hasPrefix("- ") || line.hasPrefix("* ") || line.hasPrefix("+ ") { flush(); blocks.append(.bullet(String(line.dropFirst(2)))) }
            else { paragraph.append(line) }
        }
        flush()
        return blocks
    }
    static func inline(_ text: String) -> AttributedString {
        (try? AttributedString(markdown: text, options: .init(interpretedSyntax: .inlineOnlyPreservingWhitespace))) ?? AttributedString(text)
    }
    private static func flatten(html: String) -> String {
        var text = html
        for (pattern, replacement) in [("<li[^>]*>", "\n- "), ("<h[1-6][^>]*>", "\n# "), ("</(p|h[1-6]|li|ul|ol|div)>", "\n"), ("<br\\s*/?>", "\n"), ("<[^>]+>", "")] {
            text = text.replacingOccurrences(of: pattern, with: replacement, options: .regularExpression)
        }
        for (entity, character) in [("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"), ("&quot;", "\""), ("&#39;", "'"), ("&nbsp;", " ")] { text = text.replacingOccurrences(of: entity, with: character) }
        return text
    }
}
