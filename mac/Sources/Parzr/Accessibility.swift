import AppKit
import ApplicationServices
import Carbon
import ParzrCore

@MainActor
enum AX {
    static var gate = ActivationGate()
    static func get(_ element: AXUIElement, _ attribute: String) -> CFTypeRef? {
        var value: CFTypeRef?
        guard AXUIElementCopyAttributeValue(element, attribute as CFString, &value) == .success else { return nil }
        return value
    }
    static func string(_ element: AXUIElement, _ attribute: String) -> String? { get(element, attribute) as? String }
    /// The selection as the editor reports it. Google Docs counts offsets without paragraph breaks, so `range` converts those to value offsets.
    static func rawRange(_ element: AXUIElement) -> NSRange? {
        guard let value = get(element, kAXSelectedTextRangeAttribute), CFGetTypeID(value) == AXValueGetTypeID() else { return nil }
        var range = CFRange()
        guard AXValueGetValue(value as! AXValue, .cfRange, &range), range.location >= 0, range.length >= 0 else { return nil }
        return NSRange(location: range.location, length: range.length)
    }
    static func range(_ element: AXUIElement) -> NSRange? {
        if isDocsText(element) { return docsSelection(element) }
        // Chromium composers count their selection without some of the breaks their value has; markers on the text runs give value offsets.
        if isChromiumComposer(element) { return chromiumSelection(element) }
        return rawRange(element)
    }
    static func setRange(_ element: AXUIElement, _ range: NSRange) -> Bool {
        if !isDocsText(element), isChromiumComposer(element) { return chromiumSelect(element, range) }
        let target = isDocsText(element) ? docsSelectionRange(element, range) : range
        var range = CFRange(location: target.location, length: target.length)
        guard let value = AXValueCreate(.cfRange, &range) else { return false }
        return AXUIElementSetAttributeValue(element, kAXSelectedTextRangeAttribute as CFString, value) == .success
    }
    static func settable(_ element: AXUIElement, _ attribute: String) -> Bool {
        var flag = DarwinBoolean(false)
        return AXUIElementIsAttributeSettable(element, attribute as CFString, &flag) == .success && flag.boolValue
    }
    static func focused(_ app: NSRunningApplication) -> AXUIElement? {
        let appElement = AXUIElementCreateApplication(app.processIdentifier)
        AXUIElementSetMessagingTimeout(appElement, 0.25)
        prepare(app)
        if let value = get(appElement, kAXFocusedUIElementAttribute), CFGetTypeID(value) == AXUIElementGetTypeID() {
            let element = value as! AXUIElement
            AXUIElementSetMessagingTimeout(element, 0.25)
            return element
        }
        guard let element = systemFocused(for: app) else { return nil }
        AXUIElementSetMessagingTimeout(element, 0.25)
        return element
    }
    /// What one field's ancestry told us stays true for this long, or until focus moves; every capture, validation and mark check asks again.
    private static let verdictLifetime: TimeInterval = 1.5
    private static var verdicts: [(element: AXUIElement, secure: Bool, time: TimeInterval)] = []
    private static var resolved: (raw: AXUIElement, text: AXUIElement, time: TimeInterval)?
    /// Focus moved: forget what was learned about the previous field.
    static func forgetFocus() { verdicts = []; resolved = nil; fieldVerdicts = []; forgetDocs(); forgetWeb() }
    /// Several attributes in one round trip to the app; any that fail come back nil.
    static func multiple(_ element: AXUIElement, _ attributes: [String]) -> [CFTypeRef?] {
        var values: CFArray?
        guard AXUIElementCopyMultipleAttributeValues(element, attributes as CFArray, [], &values) == .success, let array = values as? [AnyObject], array.count == attributes.count else { return attributes.map { get(element, $0) } }
        return array.map { value in CFGetTypeID(value) == AXValueGetTypeID() && AXValueGetType(value as! AXValue) == .axError ? nil : value }
    }
    static func focusedText(_ app: NSRunningApplication, automatic: Bool = false) -> AXUIElement? {
        guard let focused = focused(app), !isSecure(focused) else { return nil }
        if automatic {
            // AX objects can become readonly without changing identity, so automatic eligibility is never cached.
            return Compat.editableAncestor(focused, eligibility: automaticEligibility, parent: { element in
                guard let parent = get(element, kAXParentAttribute), CFGetTypeID(parent) == AXUIElementGetTypeID() else { return nil }
                return (parent as! AXUIElement)
            })
        }
        let now = ProcessInfo.processInfo.systemUptime
        if let known = resolved, now - known.time < verdictLifetime, CFEqual(known.raw, focused) { return known.text }
        var cursor: AXUIElement? = focused
        // Chat/rich-text hosts often focus a text leaf inside their editable field.
        // Resolve only the focus ancestry, never unrelated text elsewhere in the app.
        for _ in 0..<8 {
            guard let current = cursor, !isSecure(current) else { return nil }
            if selection(current) != nil,
               text(current) != nil || string(current, kAXSelectedTextAttribute) != nil { resolved = (focused, current, now); return current }
            let role = string(current, kAXRoleAttribute) ?? ""
            if [kAXWindowRole, kAXApplicationRole, "AXWebArea"].contains(role) { break }
            guard let parent = get(current, kAXParentAttribute), CFGetTypeID(parent) == AXUIElementGetTypeID() else { break }
            cursor = (parent as! AXUIElement)
        }
        return nil
    }
    static func automaticEligibility(_ element: AXUIElement) -> Compat.EditorEligibility {
        guard !isSecure(element) else { return .blocked }
        let eligibility = Compat.editorEligibility(role: string(element, kAXRoleAttribute), enabled: get(element, kAXEnabledAttribute) as? Bool,
                                                   valueSettable: settable(element, kAXValueAttribute), textSettable: settable(element, kAXSelectedTextAttribute),
                                                   markerEditor: isMarkerEditor(element), search: isSearch(element))
        // Only a field that already qualifies is asked about: the rules can take it away (a one-time code box, a sign-in form), never add one.
        return eligibility == .editor ? Compat.applying(hostVerdict(element), to: eligibility) : eligibility
    }
    private static var fieldVerdicts: [(element: AXUIElement, verdict: HostRules.Verdict, time: TimeInterval)] = []
    /// What the host rules say about this field. Reads only names (labels, identifiers, DOM classes, the page URL), never the field's text;
    /// remembered for as long as the secure-field verdict, or until focus moves.
    static func hostVerdict(_ element: AXUIElement) -> HostRules.Verdict {
        let now = ProcessInfo.processInfo.systemUptime
        if let known = fieldVerdicts.first(where: { now - $0.time < verdictLifetime && CFEqual($0.element, element) }) { return known.verdict }
        let field = fieldContext(element)
        let verdict = HostRules.shared.verdict(for: field)
        fieldVerdicts = Array((fieldVerdicts.filter { now - $0.time < verdictLifetime } + [(element, verdict, now)]).suffix(16))
        return verdict
    }
    static func fieldContext(_ element: AXUIElement) -> HostRules.Field {
        let attributes = [kAXRoleAttribute, "AXPlaceholderValue", kAXDescriptionAttribute, kAXTitleAttribute, kAXIdentifierAttribute, "AXDOMIdentifier", "AXDOMClassList", kAXParentAttribute]
        func names(_ values: [CFTypeRef?]) -> (labels: [String], classes: [String]) {
            (values[1...5].compactMap { $0 as? String }.filter { !$0.isEmpty }, (values[6] as? [String] ?? []).prefix(16).map { $0 })
        }
        var pid: pid_t = 0
        _ = AXUIElementGetPid(element, &pid)
        let values = multiple(element, attributes), own = names(values)
        var field = HostRules.Field(bundle: NSRunningApplication(processIdentifier: pid)?.bundleIdentifier, role: values[0] as? String, labels: own.labels, markers: own.classes)
        var parent = values[7]
        // Up to the page or window: their titles are page and document names, not this field's.
        for _ in 0..<12 {
            guard let next = parent, CFGetTypeID(next) == AXUIElementGetTypeID() else { break }
            let current = next as! AXUIElement, values = multiple(current, attributes), role = values[0] as? String ?? ""
            if role == "AXWebArea" { field.url = (get(current, "AXURL") as? URL)?.absoluteString; break }
            if [kAXWindowRole, kAXApplicationRole].contains(role) { break }
            let around = names(values)
            if field.ancestors.count < 6 { field.ancestors.append(around.labels + around.classes) }
            parent = values[7]
        }
        return field
    }
    static func isSecure(_ element: AXUIElement) -> Bool {
        let now = ProcessInfo.processInfo.systemUptime
        if let known = verdicts.first(where: { now - $0.time < verdictLifetime && CFEqual($0.element, element) }) { return known.secure }
        // Inspect ancestors because custom secure editors may put focus on a descendant.
        var cursor: AXUIElement? = element, walked: [AXUIElement] = [], secure = false
        for _ in 0..<12 {
            guard let current = cursor else { break }
            walked.append(current)
            let values = multiple(current, [kAXRoleAttribute, kAXSubroleAttribute, kAXParentAttribute])
            let role = values[0] as? String ?? "", subrole = values[1] as? String ?? ""
            if subrole == kAXSecureTextFieldSubrole || role.lowercased().contains("secure") || subrole.lowercased().contains("password") { secure = true; break }
            if let parent = values[2], CFGetTypeID(parent) == AXUIElementGetTypeID() { cursor = (parent as! AXUIElement) } else { break }
        }
        // One walk answers for every level it passed: all clear below no secure ancestor, all secure below a secure one.
        verdicts = Array((verdicts.filter { now - $0.time < verdictLifetime } + walked.map { ($0, secure, now) }).suffix(32))
        return secure
    }
    /// AX range bounds as the API reports them: global coordinates with the origin at the top left of the primary display.
    static func axBounds(_ element: AXUIElement, _ range: NSRange) -> CGRect? {
        var cf = CFRange(location: range.location, length: range.length)
        guard let parameter = AXValueCreate(.cfRange, &cf) else { return nil }
        var value: CFTypeRef?
        guard AXUIElementCopyParameterizedAttributeValue(element, kAXBoundsForRangeParameterizedAttribute as CFString, parameter, &value) == .success,
              let value, CFGetTypeID(value) == AXValueGetTypeID() else { return nil }
        var rect = CGRect.zero
        guard AXValueGetValue(value as! AXValue, .cgRect, &rect), rect.width >= 0, rect.height > 0 else { return nil }
        return rect
    }
    /// Cocoa coordinates (origin at the bottom left of the primary display).
    static func cocoa(_ rect: CGRect) -> CGRect {
        let top = NSScreen.screens.first?.frame.maxY ?? 0
        return CGRect(x: rect.minX, y: top - rect.maxY, width: rect.width, height: rect.height)
    }
    static func bounds(_ element: AXUIElement, _ range: NSRange) -> CGRect? {
        if isDocsText(element) { return docsBounds(element, range).map(cocoa) }
        // Chromium contenteditable composers answer with an empty rect; their text runs carry the geometry (see WebGeometry).
        return (axBounds(element, range) ?? webBounds(element, range)).map(cocoa)
    }
    static func line(_ element: AXUIElement, _ index: Int) -> Int? {
        var value: CFTypeRef?
        guard AXUIElementCopyParameterizedAttributeValue(element, kAXLineForIndexParameterizedAttribute as CFString, NSNumber(value: index), &value) == .success,
              let number = value as? NSNumber, number.intValue >= 0 else { return nil }
        return number.intValue
    }
    static func lineRange(_ element: AXUIElement, _ line: Int) -> NSRange? {
        var value: CFTypeRef?
        guard AXUIElementCopyParameterizedAttributeValue(element, kAXRangeForLineParameterizedAttribute as CFString, NSNumber(value: line), &value) == .success,
              let value, CFGetTypeID(value) == AXValueGetTypeID() else { return nil }
        var range = CFRange()
        guard AXValueGetValue(value as! AXValue, .cfRange, &range), range.location >= 0, range.length > 0 else { return nil }
        return NSRange(location: range.location, length: range.length)
    }
    /// One rect per visual line of `range`; editors without line APIs only get a single-line fallback.
    static func lineRects(_ element: AXUIElement, _ range: NSRange) -> [CGRect] {
        guard range.length > 0 else { return [] }
        if isDocsText(element) { return docsLines(element, range).map(cocoa).filter { $0.width > 0 } }
        if isChromiumText(element) { return chromiumLines(element, range) }
        if let first = line(element, range.location), let last = line(element, NSMaxRange(range) - 1), last >= first, lineRange(element, first) != nil {
            var rects: [CGRect] = []
            for index in first...min(last, first + 7) {
                guard let span = lineRange(element, index) else { continue }
                let piece = NSIntersectionRange(span, range)
                if piece.length > 0, let rect = bounds(element, piece), rect.width > 0 { rects.append(rect) }
            }
            return rects
        }
        guard let rect = bounds(element, range), rect.height < 40 else { return [] }
        return [rect]
    }
    /// The visible box a field scrolls in, in AppKit coordinates: its scroll area when it sits in one (an NSTextView's own frame is the whole document), else its own frame.
    static func scrollArea(_ element: AXUIElement) -> CGRect? {
        func frame(_ element: AXUIElement) -> CGRect? {
            let values = multiple(element, [kAXPositionAttribute, kAXSizeAttribute])
            guard let p = values[0], let s = values[1], CFGetTypeID(p) == AXValueGetTypeID(), CFGetTypeID(s) == AXValueGetTypeID() else { return nil }
            var origin = CGPoint.zero, size = CGSize.zero
            guard AXValueGetValue(p as! AXValue, .cgPoint, &origin), AXValueGetValue(s as! AXValue, .cgSize, &size), size.width > 0, size.height > 0 else { return nil }
            return cocoa(CGRect(origin: origin, size: size))
        }
        var cursor: AXUIElement? = element
        for _ in 0..<4 {
            guard let current = cursor else { break }
            if string(current, kAXRoleAttribute) == kAXScrollAreaRole { return frame(current) }
            guard let parent = get(current, kAXParentAttribute), CFGetTypeID(parent) == AXUIElementGetTypeID() else { break }
            cursor = (parent as! AXUIElement)
        }
        return frame(element)
    }
    static func attributed(_ element: AXUIElement, _ range: NSRange) -> NSAttributedString? {
        var cf = CFRange(location: range.location, length: range.length)
        guard let parameter = AXValueCreate(.cfRange, &cf) else { return nil }
        var value: CFTypeRef?
        guard AXUIElementCopyParameterizedAttributeValue(element, kAXAttributedStringForRangeParameterizedAttribute as CFString, parameter, &value) == .success else { return markerAttributed(element, range) }
        return value as? NSAttributedString
    }
}

@MainActor
struct SelectionSnapshot {
    let app: NSRunningApplication
    let element: AXUIElement
    let selection: NSRange
    let expectedSelection: NSRange
    let text: String
    let fullText: String?
    let bounds: CGRect?
    let richText: NSAttributedString?
    /// True when the text came from Cmd+C because the editor exposes no AX text (canvas editors). Never patchable.
    let copied: Bool
    /// Whether the editor accepts a minimal range patch, asked once at capture: a live AX query on every card render could time out under load and grey out Apply.
    let canPatch: Bool
    /// Google Docs through its hidden text area: replacements are typed, and range geometry comes from `DocsGeometry` rather than AX bounds.
    let docs: Bool
    /// Document offsets of line breaks Chromium wrote around an inline image inside this paragraph: `text` has spaces there, and they are protected.
    var inlineBreaks: [Int] = []
    /// Automatic results keep their origin so a new pause also blocks pending display and application.
    var automatic = false
    /// Set only by headless tests: the writing space this snapshot was read from, validated and patched directly because Accessibility needs an on-screen, key window.
    var headlessEditor: NSTextView?
    var checkingEnabled: Bool { Preferences.shared.checkingEnabled(for: app.bundleIdentifier ?? "", automatic: automatic) }
    func validateCheckingEligibility(preferences: Preferences = .shared) throws {
        guard preferences.checkingEnabled(for: app.bundleIdentifier ?? "", automatic: automatic) else { throw ParzrError.message("Checking is paused or disabled for this app.") }
    }
    /// The Studio writing space: the card is a key window of this same app, so the app's focus is then the card, not the editor.
    var own: Bool { app.processIdentifier == ProcessInfo.processInfo.processIdentifier }
    var bundle: String { app.bundleIdentifier ?? "pid.\(app.processIdentifier)" }
    /// How far a mark's re-measured position may drift before it is dropped: Docs positions are rebuilt from the caret, so they move a point or two with it.
    var markDrift: CGFloat { docs ? 4 : 1.5 }
    static func capture(passive: Bool = false) throws -> SelectionSnapshot {
        guard AXIsProcessTrusted() else { throw ParzrError.message("Allow Accessibility to use Parzr in your editors.") }
        guard let app = SelfTestTarget.watched else { throw ParzrError.message("Select text in an editor, then press your Parzr shortcut.") }
        // Check app policy before resolving the focused text, which itself reads editor attributes.
        guard Preferences.shared.enabled(for: app.bundleIdentifier ?? "") else { throw ParzrError.message("Parzr is disabled for this app. Enable it in Apps settings.") }
        guard Preferences.shared.checkingEnabled(for: app.bundleIdentifier ?? "", automatic: passive) else { throw ParzrError.message("Automatic checking is paused for this app.") }
        // Password managers, authenticators and security panes are never read, on request or not.
        guard !HostRules.shared.excludesApp(app.bundleIdentifier) else { throw ParzrError.message("Parzr does not read this app.") }
        guard let element = AX.focusedText(app, automatic: passive),
              Compat.allowsCapture(appPID: app.processIdentifier, ownPID: ProcessInfo.processInfo.processIdentifier, identifier: AX.string(element, kAXIdentifierAttribute)) else { throw ParzrError.message("Select text in an editor, then press your Parzr shortcut.") }
        guard !AX.isSecure(element) else { throw ParzrError.message("Parzr does not read secure fields.") }
        if !passive, Compat.blocksExplicitCheck(bundle: app.bundleIdentifier, verdict: AX.hostVerdict(element)) { throw ParzrError.message("Parzr does not read this field.") }
        // Another app's secure input hides this plain field's typing too: name that app instead of blaming the field.
        guard !IsSecureEventInputEnabled() else { throw ParzrError.message(SecureInput.message(SecureInput.holder(watching: app) ?? .elsewhere)) }
        if passive, Compat.isVSCode(app.bundleIdentifier), !Compat.isProseFile(windowTitle: AX.windowTitle(app, element)) { throw ParzrError.message("No supported typing context.") }
        guard let selectedRange = AX.selection(element) else { throw ParzrError.message("This editor hides its selection. Use the Parzr editor extension, or copy text into the playground.") }
        let full = AX.text(element)
        let docs = AX.isDocsText(element)
        // Docs with braille support off: only zero-width characters here, so the explicit check falls back to copying.
        if docs, Compat.docsTextHidden(full) { throw ParzrError.message("Select the words you want to improve, then try again.") }
        var selection = selectedRange
        // Docs' own selected text lacks the paragraph breaks its ranges skip, and a Chromium composer's lacks its image breaks, so their text comes from the value.
        var text = docs || AX.isChromiumComposer(element) ? "" : AX.string(element, kAXSelectedTextAttribute) ?? ""
        var inlineBreaks: [Int] = []
        if passive {
            guard let full, selectedRange.location <= (full as NSString).length,
                  selectedRange.length <= (full as NSString).length - selectedRange.location,
                  full.utf8.count <= 262_144 else { throw ParzrError.message("No supported typing context.") }
            // A Chromium composer's emoji image reads as a line break; the sentence around it is one paragraph.
            let joined = selectedRange.length == 0 ? AX.chromiumParagraph(element, value: full, around: selectedRange) : nil
            selection = joined?.range ?? (selectedRange.length == 0 ? (full as NSString).paragraphRange(for: selectedRange) : selectedRange)
            inlineBreaks = joined?.inlineBreaks ?? []
            // Pasted paragraphs commonly end in a newline, leaving the caret in an
            // empty paragraph. Keep the just-written paragraph eligible for marks.
            if selectedRange.length == 0, selection.length == 0, selectedRange.location == (full as NSString).length, selectedRange.location > 0 {
                selection = (full as NSString).paragraphRange(for: NSRange(location: selectedRange.location - 1, length: 0))
            }
            guard selection.length <= 8192 else { throw ParzrError.message("Paragraph exceeds passive-analysis limit.") }
            text = WebGeometry.joining((full as NSString).substring(with: selection), origin: selection.location, breaks: inlineBreaks)
        } else if text.isEmpty, let full, selectedRange.location <= (full as NSString).length, selectedRange.length <= (full as NSString).length - selectedRange.location {
            text = (full as NSString).substring(with: selectedRange)
        }
        guard !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty, selection.length > 0 else { throw ParzrError.message("Select the words you want to improve, then try again.") }
        guard text.utf8.count <= 65_536, text.utf16.count == selection.length else { throw ParzrError.message("This selection is too large or this editor reports inconsistent ranges. Copy it into the playground.") }
        return SelectionSnapshot(app: app, element: element, selection: selection, expectedSelection: selectedRange, text: text, fullText: full,
                                 bounds: AX.bounds(element, selection) ?? (Compat.isVSCode(app.bundleIdentifier) ? AX.anchor(element) : nil), richText: docs ? nil : AX.attributed(element, selection), copied: false,
                                 // Docs always patches by select-then-type (the settable-text path is a silent no-op there).
                                 canPatch: full != nil && ReplacePlan.first(textSettable: AX.settable(element, kAXSelectedTextAttribute), rangeSettable: AX.canSelect(element), docs: docs) != nil, docs: docs, inlineBreaks: inlineBreaks, automatic: passive)
    }
    /// Explicit checks only: reads the selection via Cmd+C when AX cannot. Restores the clipboard; never logs or stores the text.
    static func captureByCopy() async throws -> SelectionSnapshot {
        guard AXIsProcessTrusted() else { throw ParzrError.message("Allow Accessibility to use Parzr in your editors.") }
        guard let app = NSWorkspace.shared.frontmostApplication, app.bundleIdentifier != Bundle.main.bundleIdentifier else { throw ParzrError.message("Parzr does not read secure fields.") }
        guard Preferences.shared.enabled(for: app.bundleIdentifier ?? "") else { throw ParzrError.message("Parzr is disabled for this app. Enable it in Apps settings.") }
        let element = AX.focusedText(app) ?? AX.focused(app) ?? AXUIElementCreateApplication(app.processIdentifier)
        guard !AX.isSecure(element) else { throw ParzrError.message("Parzr does not read secure fields.") }
        // Cmd+C goes only to an app Parzr checks and a field no rule blocks (never a password manager, a terminal or a sign-in field).
        guard Compat.allowsCopyFallback(bundle: app.bundleIdentifier, verdict: AX.hostVerdict(element), secure: false) else { throw ParzrError.message("Parzr does not read this field.") }
        guard !IsSecureEventInputEnabled() else { throw ParzrError.message(SecureInput.message(SecureInput.holder(watching: app) ?? .elsewhere)) }
        let text = try await ClipboardTransaction.copySelection(from: app.processIdentifier) ?? ""
        guard !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { throw ParzrError.message("Select the words you want to improve, then try again.") }
        guard text.utf8.count <= 65_536 else { throw ParzrError.message("This selection is too large or this editor reports inconsistent ranges. Copy it into the playground.") }
        let range = NSRange(location: 0, length: text.utf16.count)
        return SelectionSnapshot(app: app, element: element, selection: range, expectedSelection: range, text: text, fullText: nil, bounds: nil, richText: nil, copied: true, canPatch: false, docs: false)
    }
    /// Two copies of the same range may differ only by trailing newlines.
    nonisolated static func sameCopiedText(_ a: String, _ b: String) -> Bool {
        func trimmed(_ s: String) -> String { var s = s; while s.last?.isNewline == true { s.removeLast() }; return s }
        return trimmed(a) == trimmed(b)
    }

    func automaticEditorIsCurrent() -> Bool {
        guard automatic else { return true }
        if let editor = headlessEditor { return editor.isEditable }
        // The Studio card takes focus inside this app without changing its writing space.
        if own { return AX.automaticEligibility(element) == .editor }
        guard app == SelfTestTarget.watched else { return false }
        return ReplacePlan.focusMatches(element, automatic: true, resolve: { automatic in AX.focusedText(app, automatic: automatic) }, same: { CFEqual($0, $1) })
    }
    /// What the apply log records about this snapshot's field: names and flags only, never its text.
    var logContext: ApplyLog.Context {
        let headless = headlessEditor != nil
        return ApplyLog.Context(bundle: bundle, role: headless ? "headless" : AX.string(element, kAXRoleAttribute) ?? "unknown", automatic: automatic,
                                chromium: !headless && !copied && AX.isChromiumText(element), docs: docs)
    }
    /// Which guard a field that is no longer the focused editor fails: it is gone, it became read-only, another field has focus, or none does.
    private func focusFailure() -> ApplyFailure {
        if headlessEditor != nil { return .notEditable }
        if app.isTerminated { return .editorClosed }
        guard own || app == SelfTestTarget.watched else { return .editorNotInFront }
        if automatic, !own, AX.text(element) == nil { return .editorUnavailable }
        let editable = !automatic || AX.automaticEligibility(element) == .editor
        return ApplyFocus.focusFailure(editable: editable, focusResolves: AX.focusedText(app, automatic: automatic) != nil)
    }
    /// `applying`: the last check before a fix is written. Its failures go to the apply log, and an inline mark's caret is not compared then:
    /// the writer selected nothing, and the fix is placed by its offsets in the text verified here, so a caret that Chromium reports differently
    /// (or not at all) once Parzr's card has taken the keyboard is no reason to refuse.
    func validate(preferences: Preferences = .shared, applying: Bool = false) throws {
        func fail(_ failure: ApplyFailure, _ detail: String = "") -> ApplyError {
            applying ? ApplyLog.fail(failure, stage: "validate", context: logContext, detail: detail) : ApplyError(failure, automatic: automatic)
        }
        let caretMatters = !(applying && automatic)
        guard preferences.checkingEnabled(for: app.bundleIdentifier ?? "", automatic: automatic) else { throw fail(.checkingOff) }
        guard automaticEditorIsCurrent() else { throw fail(focusFailure(), "current=false") }
        if let editor = headlessEditor {
            guard editor.string == fullText else { throw fail(.textChanged) }
            guard !caretMatters || editor.selectedRange() == expectedSelection else { throw fail(.selectionChanged) }
            return
        }
        guard !app.isTerminated else { throw fail(.editorClosed) }
        guard !IsSecureEventInputEnabled() else {
            if applying { ApplyLog.fail(.secureInput, stage: "validate", context: logContext) }
            throw ApplyError(.secureInput, message: SecureInput.message(SecureInput.holder(watching: app) ?? .elsewhere))
        }
        if copied {
            guard app == SelfTestTarget.watched else { throw fail(.editorNotInFront) }
            return
        }
        guard !AX.isSecure(element) else { throw fail(.secureField) }
        guard own || automatic || AX.focusedText(app).map({ CFEqual($0, element) }) == true else { throw fail(focusFailure(), "explicit") }
        if caretMatters {
            let current = AX.selection(element)
            guard let current, current == expectedSelection || (expectedSelection.length == 0 && current.length == 0) else {
                throw fail(.selectionChanged, current == nil ? "selection=none" : "selection=moved")
            }
        }
        if let fullText {
            guard AX.text(element) == fullText else { throw fail(.textChanged) }
        } else {
            guard AX.string(element, kAXSelectedTextAttribute) == text else { throw fail(.selectionChanged, "selectedText") }
        }
    }
    /// The same check on a field that took over from this one (see `ApplyFocus.Seen.standIn`).
    func moved(to editor: AXUIElement) -> SelectionSnapshot {
        SelectionSnapshot(app: app, element: editor, selection: selection, expectedSelection: expectedSelection, text: text, fullText: fullText, bounds: bounds,
                          richText: richText, copied: copied,
                          canPatch: fullText != nil && ReplacePlan.first(textSettable: AX.settable(editor, kAXSelectedTextAttribute), rangeSettable: AX.canSelect(editor), docs: docs) != nil,
                          docs: docs, inlineBreaks: inlineBreaks, automatic: automatic)
    }
    /// Run once the card has handed the keyboard back (`AppModel.handOff`), before anything is written. The editor's window needs a moment to
    /// take the keyboard again, and Chromium reports no focused field until it has, so focus is polled rather than read once. An inline mark's
    /// field is accepted as it is, or as a rebuilt field with exactly the checked text in exactly the same place; when no field has focus, focus
    /// is put back into the mark's own field once. Another field with focus is never touched: the writer moved there. An explicit selection only
    /// waits for its field. Ends with the full pre-apply validation (text, secure input, eligibility) of the field that will be written.
    func prepareToApply() async throws -> SelectionSnapshot {
        if headlessEditor != nil || own || copied { try validate(applying: true); return self }
        let context = logContext
        guard checkingEnabled else { throw ApplyLog.fail(.checkingOff, stage: "prepare", context: context) }
        var restored = false, others = 0
        for attempt in 0..<ApplyFocus.attempts {
            guard !app.isTerminated else { throw ApplyLog.fail(.editorClosed, stage: "prepare", context: context) }
            guard app == SelfTestTarget.watched else { throw ApplyLog.fail(.editorNotInFront, stage: "prepare", context: context, detail: "attempt=\(attempt)") }
            let focus = AX.focusedText(app, automatic: automatic)
            let seen = ApplyFocus.seen(captured: element, focus: focus, same: { CFEqual($0, $1) }, isStandIn: { candidate in
                // Geometry is measured only for a field that already reads exactly the checked text.
                guard automatic, let now = AX.text(candidate), now == fullText else { return false }
                return ApplyFocus.isStandIn(text: now, expected: fullText, bounds: AX.bounds(candidate, selection), captured: bounds)
            })
            others = seen == .other ? others + 1 : 0
            if !automatic {
                // An explicit selection is the writer's own: wait for its field, and let validation name what changed if it never comes back.
                if seen == .captured || attempt + 1 == ApplyFocus.attempts { break }
                try await Task.sleep(for: .milliseconds(ApplyFocus.pollInterval)); continue
            }
            let field: ApplyFocus.Field = seen != .none ? .usable : {
                guard let now = AX.text(element) else { return .gone }
                guard now == fullText else { return .changed }
                return AX.automaticEligibility(element) == .editor ? .usable : .readOnly
            }()
            switch ApplyFocus.step(seen: seen, attempt: attempt, others: others, restored: restored, field: field) {
            case .proceed:
                var target = self
                if seen == .standIn, let focus { target = moved(to: focus); ApplyLog.note("stand-in field", context: context, detail: "attempt=\(attempt)") }
                if attempt > 0 { ApplyLog.note("focus back", context: context, detail: "attempt=\(attempt) restored=\(restored)") }
                try target.validate(applying: true)
                return target
            case .restore:
                restored = true
                ApplyLog.note("restoring focus", context: context, detail: "attempt=\(attempt)")
                AX.restoreFocus(element)
            case .wait: break
            case .fail(let failure):
                throw ApplyLog.fail(failure, stage: "prepare", context: context, detail: "attempt=\(attempt) restored=\(restored) seen=\(seen) field=\(field)")
            }
            try await Task.sleep(for: .milliseconds(ApplyFocus.pollInterval))
        }
        try validate(applying: true)
        return self
    }
    var startsSentence: Bool {
        guard let fullText, selection.location > 0, selection.location <= (fullText as NSString).length else { return true }
        let prefix = (fullText as NSString).substring(to: selection.location).trimmingCharacters(in: .whitespaces)
        return prefix.isEmpty || prefix.last.map { ".!?\n".contains($0) } == true
    }
    var endsSentence: Bool {
        guard let fullText, selection.location + selection.length < fullText.utf16.count else { return true }
        return text.trimmingCharacters(in: .whitespaces).last.map { ".!?\n".contains($0) } == true
    }
    func protectedRanges() -> [TextSpan] {
        // A joined image break is a space only in `text`: no edit may touch it.
        let breaks = inlineBreaks.filter { NSLocationInRange($0, selection) }.map { TextSpan(NSRange(location: $0 - selection.location, length: 1)) }
        let raw = inlineBreaks.isEmpty ? text : fullText.map { ($0 as NSString).substring(with: selection) } ?? text
        guard let richText, richText.string == raw else { return breaks }
        return Self.protectedSpans(in: richText) + (Compat.isXcode(bundle) ? Compat.codeProtectedSpans(in: richText) : []) + breaks
    }
    /// Links and attachments, under both the AppKit keys and the "AXLink"/"AXAttachment" keys the Accessibility API uses, plus @mention runs.
    nonisolated static func protectedSpans(in text: NSAttributedString) -> [TextSpan] {
        let keys: [NSAttributedString.Key] = [.link, .attachment, NSAttributedString.Key("AXLink"), NSAttributedString.Key("AXAttachment")]
        var ranges: [TextSpan] = []
        text.enumerateAttributes(in: NSRange(location: 0, length: text.length)) { attributes, range, _ in
            if keys.contains(where: { attributes[$0] != nil }) || (text.string as NSString).substring(with: range).hasPrefix("@") { ranges.append(TextSpan(range)) }
        }
        return ranges
    }
    func apply(_ edits: [WritingEdit]) async throws {
        try validate(applying: true); try EditPlan.validate(edits, in: text)
        if let editor = headlessEditor {
            editor.undoManager?.beginUndoGrouping()
            for edit in edits.reversed() { editor.insertText(edit.replacement, replacementRange: NSRange(location: selection.location + edit.start_utf16, length: edit.end_utf16 - edit.start_utf16)) }
            editor.undoManager?.endUndoGrouping(); editor.undoManager?.setActionName("Apply Parzr corrections")
            return
        }
        // A passive caret may have moved since the snapshot; restore it from where it is now.
        let caretStart = expectedSelection.length == 0 ? (AX.selection(element)?.location ?? expectedSelection.location) : expectedSelection.location
        guard canPatch, let fullText else { throw ParzrError.message("This editor needs paste replacement. Review the formatting notice before using Paste instead.") }
        var expected = fullText
        var applied = 0
        for edit in edits.reversed() {
            guard checkingEnabled else {
                throw ApplyLog.fail(.checkingOff, stage: "apply", context: logContext).adding(ApplyFocus.outcome(applied: applied, untouched: applied == 0))
            }
            // Verify between every range patch; never replace the entire document.
            // An editor may restyle quotes or spaces as it takes a write; plan from its text when every offset still holds.
            guard let current = ReplacePlan.adopt(AX.text(element), expected: expected) else {
                throw ApplyLog.fail(applied == 0 ? .textChanged : .changedDuring, stage: "apply", context: logContext, detail: "applied=\(applied)")
                    .adding(ApplyFocus.outcome(applied: applied, untouched: applied == 0))
            }
            expected = current
            let global = NSRange(location: selection.location + edit.start_utf16, length: edit.end_utf16 - edit.start_utf16)
            let next = NSMutableString(string: expected); next.replaceCharacters(in: global, with: edit.replacement)
            do { try await AX.replace(element, in: app, range: global, with: edit.replacement, before: expected, expected: next as String, automatic: automatic) }
            catch {
                // Nothing is claimed unchanged unless the editor still reads exactly what it read before this edit.
                let untouched = applied == 0 && AX.text(element) == expected
                _ = AX.select(element, expectedSelection)
                let failure = (error as? ApplyError) ?? ApplyError(.notAccepted, message: error.localizedDescription)
                throw failure.adding(ApplyFocus.outcome(applied: applied, untouched: untouched))
            }
            expected = next as String
            applied += 1
        }
        guard let final = AX.text(element), ReplacePlan.sameText(final, expected) else { throw ApplyLog.fail(.finalUnconfirmed, stage: "apply", context: logContext, detail: "applied=\(applied)") }
        if final.utf16.count == expected.utf16.count { expected = final }
        ApplyLog.note("applied", context: logContext, detail: "edits=\(applied)")
        FixLearning.record(edits, in: self)
        let delta = edits.reduce(0) { $0 + $1.replacement.utf16.count - $1.range.length }
        if expectedSelection.length == 0 {
            // A passive paragraph is an analysis range, not the user's selection.
            // Restore the typing caret so remaining issues can be checked again.
            let relativeCaret = caretStart - selection.location
            var caret = caretStart
            for edit in edits.reversed() {
                if relativeCaret >= edit.end_utf16 { caret += edit.replacement.utf16.count - edit.range.length }
                else if relativeCaret > edit.start_utf16 { caret = selection.location + edit.start_utf16 + edit.replacement.utf16.count }
            }
            let target = min(max(0, caret), expected.utf16.count)
            if docs, let first = edits.first {
                // The typed replacement left the caret after the earliest edit; walk it back to the writer's place (see docsMoveCaret).
                let after = min(selection.location + first.start_utf16 + first.replacement.utf16.count, expected.utf16.count)
                let span = NSRange(location: min(after, target), length: abs(target - after))
                await AX.docsMoveCaret(app, element: element, automatic: automatic, by: ((expected as NSString).substring(with: span).count) * (target >= after ? 1 : -1))
            } else {
                _ = AX.select(element, NSRange(location: target, length: 0))
            }
        } else {
            _ = AX.select(element, NSRange(location: selection.location, length: selection.length + delta))
        }
    }
    func metadata() -> String {
        if headlessEditor != nil { return "Headless writing space.\nText is excluded from this report." }
        var attributes: CFArray?; var parameters: CFArray?
        AXUIElementCopyAttributeNames(element, &attributes)
        AXUIElementCopyParameterizedAttributeNames(element, &parameters)
        return "App: \(bundle)\nRole: \(AX.string(element, kAXRoleAttribute) ?? "unknown")\nSubrole: \(AX.string(element, kAXSubroleAttribute) ?? "none")\nSelection range: available\nFull value: \(fullText != nil)\nMinimal range patch: \(canPatch)\nAttributed text: \(richText != nil)\nRange bounds: \(bounds != nil)\nAttributes: \((attributes as? [String] ?? []).joined(separator: ", "))\nParameterized: \((parameters as? [String] ?? []).joined(separator: ", "))\nText is excluded from this report."
    }
}
