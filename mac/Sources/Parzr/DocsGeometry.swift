import AppKit
import ApplicationServices

/// Google Docs paints its page on a canvas and exposes no word geometry (AXBoundsForRange on its text area is invalid).
/// What it does expose, measured in Chrome: a hidden copy of the text (children of the text area) whose runs report real x and a line pitch about
/// 4% too tall, and the caret as a DOM element whose origin equals the origin of the text-event iframe. A character's screen rect is
/// therefore the caret's screen point plus its hidden offset from the character under the caret.
/// Everything Parzr sees is in "value" offsets (the AXValue with its paragraph breaks); Docs' own selection offsets skip the breaks, so they are converted at the AX boundary.
enum DocsGeometry {
    /// Real line pitch over hidden line pitch: 0.956 to 0.959 at 100% and 150% zoom, with single, 1.15 and double spacing, at 11 and 16 pt. x needs no scale (the copy follows the page's zoom).
    static let pitchScale: CGFloat = 0.958

    /// Start offset of each hidden run in `value`, or nil unless every run matches exactly. Paragraph breaks are in the value but belong to no run.
    static func offsets(runs: [String], in value: String) -> [Int]? {
        let text = value as NSString
        var offset = 0, starts: [Int] = []
        for run in runs {
            let length = (run as NSString).length
            while offset < text.length, text.character(at: offset) == 10, !run.hasPrefix("\n") { offset += 1 }
            guard offset + length <= text.length, text.substring(with: NSRange(location: offset, length: length)) == run else { return nil }
            starts.append(offset); offset += length
        }
        return starts
    }
    /// Docs' selection offset for a value offset: the same text without the paragraph breaks before it.
    static func selectionIndex(valueIndex: Int, in value: NSString) -> Int {
        var breaks = 0
        for index in 0..<min(valueIndex, value.length) where value.character(at: index) == 10 { breaks += 1 }
        return valueIndex - breaks
    }
    /// Value offsets a Docs selection offset can mean: just before a run of paragraph breaks at that offset, and after each of them (one entry when it is not on a break).
    static func valueCandidates(selectionIndex: Int, in value: NSString) -> [Int] {
        var position = 0, seen = 0
        while position < value.length, seen < selectionIndex { if value.character(at: position) != 10 { seen += 1 }; position += 1 }
        var candidates = [position]
        while position < value.length, value.character(at: position) == 10 { position += 1; candidates.append(position) }
        return candidates
    }
    /// Screen rect (AX coordinates) of a hidden rect, given the hidden rect of the character under the caret and the caret's screen point.
    static func screen(_ hidden: CGRect, anchor: CGRect, caret: CGPoint) -> CGRect {
        CGRect(x: caret.x + hidden.minX - anchor.minX, y: caret.y + pitchScale * (hidden.minY - anchor.minY), width: hidden.width, height: hidden.height)
    }
    /// The candidate (a character's leading edge, or the trailing edge of the one before) whose hidden x sits on the caret's x; nil when none is close,
    /// which means the caret is stale. The first candidate wins a tie.
    static func nearest(_ candidates: [(position: Int, rect: CGRect)], caretX: CGFloat) -> (position: Int, rect: CGRect)? {
        guard let best = candidates.min(by: { abs($0.rect.minX - caretX) < abs($1.rect.minX - caretX) }), abs(best.rect.minX - caretX) <= max(4, best.rect.height * 0.35) else { return nil }
        return best
    }
    /// One rect per visual line: neighbours at the same y merge.
    static func lines(_ rects: [CGRect]) -> [CGRect] {
        var lines: [CGRect] = []
        for rect in rects {
            if let last = lines.last, abs(last.minY - rect.minY) < max(2, rect.height * 0.3) { lines[lines.count - 1] = last.union(rect) } else { lines.append(rect) }
        }
        return lines
    }
}

extension AX {
    /// One hidden text run: the AXStaticText element and where its text sits in the text area's value.
    struct DocsRun { let element: AXUIElement; let range: NSRange }
    private struct DocsGeometryContext { let runs: [DocsRun]; let anchor: CGRect; let caret: CGPoint }
    private struct DocsContext { let element: AXUIElement; let value: String; let raw: NSRange; let selection: NSRange; let geometry: DocsGeometryContext?; let time: TimeInterval }
    private static var docsKnown: [(element: AXUIElement, docs: Bool, time: TimeInterval)] = []
    private static var docsRunsCache: (element: AXUIElement, value: String, runs: [DocsRun], time: TimeInterval)?
    private static var docsCurrent: DocsContext?
    /// Runs stay valid while the text does; the caret-relative context is rebuilt after this long, since the caret moves.
    private static let docsRunsLifetime: TimeInterval = 1.5, docsContextLifetime: TimeInterval = 0.25
    static func forgetDocs() { docsKnown = []; docsRunsCache = nil; docsCurrent = nil }

    private static func parent(_ element: AXUIElement) -> AXUIElement? {
        guard let value = get(element, kAXParentAttribute), CFGetTypeID(value) == AXUIElementGetTypeID() else { return nil }
        return (value as! AXUIElement)
    }
    private static func children(_ element: AXUIElement) -> [AXUIElement] { get(element, kAXChildrenAttribute) as? [AXUIElement] ?? [] }
    private static func point(_ element: AXUIElement) -> CGPoint? {
        guard let value = get(element, kAXPositionAttribute), CFGetTypeID(value) == AXValueGetTypeID() else { return nil }
        var point = CGPoint.zero
        return AXValueGetValue(value as! AXValue, .cgPoint, &point) ? point : nil
    }
    private static func frame(_ element: AXUIElement) -> CGRect? {
        guard let origin = point(element), let value = get(element, kAXSizeAttribute), CFGetTypeID(value) == AXValueGetTypeID() else { return nil }
        var size = CGSize.zero
        return AXValueGetValue(value as! AXValue, .cgSize, &size) ? CGRect(origin: origin, size: size) : nil
    }
    private static func domClasses(_ element: AXUIElement) -> [String] { get(element, "AXDOMClassList") as? [String] ?? [] }

    /// The text area Docs reads from: described "Document content", inside a docs.google.com document page (its outer web area's URL).
    static func isDocsText(_ element: AXUIElement) -> Bool {
        let now = ProcessInfo.processInfo.systemUptime
        if let known = docsKnown.first(where: { now - $0.time < 1.5 && CFEqual($0.element, element) }) { return known.docs }
        var docs = false
        if string(element, kAXRoleAttribute) == kAXTextAreaRole, string(element, kAXDescriptionAttribute) == Compat.docsTextDescription {
            var cursor = parent(element)
            for _ in 0..<8 {
                guard let current = cursor else { break }
                if string(current, kAXRoleAttribute) == "AXWebArea", let url = get(current, "AXURL") as? URL, url.scheme != "about" { docs = Compat.isGoogleDocsURL(url.absoluteString); break }
                cursor = parent(current)
            }
        }
        docsKnown = Array((docsKnown.filter { now - $0.time < 1.5 } + [(element, docs, now)]).suffix(16))
        return docs
    }
    /// The hidden text runs in document order, aligned to `value`; nil when they do not line up exactly (then there is no geometry rather than a wrong one).
    private static func docsRuns(_ element: AXUIElement, value: String) -> [DocsRun]? {
        let now = ProcessInfo.processInfo.systemUptime
        if let known = docsRunsCache, now - known.time < docsRunsLifetime, CFEqual(known.element, element), known.value == value { return known.runs }
        var found: [(element: AXUIElement, text: String)] = []
        var budget = 3000
        func walk(_ node: AXUIElement) {
            for child in children(node) {
                budget -= 1
                guard budget > 0 else { return }
                let values = multiple(child, [kAXRoleAttribute, kAXValueAttribute])
                if values[0] as? String == kAXStaticTextRole { if let text = values[1] as? String, !text.isEmpty { found.append((child, text)) } } else { walk(child) }
            }
        }
        walk(element)
        guard budget > 0, let starts = DocsGeometry.offsets(runs: found.map(\.text), in: value) else { return nil }
        let runs = zip(found, starts).map { DocsRun(element: $0.element, range: NSRange(location: $1, length: ($0.text as NSString).length)) }
        docsRunsCache = (element, value, runs, now)
        return runs
    }
    /// The local caret's screen point. A collapsed caret is a "kix-cursor-caret" DOM element (collaborators' carets have a name flag beside it) and is visible only
    /// when it has real height: scrolled out of view Docs shrinks it to one point. A selection has no caret element, so the iframe origin (the selection's focus) stands in.
    private static func docsCaret(_ element: AXUIElement, collapsed: Bool) -> CGPoint? {
        guard let web = parent(element), let iframe = parent(web), domClasses(iframe).contains("docs-texteventtarget-iframe"), let origin = point(iframe) else { return nil }
        guard collapsed else { return origin }
        guard let root = parent(iframe) else { return nil }
        var budget = 400
        func search(_ node: AXUIElement, _ depth: Int) -> CGPoint? {
            for child in children(node) {
                budget -= 1
                guard budget > 0 else { return nil }
                let classes = domClasses(child)
                if classes.contains("kix-cursor"), children(child).count == 1, let caret = children(child).first, domClasses(caret).contains("kix-cursor-caret"),
                   let box = frame(caret), box.height > 4, abs(box.minX - origin.x) < 2, abs(box.minY - origin.y) < 2 { return box.origin }
                if depth < 9, classes.isEmpty || classes.contains(where: { $0.hasPrefix("kix-appview") }), let found = search(child, depth + 1) { return found }
            }
            return nil
        }
        return search(root, 0)
    }
    private static func docsRun(_ runs: [DocsRun], containing index: Int) -> DocsRun? { runs.first { NSLocationInRange(index, $0.range) } }
    /// Hidden rect of the character at `index` (the leading edge).
    private static func docsLeading(_ runs: [DocsRun], _ index: Int) -> CGRect? {
        guard let run = docsRun(runs, containing: index) else { return nil }
        return axBounds(run.element, NSRange(location: index - run.range.location, length: 1))
    }
    /// Zero-width rect at the trailing edge of the character before `index` (a caret at the end of a run or of the text).
    private static func docsTrailing(_ runs: [DocsRun], _ index: Int) -> CGRect? {
        guard index > 0, let run = docsRun(runs, containing: index - 1), let box = axBounds(run.element, NSRange(location: index - 1 - run.range.location, length: 1)) else { return nil }
        return CGRect(x: box.maxX, y: box.minY, width: 0, height: box.height)
    }
    /// The selection in value offsets, and with `geometry` the runs, the hidden rect under the caret and the caret's screen point.
    /// A collapsed caret on a paragraph break reads the same from the end of one paragraph and the start of the next, so the caret's x settles which.
    private static func docsContext(_ element: AXUIElement, geometry wanted: Bool) -> DocsContext? {
        guard let value = string(element, kAXValueAttribute), let raw = rawRange(element) else { return nil }
        let now = ProcessInfo.processInfo.systemUptime
        if let known = docsCurrent, now - known.time < docsContextLifetime, CFEqual(known.element, element), known.value == value, known.raw == raw, !wanted || known.geometry != nil { return known }
        let text = value as NSString
        let starts = DocsGeometry.valueCandidates(selectionIndex: raw.location, in: text)
        let ends = raw.length == 0 ? starts : DocsGeometry.valueCandidates(selectionIndex: NSMaxRange(raw), in: text)
        var selection = NSRange(location: starts[starts.count - 1], length: raw.length == 0 ? 0 : max(0, ends[0] - starts[starts.count - 1]))
        let ambiguous = raw.length == 0 && starts.count > 1
        guard wanted || ambiguous else { return DocsContext(element: element, value: value, raw: raw, selection: selection, geometry: nil, time: now) }
        var geometry: DocsGeometryContext?
        if let runs = docsRuns(element, value: value), let caret = docsCaret(element, collapsed: raw.length == 0) {
            let positions = raw.length == 0 ? starts : [starts[starts.count - 1], ends[0]]
            let rects = positions.flatMap { position in [docsLeading(runs, position), docsTrailing(runs, position)].compactMap { $0 }.map { (position: position, rect: $0) } }
            if let best = DocsGeometry.nearest(rects, caretX: caret.x) {
                // More than one break at the offset means a blank paragraph: the caret's line has no hidden text to anchor on.
                if raw.length == 0 { selection = NSRange(location: best.position, length: 0) }
                if starts.count <= 2 || raw.length > 0 { geometry = DocsGeometryContext(runs: runs, anchor: best.rect, caret: caret) }
            }
        }
        let context = DocsContext(element: element, value: value, raw: raw, selection: selection, geometry: geometry, time: now)
        docsCurrent = context
        return context
    }
    /// The selection in value offsets (Parzr's offsets), from Docs' own.
    static func docsSelection(_ element: AXUIElement) -> NSRange? { docsContext(element, geometry: false)?.selection }
    /// Docs' selection range for a range in value offsets.
    static func docsSelectionRange(_ element: AXUIElement, _ range: NSRange) -> NSRange {
        guard let value = string(element, kAXValueAttribute) else { return range }
        let text = value as NSString
        let start = DocsGeometry.selectionIndex(valueIndex: range.location, in: text)
        return NSRange(location: start, length: DocsGeometry.selectionIndex(valueIndex: NSMaxRange(range), in: text) - start)
    }
    /// One screen rect (AX coordinates) per run piece of `range`, in text order.
    private static func docsPieces(_ element: AXUIElement, _ range: NSRange) -> [CGRect] {
        guard let context = docsContext(element, geometry: true)?.geometry else { return [] }
        return context.runs.compactMap { run in
            let part = NSIntersectionRange(run.range, range)
            guard part.length > 0, let hidden = axBounds(run.element, NSRange(location: part.location - run.range.location, length: part.length)) else { return nil }
            return DocsGeometry.screen(hidden, anchor: context.anchor, caret: context.caret)
        }
    }
    /// Screen rect (AX coordinates) enclosing `range`.
    static func docsBounds(_ element: AXUIElement, _ range: NSRange) -> CGRect? {
        let pieces = docsPieces(element, range)
        return pieces.dropFirst().reduce(pieces.first) { $0?.union($1) }
    }
    /// One screen rect (AX coordinates) per visual line of `range`.
    static func docsLines(_ element: AXUIElement, _ range: NSRange) -> [CGRect] { DocsGeometry.lines(docsPieces(element, range)) }
    /// Docs cannot place a caret at the end of a paragraph through a selection range (that offset means the start of the next paragraph), so a caret
    /// is put back with arrow keys: `count` characters right, or left when negative, from where the typed replacement left it.
    static func docsMoveCaret(_ app: NSRunningApplication, by count: Int) async {
        let key: CGKeyCode = count > 0 ? 124 : 123
        for _ in 0..<min(abs(count), 600) {
            for down in [true, false] {
                guard let event = CGEvent(keyboardEventSource: nil, virtualKey: key, keyDown: down) else { continue }
                event.flags = []
                event.postToPid(app.processIdentifier)
            }
            try? await Task.sleep(for: .milliseconds(8))
        }
    }
}
