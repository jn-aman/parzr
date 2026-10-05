#!/usr/bin/env python3
"""Fresh topic/lexical generalization of the authored English challenge families."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("challenge", ROOT / "scripts/generate-english-benchmark.py")
challenge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(challenge)

# New names, settings and vocabulary. Structures intentionally remain comparable
# to the development challenge; this is not a held-out natural-language corpus.
TOPICS = [
    dict(name="Anika", topic="charity concert", report="brief", plural="briefs", place="bakery", goods="cakes"),
    dict(name="Omar", topic="station repair", report="letter", plural="letters", place="toy shop", goods="toys"),
    dict(name="Aarav", topic="harbor festival", report="document", plural="documents", place="grocery store", goods="apples"),
    dict(name="Mira", topic="theater opening", report="draft", plural="drafts", place="flower shop", goods="flowers"),
    dict(name="Nora", topic="hospital expansion", report="memo", plural="memos", place="hardware store", goods="tools"),
    dict(name="Lena", topic="village celebration", report="plan", plural="plans", place="clothing store", goods="shirts"),
    dict(name="Theo", topic="sports tournament", report="review", plural="reviews", place="fruit stall", goods="oranges"),
    dict(name="Ravi", topic="bridge inspection", report="record", plural="records", place="music shop", goods="drums"),
    dict(name="Amir", topic="science conference", report="notice", plural="notices", place="furniture store", goods="chairs"),
    dict(name="Jules", topic="railway extension", report="statement", plural="statements", place="shoe shop", goods="boots"),
]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--milestone", type=Path, default=ROOT / "dist/qa/english-1000-milestone/summary.json")
    parser.add_argument("--seed", type=int, default=2610042000)
    args = parser.parse_args()
    milestone = json.loads(args.milestone.read_text())
    counts = milestone["runs"]["native-nlp"]["counts"]
    assert counts.get("exact_match") == 1000 and counts.get("clean_preserved") == 100
    original = ROOT / "benchmarks/english-1000.jsonl"
    assert hashlib.sha256(original.read_bytes()).hexdigest() == milestone["metadata"]["corpus_sha256"]
    originals = {json.loads(line)["input"] for line in original.read_text().splitlines()}
    known = dict(json.loads((ROOT / "engine/rules/lexicon.json").read_text()))
    rows, controls = [], []
    for fi, (family, template, errors) in enumerate(challenge.FAMILIES):
        for ti, topic in enumerate(TOPICS):
            base = f"fresh-{fi * len(TOPICS) + ti + 1:03}"
            correct = template.format(**topic)
            mistakes = [(a.format(**topic), b.format(**topic)) for a, b in errors]
            controls.append(dict(id=base, family=family, input=correct, expected=correct, kind="clean_control"))
            for ci, combination in enumerate(challenge.COMBINATIONS):
                corrupted, annotations = challenge.corrupt(correct, mistakes, combination, random.Random(args.seed + fi * 10000 + ti * 100 + ci), known)
                assert corrupted not in originals
                rows.append(dict(id=f"{base}-{ci+1:02}", base_id=base, family=family, combination=combination[0], input=corrupted, expected=correct, expected_edits=annotations, kind="corrupted_paragraph"))
    assert len(rows) == len({r["input"] for r in rows}) == 2000
    assert len(controls) == 200
    out = ROOT / "benchmarks/english-2000.jsonl"
    clean = out.with_name("english-200-clean.jsonl")
    manifest = out.with_name("english-2000-manifest.json")
    # Fresh first-run evaluation must not silently regenerate different samples.
    if any(p.exists() for p in [out, clean, manifest]):
        raise SystemExit("Fresh corpus already exists; preserve it for reproducible evaluation.")
    for p, data in [(out, rows), (clean, controls)]:
        p.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in data))
    manifest.write_text(json.dumps(dict(seed=args.seed, corrupted_paragraphs=2000, clean_controls=200, base_paragraphs=200, combinations_per_base=10, sha256=hashlib.sha256(out.read_bytes()).hexdigest(), clean_sha256=hashlib.sha256(clean.read_bytes()).hexdigest(), prior_corpus_sha256=milestone["metadata"]["corpus_sha256"], scope="New topics, names, vocabulary and corruptions of the same 20 authored grammar families. Topic/lexical generalization, not new grammar structures or natural-language English accuracy."), indent=2) + "\n")
    print("Generated 2,000 fresh corrupted paragraphs, 200 clean controls; no duplicate inputs with the development set.")

if __name__ == "__main__":
    main()
