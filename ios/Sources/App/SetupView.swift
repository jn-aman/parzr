import SwiftUI
import ParzrKit

/// Onboarding: how to turn on the keyboard and Full Access, and what the keyboard reported.
struct SetupView: View {
    @Environment(AppModel.self) private var model
    @Environment(\.openURL) private var openURL
    /// Shown as a Done button when the view is the first-launch sheet.
    var onDone: (() -> Void)?

    var body: some View {
        NavigationStack {
            List {
                Section {
                    step(1, "Open Settings", detail: "Parzr’s page in Settings opens.", done: false)
                    step(2, "Tap Keyboards, then turn on Parzr", detail: "Or: General > Keyboard > Keyboards > Add New Keyboard > Parzr.", done: model.keyboardEnabled)
                    step(3, "Turn on Allow Full Access", detail: "Lets the keyboard hand rewrites to this app through a shared folder on this device. Parzr sends nothing over the network.", done: model.keyboardReport?.fullAccess == true)
                    step(4, "Switch to Parzr", detail: "In any app, touch and hold the globe key and choose Parzr.", done: model.keyboardReport != nil)
                    Button("Open Settings") { if let url = URL(string: UIApplication.openSettingsURLString) { openURL(url) } }
                } header: {
                    Text("Turn on the keyboard")
                }
                Section("Apple Intelligence") {
                    Label(model.appleModel.message, systemImage: model.appleModel.isAvailable ? "checkmark.circle" : "exclamationmark.circle")
                    Text("Tone rewrites use the on-device Apple model: nothing to download, and your text stays on this device. Grammar and spelling checks never need it.")
                        .font(.caption).foregroundStyle(.secondary)
                }
                if let report = model.keyboardReport {
                    Section("What the keyboard reported") {
                        LabeledContent("Last seen", value: report.seen.formatted(.relative(presentation: .named)))
                        LabeledContent("Checker", value: report.checker)
                        if let headroom = report.memoryHeadroomMB { LabeledContent("Memory headroom", value: "\(headroom) MB") }
                        LabeledContent("Apple Intelligence in the keyboard", value: report.appleModel)
                    }
                }
            }
            .navigationTitle("Keyboard")
            .toolbar {
                if let onDone { ToolbarItem(placement: .confirmationAction) { Button("Done", action: onDone) } }
            }
        }
    }

    private func step(_ number: Int, _ title: String, detail: String, done: Bool) -> some View {
        HStack(alignment: .top, spacing: 12) {
            Image(systemName: done ? "checkmark.circle.fill" : "\(number).circle")
                .foregroundStyle(done ? .green : .secondary)
                .font(.title3)
            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                Text(detail).font(.caption).foregroundStyle(.secondary)
            }
        }
        .accessibilityElement(children: .combine)
        .accessibilityValue(done ? "Done" : "")
    }
}
