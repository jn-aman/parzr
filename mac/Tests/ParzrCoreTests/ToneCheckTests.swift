import XCTest
@testable import ParzrCore

/// A scorer that reads the token ids: a text containing a trigger word gets that word's probabilities, anything else is neutral.
struct KeywordScorer: ToneScorer {
    let triggers: [Int32: [Float]]
    func probabilities(ids: [Int32], mask: [Int32]) throws -> [Float] {
        for id in ids { if let probs = triggers[id] { return probs } }
        return [0.97, 0.01, 0.01, 0.005, 0.005]
    }
}

final class ToneCheckTests: XCTestCase {
    static let words = ["[PAD]", "[UNK]", "[CLS]", "[SEP]", "thanks", "for", "finally", "replying", ".", "fix", "it", "now", "so", "sorry", ",",
                        "i", "'", "m", "the", "worst", "un", "##aff", "##able", "cafe", "can", "you", "send", "deck", "?", "here", "is", "!"]
    static let vocab = Dictionary(uniqueKeysWithValues: words.enumerated().map { ($1, Int32($0)) })
    static func id(_ word: String) -> Int32 { vocab[word]! }
    let config = ToneConfig(labels: ["neutral", "rude", "passive_aggressive", "curt", "over_apologetic"], threshold: 0.8, max_len: 16)
    func classifier(maxLength: Int = 16) throws -> ToneClassifier {
        let scorer = KeywordScorer(triggers: [Self.id("finally"): [0.05, 0.1, 0.8, 0.03, 0.02], Self.id("now"): [0.1, 0.2, 0.05, 0.6, 0.05],
                                              Self.id("worst"): [0.15, 0.05, 0.05, 0.05, 0.7], Self.id("deck"): [0.3, 0.6, 0.05, 0.03, 0.02]])
        return ToneClassifier(tokenizer: try WordPieceTokenizer(vocab: Self.vocab), scorer: scorer, config: ToneConfig(labels: config.labels, threshold: config.threshold, max_len: maxLength))
    }

    func testBasicTokensLowercaseStripAccentsAndSplitPunctuation() {
        XCTAssertEqual(WordPieceTokenizer.basicTokens("Thanks for FINALLY replying."), ["thanks", "for", "finally", "replying", "."])
        XCTAssertEqual(WordPieceTokenizer.basicTokens("I'm  the\tworst!"), ["i", "'", "m", "the", "worst", "!"])
        XCTAssertEqual(WordPieceTokenizer.basicTokens("Café"), ["cafe"])
        XCTAssertEqual(WordPieceTokenizer.basicTokens("a\u{0}b\u{7}c"), ["abc"], "control characters are dropped")
        XCTAssertEqual(WordPieceTokenizer.basicTokens("$5—ok"), ["$", "5", "—", "ok"])
    }

    func testWordPiecesUseLongestMatchAndUnknown() throws {
        let tokenizer = try WordPieceTokenizer(vocab: Self.vocab)
        XCTAssertEqual(tokenizer.wordPieces("unaffable"), [Self.id("un"), Self.id("##aff"), Self.id("##able")])
        XCTAssertEqual(tokenizer.wordPieces("zebra"), [tokenizer.unk])
        XCTAssertEqual(tokenizer.wordPieces(String(repeating: "a", count: 101)), [tokenizer.unk])
    }

    func testEncodeAddsSpecialTokensPadsAndTruncates() throws {
        let tokenizer = try WordPieceTokenizer(vocab: Self.vocab)
        let short = tokenizer.encode("Fix it now.", maxLength: 8)
        XCTAssertEqual(short.ids, [2, Self.id("fix"), Self.id("it"), Self.id("now"), Self.id("."), 3, 0, 0])
        XCTAssertEqual(short.mask, [1, 1, 1, 1, 1, 1, 0, 0])
        XCTAssertFalse(short.truncated)
        let long = tokenizer.encode("fix it now fix it now fix it now", maxLength: 6)
        XCTAssertEqual(long.ids.count, 6); XCTAssertEqual(long.ids.first, 2); XCTAssertEqual(long.ids.last, 3)
        XCTAssertEqual(long.mask, [1, 1, 1, 1, 1, 1])
        XCTAssertTrue(long.truncated)
    }

    func testTheVocabularyFileIsReadByLine() throws {
        let file = FileManager.default.temporaryDirectory.appendingPathComponent("vocab-\(UUID().uuidString).txt")
        defer { try? FileManager.default.removeItem(at: file) }
        try (Self.words.joined(separator: "\n") + "\n").write(to: file, atomically: true, encoding: .utf8)
        let tokenizer = try WordPieceTokenizer(vocabFile: file)
        XCTAssertEqual(tokenizer.vocab, Self.vocab)
        XCTAssertThrowsError(try WordPieceTokenizer(vocab: ["hello": 0]), "a vocabulary without [CLS] and friends is refused")
    }

    func testFlagsTheCategoryAboveTheThresholdAndLeavesNeutralTextAlone() throws {
        let tone = try classifier()
        let flag = try XCTUnwrap(try tone.check("Thanks for finally replying."))
        XCTAssertEqual(flag.category, .passiveAggressive)
        XCTAssertEqual(flag.score, 0.95, accuracy: 0.001)
        XCTAssertEqual(flag.range, NSRange(location: 0, length: 28))
        XCTAssertEqual(try tone.check("Fix it now.")?.category, .curt)
        XCTAssertEqual(try tone.check("So sorry, I'm the worst!")?.category, .overApologetic)
        XCTAssertNil(try tone.check("Can you send it?"))
        XCTAssertNil(try tone.check("Can you send the deck?"), "0.7 is below the 0.8 threshold")
    }

    func testNothingToCheckIsNeverFlagged() throws {
        let tone = try classifier()
        XCTAssertNil(try tone.check(""))
        XCTAssertNil(try tone.check("   \n"))
        XCTAssertNil(try tone.check("?!"))
        XCTAssertNil(try tone.check(String(repeating: "finally ", count: 300)), "past the length limit")
        XCTAssertFalse(ToneClassifier.checks(String(repeating: "a", count: ToneClassifier.maxCharacters + 1)))
    }

    func testALongMessageIsScoredBySentenceAndPointsAtTheWorstOne() throws {
        let tone = try classifier(maxLength: 8)
        let text = "Here is the deck. Can you send it? Thanks for finally replying."
        let flag = try XCTUnwrap(try tone.check(text))
        XCTAssertEqual(flag.category, .passiveAggressive)
        XCTAssertEqual((text as NSString).substring(with: flag.range), "Thanks for finally replying.")
        XCTAssertNil(try tone.check("Here is it. Can you send it? Thanks for replying."))
    }

    func testPartsAreTrimmedSentencesAndFittingPairs() {
        let text = "  One two.  Three four. Five.  "
        let all = ToneClassifier.parts(of: text) { _ in true }
        XCTAssertEqual(all.map { (text as NSString).substring(with: $0) }, ["One two.  Three four. Five."])
        let split = ToneClassifier.parts(of: text) { $0.count < 18 }.map { (text as NSString).substring(with: $0) }
        XCTAssertEqual(split, ["One two.", "Three four.", "Five.", "Three four. Five."])
    }

    func testCategoriesExplainThemselvesAndPickTheSofteningTone() {
        for category in ToneCategory.allCases {
            XCTAssertFalse(category.title.isEmpty); XCTAssertFalse(category.reason.isEmpty)
            XCTAssertLessThanOrEqual(category.reason.count, 90, "a reason is one short sentence")
        }
        XCTAssertEqual(ToneCategory.rude.softenMode(bundle: "com.tinyspeck.slackmacgap", text: "x"), .friendly)
        XCTAssertEqual(ToneCategory.passiveAggressive.softenMode(bundle: "com.apple.mail", text: "x"), .professional)
        XCTAssertEqual(ToneCategory.curt.softenMode(bundle: "com.apple.mail", text: "x"), .friendly)
        XCTAssertEqual(ToneCategory.overApologetic.softenMode(bundle: nil, text: "x"), .direct)
        XCTAssertEqual(ToneCategory(rawValue: "passive_aggressive"), .passiveAggressive)
    }

    func testTheCheckerCachesAndUnloads() async throws {
        let checker = ToneChecker()
        let noModel = await checker.check("Thanks for finally replying.")
        XCTAssertNil(noModel, "nothing is flagged before the model is loaded")
        await checker.use(try classifier())
        let first = await checker.check("Thanks for finally replying.")
        let again = await checker.check("Thanks for finally replying.")
        XCTAssertEqual(first?.category, .passiveAggressive); XCTAssertEqual(first, again)
        await checker.unload()
        let unloaded = await checker.isLoaded
        XCTAssertFalse(unloaded)
    }

    func testAPackFolderWithBadSettingsIsRefused() throws {
        let folder = FileManager.default.temporaryDirectory.appendingPathComponent("tone-\(UUID().uuidString)")
        defer { try? FileManager.default.removeItem(at: folder) }
        try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
        XCTAssertThrowsError(try ToneClassifier(folder: folder), "no files")
        try Data(#"{"labels":["rude","neutral"],"threshold":0.5,"max_len":64}"#.utf8).write(to: folder.appendingPathComponent("tone-config.json"))
        XCTAssertThrowsError(try ToneClassifier(folder: folder), "neutral must come first")
    }

    /// The real pack, when PARZR_TONE_DIR points at one (the `tone` folder scripts/tone-check/convert_coreml.py writes).
    func testTheRealModelFlagsTheObviousCasesAndPassesOrdinaryMessages() throws {
        let folder = URL(fileURLWithPath: ProcessInfo.processInfo.environment["PARZR_TONE_DIR"] ?? "")
        guard FileManager.default.fileExists(atPath: folder.appendingPathComponent("tone.mlmodelc").path) else { throw XCTSkip("No tone model here (set PARZR_TONE_DIR).") }
        let tone = try ToneClassifier(folder: folder)
        XCTAssertEqual(try tone.check("Who wrote this garbage? Are you incompetent?")?.category, .rude)
        XCTAssertEqual(try tone.check("Per my last three emails, the invoice was due on Monday.")?.category, .passiveAggressive)
        XCTAssertEqual(try tone.check("Sorry, sorry, I'm so sorry to bother you again, I'm the worst, sorry!")?.category, .overApologetic)
        XCTAssertNotNil(try tone.check("Not my problem. Figure it out yourself."))
        for fine in ["Can you send me the report by Friday?", "Thanks for the quick fix!", "I disagree, the data doesn't support that.", "ok", "Sorry, I missed your call. What's up?"] {
            XCTAssertNil(try tone.check(fine), fine)
        }
        // Warm once (the first prediction loads the model), then keep the fastest of three rounds: a busy test machine
        // slows a round down, it never speeds one up, so the best round is the check's own cost.
        _ = try tone.check("Warm the model up.")
        var best = Double.infinity
        for _ in 0..<3 {
            let started = Date()
            for _ in 0..<10 { _ = try tone.check("Thanks for finally getting back to me about the contract.") }
            best = min(best, Date().timeIntervalSince(started) / 10)
        }
        XCTAssertLessThan(best, 0.05, "a check takes well under 50 ms")
    }

    /// Swift's WordPiece against Hugging Face's on every DEV text: PARZR_TONE_PARITY names the JSON lines file
    /// scripts/tone-check/token_parity.py writes ({"text", "ids"}), PARZR_TONE_DIR the pack (for vocab.txt).
    func testTheTokenizerMatchesHuggingFaceOnTheDevelopmentTexts() throws {
        let environment = ProcessInfo.processInfo.environment
        guard let parity = environment["PARZR_TONE_PARITY"], let dir = environment["PARZR_TONE_DIR"], FileManager.default.fileExists(atPath: parity) else { throw XCTSkip("Set PARZR_TONE_PARITY and PARZR_TONE_DIR.") }
        let tokenizer = try WordPieceTokenizer(vocabFile: URL(fileURLWithPath: dir).appendingPathComponent("vocab.txt"))
        struct Row: Decodable { let text: String; let ids: [Int32] }
        var checked = 0, mismatches: [String] = []
        for line in try String(contentsOfFile: parity, encoding: .utf8).split(separator: "\n") {
            let row = try JSONDecoder().decode(Row.self, from: Data(line.utf8))
            if tokenizer.encode(row.text, maxLength: 64).ids != row.ids { mismatches.append(row.text) }
            checked += 1
        }
        XCTAssertGreaterThan(checked, 1000)
        XCTAssertEqual(mismatches, [], "\(mismatches.count) of \(checked) texts tokenize differently")
    }

    func testTheTonePackIsInTheEngineManifest() throws {
        guard let data = WritingEngine.modelManifest() else { throw XCTSkip("The engine library is not built here (set PARZR_ENGINE_PATH).") }
        let manifest = try ModelManifest.decode(data)
        let pack = try XCTUnwrap(manifest.pack(providing: "tone_model"))
        XCTAssertNotEqual(pack.id, manifest.essential?.id, "the tone model is its own download")
        XCTAssertLessThan(pack.bytes, 40_000_000, "the tone pack stays small")
        for name in ["tone/tone.mlmodelc/model.mil", "tone/vocab.txt", "tone/tone-config.json"] {
            XCTAssertTrue(pack.files.contains { $0.path == name }, name)
        }
    }
}
