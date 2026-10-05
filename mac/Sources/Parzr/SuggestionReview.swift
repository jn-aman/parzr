import SwiftUI
import ParzrCore

struct SuggestionReview: View {
    @ObservedObject var model: AppModel
    var apply: (WritingEdit) -> Void
    var ignore: (WritingEdit) -> Void
    var select: (WritingEdit) -> Void
    @ObservedObject var preferences = Preferences.shared
    @State private var category = "All"
    private var categories: [String] { ["All"] + Set(model.chosenEdits.map(\.category)).sorted() }
    private var edits: [WritingEdit] { model.chosenEdits.filter { category == "All" || $0.category == category } }
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack { Text("Review suggestions").font(.system(size: 16, weight: .semibold)); Spacer(); Text("\(model.chosenEdits.count)").font(.system(size: 12, design: .monospaced)).foregroundStyle(Color.mintAccent) }
            ScrollView(.horizontal, showsIndicators: false) { ChoiceStrip(label: "Suggestion category", choices: categories.map { ($0, $0) }, selection: $category) }
            ScrollView {
                VStack(spacing: 9) {
                    ForEach(edits) { edit in
                        VStack(alignment: .leading, spacing: 8) {
                            Button { select(edit) } label: {
                                HStack { Text(edit.originalLabel).strikethrough().foregroundStyle(Color.textSecondary); Image(systemName: "arrow.right"); Text(edit.replacementLabel).foregroundStyle(Color.mintAccent); Spacer() }.font(.system(size: 12, weight: .medium)).contentShape(Rectangle())
                            }.buttonStyle(.plain).help("Show this correction in your draft")
                            Text(edit.explanation).font(.system(size: 11)).foregroundStyle(Color.textSecondary).fixedSize(horizontal: false, vertical: true)
                            HStack {
                                NativeButton(title: "Ignore", kind: .utility, action: { preferences.noteIgnored(edit); ignore(edit) }).fixedSize()
                                if let name = edit.nameCandidate { NativeButton(title: "This is a name", kind: .utility, symbol: "person.text.rectangle", label: "Mark as a name", action: { preferences.learnName(name); ignore(edit) }).fixedSize() }
                                else if edit.canAddToDictionary { NativeButton(title: "Save word", kind: .utility, label: "Add to dictionary", action: { preferences.saveWord(edit.original); ignore(edit) }).fixedSize() }
                                Spacer()
                                NativeButton(title: "Apply", kind: .primary, label: "Apply correction: \(edit.replacementLabel)", enabled: !model.busy, action: { apply(edit) }).fixedSize()
                            }
                        }.padding(12).graphiteSurface()
                    }
                    if edits.isEmpty { Text(model.busy ? "Checking…" : "No suggestions in this category.").font(.system(size: 12)).foregroundStyle(Color.textSecondary).padding(.vertical, 30) }
                }
            }.frame(maxHeight: 320)
        }.padding(16).frame(width: 350).background(Color.canvas).foregroundStyle(Color.textPrimary)
    }
}
