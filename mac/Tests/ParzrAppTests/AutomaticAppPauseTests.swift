import XCTest
import Combine
@testable import Parzr

/// Policy tests only: no app, windows, Accessibility queries, engine, or model.
@MainActor
final class AutomaticAppPauseTests: XCTestCase {
    private final class Clock {
        var date = Date(timeIntervalSince1970: 1_800_000_000)
    }
    private let app = "com.example.editor"
    private let otherApp = "com.example.chat"

    private func preferences(_ clock: Clock) throws -> (Preferences, UserDefaults, String) {
        let suite = "app.parzr.tests.AutomaticAppPauseTests.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        defaults.removePersistentDomain(forName: suite)
        defaults.set(true, forKey: "onboardingCompleted")
        defaults.set(true, forKey: "passive")
        defaults.set(false, forKey: "paused")
        defaults.set([String](), forKey: "disabledApps")
        defaults.set([String: Date](), forKey: "automaticAppPauses")
        addTeardownBlock { UserDefaults(suiteName: suite)?.removePersistentDomain(forName: suite) }
        return (Preferences(defaults: defaults, now: { clock.date }, permissionGranted: false), defaults, suite)
    }

    /// Suspend a result until the test changes policy; do not rely on sleeps or task scheduling order.
    private func pendingEligibility(_ preferences: Preferences, bundle: String, automatic: Bool = true) async throws -> (Task<Bool, Never>, CheckedContinuation<Void, Never>) {
        var pending: Task<Bool, Never>?
        let release: CheckedContinuation<Void, Never> = await withCheckedContinuation { started in
            pending = Task { @MainActor in
                await withCheckedContinuation { (release: CheckedContinuation<Void, Never>) in
                    started.resume(returning: release)
                }
                return preferences.checkingEnabled(for: bundle, automatic: automatic)
            }
        }
        return (try XCTUnwrap(pending), release)
    }

    func testBothDurationsExpireAtExactBoundariesWithoutCachedEligibility() async throws {
        let clock = Clock(), start = clock.date
        let (prefs, _, _) = try preferences(clock)
        prefs.pauseAutomaticChecking(for: app, duration: .fifteenMinutes)
        prefs.pauseAutomaticChecking(for: otherApp, duration: .oneHour)
        XCTAssertEqual(prefs.automaticPauseExpiration(for: app), start.addingTimeInterval(900))
        XCTAssertEqual(prefs.automaticPauseExpiration(for: otherApp), start.addingTimeInterval(3600))
        clock.date = start.addingTimeInterval(899.999)
        XCTAssertFalse(prefs.checkingEnabled(for: app, automatic: true))
        clock.date = start.addingTimeInterval(900)
        XCTAssertTrue(prefs.checkingEnabled(for: app, automatic: true))
        XCTAssertFalse(prefs.checkingEnabled(for: otherApp, automatic: true))
        clock.date = start.addingTimeInterval(3599.999)
        XCTAssertFalse(prefs.checkingEnabled(for: otherApp, automatic: true))
        clock.date = start.addingTimeInterval(3600)
        XCTAssertTrue(prefs.checkingEnabled(for: otherApp, automatic: true))
    }

    func testPauseIsIsolatedByExactBundleID() async throws {
        let (prefs, _, _) = try preferences(Clock())
        prefs.pauseAutomaticChecking(for: app, duration: .fifteenMinutes)
        XCTAssertFalse(prefs.checkingEnabled(for: app, automatic: true))
        XCTAssertTrue(prefs.checkingEnabled(for: otherApp, automatic: true))
        XCTAssertTrue(prefs.checkingEnabled(for: app + ".helper", automatic: true))
        XCTAssertTrue(prefs.enabled(for: app), "A temporary pause is not a permanent opt-out.")
    }

    func testResumeDoesNotClearOtherPausesOrPermanentOptOuts() async throws {
        let (prefs, defaults, _) = try preferences(Clock())
        prefs.disabledApps = [app]
        prefs.pauseAutomaticChecking(for: app, duration: .fifteenMinutes)
        prefs.pauseAutomaticChecking(for: otherApp, duration: .oneHour)
        prefs.resumeAutomaticChecking(for: app)
        prefs.resumeAutomaticChecking(for: app)
        XCTAssertNil(prefs.automaticPauseExpiration(for: app))
        XCTAssertNotNil(prefs.automaticPauseExpiration(for: otherApp))
        XCTAssertFalse(prefs.checkingEnabled(for: app, automatic: true))
        XCTAssertFalse(prefs.checkingEnabled(for: app, automatic: false))
        XCTAssertEqual(defaults.stringArray(forKey: "disabledApps"), [app])
        prefs.disabledApps = []
        XCTAssertTrue(prefs.checkingEnabled(for: app, automatic: true))
        XCTAssertFalse(prefs.checkingEnabled(for: otherApp, automatic: true))
    }

    func testPersistenceReloadContainsOnlyBundleIDsAndExpirations() async throws {
        let clock = Clock()
        let (prefs, defaults, suite) = try preferences(clock)
        var before = defaults.persistentDomain(forName: suite) ?? [:]
        before.removeValue(forKey: "automaticAppPauses")
        prefs.pauseAutomaticChecking(for: app, duration: .fifteenMinutes)
        prefs.pauseAutomaticChecking(for: otherApp, duration: .oneHour)
        let stored = try XCTUnwrap(defaults.dictionary(forKey: "automaticAppPauses") as? [String: Date])
        XCTAssertEqual(stored, [app: clock.date.addingTimeInterval(900), otherApp: clock.date.addingTimeInterval(3600)])
        var after = defaults.persistentDomain(forName: suite) ?? [:]
        after.removeValue(forKey: "automaticAppPauses")
        XCTAssertEqual(NSDictionary(dictionary: after), NSDictionary(dictionary: before), "Pausing must not save text or change other preferences.")
        let reloadedDefaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        let restored = Preferences(defaults: reloadedDefaults, now: { clock.date }, permissionGranted: false)
        XCTAssertEqual(restored.automaticAppPauses, stored)
        XCTAssertFalse(restored.checkingEnabled(for: app, automatic: true))
        restored.resumeAutomaticChecking(for: app)
        let resumed = Preferences(defaults: reloadedDefaults, now: { clock.date }, permissionGranted: false)
        XCTAssertNil(resumed.automaticPauseExpiration(for: app))
        XCTAssertNotNil(resumed.automaticPauseExpiration(for: otherApp))
    }

    func testReloadRemovesExpiredAndMalformedEntries() async throws {
        let clock = Clock()
        let (_, defaults, _) = try preferences(clock)
        let expiry = clock.date.addingTimeInterval(3600)
        let malformed: [String: Any] = [app: expiry, otherApp: clock.date, "": expiry, "com.example.invalid": "not-an-expiration"]
        defaults.set(malformed, forKey: "automaticAppPauses")
        let restored = Preferences(defaults: defaults, now: { clock.date }, permissionGranted: false)
        XCTAssertEqual(restored.automaticAppPauses, [app: expiry])
        XCTAssertEqual(defaults.dictionary(forKey: "automaticAppPauses") as? [String: Date], [app: expiry])
        restored.pauseAutomaticChecking(for: "", duration: .oneHour)
        XCTAssertEqual(restored.automaticAppPauses, [app: expiry])
        clock.date = expiry
        let expired = Preferences(defaults: defaults, now: { clock.date }, permissionGranted: false)
        XCTAssertTrue(expired.automaticAppPauses.isEmpty)
        XCTAssertTrue(expired.checkingEnabled(for: app, automatic: true))
        XCTAssertEqual(defaults.dictionary(forKey: "automaticAppPauses")?.count, 0)
    }

    func testExpiryPublishesCleanupForAutomaticReattachment() async throws {
        let clock = Clock()
        let (prefs, defaults, _) = try preferences(clock)
        prefs.pauseAutomaticChecking(for: app, duration: .fifteenMinutes)
        prefs.pauseAutomaticChecking(for: otherApp, duration: .oneHour)
        var changes: [[String: Date]] = []
        let subscription = prefs.$automaticAppPauses.dropFirst().sink { changes.append($0) }
        defer { subscription.cancel() }
        clock.date = clock.date.addingTimeInterval(900)
        prefs.refreshAutomaticAppPauses()
        XCTAssertEqual(changes.count, 1)
        XCTAssertNil(changes.last?[app])
        XCTAssertNotNil(changes.last?[otherApp])
        XCTAssertNil(prefs.automaticAppPauses[app])
        XCTAssertNotNil(prefs.automaticAppPauses[otherApp])
        XCTAssertEqual(defaults.dictionary(forKey: "automaticAppPauses") as? [String: Date], prefs.automaticAppPauses)
    }

    func testTemporaryPausePreservesExplicitChecksAndGlobalAutomaticControls() async throws {
        let clock = Clock()
        let (prefs, _, _) = try preferences(clock)
        prefs.pauseAutomaticChecking(for: app, duration: .fifteenMinutes)
        XCTAssertTrue(prefs.checkingEnabled(for: app, automatic: false))
        prefs.paused = true
        prefs.resumeAutomaticChecking(for: app)
        XCTAssertFalse(prefs.checkingEnabled(for: app, automatic: true))
        XCTAssertTrue(prefs.checkingEnabled(for: app, automatic: false))
        prefs.paused = false; prefs.passive = false
        XCTAssertFalse(prefs.checkingEnabled(for: app, automatic: true))
        XCTAssertTrue(prefs.checkingEnabled(for: app, automatic: false))
        prefs.passive = true; prefs.onboardingCompleted = false
        XCTAssertFalse(prefs.checkingEnabled(for: app, automatic: true))
        prefs.onboardingCompleted = true; prefs.disabledApps = [app]
        XCTAssertFalse(prefs.checkingEnabled(for: app, automatic: false))
    }

    func testPendingAsyncResultRechecksNewPauseButExplicitCheckStillWorks() async throws {
        let (prefs, _, _) = try preferences(Clock())
        XCTAssertTrue(prefs.checkingEnabled(for: app, automatic: true))
        let (automatic, releaseAutomatic) = try await pendingEligibility(prefs, bundle: app)
        let (explicit, releaseExplicit) = try await pendingEligibility(prefs, bundle: app, automatic: false)
        prefs.pauseAutomaticChecking(for: app, duration: .fifteenMinutes)
        releaseAutomatic.resume(); releaseExplicit.resume()
        let automaticAllowed = await automatic.value, explicitAllowed = await explicit.value
        XCTAssertFalse(automaticAllowed, "A pending automatic result must not use eligibility captured before the pause.")
        XCTAssertTrue(explicitAllowed)
    }

    func testPendingAsyncResultRechecksPermanentOptOut() async throws {
        let (prefs, _, _) = try preferences(Clock())
        let (pending, release) = try await pendingEligibility(prefs, bundle: app, automatic: false)
        prefs.disabledApps = [app]
        release.resume()
        let allowed = await pending.value
        XCTAssertFalse(allowed, "Explicit checks do not bypass permanent privacy opt-outs.")
    }
}
