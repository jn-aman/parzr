import AppKit
import ApplicationServices

/// Chromium answers AXBoundsForRange on a contenteditable composer with an empty rect (measured in Chrome 149, Electron 37 and the Edge 154 WebView
/// inside new Teams), so the composers of Slack, Discord, Notion, Teams, and Gmail or Outlook on the web in Chrome, Edge, Brave and Arc gave Parzr no
/// word geometry: it read the text, found the mistakes and drew nothing. The composer's AXStaticText descendants (one per DOM text node) do answer
/// AXBoundsForRange with the real word rects, so a range is measured on the runs it covers. Textareas and inputs still answer directly and keep that.
enum WebGeometry {
    /// What may sit in the composer's value between two text runs: line and paragraph breaks, spaces, and object replacement or zero-width characters.
    static func isGap(_ unit: unichar) -> Bool {
        unit == 0xFFFC || unit == 0x200B || unit == 0xFEFF || unit == 0x2060 || (Unicode.Scalar(unit).map { CharacterSet.whitespacesAndNewlines.contains($0) } ?? false)
    }
    /// Where `run` starts in `value` when it follows `cursor` across a gap only; nil otherwise, so a run that cannot be placed exactly gets no geometry rather than a wrong one.
    static func next(_ run: String, in value: NSString, from cursor: Int) -> Int? {
        guard !run.isEmpty, cursor <= value.length else { return nil }
        let found = value.range(of: run, options: .literal, range: NSRange(location: cursor, length: value.length - cursor))
        guard found.location != NSNotFound else { return nil }
        for index in cursor..<found.location where !isGap(value.character(at: index)) { return nil }
        return found.location
    }
    /// Start offset of each run in `value`, in order, up to the first run that cannot be placed.
    static func offsets(runs: [String], in value: String) -> [Int] {
        let text = value as NSString
        var cursor = 0, starts: [Int] = []
        for run in runs {
            guard let start = next(run, in: text, from: cursor) else { break }
            starts.append(start); cursor = start + (run as NSString).length
        }
        return starts
    }
}

extension AX {
    private static var chromiumKnown: [(element: AXUIElement, chromium: Bool, time: TimeInterval)] = []
    /// `covered`: how far into the value the runs reach; `complete`: the walk saw everything it could (it did not stop early at the range it was asked for).
    private static var webRunsCache: (element: AXUIElement, value: String, runs: [DocsRun], covered: Int, complete: Bool, time: TimeInterval)?
    private static let webLifetime: TimeInterval = 1.5
    static func forgetWeb() { chromiumKnown = []; webRunsCache = nil }

    /// Chromium tags every node it exposes with ChromeAXNodeId (Chrome, Edge, Brave, Arc, Electron apps, and Teams' WebView).
    static func isChromiumText(_ element: AXUIElement) -> Bool {
        let now = ProcessInfo.processInfo.systemUptime
        if let known = chromiumKnown.first(where: { now - $0.time < webLifetime && CFEqual($0.element, element) }) { return known.chromium }
        let chromium = get(element, "ChromeAXNodeId") != nil
        chromiumKnown = Array((chromiumKnown.filter { now - $0.time < webLifetime } + [(element, chromium, now)]).suffix(16))
        return chromium
    }
    /// The composer's text runs in document order, aligned to its value, at least through `end` when the runs reach that far.
    private static func webRuns(_ element: AXUIElement, through end: Int) -> [DocsRun] {
        guard let value = string(element, kAXValueAttribute) else { return [] }
        let now = ProcessInfo.processInfo.systemUptime
        if let known = webRunsCache, now - known.time < webLifetime, CFEqual(known.element, element), known.value == value, known.complete || known.covered >= end { return known.runs }
        let text = value as NSString
        var runs: [DocsRun] = [], cursor = 0, budget = 1500, reachedEnd = false, stopped = false
        func walk(_ node: AXUIElement, _ depth: Int) {
            for child in get(node, kAXChildrenAttribute) as? [AXUIElement] ?? [] {
                guard !stopped else { return }
                budget -= 1
                guard budget > 0 else { stopped = true; return }
                let values = multiple(child, [kAXRoleAttribute, kAXValueAttribute])
                if values[0] as? String == kAXStaticTextRole {
                    guard let run = values[1] as? String, !run.isEmpty else { continue }
                    guard let start = WebGeometry.next(run, in: text, from: cursor) else { stopped = true; return }
                    let length = (run as NSString).length
                    runs.append(DocsRun(element: child, range: NSRange(location: start, length: length)))
                    cursor = start + length
                    if cursor >= end { reachedEnd = true; stopped = true; return }
                } else if depth < 24 { walk(child, depth + 1) }
            }
        }
        walk(element, 0)
        webRunsCache = (element, value, runs, cursor, !reachedEnd, now)
        return runs
    }
    /// One rect (AX coordinates) per run piece of `range`, in text order; empty unless this is a Chromium element.
    private static func webPieces(_ element: AXUIElement, _ range: NSRange) -> [CGRect] {
        guard range.length > 0, isChromiumText(element) else { return [] }
        return webRuns(element, through: NSMaxRange(range)).compactMap { run in
            let part = NSIntersectionRange(run.range, range)
            guard part.length > 0 else { return nil }
            return axBounds(run.element, NSRange(location: part.location - run.range.location, length: part.length))
        }
    }
    /// Rect (AX coordinates) enclosing `range` in a Chromium composer, measured on its text runs.
    static func webBounds(_ element: AXUIElement, _ range: NSRange) -> CGRect? {
        let pieces = webPieces(element, range)
        guard let whole = pieces.dropFirst().reduce(pieces.first, { $0?.union($1) }) else { return nil }
        // A range that wraps measures as one box over both lines; the mark belongs on its first line.
        guard whole.height > 20, let character = webPieces(element, NSRange(location: range.location, length: 1)).first, whole.height > character.height * 1.5,
              let value = string(element, kAXValueAttribute), NSMaxRange(range) <= (value as NSString).length else { return whole }
        var words: [CGRect] = []
        (value as NSString).enumerateSubstrings(in: range, options: [.byWords, .substringNotRequired]) { _, word, _, stop in
            if words.count >= 40 { stop.pointee = true; return }
            words += webPieces(element, word)
        }
        return DocsGeometry.lines(words).first ?? whole
    }
    /// Chromium's line APIs are unreliable (AXLineForIndex answers 1 for every index past 0, AXRangeForLine only knows line 0),
    /// so a Chromium range is measured word by word and the words merged into one rect per visual line (Cocoa coordinates).
    static func chromiumLines(_ element: AXUIElement, _ range: NSRange) -> [CGRect] {
        guard let value = string(element, kAXValueAttribute) else { return [] }
        let text = value as NSString
        guard NSMaxRange(range) <= text.length else { return [] }
        var rects: [CGRect] = []
        text.enumerateSubstrings(in: range, options: [.byWords, .substringNotRequired]) { _, word, _, stop in
            if rects.count >= 80 { stop.pointee = true; return }
            if let rect = bounds(element, word), rect.width > 0 { rects.append(rect) }
        }
        return DocsGeometry.lines(rects)
    }
}
