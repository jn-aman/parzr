import AppKit
import ParzrCore
import SwiftUI

extension ModelCenter {
    /// The app's model pack. Self tests, snapshots and `swift test` use the throwaway preferences suite and never start a download on their own.
    static let app = ModelCenter.live(defaults: Preferences.selfTestDefaults ?? .standard)
    /// One center per optional pack (`OptionalPack.all`), in Settings order; a pack this build does not pin is left out.
    static let optionalCenters: [ModelCenter] = OptionalPack.all.compactMap { ModelCenter.live($0, defaults: Preferences.selfTestDefaults ?? .standard) }
    /// The slip check's pack (the typing-time word-choice check), downloaded after the essential pack while Slip check is on.
    static var slips: ModelCenter? { optionalCenters.first { $0.optional == OptionalPack.slips } }
    /// The tone check's pack, downloaded after the essential pack while Tone check is on. PARZR_TONE_DIR points at a local copy instead.
    static var tone: ModelCenter? { optionalCenters.first { $0.optional == OptionalPack.tone } }
    /// A normal launch may download (never a self test, a snapshot or `swift test`).
    static var downloadsAllowed: Bool { !Preferences.isSelfTest && !Preferences.underXCTest && !CommandLine.arguments.contains("--health-check") }
}

/// Each optional check's switch in Settings, Writing, and the download policy that follows it. A switched-on check
/// downloads its pack after the essential pack (never after the user's Remove); switching a check on again asks for a
/// missing pack; switching it off only stops the check, and its files stay until Remove in Settings, Models.
@MainActor
enum OptionalChecks {
    /// Whether the check that uses `pack` is switched on.
    static func isOn(_ pack: OptionalPack?, preferences: Preferences = .shared) -> Bool {
        switch pack?.role {
        case OptionalPack.slips.role?: preferences.slipCheck
        case OptionalPack.tone.role?: preferences.toneCheck
        default: false
        }
    }
    /// After the essential pack is ready (and at launch once it is): every switched-on automatic pack still missing.
    static func startAutomatic(_ centers: [ModelCenter] = ModelCenter.optionalCenters, essentialReady: Bool = ModelCenter.app.isReady) {
        guard ModelCenter.downloadsAllowed else { return }
        for center in centers { center.startAutomatically(switchedOn: isOn(center.optional), essentialReady: essentialReady) }
    }
    /// The user flipped a check's switch.
    static func switched(_ pack: OptionalPack, on: Bool) {
        let center = ModelCenter.optionalCenters.first { $0.optional == pack }
        if on, ModelCenter.downloadsAllowed { center?.checkSwitchedOn(essentialReady: ModelCenter.app.isReady) }
        switch pack.role {
        case OptionalPack.tone.role: if on { ToneModel.load() } else { Task { await ToneChecker.shared.unload() } }
        case OptionalPack.slips.role: if on, center?.isReady == true, Preferences.shared.smartGrammar { Task { await WritingEngine.warmSlips() } }
        default: break
        }
    }
}

/// Loads the tone classifier from the installed tone pack while Tone check is on, and says in Settings where it stands.
@MainActor
enum ToneModel {
    static var center: ModelCenter? { .tone }
    /// The installed classifier folder, or PARZR_TONE_DIR in development.
    static func folder() -> URL? {
        if let custom = DevOverrides.value("PARZR_TONE_DIR") { return URL(fileURLWithPath: custom, isDirectory: true) }
        guard let center, center.state == .ready, let pack = center.pack, let store = center.store, let relative = pack.provides[OptionalPack.tone.role] else { return nil }
        return store.folder(pack).appendingPathComponent(relative, isDirectory: true)
    }
    static func load() {
        guard Preferences.shared.toneCheck, let folder = folder() else { return }
        Task.detached(priority: .utility) { try? await ToneChecker.shared.load(folder: folder) }
    }
    /// One line for Settings.
    static var status: String {
        guard let center else { return "This copy of Parzr has no tone model." }
        return switch center.state {
        case .ready, .development: "Checks a selection when you press your shortcut, and the playground as you type. It runs entirely on your Mac."
        case .missing where center.removedByUser: "Its model (\(center.sizeText)) was removed. Turn this off and on again, or download it in Settings, Models."
        case .missing: Preferences.shared.toneCheck ? "Uses a small extra model (\(center.sizeText)), downloaded after the grammar models." : "Uses a small extra model (\(center.sizeText)), downloaded when this is on."
        default: center.statusLine
        }
    }
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
        case .ready: compact ? "\(center.feature) is ready" : "Downloaded and checked"
        case .development: "Development models in use"
        case .downloading(_, let total): compact ? "\(center.feature) is downloading · \(percent)" : "Downloading · \(percent) of \(ByteCountFormatter.string(fromByteCount: total, countStyle: .file))"
        case .verifying: compact ? "\(center.feature) · checking the download" : "Checking the download…"
        case .missing where center.removedByUser: compact ? "\(center.feature) isn't downloaded" : "Not downloaded"
        case .missing where center.optional?.automatic == false || (center.optional != nil && !OptionalChecks.isOn(center.optional)): compact ? "\(center.feature) isn't downloaded" : "Not downloaded"
        case .missing: compact ? "\(center.feature) downloads soon" : "Waiting to download"
        case .failed: compact ? "\(center.feature) isn't downloaded" : "Download paused"
        }
    }
    private var detail: String? {
        switch center.state {
        case .ready: "\(center.sizeText) on this Mac, each file checked against its pinned SHA-256."
        case .development: center.statusLine
        case .downloading, .verifying: nil
        case .missing where center.optional != nil: center.removedByUser ? center.optional?.removedNote : OptionalChecks.isOn(center.optional) ? center.optional?.missingNote : center.optional?.switchedOffNote
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
        case .failed(.changedOnDisk): NativeButton(title: "Download again", label: "Download the models again", action: { center.start(userInitiated: true) }).fixedSize()
        case .failed: NativeButton(title: "Try again", label: "Try the model download again", action: { center.start(userInitiated: true) }).fixedSize()
        case .ready, .verifying, .development: EmptyView()
        }
    }
}

/// Settings, Models: what is on this Mac, how big, under which license, and Re-download / Remove.
struct ModelsSettings: View {
    @ObservedObject var center: ModelCenter
    /// The optional packs (slip check, tone check), each listed below the essential one with its own Download / Remove.
    var optional: [ModelCenter] = []
    @State private var confirmRemove = false
    var body: some View {
        VStack(alignment: .leading, spacing: 22) {
            PackSection(center: center)
            ForEach(Array(optional.enumerated()), id: \.offset) { _, pack in PackSection(center: pack, removable: true) }
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

/// One pack in Settings, Models: its purpose, state and action, and one line per model with size, license and version.
/// An optional pack (`removable`) also offers Remove here; the essential pack's Re-download and Remove are under MANAGE.
struct PackSection: View {
    @ObservedObject var center: ModelCenter
    var removable = false
    @State private var confirmRemove = false
    var body: some View {
        VStack(alignment: .leading, spacing: 9) {
            Text(center.pack?.title.uppercased() ?? "MODELS").font(.system(size: 9, weight: .semibold)).tracking(1.2).foregroundStyle(Color.textSecondary).padding(.leading, 2)
            VStack(spacing: 0) {
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
                if removable, center.state == .ready {
                    divider
                    HStack(alignment: .center, spacing: 18) {
                        Text("Frees \(center.sizeText). Parzr does not download it again until you ask.").font(.system(size: 11)).foregroundStyle(Color.textSecondary).fixedSize(horizontal: false, vertical: true)
                        Spacer(minLength: 8)
                        NativeButton(title: "Remove", label: "Remove the \(center.feature.lowercased()) model", action: { confirmRemove = true }).fixedSize()
                    }.padding(16)
                }
            }.graphiteSurface()
        }
        .confirmationDialog("Remove the \(center.feature.lowercased()) model?", isPresented: $confirmRemove) {
            Button("Remove", role: .destructive) { center.remove() }
            Button("Cancel", role: .cancel) {}
        } message: { Text("\(center.optional?.removedNote ?? "Parzr checks with its rules only until you download it again.") (\(center.sizeText))") }
    }
    private var divider: some View { Rectangle().fill(Color.hairline.opacity(0.5)).frame(height: 0.5).padding(.horizontal, 16) }
}
