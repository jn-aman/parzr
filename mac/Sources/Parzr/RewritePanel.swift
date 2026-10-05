import AppKit
import SwiftUI
import ParzrCore

struct RewritePanel: View {
    static let size = CGSize(width: 340, height: 218)
    static let hintSize = CGSize(width: 340, height: 128)
    @ObservedObject var model: AppModel
    @ObservedObject var preferences = Preferences.shared
    var ignore: ((WritingEdit) -> Void)?
    var showsModes = true
    private var position: Int { (model.chosenEdits.firstIndex { $0.id == model.focusedEdit?.id } ?? 0) + 1 }
    private var headline: String { model.focusedEdit.map { model.fixesSentence ? "\(model.sentenceEdits.count) fixes in this sentence" : $0.category } ?? "Parzr" }
    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 6) {
                if showsModes {
                    ModeChoices(mode: $model.modeChoice, compact: true).disabled(model.busy || model.snapshot == nil && model.selectionHint)
                } else {
                    Circle().fill(Color.correctionInk).frame(width: 6, height: 6).accessibilityHidden(true)
                    Text(headline).font(.system(size: 12, weight: .semibold)).foregroundStyle(Color.textPrimary).lineLimit(1)
                }
                Spacer(minLength: 2)
                if model.chosenEdits.count > 1 {
                    NativeButton(title: "", kind: .utility, symbol: "chevron.left", label: "Previous correction", action: { model.navigate(-1) }).frame(width: 18, height: 22)
                    Text("\(position)/\(model.chosenEdits.count)").font(.system(size: 10, design: .monospaced)).foregroundStyle(Color.textSecondary)
                    NativeButton(title: "", kind: .utility, symbol: "chevron.right", label: "Next correction", action: { model.navigate(1) }).frame(width: 18, height: 22)
                }
                NativeButton(title: "", kind: .utility, symbol: "xmark", label: "Close corrections", key: "\u{1b}", action: { model.dismiss?() }).frame(width: 20, height: 22)
            }.frame(height: 22)
            if let error = model.error {
                VStack(alignment: .leading, spacing: 9) {
                    Label(model.selectionHint ? "Select text to check" : "Let’s get this working", systemImage: model.selectionHint ? "text.cursor" : "info.circle").font(.system(size: 13, weight: .semibold)).foregroundStyle(Color.textPrimary)
                    Text(model.selectionHint ? "Highlight a word or passage in your editor, then press \(preferences.shortcutDisplay)." : error).font(.system(size: 11)).foregroundStyle(Color.textSecondary).lineLimit(4)
                    if !preferences.permissionGranted { NativeButton(title: "Enable editor access", kind: .primary, action: { preferences.requestPermission() }).fixedSize() }
                    else if model.snapshot != nil { NativeButton(title: "Check again", action: { model.analyze() }).fixedSize() }
                }.frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading).padding(.top, 4)
            } else if model.busy {
                HStack(spacing: 8) { ProgressView().controlSize(.small); Text("Reviewing your passage…").font(.system(size: 12)).foregroundStyle(Color.textSecondary) }.frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .leading)
            } else if let edit = model.focusedEdit {
                SentenceDiffView(source: model.source, edits: model.chosenEdits, focused: edit, note: model.status == nil ? edit.explanation : "Grammar checked · Context refinement unavailable", whole: (model.snapshot?.expectedSelection.length ?? 0) > 0).frame(minHeight: 64)
            } else {
                Label(model.status ?? "No suggestions in this selection", systemImage: model.status == nil ? "checkmark.circle" : "info.circle").font(.system(size: 12)).foregroundStyle(Color.textSecondary).frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .leading)
            }
            if model.error == nil {
                HStack(spacing: 6) {
                    if let edit = model.focusedEdit, !model.busy {
                        if (model.snapshot?.expectedSelection.length ?? 0) > 0, !model.chosenEdits.isEmpty {
                            NativeButton(title: "Fix all  ⌘⏎", kind: .primary, label: "Fix all corrections", enabled: model.canApply, action: { model.apply() }).fixedSize().help("Fix every correction in this selection · Command+Return")
                            NativeButton(title: edit.actionTitle, kind: .secondary, label: "Apply correction: \(edit.replacementLabel)", enabled: model.canApply, action: { model.applyCurrent() }).help("Apply only this correction")
                        } else if model.fixesSentence {
                            NativeButton(title: "Fix sentence  ⏎", kind: .primary, label: "Fix sentence", key: "\r", enabled: model.canApply, action: model.applySentence).fixedSize().help("Fix every correction in this sentence · Return")
                            NativeButton(title: "This word", kind: .utility, label: "Apply correction: \(edit.replacementLabel)", enabled: model.canApply, action: { model.applyCurrent() }).fixedSize().help("Apply only \(edit.actionTitle)")
                        } else {
                            NativeButton(title: "\(edit.actionTitle)  ⏎", kind: .primary, label: "Apply correction: \(edit.replacementLabel)", key: "\r", enabled: model.canApply, action: { model.applyCurrent() }).help("Apply this correction · Return")
                        }
                        Spacer(minLength: 0)
                        if let name = edit.nameCandidate { NativeButton(title: "", kind: .utility, symbol: "person.text.rectangle", label: "Mark as a name", action: { preferences.learnName(name); if let ignore { ignore(edit) } else { model.toggle(edit) } }).frame(width: 24, height: 24).help("This is a name: never correct \(name)") }
                        else if edit.canAddToDictionary { NativeButton(title: "", kind: .utility, symbol: "character.book.closed", label: "Add to dictionary", action: { preferences.saveWord(edit.original); if let ignore { ignore(edit) } else { model.toggle(edit) } }).frame(width: 24, height: 24).help("Add \(edit.original) to your personal dictionary") }
                        NativeButton(title: "Ignore", kind: .utility, action: { preferences.noteIgnored(edit); if let ignore { ignore(edit) } else { model.toggle(edit) } }).fixedSize()
                    } else { Spacer(minLength: 0) }
                    if showsModes { NativeButton(title: "", kind: .utility, symbol: "doc.on.doc", label: "Copy corrected passage", enabled: !model.busy && model.result != nil, action: model.copy).frame(width: 22, height: 22) }
                    if model.snapshot?.canPatch == false && model.snapshot?.copied != true && preferences.clipboardFallback {
                        NativeButton(title: "Paste", enabled: !model.busy && !model.chosenEdits.isEmpty, action: model.pasteFallback).fixedSize()
                    }
                }.frame(height: 28)
            }
        }.padding(12).frame(width: Self.size.width, height: model.selectionHint ? Self.hintSize.height : Self.size.height).background(Color.canvas).foregroundStyle(Color.textPrimary)
            .overlay(RoundedRectangle(cornerRadius: 10).strokeBorder(Color.hairline, lineWidth: 0.5))
    }
}

extension WritingEdit {
    var originalLabel: String { original.isEmpty ? "Insert" : original.allSatisfy(\.isWhitespace) ? "Whitespace" : original }
    var replacementLabel: String { replacement.isEmpty ? "Remove" : replacement == " " ? "Add space" : replacement.allSatisfy(\.isWhitespace) ? "Whitespace" : replacement }
    var actionTitle: String {
        if replacement.isEmpty { return original.allSatisfy(\.isWhitespace) ? "Remove space" : "Remove “\(original)”" }
        if original.isEmpty { return replacement == " " ? "Add space" : "Insert “\(replacement)”" }
        return replacement.allSatisfy(\.isWhitespace) ? "Fix spacing" : "Use “\(replacement)”"
    }
    /// Letters, apostrophes, hyphens and spaces only, possessive stripped; nil for anything else.
    static func nameToken(_ raw: String) -> String? {
        var word = raw.trimmingCharacters(in: .whitespaces)
        for suffix in ["'s", "\u{2019}s"] where word.hasSuffix(suffix) { word.removeLast(suffix.count) }
        guard word.count >= 2, word.utf8.count <= 128, word.contains(where: \.isLetter), word.allSatisfy({ $0.isLetter || "'\u{2019}- ".contains($0) }) else { return nil }
        return word
    }
    /// The name to offer "This is a name" for: a capitalized, hyphenated or multi-word spelling edit, or a grammar/model edit that splits or respells a token the system spell checker does not know.
    /// Lowercase single-word spelling edits keep the dictionary button instead (never both).
    func nameCandidate(flagged: (String) -> Bool = { NSSpellChecker.shared.checkSpelling(of: $0, startingAt: 0).location != NSNotFound }) -> String? {
        guard let name = Self.nameToken(original), name.lowercased() != replacement.lowercased() else { return nil }
        let nameLike = name.first?.isUppercase == true || name.contains { " -".contains($0) }
        if category == "Spelling" { return nameLike ? name : nil }
        let (a, b) = (name.lowercased().filter(\.isLetter), replacement.lowercased().filter(\.isLetter))
        guard a.count >= 3, a.count <= 64 else { return nil }
        let unknown = name.split(whereSeparator: { " -".contains($0) }).contains { flagged(String($0)) }
        // A split or merge keeps every letter; a respelling must not be a real word ("Your" to "You're" is grammar, not a name).
        if a == b { return nameLike || unknown ? name : nil }
        return a.first == b.first && Self.distance(a, b) <= 2 && unknown ? name : nil
    }
    var nameCandidate: String? { nameCandidate() }
    private static func distance(_ a: String, _ b: String) -> Int {
        let (a, b) = (Array(a), Array(b)); var row = Array(0...b.count)
        for i in a.indices {
            var diagonal = row[0]; row[0] = i + 1
            for j in b.indices { let up = row[j + 1]; row[j + 1] = min(row[j + 1] + 1, row[j] + 1, diagonal + (a[i] == b[j] ? 0 : 1)); diagonal = up }
        }
        return row[b.count]
    }
    var canAddToDictionary: Bool { category == "Spelling" && !original.isEmpty && original.utf8.count <= 128 && original.allSatisfy { $0.isLetter || $0 == "'" || $0 == "’" } }
}
