# Parzr for iPhone and iPad

Phase 5 of the roadmap. This folder has three parts:

- **Parzr** (`Sources/App`), the containing app:
  - onboarding that walks through turning on the keyboard and Full Access;
  - settings shared with the keyboard (dialect, personal dictionary, names, rewrites inside the keyboard);
  - a scratchpad that checks text with the Rust engine and rewrites it with Apple Foundation Models.
- **ParzrKeyboard** (`Sources/Keyboard`), a custom keyboard extension. It is a plain QWERTY layout with a suggestion bar. The bar checks the sentence being typed and applies fixes through `textDocumentProxy`, and it offers tone rewrites.
- **ParzrKit** (`Sources/ParzrKit`), a framework both of them link. It holds the Rust engine bridge, sentence extraction, proxy edit planning, suggestions, the App Group store and the Foundation Models rewriter. It also compiles `mac/Sources/ParzrCore/Models.swift` and `LinguisticHints.swift`, so the request and result types and the NaturalLanguage hints are the same code as on the Mac.

## Build

You need Xcode 26 or later with an iOS 26+ SDK (tested with Xcode 27.1 and the iOS 27.1 SDK), `xcodegen`, and rustup with the iOS targets. No signing identity is needed.

```sh
rustup target add aarch64-apple-ios aarch64-apple-ios-sim   # once
ios/scripts/build.sh          # engine XCFramework, xcodegen, unsigned simulator build
ios/scripts/build.sh test     # the same, then ParzrKitTests on an iPhone simulator
```

- `ios/scripts/build-engine-xcframework.sh` builds `engine/` with `--no-default-features` (rules only, without the native model runtime), as a static library for `aarch64-apple-ios` and `aarch64-apple-ios-sim`. It wraps both in `ios/Engine/ParzrEngine.xcframework` with the C header and module map from `ios/Engine/include`.
- The Swift side imports the engine as `ParzrEngineFFI` and calls `parzr_rewrite_json`, `parzr_tone_guard_json`, `parzr_string_free` and `parzr_is_known_misspelling` directly. This is the same FFI the Mac app reaches through `dlopen`.
- The archives are not stripped. An earlier `strip -S -x` on the static archive broke relocations: the engine crashed with SIGSEGV inside `contractions::check` on the simulator.
- The simulator build is Apple-silicon only (`EXCLUDED_ARCHS = x86_64`).
- Both scripts run under `nice` with 2 jobs (`PARZR_JOBS` overrides this). `build.sh test` shuts its simulator down afterwards.
- `Parzr.xcodeproj`, the XCFramework and `ios/build/` are generated and ignored by git.

Bundle IDs are `app.parzr.ios`, `app.parzr.ios.keyboard` and the App Group `group.app.parzr.ios`. A device build needs a team that owns these IDs and the App Group capability.

## Engine changes for iOS

- **`parzr_tone_guard_json`.** A new FFI entry that runs the engine's tone meaning guard (`meaning::keeps_meaning` plus preamble stripping) on a rewrite written outside the engine. Apple Foundation Models output passes the same check as the Mac's own tone rewrites: names, numbers, negation and content words are kept, and replies and refusals are rejected.
- **`meaning` builds without `local-model`.** Before, the meaning module was compiled only with the local model. It now builds in the rules-only configuration too, and `distance` moved from `model.rs` to `meaning.rs`.
- **Checks.** `cargo fmt --check`, `clippy -D warnings` (both feature sets) and `cargo test` (both feature sets) pass.

## Memory: the engine does not fit a keyboard today

Peak memory footprint of the rules-only engine for one request, measured on macOS (`/usr/bin/time -l`, release build):

| Request | Peak footprint |
|---|---|
| empty text | 20 MB |
| "Hello." (loads the lexicon and rules) | 108 MB |
| "i recieved teh report" (also spelling candidates, word pairs) | 137 MB |
| the same, without the SymSpell deletes index (experiment) | 75 MB |
| the same, without the deletes index and the word-pair table | 57 MB |

A keyboard extension is ended by the system at roughly 60–70 MB (est.; Apple does not publish the limit, and it varies by device). So:

- The keyboard calls `MemoryBudget.engineFits()`, which reads `os_proc_available_memory()`, before loading the engine. It needs 160 MB of headroom.
- On a device, the keyboard falls back to `SystemSpelling`, the UITextChecker corrections expressed as engine edits. The same bar and the same apply path work with either checker.
- The simulator sets no memory limit, so the engine runs in the keyboard there.
- The keyboard writes which checker it used, and its headroom, to the App Group. The app's Keyboard tab shows it.

**Fix (next step):** build the lexicon's deletes index (about 62 MB) and the word-pair table (about 18 MB) at build time, as sorted static arrays read in place from the binary. They are `HashMap<String, …>` values built at first use today. That should bring the engine under about 30 MB with identical lookups. Then the full engine, and the meaning guard that in-keyboard rewrites need, can run in the keyboard.

## Apple Foundation Models

`ToneRewriter` follows `dist/model-bakeoff2/README.md`:

- **Prompt.** The model gets the real words. Parzr's `ZXQPARZRKEEP` placeholders, which caused most guardrail errors in the bake-off, are never sent. The instructions mirror the engine's tone prompts.
- **Guardrails and sampling.** It uses `SystemLanguageModel(guardrails: .permissiveContentTransformations)` with greedy sampling.
- **Deadline.** `withTimeout` returns at the deadline even when the call ignores cancellation. The bake-off saw stalls of 20–77 s. The deadline is 3 s in the keyboard and 8 s for a handoff in the app, where a cold start can take 2–3 s. The app prewarms the model when it becomes active.
- **Pipeline.** The text is first corrected by the rules. The model's answer then goes through `parzr_tone_guard_json`, which drops preambles, replies, refusals and changed facts, and the rules correct the result once more.
- **Unavailability.** `AppleModelStatus` turns the cases (device not eligible, Apple Intelligence off, model not ready, unsupported language) into plain messages. Grammar and spelling keep working without the model.

### Can a keyboard extension use FoundationModels?

What was measured (2026-10-19, iPhone 17 Pro simulator, iOS 26.5 runtime, on an M5 Mac with Apple Intelligence on, under a load average of 80–270):

- **The containing app.** `-parzr-selftest` ran the following in the app process:
  - **Engine.** "i recieved teh report yesterday" became "I received the report yesterday" (3 edits; 1.6 s on the first call, which builds the tables).
  - **Model status.** `SystemLanguageModel` reported available.
  - **`ToneRewriter.probe()`.** The probe answered in 1.8 s.
  - **Professional, "this is a dumb idea and you know it".** The meaning guard withheld the answer.
  - **Friendly, "send me the report by friday".** "Please send me the report by Friday." (0.65 s)
- **The keyboard.**
  - I enabled it in the simulator by adding `app.parzr.ios.keyboard` to `AppleKeyboards` and launched the app with `-parzr-focus`.
  - No keyboard log lines appeared in a headless simulator, so the in-extension probe is still untested.
  - I stopped there to keep the machine's load down. Running the keyboard in Simulator.app or on a device and reading `log stream --predicate 'subsystem == "app.parzr.ios"'` gives the answer.

What is known:

- **It compiles and links.** The iOS 27.1 SDK's FoundationModels interface has no `@available(iOSApplicationExtension, unavailable)` marks. ParzrKit is built with `APPLICATION_EXTENSION_API_ONLY = YES`, and the keyboard links it without warnings.
- **Memory is not the problem for the model itself.** Inference runs out of process, in `TGOnDeviceInferenceProviderService` (bake-off 2 measured about 335 MB there and nothing in the caller). A session costs the keyboard little.
- **The open question is the keyboard sandbox at run time.**
  - Without Full Access, a keyboard cannot use the network or write a shared container. Whether it may open the XPC connection to the model service is not documented.
  - Foundation Models is rate-limited for apps in the background. A keyboard runs inside another app's foreground session.
  - Neither can be settled in the simulator, which applies neither the device sandbox nor the memory limit.
- **The meaning guard is the binding constraint today.** A rewrite must not reach the text field unchecked, and the guard needs the engine's lexicon, which does not fit (see Memory above).

So the design does not depend on the answer:

1. **Probe at run time.** With Full Access, the keyboard makes one short `ToneRewriter.probe()` call per launch (3 s deadline). It records "works (N ms)" or the exact error in the App Group, and the app's Keyboard tab shows it. Running it on a real iPhone answers the question.
2. **Rewrite in the keyboard** only when the engine fits *and* Apple Intelligence answers there. That is the simulator today, and devices once the engine's memory is reduced.
3. **Otherwise, hand off through the App Group.**
   - The keyboard stores the sentence and tone (`SharedStore.post`) and says "Open Parzr to write a Professional version".
   - When the app is next active, it writes the rewrite with the full engine and AFM (`AppModel.answerHandoff`) and stores the result or the reason there is none.
   - When the keyboard appears again, it checks that the text before the cursor still ends with that sentence and offers "Use Professional version".
   - One slot, latest request wins, and handoffs expire after 15 minutes.
   - The keyboard does not open the app itself. Extensions have no public API for that, and the responder-chain workaround is not used.

## Applying fixes through `textDocumentProxy`

- **What is checked.** `SentenceContext` takes the last two sentences of `documentContextBeforeInput`, from the current paragraph only. It leaves out the word still being typed and flags whether the span ends a sentence.
- **How a fix is applied.** `ProxyEdit.plan` turns engine edits (UTF-16 offsets) into a number of `deleteBackward()` calls and one `insertText`. It deletes back to the first changed character, on a grapheme boundary, and retypes the corrected text plus anything typed since the check.
- **When it refuses.** It returns nil when the checked text is no longer before the cursor, more than 80 characters were typed since, or a new paragraph started.
- **Rewrites.** A tone rewrite replaces the whole span the same way.
- **Assumption.** One `deleteBackward()` removes one grapheme cluster. This holds for the system text views tested by other keyboards, but check it on a device in a web view.

## Tests

`Tests/ParzrKitTests` run on an iPhone simulator. They cover:

- sentence extraction;
- proxy edit plans, including emoji and stale text;
- suggestion grouping;
- the App Group handoff and settings;
- the real engine (a fix, and the meaning guard on an outside rewrite);
- the memory gate;
- the prompts (no placeholders);
- the deadline returning even when the work ignores cancellation.

## Next steps

1. **Compact the engine's tables** (see Memory) so that the engine and the meaning guard run in the keyboard. Measure with `os_proc_available_memory` on the oldest supported iPhone.
2. **Run the keyboard on a device with Full Access** and read the Apple Intelligence probe result in the Keyboard tab. If it works, in-keyboard rewrites only wait on step 1.
3. **Keyboard polish:**
   - long-press accents;
   - double-space period;
   - autocorrect on space using the engine's high-confidence spelling edits;
   - haptics and key previews;
   - iPad layouts;
   - dark-mode key colours.
4. **iOS 27's `LanguageModel` protocol.** It lets the same `LanguageModelSession` code drive Parzr's own model. That is the route to the 2B rewriter on iPhone if AFM's tone quality stays behind (bake-off 2: 22% vs 36% good).
5. **A held-out iOS benchmark run.** Run `run-heldout-benchmark.py` against the rules-only engine with NaturalLanguage hints from iOS, so iPhone quality is measured before release.
6. **Ship:** an App Store Connect record, a team for the bundle IDs and App Group, and a Release workflow job for an archive (`xcodebuild archive`) using CI signing.
