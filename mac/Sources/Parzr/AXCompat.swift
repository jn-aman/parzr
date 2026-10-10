import AppKit
import ApplicationServices
import Carbon
import ParzrCore

/// Per-app compatibility decisions, kept pure so they are unit-tested; the AX calls live in `AX`.
enum Compat {
    static let vscode = ["com.microsoft.VSCode", "com.todesktop.230313mzl4w4u92"]
    static let chromium = ["com.google.Chrome", "com.microsoft.edgemac", "com.brave.Browser", "company.thebrowser.Browser", "com.vivaldi.Vivaldi", "com.operasoftware.Opera", "org.chromium.Chromium", "com.microsoft.teams2"]
    /// Never checked automatically: terminals (commands and output are not prose) and code editors with their own tooling. Bundle id prefixes,
    /// so preview and nightly builds match too (Warp Preview is dev.warp.Warp-Preview).
    static let excluded = ["com.apple.Terminal", "com.googlecode.iterm2", "dev.warp.Warp", "com.mitchellh.ghostty", "net.kovidgoyal.kitty", "org.alacritty",
                           "com.github.wez.wezterm", "org.tabby", "co.zeit.hyper", "dev.zed.Zed", "com.jetbrains"]
    static func isExcluded(_ bundle: String?) -> Bool { excluded.contains { bundle?.hasPrefix($0) == true } }
    static let proseExtensions = [".md", ".markdown", ".txt", ".mdx", ".rst"]
    /// Firefox needs this many keystrokes with no text field found before the hint appears.
    static let firefoxHintKeystrokes = 8
    static func isVSCode(_ bundle: String?) -> Bool { vscode.contains { bundle?.hasPrefix($0) == true } }
    static func isFirefox(_ bundle: String?) -> Bool { bundle?.hasPrefix("org.mozilla.") == true }
    static func isChromium(_ bundle: String?) -> Bool { chromium.contains { bundle?.hasPrefix($0) == true } }
    /// A Chromium browser that is not on the list (Chrome for Testing, and new ones packaged the standard way) keeps a "<Name> Helper (Renderer).app" inside its
    /// "<Name> Framework.framework/Versions/Current/Helpers". Electron apps keep theirs beside the framework, and take AXManualAccessibility anyway.
    static func hasRendererHelper(_ helpers: [String]) -> Bool { helpers.contains { $0.hasSuffix(" (Renderer).app") } }
    static func isXcode(_ bundle: String?) -> Bool { bundle == "com.apple.dt.Xcode" }
    /// VS Code and Cursor show a screen-reader notice when asked for accessibility, so they are touched only when the user opted in.
    static func shouldPrepare(bundle: String?, vscodeEnabled: Bool) -> Bool { !isVSCode(bundle) || vscodeEnabled }
    /// Firefox 121+ and Chromium start their accessibility engines when a client reads the application role.
    static func readsAppRole(_ bundle: String?) -> Bool { isFirefox(bundle) || isChromium(bundle) }
    /// Parzr never reads its own windows (card, settings, popovers) except the Studio writing space, which carries this accessibility identifier.
    static let draftEditorIdentifier = "parzr.draftEditor"
    static func allowsCapture(appPID: pid_t, ownPID: pid_t, identifier: String?) -> Bool { appPID != ownPID || identifier == draftEditorIdentifier }
    /// First focus queries after activation can miss the editor while Firefox or VS Code switch accessibility on.
    static func needsFocusRetry(bundle: String?, vscodeEnabled: Bool) -> Bool { isFirefox(bundle) || (isVSCode(bundle) && vscodeEnabled) }
    /// The system-wide focused element is accepted only when it belongs to the app being checked.
    static func acceptsFocus(elementPID: pid_t?, appPID: pid_t) -> Bool { elementPID == appPID }
    /// VS Code window titles read "file.md - folder - Visual Studio Code", sometimes with a leading dirty dot or an em or en dash separator.
    static func isProseFile(windowTitle: String?) -> Bool {
        guard var name = windowTitle else { return false }
        for separator in [" - ", " \u{2014} ", " \u{2013} "] { if let found = name.range(of: separator) { name = String(name[..<found.lowerBound]) } }
        name = name.trimmingCharacters(in: CharacterSet.alphanumerics.inverted.subtracting(CharacterSet(charactersIn: "._-")))
        let lower = name.lowercased()
        return proseExtensions.contains { lower.hasSuffix($0) && lower.count > $0.count }
    }
    /// Show the Firefox hint once the user has typed several keys while no text field resolved and the focus is a bare page element.
    static func firefoxHintNeeded(bundle: String?, focusedRole: String?, hasText: Bool, keystrokes: Int, dismissed: Bool) -> Bool {
        isFirefox(bundle) && !dismissed && !hasText && keystrokes >= firefoxHintKeystrokes && (focusedRole == nil || ["AXWebArea", "AXGroup"].contains(focusedRole!))
    }
    /// Editors with no word geometry (VS Code reports 0x0) still get a review marker: a thin rect at the top right of the editor, in AX (top-left origin) coordinates.
    static func reviewAnchor(frame: CGRect) -> CGRect {
        CGRect(x: max(frame.minX, frame.maxX - 60), y: frame.minY + 8, width: 1, height: min(22, max(1, frame.height)))
    }
    /// Google Docs draws its page on a canvas; its only text surface is this hidden text area in an iframe, trusted only on a docs.google.com document page.
    static let docsTextDescription = "Document content"
    static func isGoogleDocsURL(_ url: String?) -> Bool {
        guard let url, let parts = URLComponents(string: url) else { return false }
        return parts.host == "docs.google.com" && parts.path.hasPrefix("/document/")
    }
    /// With "braille support" off, Docs fills the text area with zero-width characters only: the real text exists on the canvas, so there is nothing to read.
    static func docsTextHidden(_ value: String?) -> Bool {
        guard let value else { return false }
        return value.unicodeScalars.allSatisfy { $0 == "\u{200B}" || CharacterSet.whitespacesAndNewlines.contains($0) }
    }
    /// Keystrokes in Docs with no readable text before the setup hint appears (a new empty document reads the same until the first characters land).
    static let docsHintKeystrokes = 8
    static func docsHintNeeded(isDocs: Bool, value: String?, keystrokes: Int, dismissed: Bool) -> Bool {
        isDocs && !dismissed && keystrokes >= docsHintKeystrokes && docsTextHidden(value)
    }
    /// Xcode's semantic runs: only comments, documentation and strings are prose.
    static func isCheckable(semanticType: String?) -> Bool {
        guard let type = semanticType?.split(separator: ".").last?.lowercased() else { return false }
        return ["comment", "documentation", "string", "aside", "heading"].contains(type)
    }
    /// Every run that is not a comment or string literal, merged, so the engine skips code.
    static func codeProtectedSpans(in text: NSAttributedString) -> [TextSpan] {
        var spans: [NSRange] = []
        text.enumerateAttribute(NSAttributedString.Key("AXCodeSemanticType"), in: NSRange(location: 0, length: text.length)) { value, range, _ in
            guard !isCheckable(semanticType: value.map { "\($0)" }) else { return }
            if let last = spans.last, NSMaxRange(last) == range.location { spans[spans.count - 1] = NSUnionRange(last, range) } else { spans.append(range) }
        }
        return spans.map(TextSpan.init)
    }
}

/// Rate limit for the Electron/Chromium accessibility switches: a first set builds the tree, a second one after activation flips the editor into screen-reader mode.
struct ActivationGate {
    static let minimumGap: TimeInterval = 2
    private(set) var last: [pid_t: Date] = [:]
    /// First sight of a pid always sets; later sets happen only when forced (activation, focus change) and `minimumGap` has passed.
    mutating func shouldSet(pid: pid_t, now: Date = Date(), force: Bool) -> Bool {
        if let previous = last[pid] { guard force, now.timeIntervalSince(previous) >= Self.minimumGap else { return false } }
        if last.count >= 128 { last.removeAll() }
        last[pid] = now
        return true
    }
}

/// How a range edit is made. Some editors accept the AXSelectedText write and ignore it (Word, VS Code screen-reader mode, Chrome textareas), so the second path types the replacement as Unicode key events.
enum ReplacePlan {
    enum Step: Equatable { case axText, typed }
    enum Verdict: Equatable { case applied, unchanged, diverged }
    /// A settable selection range is required for either path; a settable selected text only picks the cheaper one.
    /// Google Docs accepts the AXSelectedText write and does nothing, so it is typed at once instead of waiting out a write that cannot land.
    static func first(textSettable: Bool, rangeSettable: Bool, docs: Bool = false) -> Step? { rangeSettable ? (textSettable && !docs ? .axText : .typed) : nil }
    /// `unchanged` is the only state that may fall back to typing; anything else could double-apply.
    static func verdict(before: String, after: String?, expected: String) -> Verdict {
        guard let after else { return .diverged }
        return after == expected ? .applied : after == before ? .unchanged : .diverged
    }
}

enum TypedReplacement {
    enum Event: Equatable { case text([UInt16]), delete }
    static let chunkSize = 20
    /// Whole characters per event, at most `chunk` UTF-16 units each (a longer character is sent alone); deleting needs a Delete key press.
    static func events(for replacement: String, chunk: Int = chunkSize) -> [Event] {
        guard !replacement.isEmpty else { return [.delete] }
        var events: [Event] = [], current: [UInt16] = []
        for character in replacement {
            let units = Array(String(character).utf16)
            if !current.isEmpty, current.count + units.count > chunk { events.append(.text(current)); current = [] }
            current += units
        }
        if !current.isEmpty { events.append(.text(current)) }
        return events
    }
}

extension AX {
    static func param(_ element: AXUIElement, _ attribute: String, _ parameter: CFTypeRef) -> CFTypeRef? {
        var value: CFTypeRef?
        guard AXUIElementCopyParameterizedAttributeValue(element, attribute as CFString, parameter, &value) == .success else { return nil }
        return value
    }
    /// Re-sets the accessibility switches. `force` is for activation and focus changes; ordinary queries set them once per app.
    static func prepare(_ app: NSRunningApplication, force: Bool = false) {
        let bundle = app.bundleIdentifier
        guard Compat.shouldPrepare(bundle: bundle, vscodeEnabled: Preferences.shared.checkVSCode) else { return }
        let element = AXUIElementCreateApplication(app.processIdentifier)
        AXUIElementSetMessagingTimeout(element, 0.25)
        let chromium = isChromiumBrowser(app)
        if Compat.readsAppRole(bundle) || chromium { _ = get(element, kAXRoleAttribute) }
        guard !Compat.isFirefox(bundle), gate.shouldSet(pid: app.processIdentifier, force: force) else { return }
        // Electron's documented assistive-technology switch exposes nested composers. Unsupported apps simply refuse it.
        // Chrome rejects it and builds no accessibility tree without AXEnhancedUserInterface; native apps are left alone because that can disturb window managers.
        if AXUIElementSetAttributeValue(element, "AXManualAccessibility" as CFString, kCFBooleanTrue) != .success, chromium {
            _ = AXUIElementSetAttributeValue(element, "AXEnhancedUserInterface" as CFString, kCFBooleanTrue)
        }
    }
    private static var chromiumBundles: [String: Bool] = [:]
    /// A listed Chromium browser, or one recognised by its bundle (see `Compat.hasRendererHelper`); the bundle is looked at once per app.
    static func isChromiumBrowser(_ app: NSRunningApplication) -> Bool {
        if Compat.isChromium(app.bundleIdentifier) { return true }
        guard let url = app.bundleURL else { return false }
        if let known = chromiumBundles[url.path] { return known }
        let frameworks = url.appendingPathComponent("Contents/Frameworks"), files = FileManager.default
        let found = ((try? files.contentsOfDirectory(atPath: frameworks.path)) ?? []).filter { $0.hasSuffix(".framework") }.contains { name in
            Compat.hasRendererHelper((try? files.contentsOfDirectory(atPath: frameworks.appendingPathComponent(name).appendingPathComponent("Versions/Current/Helpers").path)) ?? [])
        }
        chromiumBundles[url.path] = found
        return found
    }
    /// Electron apps answer the system-wide focus query when the per-app one fails (-25212).
    static func systemFocused(for app: NSRunningApplication) -> AXUIElement? {
        let system = AXUIElementCreateSystemWide()
        AXUIElementSetMessagingTimeout(system, 0.25)
        guard let value = get(system, kAXFocusedUIElementAttribute), CFGetTypeID(value) == AXUIElementGetTypeID() else { return nil }
        var pid: pid_t = 0
        guard AXUIElementGetPid(value as! AXUIElement, &pid) == .success, Compat.acceptsFocus(elementPID: pid, appPID: app.processIdentifier) else { return nil }
        return (value as! AXUIElement)
    }
    static func windowTitle(_ app: NSRunningApplication, _ element: AXUIElement) -> String? {
        let appElement = AXUIElementCreateApplication(app.processIdentifier)
        AXUIElementSetMessagingTimeout(appElement, 0.25)
        for window in [get(appElement, kAXFocusedWindowAttribute), get(element, kAXWindowAttribute)] {
            if let window, CFGetTypeID(window) == AXUIElementGetTypeID(), let title = string(window as! AXUIElement, kAXTitleAttribute) { return title }
        }
        return nil
    }
    /// Cocoa-coordinates rect for the review marker when an editor reports no word geometry.
    static func anchor(_ element: AXUIElement) -> CGRect? {
        guard let p = get(element, kAXPositionAttribute), let s = get(element, kAXSizeAttribute), CFGetTypeID(p) == AXValueGetTypeID(), CFGetTypeID(s) == AXValueGetTypeID() else { return nil }
        var origin = CGPoint.zero, size = CGSize.zero
        guard AXValueGetValue(p as! AXValue, .cgPoint, &origin), AXValueGetValue(s as! AXValue, .cgSize, &size), size.width > 0, size.height > 0 else { return nil }
        let rect = Compat.reviewAnchor(frame: CGRect(origin: origin, size: size))
        return CGRect(x: rect.minX, y: (NSScreen.screens.first?.frame.maxY ?? 0) - rect.maxY, width: rect.width, height: rect.height)
    }

    // MARK: Text, selection and attributed text, including WebKit text-marker editors (Mail compose, other contenteditable AXWebAreas)

    /// An editable web area exposes text only through text markers: no AXSelectedTextRange, an empty AXValue, but a settable value and selection marker.
    static func isMarkerEditor(_ element: AXUIElement) -> Bool {
        get(element, "AXStartTextMarker") != nil && settable(element, kAXValueAttribute) && settable(element, "AXSelectedTextMarkerRange")
    }
    static func text(_ element: AXUIElement) -> String? {
        let value = string(element, kAXValueAttribute)
        if value?.isEmpty != false, isMarkerEditor(element), let start = get(element, "AXStartTextMarker"), let end = get(element, "AXEndTextMarker"),
           let all = param(element, "AXTextMarkerRangeForUnorderedTextMarkers", [start, end] as CFArray) { return param(element, "AXStringForTextMarkerRange", all) as? String }
        return value
    }
    static func selection(_ element: AXUIElement) -> NSRange? {
        if let known = range(element) { return known }
        guard isMarkerEditor(element), let marked = get(element, "AXSelectedTextMarkerRange"), CFGetTypeID(marked) == AXTextMarkerRangeGetTypeID(),
              let start = param(element, "AXIndexForTextMarker", AXTextMarkerRangeCopyStartMarker(marked as! AXTextMarkerRange)) as? Int,
              let end = param(element, "AXIndexForTextMarker", AXTextMarkerRangeCopyEndMarker(marked as! AXTextMarkerRange)) as? Int, start >= 0, end >= start else { return nil }
        return NSRange(location: start, length: end - start)
    }
    static func markerRange(_ element: AXUIElement, _ range: NSRange) -> CFTypeRef? {
        guard let start = param(element, "AXTextMarkerForIndex", NSNumber(value: range.location)), let end = param(element, "AXTextMarkerForIndex", NSNumber(value: NSMaxRange(range))) else { return nil }
        return param(element, "AXTextMarkerRangeForUnorderedTextMarkers", [start, end] as CFArray)
    }
    static func canSelect(_ element: AXUIElement) -> Bool { settable(element, kAXSelectedTextRangeAttribute) || (isMarkerEditor(element) && range(element) == nil) }
    @discardableResult
    static func select(_ element: AXUIElement, _ range: NSRange) -> Bool {
        if settable(element, kAXSelectedTextRangeAttribute) { return setRange(element, range) }
        guard isMarkerEditor(element), let marked = markerRange(element, range) else { return false }
        return AXUIElementSetAttributeValue(element, "AXSelectedTextMarkerRange" as CFString, marked) == .success
    }
    static func markerAttributed(_ element: AXUIElement, _ range: NSRange) -> NSAttributedString? {
        guard isMarkerEditor(element), let marked = markerRange(element, range) else { return nil }
        return param(element, "AXAttributedStringForTextMarkerRange", marked) as? NSAttributedString
    }

    // MARK: Replacement

    /// Replaces `range`: AXSelectedText when the editor honours it, otherwise Unicode key events posted to the app. Verified by re-reading the text.
    static func replace(_ element: AXUIElement, in app: NSRunningApplication, range: NSRange, with replacement: String, before: String, expected: String) async throws {
        guard let first = ReplacePlan.first(textSettable: settable(element, kAXSelectedTextAttribute), rangeSettable: canSelect(element), docs: isDocsText(element)), select(element, range) else {
            throw ParzrError.message("The editor refused a range edit.")
        }
        if first == .axText, AXUIElementSetAttributeValue(element, kAXSelectedTextAttribute as CFString, replacement as CFString) == .success {
            // Some editors accept the write and change nothing; a slow one may still apply it, so wait before deciding.
            switch await settled(element, before: before, expected: expected, attempts: 8) {
            case .applied: return
            case .diverged: throw ParzrError.message("The editor changed during replacement.")
            case .unchanged: break
            }
        }
        // Docs handles a selection asynchronously: setting the same range twice in quick succession scrambles it, so it is set once and then waited for.
        let docs = isDocsText(element)
        guard SelfTestTarget.watched?.processIdentifier == app.processIdentifier, !IsSecureEventInputEnabled(),
              let focus = focusedText(app), CFEqual(focus, element), docs || select(element, range) else {
            throw ParzrError.message("Your selection changed. Select the text again.")
        }
        if docs {
            var held = false
            for _ in 0..<40 { if self.range(element) == range { held = true; break }; try await Task.sleep(for: .milliseconds(20)) }
            guard held else { throw ParzrError.message("Docs did not select the text. Try again.") }
            try await Task.sleep(for: .milliseconds(120))
        }
        for event in TypedReplacement.events(for: replacement) {
            post(event, to: app.processIdentifier)
            try await Task.sleep(for: .milliseconds(8))
        }
        guard await settled(element, before: before, expected: expected, attempts: 30) == .applied else { throw ParzrError.message("The editor did not accept the replacement.") }
    }
    private static func settled(_ element: AXUIElement, before: String, expected: String, attempts: Int) async -> ReplacePlan.Verdict {
        var verdict = ReplacePlan.Verdict.unchanged
        for _ in 0..<attempts {
            try? await Task.sleep(for: .milliseconds(40))
            verdict = ReplacePlan.verdict(before: before, after: text(element), expected: expected)
            if verdict != .unchanged { break }
        }
        return verdict
    }
    private static func post(_ event: TypedReplacement.Event, to pid: pid_t) {
        for down in [true, false] {
            let key: CGKeyCode = { if case .delete = event { return 51 } else { return 0 } }()
            guard let keyEvent = CGEvent(keyboardEventSource: nil, virtualKey: key, keyDown: down) else { continue }
            keyEvent.flags = [] // never inherit the Option held for the Parzr shortcut
            if case .text(let units) = event { keyEvent.keyboardSetUnicodeString(stringLength: units.count, unicodeString: units) }
            keyEvent.postToPid(pid)
        }
    }
}
