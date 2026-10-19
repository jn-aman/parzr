import CoreML
import Foundation
import NaturalLanguage

// Tone check: a small on-device classifier (MiniLM fine-tuned on synthetic and openly licensed lines, see
// scripts/tone-check) that flags a message likely to read as rude, passive-aggressive, curt or overly
// apologetic, with a short reason. It only flags; softening goes through the existing tone rewrite.
// The model is the "tone" pack in engine/models.json, downloaded on demand when the setting is turned on.

/// What the tone check found. `neutral` is never flagged.
public enum ToneCategory: String, Codable, CaseIterable, Sendable {
    case rude, passiveAggressive = "passive_aggressive", curt, overApologetic = "over_apologetic"
    public var title: String {
        switch self {
        case .rude: "May read as rude"
        case .passiveAggressive: "May read as passive-aggressive"
        case .curt: "May read as curt"
        case .overApologetic: "Apologizes a lot"
        }
    }
    /// One short sentence: why a reader might take it that way.
    public var reason: String {
        switch self {
        case .rude: "Words aimed at the person, not the problem, can put the reader on the defensive."
        case .passiveAggressive: "Sarcasm or a pointed reminder can read as blame, even when you mean it lightly."
        case .curt: "A bare order or brush-off can sound cold. A little context or a please helps."
        case .overApologetic: "Several apologies can bury the request and undersell you."
        }
    }
    /// The rewrite that softens it: the app's usual tone for rude and passive-aggressive text, Friendly for a curt one,
    /// and Direct (no hedging or filler) for one that over-apologizes.
    public func softenMode(bundle: String?, text: String) -> RewriteMode {
        switch self {
        case .rude, .passiveAggressive: SuggestedRewrite.tone(for: bundle, text: text)
        case .curt: .friendly
        case .overApologetic: .direct
        }
    }
}

public struct ToneFlag: Equatable, Sendable {
    public var category: ToneCategory
    /// 1 - P(neutral) of the part that was flagged.
    public var score: Double
    /// The flagged part of the text in UTF-16 (the engine's unit): the whole text, or the sentence that scored highest.
    public var range: NSRange
    public var title: String { category.title }
    public var reason: String { category.reason }
    public init(category: ToneCategory, score: Double, range: NSRange) { self.category = category; self.score = score; self.range = range }
}

/// The settings the classifier was trained with (tone-config.json in the pack).
public struct ToneConfig: Codable, Equatable, Sendable {
    public var labels: [String]
    public var threshold: Double
    public var max_len: Int
    public init(labels: [String], threshold: Double, max_len: Int) { self.labels = labels; self.threshold = threshold; self.max_len = max_len }
}

/// BERT's uncased WordPiece tokenizer (what all-MiniLM-L6-v2 uses): lowercase, strip accents, split on whitespace and
/// punctuation, then greedy longest-match subwords with "##" continuations. Matches Hugging Face's BertTokenizer.
public struct WordPieceTokenizer: Sendable {
    public let vocab: [String: Int32]
    public let cls: Int32, sep: Int32, pad: Int32, unk: Int32
    static let maxWordCharacters = 100
    public init(vocab: [String: Int32]) throws {
        guard let cls = vocab["[CLS]"], let sep = vocab["[SEP]"], let pad = vocab["[PAD]"], let unk = vocab["[UNK]"] else {
            throw ParzrError.message("The tone model's vocabulary is incomplete.")
        }
        self.vocab = vocab; self.cls = cls; self.sep = sep; self.pad = pad; self.unk = unk
    }
    /// vocab.txt: one token per line, the line number is its id.
    public init(vocabFile: URL) throws {
        let text = try String(contentsOf: vocabFile, encoding: .utf8)
        var vocab: [String: Int32] = [:]
        for (index, line) in text.split(separator: "\n", omittingEmptySubsequences: false).enumerated() where !line.isEmpty {
            vocab[String(line)] = Int32(index)
        }
        try self.init(vocab: vocab)
    }
    static func isPunctuation(_ scalar: Unicode.Scalar) -> Bool {
        let v = scalar.value
        if (33...47).contains(v) || (58...64).contains(v) || (91...96).contains(v) || (123...126).contains(v) { return true }
        return CharacterSet.punctuationCharacters.contains(scalar)
    }
    static func isCJK(_ v: UInt32) -> Bool {
        (0x4E00...0x9FFF).contains(v) || (0x3400...0x4DBF).contains(v) || (0x20000...0x2A6DF).contains(v) || (0x2A700...0x2B73F).contains(v)
            || (0x2B740...0x2B81F).contains(v) || (0x2B820...0x2CEAF).contains(v) || (0xF900...0xFAFF).contains(v) || (0x2F800...0x2FA1F).contains(v)
    }
    /// Lowercased, accent-free words and punctuation marks.
    public static func basicTokens(_ text: String) -> [String] {
        var tokens: [String] = [], current = String.UnicodeScalarView()
        func flush() { if !current.isEmpty { tokens.append(String(current)); current = String.UnicodeScalarView() } }
        for scalar in text.lowercased().decomposedStringWithCanonicalMapping.unicodeScalars {
            let v = scalar.value
            let category = scalar.properties.generalCategory
            // As BertTokenizer: whitespace is space, tab, newline, return or a space separator (Zs); every other
            // "C" category (control, format such as a zero-width space, private use, unassigned) is dropped.
            if " \t\n\r".unicodeScalars.contains(scalar) || category == .spaceSeparator { flush(); continue }
            if v == 0 || v == 0xFFFD || [.control, .format, .privateUse, .surrogate, .unassigned].contains(category) { continue }
            if category == .nonspacingMark { continue }
            if isPunctuation(scalar) || isCJK(v) { flush(); tokens.append(String(scalar)); continue }
            current.append(scalar)
        }
        flush()
        return tokens
    }
    public func wordPieces(_ word: String) -> [Int32] {
        let chars = Array(word.unicodeScalars)
        guard chars.count <= Self.maxWordCharacters else { return [unk] }
        var pieces: [Int32] = [], start = 0
        while start < chars.count {
            var end = chars.count, found: Int32?
            while start < end {
                var piece = String(String.UnicodeScalarView(chars[start..<end]))
                if start > 0 { piece = "##" + piece }
                if let id = vocab[piece] { found = id; break }
                end -= 1
            }
            guard let id = found else { return [unk] }
            pieces.append(id); start = end
        }
        return pieces
    }
    /// [CLS] pieces [SEP], truncated to `maxLength`, then padded: the ids and the attention mask.
    public func encode(_ text: String, maxLength: Int) -> (ids: [Int32], mask: [Int32], truncated: Bool) {
        var ids: [Int32] = [cls]
        var truncated = false
        for word in Self.basicTokens(text) {
            let pieces = wordPieces(word)
            if ids.count + pieces.count > maxLength - 1 { ids += pieces.prefix(maxLength - 1 - ids.count); truncated = true; break }
            ids += pieces
        }
        ids.append(sep)
        let mask = [Int32](repeating: 1, count: ids.count) + [Int32](repeating: 0, count: maxLength - ids.count)
        return (ids + [Int32](repeating: pad, count: maxLength - ids.count), mask, truncated)
    }
}

/// Runs the network: token ids and mask in, one probability per label out (in ToneConfig.labels order).
public protocol ToneScorer: Sendable {
    func probabilities(ids: [Int32], mask: [Int32]) throws -> [Float]
}

/// The Core ML network from the tone pack (`tone.mlmodelc`): inputs input_ids and attention_mask (1 x max_len, int32),
/// output probs (1 x labels). Runs on the Neural Engine (about 1 ms), falling back to the CPU. Never the GPU: the 8-bit
/// network trips an MPSGraph assertion there, and the GPU belongs to the writing model.
public final class CoreMLToneScorer: ToneScorer, @unchecked Sendable {
    private let model: MLModel
    private let length: Int
    private let lock = NSLock()
    public init(compiledModel: URL, maxLength: Int) throws {
        let configuration = MLModelConfiguration()
        configuration.computeUnits = .cpuAndNeuralEngine
        model = try MLModel(contentsOf: compiledModel, configuration: configuration)
        length = maxLength
    }
    public func probabilities(ids: [Int32], mask: [Int32]) throws -> [Float] {
        let shape = [1, NSNumber(value: length)]
        let idArray = try MLMultiArray(shape: shape, dataType: .int32), maskArray = try MLMultiArray(shape: shape, dataType: .int32)
        for i in 0..<length { idArray[i] = NSNumber(value: ids[i]); maskArray[i] = NSNumber(value: mask[i]) }
        let input = try MLDictionaryFeatureProvider(dictionary: ["input_ids": idArray, "attention_mask": maskArray])
        let output = try lock.withLock { try model.prediction(from: input) }
        guard let probs = output.featureValue(for: "probs")?.multiArrayValue else { throw ParzrError.message("The tone model returned no scores.") }
        return (0..<probs.count).map { probs[$0].floatValue }
    }
}

/// Flags a message, or returns nil when it reads fine. Short texts are scored whole; a longer one is scored sentence by
/// sentence (two at a time, so a pointed second sentence keeps its context) and the highest-scoring part decides.
public struct ToneClassifier: Sendable {
    public let tokenizer: WordPieceTokenizer
    public let scorer: any ToneScorer
    public let config: ToneConfig
    /// Texts longer than this are not checked (a tone check is for a message, not a document).
    public static let maxCharacters = 2000
    public init(tokenizer: WordPieceTokenizer, scorer: any ToneScorer, config: ToneConfig) {
        self.tokenizer = tokenizer; self.scorer = scorer; self.config = config
    }
    /// The installed pack folder: tone.mlmodelc, vocab.txt and tone-config.json.
    public init(folder: URL) throws {
        let config = try JSONDecoder().decode(ToneConfig.self, from: Data(contentsOf: folder.appendingPathComponent("tone-config.json")))
        guard config.labels.first == "neutral", config.max_len >= 8, config.max_len <= 512, (0.0...1.0).contains(config.threshold) else {
            throw ParzrError.message("The tone model's settings are invalid.")
        }
        let tokenizer = try WordPieceTokenizer(vocabFile: folder.appendingPathComponent("vocab.txt"))
        let scorer = try CoreMLToneScorer(compiledModel: folder.appendingPathComponent("tone.mlmodelc"), maxLength: config.max_len)
        self.init(tokenizer: tokenizer, scorer: scorer, config: config)
    }

    /// Worth checking: some letters, at least one word, not too long.
    public static func checks(_ text: String) -> Bool {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        return !trimmed.isEmpty && trimmed.count <= maxCharacters && trimmed.contains(where: \.isLetter)
    }

    /// The highest-scoring part's category when 1 - P(neutral) reaches the threshold.
    public func check(_ text: String) throws -> ToneFlag? {
        guard Self.checks(text) else { return nil }
        var best: (score: Double, category: ToneCategory, range: NSRange)?
        for part in Self.parts(of: text, fits: { tokenizer.encode($0, maxLength: config.max_len).truncated == false }) {
            let encoded = tokenizer.encode((text as NSString).substring(with: part), maxLength: config.max_len)
            let probs = try scorer.probabilities(ids: encoded.ids, mask: encoded.mask)
            guard probs.count == config.labels.count else { throw ParzrError.message("The tone model returned \(probs.count) scores for \(config.labels.count) labels.") }
            let harsh = 1 - Double(probs[0])
            var top: (Float, ToneCategory)?
            for (index, label) in config.labels.enumerated().dropFirst() {
                guard let category = ToneCategory(rawValue: label) else { continue }
                if top == nil || probs[index] > top!.0 { top = (probs[index], category) }
            }
            if let top, best == nil || harsh > best!.score { best = (harsh, top.1, part) }
        }
        guard let best, best.score >= config.threshold else { return nil }
        return ToneFlag(category: best.category, score: best.score, range: best.range)
    }

    /// The whole text when it fits the model; otherwise each sentence and each pair of neighbouring sentences that fits
    /// (a sentence too long on its own is still scored, truncated). Ranges are UTF-16, trimmed of surrounding spaces.
    static func parts(of text: String, fits: (String) -> Bool) -> [NSRange] {
        let whole = trimmed(NSRange(location: 0, length: (text as NSString).length), in: text)
        if fits(text) { return [whole] }
        let tokenizer = NLTokenizer(unit: .sentence)
        tokenizer.string = text
        var sentences: [NSRange] = []
        tokenizer.enumerateTokens(in: text.startIndex..<text.endIndex) { range, _ in
            let r = trimmed(NSRange(range, in: text), in: text)
            if r.length > 0 { sentences.append(r) }
            return true
        }
        if sentences.isEmpty { return [whole] }
        var parts = sentences
        for (a, b) in zip(sentences, sentences.dropFirst()) {
            let pair = NSRange(location: a.location, length: b.location + b.length - a.location)
            if fits((text as NSString).substring(with: pair)) { parts.append(pair) }
        }
        return parts
    }
    static func trimmed(_ range: NSRange, in text: String) -> NSRange {
        let ns = text as NSString
        var start = range.location, end = range.location + range.length
        while start < end, let s = UnicodeScalar(ns.character(at: start)), CharacterSet.whitespacesAndNewlines.contains(s) { start += 1 }
        while end > start, let s = UnicodeScalar(ns.character(at: end - 1)), CharacterSet.whitespacesAndNewlines.contains(s) { end -= 1 }
        return NSRange(location: start, length: end - start)
    }
}

/// Loads the classifier once from the installed tone pack and runs checks off the main actor.
public actor ToneChecker {
    public static let shared = ToneChecker()
    private var classifier: ToneClassifier?
    private var loadedFolder: URL?
    private var cache: [String: ToneFlag?] = [:]
    public init() {}
    /// Uses this classifier (tests; or a classifier the app built itself).
    public func use(_ classifier: ToneClassifier?) { self.classifier = classifier; loadedFolder = nil; cache = [:] }
    /// Loads the pack folder if it is not the one already loaded. Throws when the files are damaged.
    public func load(folder: URL) throws {
        guard loadedFolder != folder else { return }
        classifier = try ToneClassifier(folder: folder); loadedFolder = folder; cache = [:]
    }
    public func unload() { classifier = nil; loadedFolder = nil; cache = [:] }
    public var isLoaded: Bool { classifier != nil }
    /// nil when the message reads fine, the classifier is not loaded, or it failed.
    public func check(_ text: String) -> ToneFlag? {
        guard let classifier else { return nil }
        if let hit = cache[text] { return hit }
        let flag = try? classifier.check(text)
        if cache.count > 256 { cache.removeAll() }
        cache[text] = flag
        return flag
    }
}
