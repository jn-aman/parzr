import AppKit
import os
import ParzrCore

/// Why applying a fix stopped. Each case has its own wording for the card, and its raw value is what the apply log records,
/// so a failure in the field can be read back with
/// `log show --last 1h --predicate 'subsystem == "app.parzr.desktop" AND category == "apply"' --info --debug`.
enum ApplyFailure: String, Equatable, CaseIterable {
    case checkingOff, editorClosed, editorNotInFront, secureInput, secureField
    /// Another text field has the keyboard: Parzr never moves it back, the writer chose that field.
    case focusElsewhere
    /// No text field has the keyboard and Parzr could not put it back in the one the fix belongs to.
    case focusLost
    /// The field the fix belongs to is gone (the page rebuilt it) and no field with the same text and place took over.
    case editorUnavailable
    /// The field can no longer be edited (it became read-only, or the host rules now block it).
    case notEditable
    case textChanged
    /// Explicit checks only: the writer's own selection moved. Inline marks have no selection of the writer's to lose.
    case selectionChanged
    case rangeRefused, selectionNotHeld, docsNotSelected, notAccepted, changedDuring, finalUnconfirmed

    /// `automatic`: the fix came from an inline mark (the writer selected nothing), so nothing may talk about "your selection".
    func message(automatic: Bool) -> String {
        switch self {
        case .checkingOff: "Checking is paused or disabled for this app."
        case .editorClosed: "The app you were writing in has closed."
        case .editorNotInFront: "Your editor is no longer in front. Switch back to it, then try again."
        case .secureInput: "Secure input is on, so macOS hides typing from other apps. Close any open password prompt, then try again."
        case .secureField: "Parzr does not edit secure fields."
        case .focusElsewhere: automatic ? "You’re typing in a different field now. Click back into this text, then try again."
                                        : "You moved to a different text field. Select the text again."
        case .focusLost: "Parzr couldn’t get back into your text field. Click into it, then try again."
        case .editorUnavailable: "This text field was rebuilt by the page. Click into it so Parzr can check it again."
        case .notEditable: "This field can’t be edited right now."
        case .textChanged: automatic ? "The text changed after Parzr checked it. Keep writing and Parzr will check it again."
                                     : "Your text changed. Select it again."
        // Reached for an inline mark only outside an apply (a caret move retires a pending result); the writer selected nothing.
        case .selectionChanged: automatic ? "You moved on in this text after Parzr checked it. Parzr will check it again."
                                          : "Your selection changed. Select the text again."
        case .rangeRefused: "The editor didn’t let Parzr select the words to fix."
        case .selectionNotHeld: "The editor didn’t select the words to fix, so nothing was typed."
        case .docsNotSelected: "Docs didn’t highlight the words to fix, so nothing was typed. Try again."
        case .notAccepted: "The editor didn’t accept the change."
        case .changedDuring: "The text changed while Parzr was editing it."
        case .finalUnconfirmed: "The editor did not confirm the final edit. Check your text before continuing."
        }
    }
}

/// An apply failure with the words the card shows. `failure` stays attached through the extra sentence `apply` adds (edits applied, Undo).
struct ApplyError: LocalizedError, Equatable {
    let failure: ApplyFailure
    let message: String
    init(_ failure: ApplyFailure, automatic: Bool) { self.failure = failure; message = failure.message(automatic: automatic) }
    init(_ failure: ApplyFailure, message: String) { self.failure = failure; self.message = message }
    var errorDescription: String? { message }
    /// The same failure with a closing sentence about what was (or was not) changed.
    func adding(_ sentence: String) -> ApplyError { ApplyError(failure, message: sentence.isEmpty ? message : "\(message) \(sentence)") }
}

/// Where the keyboard is when a fix from an inline mark is about to be applied, and what to do about it. Pure, so the decisions are unit-tested.
///
/// A click on the card makes Parzr's panel the key window. The writer's app stays frontmost, but its own window is no longer key. Chromium
/// (Brave, Chrome, Edge, Arc, Slack, Notion's desktop app) reports a focused element only while it has the keyboard (measured for a background
/// Chromium; a key panel of another app over it is expected to read the same), so until the card hands the keyboard back the editor can read as
/// unfocused, and typed keys posted to it would reach no field.
enum ApplyFocus {
    /// What the app's focus resolves to, compared with the field the fix was checked in.
    enum Seen: Equatable {
        /// No writable field has focus (the card has the keyboard, or the page itself is focused).
        case none
        case captured
        /// A different element with exactly the checked text in exactly the same place: the page rebuilt the same field.
        case standIn
        /// Another writable field.
        case other
    }
    enum Step: Equatable { case proceed, wait, restore, fail(ApplyFailure) }
    /// The checked field itself, read while nothing has focus: still the checked text and still an editor, gone (the page rebuilt or removed it),
    /// changed, or no longer editable.
    enum Field: Equatable { case usable, gone, changed, readOnly }
    /// Polls, `pollInterval` apart: about 0.8 s for the editor's window to take the keyboard back once the card is out of the way.
    static let attempts = 20
    static let pollInterval = 40
    /// After this many polls with nothing focused, focus is put back in the field once (it is the field the writer asked to fix).
    static let restoreAfter = 6
    /// A different field must be seen this many polls in a row before it counts (one transient read while the window comes back is ignored).
    static let otherSettles = 3
    /// How far (points) a rebuilt field's range may sit from where the checked range was measured.
    static let standInTolerance: CGFloat = 3

    static func seen<Element>(captured: Element, focus: Element?, same: (Element, Element) -> Bool, isStandIn: (Element) -> Bool) -> Seen {
        guard let focus else { return .none }
        if same(focus, captured) { return .captured }
        return isStandIn(focus) ? .standIn : .other
    }
    /// `attempt` counts from 0; `others` is how many polls in a row saw another field; `field` is read only while nothing has focus. Focus is put
    /// back only into a field that still reads the checked text and is still an editor.
    static func step(seen: Seen, attempt: Int, others: Int, restored: Bool, field: Field) -> Step {
        switch seen {
        case .captured, .standIn: return .proceed
        case .other: return others >= otherSettles || attempt + 1 >= attempts ? .fail(.focusElsewhere) : .wait
        case .none:
            switch field {
            case .changed: return .fail(.textChanged)
            case .readOnly: return .fail(.notEditable)
            case .gone: return attempt + 1 >= attempts ? .fail(.editorUnavailable) : .wait   // a rebuilt field may still take focus
            case .usable:
                if !restored, attempt >= restoreAfter { return .restore }
                return attempt + 1 >= attempts ? .fail(.focusLost) : .wait
            }
        }
    }
    /// A field that took over from the checked one: the same text, and the checked range measures where it was measured at check time.
    /// Without geometry on both sides nothing can show it is the same place, so it is not accepted.
    static func isStandIn(text: String?, expected: String?, bounds: CGRect?, captured: CGRect?) -> Bool {
        guard let text, let expected, text == expected, let bounds, let captured else { return false }
        return abs(bounds.minX - captured.minX) <= standInTolerance && abs(bounds.minY - captured.minY) <= standInTolerance
            && abs(bounds.width - captured.width) <= standInTolerance && abs(bounds.height - captured.height) <= standInTolerance
    }
    /// Which failure a check names when the snapshot's field is no longer the focused one.
    static func focusFailure(editable: Bool, focusResolves: Bool) -> ApplyFailure {
        guard editable else { return .notEditable }
        return focusResolves ? .focusElsewhere : .focusLost
    }
    /// The sentence `apply` adds to a failure: nothing changed, or how many fixes landed before it stopped.
    static func outcome(applied: Int, untouched: Bool) -> String {
        if applied == 0 && untouched { return "Nothing was changed." }
        return "\(applied) \(applied == 1 ? "edit" : "edits") applied; use the editor’s Undo if needed."
    }
}

/// Structured, text-free log of every apply: which guard stopped it, in which app and kind of field, and how focus came back.
/// Never logs the writer's text, the replacement, or anything read from the field's value.
enum ApplyLog {
    static let logger = Logger(subsystem: "app.parzr.desktop", category: "apply")
    struct Context {
        var bundle: String
        var role: String
        var automatic: Bool
        var chromium: Bool
        var docs: Bool
    }
    @discardableResult
    static func fail(_ failure: ApplyFailure, stage: String, context: Context, detail: String = "") -> ApplyError {
        logger.error("apply failed guard=\(failure.rawValue, privacy: .public) stage=\(stage, privacy: .public) app=\(context.bundle, privacy: .public) role=\(context.role, privacy: .public) automatic=\(context.automatic, privacy: .public) chromium=\(context.chromium, privacy: .public) docs=\(context.docs, privacy: .public) \(detail, privacy: .public)")
        return ApplyError(failure, automatic: context.automatic)
    }
    static func note(_ event: String, context: Context, detail: String = "") {
        logger.info("apply \(event, privacy: .public) app=\(context.bundle, privacy: .public) role=\(context.role, privacy: .public) automatic=\(context.automatic, privacy: .public) chromium=\(context.chromium, privacy: .public) \(detail, privacy: .public)")
    }
}
