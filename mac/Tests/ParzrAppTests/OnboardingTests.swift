import Contacts
import XCTest
@testable import Parzr

@MainActor
final class OnboardingTests: XCTestCase {
    private func prefs() throws -> (Preferences, () -> Void) {
        let name = "app.parzr.tests.onboarding"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: name)); defaults.removePersistentDomain(forName: name)
        return (Preferences(defaults: defaults), { defaults.removePersistentDomain(forName: name) })
    }
    func testFirstStepAndWhenToShow() {
        XCTAssertEqual(OnboardingFlow.firstStep(completed: false, granted: false), .welcome)
        XCTAssertEqual(OnboardingFlow.firstStep(completed: false, granted: true), .welcome)
        XCTAssertEqual(OnboardingFlow.firstStep(completed: true, granted: false), .accessibility, "a returning user without the grant lands on that step")
        XCTAssertEqual(OnboardingFlow.firstStep(completed: true, granted: true), .welcome)
        XCTAssertTrue(OnboardingFlow.shouldShow(completed: false, granted: true))
        XCTAssertTrue(OnboardingFlow.shouldShow(completed: false, granted: false))
        XCTAssertTrue(OnboardingFlow.shouldShow(completed: true, granted: false))
        XCTAssertFalse(OnboardingFlow.shouldShow(completed: true, granted: true))
    }
    func testNextIsBlockedOnlyOnAccessibilityUntilGranted() {
        for step in OnboardingStep.allCases {
            XCTAssertEqual(OnboardingFlow.canAdvance(from: step, granted: true), step != .done)
            XCTAssertEqual(OnboardingFlow.canAdvance(from: step, granted: false), step != .done && step != .accessibility)
        }
    }
    func testStepOrderAndBounds() {
        XCTAssertEqual(OnboardingStep.allCases, [.welcome, .accessibility, .contacts, .login, .tryIt, .done])
        XCTAssertNil(OnboardingStep.welcome.previous); XCTAssertNil(OnboardingStep.done.next)
        XCTAssertEqual(OnboardingStep.contacts.previous, .accessibility); XCTAssertEqual(OnboardingStep.contacts.next, .login)
    }
    func testModelNavigationFollowsTheLiveGrant() throws {
        let (prefs, cleanup) = try prefs(); defer { cleanup() }
        prefs.permissionGranted = false
        let model = OnboardingModel(preferences: prefs)
        XCTAssertEqual(model.step, .welcome)
        model.next(); XCTAssertEqual(model.step, .accessibility)
        XCTAssertFalse(model.canAdvance); model.next(); XCTAssertEqual(model.step, .accessibility, "Next does nothing without the grant")
        prefs.permissionGranted = true // the watcher or trust notification flips this while the window is open
        XCTAssertTrue(model.canAdvance); model.next(); XCTAssertEqual(model.step, .contacts)
        model.back(); XCTAssertEqual(model.step, .accessibility)
        prefs.permissionGranted = false
        model.skip(); XCTAssertEqual(model.step, .contacts, "Skip for now moves on without the grant")
        model.step = .done; model.next(); XCTAssertEqual(model.step, .done)
        model.step = .welcome; model.back(); XCTAssertEqual(model.step, .welcome)
    }
    func testModelPreviewOverridesTheGrantAndFirstStepFollowsState() throws {
        let (prefs, cleanup) = try prefs(); defer { cleanup() }
        prefs.permissionGranted = false; prefs.onboardingCompleted = true
        XCTAssertEqual(OnboardingModel(preferences: prefs).step, .accessibility)
        XCTAssertEqual(OnboardingModel(preferences: prefs, step: .tryIt).step, .tryIt)
        let model = OnboardingModel(preferences: prefs, step: .accessibility)
        model.previewGranted = true; XCTAssertTrue(model.granted); XCTAssertTrue(model.canAdvance)
    }
    func testCompletionPersistsAcrossLaunches() throws {
        let name = "app.parzr.tests.onboarding.persist"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: name)); defaults.removePersistentDomain(forName: name)
        defer { defaults.removePersistentDomain(forName: name) }
        let first = Preferences(defaults: defaults)
        XCTAssertFalse(first.onboardingCompleted)
        let model = OnboardingModel(preferences: first); model.complete()
        XCTAssertTrue(first.onboardingCompleted)
        XCTAssertTrue(Preferences(defaults: defaults).onboardingCompleted)
    }
    func testContactsStateMapsAuthorization() {
        XCTAssertEqual(OnboardingFlow.contactsState(.authorized), .allowed)
        XCTAssertEqual(OnboardingFlow.contactsState(.denied), .denied)
        XCTAssertEqual(OnboardingFlow.contactsState(.restricted), .denied)
        XCTAssertEqual(OnboardingFlow.contactsState(.notDetermined), .notAsked)
    }
    func testSampleHasTheTypos() {
        XCTAssertEqual(OnboardingFlow.sample, "i recieved your mesage, can you chek it?")
    }
}
