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
    static func range(_ element: AXUIElement) -> NSRange? { isDocsText(element) ? docsSelection(element) : rawRange(element) }
    static func setRange(_ element: AXUIElement, _ range: NSRange) -> Bool {
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
    static func forgetFocus() { verdicts = []; resolved = nil; forgetDocs(); forgetWeb() }
    /// Several attributes in one round trip to the app; any that fail come back nil.
    static func multiple(_ element: AXUIElement, _ attributes: [String]) -> [CFTypeRef?] {
        var values: CFArray?
        guard AXUIElementCopyMultipleAttributeValues(element, attributes as CFArray, [], &values) == .success, let array = values as? [AnyObject], array.count == attributes.count else { return attributes.map { get(element, $0) } }
        return array.map { value in CFGetTypeID(value) == AXValueGetTypeID() && AXValueGetType(value as! AXValue) == .axError ? nil : value }
    }
    static func focusedText(_ app: NSRunningApplication) -> AXUIElement? {
        guard let focused = focused(app), !isSecure(focused) else { return nil }
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
    /// Set only by headless tests: the writing space this snapshot was read from, validated and patched directly because Accessibility needs an on-screen, key window.
    var headlessEditor: NSTextView?
    /// The Studio writing space: the card is a key window of this same app, so the app's focus is then the card, not the editor.
    var own: Bool { app.processIdentifier == ProcessInfo.processInfo.processIdentifier }
    var bundle: String { app.bundleIdentifier ?? "pid.\(app.processIdentifier)" }
    /// How far a mark's re-measured position may drift before it is dropped: Docs positions are rebuilt from the caret, so they move a point or two with it.
    var markDrift: CGFloat { docs ? 4 : 1.5 }
    static func capture(passive: Bool = false) throws -> SelectionSnapshot {
        guard AXIsProcessTrusted() else { throw ParzrError.message("Allow Accessibility to use Parzr in your editors.") }
        guard let app = SelfTestTarget.watched, let element = AX.focusedText(app),
              Compat.allowsCapture(appPID: app.processIdentifier, ownPID: ProcessInfo.processInfo.processIdentifier, identifier: AX.string(element, kAXIdentifierAttribute)) else { throw ParzrError.message("Select text in an editor, then press your Parzr shortcut.") }
        guard !AX.isSecure(element), !IsSecureEventInputEnabled() else { throw ParzrError.message("Parzr does not read secure fields.") }
        guard Preferences.shared.enabled(for: app.bundleIdentifier ?? "") else { throw ParzrError.message("Parzr is disabled for this app. Enable it in Apps settings.") }
        if passive, Compat.isVSCode(app.bundleIdentifier), !Compat.isProseFile(windowTitle: AX.windowTitle(app, element)) { throw ParzrError.message("No supported typing context.") }
        guard let selectedRange = AX.selection(element) else { throw ParzrError.message("This editor hides its selection. Use the Parzr editor extension, or copy text into the playground.") }
        let full = AX.text(element)
        let docs = AX.isDocsText(element)
        // Docs with braille support off: only zero-width characters here, so the explicit check falls back to copying.
        if docs, Compat.docsTextHidden(full) { throw ParzrError.message("Select the words you want to improve, then try again.") }
        var selection = selectedRange
        // Docs' own selected text lacks the paragraph breaks its ranges skip, so its text always comes from the value.
        var text = docs ? "" : AX.string(element, kAXSelectedTextAttribute) ?? ""
        if passive {
            guard let full, selectedRange.location <= (full as NSString).length,
                  selectedRange.length <= (full as NSString).length - selectedRange.location,
                  full.utf8.count <= 262_144 else { throw ParzrError.message("No supported typing context.") }
            selection = selectedRange.length == 0 ? (full as NSString).paragraphRange(for: selectedRange) : selectedRange
            // Pasted paragraphs commonly end in a newline, leaving the caret in an
            // empty paragraph. Keep the just-written paragraph eligible for marks.
            if selectedRange.length == 0, selection.length == 0, selectedRange.location == (full as NSString).length, selectedRange.location > 0 {
                selection = (full as NSString).paragraphRange(for: NSRange(location: selectedRange.location - 1, length: 0))
            }
            guard selection.length <= 8192 else { throw ParzrError.message("Paragraph exceeds passive-analysis limit.") }
            text = (full as NSString).substring(with: selection)
        } else if text.isEmpty, let full, selectedRange.location <= (full as NSString).length, selectedRange.length <= (full as NSString).length - selectedRange.location {
            text = (full as NSString).substring(with: selectedRange)
        }
        guard !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty, selection.length > 0 else { throw ParzrError.message("Select the words you want to improve, then try again.") }
        guard text.utf8.count <= 65_536, text.utf16.count == selection.length else { throw ParzrError.message("This selection is too large or this editor reports inconsistent ranges. Copy it into the playground.") }
        return SelectionSnapshot(app: app, element: element, selection: selection, expectedSelection: selectedRange, text: text, fullText: full,
                                 bounds: AX.bounds(element, selection) ?? (Compat.isVSCode(app.bundleIdentifier) ? AX.anchor(element) : nil), richText: docs ? nil : AX.attributed(element, selection), copied: false,
                                 // Docs always patches by select-then-type (the settable-text path is a silent no-op there).
                                 canPatch: full != nil && ReplacePlan.first(textSettable: AX.settable(element, kAXSelectedTextAttribute), rangeSettable: AX.canSelect(element), docs: docs) != nil, docs: docs)
    }
    /// Explicit checks only: reads the selection via Cmd+C when AX cannot. Restores the clipboard; never logs or stores the text.
    static func captureByCopy() async throws -> SelectionSnapshot {
        guard AXIsProcessTrusted() else { throw ParzrError.message("Allow Accessibility to use Parzr in your editors.") }
        guard let app = NSWorkspace.shared.frontmostApplication, app.bundleIdentifier != Bundle.main.bundleIdentifier,
              !IsSecureEventInputEnabled() else { throw ParzrError.message("Parzr does not read secure fields.") }
        guard Preferences.shared.enabled(for: app.bundleIdentifier ?? "") else { throw ParzrError.message("Parzr is disabled for this app. Enable it in Apps settings.") }
        let element = AX.focusedText(app) ?? AX.focused(app) ?? AXUIElementCreateApplication(app.processIdentifier)
        guard !AX.isSecure(element) else { throw ParzrError.message("Parzr does not read secure fields.") }
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

    func validate() throws {
        if let editor = headlessEditor {
            guard editor.string == fullText, editor.selectedRange() == expectedSelection else { throw ParzrError.message("Your selection changed. Select the text again.") }
            return
        }
        if copied {
            guard !app.isTerminated, app == SelfTestTarget.watched, !IsSecureEventInputEnabled() else { throw ParzrError.message("Your selection changed. Select the text again.") }
            return
        }
        guard !app.isTerminated, !IsSecureEventInputEnabled(), !AX.isSecure(element),
              own || AX.focusedText(app).map({ CFEqual($0, element) }) == true,
              let current = AX.selection(element), current == expectedSelection || (expectedSelection.length == 0 && current.length == 0) else {
            throw ParzrError.message("Your selection changed. Select the text again.")
        }
        if let fullText {
            guard AX.text(element) == fullText else { throw ParzrError.message("Your text changed. Select it again.") }
        } else {
            guard AX.string(element, kAXSelectedTextAttribute) == text else { throw ParzrError.message("Your selection changed. Select it again.") }
        }
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
        guard let richText, richText.string == text else { return [] }
        return Self.protectedSpans(in: richText) + (Compat.isXcode(bundle) ? Compat.codeProtectedSpans(in: richText) : [])
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
        try validate(); try EditPlan.validate(edits, in: text)
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
            // Verify between every range patch; never replace the entire document.
            guard AX.text(element) == expected else {
                throw ParzrError.message("The editor changed during replacement. \(applied) edits applied; use the editor's Undo to revert.")
            }
            let global = NSRange(location: selection.location + edit.start_utf16, length: edit.end_utf16 - edit.start_utf16)
            let next = NSMutableString(string: expected); next.replaceCharacters(in: global, with: edit.replacement)
            do { try await AX.replace(element, in: app, range: global, with: edit.replacement, before: expected, expected: next as String) }
            catch {
                _ = AX.select(element, expectedSelection)
                throw ParzrError.message("\(error.localizedDescription) \(applied) edits applied; use the editor's Undo if needed.")
            }
            expected = next as String
            applied += 1
        }
        guard AX.text(element) == expected else { throw ParzrError.message("The editor did not confirm the final edit. Check your text before continuing.") }
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
                await AX.docsMoveCaret(app, by: ((expected as NSString).substring(with: span).count) * (target >= after ? 1 : -1))
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
