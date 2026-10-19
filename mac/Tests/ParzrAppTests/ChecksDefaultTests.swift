import XCTest
import ParzrCore
@testable import Parzr

/// The Slip check and the Tone check: both on by default, an explicit earlier "off" kept, one switch each, and the
/// switch decides whether a check runs and whether its pack downloads on its own.
@MainActor
final class ChecksDefaultTests: XCTestCase {
    private func suite(_ name: String) throws -> UserDefaults {
        let defaults = try XCTUnwrap(UserDefaults(suiteName: name)); defaults.removePersistentDomain(forName: name)
        return defaults
    }

    func testBothChecksAreOnForAnyoneWhoNeverTouchedTheSwitch() throws {
        let defaults = try suite("app.parzr.tests.checks-fresh"); defer { defaults.removePersistentDomain(forName: "app.parzr.tests.checks-fresh") }
        let prefs = Preferences(defaults: defaults)
        XCTAssertTrue(prefs.toneCheck); XCTAssertTrue(prefs.slipCheck)
        XCTAssertNil(defaults.object(forKey: "toneCheck"), "the default is not written: a later default change still reaches untouched users")
        XCTAssertTrue(OptionalChecks.isOn(.tone, preferences: prefs)); XCTAssertTrue(OptionalChecks.isOn(.slips, preferences: prefs))
    }

    func testAnExplicitEarlierOffStaysOff() throws {
        let defaults = try suite("app.parzr.tests.checks-off"); defer { defaults.removePersistentDomain(forName: "app.parzr.tests.checks-off") }
        // Tone check was opt-in before 0.5.3: someone who turned it on and off again has false stored.
        defaults.set(false, forKey: "toneCheck"); defaults.set(false, forKey: "slipCheck")
        let prefs = Preferences(defaults: defaults)
        XCTAssertFalse(prefs.toneCheck); XCTAssertFalse(prefs.slipCheck)
        XCTAssertFalse(OptionalChecks.isOn(.tone, preferences: prefs)); XCTAssertFalse(OptionalChecks.isOn(.slips, preferences: prefs))
        prefs.slipCheck = true
        XCTAssertTrue(Preferences(defaults: defaults).slipCheck, "the switch persists")
        XCTAssertFalse(Preferences(defaults: defaults).toneCheck)
    }

    func testTheSlipSwitchTravelsInEveryRequest() throws {
        let on = try JSONSerialization.jsonObject(with: JSONEncoder().encode(EngineRequest(text: "I hat it."))) as? [String: Any]
        XCTAssertEqual(on?["slips"] as? Bool, true)
        let off = try JSONSerialization.jsonObject(with: JSONEncoder().encode(EngineRequest(text: "I hat it.", slips: false))) as? [String: Any]
        XCTAssertEqual(off?["slips"] as? Bool, false)
    }

    /// A classifier that reads every message as passive-aggressive, so the switch alone decides whether a flag shows.
    private struct AlwaysHarsh: ToneScorer {
        func probabilities(ids: [Int32], mask: [Int32]) throws -> [Float] { [0.01, 0.01, 0.96, 0.01, 0.01] }
    }
    func testTheToneSwitchDecidesWhetherAFixCheckShowsAFlag() async throws {
        guard ProcessInfo.processInfo.environment["PARZR_ENGINE_PATH"] != nil else { throw XCTSkip("Supply the built engine library.") }
        let vocab: [String: Int32] = ["[PAD]": 0, "[UNK]": 1, "[CLS]": 2, "[SEP]": 3]
        let classifier = ToneClassifier(tokenizer: try WordPieceTokenizer(vocab: vocab), scorer: AlwaysHarsh(),
                                        config: ToneConfig(labels: ["neutral", "rude", "passive_aggressive", "curt", "over_apologetic"], threshold: 0.9, max_len: 16))
        let previous = Preferences.shared.toneCheck
        defer { Preferences.shared.toneCheck = previous; Task { await ToneChecker.shared.unload() } }
        await ToneChecker.shared.use(classifier)
        func flag(_ on: Bool) async throws -> ToneFlag? {
            Preferences.shared.toneCheck = on
            let model = AppModel(); model.playground("Thanks for finally replying.")
            for _ in 0..<3000 where model.busy || model.result == nil { try await Task.sleep(for: .milliseconds(20)) }
            try await Task.sleep(for: .milliseconds(200))   // the tone check runs just after the Fix result
            return model.toneFlag
        }
        let flagged = try await flag(true)
        XCTAssertEqual(flagged?.category, .passiveAggressive)
        let off = try await flag(false)
        XCTAssertNil(off, "switched off, no flag")
    }

    /// The typing route with the real slip pack (PARZR_SLIP_DIR and PARZR_MODEL_RUNTIME): on, "I hat it" is fixed by the
    /// slip check; off, the app sends `slips: false` and no edit comes from the slip check.
    func testTheSlipSwitchDecidesWhetherTypingUsesTheSlipModel() async throws {
        let environment = ProcessInfo.processInfo.environment
        guard environment["PARZR_ENGINE_PATH"] != nil, !(environment["PARZR_SLIP_DIR"] ?? "").isEmpty, !(environment["PARZR_MODEL_RUNTIME"] ?? "").isEmpty else {
            throw XCTSkip("Needs the engine, the slip pack (PARZR_SLIP_DIR) and the native runtime (PARZR_MODEL_RUNTIME).")
        }
        let (previousSlips, previousGrammar) = (Preferences.shared.slipCheck, Preferences.shared.smartGrammar)
        defer { Preferences.shared.slipCheck = previousSlips; Preferences.shared.smartGrammar = previousGrammar }
        Preferences.shared.smartGrammar = true
        _ = await WritingEngine.warmSlips()
        func slipEdits(_ on: Bool) async throws -> [WritingEdit] {
            Preferences.shared.slipCheck = on
            // A typing check, asked again 900 ms later while the engine answers "context.pending" (as PassiveObserver does).
            var edits: [WritingEdit] = []
            for _ in 0..<4 {
                let model = AppModel(); model.playground("This is so bad. I hat it.", debounce: true)
                for _ in 0..<3000 where model.busy || model.result == nil { try await Task.sleep(for: .milliseconds(20)) }
                edits = model.result?.edits ?? []
                if !(model.result?.warnings?.contains("context.pending") ?? false) { break }
                try await Task.sleep(for: .milliseconds(900))
            }
            return edits.filter { $0.rule_id == "context.slip_swap" }
        }
        let on = try await slipEdits(true)
        XCTAssertEqual(on.map(\.replacement), ["hate"], "the slip check fixes it while typing")
        let off = try await slipEdits(false)
        XCTAssertEqual(off, [], "switched off, the slip model is never asked")
    }
}
