import SwiftUI
import AppKit

extension Color {
    private static func adaptive(_ dark: UInt32, _ light: UInt32) -> Color {
        Color(NSColor(name: nil) { appearance in
            let rgb = appearance.bestMatch(from: [.darkAqua, .aqua]) == .darkAqua ? dark : light
            return NSColor(red: Double((rgb >> 16) & 255) / 255, green: Double((rgb >> 8) & 255) / 255, blue: Double(rgb & 255) / 255, alpha: 1)
        })
    }
    static let canvas = adaptive(0x202629, 0xF5F5F1)
    static let surface = adaptive(0x292F32, 0xFFFFFF)
    static let writingSurface = adaptive(0x191F22, 0xFFFFFF)
    static let sidebar = adaptive(0x1A2023, 0xEDEEE9)
    static let textPrimary = adaptive(0xEAF0EB, 0x202A24)
    static let textSecondary = adaptive(0xA7B4AE, 0x64736B)
    static let mintAccent = adaptive(0xA8ECC4, 0x24754D)
    static let accentWash = adaptive(0x31473C, 0xDFEEE2)
    static let onAccent = adaptive(0x153C28, 0xFFFFFF)
    static let hairline = adaptive(0x394144, 0xDDE2DC)
    static let errorInk = adaptive(0xE6C28B, 0x876321)
    static let correctionInk = adaptive(0xA8ECC4, 0x24754D)
}
struct GraphiteSurface: ViewModifier {
    var radius: CGFloat = 12
    func body(content: Content) -> some View {
        content.background(Color.surface, in: RoundedRectangle(cornerRadius: radius))
            .overlay(RoundedRectangle(cornerRadius: radius).strokeBorder(Color.hairline.opacity(0.7), lineWidth: 0.5))
    }
}
extension View { func graphiteSurface(radius: CGFloat = 12) -> some View { modifier(GraphiteSurface(radius: radius)) } }
struct Brand: View {
    @MainActor private static let icon = Bundle.main.resourceURL.flatMap { NSImage(contentsOf: $0.appendingPathComponent("Brand/ParzrIcon.png")) }
    var inverted = false
    var body: some View {
        HStack(spacing: 10) {
            if let icon = Self.icon {
                Image(nsImage: icon).resizable().interpolation(.high).frame(width: 36, height: 36)
            } else {
                ParzrMark().fill(Color.mintAccent, style: FillStyle(eoFill: true)).frame(width: 25, height: 29)
            }
            Text("Parzr").font(.system(size: 23, weight: .semibold)).tracking(-0.8)
        }.foregroundStyle(inverted ? Color.white : .textPrimary).accessibilityElement(children: .ignore).accessibilityLabel("Parzr")
    }
}
/// The small-size counterpart of the folded P app icon, with a separate underline.
struct ParzrMark: Shape {
    func path(in r: CGRect) -> Path {
        var p = Path()
        func point(_ x: CGFloat, _ y: CGFloat) -> CGPoint { CGPoint(x: r.minX + r.width * x, y: r.minY + r.height * y) }
        p.move(to: point(0.16, 0.90)); p.addLine(to: point(0.16, 0.23))
        p.addQuadCurve(to: point(0.28, 0.12), control: point(0.16, 0.12))
        p.addLine(to: point(0.53, 0.12)); p.addCurve(to: point(0.85, 0.36), control1: point(0.78, 0.12), control2: point(0.85, 0.22))
        p.addCurve(to: point(0.54, 0.64), control1: point(0.85, 0.51), control2: point(0.69, 0.60))
        p.addLine(to: point(0.35, 0.71)); p.addLine(to: point(0.35, 0.90)); p.closeSubpath()
        p.move(to: point(0.35, 0.31)); p.addLine(to: point(0.35, 0.50)); p.addLine(to: point(0.55, 0.44))
        p.addQuadCurve(to: point(0.65, 0.36), control: point(0.65, 0.42)); p.addQuadCurve(to: point(0.54, 0.29), control: point(0.65, 0.29)); p.closeSubpath()
        p.addRoundedRect(in: CGRect(x: r.minX + r.width * 0.48, y: r.minY + r.height * 0.80, width: r.width * 0.42, height: r.height * 0.10), cornerSize: CGSize(width: r.width * 0.05, height: r.height * 0.05))
        return p
    }
    @MainActor static func menuImage(paused: Bool = false) -> NSImage {
        let image = NSImage(size: NSSize(width: 18, height: 20), flipped: true) { rect in
            NSColor.labelColor.setFill()
            if let context = NSGraphicsContext.current?.cgContext { context.addPath(ParzrMark().path(in: rect.insetBy(dx: 1, dy: 1)).cgPath); context.drawPath(using: .eoFill) }
            if paused { NSColor.labelColor.setFill(); NSBezierPath(ovalIn: NSRect(x: 13, y: 0, width: 4, height: 4)).fill() }
            return true
        }
        image.isTemplate = true
        return image
    }
}
struct PrimaryButtonStyle: PrimitiveButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        Button(configuration).buttonStyle(.borderedProminent).tint(Color.mintAccent).foregroundStyle(Color.onAccent).controlSize(.regular)
    }
}
struct SecondaryButtonStyle: PrimitiveButtonStyle {
    func makeBody(configuration: Configuration) -> some View { Button(configuration).buttonStyle(.bordered).controlSize(.regular) }
}
struct StatusLine: View {
    let title: String
    var good = true
    var body: some View {
        HStack(spacing: 6) {
            Circle().fill(good ? Color.mintAccent : Color.errorInk).frame(width: 5, height: 5)
            Text(title).font(.system(size: 11, weight: .medium))
        }.foregroundStyle(Color.textSecondary)
    }
}
