import SwiftUI
import AppKit
import ParzrCore

/// All choices remain visible; no popup menus or hidden mode options.
struct ChoiceStrip<Value: Equatable>: View {
    let label: String
    let choices: [(String, Value)]
    @Binding var selection: Value
    var body: some View {
        HStack(spacing: 3) {
            ForEach(choices.indices, id: \.self) { index in
                let choice = choices[index]
                Button { selection = choice.1 } label: {
                    Text(choice.0).font(.system(size: 11, weight: selection == choice.1 ? .semibold : .medium))
                        .foregroundStyle(selection == choice.1 ? Color.mintAccent : Color.textSecondary)
                        .padding(.horizontal, 10).frame(height: 29)
                        .background(selection == choice.1 ? Color.accentWash : Color.clear, in: RoundedRectangle(cornerRadius: 6))
                        .contentShape(RoundedRectangle(cornerRadius: 6))
                }.buttonStyle(.plain).accessibilityLabel("\(label): \(choice.0)")
                    .accessibilityAddTraits(selection == choice.1 ? [.isSelected] : [])
            }
        }.padding(3).background(Color.writingSurface, in: RoundedRectangle(cornerRadius: 8))
    }
}
struct ModeChoices: View {
    @Binding var mode: RewriteMode
    var compact = false
    var body: some View {
        HStack(spacing: compact ? 2 : 5) {
            ForEach(RewriteMode.allCases) { item in
                Button { mode = item } label: {
                    HStack(spacing: 5) {
                        Image(systemName: item.symbol).font(.system(size: compact ? 11 : 12))
                        if !compact { Text(item.title).font(.system(size: 11, weight: .medium)) }
                    }.foregroundStyle(mode == item ? Color.mintAccent : Color.textSecondary)
                        .padding(.horizontal, compact ? 7 : 9).frame(height: compact ? 25 : 31)
                        .background(mode == item ? Color.accentWash : Color.clear, in: RoundedRectangle(cornerRadius: 7))
                        .contentShape(RoundedRectangle(cornerRadius: 7))
                }.buttonStyle(.plain).help("\(item.title) · \(item.detail)")
                    .accessibilityLabel("\(item.title) mode").accessibilityAddTraits(mode == item ? [.isSelected] : [])
            }
        }
    }
}
@MainActor enum Support {
    static let issues = URL(string: "https://github.com/jn-aman/parzr/issues")!
    static var version: String { Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "Development" }
    static var build: String { Bundle.main.object(forInfoDictionaryKey: "ParzrBuildRevision") as? String ?? "development" }
    private static func sysctl(_ name: String) -> String? {
        var size = 0
        guard sysctlbyname(name, nil, &size, nil, 0) == 0, size > 0 else { return nil }
        var value = [CChar](repeating: 0, count: size)
        return sysctlbyname(name, &value, &size, nil, 0) == 0 ? String(cString: value) : nil
    }
    /// Hardware facts only; a report never includes writing unless the user adds it.
    static var mac: String {
        let memory = ProcessInfo.processInfo.physicalMemory / 1_073_741_824
        return "\(sysctl("hw.model") ?? "Mac") · \(sysctl("machdep.cpu.brand_string") ?? "Apple Silicon") · \(memory) GB"
    }
    /// support@parzr.app has no mailbox; reports go to the public issue tracker, prefilled.
    static func reportIssue() {
        var components = URLComponents(url: issues.appendingPathComponent("new"), resolvingAgainstBaseURL: false)!
        components.queryItems = [URLQueryItem(name: "title", value: "Parzr \(version): "), URLQueryItem(name: "body", value: "What happened?\n\nWhat did you expect?\n\nSteps to reproduce:\n\nParzr: \(version) (\(build))\nmacOS: \(ProcessInfo.processInfo.operatingSystemVersionString)\nMac: \(mac)\n\nOnly include writing or screenshots you choose to share.")]
        if let url = components.url { NSWorkspace.shared.open(url) }
    }
}
