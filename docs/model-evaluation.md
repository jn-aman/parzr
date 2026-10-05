# Local writing model evaluation

## Needle 3

Decision: keep Needle out of the application for now. The tested base model did
not correct the authored grammar fixtures or select their corrected alternatives.
Local fine-tuning remains an experiment; these results do not predict a tuned
model's quality.

The [upstream project](https://github.com/cactus-compute/needle) describes a small
model for tool calling, structured extraction, classification and embeddings.
Its published task scores do not measure English grammar correction or passage
rewriting. The advertised 8–29 MB sizes describe model variants; the full archive
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
