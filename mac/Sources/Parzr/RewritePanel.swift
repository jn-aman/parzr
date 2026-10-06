import AppKit
import SwiftUI
import ParzrCore

struct RewritePanel: View {
    static let size = CGSize(width: 360, height: 232)
    @ObservedObject var model: AppModel
    @ObservedObject var preferences = Preferences.shared
    var ignore: ((WritingEdit) -> Void)?
    var showsModes = true
    private var position: Int { (model.chosenEdits.firstIndex { $0.id == model.focusedEdit?.id } ?? 0) + 1 }
    private var headline: String { model.focusedEdit.map { model.fixesSentence ? "\(model.sentenceEdits.count) fixes in this sentence" : $0.category } ?? "Parzr" }
    private var copied: Bool { model.status == "Copied to clipboard" }
    /// Engine warnings only; "Copied to clipboard" is feedback, not a degraded check.
    private var warning: String? { copied ? nil : model.status }
    /// Errors and empty results shrink to their content; a result or a running check keeps the full card so it never jumps.
    var isCompact: Bool { model.error != nil || !model.busy && model.result != nil && model.focusedEdit == nil }
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 6) {
                if showsModes {
                    Text(model.mode.summary).font(.system(size: 11)).foregroundStyle(Color.textSecondary).lineLimit(1)
                } else {
                    Circle().fill(Color.correctionInk).frame(width: 6, height: 6).accessibilityHidden(true)
                    Text(headline).font(.system(size: 12, weight: .semibold)).foregroundStyle(Color.textPrimary).lineLimit(1)
                }
                Spacer(minLength: 2)
                if model.chosenEdits.count > 1 {
                    NativeButton(title: "", kind: .utility, symbol: "chevron.left", label: "Previous correction", action: { model.navigate(-1) }).frame(width: 18, height: 22).help("Previous correction · Left arrow")
                    Text("\(position)/\(model.chosenEdits.count)").font(.system(size: 10, design: .monospaced)).foregroundStyle(Color.textSecondary)
                    NativeButton(title: "", kind: .utility, symbol: "chevron.right", label: "Next correction", action: { model.navigate(1) }).frame(width: 18, height: 22).help("Next correction · Right arrow")
                }
                NativeButton(title: "", kind: .utility, symbol: "xmark", label: "Close corrections", key: "\u{1b}", action: { model.dismiss?() }).frame(width: 20, height: 22).help("Close · Esc")
            }.frame(height: 22)
            if showsModes {
                ModeChoices(mode: $model.modeChoice, compact: true).disabled(model.busy || model.snapshot == nil && model.selectionHint)
                    .padding(2).background(Color.writingSurface, in: RoundedRectangle(cornerRadius: 8)).frame(maxWidth: .infinity, alignment: .leading)
            }
            if let error = model.error {
                VStack(alignment: .leading, spacing: 8) {
                    Label(model.selectionHint ? "Select text to check" : "Let’s get this working", systemImage: model.selectionHint ? "text.cursor" : "info.circle").font(.system(size: 13, weight: .semibold)).foregroundStyle(Color.textPrimary)
                    Text(model.selectionHint ? "Highlight a word or passage in your editor, then press \(preferences.shortcutDisplay)." : error).font(.system(size: 11)).foregroundStyle(Color.textSecondary).lineLimit(4).fixedSize(horizontal: false, vertical: true)
                    if !preferences.permissionGranted { NativeButton(title: "Enable editor access", kind: .primary, action: { preferences.requestPermission() }).fixedSize() }
                    else if model.snapshot != nil { NativeButton(title: "Check again", action: { model.analyze() }).fixedSize() }
                }.frame(maxWidth: .infinity, alignment: .topLeading).padding(.bottom, 4)
            } else if model.busy || model.result == nil {
                HStack(spacing: 8) { ProgressView().controlSize(.small); Text(model.mode == .fix ? "Checking your passage…" : "Rewriting as \(model.mode.title)…").font(.system(size: 12)).foregroundStyle(Color.textSecondary) }
                    .frame(maxWidth: .infinity, maxHeight: .infinity).background(Color.writingSurface, in: RoundedRectangle(cornerRadius: 9))
            } else if let edit = model.focusedEdit {
                SentenceDiffView(source: model.source, edits: model.chosenEdits, focused: edit, note: warning == nil ? edit.explanation : "Grammar checked · Context refinement unavailable", whole: (model.snapshot?.expectedSelection.length ?? 0) > 0).frame(minHeight: 64)
            } else {
                let empty = EmptyCheck(mode: model.mode, status: warning)
                VStack(alignment: .leading, spacing: 4) {
                    Label(empty.title, systemImage: empty.warning ? "info.circle" : "checkmark.circle").font(.system(size: 13, weight: .semibold)).foregroundStyle(Color.textPrimary)
                    Text(empty.detail).font(.system(size: 11)).foregroundStyle(Color.textSecondary).lineLimit(3).fixedSize(horizontal: false, vertical: true)
                    if showsModes { Label(empty.hint, systemImage: "arrow.up").font(.system(size: 11)).foregroundStyle(Color.mintAccent).padding(.top, 6) }
                }.frame(maxWidth: .infinity, alignment: .topLeading).padding(.bottom, 4)
            }
            if model.error == nil, !isCompact {
                // Every action shows text. Copy sits in the row when no word action competes for it; otherwise "More" holds both, as labelled menu items.
                let hasWordAction = !model.busy && model.focusedEdit.map { $0.nameCandidate != nil || $0.canAddToDictionary } == true
                ViewThatFits(in: .horizontal) { if !hasWordAction { footer(more: false) }; footer(more: true) }.frame(maxWidth: .infinity).frame(height: 28)
            }
        }.padding(12).frame(width: Self.size.width, height: isCompact ? nil : Self.size.height).background(Color.canvas).foregroundStyle(Color.textPrimary)
            .overlay(RoundedRectangle(cornerRadius: 10).strokeBorder(Color.hairline, lineWidth: 0.5))
    }
    private func footer(more: Bool) -> some View {
        let focused = model.busy ? nil : model.focusedEdit
        let moreMenu = CardMore(edit: focused, done: { if let edit = focused { if let ignore { ignore(edit) } else { model.toggle(edit) } } }, copy: showsModes ? { model.copy() } : nil, copied: copied, copyEnabled: !model.busy && model.result != nil)
        return HStack(spacing: 6) {
            if let edit = focused {
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
                if more { moreMenu }
                NativeButton(title: "Ignore", kind: .utility, action: { preferences.noteIgnored(edit); if let ignore { ignore(edit) } else { model.toggle(edit) } }).fixedSize()
            } else { Spacer(minLength: 0); if more { moreMenu } }
            if !more, showsModes { copyButton }
            if model.snapshot?.canPatch == false && model.snapshot?.copied != true && preferences.clipboardFallback {
                NativeButton(title: "Paste", enabled: !model.busy && !model.chosenEdits.isEmpty, action: model.pasteFallback).fixedSize()
            }
        }
    }
    private var copyButton: some View {
        NativeButton(title: copied ? "Copied" : "Copy", kind: .utility, symbol: copied ? "checkmark" : "doc.on.doc", label: "Copy corrected passage", enabled: !model.busy && model.result != nil, action: model.copy).fixedSize().help("Copy the corrected passage · Command+C")
    }
}

/// "More": the secondary card actions as a menu whose items all carry text (a bare icon says nothing). Empty when there is nothing to offer.
struct CardMore: View {
    var edit: WritingEdit?
    var done: () -> Void
    var copy: (() -> Void)? = nil
    var copied = false
    var copyEnabled = true
    @ObservedObject var preferences = Preferences.shared
    @State private var hover = false
    var body: some View {
        let name = edit?.nameCandidate, word = edit.flatMap { $0.canAddToDictionary ? $0.original : nil }
        if name != nil || word != nil || copy != nil {
            Menu {
                if let name { Button("This is a name: \(name)") { preferences.learnName(name); done() } }
                else if let word { Button("Add “\(word)” to dictionary") { preferences.saveWord(word); done() } }
                if let copy { Button(copied ? "Copied" : "Copy corrected passage", action: copy).disabled(!copyEnabled) }
            } label: {
                (Text("More ").font(.system(size: 12, weight: .medium)) + Text(Image(systemName: "chevron.down")).font(.system(size: 8, weight: .bold)))
                    .foregroundStyle(Color.textPrimary).padding(.horizontal, 8).frame(height: 24)
                    .background(hover ? Color.textPrimary.opacity(0.07) : Color.clear, in: RoundedRectangle(cornerRadius: 6)).contentShape(RoundedRectangle(cornerRadius: 6))
            }.menuStyle(.borderlessButton).menuIndicator(.hidden).fixedSize().onHover { hover = $0 }
                .help([name.map { "This is a name: never correct \($0)" }, word.map { "Add \($0) to your personal dictionary" }, copy == nil ? nil : "Copy the corrected passage"].compactMap { $0 }.joined(separator: " · "))
                .accessibilityLabel("More actions")
        }
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
