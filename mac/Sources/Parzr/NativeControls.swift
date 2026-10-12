import AppKit
import ParzrCore

/// Access the same native accessibility actions used by keyboard and assistive input.
@MainActor
enum NativeControls {
    static func snapshot(_ view: NSView, to url: URL) throws {
        view.layoutSubtreeIfNeeded()
        guard let bitmap = view.bitmapImageRepForCachingDisplay(in: view.bounds) else { throw ParzrError.message("Could not capture the native view.") }
        view.cacheDisplay(in: view.bounds, to: bitmap)
        guard let png = bitmap.representation(using: .png, properties: [:]) else { throw ParzrError.message("Could not encode the native view.") }
        try png.write(to: url)
    }
    /// Depth-first search for a control by its accessibility label or title. A plain loop over an explicit stack:
    /// the nested recursive function this replaced crashed the Swift 6.3 compiler in release builds.
    static func find(label: String, in root: Any) -> (any NSAccessibilityProtocol)? {
        var visited: Set<ObjectIdentifier> = []
        var stack: [(object: Any, depth: Int)] = [(root, 0)]
        while let (object, depth) = stack.popLast() {
            guard depth < 48, let control = object as? any NSAccessibilityProtocol else { continue }
            guard visited.insert(ObjectIdentifier(control as AnyObject)).inserted else { continue }
            if (control.accessibilityLabel() ?? control.accessibilityTitle()) == label { return control }
            var children: [Any] = control.accessibilityChildren() ?? []
            if let view = object as? NSView { children += view.subviews as [Any] }
            // Reversed, so the first child is visited first, as the recursive search did.
            stack += children.reversed().map { ($0, depth + 1) }
        }
        return nil
    }
}
