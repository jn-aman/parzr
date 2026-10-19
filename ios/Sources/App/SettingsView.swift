import SwiftUI
import ParzrKit

/// Settings shared with the keyboard through the App Group.
struct SettingsView: View {
    @Environment(AppModel.self) private var model
    @State private var dictionary = ""
    @State private var names = ""

    var body: some View {
        @Bindable var model = model
        NavigationStack {
            Form {
                Section("English") {
                    Picker("Spelling", selection: $model.settings.dialect) {
                        Text("American").tag("american")
                        Text("British").tag("british")
                    }
                }
                Section {
                    TextField("Words Parzr should accept, separated by commas", text: $dictionary, axis: .vertical)
                        .textInputAutocapitalization(.never)
                        .onSubmit(save)
                } header: { Text("Personal dictionary") }
                Section {
                    TextField("Names, separated by commas", text: $names, axis: .vertical)
                        .onSubmit(save)
                } header: { Text("Names") } footer: { Text("Parzr only changes the capitals of these names, never their spelling.") }
                Section {
                    Toggle("Rewrite inside the keyboard", isOn: $model.settings.rewriteInKeyboard)
                } footer: {
                    Text("When the keyboard can run Apple Intelligence itself, it writes rewrites without opening Parzr. Otherwise it hands them to this app.")
                }
            }
            .navigationTitle("Settings")
            .onAppear {
                dictionary = model.settings.dictionary.joined(separator: ", ")
                names = model.settings.names.joined(separator: ", ")
            }
            .onDisappear(perform: save)
        }
    }

    private func save() {
        func list(_ text: String) -> [String] { text.split(separator: ",").map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }.filter { !$0.isEmpty && $0.utf8.count <= 128 } }
        model.settings.dictionary = list(dictionary)
        model.settings.names = Array(list(names).prefix(2000))
    }
}
