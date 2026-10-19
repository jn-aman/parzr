import XCTest
@testable import Parzr

/// Per-app and per-field rules and the sensitive-field keywords (pure: fields are described, never read from AX).
@MainActor
final class HostRulesTests: XCTestCase {
    private let rules = HostRules.builtIn
    private func field(_ role: String = "AXTextField", bundle: String = "com.example.app", url: String? = nil, labels: [String] = [], markers: [String] = [], ancestors: [[String]] = []) -> HostRules.Field {
        HostRules.Field(bundle: bundle, url: url, role: role, labels: labels, markers: markers, ancestors: ancestors)
    }
    private func blocked(_ field: HostRules.Field) -> Bool { rules.verdict(for: field) != .allowed }

    func testTheBuiltInListParses() {
        XCTAssertFalse(rules.rules.isEmpty)
        XCTAssertFalse(rules.sensitive.isEmpty)
        XCTAssertEqual(Set(rules.rules.map(\.id)).count, rules.rules.count, "rule ids are unique")
    }
    func testPasswordAndOneTimeCodeFieldsAreSkippedEverywhere() {
        for label in ["Password", "Enter passcode", "PIN", "One-time code", "Verification code", "2FA code", "OTP", "Two-factor authentication", "Contraseña", "Mot de passe"] {
            XCTAssertTrue(blocked(field(labels: [label])), label)
            XCTAssertTrue(blocked(field("AXTextArea", labels: [label])), "\(label) in a multi-line field")
        }
        XCTAssertEqual(rules.verdict(for: field(labels: ["Verification code"])), .blocked("sensitive:one-time-code"))
    }
    func testWordBoundariesKeepOrdinaryLabelsChecked() {
        for label in ["Spinning class notes", "Footprint summary", "Describe your setup", "Message", "Write a comment", "Subject", "Title", "Summary", "Compose email body"] {
            XCTAssertFalse(blocked(field("AXTextArea", labels: [label])), label)
        }
        for label in ["Subject", "Title", "Summary", "Commit message"] { XCTAssertFalse(blocked(field(labels: [label])), "single-line \(label)") }
    }
    func testFormFieldsAreSkippedOnlyWhenSingleLine() {
        for label in ["Email", "Phone number", "Username", "Street address", "City", "ZIP code", "Postal code", "First name", "Search", "Filter", "To", "Cc", "Website", "alice@example.com"] {
            XCTAssertTrue(blocked(field(labels: [label])), label)
            XCTAssertFalse(blocked(field("AXTextArea", labels: [label])), "a multi-line \(label) field is prose")
        }
    }
    func testASignInFormBlocksItsSingleLineFieldsByItsAncestors() {
        XCTAssertTrue(blocked(field(labels: ["Your workspace"], ancestors: [["form"], ["Sign in to Example", "login-form"]])))
        XCTAssertFalse(blocked(field("AXTextArea", labels: ["Your feedback"], ancestors: [["Sign in"]])), "a multi-line field inside such a section is still prose")
        XCTAssertFalse(blocked(field(labels: ["Your workspace"], ancestors: [["Settings"]])))
    }
    func testPasswordManagersAndSystemPanesAreOffWholesale() {
        for bundle in ["com.1password.1password", "com.bitwarden.desktop", "org.keepassxc.keepassxc", "com.apple.Passwords", "com.apple.systempreferences"] {
            XCTAssertTrue(rules.excludesApp(bundle), bundle)
            XCTAssertTrue(blocked(field("AXTextArea", bundle: bundle, labels: ["Notes"])), bundle)
        }
        for bundle in ["com.apple.TextEdit", "com.tinyspeck.slackmacgap", "com.apple.mail", "com.apple.Safari"] { XCTAssertFalse(rules.excludesApp(bundle), bundle) }
    }
    func testEveryCommonPasswordManagerAndAuthenticatorIsOff() {
        let bundles = ["com.1password.1password", "com.agilebits.onepassword7", "com.agilebits.onepassword-osx", "com.1password.safari", "com.bitwarden.desktop",
                       "com.dashlane.dashlanephonefinal", "com.lastpass.LastPass", "org.keepassxc.keepassxc", "me.proton.pass.electron", "in.sinew.Enpass-Desktop",
                       "com.nordsec.nordpass", "com.keepersecurity.passwordmanager", "com.callpod.keepermac", "com.siber.RoboForm", "com.markmcguill.strongbox.mac",
                       "com.hicknhacksoftware.MacPass", "com.keepassium.ios", "com.zetetic.Codebook", "com.outercorner.Secrets", "com.apple.Passwords",
                       "com.apple.keychainaccess", "com.authy.authy-mac", "io.ente.auth.mac", "com.bitwarden.authenticator"]
        for bundle in bundles { XCTAssertTrue(rules.excludesApp(bundle), bundle) }
        for bundle in ["com.apple.Notes", "com.siber.goodsync", "com.example.passwords-blog", "me.proton.mail"] { XCTAssertFalse(rules.excludesApp(bundle), bundle) }
    }
    func testOptionSpaceAndTheCopyFallbackHonourExclusions() {
        // Option+Space: never in an excluded app, a field a rule turns off, or one named for a secret; a no-prose form field stays checkable on request.
        XCTAssertTrue(Compat.blocksExplicitCheck(bundle: "com.1password.1password", verdict: .allowed, rules: rules))
        XCTAssertTrue(Compat.blocksExplicitCheck(bundle: "com.apple.Safari", verdict: rules.verdict(for: field("AXTextArea", bundle: "com.apple.Safari", markers: ["parzr-disable"])), rules: rules))
        XCTAssertTrue(Compat.blocksExplicitCheck(bundle: "com.apple.Safari", verdict: rules.verdict(for: field("AXTextArea", bundle: "com.apple.Safari", url: "https://accounts.example.com/")), rules: rules))
        for label in ["Password", "Verification code", "Card number", "Social security number", "API key"] {
            XCTAssertTrue(Compat.blocksExplicitCheck(bundle: "com.example.app", verdict: rules.verdict(for: field(labels: [label])), rules: rules), label)
        }
        for label in ["Search", "City", "First name", "Email"] {
            XCTAssertFalse(Compat.blocksExplicitCheck(bundle: "com.example.app", verdict: rules.verdict(for: field(labels: [label])), rules: rules), label)
        }
        XCTAssertFalse(Compat.blocksExplicitCheck(bundle: "com.apple.TextEdit", verdict: .allowed, rules: rules))
        // The copy fallback sends Cmd+C into the app: only where Parzr checks, in a field nothing blocks.
        XCTAssertTrue(Compat.allowsCopyFallback(bundle: "com.google.Chrome", verdict: .allowed, secure: false, rules: rules))
        XCTAssertFalse(Compat.allowsCopyFallback(bundle: "com.google.Chrome", verdict: .allowed, secure: true, rules: rules), "a secure field")
        for bundle in ["com.1password.1password", "com.bitwarden.desktop", "com.apple.Terminal", "com.googlecode.iterm2", "com.jetbrains.intellij", "com.apple.systempreferences"] {
            XCTAssertFalse(Compat.allowsCopyFallback(bundle: bundle, verdict: .allowed, secure: false, rules: rules), bundle)
        }
        for label in ["Password", "Search", "Email"] {
            XCTAssertFalse(Compat.allowsCopyFallback(bundle: "com.google.Chrome", verdict: rules.verdict(for: field(bundle: "com.google.Chrome", labels: [label])), secure: false, rules: rules), label)
        }
    }
    func testSignInAndCheckoutPagesAreOff() {
        XCTAssertTrue(blocked(field("AXTextArea", bundle: "com.google.Chrome", url: "https://accounts.example.com/signin")))
        XCTAssertTrue(blocked(field("AXTextArea", bundle: "com.google.Chrome", url: "https://shop.example.com/checkout?step=2")))
        XCTAssertTrue(blocked(field("AXTextArea", bundle: "com.google.Chrome", url: "https://example.com/u/login")))
        XCTAssertFalse(blocked(field("AXTextArea", bundle: "com.google.Chrome", url: "https://android.com/blog/logins-explained")), "a word inside a slug is no sign-in page")
        XCTAssertFalse(blocked(field("AXTextArea", bundle: "com.google.Chrome", url: "https://mail.google.com/mail/u/0/#inbox")))
    }
    func testChatComposersNamedAfterASensitiveChannelStayChecked() {
        let composer = field("AXTextArea", bundle: "com.tinyspeck.slackmacgap", labels: ["Message #password-reset"])
        XCTAssertEqual(rules.verdict(for: composer), .allowed)
        XCTAssertEqual(rules.verdict(for: field("AXTextArea", bundle: "com.google.Chrome", url: "https://app.slack.com/client/T1/C2", labels: ["Message #2fa-rollout"])), .allowed)
        XCTAssertTrue(blocked(field("AXTextArea", bundle: "com.example.chat", labels: ["Message #password-reset"])), "an unknown host keeps the keyword list")
        XCTAssertTrue(blocked(field(bundle: "com.tinyspeck.slackmacgap", labels: ["Password"])), "the lift is for multi-line composers only")
    }
    func testPagesCanOptOutOrLiftTheKeywordList() {
        XCTAssertEqual(rules.verdict(for: field("AXTextArea", labels: ["Notes"], ancestors: [["parzr-disable"]])), .blocked("rule:page-opt-out"))
        XCTAssertEqual(rules.verdict(for: field("AXTextArea", labels: ["Password hints for the team"], markers: ["parzr-enable"])), .allowed)
        XCTAssertEqual(rules.verdict(for: field("AXTextArea", markers: ["parzr-enable", "parzr-disable"])), .blocked("rule:page-opt-out"), "opting out wins")
    }
    func testRulesOnlyEverTakeAnEditorAway() {
        for eligibility in [Compat.EditorEligibility.editor, .ancestor, .blocked] {
            XCTAssertEqual(Compat.applying(.allowed, to: eligibility), eligibility)
        }
        XCTAssertEqual(Compat.applying(.blocked("sensitive:password"), to: .editor), .blocked)
        XCTAssertEqual(Compat.applying(.blocked("x"), to: .blocked), .blocked, "never upgrades a blocked field")
        XCTAssertEqual(Compat.applying(.blocked("x"), to: .ancestor), .ancestor, "the walk itself is unchanged")
    }
    func testAUserFileAddsToTheBuiltInRulesAndCanTurnAHostOff() throws {
        let user = try JSONDecoder().decode(HostRules.self, from: Data(#"{"rules": [{"id": "my-crm-notes", "bundle": "^com\\.example\\.crm$", "textFields": false}], "sensitive": [{"id": "ticket", "pattern": "^ticket id$"}]}"#.utf8))
        let merged = rules.merged(with: user)
        XCTAssertEqual(merged.verdict(for: field(bundle: "com.example.crm", labels: ["Notes"])), .blocked("rule:my-crm-notes"))
        XCTAssertEqual(merged.verdict(for: field("AXTextArea", bundle: "com.example.crm", labels: ["Notes"])), .allowed, "textFields: false leaves multi-line editors on")
        XCTAssertEqual(merged.verdict(for: field("AXTextArea", labels: ["Ticket ID"])), .blocked("sensitive:ticket"))
        XCTAssertTrue(merged.verdict(for: field(labels: ["Password"])) != .allowed, "the built-in list still applies")
        XCTAssertThrowsError(try JSONDecoder().decode(HostRules.self, from: Data(#"{"rules": [{"id": "bad", "bundle": "("}]}"#.utf8)), "a broken pattern is refused, not half-loaded")
    }
}
