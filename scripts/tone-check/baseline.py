#!/usr/bin/env python3
"""Bake-off 2's baseline on the tone-check DEV sets: frozen all-MiniLM-L6-v2 embeddings + its logistic regression
(dist/model-bakeoff2/data/tone/clf-minilm-all.npy), harsh-or-not at 0.5 and at its p90 threshold 0.75.

    venv/bin/python -I scripts/tone-check/baseline.py
"""
import json
import pathlib
import sys

import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from paths import BAKEOFF as B, TONE  # noqa: E402


def main():
    from sentence_transformers import SentenceTransformer
    m = SentenceTransformer(str(B / "models/sentence-transformers__all-MiniLM-L6-v2"), device="cpu")
    w = np.load(B / "data/tone/clf-minilm-all.npy")
    out = {}
    for name in ("dev", "dev2"):
        rows = [json.loads(l) for l in open(REPO / f"benchmarks/tone-check/{name}.jsonl", encoding="utf-8")]
        X = m.encode([r["text"] for r in rows], normalize_embeddings=True, batch_size=64)
        p = 1 / (1 + np.exp(-(X @ w[:-1] + w[-1])))
        for thr in (0.5, 0.75):
            harsh = [r["label"] != "neutral" for r in rows]
            flag = p >= thr
            neutral = [not h for h in harsh]
            fp = int(sum(f and n for f, n in zip(flag, neutral)))
            per = {}
            for c in ("rude", "passive_aggressive", "curt", "over_apologetic"):
                idx = [i for i, r in enumerate(rows) if r["label"] == c]
                per[c] = f"{int(sum(flag[i] for i in idx))}/{len(idx)}"
            rec = sum(f and h for f, h in zip(flag, harsh)) / sum(harsh)
            out[f"{name}@{thr}"] = {"recall_any": rec, "fp": fp, "neutral": sum(neutral), "fp_rate": fp / sum(neutral), "per_category": per}
            print(name, thr, f"recall {rec:.3f} FP {fp}/{sum(neutral)} ({fp / sum(neutral):.4f})", per)
    json.dump(out, open(TONE / "results/baseline-minilm-lr.json", "w"), indent=1)


if __name__ == "__main__":
    main()
