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
    func testTheWelcomeGuideSampleIsNeverReported() {
        XCTAssertFalse(OnboardingModel().editor.reports)
        XCTAssertTrue(AppModel().reports)
    }
    func testTheBundledEndpointIsHTTPS() throws {
        // The repository's Info.plist (what release builds ship) names an HTTPS endpoint.
        var directory = URL(fileURLWithPath: #filePath)
        while directory.path != "/" && !FileManager.default.fileExists(atPath: directory.appendingPathComponent("resources/Info.plist").path) { directory.deleteLastPathComponent() }
        let data = try Data(contentsOf: directory.appendingPathComponent("resources/Info.plist"))
        let info = try XCTUnwrap(PropertyListSerialization.propertyList(from: data, format: nil) as? [String: Any])
        XCTAssertNotNil(Reports.endpoint(info[Reports.endpointKey]))
    }
}
