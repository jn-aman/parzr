import XCTest
import Sparkle
@testable import Parzr

@MainActor
final class UpdateTests: XCTestCase {
    private let now = Date(timeIntervalSince1970: 1_000_000)

    func testQuietInstallWaitsForAFiveMinuteIdleWithNothingOpen() {
        let may = { (idle: TimeInterval, busy: Bool, critical: Bool, notBefore: Date) in UpdatePolicy.mayStartCountdown(idle: idle, busy: busy, critical: critical, now: self.now, notBefore: notBefore) }
        XCTAssertFalse(may(299, false, false, .distantPast))
        XCTAssertTrue(may(300, false, false, .distantPast))
        XCTAssertFalse(may(900, true, false, .distantPast), "a card, panel or Parzr window in use blocks it")
        XCTAssertFalse(may(900, false, false, now.addingTimeInterval(60)), "a cancelled countdown is not retried at once")
        XCTAssertTrue(may(15, false, true, .distantPast), "critical skips most of the wait")
        XCTAssertFalse(may(14, false, true, .distantPast))
    }
    func testAScheduledPanelWaitsForAPauseInTyping() {
        XCTAssertFalse(UpdatePolicy.mayPresent(idle: 1, critical: false))
        XCTAssertTrue(UpdatePolicy.mayPresent(idle: 4, critical: false))
        XCTAssertTrue(UpdatePolicy.mayPresent(idle: 1.5, critical: true))
        XCTAssertFalse(UpdatePolicy.mayPresent(idle: 0.5, critical: true), "even a critical update lets the user finish typing")
    }
    func testCountdownTicksDownThenInstallsAndAnyInputCancelsIt() {
        XCTAssertEqual(UpdatePolicy.step(remaining: 10, idle: 301, elapsed: 1, busy: false), .tick(9))
        XCTAssertEqual(UpdatePolicy.step(remaining: 2, idle: 305, elapsed: 8, busy: false), .tick(1))
        XCTAssertEqual(UpdatePolicy.step(remaining: 1, idle: 310, elapsed: 10, busy: false), .install)
        XCTAssertEqual(UpdatePolicy.step(remaining: 6, idle: 0.2, elapsed: 4, busy: false), .cancel, "a key press during the countdown")
        XCTAssertEqual(UpdatePolicy.step(remaining: 6, idle: 400, elapsed: 4, busy: true), .cancel, "a card opened")
        XCTAssertEqual(UpdatePolicy.step(remaining: 6, idle: 4.5, elapsed: 5, busy: false), .tick(5), "timer jitter is not input")
    }
    func testTheUpdatedToastShowsOnlyForAnUpdateSparkleInstalled() {
        XCTAssertTrue(UpdatePolicy.shouldAnnounce(installed: "0.3.2", current: "0.3.2"), "the recorded version is the running one")
        XCTAssertTrue(UpdatePolicy.shouldAnnounce(installed: "0.2.10", current: "0.2.10"))
        XCTAssertFalse(UpdatePolicy.shouldAnnounce(installed: "0.3.3", current: "0.3.2"), "a record for another version: the user installed by hand")
        XCTAssertFalse(UpdatePolicy.shouldAnnounce(installed: nil, current: "0.3.2"), "no record: a manual install or a first run")
        XCTAssertFalse(UpdatePolicy.shouldAnnounce(installed: "0.3.4", current: "0.3.2"), "a downgrade is not news")
        XCTAssertFalse(UpdatePolicy.shouldAnnounce(installed: "Development", current: "Development"))
    }
    func testVersionAndSizeDisplay() {
        let info = UpdateInfo(version: "0.2.3", bytes: 14_800_000)
        XCTAssertEqual(info.releasePage.absoluteString, "https://github.com/jn-aman/parzr/releases/tag/v0.2.3")
        XCTAssertNotNil(info.sizeText)
        XCTAssertNil(UpdateInfo(version: "0.2.3").sizeText)
        XCTAssertEqual(UpdateText.progress(received: 0, total: 0), UpdateText.megabytes(0))
        XCTAssertTrue(UpdateText.progress(received: 5_000_000, total: 10_000_000).contains(" of "))
        XCTAssertEqual(UpdateText.ago(now, now: now.addingTimeInterval(20)), "just now")
    }
    func testFriendlyErrorsNeverShowRawText() {
        let offline = UpdateText.friendly(NSError(domain: NSURLErrorDomain, code: NSURLErrorNotConnectedToInternet))
        XCTAssertTrue(offline.contains("try again later"))
        let signature = UpdateText.friendly(NSError(domain: SUSparkleErrorDomain, code: Int(SUError.signatureError.rawValue), userInfo: [NSLocalizedDescriptionKey: "raw: EdDSA mismatch"]))
        XCTAssertTrue(signature.contains("security check") && !signature.contains("EdDSA"))
        XCTAssertTrue(UpdateText.friendly(NSError(domain: SUSparkleErrorDomain, code: Int(SUError.unarchivingError.rawValue))).contains("damaged"))
        XCTAssertTrue(UpdateText.friendly(NSError(domain: "x", code: 1)).contains("untouched"))
    }
    func testNoUpdateMessageFollowsTheReason() {
        let old = NSError(domain: SUSparkleErrorDomain, code: Int(SUError.noUpdateError.rawValue), userInfo: [SPUNoUpdateFoundReasonKey: NSNumber(value: SPUNoUpdateFoundReason.systemIsTooOld.rawValue)])
        XCTAssertTrue(UpdateText.upToDate(old).contains("newer macOS"))
        XCTAssertTrue(UpdateText.upToDate(NSError(domain: SUSparkleErrorDomain, code: Int(SUError.noUpdateError.rawValue))).contains("latest version"))
    }
    func testReleaseNotesMarkdownBecomesBlocks() {
        let blocks = ReleaseNotes.blocks("## New\n- **Faster** names\n* Fewer false alarms\n\nThanks for the reports.\nSee the releases page.", format: "markdown")
        XCTAssertEqual(blocks, [.heading("New"), .bullet("**Faster** names"), .bullet("Fewer false alarms"), .paragraph("Thanks for the reports. See the releases page.")])
        XCTAssertEqual(String(ReleaseNotes.inline("**Faster** names").characters), "Faster names")
        XCTAssertEqual(ReleaseNotes.blocks("", format: nil), [])
    }
    func testReleaseNotesHTMLIsFlattenedToTheSameBlocks() {
        let blocks = ReleaseNotes.blocks("<h2>New</h2><ul><li>Faster &amp; quieter</li><li>Fixes</li></ul><p>Thanks.</p>", format: "html")
        XCTAssertEqual(blocks, [.heading("New"), .bullet("Faster & quieter"), .bullet("Fixes"), .paragraph("Thanks.")])
    }
    func testTheRowPrefersARestartOverAFind() {
        let model = UpdateModel()
        XCTAssertNil(model.row); XCTAssertFalse(model.badge)
        model.available = UpdateInfo(version: "0.3.0", bytes: 1_000_000)
        XCTAssertEqual(model.row, .view("0.3.0", size: model.available?.sizeText)); XCTAssertTrue(model.badge)
        model.pending = UpdateInfo(version: "0.3.0")
        XCTAssertEqual(model.row, .restart("0.3.0"))
    }
    func testTogglesReachTheUpdaterOnlyWhenTheUserChangesThem() {
        let model = UpdateModel(); var calls: [[Bool]] = []
        model.onToggle = { calls.append([$0, $1]) }
        model.load(checks: false, downloads: true)
        XCTAssertTrue(calls.isEmpty, "loading Sparkle's values back is not a user change")
        model.automaticChecks = true
        XCTAssertEqual(calls, [[true, true]])
    }
    func testADownloadAfterTheQuickUpdateFailedBecomesAFullDownloadWithItsOwnProgress() {
        let info = UpdateInfo(version: "0.3.4", bytes: 3_000_000)
        XCTAssertEqual(UpdatePhase.found(info).afterDownloadStarted, .downloading(info, received: 0, total: 3_000_000), "the first download starts from the offer")
        var full = info; full.fullInstead = true
        for stuck in [UpdatePhase.extracting(info, progress: 0.14), .installing(info)] {
            XCTAssertEqual(stuck.afterDownloadStarted, .downloading(full, received: 0, total: 0), "the size follows from the new response")
        }
        XCTAssertEqual(UpdatePhase.idle.afterDownloadStarted, .idle, "a background download with no panel stays quiet")
        XCTAssertEqual(UpdatePhase.checking.afterDownloadStarted, .checking)
        XCTAssertEqual(UpdatePhase.ready(info).afterDownloadStarted, .ready(info))
    }
    func testTheStatusLineFollowsEveryWorkingPhase() {
        let model = UpdateModel(), info = UpdateInfo(version: "0.3.4")
        for (phase, line) in [(UpdatePhase.downloading(info, received: 0, total: 0), "Downloading Parzr 0.3.4…"), (.extracting(info, progress: 0), "Preparing Parzr 0.3.4…"), (.installing(info), "Installing Parzr 0.3.4…")] {
            model.phase = phase; XCTAssertEqual(model.statusLine, line)
        }
    }
    func testInstallingAndCheckingBlockAnotherCheck() {
        let model = UpdateModel()
        for phase in [UpdatePhase.checking, .downloading(UpdateInfo(version: "1"), received: 0, total: 0), .installing(UpdateInfo(version: "1"))] { model.phase = phase; XCTAssertTrue(model.inProgress) }
        model.phase = .upToDate("ok"); XCTAssertFalse(model.inProgress)
    }
}
