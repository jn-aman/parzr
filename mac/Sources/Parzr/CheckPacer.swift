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
