import AppKit
import SwiftUI

/// AppKit owns hit testing, focus rings, disabled states and activation for app actions.
struct NativeButton: NSViewRepresentable {
    enum Kind { case primary, secondary, utility }
    let title: String
    var kind: Kind = .secondary
    var symbol: String? = nil
    var label: String? = nil
    var key: String = ""
    var enabled = true
    var action: () -> Void
    @Environment(\.isEnabled) private var environmentEnabled
    func makeCoordinator() -> Coordinator { Coordinator(action) }
    func makeNSView(context: Context) -> NSButton {
        let button = ActionButton(); button.target = context.coordinator; button.action = #selector(Coordinator.activateAction)
        button.controlSize = .small; button.bezelStyle = .rounded; button.imageHugsTitle = true
        button.focusRingType = .exterior
        button.font = .systemFont(ofSize: 12, weight: .medium)
        button.cell?.lineBreakMode = .byTruncatingTail
        button.setContentCompressionResistancePriority(.defaultLow, for: .horizontal)
        button.setContentHuggingPriority(.required, for: .horizontal)
        return button
    }
    func updateNSView(_ button: NSButton, context: Context) {
        context.coordinator.action = action
        button.title = title; button.isEnabled = enabled && environmentEnabled
        button.isBordered = false
        (button as? ActionButton)?.visualKind = kind
        let ink = kind == .primary && button.isEnabled ? NSColor(Color.onAccent) : NSColor(Color.textPrimary)
        button.contentTintColor = ink
        button.attributedTitle = NSAttributedString(string: symbol != nil && !title.isEmpty ? " " + title : title, attributes: [.font: button.font ?? .systemFont(ofSize: 12), .foregroundColor: ink.withAlphaComponent(button.isEnabled ? 1 : 0.4)])
        button.image = symbol.flatMap { NSImage(systemSymbolName: $0, accessibilityDescription: nil) }
        button.imagePosition = symbol == nil ? .noImage : title.isEmpty ? .imageOnly : .imageLeading
        button.keyEquivalent = key; button.keyEquivalentModifierMask = []
        button.setAccessibilityLabel(label ?? title)
    }
    func sizeThatFits(_ proposal: ProposedViewSize, nsView: NSButton, context: Context) -> CGSize? {
        let intrinsic = nsView.intrinsicContentSize
        return CGSize(width: min(max(title.isEmpty ? 24 : 44, intrinsic.width + (kind == .utility ? (title.isEmpty ? 0 : 16) : 24)), proposal.width ?? 220), height: kind == .utility ? 24 : 28)
    }
    @MainActor final class Coordinator: NSObject {
        var action: () -> Void
        init(_ action: @escaping () -> Void) { self.action = action }
        @objc func activateAction() { action() }
    }
}

@MainActor
class ActionButton: NSButton {
    var visualKind: NativeButton.Kind? { didSet { needsDisplay = true } }
    private var hover = false
    private var hoverArea: NSTrackingArea?
    override func updateTrackingAreas() {
        super.updateTrackingAreas()
        if let hoverArea { removeTrackingArea(hoverArea) }
        let area = NSTrackingArea(rect: bounds, options: [.mouseEnteredAndExited, .activeInActiveApp, .inVisibleRect], owner: self)
        addTrackingArea(area); hoverArea = area
    }
    override func mouseEntered(with event: NSEvent) { hover = true; needsDisplay = true }
    override func mouseExited(with event: NSEvent) { hover = false; needsDisplay = true }
    override func draw(_ dirtyRect: NSRect) {
        if let kind = visualKind {
            let path = NSBezierPath(roundedRect: bounds.insetBy(dx: 0.5, dy: 1), xRadius: 6, yRadius: 6)
            let active = isEnabled && (hover || isHighlighted)
            let color: NSColor
            if kind == .primary { color = isEnabled ? NSColor(Color.mintAccent).withAlphaComponent(isHighlighted ? 0.8 : 1) : NSColor(Color.textSecondary).withAlphaComponent(0.1) }
            else { color = NSColor(Color.textPrimary).withAlphaComponent(kind == .utility ? active ? 0.07 : 0 : active ? 0.11 : 0.06) }
            color.setFill(); path.fill()
            if kind == .secondary { NSColor(Color.hairline).withAlphaComponent(isEnabled ? 0.6 : 0.3).setStroke(); path.lineWidth = 0.5; path.stroke() }
        }
        super.draw(dirtyRect)
    }
    override func accessibilityPerformPress() -> Bool {
        guard isEnabled, action != nil else { return false }
        performClick(nil)
        return true
    }
}

@MainActor
final class UnderlineButton: ActionButton {
    var onPress: (() -> Void)?
    private var hovering = false
    private var wordArea: NSTrackingArea?
    init(label: String, action: @escaping () -> Void) {
        super.init(frame: .zero)
        title = ""; isBordered = false; setButtonType(.momentaryPushIn)
        setAccessibilityLabel(label); target = self; self.action = #selector(pressUnderline)
        onPress = action
    }
    required init?(coder: NSCoder) { fatalError("Created programmatically") }
    override func updateTrackingAreas() {
        super.updateTrackingAreas()
        if let wordArea { removeTrackingArea(wordArea) }
        // The host app is active, so hover must track regardless of Parzr's activation.
        let area = NSTrackingArea(rect: bounds, options: [.mouseEnteredAndExited, .activeAlways, .inVisibleRect], owner: self)
        addTrackingArea(area); wordArea = area
    }
    override func mouseEntered(with event: NSEvent) { hovering = true; needsDisplay = true; NSCursor.pointingHand.set() }
    override func mouseExited(with event: NSEvent) { hovering = false; needsDisplay = true; NSCursor.arrow.set() }
    override func draw(_ dirtyRect: NSRect) {
        if hovering || isHighlighted {
            let word = NSRect(x: 0, y: isFlipped ? 0 : 5, width: bounds.width, height: max(0, bounds.height - 5))
            NSColor(Color.correctionInk).withAlphaComponent(0.14).setFill()
            NSBezierPath(roundedRect: word, xRadius: 3, yRadius: 3).fill()
        }
        NSColor(Color.correctionInk).setStroke()
        let path = NSBezierPath(); path.lineWidth = isHighlighted ? 2.2 : 1.7; path.lineCapStyle = .round
        path.setLineDash([1, 3], count: 2, phase: 0)
        let y = isFlipped ? bounds.maxY - 5 : 5
        path.move(to: NSPoint(x: 1, y: y)); path.line(to: NSPoint(x: bounds.maxX - 1, y: y)); path.stroke()
    }
    @objc private func pressUnderline() { onPress?() }
}
