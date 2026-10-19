#!/usr/bin/env python3
"""Scores the shipped artifact (the compiled Core ML model in a pack folder, with its own threshold) on DEV and on
DEV2, and writes results/final-<run>.json. DEV2 is scored here only, once, at the end.

    venv/bin/python -I scripts/tone-check/eval_final.py --run v1-minilm6
"""
import argparse
import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from metrics import evaluate  # noqa: E402

from paths import TONE as OUT  # noqa: E402
REPO = pathlib.Path(__file__).resolve().parents[2]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    a = ap.parse_args()
    import coremltools as ct
    from transformers import AutoTokenizer
    pack = OUT / "models" / a.run / "pack/tone"
    cfg = json.load(open(pack / "tone-config.json"))
    tok = AutoTokenizer.from_pretrained(str(OUT / "models" / a.run))
    model = ct.models.CompiledMLModel(str(pack / "tone.mlmodelc"), compute_units=ct.ComputeUnit.CPU_AND_NE)
    out = {"run": a.run, "threshold": cfg["threshold"]}
    for name in ("dev", "dev2"):
        rows = [json.loads(l) for l in open(REPO / f"benchmarks/tone-check/{name}.jsonl", encoding="utf-8")]
        probs = []
        for r in rows:
            enc = tok(r["text"], padding="max_length", truncation=True, max_length=cfg["max_len"], return_tensors="np")
            p = model.predict({"input_ids": enc["input_ids"].astype(np.int32), "attention_mask": enc["attention_mask"].astype(np.int32)})["probs"]
            probs.append(np.asarray(p).reshape(-1))
        out[name] = evaluate(np.stack(probs), [r["label"] for r in rows], cfg["threshold"], rows=rows)
        d = out[name]
        print(f"{name}: n={len(rows)} recall {d['recall_any']:.3f} FP {d['fp_rate']:.4f} ({d['fp']}/{d['neutral']}) precision {d['precision_any']:.3f}")
        for c, v in d["per_category"].items():
            print(f"   {c:19s} flagged {v['flagged']}/{v['n']} ({v['recall_flagged']}), right category {v['category_correct']}")
        print("   FP by source:", d["fp_by_source"])
    (OUT / "results").mkdir(exist_ok=True)
    json.dump(out, open(OUT / f"results/final-{a.run}.json", "w"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
