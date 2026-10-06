import AppKit
import SwiftUI
import ParzrCore

struct DraftEditor: NSViewRepresentable {
    @Binding var text: String
    var edits: [WritingEdit]
    /// The marks come from an earlier version of the text: drawn, but a click offers no fix.
    var provisional = false
    var fontSize: Double = 18
    var lineSpacing: Double = 6
    var highlightFill = true
    var focusedEditID: String? = nil
    var ignore: (WritingEdit) -> Void = { _ in }
    func makeCoordinator() -> Coordinator { Coordinator(self) }
    func makeNSView(context: Context) -> NSScrollView {
        let scroll = NSScrollView(); scroll.drawsBackground = false; scroll.hasVerticalScroller = true
        let editor = CorrectionTextView(frame: .zero)
        editor.isRichText = false; editor.allowsUndo = true; editor.drawsBackground = false
        editor.font = .systemFont(ofSize: 18, weight: .regular)
        editor.textColor = NSColor(Color.textPrimary); editor.insertionPointColor = NSColor(Color.mintAccent)
        editor.textContainerInset = NSSize(width: 18, height: 18)
        editor.isVerticallyResizable = true; editor.isHorizontallyResizable = false
        editor.autoresizingMask = [.width]; editor.textContainer?.widthTracksTextView = true
        let paragraph = NSMutableParagraphStyle(); paragraph.lineSpacing = 6
        editor.defaultParagraphStyle = paragraph
        editor.isContinuousSpellCheckingEnabled = false; editor.isGrammarCheckingEnabled = false
        editor.isAutomaticSpellingCorrectionEnabled = false; editor.isAutomaticQuoteSubstitutionEnabled = false
        editor.delegate = context.coordinator; editor.string = text
        editor.setAccessibilityLabel("Writing space")
        scroll.documentView = editor
        return scroll
    }
    func updateNSView(_ scroll: NSScrollView, context: Context) {
        context.coordinator.parent = self
        guard let editor = scroll.documentView as? CorrectionTextView else { return }
        // Appearance changes are presentation, so they must never become the
        // most recent Undo action ahead of a writing correction.
        let undo = editor.undoManager
        let restoreUndoRegistration = undo?.isUndoRegistrationEnabled == true
        if restoreUndoRegistration { undo?.disableUndoRegistration() }
        if editor.font?.pointSize != CGFloat(fontSize) { editor.font = .systemFont(ofSize: fontSize) }
        editor.textColor = NSColor(Color.textPrimary)
        editor.insertionPointColor = NSColor(Color.mintAccent)
        if editor.defaultParagraphStyle?.lineSpacing != CGFloat(lineSpacing) {
            let paragraph = NSMutableParagraphStyle(); paragraph.lineSpacing = lineSpacing
            editor.defaultParagraphStyle = paragraph
            editor.textStorage?.addAttribute(.paragraphStyle, value: paragraph, range: NSRange(location: 0, length: editor.string.utf16.count))
        }
        if restoreUndoRegistration { undo?.enableUndoRegistration() }
        editor.suggestions = provisional ? [] : edits
        editor.ignore = ignore
        if editor.string != text && !editor.hasMarkedText() {
            let selected = editor.selectedRange()
            context.coordinator.writingFromBinding = true
            if text.isEmpty { editor.string = ""; editor.undoManager?.removeAllActions() }
            else {
                editor.breakUndoCoalescing()
                editor.insertText(text, replacementRange: NSRange(location: 0, length: editor.string.utf16.count))
                editor.undoManager?.setActionName("Apply Parzr corrections")
                editor.breakUndoCoalescing()
            }
            context.coordinator.writingFromBinding = false
            let location = min(selected.location, editor.string.utf16.count)
            editor.setSelectedRange(NSRange(location: location, length: 0))
        }
        if context.coordinator.lastFocusedID != focusedEditID {
            context.coordinator.lastFocusedID = focusedEditID
            if let edit = edits.first(where: { $0.id == focusedEditID }), let range = editor.displayRange(for: edit) { editor.scrollRangeToVisible(range) }
        }
        guard let layout = editor.layoutManager else { return }
        // Redraw the marks only when they or the text moved: rewriting identical marks on every update is wasted work and a chance to flash.
        let marks = edits.compactMap { edit in editor.displayRange(for: edit).map { Mark(range: $0, category: edit.category) } }
        guard context.coordinator.drawn != Drawn(marks: marks, string: editor.string, fill: highlightFill, appearance: editor.effectiveAppearance.name) else { return }
        context.coordinator.drawn = Drawn(marks: marks, string: editor.string, fill: highlightFill, appearance: editor.effectiveAppearance.name)
        let full = NSRange(location: 0, length: editor.string.utf16.count)
        layout.removeTemporaryAttribute(.underlineStyle, forCharacterRange: full)
        layout.removeTemporaryAttribute(.underlineColor, forCharacterRange: full)
        layout.removeTemporaryAttribute(.backgroundColor, forCharacterRange: full)
        for mark in marks {
            layout.addTemporaryAttributes([.underlineStyle: NSUnderlineStyle.thick.rawValue, .underlineColor: NSColor(Color.ink(for: mark.category)), .backgroundColor: NSColor(Color.ink(for: mark.category)).withAlphaComponent(highlightFill ? 0.12 : 0)], forCharacterRange: mark.range)
        }
    }
    struct Mark: Equatable { let range: NSRange, category: String }
    struct Drawn: Equatable { let marks: [Mark], string: String, fill: Bool, appearance: NSAppearance.Name }
    @MainActor final class Coordinator: NSObject, NSTextViewDelegate {
        var parent: DraftEditor
        var writingFromBinding = false
        var lastFocusedID: String?
        var drawn: Drawn?
        init(_ parent: DraftEditor) { self.parent = parent }
        func textDidChange(_ notification: Notification) {
            if let editor = notification.object as? CorrectionTextView {
                guard !writingFromBinding, parent.text != editor.string else { return }
                editor.dismissCorrection()
                editor.suggestions = []
                parent.text = editor.string
            }
        }
    }
}

/// The draft's marks are actual correction controls, backed by native text editing and Undo.
@MainActor
final class CorrectionTextView: NSTextView {
    var suggestions: [WritingEdit] = []
    var ignore: (WritingEdit) -> Void = { _ in }
    private var correction: NSPopover?

    func dismissCorrection() { correction?.close(); correction = nil }

    func displayRange(for edit: WritingEdit) -> NSRange? {
        guard !string.isEmpty, (try? EditPlan.validate([edit], in: string)) != nil else { return nil }
        if edit.range.length > 0 { return edit.range }
        let text = string as NSString
        return text.rangeOfComposedCharacterSequence(at: min(edit.start_utf16, text.length - 1))
    }

    override func mouseDown(with event: NSEvent) {
        super.mouseDown(with: event)
        guard let layout = layoutManager, let container = textContainer, !string.isEmpty else { return }
        let point = convert(event.locationInWindow, from: nil)
        let local = NSPoint(x: point.x - textContainerOrigin.x, y: point.y - textContainerOrigin.y)
        var fraction: CGFloat = 0
        let glyph = layout.glyphIndex(for: local, in: container, fractionOfDistanceThroughGlyph: &fraction)
        guard glyph < layout.numberOfGlyphs else { return }
        let index = layout.characterIndexForGlyph(at: glyph)
        guard let edit = suggestions.first(where: { displayRange(for: $0).map { NSLocationInRange(index, $0) } == true }), let range = displayRange(for: edit) else { dismissCorrection(); return }
        let glyphs = layout.glyphRange(forCharacterRange: range, actualCharacterRange: nil)
        let rect = layout.boundingRect(forGlyphRange: glyphs, in: container).offsetBy(dx: textContainerOrigin.x, dy: textContainerOrigin.y)
        guard rect.insetBy(dx: 2, dy: 4).contains(point) else { dismissCorrection(); return }
        dismissCorrection()
        let popover = NSPopover(); popover.behavior = .transient
        popover.contentViewController = NSHostingController(rootView: InlineCorrection(edit: edit, source: string, edits: suggestions, canApply: true, apply: { [weak self] in self?.accept(edit) }, applySentence: { [weak self] in self?.acceptSentence(edit) }, ignore: { [weak self] in self?.ignore(edit); self?.dismissCorrection() }, close: { [weak self] in self?.dismissCorrection() }))
        popover.contentSize = InlineCorrection.size
        correction = popover
        popover.show(relativeTo: rect, of: self, preferredEdge: .maxY)
    }

    func accept(_ edit: WritingEdit) {
        let related = EditPlan.related(to: edit, in: suggestions)
        guard suggestions.contains(edit), (try? EditPlan.validate(related, in: string)) != nil else { dismissCorrection(); return }
        // insertText follows NSTextView's normal binding, selection, and undo transaction.
        undoManager?.beginUndoGrouping()
        for item in related.reversed() { insertText(item.replacement, replacementRange: item.range) }
        undoManager?.endUndoGrouping()
        undoManager?.setActionName("Apply Parzr correction")
        dismissCorrection()
    }

    func acceptSentence(_ edit: WritingEdit) {
        let batch = SentencePreview.edits(source: string, edits: suggestions, focused: edit)
        guard !batch.isEmpty, (try? EditPlan.validate(batch, in: string)) != nil else { dismissCorrection(); return }
        undoManager?.beginUndoGrouping()
        for item in batch.sorted(by: { $0.start_utf16 > $1.start_utf16 }) { insertText(item.replacement, replacementRange: item.range) }
        undoManager?.endUndoGrouping()
        undoManager?.setActionName("Apply Parzr sentence")
        dismissCorrection()
    }
}
