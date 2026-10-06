import AppKit
import Combine
import SwiftUI

/// The one panel for every update state: found, downloading, ready, countdown, and the toasts.
struct UpdatePanelView: View {
    static let width: CGFloat = 380
    @Environment(\.accessibilityReduceMotion) private var systemReduceMotion
    @ObservedObject var model: UpdateModel
    @ObservedObject private var preferences = Preferences.shared
    var renderingSnapshot = false
    private var animate: Bool { !systemReduceMotion && !preferences.reduceMotion && !renderingSnapshot }
    var body: some View {
        VStack(alignment: .leading, spacing: 14) { content }
            .padding(18).frame(width: Self.width, alignment: .leading).background(Color.canvas).foregroundStyle(Color.textPrimary).tint(Color.mintAccent)
            .overlay(RoundedRectangle(cornerRadius: 14).strokeBorder(Color.hairline, lineWidth: 0.7))
            .clipShape(RoundedRectangle(cornerRadius: 14))
            .accessibilityElement(children: .contain)
    }
    @ViewBuilder private var content: some View {
        switch model.phase {
        case .idle: EmptyView()
        case .checking:
            header("arrow.triangle.2.circlepath", "Checking for updates", "Asking GitHub for the latest Parzr.")
            UpdateProgressBar(fraction: nil, animate: animate, label: "Checking for updates")
            actions { Spacer(minLength: 4); NativeButton(title: "Cancel", kind: .secondary, key: "\u{1b}", action: { model.perform(.cancel) }) }
        case .found(let info):
            HStack(spacing: 12) {
                tile("sparkle")
                VStack(alignment: .leading, spacing: 3) {
                    if info.critical { Text("IMPORTANT UPDATE").font(.system(size: 9, weight: .semibold)).tracking(1.4).foregroundStyle(Color.errorInk) }
                    Text("Parzr \(info.version) is here").font(.system(size: 16, weight: .semibold)).tracking(-0.3)
                    Text(["You have \(Support.version)", info.sizeText.map { "\($0) download" }].compactMap { $0 }.joined(separator: " · ")).font(.system(size: 11)).foregroundStyle(Color.textSecondary)
                }
            }.accessibilityElement(children: .combine)
            if let notes = info.notes, !ReleaseNotes.blocks(notes, format: info.notesFormat).isEmpty { notesView(notes, info.notesFormat) }
            actions {
                if !info.critical { NativeButton(title: "Skip this version", kind: .utility, action: { model.perform(.skip) }) }
                Spacer(minLength: 4)
                NativeButton(title: "Later", kind: .secondary, key: "\u{1b}", action: { model.perform(.later) })
                NativeButton(title: "Install and Relaunch", kind: .primary, key: "\r", action: { model.perform(.install) })
            }
        case .downloading(let info, let received, let total):
            header("arrow.down.circle", "Downloading Parzr \(info.version)", UpdateText.progress(received: received, total: total))
            UpdateProgressBar(fraction: total > 0 ? min(1, Double(received) / Double(total)) : nil, animate: animate, label: "Download progress")
            actions { Spacer(minLength: 4); NativeButton(title: "Cancel", kind: .secondary, key: "\u{1b}", action: { model.perform(.cancel) }) }
        case .extracting(let info, let progress):
            header("shippingbox", "Preparing Parzr \(info.version)", "Checking the download and unpacking it.")
            UpdateProgressBar(fraction: progress > 0 ? progress : nil, animate: animate, label: "Preparing the update")
        case .ready(let info):
            header("checkmark.circle", "Restart Parzr to finish", "Parzr \(info.version) is ready. Parzr reopens in a moment.")
            actions {
                Spacer(minLength: 4)
                NativeButton(title: "Later", kind: .secondary, key: "\u{1b}", action: { model.perform(.later) })
                NativeButton(title: "Restart now", kind: .primary, key: "\r", action: { model.perform(.restartNow) })
            }
        case .installing(let info):
            header("arrow.triangle.2.circlepath", "Installing Parzr \(info.version)", "Parzr reopens on its own.")
            UpdateProgressBar(fraction: nil, animate: animate, label: "Installing")
        case .countdown(let info, let seconds):
            header("moon.zzz", "Updating Parzr in \(seconds)s", "Parzr \(info.version) is ready, and you have been away a while.")
            actions {
                Spacer(minLength: 4)
                NativeButton(title: "Cancel", kind: .secondary, key: "\u{1b}", action: { model.perform(.cancelCountdown) })
                NativeButton(title: "Restart now", kind: .primary, key: "\r", action: { model.perform(.restartNow) })
            }
        case .upToDate(let message):
            header("checkmark.circle", "You're up to date", message)
            actions { Spacer(minLength: 4); NativeButton(title: "Done", kind: .primary, key: "\r", action: { model.perform(.dismiss) }) }
        case .failed(let message):
            header("exclamationmark.triangle", "The update did not finish", message, tint: Color.errorInk)
            actions { Spacer(minLength: 4); NativeButton(title: "Dismiss", kind: .secondary, key: "\r", action: { model.perform(.dismiss) }) }
        case .updated(let version):
            header("checkmark.circle", "Updated to Parzr \(version)", "Parzr is ready.")
            actions {
                NativeButton(title: "What's new", kind: .utility, symbol: "arrow.up.right", action: { model.perform(.whatsNew) })
                Spacer(minLength: 4)
                NativeButton(title: "Dismiss", kind: .secondary, key: "\r", action: { model.perform(.dismiss) })
            }
        }
    }
    private func tile(_ symbol: String, tint: Color = .mintAccent) -> some View {
        RoundedRectangle(cornerRadius: 10).fill(Color.accentWash).frame(width: 38, height: 38)
            .overlay(RoundedRectangle(cornerRadius: 10).strokeBorder(Color.mintAccent.opacity(0.25), lineWidth: 0.5))
            .overlay(Image(systemName: symbol).font(.system(size: 16, weight: .medium)).foregroundStyle(tint)).accessibilityHidden(true)
    }
    private func header(_ symbol: String, _ title: String, _ detail: String, tint: Color = .mintAccent) -> some View {
        HStack(alignment: .center, spacing: 12) {
            tile(symbol, tint: tint)
            VStack(alignment: .leading, spacing: 3) {
                Text(title).font(.system(size: 16, weight: .semibold)).tracking(-0.3)
                Text(detail).font(.system(size: 11)).foregroundStyle(Color.textSecondary).lineSpacing(2).fixedSize(horizontal: false, vertical: true).monospacedDigit()
            }
        }.accessibilityElement(children: .combine)
    }
    private func actions<Content: View>(@ViewBuilder _ content: () -> Content) -> some View { HStack(spacing: 8, content: content) }
    /// Markdown only when the appcast says so; anything else is shown as plain text, never as HTML.
    private func rich(_ text: String, _ format: String?) -> AttributedString { format == "markdown" ? ReleaseNotes.inline(text) : AttributedString(text) }
    private func notesView(_ notes: String, _ format: String?) -> some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 7) {
                ForEach(Array(ReleaseNotes.blocks(notes, format: format).enumerated()), id: \.offset) { _, block in
                    switch block {
                    case .heading(let text): Text(rich(text, format)).font(.system(size: 11, weight: .semibold)).padding(.top, 2)
                    case .bullet(let text):
                        HStack(alignment: .firstTextBaseline, spacing: 8) {
                            Circle().fill(Color.mintAccent).frame(width: 4, height: 4).offset(y: -2).accessibilityHidden(true)
                            Text(rich(text, format)).font(.system(size: 12)).lineSpacing(2).fixedSize(horizontal: false, vertical: true)
                        }
                    case .paragraph(let text): Text(rich(text, format)).font(.system(size: 12)).foregroundStyle(Color.textSecondary).lineSpacing(2).fixedSize(horizontal: false, vertical: true)
                    }
                }
            }.frame(maxWidth: .infinity, alignment: .leading).padding(13)
        }.frame(maxHeight: 190).graphiteSurface(radius: 10).accessibilityLabel("Release notes")
    }
}

/// A thin mint bar. Known progress eases between values; unknown progress is a slow sweep (a still half-bar when Reduce Motion is on).
struct UpdateProgressBar: View {
    var fraction: Double?
    var animate: Bool
    var label: String
    @State private var sweep = false
    var body: some View {
        GeometryReader { proxy in
            ZStack(alignment: .leading) {
                Capsule().fill(Color.hairline)
                if let fraction { Capsule().fill(Color.mintAccent).frame(width: max(6, proxy.size.width * fraction)).animation(animate ? .easeOut(duration: 0.3) : nil, value: fraction) }
                else if animate { Capsule().fill(Color.mintAccent).frame(width: proxy.size.width * 0.3).offset(x: sweep ? proxy.size.width * 0.7 : 0).onAppear { withAnimation(.easeInOut(duration: 1.1).repeatForever(autoreverses: true)) { sweep = true } } }
                else { Capsule().fill(Color.mintAccent.opacity(0.5)).frame(width: proxy.size.width * 0.5) }
            }.clipShape(Capsule())
        }.frame(height: 6)
            .accessibilityElement(children: .ignore).accessibilityLabel(label)
            .accessibilityValue(fraction.map { "\(Int($0 * 100)) percent" } ?? "In progress")
    }
}

/// The row at the top of the status popover: a downloaded update to restart into, or one that is waiting to be looked at.
struct UpdateRow: View {
    @ObservedObject var model: UpdateModel
    var body: some View {
        if let row = model.row {
            HStack(spacing: 10) {
                VStack(alignment: .leading, spacing: 2) {
                    switch row {
                    case .restart(let version): Text("Restart to update to \(version)").font(.system(size: 12, weight: .semibold)).fixedSize(horizontal: false, vertical: true); Text("Installs when you quit Parzr.").font(.system(size: 10)).foregroundStyle(Color.textSecondary)
                    case .view(let version, let size): Text("Parzr \(version) is here").font(.system(size: 12, weight: .semibold)); Text(size.map { "\($0) download" } ?? "A new version is ready.").font(.system(size: 10)).foregroundStyle(Color.textSecondary)
                    }
                }
                Spacer(minLength: 4)
                switch row {
                case .restart: NativeButton(title: "Restart", kind: .primary, label: "Restart Parzr to update", action: { model.perform(.restartNow) }).fixedSize()
                case .view: NativeButton(title: "View", kind: .primary, label: "View the new Parzr version", action: { model.perform(.view) }).fixedSize()
                }
            }.padding(12).background(Color.accentWash.opacity(0.5), in: RoundedRectangle(cornerRadius: 12))
                .overlay(RoundedRectangle(cornerRadius: 12).strokeBorder(Color.mintAccent.opacity(0.3), lineWidth: 0.5)).accessibilityElement(children: .contain)
        }
    }
}

/// "Check for Updates…" with the one-line state beside it. Used by the popover and About.
struct UpdateCheckButton: View {
    @ObservedObject var model: UpdateModel
    var kind: NativeButton.Kind = .utility
    var body: some View {
        NativeButton(title: "Check for Updates…", kind: kind, symbol: kind == .utility ? nil : "arrow.triangle.2.circlepath", label: "Check for updates", enabled: model.canCheck && !model.inProgress, action: { model.perform(.check) }).fixedSize()
    }
}

final class UpdatePanel: NSPanel {
    var onCancel: (() -> Void)?
    override var canBecomeKey: Bool { true }
    override var canBecomeMain: Bool { false }
    override func cancelOperation(_ sender: Any?) { onCancel?() }
}

/// Puts the panel under the menu-bar icon, keeps its top edge fixed as the content changes size, and never steals focus unless asked.
@MainActor
final class UpdatePresenter {
    private let model: UpdateModel
    private let anchor: () -> NSRect?
    private var panel: UpdatePanel?
    private var host: NSHostingView<UpdatePanelView>?
    private var subscriptions: Set<AnyCancellable> = []
    private var announced: UpdatePhase?
    #if DEBUG
    /// Off only for the debug update test, which must never take the keyboard from someone working.
    var allowsFocus = true
    #else
    private let allowsFocus = true
    #endif
    init(model: UpdateModel = .shared, anchor: @escaping () -> NSRect?) {
        self.model = model; self.anchor = anchor
        Publishers.CombineLatest3(model.$phase, model.$shown, model.$focus).receive(on: RunLoop.main).sink { [weak self] phase, shown, focus in self?.update(phase: phase, shown: shown, focus: focus) }.store(in: &subscriptions)
    }
    private var motion: Bool { !Preferences.shared.reduceMotion && !NSWorkspace.shared.accessibilityDisplayShouldReduceMotion }
    private func update(phase: UpdatePhase, shown: Bool, focus: Bool) {
        guard shown, phase != .idle else { hide(); return }
        let panel = self.panel ?? makePanel()
        let wasVisible = panel.isVisible, focus = focus && allowsFocus
        resize(panel)
        if !wasVisible {
            if motion { panel.alphaValue = 0 }
            if focus { NSApp.activate(ignoringOtherApps: true); panel.makeKeyAndOrderFront(nil) } else { panel.orderFrontRegardless() }
            if motion { NSAnimationContext.runAnimationGroup { $0.duration = 0.18; panel.animator().alphaValue = 1 } }
        } else if focus, !panel.isKeyWindow { NSApp.activate(ignoringOtherApps: true); panel.makeKeyAndOrderFront(nil) }
        announce(phase, on: panel)
    }
    private func makePanel() -> UpdatePanel {
        let panel = UpdatePanel(contentRect: NSRect(x: 0, y: 0, width: UpdatePanelView.width, height: 120), styleMask: [.borderless, .nonactivatingPanel], backing: .buffered, defer: false)
        panel.level = .floating; panel.isOpaque = false; panel.backgroundColor = .clear; panel.hasShadow = true; panel.isReleasedWhenClosed = false; panel.hidesOnDeactivate = false
        panel.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]; panel.setAccessibilityLabel("Parzr update")
        panel.onCancel = { [weak self] in
            switch self?.model.phase {
            case .found, .ready: self?.model.perform(.later)
            case .checking, .downloading: self?.model.perform(.cancel)
            case .countdown: self?.model.perform(.cancelCountdown)
            default: self?.model.perform(.dismiss)
            }
        }
        let host = NSHostingView(rootView: UpdatePanelView(model: model)); host.wantsLayer = true; host.layer?.cornerRadius = 14; host.layer?.masksToBounds = true
        panel.contentView = host; self.panel = panel; self.host = host
        return panel
    }
    /// Fit to the content, anchored by the top-right corner under the menu-bar icon (or the screen's top right when there is none).
    private func resize(_ panel: UpdatePanel) {
        guard let host else { return }
        host.layoutSubtreeIfNeeded()
        let size = host.fittingSize
        let screen = NSScreen.screens.first(where: { $0.frame.contains(anchor()?.origin ?? .zero) }) ?? NSScreen.main ?? NSScreen.screens[0]
        let visible = screen.visibleFrame
        // A status item the menu bar has hidden (too many icons, the notch) reports a frame near the left edge: ignore it.
        let icon = anchor().flatMap { $0.minX > screen.frame.midX ? $0 : nil }
        let top = panel.isVisible ? panel.frame.maxY : visible.maxY - 8
        let right = panel.isVisible ? panel.frame.maxX : min(visible.maxX - 12, (icon?.maxX ?? visible.maxX) - 4)
        panel.setFrame(NSRect(x: max(visible.minX + 8, right - size.width), y: max(visible.minY + 8, top - size.height), width: size.width, height: size.height), display: true)
    }
    private func hide() {
        guard let panel, panel.isVisible else { return }
        announced = nil
        if motion { NSAnimationContext.runAnimationGroup({ $0.duration = 0.14; panel.animator().alphaValue = 0 }, completionHandler: { MainActor.assumeIsolated { if !self.model.shown { panel.orderOut(nil) } } }) } else { panel.orderOut(nil) }
    }
    /// VoiceOver hears the moments that matter without the panel taking focus.
    private func announce(_ phase: UpdatePhase, on panel: UpdatePanel) {
        let words: String
        switch phase {
        case .found(let info): words = "Parzr \(info.version) is available"
        case .ready: words = "Update ready. Restart Parzr to finish."
        case .countdown(let info, _): words = "Parzr will restart to update to \(info.version) in \(UpdatePolicy.countdown) seconds"
        case .upToDate: words = "Parzr is up to date"
        case .failed(let message): words = message
        case .updated(let version): words = "Updated to Parzr \(version)"
        default: return
        }
        let key = { () -> UpdatePhase in if case .countdown(let info, _) = phase { return .countdown(info, seconds: 0) }; return phase }()
        guard announced != key else { return }
        announced = key
        NSAccessibility.post(element: panel, notification: .announcementRequested, userInfo: [.announcement: words, .priority: NSAccessibilityPriorityLevel.high.rawValue])
    }
}
