# Local writing model evaluation

## Smart grammar (GECToR), 0.2.0

How the typing path scores on neutral public data before and after 0.2.0. This is the "fast path" the app runs while you type: the rules, and with Smart grammar on, the rules plus GECToR (see [architecture](architecture.md#smart-grammar-gector)). It does not include Qwen, which only runs for Option+Space and the tones. The corpora are used for evaluation only and are not in this repository, because their terms do not allow redistribution (see [grammar evidence](grammar-evidence.md)).

| | 0.1.x | 0.2.0, rules only | 0.2.0, Smart grammar (default) |
| --- | --- | --- | --- |
| BEA-2019 dev, F0.5 (precision / recall) | 0.202 (0.43 / 0.065) | 0.228 (0.63 / 0.06) | 0.529 (0.71 / 0.26) |
| CoNLL-2014, F0.5 (precision) | 0.212 (0.48) | 0.222 (0.57) | 0.550 (0.72) |
| JFLEG test, GLEU (F0.5) | 0.478 (0.533) | 0.479 (0.565) | 0.540 (0.690) |
| False alarms on clean published text, per 1,000 words | 9.34 | 1.07 | 3.39 (chat 0, Hinglish 0) |
| Names damaged: all / lowercase / held-out | 0.08% / 0.18% / 1.40% | 0.03% / 0.07% / 1.14% | 0.05% / 0.11% / 1.14% |
| Real typos still corrected | 94.4% | 95.4% | 95.4% |

What the measures mean:

- **Precision** is the share of suggestions that were correct. **Recall** is the share of the real mistakes that were found.
- **F0.5** combines them and counts precision twice as much as recall. Grammar checkers use it because an unwanted or wrong suggestion annoys a writer more than a missed one does.
- **GLEU** (JFLEG) compares a corrected sentence with several human corrections, rewarding n-grams that appear in the references and penalising ones that were in the source and should have changed. It favours fluent rewrites; the F0.5 in brackets is the strict minimal-edit score on the same data.
- **False alarms per 1,000 words** count suggestions on text that needed none: 1,996 sentences of published prose (Project Gutenberg, Wikipedia, chat, Indian English and Hinglish). Lower is better.
- **Names damaged** is the share of names an edit changed beyond case, on the [name benchmark](../benchmarks/names/README.md): all 6,426 sentences, the lowercase ones, and the 104 names that are in no shipped list. **Real typos still corrected** is the share of the benchmark's misspelled controls that were fixed.

How to read it. Rules were made far more precise in 0.2.0 (run-on sentences, agreement, abbreviations such as p.m. and i.e., commas, and spelling that no longer "corrects" Hinglish, Indian English vocabulary, Latin phrases, compounds, words macOS knows, in both dialects), which cut false alarms from 9.34 to 1.07 per 1,000 words and lifted precision, with recall unchanged. GECToR then more than doubles F0.5 by finding about four times as many errors, at the price of some false alarms (3.39), still about a third of 0.1.x. Recall is still modest: on BEA-2019 dev Parzr finds about one error in four. Names are slightly more exposed with Smart grammar on than with rules alone (0.05% against 0.03% of names damaged) and still below 0.1.x on every cut. The English challenge benchmarks, which are authored for the rules, stay at 100% on the rules path.

The Qwen3.5-0.8B edits that Option+Space and the tones produce are not part of this table. They pass the filters in `engine/src/model.rs` (`vetted`): no straightening of quotes or dashes, no optional or date commas, no recasing in mid-sentence and no respelling one known word as another.

Measurements are one run on one build. Public benchmarks measure English learner and student writing, so they say little about domain jargon or a particular writer's voice.

## Needle 3

Decision: keep Needle out of the application for now. The tested base model did
not correct the authored grammar fixtures or select their corrected alternatives.
Local fine-tuning remains an experiment; these results do not predict a tuned
model's quality.

The [upstream project](https://github.com/cactus-compute/needle) describes a small
model for tool calling, structured extraction, classification and embeddings.
Its published task scores do not measure English grammar correction or passage
rewriting. The advertised 8 to 29 MB sizes describe model variants; the full archive
downloaded for this evaluation measures **35,335,380 bytes**, including its
container. File size is distinct from working memory.

The [extraction guide](https://cactuscompute.com/blog/structured-extraction-with-needle)
documents grounding values in the input passage. Corrected words and rewritten
sentences require producing text beyond those existing spans. This is a task
mismatch to investigate, rather than evidence that a valid JSON response is a
valid writing correction.

### Reproducible probe

Evaluation date: 2026-10-04. Apple Silicon macOS. No fine-tuning, cloud calls or
execution of generated tool calls. Every passage is an authored synthetic fixture.
The script uses the native C API, sets `NEEDLE_TELEMETRY=0`, `DO_NOT_TRACK=1`
and `HF_HUB_OFFLINE=1`, and re-executes under a macOS sandbox denying all network
access. It verifies the exact weight and runtime hashes before loading.

Pinned assets:

- Python/source repository revision: `9571a58b0ad3d0e4500afa6f4e00cffb8d6d1818`.
- Model repository: `Cactus-Compute/needle3`, revision `c7c415a3d1b3d929014bc6e866d51ebb971f7089`.
- `needle3.cact` SHA-256: `c9d915eca282ed42d1a09b143b592adb4cc6744ffe2d294adf5cfc5548170c38`.
- Native runtime from `cactus_needle-3.1.0-py3-none-macosx_11_0_arm64.whl`.
- Wheel SHA-256: `ad1cba80ede4c058692370964eec4d881a1fdc80014f7210b2d13891bad7d1c6`.
- Extracted `libneedle.dylib` SHA-256: `6c3d79e04c48656b275feb9b4157b43fc20a6efbb5993d0aff9e6414eaef21be`.

Place the two native assets in a local directory, then run:

```sh
python3 scripts/evaluate-needle.py --assets dist/qa/needle/assets --output dist/qa/needle/final
```

| Task | Fixtures | Accepted outputs | Exact corrections / selections | Median generation time |
| --- | ---: | ---: | ---: | ---: |
| Grammar and spelling correction | 10 | 5 | 0/10 | 50.4 ms |
| Already correct controls | 10 | 0 | No accepted rewrite | 73.9 ms |
| Choose between original and corrected sentence | 10 | 9 | 0/10 | 39.7 ms |
| Professional, friendly, concise, direct | 4 | 3 | No exact style reference | 85.6 ms |

Generation times measure `needle_complete`, excluding load and schema
initialization. Peak resident memory of the **entire Python evaluation process**
was 134,905,856 bytes; this includes Python and copied weight buffers and is not
a measurement of the model's memory alone. Load took 8.1 ms, excluding subsequent
initialization. Timings and confidence gating can vary between runs.

All five accepted grammar outputs copied the broken input. For example,
`We should sends the report.` and `Where did Maya went?` remained unchanged.
The ranker selected the broken source whenever it returned an accepted result,
despite alternating the order of the enum choices. Withheld calls are recorded
separately and never treated as accepted corrections. Withholding a clean control
would allow an application to preserve its original; it does not establish
grammar detection accuracy.

Two accepted style results copied the source. The professional output deleted
the final sentence, `I am not happy with the delay.`, while retaining `kinda bad`.
Counting any changed text as a successful rewrite would conceal that omission.

This is a small feasibility probe, **not a comprehensive language benchmark**.
The schema, prompts and fixtures are visible in `scripts/evaluate-needle.py`.
Results and raw envelopes stay in ignored `dist/qa/needle/final/`; the compact
measurement record is in `docs/qa/needle-summary.json`.

### Distribution and source review

The published weights are Apache-2.0 licensed. Upstream defaults to enabled
telemetry, so an offline integration must explicitly disable it. Its model and
engine downloads currently use Hugging Face; copying pinned assets into an app
would remove that dependency for end users. This probe confirms inference can
run with network access denied.

The inspected GitHub tree includes Python model/training code and bindings; no
C/C++ native engine source was present in that revision. The tested runtime is
a prebuilt binary. A reproducible source build or an independently implemented
runtime would therefore need investigation before treating it as part of an
end-to-end source-buildable Parzr distribution.

No Needle weights, runtime, SDK or telemetry have been added to Parzr's app or DMG.
