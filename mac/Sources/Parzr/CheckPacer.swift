import Foundation

/// When a passive check runs after typing. Pure: the caller passes the clock (seconds) and does the scheduling.
/// One keystroke fires up to three triggers (key monitor, value change, selection change); only the first moves the timer.
struct CheckPacer {
    enum Plan: Equatable { case restart(ms: Double), keep }
    /// The Checking delay setting in ms: the wait for very fast bursts. A pause in typing waits a fraction of it (35 ms at the default 90).
    var ceiling: Double
    static let burstGap = 0.08, sameKeystroke = 0.05, wordEndWindow = 0.3
    private var lastKey = -Double.infinity
    private var wordEndPending = false
    var quiet: Double { max(20, ceiling * 7 / 18) }
    init(ceiling: Double = 90) { self.ceiling = ceiling }
    /// A key went down (before the editor has applied it). A word-ending key promotes the next value change to an immediate check.
    mutating func key(at time: Double, wordEnd: Bool) -> Plan {
        let gap = time - lastKey
        lastKey = time; wordEndPending = wordEnd
        return .restart(ms: gap < Self.burstGap ? ceiling : quiet)
    }
    /// The editor reported a change (value, selection, click, focus).
    mutating func changed(at time: Double) -> Plan {
        let since = time - lastKey
        if wordEndPending, since < Self.wordEndWindow { wordEndPending = false; return .restart(ms: 0) }
        return since < Self.sameKeystroke ? .keep : .restart(ms: quiet)
    }
    /// True when the key ends a word (space, return, tab or punctuation), judged from the typed character only; the character is never stored.
    static func endsWord(_ characters: String?) -> Bool {
        guard let scalar = characters?.unicodeScalars.last else { return false }
        return CharacterSet.whitespacesAndNewlines.contains(scalar) || CharacterSet.punctuationCharacters.contains(scalar)
    }
}

/// How fast the writer is typing, in characters per second over the last few seconds, and how long new marks should wait because of it.
/// Fast typing holds new underlines back so they do not flash up mid-word; slow typing shows them almost at once. Marks already on screen
/// are never delayed. Pure: the caller passes the clock (seconds). Only key times are kept, never which keys.
struct TypingMonitor {
    /// Speed is measured over this many seconds of keys.
    static let window = 5.0
    /// A pause this long ends the burst: the next key starts a new measurement.
    static let idle = 1.0
    /// A burst shorter than this is measured as if it had lasted this long, so two quick keys do not read as a sprint.
    static let shortest = 1.0
    static let capacity = 100
    /// Below `slow` characters a second new marks wait `minDelay`; at `fast` and above, `maxDelay`; linear between (ms).
    static let slow = 3.0, fast = 8.0, minDelay = 0.0, maxDelay = 600.0
    private var keys: [Double] = []
    mutating func key(at time: Double) {
        if let last = keys.last, time - last > Self.idle || time < last { keys.removeAll() }
        keys.append(time)
        keys.removeAll { time - $0 > Self.window }
        if keys.count > Self.capacity { keys.removeFirst(keys.count - Self.capacity) }
    }
    /// Characters per second, or 0 once the writer has paused.
    func speed(at time: Double) -> Double {
        guard let last = keys.last, time - last <= Self.idle else { return 0 }
        let recent = keys.filter { time - $0 <= Self.window }
        guard let first = recent.first, recent.count > 1 else { return 0 }
        return Double(recent.count - 1) / max(Self.shortest, last - first)
    }
    /// How long new marks wait now, in ms.
    func delay(at time: Double) -> Double {
        let fraction = min(1, max(0, (speed(at: time) - Self.slow) / (Self.fast - Self.slow)))
        return Self.minDelay + fraction * (Self.maxDelay - Self.minDelay)
    }
}
