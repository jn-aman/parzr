# Rule packs

One JSON file per category of English rule. `engine/build.rs` joins every `*.json` here into one array at build time,
so a new file needs no code change. The three base files (`../grammar.json`, `../tone.json`, `../usage.json`) load
first; packs load after them, in file-name order. Ids must be unique across all of them.

## A rule

```json
{
  "id": "grammar.missing_object_after_modal",
  "pattern": "(?i)\\b(?:I|we|you|they)\\s+(?:can(?:no|')t|could not) (?P<target>delete|remove)(?:\\s*[(,.;:!?)\\n]|\\s*$)",
  "replacement": "${target} it",
  "category": "Grammar",
  "confidence": 0.88,
  "reason": "Say what cannot be done: this verb needs an object.",
  "provenance": "parzr original rule",
  "positive": "Hey, I cannot delete (don't have the permissions), but this role is good to delete.",
  "negative": "I cannot delete the file. You can delete or archive it."
}
```

- `pattern`: a Rust `regex` pattern. **No lookahead, lookbehind or backreferences** (the crate has none); consume the
  context after the target instead and keep only `(?P<target>...)` as the edited span. Prefer `(?i)`; `(?im)` when `^`
  must match line starts. The match's `target` group is replaced by `replacement`; `${name}` expands a group. For a
  move ("Me and Sarah" to "Sarah and I") use the `moved` group as the base rules do.
- Every pack rule must carry a **required literal** for the prefilter (a word that every match contains, outside
  optional groups and character classes), or the Rust test refuses it: a rule without one would run on every check.
- `category`: Grammar, Agreement, Tense, Verb form, Possessive, Word choice, Spelling, Punctuation, Capitalization,
  Style, Clarity, Redundancy, Register, Tone. Grammar/Agreement/Tense/Verb form/Possessive/Word choice/Spelling/
  Punctuation/Capitalization are corrections; Style/Clarity/Redundancy/Register are suggestions with lower confidence.
- `confidence`: 0.95 for unambiguous errors, 0.85–0.9 for likely ones, 0.7–0.8 for suggestions.
- `reason`: one short sentence shown on the card, in plain English, with curly quotes around words.
- `provenance`: who wrote it and from what ("parzr original rule"); never text copied from a licensed corpus or
  another checker's rule file.
- `positive`: one sentence the rule must change; `negative`: one or more correct sentences (joined in one string)
  the pattern must **not** match at all. Add the near misses you thought about: the imperative, the intransitive use,
  the proper noun, the idiom.
- `modes` (optional): restrict to `["professional", ...]`; omit for Fix.

Only `positive`/`negative` are read by tests. The replacement must differ from the target on the positive.

## Policy (owner decisions)

- Always capitalize a sentence start, chat included. Chat shorthand (lol, fyi, pls, u, ty, brb), @mentions, URLs,
  code, paths, identifiers and list markers stay as typed. Never respell a name.
- Roman Hindi words are never respelled; a code-mixed sentence gets spelling, capitalization and punctuation only.
- British spelling and group-noun verbs ("the team are") are right under the British dialect setting; the request
  carries `dialect`, so a rule that depends on it stays out of the packs (write it in Rust) or stays neutral.
- Non-native patterns that are plainly wrong in every variety ("I seen", "reply me", "explain me", "discuss about",
  "cope up", "I am having a doubt" when meaning "question") are corrections. Indian English words that are standard
  there (prepone, do the needful, revert meaning reply, out of station) are *Register* suggestions at ≤ 0.75, never
  Grammar.
- Style rules never flag what is merely a preference: no passive-voice policing, no split-infinitive rule, no
  rule against ending with a preposition, no "very" hunting. Redundancy ("return back", "ATM machine") and plain
  wordiness ("in order to", "at this point in time") are fine as suggestions.

## Procedure for a pack author

1. Read the base files and the other packs first (`grep -h '"id"' ../*.json *.json`) so you add, not repeat.
2. Enumerate the category exhaustively before writing: list every construction and every lexical item (irregular
   verbs, uncountables, verb+preposition pairs, confusion pairs, redundant pairs…) from your own knowledge of
   reference grammars; sort by how often real writers get it wrong. Write the rules; aim for coverage, then tighten.
3. `python3 scripts/check-rule-packs.py engine/rules/packs/<file>.json` — structural checks, fast.
4. `cargo test --release rules::` in `engine/` — positives, negatives, prefilter literal, unique ids.
5. False alarms, the gate that matters most (never ship a rule that fires on correct text):
   `PARZR_MODEL_RUNTIME=<runtime> PARZR_MODELS_DIR=<models> python3 scripts/false-alarm-gate.py --engine engine/target/release/parzr-engine --corpus /Users/aman/Desktop/parzr/dist/mining/corpus/mining.jsonl --baseline <baseline.json> --only-rules <your id prefix>`
   Inspect every hit of your rules: a hit on a genuinely correct sentence means the rule is tightened or dropped. The
   corpus is not perfectly clean (learner text, lowercase chat), so a hit can be a true positive; say which in your
   report. Also `benchmarks/english-100-clean.jsonl`, `english-200-clean.jsonl` and the everyday set's `clean` items
   must stay untouched (the gates below check them).
6. The quality gates, all of which must stay green: English 1000/2000 exact (`scripts/run-english-benchmark.py
   --require-exact`), `scripts/everyday-batch.py gate` (no newly wrong), names benchmark, held-out DEV and typo-fuzz
   DEV not lower (`scripts/run-heldout-benchmark.py`, never the test split), `cargo test --release` (all), `cargo
   clippy --all-targets -- -D warnings`, `cargo fmt --check`.
7. Measure what you gained: run `scripts/run-heldout-benchmark.py --split dev` before and after and report the fix
   rate per layer, plus the hits of your rules on `dist/mining/corpus/mining.jsonl` rows that are **not** clean
   (`clean: false`, real errors with references) if you want recall evidence — never copy any of that text.
8. Commit on your branch with the pack file and a short entry in `docs/grammar-coverage.md`.

Never read `benchmarks/heldout/*` test files. Never copy sentences from `dist/mining`, `dist/gec-data` or any
licensed corpus into a rule, a positive/negative or a test: write your own examples.
