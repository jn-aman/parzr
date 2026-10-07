import Combine
import Contacts
import SwiftUI

enum OnboardingStep: Int, CaseIterable {
    case welcome, accessibility, contacts, login, tryIt, done
    var next: OnboardingStep? { Self(rawValue: rawValue + 1) }
    var previous: OnboardingStep? { Self(rawValue: rawValue - 1) }
}

/// Step logic with no UI, so it can be tested: what shows first, and when Next is allowed.
enum OnboardingFlow {
    static let sample = "i recieved your mesage, can you chek it?"
    enum ContactsState: Equatable { case allowed, denied, notAsked }
    /// First launch, or Accessibility missing (revoked, or skipped last time).
    static func shouldShow(completed: Bool, granted: Bool) -> Bool { !completed || !granted }
    /// A returning user who still lacks Accessibility lands straight on that step; everyone else starts at the welcome.
    static func firstStep(completed: Bool, granted: Bool) -> OnboardingStep { completed && !granted ? .accessibility : .welcome }
    /// Accessibility is the one step that waits: Next stays off until macOS reports the grant. There is no skip; setup is mandatory.
    static func canAdvance(from step: OnboardingStep, granted: Bool) -> Bool { step.next != nil && (step != .accessibility || granted) }
    static func contactsState(_ status: CNAuthorizationStatus) -> ContactsState { status == .authorized ? .allowed : status == .denied || status == .restricted ? .denied : .notAsked }
}

@MainActor
final class OnboardingModel: ObservableObject {
    @Published var step: OnboardingStep
    @Published var draft = OnboardingFlow.sample
    let preferences: Preferences
    /// Runs the live "Try it" field; separate from the editor window's model so the two never share a draft.
    let editor = AppModel()
    /// Snapshots only: pretend Accessibility is (not) granted without touching macOS.
    var previewGranted: Bool?
    var granted: Bool { previewGranted ?? preferences.permissionGranted }
    var canAdvance: Bool { OnboardingFlow.canAdvance(from: step, granted: granted) }
    init(preferences: Preferences = .shared, step: OnboardingStep? = nil) {
        self.preferences = preferences
        self.step = step ?? OnboardingFlow.firstStep(completed: preferences.onboardingCompleted, granted: preferences.permissionGranted)
    }
    func next() { if canAdvance, let next = step.next { step = next } }
    func back() { if let previous = step.previous { step = previous } }
    /// Start writing on the last step. Closing the window any other way leaves setup unfinished.
    func complete() { preferences.onboardingCompleted = true }
}
