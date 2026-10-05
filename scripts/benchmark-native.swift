import Foundation

// Compiled alongside the application's unchanged ParzrCore sources. Uses the
// packaged Rust library and the same Apple NaturalLanguage enrichment as the UI.
@main
struct NativeBenchmark {
    static func main() async throws {
        guard CommandLine.arguments.count == 2 else {
            throw ParzrError.message("Usage: native-benchmark corpus.jsonl")
        }
        let input = try String(contentsOfFile: CommandLine.arguments[1], encoding: .utf8)
        for line in input.split(separator: "\n") {
            let data = Data(line.utf8)
            guard let fixture = try JSONSerialization.jsonObject(with: data) as? [String: Any],
                  let id = fixture["id"] as? String, let text = fixture["input"] as? String else {
                throw ParzrError.message("Invalid benchmark fixture.")
            }
            let start = ContinuousClock.now
            var record: [String: Any] = ["id": id]
            do {
                let result = try await WritingEngine.shared.rewrite(EngineRequest(text: text))
                record["result"] = try JSONSerialization.jsonObject(with: JSONEncoder().encode(result))
            } catch {
                record["error"] = error.localizedDescription
            }
            let duration = start.duration(to: .now).components
            record["wall_ms"] = Double(duration.seconds) * 1000 + Double(duration.attoseconds) / 1e15
            let encoded = try JSONSerialization.data(withJSONObject: record, options: [.sortedKeys])
            print(String(decoding: encoded, as: UTF8.self))
        }
    }
}
