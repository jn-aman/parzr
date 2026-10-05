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
    static func find(label: String, in root: Any) -> (any NSAccessibilityProtocol)? {
        var visited: Set<ObjectIdentifier> = []
        func visit(_ object: Any, depth: Int) -> (any NSAccessibilityProtocol)? {
            guard depth < 48, let control = object as? any NSAccessibilityProtocol else { return nil }
            let identity = ObjectIdentifier(control as AnyObject)
            guard visited.insert(identity).inserted else { return nil }
            let name = control.accessibilityLabel() ?? control.accessibilityTitle()
            if name == label { return control }
            for child in control.accessibilityChildren() ?? [] {
                if let found = visit(child, depth: depth + 1) { return found }
            }
            if let view = object as? NSView {
                for child in view.subviews { if let found = visit(child, depth: depth + 1) { return found } }
            }
            return nil
        }
        return visit(root, depth: 0)
    }
}
