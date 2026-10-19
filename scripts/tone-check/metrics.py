"""Tone-check metrics shared by training, Core ML checks and reports.

probs: N x 5 array in LABELS order. A message is flagged when 1 - P(neutral) >= threshold; its category is
the most likely non-neutral class.
"""
from collections import Counter

import numpy as np

LABELS = ["neutral", "rude", "passive_aggressive", "curt", "over_apologetic"]


def decide(probs, threshold):
    probs = np.asarray(probs)
    harsh = 1.0 - probs[:, 0]
    cat = probs[:, 1:].argmax(1) + 1
    return [LABELS[c] if h >= threshold else "neutral" for h, c in zip(harsh, cat)]


def pick_threshold(probs, labels, max_fp):
    """The lowest threshold (0.05 steps of 0.01) whose false-positive rate on neutral items is at most max_fp."""
    harsh = 1.0 - np.asarray(probs)[:, 0]
    neutral = np.array([l == "neutral" for l in labels])
    for t in np.arange(0.30, 0.99, 0.01):
        if (harsh[neutral] >= t).mean() <= max_fp:
            return round(float(t), 2)
    return 0.99


def evaluate(probs, labels, threshold, rows=None):
    pred = decide(probs, threshold)
    n_neutral = sum(1 for l in labels if l == "neutral")
    fp = sum(1 for p, l in zip(pred, labels) if l == "neutral" and p != "neutral")
    harsh = [(p, l) for p, l in zip(pred, labels) if l != "neutral"]
    tp_any = sum(1 for p, _ in harsh if p != "neutral")
    per = {}
    f1s = []
    for c in LABELS[1:]:
        items = [(p, l) for p, l in harsh if l == c]
        flagged = sum(1 for p, _ in items if p != "neutral")
        exact = sum(1 for p, _ in items if p == c)
        predicted_c = sum(1 for p in pred if p == c)
        prec = exact / predicted_c if predicted_c else 0.0
        rec = exact / len(items) if items else 0.0
        f1s.append(2 * prec * rec / (prec + rec) if prec + rec else 0.0)
        per[c] = {"n": len(items), "flagged": flagged, "recall_flagged": round(flagged / len(items), 3) if items else None,
                  "category_correct": exact, "recall_category": round(rec, 3) if items else None, "precision_category": round(prec, 3)}
    flagged_total = sum(1 for p in pred if p != "neutral")
    out = {"threshold": threshold, "neutral": n_neutral, "fp": fp, "fp_rate": fp / n_neutral if n_neutral else None,
           "harsh": len(harsh), "recall_any": tp_any / len(harsh) if harsh else None,
           "precision_any": tp_any / flagged_total if flagged_total else None, "macro_f1": float(np.mean(f1s)), "per_category": per}
    if rows is not None:
        by = {}
        for r, p in zip(rows, pred):
            if r["label"] != "neutral":
                continue
            key = "hard" if r.get("hard") else r["source"]
            c = by.setdefault(key, Counter())
            c["n"] += 1
            c["fp"] += p != "neutral"
        out["fp_by_source"] = {k: {"n": v["n"], "fp": v["fp"], "rate": round(v["fp"] / v["n"], 4)} for k, v in by.items()}
        out["false_positives"] = [r["text"] for r, p in zip(rows, pred) if r["label"] == "neutral" and p != "neutral"]
        out["misses"] = [(r["label"], r["text"]) for r, p in zip(rows, pred) if r["label"] != "neutral" and p == "neutral"]
    return out
