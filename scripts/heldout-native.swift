import Foundation

// The held-out benchmark's app path: reads one JSON request per line on stdin ({text, gec, deep, dialect,
// capitalize_names}) and answers with ParzrCore's WritingEngine result, so Apple NaturalLanguage hints are added
// as in the app. capitalize_names defaults to true, the app's "Everywhere" default. Build:
//   swiftc -O -parse-as-library mac/Sources/ParzrCore/Models.swift mac/Sources/ParzrCore/WritingEngine.swift \
//     scripts/heldout-native.swift -o dist/qa/heldout-native
// and run it with PARZR_ENGINE_PATH (libparzr_engine.dylib), PARZR_MODEL_RUNTIME and PARZR_MODEL_PATH set.
@main
struct HeldoutNative {
    static func main() async throws {
        while let line = readLine(strippingNewline: true) {
            guard let object = try JSONSerialization.jsonObject(with: Data(line.utf8)) as? [String: Any], let text = object["text"] as? String else { continue }
            let request = EngineRequest(text: text, capitalizeNames: object["capitalize_names"] as? Bool ?? true, dialect: object["dialect"] as? String ?? "american", deep: object["deep"] as? Bool ?? false, gec: object["gec"] as? Bool ?? false)
            var out = Data("{\"error\":\"failed\"}".utf8)
            if let result = try? await WritingEngine.shared.rewrite(request) { out = try JSONEncoder().encode(result) }
            FileHandle.standardOutput.write(out + Data("\n".utf8))
        }
    }
}
