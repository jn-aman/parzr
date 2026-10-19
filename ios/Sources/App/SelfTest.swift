import Foundation
import ParzrKit

/// `-parzr-selftest` launch argument: checks the engine, Apple Intelligence and a full tone
/// rewrite in this process, prints the results, and exits. For the simulator and devices:
/// `xcrun simctl launch --console-pty booted app.parzr.ios -parzr-selftest`.
enum SelfTest {
    static var requested: Bool { ProcessInfo.processInfo.arguments.contains("-parzr-selftest") }

    @MainActor
    static func run() async {
        let log = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0].appendingPathComponent("selftest.txt")
        try? Data().write(to: log)
        func line(_ text: String) {
            print("parzr-selftest: \(text)"); fflush(stdout)
            if let handle = try? FileHandle(forWritingTo: log) { handle.seekToEndOfFile(); handle.write(Data((text + "\n").utf8)); try? handle.close() }
        }
        line("start")
        let engine = ParzrEngine.shared
        engine.setKnownWords { SystemSpelling.knownWordsFromAnyThread(in: $0) }
        let clock = ContinuousClock()
        var start = clock.now
        let sample = "i recieved teh report yesterday"
        if let json = try? JSONEncoder().encode(EngineRequest(text: sample, tokens: LinguisticHints.hints(for: sample))) {
            line("request \(String(decoding: json, as: UTF8.self))")
        }
        do {
            let result = try await engine.check(EngineRequest(text: "i recieved teh report yesterday"))
            line("engine \(result.text) (\(result.edits.count) edits, \(clock.now - start))")
        } catch { line("engine failed: \(error.localizedDescription)") }
        line("apple model: \(AppleModelStatus.current.message)")
        line("probe: \(await ToneRewriter.probe(timeout: .seconds(10)))")
        for (mode, text) in [(RewriteMode.professional, "this is a dumb idea and you know it"), (.friendly, "send me the report by friday"), (.concise, "I just wanted to quickly check in to see if you might have had a chance to look at the document")] {
            start = clock.now
            let outcome = await ToneRewriter(timeout: .seconds(10)).rewrite(text, mode: mode)
            line("\(mode.rawValue): \(outcome) (\(clock.now - start))")
        }
        line("done")
        exit(0)
    }
}
