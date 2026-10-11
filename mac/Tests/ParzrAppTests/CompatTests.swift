import XCTest
import AppKit
import ParzrCore
@testable import Parzr

@MainActor
final class CompatTests: XCTestCase {
    func testFocusFallbackAcceptsOnlyTheAppsOwnPid() {
        XCTAssertTrue(Compat.acceptsFocus(elementPID: 42, appPID: 42))
        XCTAssertFalse(Compat.acceptsFocus(elementPID: 43, appPID: 42))
        XCTAssertFalse(Compat.acceptsFocus(elementPID: nil, appPID: 42))
    }
    func testSecureInputNamesAHolderOnlyWhenItCanAndNeverExplainsTheWritersOwnSecureField() {
        func holder(owner: pid_t?, name: String?, terminal: Bool = false, watched: pid_t = 20, known: Bool = true, secure: Bool = false) -> Compat.SecureInputHolder? {
            Compat.secureInputHolder(ownerPID: owner, ownerName: name, ownerIsTerminal: terminal, watchedPID: watched, focusKnown: known, focusSecure: secure)
        }
        // The writer is in a password field: that is the reason, say nothing.
        XCTAssertNil(holder(owner: 20, name: "Safari", secure: true))
        XCTAssertNil(holder(owner: 10, name: "iTerm2", secure: true))
        // The reported app is the writer's and Parzr cannot see the field: it may be a secure one.
        XCTAssertNil(holder(owner: 20, name: "Safari", known: false))
        // A terminal with Secure Keyboard Entry, checked with Option+Space: name it.
        XCTAssertEqual(holder(owner: 20, name: "Terminal", terminal: true), .app("Terminal"))
        // Slack's plain composer while a background app holds secure input: the window server reports Slack itself, so Slack is not blamed.
        XCTAssertEqual(holder(owner: 20, name: "Slack"), .elsewhere)
        // A different app recorded as the holder is named.
        XCTAssertEqual(holder(owner: 10, name: "iTerm2"), .app("iTerm2"))
        XCTAssertEqual(holder(owner: nil, name: nil), .elsewhere)
        XCTAssertTrue(Compat.isTerminal("com.googlecode.iterm2")); XCTAssertFalse(Compat.isTerminal("dev.zed.Zed")); XCTAssertFalse(Compat.isTerminal("com.tinyspeck.slackmacgap"))
    }
    @MainActor func testSecureInputWording() {
        XCTAssertEqual(SecureInput.message(nil), "Parzr does not read secure fields.")
        XCTAssertTrue(SecureInput.message(.app("iTerm2")).hasPrefix("Secure input is on in iTerm2"))
        XCTAssertTrue(SecureInput.message(.elsewhere).hasPrefix("Another app has secure input on"))
        XCTAssertEqual(SecureInput.pausedLine(.app("iTerm2")), "Paused: Secure input is on in iTerm2")
        XCTAssertEqual(SecureInput.pausedLine(.elsewhere), "Paused: Secure input is on in another app")
    }
    func testTerminalsAndCodeEditorsAreNeverCheckedAutomatically() {
        for bundle in ["com.apple.Terminal", "com.googlecode.iterm2", "dev.warp.Warp-Stable", "dev.warp.Warp-Preview", "com.mitchellh.ghostty", "net.kovidgoyal.kitty",
                       "org.alacritty", "com.github.wez.wezterm", "org.tabby", "co.zeit.hyper", "dev.zed.Zed", "com.jetbrains.intellij"] {
            XCTAssertTrue(Compat.isExcluded(bundle), bundle)
        }
        for bundle in ["com.apple.TextEdit", "com.tinyspeck.slackmacgap", "com.microsoft.teams2", "com.google.Chrome", "com.apple.mail", nil] as [String?] {
            XCTAssertFalse(Compat.isExcluded(bundle), bundle ?? "nil")
        }
    }
    func testUnlistedChromiumBrowsersAreRecognisedByTheirRendererHelper() {
        XCTAssertTrue(Compat.hasRendererHelper(["Google Chrome for Testing Helper (Alerts).app", "Google Chrome for Testing Helper (Renderer).app", "chrome_crashpad_handler"]))
        XCTAssertTrue(Compat.hasRendererHelper(["Brave Browser Helper (Aperitif Renderer).app", "Brave Browser Helper (Renderer).app"]))
        XCTAssertFalse(Compat.hasRendererHelper(["chrome_crashpad_handler"]), "Electron's framework keeps only the crash handler; its helpers sit beside the framework")
        XCTAssertFalse(Compat.hasRendererHelper([]))
    }
    func testElectronSwitchIsResetOnActivationButRateLimited() {
        var gate = ActivationGate(); let t = Date(timeIntervalSince1970: 1000)
        XCTAssertTrue(gate.shouldSet(pid: 1, now: t, force: false), "first sight sets once")
        XCTAssertFalse(gate.shouldSet(pid: 1, now: t.addingTimeInterval(5), force: false), "ordinary queries do not re-set")
        XCTAssertFalse(gate.shouldSet(pid: 1, now: t.addingTimeInterval(1), force: true), "inside 2 s")
        XCTAssertTrue(gate.shouldSet(pid: 1, now: t.addingTimeInterval(2.1), force: true), "activation re-sets after 2 s")
        XCTAssertFalse(gate.shouldSet(pid: 1, now: t.addingTimeInterval(3), force: true), "the clock restarts at each set")
        XCTAssertTrue(gate.shouldSet(pid: 2, now: t.addingTimeInterval(3), force: true), "per pid")
    }
    func testTypedReplacementChunksWholeCharactersWithinTheLimit() {
        let long = String(repeating: "a", count: 45)
        let events = TypedReplacement.events(for: long)
        XCTAssertEqual(events.count, 3)
        XCTAssertEqual(events.map { if case .text(let u) = $0 { u.count } else { 0 } }, [20, 20, 5])
        let emoji = String(repeating: "x", count: 19) + "\u{1F642}" + "tail"
        let pieces = TypedReplacement.events(for: emoji).map { event -> [UInt16] in if case .text(let u) = event { return u } else { return [] } }
        XCTAssertTrue(pieces.allSatisfy { $0.count <= 20 })
        XCTAssertEqual(String(decoding: pieces.flatMap { $0 }, as: UTF16.self), emoji)
        XCTAssertEqual(pieces[0].count, 19, "a surrogate pair is never split")
        XCTAssertEqual(TypedReplacement.events(for: ""), [.delete])
        XCTAssertEqual(TypedReplacement.events(for: "ok"), [.text(Array("ok".utf16))])
    }
    func testReplacementDecisions() {
        XCTAssertEqual(ReplacePlan.first(textSettable: true, rangeSettable: true), .axText)
        XCTAssertEqual(ReplacePlan.first(textSettable: false, rangeSettable: true), .typed, "Word: selected text is not settable")
        XCTAssertNil(ReplacePlan.first(textSettable: true, rangeSettable: false))
        XCTAssertEqual(ReplacePlan.verdict(before: "a teh b", after: "a the b", expected: "a the b"), .applied)
        XCTAssertEqual(ReplacePlan.verdict(before: "a teh b", after: "a teh b", expected: "a the b"), .unchanged, "write accepted but ignored: type it")
        XCTAssertEqual(ReplacePlan.verdict(before: "a teh b", after: "a tehe b", expected: "a the b"), .diverged, "never type over unexpected changes")
        XCTAssertEqual(ReplacePlan.verdict(before: "a teh b", after: nil, expected: "a the b"), .diverged)
    }
    func testVSCodeProseFileTitleFilter() {
        for title in ["README.md - parzr - Visual Studio Code", "notes.txt \u{2014} docs \u{2014} Cursor", "\u{25CF} draft.mdx - site - Visual Studio Code", "my notes.rst - x", "a.MARKDOWN - x"] { XCTAssertTrue(Compat.isProseFile(windowTitle: title), title) }
        for title in ["main.rs - parzr - Visual Studio Code", "Welcome - Visual Studio Code", "md - parzr", ".md - parzr", "notes.txt.swift - x", "", "Settings"] { XCTAssertFalse(Compat.isProseFile(windowTitle: title), title) }
        XCTAssertFalse(Compat.isProseFile(windowTitle: nil))
    }
    func testVSCodeIsPreparedOnlyAfterOptIn() {
        XCTAssertFalse(Compat.shouldPrepare(bundle: "com.microsoft.VSCode", vscodeEnabled: false))
        XCTAssertFalse(Compat.shouldPrepare(bundle: "com.todesktop.230313mzl4w4u92", vscodeEnabled: false))
        XCTAssertTrue(Compat.shouldPrepare(bundle: "com.microsoft.VSCode", vscodeEnabled: true))
        XCTAssertTrue(Compat.shouldPrepare(bundle: "com.apple.TextEdit", vscodeEnabled: false))
        XCTAssertTrue(Compat.needsFocusRetry(bundle: "org.mozilla.firefox", vscodeEnabled: false))
        XCTAssertFalse(Compat.needsFocusRetry(bundle: "com.microsoft.VSCode", vscodeEnabled: false))
        XCTAssertTrue(Compat.readsAppRole("org.mozilla.firefox")); XCTAssertTrue(Compat.readsAppRole("com.google.Chrome")); XCTAssertFalse(Compat.readsAppRole("com.apple.TextEdit"))
    }
    func testVSCodeReviewAnchorStaysInsideTheEditor() {
        let frame = CGRect(x: 100, y: 50, width: 800, height: 600)
        let anchor = Compat.reviewAnchor(frame: frame)
        XCTAssertTrue(frame.contains(anchor)); XCTAssertEqual(anchor.maxX, 840 + 1)
        XCTAssertEqual(Compat.reviewAnchor(frame: CGRect(x: 0, y: 0, width: 30, height: 10)).minX, 0)
    }
    func testXcodeProtectsEverythingButCommentsAndStrings() {
        let text = NSMutableAttributedString()
        let key = NSAttributedString.Key("AXCodeSemanticType")
        for (piece, type) in [("let a = ", "AXCodeSemanticType.Keyword"), ("\"teh string\"", "AXCodeSemanticType.String"), (" ", nil), ("x", "AXCodeSemanticType.Identifier"), ("// teh comment", "AXCodeSemanticType.Comment"), ("/// doc", "Documentation")] as [(String, String?)] {
            text.append(NSAttributedString(string: piece, attributes: type.map { [key: $0] } ?? [:]))
        }
        let spans = Compat.codeProtectedSpans(in: text)
        let ns = text.string as NSString
        XCTAssertEqual(spans.map { ns.substring(with: NSRange(location: $0.start_utf16, length: $0.end_utf16 - $0.start_utf16)) }, ["let a = ", " x"], "adjacent code runs merge; strings, comments and docs stay checkable")
        XCTAssertTrue(Compat.isCheckable(semanticType: "AXCodeSemanticType.Comment")); XCTAssertFalse(Compat.isCheckable(semanticType: "AXCodeSemanticType.DocumentationKeyword")); XCTAssertFalse(Compat.isCheckable(semanticType: nil))
    }
    func testOwnProcessIsReadableOnlyThroughTheWritingSpace() {
        let own: pid_t = 100, other: pid_t = 200, id = Compat.draftEditorIdentifier
        XCTAssertTrue(Compat.allowsCapture(appPID: own, ownPID: own, identifier: id), "Parzr's writing space")
        XCTAssertFalse(Compat.allowsCapture(appPID: own, ownPID: own, identifier: nil), "card, settings fields, popovers have no identifier")
        XCTAssertFalse(Compat.allowsCapture(appPID: own, ownPID: own, identifier: ""))
        XCTAssertFalse(Compat.allowsCapture(appPID: own, ownPID: own, identifier: "parzr.draftEditor.extra"), "exact match only")
        XCTAssertFalse(Compat.allowsCapture(appPID: own, ownPID: own, identifier: "Writing space"), "a label is not the identifier")
        XCTAssertTrue(Compat.allowsCapture(appPID: other, ownPID: own, identifier: nil), "other apps are never filtered by identifier")
        XCTAssertTrue(Compat.allowsCapture(appPID: other, ownPID: own, identifier: id))
    }
    func testFirefoxHintConditions() {
        let n = Compat.firefoxHintKeystrokes
        func hint(_ bundle: String? = "org.mozilla.firefox", role: String? = "AXWebArea", text: Bool = false, keys: Int = Compat.firefoxHintKeystrokes, dismissed: Bool = false) -> Bool {
            Compat.firefoxHintNeeded(bundle: bundle, focusedRole: role, hasText: text, keystrokes: keys, dismissed: dismissed)
        }
        XCTAssertTrue(hint()); XCTAssertTrue(hint(role: "AXGroup")); XCTAssertTrue(hint(role: nil))
        XCTAssertFalse(hint(keys: n - 1), "not enough typing yet")
        XCTAssertFalse(hint(text: true), "text resolved: accessibility works")
        XCTAssertFalse(hint(dismissed: true)); XCTAssertFalse(hint("com.google.Chrome")); XCTAssertFalse(hint(role: "AXTextField"))
        XCTAssertFalse(StatusPopover.firefoxHint.contains("\u{2014}") || StatusPopover.firefoxHint.contains("\u{2013}"))
    }
    func testVSCodeOptInDefaultsOffAndPersists() throws {
        let name = "app.parzr.tests.compat"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: name)); defaults.removePersistentDomain(forName: name)
        defer { defaults.removePersistentDomain(forName: name) }
        let prefs = Preferences(defaults: defaults)
        XCTAssertFalse(prefs.checkVSCode); XCTAssertFalse(prefs.firefoxHintDismissed)
        prefs.checkVSCode = true; prefs.firefoxHint = true; prefs.dismissFirefoxHint()
        let restored = Preferences(defaults: defaults)
        XCTAssertTrue(restored.checkVSCode); XCTAssertTrue(restored.firefoxHintDismissed); XCTAssertFalse(restored.firefoxHint)
    }
    /// A grant made while Parzr runs must replace the global monitors created before it. Seam only: a live revoke and grant cycle is not covered.
    func testGrantingAccessibilityReinstallsGlobalMonitors() {
        let prefs = Preferences.shared, original = prefs.permissionGranted
        defer { prefs.permissionGranted = original }
        prefs.permissionGranted = false
        let observer = PassiveObserver(), inline = InlineSuggestions()
        defer { observer.stop(); inline.stop() }
        let (passiveBefore, inlineBefore) = (observer.monitorInstalls, inline.monitorInstalls)
        prefs.permissionGranted = true
        XCTAssertEqual(observer.monitorInstalls, passiveBefore + 1)
        XCTAssertEqual(inline.monitorInstalls, inlineBefore + 1)
        prefs.permissionGranted = true
        XCTAssertEqual(observer.monitorInstalls, passiveBefore + 1, "no reinstall without a change")
    }
}
