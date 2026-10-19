import XCTest
import ParzrCore
@testable import Parzr

/// Typing-speed-aware reveal of new marks (pure: the clock is passed in; no AX, windows or engine).
final class TypingRevealTests: XCTestCase {
    private func typed(_ count: Int, every gap: Double, from start: Double = 100) -> (TypingMonitor, Double) {
        var monitor = TypingMonitor(), time = start
        for index in 0..<count { time = start + Double(index) * gap; monitor.key(at: time) }
        return (monitor, time)
    }
    func testNoTypingMeansNoDelay() {
        XCTAssertEqual(TypingMonitor().delay(at: 10), 0)
        XCTAssertEqual(TypingMonitor().speed(at: 10), 0)
    }
    func testSlowTypingShowsNewMarksAtOnce() {
        let (monitor, last) = typed(6, every: 0.5)
        XCTAssertEqual(monitor.speed(at: last), 2, accuracy: 0.001)
        XCTAssertEqual(monitor.delay(at: last), TypingMonitor.minDelay)
    }
    func testFastTypingWaitsTheLongestDelay() {
        let (monitor, last) = typed(40, every: 0.08)
        XCTAssertEqual(monitor.speed(at: last), 12.5, accuracy: 0.01)
        XCTAssertEqual(monitor.delay(at: last), TypingMonitor.maxDelay)
    }
    func testInBetweenSpeedsMapLinearly() {
        let (monitor, last) = typed(23, every: 1.0 / 5.5)
        XCTAssertEqual(monitor.speed(at: last), 5.5, accuracy: 0.01)
        XCTAssertEqual(monitor.delay(at: last), TypingMonitor.maxDelay / 2, accuracy: 1)
    }
    func testTwoQuickKeysAreNotASprint() {
        let (monitor, last) = typed(2, every: 0.03)
        XCTAssertEqual(monitor.speed(at: last), 1, accuracy: 0.001, "a burst shorter than a second counts as a second")
        XCTAssertEqual(monitor.delay(at: last), 0)
    }
    func testAPauseEndsTheBurst() {
        var (monitor, last) = typed(40, every: 0.08)
        XCTAssertEqual(monitor.delay(at: last + 1.01), 0, "the writer stopped: new marks show")
        monitor.key(at: last + 3)
        XCTAssertEqual(monitor.speed(at: last + 3), 0, "the next key starts a new measurement")
    }
    func testOnlyTheLastFiveSecondsCount() {
        var monitor = TypingMonitor(), time = 0.0
        for _ in 0..<60 { monitor.key(at: time); time += 0.1 } // 10 a second for 6 s
        for _ in 0..<10 { monitor.key(at: time); time += 0.5 } // then 2 a second for 5 s
        XCTAssertEqual(monitor.speed(at: time - 0.5), 2.8, accuracy: 0.01, "the fast burst has mostly left the window")
        XCTAssertEqual(monitor.delay(at: time - 0.5), 0)
    }

    func testMarksAlreadyOnScreenAreNotNew() {
        let shown = [WritingEdit(start: 2, end: 10, replacement: "received", original: "recieved")]
        let visible = Set(shown.map { MarkReveal.Key($0, at: 13) })
        let next = [WritingEdit(start: 2, end: 10, replacement: "received", original: "recieved"), WritingEdit(start: 16, end: 22, replacement: "message", original: "mesage")]
        XCTAssertEqual(MarkReveal.fresh(next, at: 13, visible: visible), [next[1].id])
    }
    func testTheSameWordsElsewhereOrWithAnotherFixAreNew() {
        let edit = WritingEdit(start: 2, end: 10, replacement: "received", original: "recieved")
        let visible: Set<MarkReveal.Key> = [MarkReveal.Key(edit, at: 13)]
        XCTAssertEqual(MarkReveal.fresh([edit], at: 20, visible: visible), [edit.id], "another place in the document")
        let other = WritingEdit(start: 2, end: 10, replacement: "relieved", original: "recieved")
        XCTAssertEqual(MarkReveal.fresh([other], at: 13, visible: visible), [other.id], "another replacement")
        XCTAssertTrue(MarkReveal.fresh([edit], at: 13, visible: visible).isEmpty)
    }
}
