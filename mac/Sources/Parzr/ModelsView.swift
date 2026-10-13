import AppKit
import ParzrCore
import SwiftUI

extension ModelCenter {
    /// The app's model pack. Self tests, snapshots and `swift test` use the throwaway preferences suite and never start a download on their own.
    static let app = ModelCenter.live(defaults: Preferences.selfTestDefaults ?? .standard)
    /// A normal launch may download (never a self test, a snapshot or `swift test`).
    static var downloadsAllowed: Bool { !Preferences.isSelfTest && !Preferences.underXCTest && !CommandLine.arguments.contains("--health-check") }
}

/// A thin progress bar in the accent colour; indeterminate stripes are avoided so snapshots and reduced motion stay still.
struct ModelProgressBar: View {
    let fraction: Double
    var body: some View {
        GeometryReader { geometry in
            ZStack(alignment: .leading) {
                Capsule().fill(Color.hairline.opacity(0.7))
                Capsule().fill(Color.mintAccent).frame(width: max(4, geometry.size.width * min(1, max(0, fraction))))
            }
        }.frame(height: 4).accessibilityElement().accessibilityLabel("Download progress").accessibilityValue("\(Int(fraction * 100)) percent")
    }
}

/// The pack's state and the one action that fits it: Download, Stop, Try again. Used by the welcome guide, Settings and the popover.
struct ModelStatus: View {
    @ObservedObject var center: ModelCenter
    var compact = false
    var body: some View {
        VStack(alignment: .leading, spacing: compact ? 6 : 8) {
            HStack(alignment: .center, spacing: 8) {
                icon
                Text(title).font(.system(size: compact ? 11 : 12, weight: .medium)).fixedSize(horizontal: false, vertical: true)
                Spacer(minLength: 6)
                action
            }
            if let fraction = center.state.fraction { ModelProgressBar(fraction: fraction) }
            if !compact, let detail { Text(detail).font(.system(size: 11)).foregroundStyle(Color.textSecondary).lineSpacing(2).fixedSize(horizontal: false, vertical: true) }
        }.accessibilityElement(children: .contain)
    }
    private var percent: String { "\(Int((center.state.fraction ?? 0) * 100))%" }
    private var title: String {
        switch center.state {
        case .ready: compact ? "Smart grammar is ready" : "Downloaded and checked"
        case .development: "Development models in use"
        case .downloading(_, let total): compact ? "Smart grammar is downloading · \(percent)" : "Downloading · \(percent) of \(ByteCountFormatter.string(fromByteCount: total, countStyle: .file))"
        case .verifying: compact ? "Smart grammar · checking the download" : "Checking the download…"
        case .missing where center.removedByUser: compact ? "Smart grammar isn't downloaded" : "Not downloaded"
        case .missing: compact ? "Smart grammar downloads soon" : "Waiting to download"
        case .failed: compact ? "Smart grammar isn't downloaded" : "Download paused"
        }
    }
    private var detail: String? {
        switch center.state {
        case .ready: "\(center.sizeText) on this Mac, each file checked against its pinned SHA-256."
        case .development: center.statusLine
        case .downloading, .verifying: nil
        case .missing: center.removedByUser ? "Parzr checks with its rules only until you download it." : "Parzr checks with its rules until it arrives."
        case .failed(let failure): failure.message
        }
    }
    @ViewBuilder private var icon: some View {
        switch center.state {
        case .ready, .development: Image(systemName: "checkmark.circle.fill").foregroundStyle(Color.mintAccent)
        case .downloading, .verifying: Image(systemName: "arrow.down.circle").foregroundStyle(Color.mintAccent)
        case .missing: Image(systemName: "arrow.down.circle").foregroundStyle(Color.textSecondary)
        case .failed: Image(systemName: "exclamationmark.circle").foregroundStyle(Color.errorInk)
        }
    }
    @ViewBuilder private var action: some View {
        switch center.state {
        case .downloading: NativeButton(title: "Stop", kind: .utility, label: "Stop the model download", action: { center.cancel() }).fixedSize()
        case .missing: NativeButton(title: "Download", kind: compact ? .secondary : .primary, label: "Download the models", action: { center.start(userInitiated: true) }).fixedSize()
        case .failed: NativeButton(title: "Try again", label: "Try the model download again", action: { center.start(userInitiated: true) }).fixedSize()
        case .ready, .verifying, .development: EmptyView()
        }
    }
}

/// Settings, Models: what is on this Mac, how big, under which license, and Re-download / Remove.
struct ModelsSettings: View {
    @ObservedObject var center: ModelCenter
    @State private var confirmRemove = false
    var body: some View {
        VStack(alignment: .leading, spacing: 22) {
            section(center.pack?.title.uppercased() ?? "MODELS") {
                VStack(alignment: .leading, spacing: 10) {
                    Text(center.pack?.purpose ?? "").font(.system(size: 11)).foregroundStyle(Color.textSecondary).lineSpacing(2).fixedSize(horizontal: false, vertical: true)
                    ModelStatus(center: center)
                }.padding(16)
                divider
                ForEach(Array(center.models.enumerated()), id: \.offset) { index, model in
                    if index > 0 { divider }
                    HStack(alignment: .top, spacing: 18) {
                        VStack(alignment: .leading, spacing: 4) {
                            Text(model.name).font(.system(size: 12, weight: .medium))
                            Text(model.purpose).font(.system(size: 11)).foregroundStyle(Color.textSecondary)
                            Text("\(model.license) · \(model.version)").font(.system(size: 10)).foregroundStyle(Color.textSecondary.opacity(0.8)).lineLimit(2).fixedSize(horizontal: false, vertical: true)
                        }
                        Spacer(minLength: 8)
                        Text(ByteCountFormatter.string(fromByteCount: model.bytes, countStyle: .file)).font(.system(size: 11)).monospacedDigit().foregroundStyle(Color.textSecondary)
                    }.padding(16)
                }
            }
            section("MANAGE") {
                row("Download again", detail: "Deletes the downloaded files and fetches them again from GitHub, checking each one.") {
                    NativeButton(title: "Re-download", label: "Download the models again", enabled: center.pack != nil && !center.state.isWorking && center.state != .development, action: { center.redownload() }).fixedSize()
                }
                divider
                row("Remove from this Mac", detail: "Frees \(center.sizeText). Parzr then checks with its rules only, and does not download the models again until you ask.") {
                    NativeButton(title: "Remove", label: "Remove the models", enabled: center.pack != nil && center.state != .development, action: { confirmRemove = true }).fixedSize()
                }
            }
            HStack(alignment: .top, spacing: 9) {
                Image(systemName: "lock").foregroundStyle(Color.mintAccent)
                Text("The download is a plain HTTPS request to GitHub for these files, nothing else. It carries nothing about you or your writing. Each file is checked against the SHA-256 pinned in this version of Parzr before it is used. The models are stored in ~/Library/Application Support/Parzr/Models.").font(.system(size: 11)).foregroundStyle(Color.textSecondary).lineSpacing(3).fixedSize(horizontal: false, vertical: true)
            }.padding(14).frame(maxWidth: .infinity, alignment: .leading).background(Color.accentWash.opacity(0.4), in: RoundedRectangle(cornerRadius: 10))
        }
        .confirmationDialog("Remove the models?", isPresented: $confirmRemove) {
            Button("Remove", role: .destructive) { center.remove() }
            Button("Cancel", role: .cancel) {}
        } message: { Text("Smart grammar and rewrites stop until you download them again (\(center.sizeText)).") }
    }
    private var divider: some View { Rectangle().fill(Color.hairline.opacity(0.5)).frame(height: 0.5).padding(.horizontal, 16) }
    private func section<Content: View>(_ title: String, @ViewBuilder content: () -> Content) -> some View {
        VStack(alignment: .leading, spacing: 9) { Text(title).font(.system(size: 9, weight: .semibold)).tracking(1.2).foregroundStyle(Color.textSecondary).padding(.leading, 2); VStack(spacing: 0, content: content).graphiteSurface() }
    }
    private func row<Control: View>(_ title: String, detail: String, @ViewBuilder control: () -> Control) -> some View {
        HStack(alignment: .center, spacing: 18) { VStack(alignment: .leading, spacing: 5) { Text(title).font(.system(size: 12, weight: .medium)); Text(detail).font(.system(size: 11)).foregroundStyle(Color.textSecondary).fixedSize(horizontal: false, vertical: true).lineSpacing(2) }; Spacer(minLength: 8); control() }.padding(16)
    }
}
