import XCTest
@testable import Parzr

/// Underlines cover only the words a fix changes (pure: strings only; line splitting itself needs AX geometry).
final class MarkSpanTests: XCTestCase {
    private func underlined(_ original: String, _ replacement: String) -> String {
        (original as NSString).substring(with: MarkSpan.changed(original: original, replacement: replacement))
    }
    func testASpellingFixUnderlinesTheWholeWord() {
        XCTAssertEqual(underlined("teh", "the"), "teh")
        XCTAssertEqual(underlined("recieved", "received"), "recieved")
        XCTAssertEqual(underlined("dont", "don't"), "dont")
    }
    func testOnlyTheChangedWordOfALongerEditIsUnderlined() {
        XCTAssertEqual(underlined("a apple", "an apple"), "a")
        XCTAssertEqual(underlined("the the", "the"), "the")
        XCTAssertEqual(MarkSpan.changed(original: "the the", replacement: "the"), NSRange(location: 4, length: 3), "the repeated word, not the first")
        XCTAssertEqual(underlined("in order to make", "to make"), "in order")
        XCTAssertEqual(underlined("She go to school", "She goes to school"), "go")
        XCTAssertEqual(underlined("Hi John", "Hi, John"), "Hi", "a missing comma marks the word it follows")
    }
    func testAFullRewriteKeepsTheWholeEdit() {
        XCTAssertEqual(underlined("has went", "have gone"), "has went")
        XCTAssertEqual(underlined("irregardless", "regardless"), "irregardless")
        XCTAssertEqual(MarkSpan.changed(original: "", replacement: ","), NSRange(location: 0, length: 0))
    }
    func testADeletedSpaceOrPunctuationStillMarksSomething() {
        XCTAssertEqual(underlined("word ,", "word,"), "word ,", "a removed space alone has no word to mark, so the whole edit is")
        XCTAssertFalse(MarkSpan.changed(original: "  ", replacement: " ").length == 0, "an all-space edit falls back to the whole edit")
    }
    func testEmojiAreNeverCutInHalf() {
        let range = MarkSpan.changed(original: "I 😀 it", replacement: "I 😃 it")
        XCTAssertEqual(("I 😀 it" as NSString).substring(with: range), "😀")
    }
    func testOnlyTextWithABreakOrSpaceCanWrap() {
        XCTAssertTrue(MarkSpan.mayWrap("in order"))
        XCTAssertTrue(MarkSpan.mayWrap("end\nstart"))
        XCTAssertFalse(MarkSpan.mayWrap("recieved"))
    }
}
