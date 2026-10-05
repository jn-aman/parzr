import AppKit
import ApplicationServices
import Carbon
import ParzrCore

@MainActor
enum AX {
    private static var preparedApplications: Set<pid_t> = []
    static func get(_ element: AXUIElement, _ attribute: String) -> CFTypeRef? {
        var value: CFTypeRef?
        guard AXUIElementCopyAttributeValue(element, attribute as CFString, &value) == .success else { return nil }
        return value
    }
    static func string(_ element: AXUIElement, _ attribute: String) -> String? { get(element, attribute) as? String }
    static func range(_ element: AXUIElement) -> NSRange? {
        guard let value = get(element, kAXSelectedTextRangeAttribute), CFGetTypeID(value) == AXValueGetTypeID() else { return nil }
        var range = CFRange()
        guard AXValueGetValue(value as! AXValue, .cfRange, &range), range.location >= 0, range.length >= 0 else { return nil }
        return NSRange(location: range.location, length: range.length)
    }
    static func setRange(_ element: AXUIElement, _ range: NSRange) -> Bool {
        var range = CFRange(location: range.location, length: range.length)
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
        // Electron's documented assistive-technology switch exposes nested composers.
        // Unsupported apps simply refuse the attribute. Never change the user's drafts.
        if !preparedApplications.contains(app.processIdentifier) {
            if preparedApplications.count >= 128 { preparedApplications.removeAll() }
            if AXUIElementSetAttributeValue(appElement, "AXManualAccessibility" as CFString, kCFBooleanTrue) == .success {
                preparedApplications.insert(app.processIdentifier)
            }
        }
        guard let value = get(appElement, kAXFocusedUIElementAttribute), CFGetTypeID(value) == AXUIElementGetTypeID() else { return nil }
        let element = value as! AXUIElement
        AXUIElementSetMessagingTimeout(element, 0.25)
        return element
    }
    static func focusedText(_ app: NSRunningApplication) -> AXUIElement? {
        guard let focused = focused(app), !isSecure(focused) else { return nil }
        var cursor: AXUIElement? = focused
        // Chat/rich-text hosts often focus a text leaf inside their editable field.
        // Resolve only the focus ancestry, never unrelated text elsewhere in the app.
        for _ in 0..<8 {
            guard let current = cursor, !isSecure(current) else { return nil }
            if range(current) != nil,
               string(current, kAXValueAttribute) != nil || string(current, kAXSelectedTextAttribute) != nil { return current }
            let role = string(current, kAXRoleAttribute) ?? ""
            if [kAXWindowRole, kAXApplicationRole, "AXWebArea"].contains(role) { break }
            guard let parent = get(current, kAXParentAttribute), CFGetTypeID(parent) == AXUIElementGetTypeID() else { break }
            cursor = (parent as! AXUIElement)
        }
        return nil
    }
    static func isSecure(_ element: AXUIElement) -> Bool {
        // Inspect ancestors because custom secure editors may put focus on a descendant.
        var cursor: AXUIElement? = element
        for _ in 0..<12 {
            guard let current = cursor else { break }
            let role = string(current, kAXRoleAttribute) ?? ""
            let subrole = string(current, kAXSubroleAttribute) ?? ""
            if subrole == kAXSecureTextFieldSubrole || role.lowercased().contains("secure") || subrole.lowercased().contains("password") { return true }
            if let parent = get(current, kAXParentAttribute), CFGetTypeID(parent) == AXUIElementGetTypeID() { cursor = (parent as! AXUIElement) } else { break }
        }
        return false
    }
    static func bounds(_ element: AXUIElement, _ range: NSRange) -> CGRect? {
        var cf = CFRange(location: range.location, length: range.length)
        guard let parameter = AXValueCreate(.cfRange, &cf) else { return nil }
        var value: CFTypeRef?
        guard AXUIElementCopyParameterizedAttributeValue(element, kAXBoundsForRangeParameterizedAttribute as CFString, parameter, &value) == .success,
              let value, CFGetTypeID(value) == AXValueGetTypeID() else { return nil }
        var rect = CGRect.zero
        guard AXValueGetValue(value as! AXValue, .cgRect, &rect), rect.width >= 0, rect.height > 0 else { return nil }
        // AX global coordinates originate at the top of the primary display.
        let top = NSScreen.screens.first?.frame.maxY ?? 0
        return CGRect(x: rect.minX, y: top - rect.maxY, width: rect.width, height: rect.height)
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
        guard AXUIElementCopyParameterizedAttributeValue(element, kAXAttributedStringForRangeParameterizedAttribute as CFString, parameter, &value) == .success else { return nil }
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
    var bundle: String { app.bundleIdentifier ?? "pid.\(app.processIdentifier)" }
    var canPatch: Bool { fullText != nil && AX.settable(element, kAXSelectedTextAttribute) && AX.settable(element, kAXSelectedTextRangeAttribute) }
    static func capture(passive: Bool = false) throws -> SelectionSnapshot {
        guard AXIsProcessTrusted() else { throw ParzrError.message("Allow Accessibility to use Parzr in your editors.") }
        guard let app = NSWorkspace.shared.frontmostApplication, app.bundleIdentifier != Bundle.main.bundleIdentifier,
              let element = AX.focusedText(app) else { throw ParzrError.message("Select text in an editor, then press your Parzr shortcut.") }
        guard !AX.isSecure(element), !IsSecureEventInputEnabled() else { throw ParzrError.message("Parzr does not read secure fields.") }
        guard Preferences.shared.enabled(for: app.bundleIdentifier ?? "") else { throw ParzrError.message("Parzr is disabled for this app. Enable it in Apps settings.") }
        guard let selectedRange = AX.range(element) else { throw ParzrError.message("This editor hides its selection. Use the Parzr editor extension, or copy text into the playground.") }
        let full = AX.string(element, kAXValueAttribute)
        var selection = selectedRange
        var text = AX.string(element, kAXSelectedTextAttribute) ?? ""
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
                                 bounds: AX.bounds(element, selection), richText: AX.attributed(element, selection), copied: false)
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
        return SelectionSnapshot(app: app, element: element, selection: range, expectedSelection: range, text: text, fullText: nil, bounds: nil, richText: nil, copied: true)
    }
    /// Two copies of the same range may differ only by trailing newlines.
    nonisolated static func sameCopiedText(_ a: String, _ b: String) -> Bool {
        func trimmed(_ s: String) -> String { var s = s; while s.last?.isNewline == true { s.removeLast() }; return s }
        return trimmed(a) == trimmed(b)
    }

    func validate() throws {
        if copied {
            guard !app.isTerminated, app == NSWorkspace.shared.frontmostApplication, !IsSecureEventInputEnabled() else { throw ParzrError.message("Your selection changed. Select the text again.") }
            return
        }
        guard !app.isTerminated, !IsSecureEventInputEnabled(), !AX.isSecure(element),
              let focused = AX.focusedText(app), CFEqual(focused, element),
              let current = AX.range(element), current == expectedSelection || (expectedSelection.length == 0 && current.length == 0) else {
            throw ParzrError.message("Your selection changed. Select the text again.")
        }
        if let fullText {
            guard AX.string(element, kAXValueAttribute) == fullText else { throw ParzrError.message("Your text changed. Select it again.") }
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
        var ranges: [TextSpan] = []
        richText.enumerateAttributes(in: NSRange(location: 0, length: richText.length)) { attributes, range, _ in
            if attributes[.link] != nil || attributes[.attachment] != nil { ranges.append(TextSpan(range)) }
        }
        return ranges
    }
    func apply(_ edits: [WritingEdit]) throws {
        try validate(); try EditPlan.validate(edits, in: text)
        // A passive caret may have moved since the snapshot; restore it from where it is now.
        let caretStart = expectedSelection.length == 0 ? (AX.range(element)?.location ?? expectedSelection.location) : expectedSelection.location
        guard canPatch, let fullText else { throw ParzrError.message("This editor needs paste replacement. Review the formatting notice before using Paste instead.") }
        var expected = fullText
        var applied = 0
        for edit in edits.reversed() {
            // Verify between every range patch; never replace the entire document.
            guard AX.string(element, kAXValueAttribute) == expected else {
                throw ParzrError.message("The editor changed during replacement. \(applied) edits applied; use the editor's Undo to revert.")
            }
            let global = NSRange(location: selection.location + edit.start_utf16, length: edit.end_utf16 - edit.start_utf16)
            guard AX.setRange(element, global), AXUIElementSetAttributeValue(element, kAXSelectedTextAttribute as CFString, edit.replacement as CFString) == .success else {
                _ = AX.setRange(element, expectedSelection)
                throw ParzrError.message("The editor refused a range edit. \(applied) edits applied; use the editor's Undo if needed.")
            }
            let next = NSMutableString(string: expected); next.replaceCharacters(in: global, with: edit.replacement); expected = next as String
            applied += 1
        }
        guard AX.string(element, kAXValueAttribute) == expected else { throw ParzrError.message("The editor did not confirm the final edit. Check your text before continuing.") }
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
            _ = AX.setRange(element, NSRange(location: min(max(0, caret), expected.utf16.count), length: 0))
        } else {
            _ = AX.setRange(element, NSRange(location: selection.location, length: selection.length + delta))
        }
    }
    func metadata() -> String {
        var attributes: CFArray?; var parameters: CFArray?
        AXUIElementCopyAttributeNames(element, &attributes)
        AXUIElementCopyParameterizedAttributeNames(element, &parameters)
        return "App: \(bundle)\nRole: \(AX.string(element, kAXRoleAttribute) ?? "unknown")\nSubrole: \(AX.string(element, kAXSubroleAttribute) ?? "none")\nSelection range: available\nFull value: \(fullText != nil)\nMinimal range patch: \(canPatch)\nAttributed text: \(richText != nil)\nRange bounds: \(bounds != nil)\nAttributes: \((attributes as? [String] ?? []).joined(separator: ", "))\nParameterized: \((parameters as? [String] ?? []).joined(separator: ", "))\nText is excluded from this report."
    }
}
