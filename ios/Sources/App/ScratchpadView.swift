import SwiftUI
import ParzrKit

/// A place to write or paste text, check it, and rewrite it in a tone.
struct ScratchpadView: View {
    @Environment(AppModel.self) private var model
    @FocusState private var focused: Bool

    var body: some View {
        @Bindable var model = model
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    if let notice = model.handoffNotice {
                        Label(notice, systemImage: "keyboard.badge.ellipsis")
                            .font(.callout)
                            .padding(12)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .background(.tint.opacity(0.12), in: .rect(cornerRadius: 12))
                    }
                    TextEditor(text: $model.text)
                        .focused($focused)
                        .frame(minHeight: 180)
                        .padding(8)
                        .background(Color(.secondarySystemBackground), in: .rect(cornerRadius: 12))
                        .accessibilityLabel("Text to check")
                        .onChange(of: model.text) { model.scheduleCheck() }
                    suggestionsSection
                    rewriteSection
                }
                .padding()
            }
            .navigationTitle("Parzr")
            // `-parzr-focus`: open with the editor focused, so the keyboard can be tried (and
            // probed) in the simulator without tapping.
            .onAppear { if ProcessInfo.processInfo.arguments.contains("-parzr-focus") { focused = true } }
            .toolbar {
                ToolbarItemGroup(placement: .keyboard) {
                    Spacer()
                    Button("Done") { focused = false }
                }
            }
        }
    }

    @ViewBuilder private var suggestionsSection: some View {
        HStack {
            Text("Fixes").font(.headline)
            if model.checking { ProgressView().controlSize(.small) }
            Spacer()
            if model.suggestions.count > 1 { Button("Fix all") { model.applyAll() } }
        }
        if let error = model.checkError {
            Text(error).foregroundStyle(.red).font(.callout)
        } else if model.suggestions.isEmpty {
            Text(model.text.isEmpty ? "Type or paste text above." : "Looks good. No grammar or spelling changes.")
                .foregroundStyle(.secondary).font(.callout)
        } else {
            ForEach(model.suggestions) { suggestion in
                Button { model.apply(suggestion) } label: {
                    VStack(alignment: .leading, spacing: 2) {
                        Text(suggestion.detail).font(.body.weight(.medium))
                        Text(suggestion.explanation).font(.caption).foregroundStyle(.secondary)
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                }
                .buttonStyle(.bordered)
                .accessibilityHint("Applies this \(suggestion.category.lowercased()) fix")
            }
        }
    }

    @ViewBuilder private var rewriteSection: some View {
        @Bindable var model = model
        Text("Rewrite").font(.headline)
        Picker("Tone", selection: $model.rewriteMode) {
            ForEach(RewriteMode.allCases.filter { $0 != .fix }) { Text($0.title).tag($0) }
        }
        .pickerStyle(.segmented)
        Text(model.rewriteMode.help).font(.caption).foregroundStyle(.secondary)
        if !model.appleModel.isAvailable {
            Label(model.appleModel.message, systemImage: "apple.intelligence")
                .font(.callout).foregroundStyle(.secondary)
        }
        Button {
            Task { await model.rewrite() }
        } label: {
            if model.rewriting { ProgressView() } else { Text(SuggestedRewrite.action(model.rewriteMode).replacingOccurrences(of: "Use", with: "Write")) }
        }
        .buttonStyle(.borderedProminent)
        .disabled(model.rewriting || !model.appleModel.isAvailable || !SuggestedRewrite.offered(for: model.text))
        if let outcome = model.rewriteOutcome {
            if let text = outcome.text {
                VStack(alignment: .leading, spacing: 8) {
                    Text(text).textSelection(.enabled)
                    HStack {
                        Button("Use this version") { model.useRewrite() }.buttonStyle(.borderedProminent)
                        Button("Copy") { UIPasteboard.general.string = text }
                    }
                }
                .padding(12)
                .background(Color(.secondarySystemBackground), in: .rect(cornerRadius: 12))
            } else {
                Text(outcome.message).font(.callout).foregroundStyle(.secondary)
            }
        }
    }
}
