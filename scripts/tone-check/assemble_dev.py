#!/usr/bin/env python3
"""Assembles the tone-check DEV set (benchmarks/tone-check/dev.jsonl). Every item has `label` (one of the five
classes), `source`, and `hard` (a civil message that a naive classifier tends to flag).

  written     scripts/tone-check/dev_written.txt: lines written for DEV in settings the training seeds do not use
  probe       bake-off 2's workplace probe (48 harsh lines in five categories, 40 hard negatives), copied into
              benchmarks/tone-check/bakeoff2-harsh-probe.jsonl; insult, profanity and condescension map to rude
  tone-items  bake-off 2's labels of the rewrite tone set (benchmarks/tone-check/bakeoff2-tone-labels.jsonl)
  everyday    dist/batches/batch-002 texts written for Parzr (Enron lines excluded): neutral unless listed in
              benchmarks/tone-check/everyday-relabel.json after the review of the lines Apple's model flagged

The training builder removes every DEV text from training. benchmarks/heldout is not used.

    python3 -I scripts/tone-check/assemble_dev.py
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
BENCH = REPO / "benchmarks/tone-check"
sys.path.insert(0, str(HERE))
from paths import BATCHES  # noqa: E402

BATCH2 = BATCHES / "batch-002/items.jsonl"
PROBE_MAP = {"insult": "rude", "profanity": "rude", "condescending_blame": "rude", "passive_aggressive": "passive_aggressive",
             "curt_demand": "curt", "hard_negative": "neutral"}
TONE_MAP = {"adv-insult-05": "passive_aggressive", "adv-edge-03": "curt"}


def main():
    rows = []
    for i, line in enumerate(open(HERE / "dev_written.txt", encoding="utf-8")):
        if line.startswith("#") or not line.strip():
            continue
        label, text = line.rstrip("\n").split("\t", 1)
        rows.append({"id": f"dev-w{i:03d}", "label": label.replace("-hard", ""), "hard": label.endswith("-hard"), "source": "written", "text": text})
    for l in open(BENCH / "bakeoff2-harsh-probe.jsonl", encoding="utf-8"):
        r = json.loads(l)
        rows.append({"id": f"dev-{r['id']}", "label": PROBE_MAP[r["category"]], "hard": r["category"] == "hard_negative",
                     "source": "probe", "probe_category": r["category"], "text": r["text"]})
    for l in open(BENCH / "bakeoff2-tone-labels.jsonl", encoding="utf-8"):
        r = json.loads(l)
        if r["label"] == "borderline":
            continue
        label = "neutral" if r["label"] == "not_harsh" else TONE_MAP.get(r["id"], "rude")
        rows.append({"id": f"dev-{r['id']}", "label": label, "hard": False, "source": "tone-items", "text": r["text"]})
    relabel_path = BENCH / "everyday-relabel.json"
    relabel = json.load(open(relabel_path)) if relabel_path.exists() else {}
    for l in open(BATCH2, encoding="utf-8"):
        r = json.loads(l)
        if r["source"] not in ("written", "corrupted"):
            continue
        label = relabel.get(r["id"], "neutral")
        if label == "drop":
            continue
        rows.append({"id": f"dev-{r['id']}", "label": label, "hard": False, "source": "everyday", "text": r["expected"]})
    # One item per text (the tone set repeats some inputs).
    seen, out = set(), []
    for r in rows:
        key = r["text"].strip().lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    with open(BENCH / "dev.jsonl", "w", encoding="utf-8") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    # DEV2: benchmarks/tone-check/dev2_written.txt, scored once at the end (see its header).
    with open(BENCH / "dev2.jsonl", "w", encoding="utf-8") as f:
        for i, line in enumerate(open(BENCH / "dev2_written.txt", encoding="utf-8")):
            if line.startswith("#") or not line.strip():
                continue
            label, text = line.rstrip("\n").split("\t", 1)
            f.write(json.dumps({"id": f"dev2-{i:03d}", "label": label.replace("-hard", ""), "hard": label.endswith("-hard"), "source": "written", "text": text}, ensure_ascii=False) + "\n")
    from collections import Counter
    print(len(out), Counter((r["source"], r["label"]) for r in out))


if __name__ == "__main__":
    main()
