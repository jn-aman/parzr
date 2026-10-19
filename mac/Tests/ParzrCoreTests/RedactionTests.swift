import XCTest
@testable import ParzrCore

final class RedactionTests: XCTestCase {
    private func r(_ text: String, names: [String] = []) -> String { Redactor.redact(text, names: names) }

    // MARK: Emails
    func testEmailsAreRedacted() {
        XCTAssertEqual(r("write to aman.jain+work@example.co.uk today"), "write to [email] today")
        XCTAssertEqual(r("ping me at x@y.io."), "ping me at [email].")
        XCTAssertEqual(r("mail first_last@sub.mail-host.org or not"), "mail [email] or not")
        XCTAssertEqual(r("(bob@corp.com)"), "([email])")
        XCTAssertEqual(r("mailto:help@parzr.app"), "[email]")
        XCTAssertEqual(r("Ünïcode josé@exämple.com here").contains("josé"), false)
    }

    // MARK: Links
    func testLinksWithSchemesAreRedacted() {
        XCTAssertEqual(r("see https://github.com/jn-aman/parzr/issues/12 for it"), "see [link] for it")
        XCTAssertEqual(r("open http://localhost:8080/x?y=1."), "open [link].")
        XCTAssertEqual(r("join slack://channel?team=T1 now"), "join [link] now")
        XCTAssertEqual(r("visit www.example.net, then"), "visit [link], then")
        XCTAssertEqual(r("ftp://files.host/a.zip"), "[link]")
    }
    func testBareDomainsAreRedacted() {
        XCTAssertEqual(r("it is on parzr.app now"), "it is on [link] now")
        XCTAssertEqual(r("go to docs.google.com/document/d/abc and edit"), "go to [link] and edit")
        XCTAssertEqual(r("my site is aman.dev."), "my site is [link].")
        XCTAssertEqual(r("Google.com is down"), "[link] is down")
    }
    func testAMissingSpaceAfterAFullStopIsNotALink() {
        XCTAssertEqual(r("i went home.So tired"), "i went home.So tired", "a capitalized word after a missing space is a typo, not a domain")
        XCTAssertEqual(r("finish this.then go"), "finish this.then go")
        XCTAssertEqual(r("e.g. this, i.e. that"), "e.g. this, i.e. that")
    }

    // MARK: Phones and numbers
    func testPhoneNumbersAreRedacted() {
        XCTAssertEqual(r("call +1 (415) 555-0100 today"), "call [phone] today")
        XCTAssertEqual(r("my number is 98765 43210"), "my number is [phone]")
        XCTAssertEqual(r("ring 020 7946 0958."), "ring [phone].")
        XCTAssertEqual(r("fax: 555.123.4567"), "fax: [phone]")
    }
    func testEveryOtherNumberIsRedacted() {
        XCTAssertEqual(r("we have 3 dogs"), "we have [number] dogs")
        XCTAssertEqual(r("it costs $1,200.50 now"), "it costs $[number] now")
        XCTAssertEqual(r("meet at 10:30 on 2026-10-19"), "meet at [number] on [phone]", "a long run of digits reads as a phone number; either way it is gone")
        XCTAssertEqual(r("the 4th time"), "the [number] time")
        XCTAssertEqual(r("order #A12B-77 shipped"), "order #[number] shipped")
        XCTAssertEqual(r("version v2 and 3.5x faster"), "version [number] and [number] faster")
        XCTAssertEqual(r("PIN 4821"), "PIN [number]")
        XCTAssertEqual(r("card 4111 1111 1111 1111"), "card [phone]", "long digit runs are redacted whatever they are")
        XCTAssertEqual(r("COVID-19 cases"), "COVID-[number] cases")
        XCTAssertEqual(r("Arabic-Indic ٣ and full-width ７"), "Arabic-Indic [number] and full-width [number]")
        XCTAssertEqual(r("an api key sk-live-9f8a7b6c5d"), "an api key [key]")
    }
    func testSpelledOutNumbersAreRedacted() {
        XCTAssertEqual(r("pin is four four two one"), "pin is [number]")
        XCTAssertEqual(r("call nine eight seven, six five"), "call [number]")
        XCTAssertEqual(r("Code Seven-Two-Nine works"), "Code [number] works")
        XCTAssertEqual(r("one or two things"), "one or two things", "two number words are ordinary prose")
        XCTAssertEqual(r("one of the two"), "one of the two")
    }

    // MARK: Keys and tokens
    func testKeysAndTokensAreRedacted() {
        // Fake keys are assembled at run time so the source never holds a token-shaped literal (scripts/audit-public-repo.py).
        let live = "sk_" + "live_abcdefghijk", github = "gh" + "p_abcdefghijklmnopqrstuvwxyz0123"
        let slack = "xo" + "xb-abc-def-ghi", aws = "AK" + "IAABCDEFGHIJKLMNOP"
        XCTAssertEqual(r("token \(live)"), "token [key]")
        XCTAssertEqual(r("use pk_test_abcdEFGH here"), "use [key] here")
        XCTAssertEqual(r("\(github) works"), "[key] works")
        XCTAssertEqual(r("slack \(slack) ok"), "slack [key] ok")
        XCTAssertEqual(r("aws \(aws)"), "aws [key]")
        XCTAssertEqual(r("jwt eyJhbGciOiJIUzI1NiJ9.e30 sent"), "jwt [key] sent")
        XCTAssertEqual(r("secret AbCdEfGhIjKlMnOpQrStUvWx"), "secret [key]", "long mixed-case runs are keys")
        XCTAssertEqual(r("id abc_def_ghi_jkl_mno_pqr"), "id [key]")
        XCTAssertEqual(r("internationalization matters"), "internationalization matters", "a long word is not a key")
    }

    // MARK: Emails spelled out, hashtags
    func testSpelledOutEmailsAreRedacted() {
        XCTAssertEqual(r("aman at gmail dot com"), "[email]")
        XCTAssertEqual(r("write to aman (at) gmail (dot) com"), "write to [email]")
        XCTAssertEqual(r("meet at home"), "meet at home")
    }
    func testHashtagsAreRedacted() {
        XCTAssertEqual(r("ping #rahulsharma today"), "ping [name] today")
        XCTAssertEqual(r("order #A12B-77 shipped"), "order #[number] shipped")
    }

    // MARK: Lowercase names
    func testLowercaseNamesTheLexiconKnowsAreRedacted() {
        XCTAssertEqual(r("rahul has the keys"), "[name] has the keys")
        XCTAssertEqual(r("met mary and jain today"), "met [name] and [name] today")
    }
    func testWordsTheLexiconDoesNotKnowAreRedacted() {
        XCTAssertEqual(r("i has told priya about it"), "i has told [name] about it")
        XCTAssertEqual(r("with neha and vikram"), "with [name] and [name]")
    }
    func testTheWordAfterAGreetingIsAName() {
        XCTAssertEqual(r("hi rahul, i has told priya about it"), "hi [name], i has told [name] about it")
        XCTAssertEqual(r("hey mark, can you"), "hey [name], can you")
        XCTAssertEqual(r("thanks bob for this"), "thanks [name] for this")
        XCTAssertEqual(r("hi there, thanks so much"), "hi there, thanks so much")
        XCTAssertEqual(r("hey guys, thanks for coming"), "hey guys, thanks for coming")
    }
    func testOrdinaryLowercaseProseIsKept() {
        XCTAssertEqual(r("i went to the cafe yesterday and it was good"), "i went to the cafe yesterday and it was good")
        XCTAssertEqual(r("please send the report by friday"), "please send the report by friday")
    }
    func testIsCleanRefusesWhatTheNewDetectorsFind() {
        for leak in ["pin is four four two one", "aman at gmail dot com", "#rahulsharma", "token sk_live_abcdefghijk", "@rahul", "AbCdEfGhIjKlMnOpQrStUvWx", "my HIV test", "her cancer", "she is pregnant"] {
            XCTAssertFalse(Redactor.isClean(leak), leak)
        }
        XCTAssertTrue(Redactor.isClean("hi [name], the [key] is at [link]"))
    }
    func testNoDigitSurvives() {
        let samples = ["Room 101, floor 3", "IP 192.168.0.1", "ZIP 94103-1234", "sent 1/2/24 at 5pm", "x=12;y=3", "€5,00", "2nd and 3rd", "a1b2c3", "#42"]
        for sample in samples { XCTAssertFalse(r(sample).contains(where: \.isNumber), "\(sample) → \(r(sample))") }
    }

    // MARK: Names
    func testKnownNamesAreRedactedInAnyCase() {
        XCTAssertEqual(r("thanks aman, see you", names: ["Aman Jain"]), "thanks [name], see you")
        XCTAssertEqual(r("Aman's draft and jain's notes", names: ["Aman Jain"]), "[name] draft and [name] notes")
        XCTAssertEqual(r("PRIYA said hi", names: ["Priya"]), "[name] said hi")
    }
    func testAKnownNameThatIsACommonWordStaysWhenLowercase() {
        XCTAssertEqual(r("i will go", names: ["Will", "Mark"]), "i will go")
        XCTAssertEqual(r("mark it, then ask Will", names: ["Will", "Mark"]), "mark it, then ask [name]")
    }
    func testCapitalizedWordsInsideASentenceAreTreatedAsNames() {
        XCTAssertEqual(r("i met Siddharth at the cafe"), "i met [name] at the cafe")
        XCTAssertEqual(r("tell Ana-Maria and O’Brien"), "tell [name] and [name]")
        XCTAssertEqual(r("ask @devteam or @aman.j"), "ask [name] or [name]")
    }
    func testSentenceStartsTheWordIAndCalendarWordsAreKept() {
        XCTAssertEqual(r("The cat sat. Then it slept."), "The cat sat. Then it slept.")
        XCTAssertEqual(r("so I think I'm late"), "so I think I'm late")
        XCTAssertEqual(r("see you on Monday in March"), "see you on Monday in March")
        XCTAssertEqual(r("we need it ASAP, OK"), "we need it ASAP, OK", "all-caps abbreviations are not names")
        XCTAssertEqual(r("Line one\nNext line"), "Line one\nNext line")
        XCTAssertEqual(r("he said \"Hello there\""), "he said \"Hello there\"")
    }
    func testTheTaggerFindsANameAtTheStartOfASentence() {
        let out = r("Jennifer Lawrence called me yesterday.")
        XCTAssertFalse(out.contains("Jennifer") || out.contains("Lawrence"), out)
    }

    // MARK: Mixed
    func testAMessageWithEverything() {
        let text = "Hi Rahul, call me on +44 7700 900123 or mail rahul.k@acme.com; the doc is at https://acme.com/q3 (due 12/10)."
        let out = r(text)
        XCTAssertEqual(out, "Hi [name], call me on [phone] or mail [email]; the doc is at [link] (due [number]).")
        XCTAssertTrue(Redactor.isClean(out))
    }
    func testPlaceholdersAreNeverRedactedAgain() {
        XCTAssertEqual(r(r("call 555 0100 and Anna")), "call [phone] and [name]")
    }
    func testIsCleanFindsWhatRedactionRemoves() {
        XCTAssertFalse(Redactor.isClean("call 5"))
        XCTAssertFalse(Redactor.isClean("a@b.com"))
        XCTAssertFalse(Redactor.isClean("parzr.app"))
        XCTAssertFalse(Redactor.isClean("https://x"))
        XCTAssertTrue(Redactor.isClean("call [number] at [link] or [email]"))
        XCTAssertTrue(Redactor.isClean(""))
    }

    // MARK: Suggestions
    func testASuggestionOutsideAnySpanKeepsItsWordsAndMovesItsOffsets() throws {
        let sentence = "Call Rahul at 5 tomorow."
        let edit = (sentence as NSString).range(of: "tomorow")
        let s = try XCTUnwrap(Redactor.redact(sentence: sentence, edit: edit, replacement: "tomorrow"))
        XCTAssertEqual(s.sentence, "Call [name] at [number] tomorow.")
        XCTAssertEqual(s.original, "tomorow"); XCTAssertEqual(s.replacement, "tomorrow")
        XCTAssertEqual((s.sentence as NSString).substring(with: NSRange(location: s.start, length: s.end - s.start)), "tomorow")
    }
    func testASuggestionOnANameIsRedactedOnBothSides() throws {
        let sentence = "Thanks Priyanka for the notes."
        let edit = (sentence as NSString).range(of: "Priyanka")
        let s = try XCTUnwrap(Redactor.redact(sentence: sentence, edit: edit, replacement: "Priyanks"))
        XCTAssertEqual(s.original, "[name]")
        XCTAssertEqual(s.replacement, "[name]", "a respelt name must not leak through the replacement")
        XCTAssertFalse(s.sentence.contains("Priyank"))
    }
    func testALowercaseNameFixIsRedactedOnBothSides() throws {
        let sentence = "hi aman, ok"
        let edit = (sentence as NSString).range(of: "aman")
        let s = try XCTUnwrap(Redactor.redact(sentence: sentence, edit: edit, replacement: "Aman", names: ["Aman Jain"]))
        XCTAssertEqual(s.sentence, "hi [name], ok"); XCTAssertEqual(s.original, "[name]"); XCTAssertEqual(s.replacement, "[name]")
    }
    func testASuggestionThatTouchesANumberCoversTheWholeNumber() throws {
        let sentence = "see you at 5pm then"
        let edit = (sentence as NSString).range(of: "pm")
        let s = try XCTUnwrap(Redactor.redact(sentence: sentence, edit: edit, replacement: " p.m."))
        XCTAssertEqual(s.sentence, "see you at [number] then")
        XCTAssertEqual(s.original, "[number]")
        XCTAssertEqual(s.replacement, "[number] p.m.")
        XCTAssertFalse(s.replacement.contains("5"))
    }
    func testAnInsertionInsideAnEmailCoversTheEmail() throws {
        let sentence = "mail ab@cd.com now"
        let s = try XCTUnwrap(Redactor.redact(sentence: sentence, edit: NSRange(location: 7, length: 0), replacement: "x"))
        XCTAssertEqual(s.original, "[email]"); XCTAssertEqual(s.replacement, "[email]")
    }
    func testAnInsertionBetweenWordsStaysAnInsertion() throws {
        let sentence = "I has 2 dog"
        let edit = NSRange(location: 11, length: 0)
        let s = try XCTUnwrap(Redactor.redact(sentence: sentence, edit: edit, replacement: "s"))
        XCTAssertEqual(s.sentence, "I has [number] dog"); XCTAssertEqual(s.start, s.end); XCTAssertEqual(s.start, s.sentence.utf16.count)
        XCTAssertEqual(s.original, ""); XCTAssertEqual(s.replacement, "s")
    }
    func testAReplacementThatAddsPrivateTextIsRedacted() throws {
        let s = try XCTUnwrap(Redactor.redact(sentence: "email me", edit: NSRange(location: 6, length: 2), replacement: "me at a@b.com"))
        XCTAssertEqual(s.replacement, "me at [email]")
    }
    func testAnEditOutsideTheSentenceIsRefused() {
        XCTAssertNil(Redactor.redact(sentence: "short", edit: NSRange(location: 3, length: 9), replacement: "x"))
    }
}
