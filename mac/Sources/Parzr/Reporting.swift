import AppKit
import ParzrCore

/// Anonymous suggestion reports: only a suggestion the writer reports with "Report wrong suggestion" (Ignore and accepted suggestions send nothing),
/// with the text around it redacted on this Mac, sent in batches
/// to Parzr's report endpoint so wrong suggestions can be fixed. On by default; Settings, Privacy (and the welcome guide)
/// turn it off, which stops sending and erases the queue at once.
@MainActor
enum Reports {
    /// The Info.plist key holding the HTTPS endpoint. A build without it (`swift run`) never reports.
    static let endpointKey = "ParzrReportsURL"
    static let queueFile = "Parzr/report-queue.json"
    /// What is sent and kept, retention, the processor and a contact (website/public/privacy.html, docs/privacy.md).
    nonisolated static let privacyURL = URL(string: "https://parzr.app/privacy")!
    /// nil when this build has no endpoint, and always under a self test or `swift test`: those never send anything.
    static let center: ReportCenter? = {
        guard !Preferences.isSelfTest, !Preferences.underXCTest, let url = endpoint(Bundle.main.object(forInfoDictionaryKey: endpointKey)) else { return nil }
        let store = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first?.appendingPathComponent(queueFile)
        return ReportCenter(endpoint: url, storeURL: store, enabled: Preferences.shared.shareReports)
    }()
    /// Only an absolute HTTPS URL is used.
    nonisolated static func endpoint(_ value: Any?) -> URL? {
        guard let string = value as? String, let url = URL(string: string), url.scheme == "https", url.host?.isEmpty == false else { return nil }
        return url
    }
    /// At launch: applies the saved choice and sends whatever an earlier launch left queued (or erases it when off).
    static func start() { center?.setEnabled(Preferences.shared.shareReports) }
    /// The switch changed. Off is immediate: the gate closes before this returns.
    static func setEnabled(_ enabled: Bool) { center?.setEnabled(enabled) }
    /// Whether this build names a reports server; without one the switch and its text stay hidden.
    static var configured: Bool { center != nil }
    /// Whether the cards offer "Report wrong suggestion".
    static var available: Bool { center != nil && Preferences.shared.shareReports }
    /// "Report wrong suggestion": queues one report per edit; redaction runs in the background, so this costs the caller
    /// almost nothing. `source` is the text the edits' offsets refer to, `app` the bundle identifier of the app it was
    /// written in. Names to redact are the ones the checks use (`KnownNames.names(for:)`): the writer's own, learned and
    /// Contacts names, names in the text, and lowercase names the system lexicon knows.
    static func record(_ edits: [WritingEdit], source: String, mode: RewriteMode, app: String?) {
        guard Preferences.shared.shareReports, let center, !edits.isEmpty, !source.isEmpty else { return }
        center.submit(edits, source: source, mode: mode, app: app, version: Support.version) { await names(for: source) }
    }
    /// Every name source the checks use, with no cap biting before the persistent names.
    static func names(for source: String) async -> [String] {
        let checked = await KnownNames.names(for: source)
        return KnownNames.merge(checked, KnownNames.persistentNames(), limit: KnownNames.maxNames * 2)
    }
}
