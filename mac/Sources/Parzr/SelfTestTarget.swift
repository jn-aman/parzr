import AppKit

/// Test-only seam. The editor self tests (`--paste-test`, `--typing-test`, `--grammar-typing-test`, `--integration-test`) drive a fixture editor process
/// (`ParzrFixture`) that is never frontmost and whose window sits outside every screen, so they can never disturb the person using the Mac.
/// Parzr normally checks the frontmost app on the screens; while a self test has set a target it checks that app, on its stage, instead.
/// Nothing sets a target outside a self test (the setter refuses), so product behaviour is unchanged.
@MainActor
enum SelfTestTarget {
    private(set) static var app: NSRunningApplication?
    /// The fixture's off-screen window in Cocoa coordinates: one more place marks and the card may be drawn.
    private(set) static var stage: CGRect?

    static func watch(_ app: NSRunningApplication, stage: CGRect) {
        precondition(Preferences.isSelfTest, "SelfTestTarget is for self tests only")
        self.app = app; self.stage = stage
    }
    static func clear() { app = nil; stage = nil }

    /// Applying a fix first brings the editor's app forward; a fixture is never brought forward (it must stay in the background).
    static func bringForward(_ app: NSRunningApplication) { if self.app == nil { app.activate(options: []) } }
    /// The app Parzr checks: the frontmost one, or the self test's fixture.
    static var watched: NSRunningApplication? { app ?? NSWorkspace.shared.frontmostApplication }
    /// A rect Parzr may draw on: inside a screen's visible frame, or on the stage.
    static func shows(_ rect: CGRect) -> Bool { NSScreen.screens.contains { $0.visibleFrame.contains(rect) } || stage?.contains(rect) == true }
    /// Where the card may sit for an anchor: the stage when the anchor is on it, otherwise the visible frame of its screen.
    static func visibleFrame(for anchor: CGRect) -> CGRect? {
        if let stage, stage.intersects(anchor) { return stage }
        return (NSScreen.screens.first { $0.frame.intersects(anchor) } ?? NSScreen.main)?.visibleFrame
    }
    /// The identity and frame of the surface a mark lies on (a display, or the stage).
    static func surface(for rect: CGRect) -> (id: CGDirectDisplayID, frame: CGRect)? {
        if let stage, stage.intersects(rect) { return (.max, stage) }
        guard let screen = NSScreen.screens.first(where: { $0.frame.intersects(rect) }) ?? NSScreen.main else { return nil }
        return ((screen.deviceDescription[NSDeviceDescriptionKey("NSScreenNumber")] as? NSNumber)?.uint32Value ?? 0, screen.frame)
    }
}
