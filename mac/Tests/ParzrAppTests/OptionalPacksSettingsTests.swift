import XCTest
import AppKit
import SwiftUI
import ParzrCore
@testable import Parzr

/// Settings, Models lists every optional pack (slip check, tone check) under the essential one, each with its own Remove.
/// Headless: the view is laid out in a window that is never shown.
@MainActor
final class OptionalPacksSettingsTests: XCTestCase {
    private func center(_ id: String, _ role: String, _ optional: OptionalPack?, defaults: UserDefaults) -> ModelCenter {
        let file = ModelFile(path: "\(id)/model.bin", url: "https://github.com/jn-aman/parzr/releases/download/models-\(id)-1/\(id).model.bin", bytes: 1000,
                             sha256: String(repeating: "a", count: 64), name: "\(id) model", version: "test", license: "Apache-2.0", purpose: "test")
        let pack = ModelPack(id: id, version: "1", title: id.capitalized, purpose: "Test pack.", provides: [role: id], files: [file])
        let root = FileManager.default.temporaryDirectory.appendingPathComponent("parzr-optional-\(UUID().uuidString)")
        let center = ModelCenter(pack: pack, store: ModelStore(root: root, transport: URLSessionTransport()), defaults: defaults, optional: optional)
        center.preview(.ready)
        return center
    }

    func testEveryOptionalPackHasItsOwnSectionAndRemove() throws {
        let defaults = try XCTUnwrap(UserDefaults(suiteName: "parzr-optional-settings-tests"))
        defer { defaults.removePersistentDomain(forName: "parzr-optional-settings-tests") }
        let essential = center("essential", "writing_model", nil, defaults: defaults)
        let optional = [center("slips", "slip_model", .slips, defaults: defaults), center("tone", "tone_model", .tone, defaults: defaults)]
        let host = NSHostingView(rootView: ScrollView { ModelsSettings(center: essential, optional: optional) }.frame(width: 640, height: 1400))
        let window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 640, height: 1400), styleMask: [.borderless], backing: .buffered, defer: false)
        window.isReleasedWhenClosed = false; window.contentView = host
        window.layoutIfNeeded(); host.layoutSubtreeIfNeeded()
        RunLoop.current.run(until: Date().addingTimeInterval(0.1))
        XCTAssertNotNil(NativeControls.find(label: "Remove the slip check model", in: host))
        XCTAssertNotNil(NativeControls.find(label: "Remove the tone check model", in: host))
        XCTAssertNotNil(NativeControls.find(label: "Remove the models", in: host), "the essential pack keeps its own Remove under Manage")
        XCTAssertFalse(window.isVisible)
        window.close()
    }

    func testAnOptionalPackSaysWhatHappensWithoutIt() throws {
        let defaults = try XCTUnwrap(UserDefaults(suiteName: "parzr-optional-notes-tests"))
        defer { defaults.removePersistentDomain(forName: "parzr-optional-notes-tests") }
        let tone = center("tone", "tone_model", .tone, defaults: defaults)
        tone.preview(.missing)
        XCTAssertFalse(tone.removedByUser)
        tone.preview(.missing, removed: true)
        XCTAssertTrue(tone.removedByUser)
        XCTAssertEqual(tone.optional?.removedNote, OptionalPack.tone.removedNote)
    }
}
