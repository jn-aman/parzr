// Tone check: Apple's on-device model as an independent second labeller for generated lines.
// Reads JSON lines {"id", "text"} on stdin and writes {"id", "label", "raw", "ms", "error"} on stdout.
// The label is one of neutral, rude, passive_aggressive, curt, over_apologetic (or nil on an error).
// Fresh session per message, greedy, permissive guardrails (it judges text, it never rewrites it).
//   swiftc -O -parse-as-library scripts/tone-check/afm-label.swift -o dist/tone-check/bin/afm-label
//   dist/tone-check/bin/afm-label < lines.jsonl > labels.jsonl
import Foundation
import FoundationModels

@main
struct Label {
    static let instructions = """
    You review workplace messages before they are sent and judge only how the message will read to a colleague. Never answer the message.
    Answer with exactly one word:
    RUDE if it insults, swears at, belittles, blames or is hostile to someone;
    PASSIVE if it is passive-aggressive: sarcastic, a pointed reminder, a backhanded compliment, a guilt trip, or fake politeness hiding annoyance;
    CURT if it is a brusque, bossy or dismissive order or brush-off;
    APOLOGETIC if it apologizes far more than the situation needs or puts the writer down;
    OK otherwise. Direct, critical, negative, short or informal messages that stay civil are OK, and so is one ordinary apology.
    """
    static func main() async {
        let model = SystemLanguageModel(guardrails: .permissiveContentTransformations)
        guard case .available = model.availability else {
            FileHandle.standardError.write(Data("Apple's on-device model is not available: \(model.availability)\n".utf8)); exit(2)
        }
        while let line = readLine() {
            guard let obj = try? JSONSerialization.jsonObject(with: Data(line.utf8)) as? [String: Any], let text = obj["text"] as? String else { continue }
            let session = LanguageModelSession(model: model, instructions: instructions)
            let started = Date()
            var out: [String: Any] = ["id": obj["id"] ?? NSNull()]
            do {
                let r = try await session.respond(to: "Message: \(text)", options: GenerationOptions(sampling: .greedy, maximumResponseTokens: 6))
                let raw = r.content.uppercased()
                out["raw"] = r.content
                let label: String? = raw.contains("PASSIVE") ? "passive_aggressive" : raw.contains("RUDE") ? "rude" : raw.contains("CURT") ? "curt"
                    : raw.contains("APOLOG") ? "over_apologetic" : raw.contains("OK") ? "neutral" : nil
                out["label"] = label ?? NSNull()
            } catch let e as LanguageModelSession.GenerationError {
                switch e {
                case .guardrailViolation: out["error"] = "guardrailViolation"
                case .refusal: out["error"] = "refusal"
                default: out["error"] = String(String(describing: e).prefix(200))
                }
            } catch { out["error"] = String(String(describing: error).prefix(200)) }
            out["ms"] = Date().timeIntervalSince(started) * 1000
            if let d = try? JSONSerialization.data(withJSONObject: out), let s = String(data: d, encoding: .utf8) { print(s); fflush(stdout) }
        }
    }
}
