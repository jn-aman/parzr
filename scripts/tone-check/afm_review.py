#!/usr/bin/env python3
"""Second-opinion labels for the written tone-check lines from Apple's on-device model (afm-label.swift).

    python3 -I scripts/tone-check/afm_review.py input  > dist/tone-check/data/afm-input.jsonl
    dist/tone-check/bin/afm-label < dist/tone-check/data/afm-input.jsonl > dist/tone-check/data/afm-labels.jsonl
    python3 -I scripts/tone-check/afm_review.py report dist/tone-check/data/afm-labels.jsonl

`input` lists every seed line, three fills of every template and every DEV item. `report` prints agreement per
class and source, and every disagreement on seeds and on written DEV lines, for a reviewer to confirm or fix.
"""
import json
import pathlib
import random
import sys
from collections import Counter, defaultdict

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import build_dataset as bd  # noqa: E402

DEV = bd.REPO / "benchmarks/tone-check/dev.jsonl"


def items():
    rng = random.Random(3)
    for label in bd.LABELS:
        for i, line in enumerate(bd.seeds(label)):
            yield {"id": f"seed-{label}-{i}", "text": line, "label": label, "source": "seed"}
    for label, temps in bd.TEMPLATES.items():
        for ti, t in enumerate(temps):
            for k in range(3):
                yield {"id": f"tpl-{label}-{ti}-{k}", "text": bd.fill(t, rng), "label": label, "source": "template"}
    for l in open(DEV, encoding="utf-8"):
        r = json.loads(l)
        yield {"id": r["id"], "text": r["text"], "label": r["label"], "source": "dev-" + r["source"]}


def report(path):
    want = {r["id"]: r for r in items()}
    got = {}
    for l in open(path, encoding="utf-8"):
        r = json.loads(l)
        got[r["id"]] = r
    agree = defaultdict(Counter)
    harsh_agree = defaultdict(Counter)
    errors = Counter()
    dis = []
    for i, w in want.items():
        g = got.get(i)
        if g is None:
            continue
        if g.get("error") or not g.get("label"):
            errors[w["source"]] += 1
            continue
        key = (w["source"].split("-")[0] if not w["source"].startswith("dev") else w["source"], w["label"])
        agree[key][g["label"] == w["label"]] += 1
        harsh_agree[key][(g["label"] != "neutral") == (w["label"] != "neutral")] += 1
        if g["label"] != w["label"] and w["source"] in ("seed", "dev-written", "template"):
            dis.append((w["source"], w["label"], g["label"], w["id"], w["text"]))
    print("source/label: exact agreement, harsh-or-not agreement")
    for k in sorted(agree):
        a, h = agree[k], harsh_agree[k]
        print(f"  {k[0]:16s} {k[1]:19s} n={sum(a.values()):4d}  exact {a[True] / sum(a.values()):.2f}  harsh {h[True] / sum(h.values()):.2f}")
    print("errors:", dict(errors))
    for d in sorted(dis):
        print("\t".join(d))


if __name__ == "__main__":
    if sys.argv[1] == "input":
        for r in items():
            print(json.dumps({"id": r["id"], "text": r["text"]}, ensure_ascii=False))
    else:
        report(sys.argv[2])
