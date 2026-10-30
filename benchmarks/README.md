# English challenge sets

Two authored sets share the same 20 grammar families and ten error combinations: the 1,000-paragraph development challenge and a 2,000-paragraph topic generalization set. Both use the same runner and the same measurement rules.

## Development challenge (1,000 paragraphs)

100 independently authored base paragraphs across 20 grammar families and five lexical contexts, each with ten error combinations: **1,000 distinct corrupted paragraphs**, plus **100 clean controls**. There are 4,400 annotated error spans. Each corrupted paragraph has a reference correction and reversible UTF-16 edits.

The combinations include grammar, spelling, missing sentence punctuation, short-word typos, joined words, and mixtures of these errors. Grammar templates are independent of the checker's implemented rules. Spelling mutations are rejected when they produce a known word in the current lexicon; this selection step uses the project's lexicon.

This authored synthetic dataset tests specific structures. Repeated templates across lexical contexts are not independent observations of general English usage. Single reference corrections are not exhaustive: dialect, style and valid alternative corrections require human review. Exact-match rate is not a general grammar accuracy score.

This is a development challenge, not a held-out evaluation. Its failures were used to improve the checker. The corpus includes a corrected article in two base references; before/after comparisons must use the same corpus and clean-control hashes.

Generate and run against a built app:

```sh
python3 scripts/generate-english-benchmark.py
python3 scripts/run-english-benchmark.py
```

## Topic generalization set (2,000 paragraphs)

`english-2000.jsonl` holds **2,000 distinct corrupted paragraphs** from 200 fresh base paragraphs (the same 20 grammar families times 10 new topics, each with the ten error combinations), plus **200 clean controls** in `english-200-clean.jsonl`, with 8,800 annotated error spans. The topics supply new names, settings and vocabulary (a charity concert, a station repair, a harbor festival and so on). No corrupted paragraph repeats an input of the 1,000 set, and `english-2000-manifest.json` records the seed, counts, SHA-256 hashes of both files, the hash of the 1,000 corpus it avoids, and its scope.

It tests topic and lexical generalization of the same authored grammar structures. It does not add new grammar structures and is not natural-language English accuracy. Like the 1,000 set it is a regression check: the generator never changes a committed corpus (it refuses to run when the files exist), so the corpus is frozen for reproducible comparison. Its generator, `scripts/generate-english-generalization.py`, also needs the 1,000-set milestone summary (`dist/qa/english-1000-milestone/summary.json`, 100% exact and clean) to prove the development set was passing before the fresh set was drawn.

Run it with the corpus and controls flags, ideally to its own output folder:

```sh
python3 scripts/run-english-benchmark.py --output dist/qa/english-2000 \
  --corpus benchmarks/english-2000.jsonl --controls benchmarks/english-200-clean.jsonl
```

Both sets are expected to show exact corrections on every corrupted paragraph and no change to any clean control; a regression on either is a reason to revisit the rule that caused it, never to edit the corpus. `--require-exact` makes the runner exit 1 otherwise; CI's verify job runs both sets that way on the Rust engine and the app's NaturalLanguage path (`--engine`/`--library` point it at a development build instead of a packaged app, `--paths` picks the paths).

The runner measures the packaged Rust executable and a native harness compiled with the application's unchanged `WritingEngine` and model sources. The harness loads the packaged Rust library and uses the same Apple NaturalLanguage enrichment. It does not open the app, read personal writing, or exercise editor UI. Both paths use Fix mode, American English, an empty personal dictionary and no manually protected ranges.

Results are written under ignored `dist/qa/english-1000/` (or the folder given by `--output`): a searchable offline HTML report, CSV and JSONL with every input/reference/actual output, readable text files, summaries by grammar family and combination, and a ZIP containing the corpus and results. Returned edit plans are checked for UTF-16 validity, nonoverlap, original-span agreement and reconstruction of the returned text. Artifact and source hashes identify the measured checker. Runtime timings include initialization in the first case; later cases run in the same process.

The runner reports exact reference matches, nonexact changes needing review, unchanged erroneous inputs, execution errors, and changes to clean controls. It never counts every change as a successful correction. Generated reports belong to the particular measured build; changing rules requires a new run.

## Everyday errors (held-out set)

`heldout/errors.jsonl` holds **2,329** realistic messages with errors (chat, email, docs, social, technical) across 14 categories: real-word slips, spelling, agreement, verb forms, articles, prepositions, word choice, missing or extra words, word order, punctuation, capitalization, run-ons and fragments, contractions, and mixed messages with two errors. `heldout/clean.jsonl` holds **905** correct sentences, many of them deliberately tricky ("working out fine", "sold out, fine by me", effect as a verb, en-GB spellings, code identifiers, names), to measure false alarms. `heldout/TAXONOMY.md` defines every category and how items were written; the sources are `heldout/src/*.txt`, rebuilt with `heldout/src/build.py`.

The set was written by hand without reading the checker's rules, lexicons or the sets above. Unlike them it is split: a fixed 30% of items, chosen by a hash of the input text, is the **test** split and is never used for fixing. The other 70% is **dev**: rules are improved by looking at dev misses only, and the test split is only scored. The gap between the two numbers shows how much a change generalizes.

Score it through the app's own path (ParzrCore's `WritingEngine` with Apple NaturalLanguage hints and the default name capitalization):

```sh
swiftc -O -parse-as-library mac/Sources/ParzrCore/Models.swift mac/Sources/ParzrCore/WritingEngine.swift mac/Sources/ParzrCore/LinguisticHints.swift \
  scripts/heldout-native.swift -o dist/qa/heldout-native
PARZR_ENGINE_PATH=$PWD/engine/target/release/libparzr_engine.dylib \
PARZR_MODEL_RUNTIME=$PWD/dist/model/libparzr_model.dylib PARZR_MODELS_DIR=$PWD/dist/models \
  python3 scripts/run-heldout-benchmark.py --engine dist/qa/heldout-native --split dev --layers rules,gec,deep
```

Layers: `rules` (rules only), `gec` (rules and Smart grammar, what runs while typing) and `deep` (Option+Space: rules, Smart grammar and the language model). The models come from `python3 scripts/model-pack.py fetch` (into `dist/models`). Each error item is **fixed** (output equals the reference or an accepted alternative), **flagged** (every error span is touched), **wrong** or **missed**; a clean item that changes is a **false alarm**. Results go to `dist/qa/heldout/` (summary.md, per-item JSONL and false alarms).

Test split, v0.3.6 against the build that added this set:

| Layer | v0.3.6 fixed / caught / false alarms | Now |
|---|---|---|
| While typing (`gec`) | 44.5% / 52.6% / 1.7% | 64.3% / 69.5% / 1.1% |
| Option+Space (`deep`) | 59.2% / 68.4% / 4.2% | 74.5% / 80.9% / 3.5% |

The `gec` layer is scored with checks back to back, so the language-model swap check, which while typing runs in the background and lands on the next check, barely shows there; `deep` shows it (real-word slips 26% to 68% fixed). CI's verify job scores the test split for `rules` and `gec` and fails below the fix rates or above the false-alarm rates in `.github/workflows/ci-release.yml`, and against the committed baseline (see "Quality gates" below); raise those gates when a change lifts the test score, never lower them to let a regression through.

The test split is sealed: `run-heldout-benchmark.py --split test` (and the typo-fuzz `test*.jsonl` corpus) refuses to run unless `CI=true` or `PARZR_RELEASE_GATE=1`, and then writes only totals and category counts (`summary.json`, `summary.md`), never an item's input or output. Work from `--split dev`.

`scripts/run-public-gec-benchmark.py` compares the same layers with LanguageTool on CoNLL-2014, JFLEG and the GitHub Typo Corpus (downloaded into ignored `dist/gec-data/`; ERRANT and GLEU scoring). See the script's header for setup.

## Tone regression set

`tone/regression.jsonl` holds **310** sentences and short messages written for it (chat, email, requests, questions, negations, numbers and dates, names and addresses, polite, rude and hedged text, lists, multi-sentence messages, conditions, greetings and sign-offs; 20 to 25 items of each kind). It scores the tone modes (Professional, Friendly, Concise, Direct) the way the held-out set scores Fix mode: a change to the model, the meaning guard (`keeps_meaning` in `engine/src/meaning.rs`) or a mode's wording rules (the packs' `modes` field) moves a pass rate in CI. `tone/tone-eval.jsonl` and its labels stay the broader, hand-read measure of meaning and tone; this set is the cheap, automatic one.

Each line: `{"id", "kind", "text", "casual", "modes": {"professional": SPEC, "friendly": SPEC, "concise": SPEC, "direct": SPEC}}` with `SPEC = {"expect": "rewrite" | "keep" | "any", "keep_words": [...], "forbid": [...regexes...]}`.

- `rewrite`: the output must differ from the input and the response must carry no `tone.withheld` warning. Used only for clear cases: chat-speak into Professional, a rude message into Friendly, a wordy or hedged message into Concise or Direct.
- `keep`: the output equals the input (trailing whitespace ignored). Used where any rewrite is wrong, because the text is already in that tone.
- `any`: only the invariants below are scored.
- `keep_words`: every entry appears in the output (case-insensitive, whole word; `"a|b"` accepts either), for the "if" of a condition, a list item, a greeting or sign-off, a name at the start of a sentence.
- `forbid`: no regex matches the output. Most items carry four: an added commitment ("I will", "we'll", "I promise"), an invented time or urgency ("tomorrow", "ASAP"), "we" or "our" where the writer said "I", and a closing "?" on a statement; each is left out where the input already has it.
- `casual: true` sends the item as the app does for chat apps (Friendly may then end a short message with one emoji).

Invariants scored for every item in every mode, without being listed: a response `error`; every number, time, date, URL, email and @handle of the input stays (a number written out up to 100, "3" as "three", is kept; times compare as h:mm am/pm); every question word of an input question stays and an output question asks no word the input lacked; an input that ends in "?" still does (Direct may turn a request into an instruction); negation (not, n't, never, no, cannot, unable) is present in both texts or in neither; capitalized names not at the start of a sentence stay; Concise output has no more words than the input and at most 3 more characters; no stray ",." or ";,"; no emoji is added (except Friendly's one final emoji on a chat message); Professional output has none of u, ur, thx, lol, pls, plz, gonna, wanna, gotta, ya, omg, idk, tmrw, brb, haha, cuz. A `tone.withheld` warning (the guard refused a rewrite) passes `keep` and `any` and fails `rewrite`.

```sh
cargo build --release --manifest-path engine/Cargo.toml --bin parzr-engine
PARZR_MODEL_RUNTIME=$PWD/dist/model/libparzr_model.dylib PARZR_MODELS_DIR=$PWD/dist/models \
  python3 scripts/run-tone-regression.py --engine engine/target/release/parzr-engine [--modes friendly] [--baseline tone-regression]
```

Every item runs in every mode against one warmed engine (about 11 minutes for 310 items on an M-series Mac, 0.5 s a request; a runner without the GPU needs several seconds a request, so CI's own `tone` job, parallel to `verify`, scores `--every 6`, every sixth item, 52 of 310, in about 30 minutes, against the sample baseline kept under `samples` in `baselines.json`). `dist/qa/tone-regression/` gets `results.jsonl` (per item and mode: output, verdict, failed checks, elapsed_ms), `summary.json` and `summary.md` (per mode: items, passed, pass rate, failures by check and by kind, p50/p95 latency, peak memory). `--answers results.jsonl` re-scores an earlier run without the engine, to check a changed check or expectation. `--every N` scores every Nth item. `--min-pass-rate MODE=RATE` fails a mode below a rate; `--baseline tone-regression` compares each mode with `baselines.json` (see "Quality gates"). The set is frozen like the others (`frozen.json`): a failing item is a finding for the engine, and an expectation is only changed when it was wrong, as a deliberate new version with updated pins and baseline. After a change, record the new numbers with `python3 scripts/update-baselines.py tone-regression dist/qa/tone-regression/summary.json --reason "..."` (a full run, or a sample run from the `tone-summaries` artifact of CI's `tone` job). The pass rates are well under 100% on purpose: each failure the set finds is a queued fix (a rewrite the guard let through, a good rewrite it withheld, a mode wording rule, chat-speak left in).

## Tone check development sets

`tone-check/dev.jsonl` (1,330 messages) and `tone-check/dev2.jsonl` (195) measure the optional tone check (`scripts/tone-check`), which flags a message as rude, passive-aggressive, curt or over-apologetic. Each item has `label` (`neutral` or one of those four) and `hard` (a civil message a naive classifier tends to flag).

- **dev.jsonl:**
  - lines written for it in settings the training seeds do not use (`scripts/tone-check/dev_written.txt`);
  - bake-off 2's workplace probe and tone-set labels;
  - everyday batch-002 texts written for Parzr (Enron lines excluded).

  It chose the shipped threshold, and its error classes shaped the second training round, so it is a development set.
- **dev2.jsonl** (`tone-check/dev2_written.txt`) was written before the second round trained and scored once at the end.

Training removes every text of both sets. Results: dist/tone-check/README.md.

## Everyday regression set

`everyday/items.jsonl` holds 2,870 short real-world texts (chat, email, notes, commit messages, status updates, non-native English, passages; some Enron AESLC lines, a public corpus) whose expected output is certain: the certain items of the everyday batches 1 to 3, with the outputs a reader accepted as `accept` alternatives. Texts with the owner's name and Enron lines with e-mail addresses or phone numbers were left out. Expectations follow the always-capitalize policy: a sentence starts with a capital in chat too (`flex: "stop"`: only a final full stop and the case of ok/OK are optional). Items whose first word is chat shorthand, a command, a handle or a brand ("lol", "fyi", "sudo apt", "eBay") keep that word's case, with the capitalized form also accepted.

```sh
python3 scripts/everyday-batch.py gate --native dist/qa/heldout-native [--paths typing,deep] [--deep-sample N]
```

scores the typing path (Smart grammar; while the engine answers `context.pending` it asks again every 0.1 s, up to 10 s, so it scores what the typing route settles on whatever the machine's speed, where the app looks three times 0.9 s apart) and, when the writing model is present, Option+Space. It fails when an item labelled correct in `everyday/baseline.json` is not correct any more, and lists every such item. CI runs typing on every item and Option+Space on a fixed sample of 40. After an intended change, `--update` records the new labels (review the diff of `everyday/baseline.json`).

## Quality gates

- **Frozen corpora.** `frozen.json` pins every frozen corpus (the English sets and manifests, the held-out set and its sources, typo-fuzz, names, the everyday items, the tone regression set) by SHA-256 and size; `scripts/check-frozen-corpora.py` fails CI when one changes, disappears or appears unpinned. A deliberate new corpus version is pinned with `--update` (and its baselines are then updated on purpose).
- **Baselines.** `baselines.json` holds the last accepted numbers: held-out test and typo-fuzz test (fixed and false alarms per layer), names (typo recall, damaged names), the tone regression set (passed items per mode) and performance. `run-heldout-benchmark.py --baseline SUITE`, `run-name-benchmark.py --baseline` and the everyday gate fail when a fix rate falls more than 0.5 points below the baseline, false alarms (or damaged names) rise by more than 2, or p50/p95 latency or peak engine memory exceed 1.5 times the baseline (latency also gets 2 ms of slack for sub-millisecond checks). Performance is compared only with a baseline measured on the same kind of machine (`ci`, or the local chip); summaries record p50/p95 latency and peak memory either way. The tone regression sets (`tone-regression`, `tone-regression-2`) are the exception for latency: their p50/p95 comparison prints the same line ("baseline ok", or "over baseline, informational") but never fails the run, while peak memory and the pass rates stay hard gates. On the GPU-less CI runner the 0.8B tone model's latency varies by more than 1.5x between identical runs (PR #41: Direct p95 22.7 s, 25.5 s and 21.1 s on the same code against a 16.0 s single-run baseline), and a 52-item sample's p95 is its third slowest item. Tone latency is measured locally (`summary.json` p50/p95) and the everyday gate still covers Fix-mode latency; the `ci` performance entries are still recorded so the trend stays visible.
- **Updating a baseline.** `python3 scripts/update-baselines.py SUITE SUMMARY --reason "..."` records a run's summary, with the date and reason, after a change lifts a score (so later changes cannot give the gain back) or for a deliberate, explained trade-off. Test-split summaries come from CI: `gh run download RUN -n quality-summaries-SHA` holds totals only.
- **Tests.** CI fails on an XCTest skip that is not in `mac/Tests/expected-skips.txt`, and runs the engine's real-pack typing-route slip tests (`cargo test --release -- --ignored typing_route`).
