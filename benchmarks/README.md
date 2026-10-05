# English challenge set

100 independently authored base paragraphs across 20 grammar families and five lexical contexts, each with ten error combinations: **1,000 distinct corrupted paragraphs**, plus **100 clean controls**. There are 4,400 annotated error spans. Each corrupted paragraph has a reference correction and reversible UTF-16 edits.

The combinations include grammar, spelling, missing sentence punctuation, short-word typos, joined words, and mixtures of these errors. Grammar templates are independent of the checker's implemented rules. Spelling mutations are rejected when they produce a known word in the current lexicon; this selection step uses the project's lexicon.

This authored synthetic dataset tests specific structures. Repeated templates across lexical contexts are not independent observations of general English usage. Single reference corrections are not exhaustive: dialect, style and valid alternative corrections require human review. Exact-match rate is not a general grammar accuracy score.

This is a development challenge, not a held-out evaluation. Its failures were used to improve the checker. The corpus includes a corrected article in two base references; before/after comparisons must use the same corpus and clean-control hashes.

Generate and run against a built app:

```sh
python3 scripts/generate-english-benchmark.py
python3 scripts/run-english-benchmark.py
```

The runner measures the packaged Rust executable and a native harness compiled with the application's unchanged `WritingEngine` and model sources. The harness loads the packaged Rust library and uses the same Apple NaturalLanguage enrichment. It does not open the app, read personal writing, or exercise editor UI. Both paths use Fix mode, American English, an empty personal dictionary and no manually protected ranges.

Results are written under ignored `dist/qa/english-1000/`: a searchable offline HTML report, CSV and JSONL with every input/reference/actual output, readable text files, summaries by grammar family and combination, and a ZIP containing the corpus and results. Returned edit plans are checked for UTF-16 validity, nonoverlap, original-span agreement and reconstruction of the returned text. Artifact and source hashes identify the measured checker. Runtime timings include initialization in the first case; later cases run in the same process.

The runner reports exact reference matches, nonexact changes needing review, unchanged erroneous inputs, execution errors, and changes to clean controls. It never counts every change as a successful correction. Generated reports belong to the particular measured build; changing rules requires a new run.
