import SwiftUI
import AppKit

struct StatusPopover: View {
    @ObservedObject var preferences = Preferences.shared
    let engineReady: Bool
    let sourceApp: NSRunningApplication?
    var check: () -> Void
    var editor: () -> Void
    var settings: () -> Void
    var about: () -> Void
    var quit: () -> Void
    static let firefoxHint = "Firefox is blocking accessibility. In Firefox, open Settings, Privacy & Security, Permissions, turn off \"Prevent accessibility services from accessing your browser\", then restart Firefox."
    var body: some View {
        VStack(alignment: .leading, spacing: 15) {
            HStack { Brand(); Spacer(); Circle().fill(engineReady ? Color.mintAccent : Color.textSecondary).frame(width: 6, height: 6) }
            HStack(spacing: 6) { Image(systemName: "lock"); Text("Local writing assistant"); Spacer(); Text("v\(Support.version)") }.font(.system(size: 10)).foregroundStyle(Color.textSecondary)
            VStack(spacing: 10) {
                HStack {
                    Label("Automatic highlights", systemImage: "textformat.abc").font(.system(size: 12, weight: .medium))
                    Spacer()
                    Toggle("Automatic highlights", isOn: $preferences.automaticHighlights).labelsHidden().toggleStyle(.switch).controlSize(.small)
                }
                if let sourceApp, let id = sourceApp.bundleIdentifier {
                    HStack { Text(sourceApp.localizedName ?? "Current app").font(.system(size: 11)).foregroundStyle(Color.textSecondary); Spacer(); Toggle("Enable in \(sourceApp.localizedName ?? "current app")", isOn: $preferences[appEnabled: id]).labelsHidden().toggleStyle(.switch).controlSize(.small) }
                }
            }.padding(13).graphiteSurface()
            HStack {
                NativeButton(title: "Check selection", kind: .primary, symbol: "checkmark", label: "Check selected text", action: check)
                Spacer(minLength: 4)
                Text(preferences.shortcutDisplay).font(.system(size: 10, weight: .medium)).padding(.horizontal, 8).padding(.vertical, 5).background(Color.surface, in: RoundedRectangle(cornerRadius: 5))
            }
            if !preferences.permissionGranted {
                HStack { Text("Enable editor access").font(.system(size: 11)).foregroundStyle(Color.textSecondary); Spacer(); NativeButton(title: "Enable…", action: { preferences.requestPermission() }).fixedSize() }
            }
            if preferences.firefoxHint {
                VStack(alignment: .leading, spacing: 8) {
                    Text(Self.firefoxHint).font(.system(size: 11)).foregroundStyle(Color.textSecondary).lineSpacing(2).fixedSize(horizontal: false, vertical: true)
                    NativeButton(title: "Dismiss", kind: .utility, label: "Dismiss Firefox hint", action: { preferences.dismissFirefoxHint() }).fixedSize()
                }.padding(13).graphiteSurface()
            }
            Rectangle().fill(Color.hairline).frame(height: 0.5)
            HStack { NativeButton(title: "Open editor", symbol: "square.and.pencil", label: "Open Parzr", action: editor); Spacer(); NativeButton(title: "Settings", symbol: "slider.horizontal.3", action: settings) }
            HStack { NativeButton(title: "About Parzr", kind: .utility, action: about); Spacer(); NativeButton(title: "Quit", kind: .utility, label: "Quit Parzr", action: quit) }
        }.padding(18).frame(width: 318).background(Color.canvas).foregroundStyle(Color.textPrimary)
    }
}
