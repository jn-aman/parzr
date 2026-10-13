import Foundation
import ParzrCore

/// `--models-test <dir>`: the model download end to end in the real app. It needs no window, no Accessibility and no focus.
/// Before the download, checks run on the rules and say Smart grammar is not there; then the app downloads the pinned pack
/// (point PARZR_MODELS_DIR at an empty folder, and PARZR_MODELS_BASE_URL at a local copy such as file:///…/dist/model-pack/
/// to test without the release), verifies it and moves it into place; then Smart grammar (GECToR) corrects while typing and
/// Option+Space (the explicit check, and a tone rewrite) runs Qwen. Writes models-test.json and fails on any miss.
@MainActor
func runModelsTest(reportDirectory: String) async throws {
    let directory = URL(fileURLWithPath: reportDirectory)
    try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
    let center = ModelCenter.app
    guard let pack = center.pack, let store = center.store else { throw ParzrError.message("The engine has no model manifest.") }
    var report: [String: Any] = ["root": store.root.path, "pack": "\(pack.id) \(pack.version)", "bytes": pack.bytes, "base_url": store.baseURL?.absoluteString ?? "release"]
    var problems: [String] = []
    func save() throws { try JSONSerialization.data(withJSONObject: report, options: [.prettyPrinted, .sortedKeys]).write(to: directory.appendingPathComponent("models-test.json")) }
    func describe(_ state: ModelPackState) -> String { String(describing: state) }
    let typingText = "She have been working here since two years."
    let toneText = "this plan is dumb, who even approved it??"
    /// One check as the app runs it: typing (rules and Smart grammar) or explicit (Option+Space: deep, and the selected tone).
    func check(_ text: String, mode: RewriteMode = .fix, typing: Bool) async throws -> (RewriteResult, String?) {
        let request = EngineRequest(text: text, mode: mode, deep: !typing, gec: true)
        let result = try await (typing ? WritingEngine.typing : WritingEngine.shared).rewrite(request)
        return (result, AppModel.statusText(result.warnings))
    }
    func edits(_ result: RewriteResult) -> [String] { result.edits.map { "\($0.original)→\($0.replacement) [\($0.rule_id)]" } }

    center.refresh()
    report["state_before"] = describe(center.state)
    if center.state.isReady { problems.append("The models were already installed in \(store.root.path); start from an empty folder.") }
    let (typedBefore, _) = try await check(typingText, typing: true)
    let (explicitBefore, explicitNote) = try await check(typingText, typing: false)
    let (toneBefore, toneNote) = try await check(toneText, mode: .professional, typing: false)
    report["before"] = ["typing": edits(typedBefore), "option_space": edits(explicitBefore), "option_space_note": explicitNote ?? "", "tone": toneBefore.text, "tone_note": toneNote ?? ""]
    if typedBefore.edits.contains(where: { $0.rule_id.hasPrefix("gector") }) { problems.append("Smart grammar ran before its model was downloaded.") }
    if explicitNote?.contains("Smart grammar") != true { problems.append("Option+Space did not say Smart grammar is missing: \(explicitNote ?? "no note")") }
    if toneNote?.hasPrefix("Tone rewrites") != true { problems.append("A tone rewrite did not say it needs the models: \(toneNote ?? "no note")") }

    let started = Date()
    var states: [String] = [], last = ""
    center.start(userInitiated: true)
    while Date().timeIntervalSince(started) < 900 {
        let now = describe(center.state).replacingOccurrences(of: #"\d+"#, with: "#", options: .regularExpression)
        if now != last { states.append(describe(center.state)); last = now }
        if center.state == .ready { break }
        // A failure the app retries on its own (a dropped connection, offline) is waited out; the others end the test.
        if case .failed(let failure) = center.state, !failure.retriesAutomatically { break }
        try await Task.sleep(for: .milliseconds(100))
    }
    report["download_seconds"] = String(format: "%.1f", Date().timeIntervalSince(started))
    report["states"] = states
    report["state_after"] = describe(center.state)
    guard center.state == .ready else { problems.append("The download did not finish: \(describe(center.state))"); report["problems"] = problems; try save(); throw ParzrError.message(problems.joined(separator: "\n")) }
    let folder = store.folder(pack)
    report["installed"] = pack.files.allSatisfy { FileManager.default.fileExists(atPath: folder.appendingPathComponent($0.path).path) }
    report["leftovers"] = (try? FileManager.default.contentsOfDirectory(atPath: folder.deletingLastPathComponent().path)) ?? []
    // Every file on disk matches its pin (the download checked them; this checks what the engine will read).
    report["hashes_match"] = try pack.files.allSatisfy { try ModelStore.sha256(of: folder.appendingPathComponent($0.path)) == $0.sha256 }

    let warmed = Date()
    report["grammar_warm"] = await WritingEngine.warmGrammar()
    report["grammar_warm_seconds"] = String(format: "%.1f", Date().timeIntervalSince(warmed))
    let (typedAfter, _) = try await check(typingText, typing: true)
    let (explicitAfter, explicitAfterNote) = try await check(typingText, typing: false)
    let (toneAfter, toneAfterNote) = try await check(toneText, mode: .professional, typing: false)
    report["after"] = ["typing": edits(typedAfter), "option_space": edits(explicitAfter), "option_space_note": explicitAfterNote ?? "", "tone": toneAfter.text, "tone_note": toneAfterNote ?? ""]
    if report["grammar_warm"] as? Bool != true { problems.append("Smart grammar did not load from the downloaded pack.") }
    if !typedAfter.edits.contains(where: { $0.rule_id.hasPrefix("gector") }) { problems.append("Smart grammar made no correction after the download: \(edits(typedAfter))") }
    if explicitAfterNote?.contains("Smart grammar") == true || explicitAfterNote?.contains("downloaded") == true { problems.append("Option+Space still says the models are missing: \(explicitAfterNote ?? "")") }
    if toneAfterNote?.hasPrefix("Tone rewrites") == true { problems.append("The tone rewrite still says it needs the models.") }
    if toneAfter.text == toneBefore.text { problems.append("The tone rewrite after the download is the rules' text: \(toneAfter.text)") }
    if report["hashes_match"] as? Bool != true { problems.append("An installed file does not match its SHA-256.") }
    report["problems"] = problems
    try save()
    guard problems.isEmpty else { throw ParzrError.message(problems.joined(separator: "\n")) }
}
