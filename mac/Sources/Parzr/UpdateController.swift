import AppKit
import ApplicationServices
import Sparkle

/// Owns Sparkle's updater and is its user driver, so Parzr's own panel replaces Sparkle's windows. Never created in test or snapshot modes.
@MainActor
final class UpdateController: NSObject, SPUUserDriver, SPUUpdaterDelegate {
    /// The version Sparkle is about to install (or has downloaded to install on quit), consumed and cleared by the next launch.
    private static let installedKey = "updateInstalledVersion"
    let model: UpdateModel
    private var updater: SPUUpdater!
    private let isBusy: () -> Bool
    private let defaults: UserDefaults
    private var started = false
    // The reply or cancel block for whatever Sparkle is waiting on right now.
    private var foundReply: ((SPUUserUpdateChoice) -> Void)?
    private var readyReply: ((SPUUserUpdateChoice) -> Void)?
    private var cancellation: (() -> Void)?
    private var installNow: (() -> Void)?
    private var restartRequested = false
    /// The user already pressed Install and Relaunch (or Restart now): no second confirmation once the download is ready.
    private var confirmedInstall = false
    private var userInitiated = false
    private var clock: Timer?
    private var countdownStart = Date()
    private var countdownRemaining = 0
    private var notBefore = Date.distantPast
    private var dismissal: DispatchWorkItem?

    /// `nil` when this build has no feed (a bare `swift run`), so development never touches the network.
    init?(model: UpdateModel = .shared, defaults: UserDefaults = .standard, isBusy: @escaping () -> Bool) {
        guard Bundle.main.object(forInfoDictionaryKey: "SUFeedURL") != nil, Bundle.main.bundleIdentifier != nil else { return nil }
        self.model = model; self.defaults = defaults; self.isBusy = isBusy
        super.init()
        updater = SPUUpdater(hostBundle: .main, applicationBundle: .main, userDriver: self, delegate: self)
        model.load(checks: updater.automaticallyChecksForUpdates, downloads: updater.automaticallyDownloadsUpdates)
        model.onToggle = { [weak self] checks, downloads in self?.updater.automaticallyChecksForUpdates = checks; self?.updater.automaticallyDownloadsUpdates = downloads && checks }
        model.handler = { [weak self] in self?.perform($0) }
    }
    /// Starts Sparkle's schedule. Called once onboarding has finished, so nothing touches the network before.
    func start() {
        guard !started else { return }
        started = true
        do { try updater.start() } catch { NSLog("Parzr updates: the updater did not start: \(error.localizedDescription)"); return }
        model.canCheck = true; model.lastChecked = updater.lastUpdateCheckDate
        announceIfUpdated()
    }
    #if DEBUG
    func checkInBackground() { if model.canCheck { updater.checkForUpdatesInBackground() } }
    #endif
    func checkNow() { guard model.canCheck else { return }; if updater.sessionInProgress { showUpdateInFocus() } else { updater.checkForUpdates() } }

    // MARK: Actions from the panel, popover row and Settings
    func perform(_ action: UpdateAction) {
        switch action {
        case .check: checkNow()
        case .install: if let reply = foundReply { foundReply = nil; confirmedInstall = true; reply(.install) }
        case .later:
            if let reply = foundReply, case .found(let info) = model.phase { foundReply = nil; model.available = info; reply(.dismiss) }
            else if let reply = readyReply, case .ready(let info) = model.phase { readyReply = nil; model.pending = info; reply(.dismiss) }
            hide()
        case .skip: if let reply = foundReply { foundReply = nil; model.available = nil; reply(.skip) }; hide()
        case .cancel: cancellation?(); cancellation = nil; model.phase = .idle; hide()
        case .restartNow: restart()
        case .cancelCountdown: stopClock(); notBefore = Date().addingTimeInterval(UpdatePolicy.retryAfterCancel); hide()
        case .dismiss: hide()
        case .whatsNew: if case .updated(let version) = model.phase { NSWorkspace.shared.open(UpdateInfo(version: version).releasePage) }; hide()
        case .view: if foundReply != nil { present(focus: true) } else { restartRequested = false; checkNow() }
        }
    }
    private func restart() {
        if let reply = readyReply { readyReply = nil; reply(.install) }
        else if let installNow { stopClock(); if let info = model.pending { model.phase = .installing(info); present(focus: false) }; installNow() }
        else { restartRequested = true; updater.checkForUpdates() }   // Sparkle resumes the downloaded update and installs it at once
    }
    private func present(focus: Bool) { model.shown = true; model.focus = focus }
    private func hide() { dismissal?.cancel(); model.shown = false; model.focus = false; if !model.inProgress { model.phase = .idle } }
    /// A toast that fades on its own.
    private func toast(_ phase: UpdatePhase, focus: Bool = false, after seconds: TimeInterval) {
        model.phase = phase; present(focus: focus)
        dismissal?.cancel()
        let work = DispatchWorkItem { [weak self] in MainActor.assumeIsolated { if self?.model.phase == phase { self?.hide() } } }
        dismissal = work; DispatchQueue.main.asyncAfter(deadline: .now() + seconds, execute: work)
    }
    private func announceIfUpdated() {
        let current = Support.version, installed = defaults.string(forKey: Self.installedKey)
        defaults.removeObject(forKey: Self.installedKey)   // a stale record (the install never happened) must not announce a later manual install
        guard UpdatePolicy.shouldAnnounce(installed: installed, current: current), Preferences.shared.onboardingCompleted else { return }
        DispatchQueue.main.asyncAfter(deadline: .now() + 2) { MainActor.assumeIsolated { [weak self] in self?.toast(.updated(current), after: 12) } }
    }
    static var bundleVersion: String { Bundle.main.object(forInfoDictionaryKey: "CFBundleVersion") as? String ?? "" }
    static func systemIdle() -> TimeInterval { CGEventSource.secondsSinceLastEventType(.combinedSessionState, eventType: CGEventType(rawValue: ~0)!) }

    // MARK: Quiet install (idle or countdown)
    private func startClock() {
        guard clock == nil else { return }
        clock = Timer.scheduledTimer(withTimeInterval: 1, repeats: true) { [weak self] _ in MainActor.assumeIsolated { self?.tick() } }
    }
    private func stopClock() { clock?.invalidate(); clock = nil }
    private func tick() {
        let idle = Self.systemIdle()
        switch model.phase {
        case .countdown(let info, _):
            switch UpdatePolicy.step(remaining: countdownRemaining, idle: idle, elapsed: Date().timeIntervalSince(countdownStart), busy: isBusy()) {
            case .tick(let left): countdownRemaining = left; model.phase = .countdown(info, seconds: left)
            case .install: restart()
            case .cancel: perform(.cancelCountdown)
            }
        case .found(let info) where !model.shown && foundReply != nil:
            if UpdatePolicy.mayPresent(idle: idle, critical: info.critical) { present(focus: false) }   // a scheduled find waits for a pause in typing
        case .idle:
            if let info = model.pending, installNow != nil {
                guard UpdatePolicy.mayStartCountdown(idle: idle, busy: isBusy(), critical: info.critical, now: Date(), notBefore: notBefore) else { return }
                countdownStart = Date(); countdownRemaining = UpdatePolicy.countdown
                model.phase = .countdown(info, seconds: countdownRemaining); present(focus: false)
            } else if foundReply == nil { stopClock() }
        default: break
        }
    }

    // MARK: SPUUpdaterDelegate
    func updaterShouldPromptForPermissionToCheck(forUpdates updater: SPUUpdater) -> Bool { false }
    func updater(_ updater: SPUUpdater, willInstallUpdateOnQuit item: SUAppcastItem, immediateInstallationBlock: @escaping () -> Void) -> Bool {
        // Downloaded in the background: show the dot and the popover row, and install on quit or when the user steps away.
        model.pending = UpdateInfo(item: item, current: Self.bundleVersion); model.available = nil
        defaults.set(item.displayVersionString, forKey: Self.installedKey)   // Sparkle installs it when Parzr quits and never calls willInstallUpdate then
        installNow = immediateInstallation(immediateInstallationBlock); startClock()
        return true
    }
    private func immediateInstallation(_ block: @escaping () -> Void) -> () -> Void { { [weak self] in self?.installNow = nil; block() } }
    func updater(_ updater: SPUUpdater, willInstallUpdate item: SUAppcastItem) { defaults.set(item.displayVersionString, forKey: Self.installedKey) }
    func updater(_ updater: SPUUpdater, didFinishUpdateCycleFor updateCheck: SPUUpdateCheck, error: (any Error)?) { model.lastChecked = updater.lastUpdateCheckDate }

    // MARK: SPUUserDriver
    func show(_ request: SPUUpdatePermissionRequest, reply: @escaping @Sendable (SUUpdatePermissionResponse) -> Void) {
        reply(SUUpdatePermissionResponse(automaticUpdateChecks: true, sendSystemProfile: false))
    }
    func showUserInitiatedUpdateCheck(cancellation: @escaping @Sendable () -> Void) {
        self.cancellation = cancellation; userInitiated = true
        if !restartRequested { model.phase = .checking; present(focus: true) }
    }
    func showUpdateFound(with appcastItem: SUAppcastItem, state: SPUUserUpdateState, reply: @escaping @Sendable (SPUUserUpdateChoice) -> Void) {
        let info = UpdateInfo(item: appcastItem, current: Self.bundleVersion)
        if restartRequested, state.stage != .notDownloaded { reply(.install); return }
        restartRequested = false; userInitiated = state.userInitiated; cancellation = nil
        foundReply = reply; model.phase = .found(info); model.available = info
        if state.userInitiated || UpdatePolicy.mayPresent(idle: Self.systemIdle(), critical: info.critical) { present(focus: state.userInitiated) } else { model.shown = false; startClock() }
    }
    func showUpdateReleaseNotes(with downloadData: SPUDownloadData) {
        guard case .found(var info) = model.phase, info.notes == nil, let text = String(data: downloadData.data, encoding: .utf8) else { return }
        info.notes = text; info.notesFormat = downloadData.mimeType?.contains("html") == true ? "html" : "markdown"; model.phase = .found(info)
    }
    func showUpdateReleaseNotesFailedToDownloadWithError(_ error: any Error) {}
    func showUpdateNotFoundWithError(_ error: any Error, acknowledgement: @escaping @Sendable () -> Void) {
        toast(.upToDate(UpdateText.upToDate(error as NSError)), focus: true, after: 5); acknowledgement()
    }
    func showUpdaterError(_ error: any Error, acknowledgement: @escaping @Sendable () -> Void) {
        NSLog("Parzr updates: \((error as NSError).domain) \((error as NSError).code)")
        // A failure the user watched stays until dismissed; a background one fades. Either way the next scheduled check retries.
        toast(.failed(UpdateText.friendly(error as NSError)), focus: userInitiated, after: userInitiated ? 60 : 12); acknowledgement()
    }
    func showDownloadInitiated(cancellation: @escaping @Sendable () -> Void) {
        self.cancellation = cancellation
        if case .found(let info) = model.phase { model.phase = .downloading(info, received: 0, total: info.bytes); present(focus: model.focus) }
    }
    func showDownloadDidReceiveExpectedContentLength(_ expectedContentLength: UInt64) {
        if case .downloading(let info, let received, _) = model.phase { model.phase = .downloading(info, received: received, total: expectedContentLength) }
    }
    func showDownloadDidReceiveData(ofLength length: UInt64) {
        if case .downloading(let info, let received, let total) = model.phase { model.phase = .downloading(info, received: received + length, total: total) }
    }
    func showDownloadDidStartExtractingUpdate() {
        cancellation = nil
        switch model.phase {
        case .downloading(let info, _, _), .found(let info): model.phase = .extracting(info, progress: 0); present(focus: model.focus)
        default: break
        }
    }
    func showExtractionReceivedProgress(_ progress: Double) { if case .extracting(let info, _) = model.phase { model.phase = .extracting(info, progress: progress) } }
    func showReady(toInstallAndRelaunch reply: @escaping @Sendable (SPUUserUpdateChoice) -> Void) {
        if restartRequested || confirmedInstall { reply(.install); return }
        guard let info = model.available ?? model.pending else { reply(.install); return }
        readyReply = reply; model.phase = .ready(info); model.available = nil; present(focus: true)
    }
    func showInstallingUpdate(withApplicationTerminated applicationTerminated: Bool, retryTerminatingApplication: @escaping @Sendable () -> Void) {
        let info = model.pending ?? model.available ?? UpdateInfo(version: Support.version)
        if !restartRequested { model.phase = .installing(info); present(focus: false) }
        // The app refused to quit (a sheet, an unsaved window): offer Sparkle's retry again after a moment.
        if !applicationTerminated { DispatchQueue.main.asyncAfter(deadline: .now() + 5) { retryTerminatingApplication() } }
    }
    func showUpdateInstalledAndRelaunched(_ relaunched: Bool, acknowledgement: @escaping @Sendable () -> Void) { acknowledgement() }
    func showUpdateInFocus() { if model.phase != .idle { present(focus: true) } else if model.pending != nil { restartRequested = false; present(focus: true) } else { updater.checkForUpdates() } }
    func dismissUpdateInstallation() {
        foundReply = nil; readyReply = nil; cancellation = nil; restartRequested = false; confirmedInstall = false; userInitiated = false
        // Toasts and the pending dot outlive the session; an unfinished panel does not.
        switch model.phase {
        case .upToDate, .failed, .updated, .countdown: break
        case .installing: break
        default: model.phase = .idle; model.shown = false
        }
        if model.phase == .idle, model.pending == nil, model.available == nil { stopClock() }
    }
}
