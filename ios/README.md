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
- Both scripts run under `nice -n 15` with 2 jobs (`PARZR_JOBS` overrides this). `build.sh test` shuts its simulator down afterwards.
- `Parzr.xcodeproj`, the XCFramework and `ios/build/` are generated and ignored by git.

Bundle IDs are `app.parzr.ios`, `app.parzr.ios.keyboard` and the App Group `group.app.parzr.ios`. A device build needs a team that owns these IDs and the App Group capability.

## Engine changes for iOS

- **`parzr_tone_guard_json`.** A new FFI entry that runs the engine's tone meaning guard (`meaning::keeps_meaning` plus preamble stripping) on a rewrite written outside the engine. Apple Foundation Models output passes the same check as the Mac's own tone rewrites: names, numbers, negation and content words are kept, and replies and refusals are rejected.
- **`meaning` builds without `local-model`.** Before, the meaning module was compiled only with the local model. It now builds in the rules-only configuration too, and `distance` moved from `model.rs` to `meaning.rs`.
- **Checks.** `cargo fmt --check`, `clippy -D warnings` (both feature sets) and `cargo test` (both feature sets) pass.

## Memory: the engine fits a keyboard

A keyboard extension is ended by the system at roughly 60–70 MB (est.; Apple does not publish the limit, and it varies by device).

**Before (v0.5.0).** The engine built its spelling tables as `HashMap<String, …>` values from JSON at first use. One request peaked at 108 MB ("Hello.") to 137 MB ("i recieved teh report"). The SymSpell deletes index alone was about 62 MB and the word-pair table about 18 MB.

**Now.** Three changes, all with identical lookups:

- **Tables compiled at build time.** `engine/build.rs` turns `rules/lexicon.json`, `frequency.json` and `bigrams.json` into read-only hash tables: the lexicon with flags and canonical casing, the deletes index, frequencies and word pairs (format in `engine/src/table.rs`). They are embedded with `include_bytes!` and read in place, so their pages stay clean and shared, and there is no JSON parsing at run time.
- **Bounded set of compiled rule patterns.** At most 48 rule patterns stay compiled (`rules::COMPILED_PATTERNS_KEPT`, least recently used dropped). A compiled pattern is about 70–100 KB, and a long, varied session used to compile all of them (about 20 MB).
- **Bounded lazy-DFA cache.** Each rule pattern's cache is held to 16 KB (`REGEX_CACHE_BYTES`; the regex crate's default is 2 MB).

Peak footprint, macOS, release build, rules only (`/usr/bin/time -l`):

| Workload | v0.5.0 | Now |
| --- | --- | --- |
| one short request, fresh process ("i recieved teh report") | 136 MB | 21.7 MB |
| each of the 1,643 held-out DEV error items alone, fresh process | (over 100 MB) | median 19.5, p95 21.5, max 24.0 MB |
| 9,278 paragraphs in one process (English 1000 + 2000 with clean controls, typo-fuzz and held-out DEV samples), with NaturalLanguage hints | 166–174 MB | 29.3–30.6 MB |
| 18,004 one- and two-sentence windows in one process (what the keyboard sends) | 166 MB | 30.0 MB |

- **Outputs are identical.** Base and new engines were compared request by request, ignoring only `elapsed_ms`:

  | Build | Requests | Requests that differ |
  | --- | --- | --- |
  | rules-only, with NaturalLanguage hints | 9,278 | 0 |
  | rules-only, without hints | 9,278 | 0 |
  | rules-only, sentence windows | 18,004 | 0 |
  | default features (local model), with hints | 9,278 | 0 |
  | `external-tables` (the Mac bundle's configuration), rules-only, with and without hints | 9,278 each | 0 |
  | `external-tables`, default features, with hints | 9,278 | 0 |
  | `external-tables`, sentence windows, rules-only and default features | 18,004 each | 0 |

  The external build's memory matches the embedded build on the sentence windows: 31.3–32.1 MB against 32.0–32.1 MB, run to run. It takes +0.2% instructions, which is the one-time hash check of the file.

  The 9,278 requests are English 1000/2000 and their clean controls, 500 British-dialect paragraphs, a fifth of the typo-fuzz DEV set with its clean set, and the held-out DEV split by the runner's hash rule. The held-out test split was never used.
- **Lookups are tested exhaustively.** `spelling::compiled_tables` checks every word, deletion key, frequency and pair against maps rebuilt from the JSON.
- **Speed and size.**
  - Instructions retired: 105.5 G against 103.8 G on the 9,278 requests (+1.7%), and 152.0 G against 149.5 G on the sentence windows (+1.7%).
  - A cold first request takes about a third of the time: 0.10 s against 0.31 s at low load, and 0.30 s against 0.81 s under load.
  - **Binary size.**
    - Embedded, the hashed tables make each binary about 16 MB larger than the JSON did (11.1 MB compressed against 4.4 MB). iOS keeps the embedded copy: the app and keyboard share it through ParzrKit.
    - The Mac app has four engine binaries (`libparzr_engine.dylib`, `parzr-engine`, `parzr-native-host`, `parzr-lsp`), so it builds with the `external-tables` feature and ships the tables once, as `Contents/Resources/parzr-tables.dat`. Every binary maps that file read-only, and so does the dylib inside the app, which finds it through `dladdr`.
    - Each binary has the file's length and hash compiled in. A missing or mismatched file fails every request with a message naming the path and "Reinstall Parzr", and the engine never runs on other tables. `PARZR_TABLES_PATH` overrides the location.
    - `scripts/build.py` copies the file in and checks that the staged engine accepts it. `scripts/audit-bundle.py` requires the file, rejects an engine binary over 12 MB (one that embeds the tables), and runs the bundled engine against it.
  - **Mac app size, local ad-hoc build of this branch** (`build.py --skip-build` after its own cargo and swift commands; not launched) **against the v0.5.1 release:**

    | | v0.5.1 release | This branch |
    | --- | --- | --- |
    | zip (`ditto -c -k`) | 28.99 MB | 27.41 MB (−1.58 MB, −5.5%) |
    | uncompressed bundle | 84.9 MB | 72.4 MB |
    | engine files, deflated | 19.8 MB (4 binaries of 15.5 MB) | 18.3 MB (4 binaries of 5.9 MB and the 26.5 MB tables file) |
    | everything else, deflated | 9.1 MB | 9.0 MB |

    With the tables embedded in all four binaries, the engine files would have come to about 44 MB compressed.
- **In the keyboard.**
  - `MemoryBudget.engineMB` is now 40 MB of headroom, so the keyboard runs the full engine and the meaning guard, and falls back to `SystemSpelling` (UITextChecker) only when headroom is below that.
  - The simulator sets no memory limit, so the engine always runs there.
  - The keyboard writes which checker it used, and its headroom, to the App Group. The app's Keyboard tab shows it.

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
- **The meaning guard needed the engine's lexicon,** which did not fit until the tables were compiled (see Memory above). It now fits: a rewrite in the keyboard can be checked there.

So the design does not depend on the answer:

1. **Probe at run time.** The keyboard makes one short on-device `ToneRewriter.probe()` call at most once a day (3 s deadline) and logs it. It records "works (N ms)" or the exact error in the App Group, and the app's Keyboard tab shows it. Running it on a real iPhone answers the question.
2. **Rewrite in the keyboard** only when the engine fits *and* Apple Intelligence answers there.
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

1. **Run the keyboard on a device with Full Access.** Read the Apple Intelligence probe result and the memory headroom in the Keyboard tab, on the oldest supported iPhone.
2. **Shrink the tables file.** It is 26.5 MB (9.7 MB compressed). Dropping the per-entry key length (it follows from the next entry's offset) would save about 3 MB.
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
