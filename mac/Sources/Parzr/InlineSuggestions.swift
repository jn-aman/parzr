import AppKit
import Combine
import SwiftUI
import ParzrCore

enum CorrectionPlacement {
    static func origin(anchor: CGRect, size: CGSize, visible: CGRect) -> CGPoint {
        let margin: CGFloat = 8
        let x = min(max(anchor.minX, visible.minX + margin), visible.maxX - size.width - margin)
        let below = anchor.minY - size.height - margin
        let y = below >= visible.minY + margin ? below : min(anchor.maxY + margin, visible.maxY - size.height - margin)
        return CGPoint(x: max(visible.minX + margin, x), y: max(visible.minY + margin, y))
    }
}

/// Transparent range marks and one compact editor-side controller. Applying never opens a studio.
@MainActor
final class InlineSuggestions {
    private let overlay = MarkOverlay()
    private var correction: FloatingPanel?
    /// The card's SwiftUI host lives as long as the card: a click swaps its root view instead of building a new one.
    private var host: NSHostingView<RewritePanel>?
    private var scrollMonitor: Any?
    private var keyMonitor: Any?
    private let model = AppModel()
    private var revision: IgnoreRevision?
    private var ignored: Set<String> = []
    private var stopped = false
    private var shown: (snapshot: SelectionSnapshot, result: RewriteResult, probe: (range: NSRange, rect: CGRect)?)?
    private(set) var overflow = 0
    private var relayout: Task<Void, Never>?
    private let maxMarks = 32
    var hasMarks: Bool { overlay.hasMarks }
    var isPresenting: Bool { correction?.isVisible == true }
    var correctionSize: CGSize? { correction?.frame.size }
    var correctionView: NSView? { correction?.contentView }
    func markedView(for edit: WritingEdit) -> MarkElement? { overlay.element(for: edit.id) }
    private struct IgnoreRevision: Equatable {
        let pid: pid_t
        let element: CFHashCode
        let paragraph: Int
        let textHash: Int
    }
    init() {
        model.dismiss = { [weak self] in self?.closeCard(); self?.dismissIfStale() }
        model.didAnalyze = { [weak self] in
            guard let self else { return }
            self.model.selectedEdits.subtract(self.ignored)
        }
        installMonitor()
        Task { @MainActor [weak self] in try? await Task.sleep(for: .milliseconds(1500)); self?.prewarm() }
        // A global monitor made before Accessibility was granted never delivers; make a new one on grant.
        Preferences.shared.$permissionGranted.removeDuplicates().sink { [weak self] granted in
            if granted { MainActor.assumeIsolated { self?.installMonitor() } }
        }.store(in: &subscriptions)
        NotificationCenter.default.publisher(for: NSApplication.didChangeScreenParametersNotification).sink { [weak self] _ in MainActor.assumeIsolated { self?.dismiss() } }.store(in: &subscriptions)
    }
    private var subscriptions: Set<AnyCancellable> = []
    private(set) var monitorInstalls = 0
    func installMonitor() {
        guard !stopped else { return }
        if let scrollMonitor { NSEvent.removeMonitor(scrollMonitor) }
        scrollMonitor = NSEvent.addGlobalMonitorForEvents(matching: [.scrollWheel, .leftMouseDown, .rightMouseDown]) { [weak self] event in
            let scrolled = event.type == .scrollWheel
            MainActor.assumeIsolated { scrolled ? self?.scrolled() : self?.closeCard() }
        }
        monitorInstalls += 1
    }
    /// Scrolling hides marks at once and re-places them once it settles, if the text is unchanged.
    private func scrolled() {
        closeCard()
        guard shown != nil else { return }
        overlay.hide()
        relayout?.cancel()
        relayout = Task { @MainActor [weak self] in
            try? await Task.sleep(for: .milliseconds(180))
            guard !Task.isCancelled, let self else { return }
            if self.textIsCurrent, let s = self.shown { self.reset(); self.show(snapshot: s.snapshot, result: s.result) } else { self.dismiss() }
        }
    }
    private var textIsCurrent: Bool {
        guard let s = shown?.snapshot, !s.app.isTerminated, s.app == SelfTestTarget.watched,
              let focused = AX.focusedText(s.app), CFEqual(focused, s.element) else { return false }
        if let full = s.fullText { return AX.text(s.element) == full }
        return AX.string(s.element, kAXSelectedTextAttribute) == s.text
    }
    private var marksAreCurrent: Bool {
        guard textIsCurrent, let s = shown else { return false }
        guard let p = s.probe else { return true }
        guard let now = AX.bounds(s.snapshot.element, p.range) else { return false }
        return abs(now.minX - p.rect.minX) < s.snapshot.markDrift && abs(now.minY - p.rect.minY) < s.snapshot.markDrift
    }
    private func closeCard() {
        correction?.orderOut(nil)
        if let keyMonitor { NSEvent.removeMonitor(keyMonitor); self.keyMonitor = nil }
        model.clearSession()
    }
    func dismiss() { overlay.clear(); reset() }
    /// Forgets the shown result and the card but leaves the marks on screen, so the next show can keep the unchanged ones.
    private func reset() { closeCard(); shown = nil; overflow = 0; relayout?.cancel(); relayout = nil }
    func dismissIfStale() {
        // Marks and an open card persist across clicks and caret moves; they go only
        // when the text, focus, position or the passive/app settings no longer match.
        let prefs = Preferences.shared
        guard prefs.passive, !prefs.paused else { dismiss(); return }
        if let app = shown?.snapshot.app ?? model.snapshot?.app, !prefs.enabled(for: app.bundleIdentifier ?? "") { dismiss(); return }
        if shown != nil, !marksAreCurrent { dismiss(); return }
        if isPresenting, (try? model.snapshot?.validate()) == nil { if shown != nil { closeCard() } else { dismiss() }; return }
        if shown == nil, !isPresenting { dismiss() }
    }
    func stop() {
        stopped = true; relayout?.cancel(); dismiss()
        correction?.contentView = nil; host = nil; correction = nil; overlay.close()
        if let scrollMonitor { NSEvent.removeMonitor(scrollMonitor); self.scrollMonitor = nil }
        subscriptions.removeAll(); ignored = []; revision = nil
    }
    private func prepareRevision(_ snapshot: SelectionSnapshot) {
        let next = IgnoreRevision(pid: snapshot.app.processIdentifier, element: CFHash(snapshot.element), paragraph: snapshot.selection.location, textHash: snapshot.text.hashValue)
        if revision != next { ignored = []; revision = next }
    }
    @discardableResult
    func show(snapshot: SelectionSnapshot, result: RewriteResult) -> Bool {
        if let current = shown, overlay.hasMarks, CFEqual(current.snapshot.element, snapshot.element), current.snapshot.fullText == snapshot.fullText,
           current.snapshot.selection == snapshot.selection, current.result.edits == result.edits, marksAreCurrent {
            shown = (snapshot, result, current.probe); return true
        }
        reset(); prepareRevision(snapshot)
        guard snapshot.app == SelfTestTarget.watched, !snapshot.text.isEmpty else { overlay.clear(); return false }
        let edits = result.edits.filter { !ignored.contains($0.id) }
        shown = (snapshot, result, nil)
        if edits.isEmpty { overlay.clear(); return true }
        overflow = max(0, edits.count - maxMarks)
        var probe: (range: NSRange, rect: CGRect)?
        let placed: [(edit: WritingEdit, global: NSRange, bounds: CGRect)] = edits.prefix(maxMarks).compactMap { edit in
            let local = edit.range.length > 0 ? edit.range : (snapshot.text as NSString).rangeOfComposedCharacterSequence(at: min(edit.start_utf16, max(0, snapshot.text.utf16.count - 1)))
            let global = NSRange(location: snapshot.selection.location + local.location, length: local.length)
            guard let bounds = AX.bounds(snapshot.element, global), bounds.width > 0, bounds.height < 70,
                  SelfTestTarget.shows(bounds) else { return nil }
            return (edit, global, bounds)
        }
        var items: [MarkItem] = []
        if Preferences.shared.highlightFill, !placed.isEmpty {
            var washes = 0
            // Whole-sentence wash goes first so the word washes and marks stack above it.
            sentenceLoop: for range in SentencePreview.sentenceRanges(in: snapshot.text, containing: placed.map(\.edit)) {
                for line in AX.lineRects(snapshot.element, NSRange(location: snapshot.selection.location + range.location, length: range.length)) {
                    let rect = line.insetBy(dx: -1, dy: 0)
                    guard rect.height < 70, SelfTestTarget.shows(rect) else { continue }
                    if washes >= 40 { break sentenceLoop }
                    washes += 1; items.append(MarkItem(shape: MarkShape(kind: .wash, rect: rect)))
                }
            }
        }
        for (edit, global, bounds) in placed {
            let style = ["Style", "Tone"].contains(edit.category)
            if Preferences.shared.highlightFill { items.append(MarkItem(shape: MarkShape(kind: .highlight, rect: bounds, style: style), owner: edit.id)) }
            items.append(MarkItem(shape: MarkShape(kind: .underline, rect: bounds, style: style), owner: edit.id, label: "Review \(edit.category.lowercased()) correction", tip: "Parzr: \(edit.explanation)") { [weak self] in
                guard let now = AX.bounds(snapshot.element, global), abs(now.minY - bounds.minY) < max(2, snapshot.markDrift), abs(now.minX - bounds.minX) < max(2, snapshot.markDrift) else { self?.dismiss(); return }
                self?.present(snapshot: snapshot, result: result, focused: edit, anchor: bounds)
            })
            if probe == nil { probe = (global, bounds) }
        }
        overlay.apply(items)
        shown = (snapshot, result, probe)
        return overlay.hasMarks
    }
    private func card() -> FloatingPanel {
        if let correction { return correction }
        let panel = FloatingPanel(contentRect: NSRect(origin: .zero, size: RewritePanel.size), styleMask: [.borderless, .nonactivatingPanel], backing: .buffered, defer: false)
        panel.isReleasedWhenClosed = false; panel.level = .floating; panel.hasShadow = true; panel.isOpaque = false; panel.backgroundColor = .clear
        panel.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]; panel.hidesOnDeactivate = false
        correction = panel
        return panel
    }
    private func setHost(_ root: RewritePanel, in panel: FloatingPanel) {
        if let host { host.rootView = root; return }
        let host = NSHostingView(rootView: root)
        // The card has a fixed size, so SwiftUI need not also measure its minimum and maximum size on every update.
        host.sizingOptions = []
        host.wantsLayer = true; host.layer?.cornerRadius = 10; host.layer?.masksToBounds = true
        panel.contentView = host; self.host = host
    }
    /// Renders the card once, invisible and off screen, so the first click does not pay for SwiftUI's first layout.
    func prewarm() {
        let sampleJSON = #"{"version":"","text":"This is a sample.","edits":[{"start_utf16":0,"end_utf16":4,"replacement":"This","original":"Ths","category":"Spelling","rule_id":"warm","explanation":"Sample.","confidence":1}],"source_map":[],"elapsed_ms":0,"protected_count":0}"#
        guard !stopped, correction == nil, shown == nil, let sample = try? JSONDecoder().decode(RewriteResult.self, from: Data(sampleJSON.utf8)), let edit = sample.edits.first else { return }
        let panel = card()
        model.source = sample.text; model.result = sample; model.selectedEdits = [edit.id]; model.focusedEditID = edit.id
        setHost(RewritePanel(model: model, ignore: nil, showsModes: false), in: panel)
        panel.alphaValue = 0; panel.ignoresMouseEvents = true; panel.setFrameOrigin(CGPoint(x: -20_000, y: -20_000))
        panel.orderFrontRegardless(); host?.layoutSubtreeIfNeeded(); host?.displayIfNeeded(); CATransaction.flush()
        Task { @MainActor [weak self] in
            self?.correction?.orderOut(nil); self?.correction?.alphaValue = 1; self?.correction?.ignoresMouseEvents = false
            if self?.shown == nil { self?.model.clearSession() }
        }
    }
    @discardableResult
    func present(snapshot: SelectionSnapshot, result: RewriteResult, focused: WritingEdit? = nil, anchor: CGRect, activate: Bool = true) -> Bool {
        do { try snapshot.validate() } catch { dismiss(); return false }
        prepareRevision(snapshot)
        model.select(snapshot, result: result, focused: focused)
        model.selectedEdits.subtract(ignored)
        let panel = card()
        let root = RewritePanel(model: model, ignore: { [weak self] edit in self?.ignore(edit) }, showsModes: snapshot.expectedSelection.length > 0)
        setHost(root, in: panel)
        let wasVisible = correction?.isVisible == true
        guard let visible = SelfTestTarget.visibleFrame(for: anchor) else { dismiss(); return false }
        let final = CorrectionPlacement.origin(anchor: anchor, size: RewritePanel.size, visible: visible)
        let animate = !wasVisible && !Preferences.shared.reduceMotion && !NSWorkspace.shared.accessibilityDisplayShouldReduceMotion
        correction?.alphaValue = animate ? 0 : 1
        correction?.setFrameOrigin(animate ? CGPoint(x: final.x, y: final.y + 4) : final)
        if activate { correction?.makeKeyAndOrderFront(nil) } else { correction?.orderFrontRegardless() }
        if animate {
            NSAnimationContext.runAnimationGroup { context in
                context.duration = 0.14; context.timingFunction = CAMediaTimingFunction(name: .easeOut)
                correction?.animator().alphaValue = 1; correction?.animator().setFrameOrigin(final)
            }
        }
        if let keyMonitor { NSEvent.removeMonitor(keyMonitor) }
        keyMonitor = NSEvent.addLocalMonitorForEvents(matching: .keyDown) { [weak self] event in
            let handled = MainActor.assumeIsolated { () -> Bool in
                guard let self, event.window == self.correction else { return false }
                let modifiers = event.modifierFlags.intersection([.command, .option, .control, .shift])
                if event.keyCode == 53 || (modifiers == .command && event.charactersIgnoringModifiers == "w") { self.closeCard(); return true }
                if event.keyCode == 36 && modifiers.isEmpty { self.model.applyBest(); return true }
                if event.keyCode == 36 && modifiers == .command { self.model.apply(); return true }
                if [123, 124].contains(event.keyCode), modifiers.isEmpty { self.model.navigate(event.keyCode == 123 ? -1 : 1); return true }
                return false
            }
            return handled ? nil : event
        }
        return true
    }
    private func ignore(_ edit: WritingEdit) {
        let related = EditPlan.related(to: edit, in: model.result?.edits ?? [edit])
        ignored.formUnion(related.map(\.id)); model.toggle(edit)
        overlay.remove(owners: Set(related.map(\.id)))
        if model.chosenEdits.isEmpty { closeCard() }
    }
}

/// The draft uses the same compact visual grammar with its own native Undo transaction.
struct InlineCorrection: View {
    static let size = CGSize(width: 360, height: 200)
    let edit: WritingEdit
    var source: String = ""
    var edits: [WritingEdit] = []
    @ObservedObject var preferences = Preferences.shared
    var canApply: Bool
    var apply: () -> Void
    var applySentence: (() -> Void)? = nil
    var ignore: () -> Void
    var close: () -> Void
    private var sentenceEdits: [WritingEdit] { SentencePreview.edits(source: source, edits: edits, focused: edit) }
    var body: some View {
        let count = sentenceEdits.count
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 6) {
                Circle().fill(Color.correctionInk).frame(width: 6, height: 6).accessibilityHidden(true)
                Text(count > 1 ? "\(count) fixes in this sentence" : edit.category).font(.system(size: 12, weight: .semibold)).foregroundStyle(Color.textPrimary).lineLimit(1)
                Spacer(minLength: 2)
                NativeButton(title: "", kind: .utility, symbol: "xmark", label: "Close correction", key: "\u{1b}", action: close).frame(width: 20, height: 22).help("Close · Esc")
            }.frame(height: 22)
            if !source.isEmpty { SentenceDiffView(source: source, edits: edits, focused: edit, note: edit.explanation).frame(minHeight: 48) }
            else { Text(edit.explanation).font(.system(size: 11)).foregroundStyle(Color.textSecondary).lineLimit(2).frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading).help(edit.explanation) }
            HStack(spacing: 6) {
                if let applySentence, count > 1 {
                    NativeButton(title: "Fix sentence  ⏎", kind: .primary, label: "Fix sentence", key: "\r", enabled: canApply, action: applySentence).fixedSize()
                    NativeButton(title: "This word", kind: .utility, label: "Apply correction: \(edit.replacementLabel)", enabled: canApply, action: apply).fixedSize().help("Apply only \(edit.actionTitle)")
                } else {
                    NativeButton(title: "\(edit.actionTitle)  ⏎", kind: .primary, label: "Apply correction: \(edit.replacementLabel)", key: "\r", enabled: canApply, action: apply)
                }
                Spacer(minLength: 0)
                CardMore(edit: edit, done: ignore)
                NativeButton(title: "Ignore", kind: .utility, action: { preferences.noteIgnored(edit); ignore() }).fixedSize()
            }.frame(height: 28)
        }.padding(12).frame(width: Self.size.width, height: Self.size.height).background(Color.canvas).foregroundStyle(Color.textPrimary)
    }
}
