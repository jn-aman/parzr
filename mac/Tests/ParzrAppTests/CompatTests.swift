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
