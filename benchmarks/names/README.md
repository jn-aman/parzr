# Name benchmark

6,426 synthetic sentences that check Parzr never damages a name: 559 given and family names from 23 naming traditions (Indian languages, Chinese, Japanese, Korean, Arabic and Persian, Yoruba, Igbo, Swahili, Slavic, Spanish and Portuguese, German and Dutch with particles, Irish, hyphenated, diacritics, and English names that are ordinary words), each in greetings, sign-offs, direct address, subjects, objects, possessives, lists, full names, mentions, emails and lines of their own, written in lowercase, Capitalized and ALL CAPS. 306 control sentences contain real misspellings that must still be corrected.

The sentences and name lists are authored for this benchmark and contain no personal data. `generate.py` rebuilds `corpus.jsonl` deterministically (seed 1497).

`heldout.jsonl` adds 1,144 lowercase sentences with 104 names that appear in no shipped list and nowhere in the corpus, reported separately, so the score measures how well Parzr generalises rather than how well it remembers a list.

A name is damaged when an edit that overlaps it changes letters or word boundaries. Changing only its case or nearby punctuation is allowed.

```sh
cargo build --release --locked --manifest-path engine/Cargo.toml
python3 scripts/run-name-benchmark.py
```

CI runs the rules alone. Add `--gec` to include Smart grammar (the on-device GECToR model, which needs the bundled runtime and `dist/model/gector`); the 0.2 results are 0.03% of names damaged with the rules alone and 0.05% with Smart grammar, 1.14% on the held-out names in both cases.

The run fails when it exceeds `thresholds.json`, and writes a breakdown by case, context and culture with the damaged examples to `dist/qa/names/report.json`. CI runs it on every push.
