import XCTest
import ParzrCore
@testable import Parzr

@MainActor
final class ReportsTests: XCTestCase {
    private func prefs() throws -> (Preferences, () -> Void) {
        let name = "app.parzr.tests.reports"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: name)); defaults.removePersistentDomain(forName: name)
        return (Preferences(defaults: defaults), { defaults.removePersistentDomain(forName: name) })
    }
    func testReportsAreOnByDefaultAndTheChoiceIsKept() throws {
        let (preferences, cleanup) = try prefs(); defer { cleanup() }
        XCTAssertTrue(preferences.shareReports, "reports are opt-out")
        preferences.shareReports = false
        let again = Preferences(defaults: try XCTUnwrap(UserDefaults(suiteName: "app.parzr.tests.reports")))
        XCTAssertFalse(again.shareReports)
    }
    func testTestsNeverReport() {
        XCTAssertNil(Reports.center, "swift test and self tests must never send anything")
        XCTAssertFalse(Reports.available)
        XCTAssertFalse(AppModel().canReport)
    }
    func testOnlyAnHTTPSEndpointIsUsed() {
        XCTAssertEqual(Reports.endpoint("https://reports.parzr.app/v1/reports")?.host, "reports.parzr.app")
        XCTAssertNil(Reports.endpoint("http://reports.parzr.app/v1/reports"))
        XCTAssertNil(Reports.endpoint("reports.parzr.app"))
        XCTAssertNil(Reports.endpoint(""))
        XCTAssertNil(Reports.endpoint(nil))
        XCTAssertNil(Reports.endpoint(42))
    }
    func testReportsNeverComeFromExcludedAppsOrBlockedOrSecureFields() {
        func allowed(_ bundle: String? = "com.apple.Notes", rules: Bool = false, enabled: Bool = true, secure: Bool = false, verdict: HostRules.Verdict = .allowed, copied: Bool = false) -> Bool {
            Compat.reportsAllowed(bundle: bundle, excludedByRules: rules, enabled: enabled, secure: secure, verdict: verdict, copied: copied)
        }
        XCTAssertTrue(allowed())
        XCTAssertFalse(allowed("com.apple.Terminal"), "a terminal is on the exclusion list")
        XCTAssertFalse(allowed("com.jetbrains.intellij"), "so are JetBrains IDEs")
        XCTAssertFalse(allowed(rules: true), "an app a host rule turns off")
        XCTAssertFalse(allowed(enabled: false), "an app the writer turned off")
        XCTAssertFalse(allowed(secure: true), "a secure field, or while secure input is on")
        XCTAssertFalse(allowed(verdict: .blocked("sensitive:otp")), "a field the sensitive-field keywords block, even through Option+Space")
        XCTAssertFalse(allowed(verdict: .blocked("rule:x")), "a field a host rule blocks")
        XCTAssertFalse(allowed(copied: true), "text read by copying: its field is unknown")
        XCTAssertFalse(allowed(nil)); XCTAssertFalse(allowed(""))
    }
    func testTheReportSwitchFollowsTheText() {
        let model = AppModel()
        XCTAssertFalse(model.sourceReportable, "nothing to report before any text")
        model.playground("I has it.")
        XCTAssertTrue(model.sourceReportable, "Parzr's own writing space may report")
        model.clearSession()
        XCTAssertFalse(model.sourceReportable)
        XCTAssertFalse(model.canReport, "and never under tests")
    }
    func testThePrivacyPageIsHTTPS() {
        XCTAssertEqual(Reports.privacyURL.scheme, "https")
        XCTAssertEqual(Reports.privacyURL.absoluteString, "https://parzr.app/privacy")
    }
    func testTheReportsCopyIsHonest() {
        let detail = StudioView.reportsDetail
        for phrase in ["Only when you click Report wrong suggestion", "up to about 240 characters", "removes names it recognises, emails, phone numbers, other numbers, links and keys", "sent as written", "180 days", "Cloudflare", "can't be found or deleted individually", "Ignoring or accepting a suggestion sends nothing"] {
            XCTAssertTrue(detail.contains(phrase), phrase)
        }
        XCTAssertFalse(detail.contains("ignore a suggestion or report"), "Ignore no longer sends anything")
    }
    func testTheWelcomeGuideSampleIsNeverReported() {
        XCTAssertFalse(OnboardingModel().editor.reports)
        XCTAssertTrue(AppModel().reports)
    }
    func testTheBundledEndpointIsHTTPSWhenPresent() throws {
        // Release builds name no endpoint until the reports Worker is deployed; when they do, it is HTTPS.
        var directory = URL(fileURLWithPath: #filePath)
        while directory.path != "/" && !FileManager.default.fileExists(atPath: directory.appendingPathComponent("resources/Info.plist").path) { directory.deleteLastPathComponent() }
        let data = try Data(contentsOf: directory.appendingPathComponent("resources/Info.plist"))
        let info = try XCTUnwrap(PropertyListSerialization.propertyList(from: data, format: nil) as? [String: Any])
        if let value = info[Reports.endpointKey] { XCTAssertNotNil(Reports.endpoint(value)) }
    }
}
