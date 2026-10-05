import XCTest
import AppKit
@testable import ParzrCore

@MainActor
final class EditPlanTests: XCTestCase {
    func testNativeLinguisticHintsKeepParticiplesLowercaseAndPreserveEmphasis() async throws {
        guard ProcessInfo.processInfo.environment["PARZR_ENGINE_PATH"] != nil else { throw XCTSkip("Supply the built engine library.") }
        for (source, expected) in [
            ("This is not how it is suppose to be Done.", "This is not how it is supposed to be done."),
            ("This is not how it is suppose to be donme.", "This is not how it is supposed to be done."),
            ("We have DONE this.", "We have DONE this.")
        ] {
            let result = try await WritingEngine.typing.rewrite(EngineRequest(text: source))
            XCTAssertEqual(result.text, expected, source)
        }
    }
    func testTokenHintsCarryTheSystemSpellVerdictInTheRequestJSON() throws {
        let hints = WritingEngine.linguisticHints(for: "ask jatin about teh plan", known: ["ask", "about", "plan"])
        XCTAssertEqual(hints.map { String("ask jatin about teh plan".utf16.dropFirst($0.start_utf16).prefix($0.end_utf16 - $0.start_utf16))! }, ["ask", "jatin", "about", "teh", "plan"])
        XCTAssertEqual(hints.map(\.known), [true, false, true, false, true])
        let json = try XCTUnwrap(String(data: JSONEncoder().encode(EngineRequest(text: "ask plan", tokens: Array(hints.prefix(1)))), encoding: .utf8))
        XCTAssertTrue(json.contains("\"known\":true"), json)
        XCTAssertEqual(WordShape.shaped("don't"), "don't")
        XCTAssertNil(WordShape.shaped("Plan"))
    }
    func testLinkedWordOrderEditsPreserveTheNamedRun() async throws {
        guard ProcessInfo.processInfo.environment["PARZR_ENGINE_PATH"] != nil else { throw XCTSkip("Supply the built engine library.") }
        let source = "Not only Mira did help, but she also stayed."
        let result = try await WritingEngine.shared.rewrite(EngineRequest(text: source))
        XCTAssertEqual(result.text,"Not only did Mira help, but she also stayed.")
        let edits = EditPlan.related(to: try XCTUnwrap(result.edits.first), in: result.edits)
        XCTAssertEqual(edits.count,2)
        XCTAssertThrowsError(try EditPlan.apply([edits[0]],to:source))
        let attributed = NSMutableAttributedString(string:source)
        let name = (source as NSString).range(of:"Mira")
        let bold = NSFont.boldSystemFont(ofSize:16)
        attributed.addAttribute(.font,value:bold,range:name)
        let corrected = try EditPlan.apply(edits,to:attributed)
        XCTAssertEqual(corrected.string,result.text)
        let newName = (corrected.string as NSString).range(of:"Mira")
        XCTAssertEqual(corrected.attribute(.font,at:newName.location,effectiveRange:nil) as? NSFont,bold)
    }
    func testDevelopmentEngineDiscoveryFromIDEWorkingDirectory() throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: root.appendingPathComponent("engine"), withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: root) }
        try Data().write(to: root.appendingPathComponent("engine/Cargo.toml"))
        let paths = WritingEngine.libraryPaths(bundle: root.appendingPathComponent("mac/.build/debug"), workingDirectory: root.appendingPathComponent("mac"), supplied: nil)
        XCTAssertTrue(paths.contains(root.appendingPathComponent("engine/target/release/libparzr_engine.dylib").path))
        let installed = WritingEngine.libraryPaths(bundle: root.appendingPathComponent("parzr.app"), workingDirectory: root.appendingPathComponent("mac"), supplied: nil)
        XCTAssertEqual(installed, [root.appendingPathComponent("parzr.app/Contents/Frameworks/libparzr_engine.dylib").path])
    }
    func testUTF16OffsetsFollowingEmoji() throws {
        let source = "👩🏽‍💻 chek this"
        let edit = WritingEdit(start: 8, end: 12, replacement: "check", original: "chek")
        XCTAssertEqual(try EditPlan.apply([edit], to: source), "👩🏽‍💻 check this")
    }
    func testRejectsSplitSurrogatePair() {
        XCTAssertThrowsError(try EditPlan.apply([WritingEdit(start: 1, end: 2, replacement: "a", original: "")], to: "😀"))
    }
    func testRejectsStaleText() {
        XCTAssertThrowsError(try EditPlan.apply([WritingEdit(start: 0, end: 4, replacement: "check", original: "chek")], to: "chat"))
    }
    func testRejectsOverlappingEdits() {
        let a = WritingEdit(start: 0, end: 3, replacement: "a", original: "abc")
        let b = WritingEdit(start: 2, end: 4, replacement: "b", original: "cd")
        XCTAssertThrowsError(try EditPlan.apply([a,b], to: "abcd"))
    }
    func testRejectsUnsortedAndOutOfBoundsPlans() {
        XCTAssertThrowsError(try EditPlan.apply([WritingEdit(start: 9, end: 11, replacement: "", original: "")], to: "abc"))
        XCTAssertThrowsError(try EditPlan.apply([WritingEdit(start: 1, end: 0, replacement: "", original: "")], to: "abc"))
    }
    func testRichTextPreservesBoldItalicLinkAndParagraphs() throws {
        let source = NSMutableAttributedString(string: "Hello John, chek the document.\n\nThanks.")
        let font = NSFont.systemFont(ofSize: 15)
        source.addAttribute(.font, value: font, range: NSRange(location: 0, length: source.length))
        let bold = NSFontManager.shared.convert(font, toHaveTrait: .boldFontMask)
        let italic = NSFontManager.shared.convert(font, toHaveTrait: .italicFontMask)
        source.addAttribute(.font, value: bold, range: NSRange(location: 6, length: 4))
        source.addAttribute(.font, value: italic, range: NSRange(location: 12, length: 4))
        source.addAttribute(.link, value: URL(string: "https://example.com")!, range: NSRange(location: 21, length: 8))
        let paragraph = NSMutableParagraphStyle(); paragraph.headIndent = 16
        source.addAttribute(.paragraphStyle, value: paragraph, range: NSRange(location: 0, length: source.length))
        let result = try EditPlan.apply([WritingEdit(start: 12, end: 16, replacement: "check", original: "chek")], to: source)
        XCTAssertEqual(result.string, "Hello John, check the document.\n\nThanks.")
        XCTAssertEqual(result.attribute(.font, at: 6, effectiveRange: nil) as? NSFont, bold)
        XCTAssertEqual(result.attribute(.font, at: 12, effectiveRange: nil) as? NSFont, italic)
        XCTAssertEqual(result.attribute(.link, at: 22, effectiveRange: nil) as? URL, URL(string: "https://example.com"))
        XCTAssertEqual((result.attribute(.paragraphStyle, at: 0, effectiveRange: nil) as? NSParagraphStyle)?.headIndent, 16)
    }
    func testDeletionRetainsSurvivingAttributes() throws {
        let source = NSMutableAttributedString(string: "Please review this.")
        source.addAttribute(.link, value: "https://example.com", range: NSRange(location: 14, length: 4))
        let result = try EditPlan.apply([WritingEdit(start: 0, end: 7, replacement: "", original: "Please ")], to: source)
        XCTAssertEqual(result.string, "review this.")
        XCTAssertEqual(result.attribute(.link, at: 7, effectiveRange: nil) as? String, "https://example.com")
    }
    func testEmptyInsertion() throws {
        XCTAssertEqual(try EditPlan.apply([WritingEdit(start: 0, end: 0, replacement: "Hello", original: "")], to: NSAttributedString(string: "")).string, "Hello")
    }
    func testAdjacentEditsAndLineBreaks() throws {
        let edits = [WritingEdit(start: 0, end: 1, replacement: "I", original: "i"), WritingEdit(start: 2, end: 6, replacement: "check", original: "chek")]
        XCTAssertEqual(try EditPlan.apply(edits, to: "i chek\n\nthis"), "I check\n\nthis")
    }
    func testDuplicateInsertionsRejected() {
        let edit = WritingEdit(start: 0, end: 0, replacement: "x", original: "")
        XCTAssertThrowsError(try EditPlan.apply([edit,edit], to: ""))
    }
    func testJSONRoundtrip() throws {
        let request = EngineRequest(text: "Hello 😀", mode: .professional, dictionary: ["parzr"], sentenceStart: false)
        let decoded = try JSONDecoder().decode(EngineRequest.self, from: JSONEncoder().encode(request))
        XCTAssertEqual(decoded.text, request.text); XCTAssertFalse(decoded.sentence_start)
    }
    func testRequestCarriesNamesAndCapitalizeFlag() throws {
        let json = try XCTUnwrap(JSONSerialization.jsonObject(with: JSONEncoder().encode(EngineRequest(text: "x", names: ["Aman"], capitalizeNames: true))) as? [String: Any])
        XCTAssertEqual(json["names"] as? [String], ["Aman"]); XCTAssertEqual(json["capitalize_names"] as? Bool, true)
        let plain = try XCTUnwrap(JSONSerialization.jsonObject(with: JSONEncoder().encode(EngineRequest(text: "x"))) as? [String: Any])
        XCTAssertEqual(plain["names"] as? [String], []); XCTAssertEqual(plain["capitalize_names"] as? Bool, false)
    }
    func testPossessiveCliticMergesIntoNameHintOnly() {
        let text = "Aman's dog\u{2019}s book. Aman's"
        let hints = [TokenHint(range: NSRange(location: 0, length: 4), pos: "Noun", lemma: "aman", name: true), TokenHint(range: NSRange(location: 4, length: 2), pos: "Particle", lemma: "'s", name: false),
                     TokenHint(range: NSRange(location: 7, length: 3), pos: "Noun", lemma: "dog", name: false), TokenHint(range: NSRange(location: 10, length: 2), pos: "Particle", lemma: "'s", name: false)]
        let merged = WritingEngine.mergePossessives(hints, in: text)
        XCTAssertEqual(merged.count, 3)
        XCTAssertEqual(merged[0].start_utf16, 0); XCTAssertEqual(merged[0].end_utf16, 6); XCTAssertTrue(merged[0].name)
        XCTAssertEqual(merged[1].end_utf16, 10)
    }
    func testDroppingEditsRebuildsTheText() throws {
        let source = "teh Aman cat"
        let edits = [WritingEdit(start: 0, end: 3, replacement: "the", original: "teh", category: "Spelling"), WritingEdit(start: 4, end: 8, replacement: "A man", original: "Aman", category: "Spelling")]
        let result = RewriteResult(version: "t", text: "the A man cat", edits: edits, source_map: [], elapsed_ms: 0, protected_count: 0, warnings: nil)
        let trimmed = result.dropping(from: source) { $0.original == "Aman" }
        XCTAssertEqual(trimmed.edits.map(\.original), ["teh"]); XCTAssertEqual(trimmed.text, "the Aman cat")
        XCTAssertEqual(result.dropping(from: source) { _ in false }.edits.count, 2)
    }
    func testNativeEngineAcceptsNamesAndNeverRespellsThem() async throws {
        guard ProcessInfo.processInfo.environment["PARZR_ENGINE_PATH"] != nil else { throw XCTSkip("Supply PARZR_ENGINE_PATH to exercise the packaged Rust bridge.") }
        let text = "I met Aman Jain, and Aman's friend. aman jain was kind."
        let result = try await WritingEngine.typing.rewrite(EngineRequest(text: text, names: ["Aman", "Jain"], capitalizeNames: true))
        for edit in result.edits where edit.original.lowercased().contains("aman") || edit.original.lowercased().contains("jain") {
            XCTAssertEqual(edit.replacement.lowercased(), edit.original.lowercased(), "names may only change case: \(edit)")
        }
    }
    func testNativeEngineBridge() async throws {
        guard ProcessInfo.processInfo.environment["PARZR_ENGINE_PATH"] != nil else { throw XCTSkip("Supply PARZR_ENGINE_PATH to exercise the packaged Rust bridge.") }
        let result = try await WritingEngine.shared.rewrite(EngineRequest(text: "i hope your doing well. can you chek this once?"))
        XCTAssertTrue(["I hope you're doing well. Can you check this once?", "I hope you are doing well. Can you check this once?"].contains(result.text))
        XCTAssertEqual(try EditPlan.apply(result.edits, to: "i hope your doing well. can you chek this once?"), result.text)
    }
}
