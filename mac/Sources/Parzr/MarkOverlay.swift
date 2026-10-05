import AppKit
import SwiftUI
import ParzrCore

/// One thing drawn over the editor, in global (AppKit) screen coordinates. Equal shapes keep their layer from one check to the next.
struct MarkShape: Hashable {
    enum Kind { case wash, highlight, underline }
    let kind: Kind
    let rect: CGRect
    /// Style and Tone ink (blue) instead of issue ink (red).
    var style = false
    /// The clickable area of an underline: the word plus the strip the stroke sits in, at least 16 pt wide.
    var hit: CGRect { CGRect(x: rect.minX, y: rect.minY - 5, width: max(16, rect.width), height: rect.height + 5) }
    /// Everything the shape touches on screen.
    var extent: CGRect { kind == .underline ? hit : rect }
}

struct MarkItem {
    var shape: MarkShape
    /// The edit this mark belongs to (underlines and highlights); washes have none.
    var owner = ""
    var label = ""
    var tip = ""
    var press: (() -> Void)?
}

enum MarkDiff {
    /// What must change on screen to go from the shapes already drawn to `new`: the rest keep their layers.
    static func diff(old: Set<MarkShape>, new: [MarkShape]) -> (added: [MarkShape], removed: [MarkShape]) {
        let wanted = Set(new)
        return (new.reduce(into: [MarkShape]()) { if !old.contains($1), !$0.contains($1) { $0.append($1) } }, old.filter { !wanted.contains($0) })
    }
}

/// What assistive tech sees for one underline: a button that opens the same card a click does.
final class MarkElement: NSAccessibilityElement {
    var press: (() -> Void)?
    override func accessibilityPerformPress() -> Bool { guard let press else { return false }; press(); return true }
}

/// Draws every mark of one screen as CALayers in a single view. Hover and press are driven by the controller, because the window only takes mouse events while the pointer is on a mark.
@MainActor
final class MarkView: NSView, NSViewToolTipOwner {
    private let container = CALayer()
    private let hover = CALayer()
    private var layers: [MarkShape: CALayer] = [:]
    private(set) var items: [MarkItem] = []
    private var elements: [MarkElement] = []
    private(set) var hovered: Int?
    private(set) var pressed: Int?
    override var isFlipped: Bool { false }
    override func acceptsFirstMouse(for event: NSEvent?) -> Bool { true }
    override init(frame: NSRect) {
        super.init(frame: frame)
        wantsLayer = true
        // Sublayers use global screen coordinates: the container's bounds origin is the window's origin.
        container.anchorPoint = .zero; container.position = .zero; container.masksToBounds = false
        hover.cornerRadius = 3; hover.zPosition = 1.5; hover.isHidden = true
        layer?.addSublayer(container); container.addSublayer(hover)
    }
    required init?(coder: NSCoder) { fatalError("Created programmatically") }
    private static let issue = NSColor(Color.issueInk), styled = NSColor(Color.styleInk)
    private func ink(_ shape: MarkShape, alpha: CGFloat) -> CGColor {
        var color = CGColor(gray: 0, alpha: 0)
        effectiveAppearance.performAsCurrentDrawingAppearance { color = (shape.style ? Self.styled : Self.issue).withAlphaComponent(alpha).cgColor }
        return color
    }
    private func style(_ layer: CALayer, for shape: MarkShape) {
        switch shape.kind {
        case .wash: layer.backgroundColor = ink(shape, alpha: 0.05); layer.cornerRadius = 3; layer.zPosition = 0
        case .highlight: layer.backgroundColor = ink(shape, alpha: 0.12); layer.cornerRadius = 0; layer.zPosition = 1
        case .underline: layer.backgroundColor = ink(shape, alpha: 1); layer.cornerRadius = 1.5; layer.zPosition = 2
        }
    }
    private func frame(of shape: MarkShape, thick: Bool = false) -> CGRect {
        switch shape.kind {
        case .wash, .highlight: shape.rect
        // A solid, rounded 3 pt stroke, 3.4 pt on hover, centered 1 pt under the word.
        case .underline: CGRect(x: shape.hit.minX, y: shape.rect.minY - 1 - (thick ? 1.7 : 1.5), width: shape.hit.width, height: thick ? 3.4 : 3)
        }
    }
    override func viewDidChangeEffectiveAppearance() {
        super.viewDidChangeEffectiveAppearance()
        CATransaction.begin(); CATransaction.setDisableActions(true)
        for (shape, layer) in layers { style(layer, for: shape) }
        if let hovered { hover.backgroundColor = ink(items[hovered].shape, alpha: 0.22) }
        CATransaction.commit()
    }
    /// Sets the origin of the container to the window's, then brings the layers in line with `items`.
    func apply(_ items: [MarkItem], origin: CGPoint) {
        CATransaction.begin(); CATransaction.setDisableActions(true); defer { CATransaction.commit() }
        container.bounds = CGRect(origin: origin, size: bounds.size)
        let (added, removed) = MarkDiff.diff(old: Set(layers.keys), new: items.map(\.shape))
        for shape in removed { layers.removeValue(forKey: shape)?.removeFromSuperlayer() }
        for shape in added {
            let layer = CALayer(); style(layer, for: shape); layer.frame = frame(of: shape)
            container.addSublayer(layer); layers[shape] = layer
        }
        self.items = items; hovered = nil; pressed = nil; hover.isHidden = true
        elements = []; removeAllToolTips()
        for (index, item) in items.enumerated() where item.shape.kind == .underline {
            addToolTip(item.shape.hit.offsetBy(dx: -origin.x, dy: -origin.y), owner: self, userData: UnsafeMutableRawPointer(bitPattern: index + 1))
        }
    }
    func view(_ view: NSView, stringForToolTip tag: NSView.ToolTipTag, point: NSPoint, userData data: UnsafeMutableRawPointer?) -> String {
        let index = Int(bitPattern: data) - 1
        return items.indices.contains(index) ? items[index].tip : ""
    }
    /// Index of the topmost underline under the global point.
    func hitIndex(at point: CGPoint) -> Int? { items.indices.last { items[$0].shape.kind == .underline && items[$0].shape.hit.contains(point) } }
    func setHover(_ index: Int?) {
        guard index != hovered else { return }
        CATransaction.begin(); CATransaction.setDisableActions(true); defer { CATransaction.commit() }
        if let old = hovered, items.indices.contains(old), let layer = layers[items[old].shape] { layer.frame = frame(of: items[old].shape) }
        hovered = index
        if let index {
            let shape = items[index].shape
            layers[shape]?.frame = frame(of: shape, thick: true)
            hover.backgroundColor = ink(shape, alpha: 0.22); hover.frame = CGRect(x: shape.hit.minX, y: shape.rect.minY, width: shape.hit.width, height: shape.rect.height); hover.isHidden = false
        } else { hover.isHidden = true }
    }
    func element(for owner: String) -> MarkElement? { accessibilityElements().first { $0.accessibilityIdentifier() == owner } }
    private func accessibilityElements() -> [MarkElement] {
        if elements.isEmpty {
            elements = items.compactMap { item in
                guard item.shape.kind == .underline else { return nil }
                let element = MarkElement()
                element.setAccessibilityRole(.button); element.setAccessibilityLabel(item.label); element.setAccessibilityIdentifier(item.owner)
                element.setAccessibilityParent(self); element.setAccessibilityFrame(item.shape.hit); element.press = item.press
                return element
            }
        }
        return elements
    }
    override func accessibilityChildren() -> [Any]? { accessibilityElements() }
    override func isAccessibilityElement() -> Bool { true }
    override func accessibilityRole() -> NSAccessibility.Role? { .group }
    override func accessibilityLabel() -> String? { "Parzr corrections" }
    override func mouseDown(with event: NSEvent) {
        pressed = hitIndex(at: NSEvent.mouseLocation); setHover(pressed)
    }
    override func mouseUp(with event: NSEvent) {
        let target = pressed; pressed = nil
        guard let target, hitIndex(at: NSEvent.mouseLocation) == target else { return }
        items[target].press?()
    }
}

@MainActor
final class MarkWindow: NSPanel {
    let marks = MarkView(frame: .zero)
    override var canBecomeKey: Bool { false }
    init() {
        super.init(contentRect: .zero, styleMask: [.borderless, .nonactivatingPanel], backing: .buffered, defer: false)
        isReleasedWhenClosed = false; level = .floating; isOpaque = false; backgroundColor = .clear; hasShadow = false
        ignoresMouseEvents = true; hidesOnDeactivate = false; acceptsMouseMovedEvents = true
        collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
        contentView = marks
    }
}

/// All marks of the current check, drawn in one transparent click-through window per screen. The window takes mouse events only while the pointer is on an underline.
@MainActor
final class MarkOverlay {
    private var windows: [CGDirectDisplayID: MarkWindow] = [:]
    private var monitors: [Any] = []
    private var cursorIsHand = false
    private(set) var items: [MarkItem] = []
    var hasMarks: Bool { items.contains { $0.shape.kind == .underline } }
    private static func displayID(_ screen: NSScreen) -> CGDirectDisplayID { (screen.deviceDescription[NSDeviceDescriptionKey("NSScreenNumber")] as? NSNumber)?.uint32Value ?? 0 }
    func element(for owner: String) -> MarkElement? { windows.values.lazy.compactMap { $0.marks.element(for: owner) }.first }
    /// Shows exactly `items`: shapes already on screen keep their layers, the rest are added or dropped.
    func apply(_ items: [MarkItem]) {
        self.items = items
        var byScreen: [CGDirectDisplayID: (NSScreen, [MarkItem])] = [:]
        for item in items {
            guard let screen = NSScreen.screens.first(where: { $0.frame.intersects(item.shape.rect) }) ?? NSScreen.main else { continue }
            byScreen[Self.displayID(screen), default: (screen, [])].1.append(item)
        }
        for (id, window) in windows where byScreen[id] == nil { window.orderOut(nil); window.marks.apply([], origin: .zero); window.ignoresMouseEvents = true }
        for (id, (screen, group)) in byScreen {
            let window = windows[id] ?? MarkWindow()
            windows[id] = window
            let box = group.reduce(CGRect.null) { $0.union($1.shape.extent) }.insetBy(dx: -8, dy: -8).intersection(screen.frame)
            if window.frame != box { window.setFrame(box, display: false) }
            window.marks.apply(group, origin: box.origin)
            if !window.isVisible { window.orderFrontRegardless() }
        }
        monitorPointer(hasMarks)
        if hasMarks { pointerMoved() }
    }
    /// Takes the marks off screen but keeps their layers, so showing the same marks again is free.
    func hide() { for window in windows.values { window.orderOut(nil); window.ignoresMouseEvents = true }; monitorPointer(false) }
    func clear() {
        guard !items.isEmpty || !monitors.isEmpty else { return }
        apply([])
    }
    /// Closes the windows for good (the controller is stopping).
    func close() { clear(); for window in windows.values { window.close() }; windows = [:] }
    /// Drops the marks and highlights of the given edits (Ignore), keeping the rest.
    func remove(owners: Set<String>) { apply(items.filter { !owners.contains($0.owner) }) }
    private func monitorPointer(_ on: Bool) {
        if !on { monitors.forEach(NSEvent.removeMonitor); monitors = []; if cursorIsHand { NSCursor.arrow.set(); cursorIsHand = false }; return }
        guard monitors.isEmpty else { return }
        monitors = [NSEvent.addGlobalMonitorForEvents(matching: .mouseMoved) { [weak self] _ in MainActor.assumeIsolated { self?.pointerMoved() } },
                    NSEvent.addLocalMonitorForEvents(matching: .mouseMoved) { [weak self] event in MainActor.assumeIsolated { self?.pointerMoved() }; return event }].compactMap { $0 }
    }
    private func pointerMoved() {
        let point = NSEvent.mouseLocation
        var target: (window: MarkWindow, index: Int)?
        for window in windows.values where window.isVisible { if let index = window.marks.hitIndex(at: point) { target = (window, index) } }
        for window in windows.values {
            window.marks.setHover(window === target?.window ? target?.index : window.marks.pressed)
            // A press in progress keeps the window until the mouse is released.
            if window.marks.pressed == nil { window.ignoresMouseEvents = window !== target?.window }
        }
        if (target != nil) != cursorIsHand { cursorIsHand = target != nil; (cursorIsHand ? NSCursor.pointingHand : NSCursor.arrow).set() }
    }
}
