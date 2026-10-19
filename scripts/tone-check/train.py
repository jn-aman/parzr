#!/usr/bin/env python3
"""Fine-tunes a small BERT-style encoder (default all-MiniLM-L6-v2, Apache-2.0) end to end as the five-class tone
classifier, on PyTorch MPS. Mean pooling over tokens, then one linear layer.

The flag rule: a message is flagged when 1 - P(neutral) >= threshold, and its category is the most likely
non-neutral class. The threshold is chosen on the validation split (never on DEV): the lowest value whose
false-positive rate on validation neutrals is at most --val-fp. DEV is scored once at that threshold.

    venv/bin/python -I scripts/tone-check/train.py --run minilm6 [--epochs 4] [--lr 5e-5]
"""
import argparse
import json
import math
import pathlib
import random
import sys
import time

import numpy as np
import torch
from torch import nn

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from metrics import evaluate, pick_threshold  # noqa: E402

LABELS = ["neutral", "rude", "passive_aggressive", "curt", "over_apologetic"]
from paths import TONE as OUT  # noqa: E402
REPO = pathlib.Path(__file__).resolve().parents[2]
MODELS = {"minilm6": OUT / "models/base/sentence-transformers__all-MiniLM-L6-v2",
          "minilm12": OUT / "models/base/sentence-transformers__all-MiniLM-L12-v2"}
SOURCE_WEIGHT = {"paradetox": 0.5, "civil": 0.5, "politeness": 0.5}
# The threshold is set on validation messages of the workplace kind; the public corpora's neutral side (Reddit-style
# comments, Wikipedia requests) carries label noise that would push it up for no gain on real messages.
IN_DOMAIN = {"seed", "template", "combo", "everyday"}
MAX_LEN = 64


class ToneClassifier(nn.Module):
    def __init__(self, encoder, n=len(LABELS)):
        super().__init__()
        self.encoder = encoder
        self.dropout = nn.Dropout(0.1)
        self.head = nn.Linear(encoder.config.hidden_size, n)

    def forward(self, input_ids, attention_mask):
        h = self.encoder(input_ids=input_ids, attention_mask=attention_mask).last_hidden_state
        m = attention_mask.unsqueeze(-1).to(h.dtype)
        pooled = (h * m).sum(1) / m.sum(1).clamp(min=1.0)
        return self.head(self.dropout(pooled))


def load(path):
    return [json.loads(l) for l in open(path, encoding="utf-8")]


def predict(model, tok, texts, device, batch=128):
    model.eval()
    out = []
    with torch.no_grad():
        for i in range(0, len(texts), batch):
            enc = tok(texts[i:i + batch], padding="max_length", truncation=True, max_length=MAX_LEN, return_tensors="pt")
            logits = model(enc["input_ids"].to(device), enc["attention_mask"].to(device))
            out.append(torch.softmax(logits.float(), -1).cpu().numpy())
    return np.concatenate(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--base", default="minilm6")
    ap.add_argument("--epochs", type=int, default=4)
    ap.add_argument("--lr", type=float, default=5e-5)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--val-fp", type=float, default=0.01)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--data", type=pathlib.Path, default=OUT / "data/train.jsonl")
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--smoothing", type=float, default=0.1)
    ap.add_argument("--all-data", action="store_true", help="train on train+val (threshold then comes from --threshold)")
    ap.add_argument("--threshold", type=float)
    a = ap.parse_args()
    torch.set_num_threads(a.threads)
    random.seed(a.seed); np.random.seed(a.seed); torch.manual_seed(a.seed)
    from transformers import AutoModel, AutoTokenizer
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    base = MODELS[a.base]
    tok = AutoTokenizer.from_pretrained(str(base))
    model = ToneClassifier(AutoModel.from_pretrained(str(base))).to(device)
    rows = load(a.data)
    train = [r for r in rows if r["split"] == "train"]
    if a.all_data:
        train = rows
    val = [r for r in rows if r["split"] == "val"]
    dev = load(REPO / "benchmarks/tone-check/dev.jsonl")
    counts = np.bincount([LABELS.index(r["label"]) for r in train], minlength=len(LABELS))
    class_w = torch.tensor((counts.sum() / counts) ** 0.5, dtype=torch.float32)
    class_w = (class_w / class_w.mean()).to(device)
    print("train", len(train), "val", len(val), "dev", len(dev), "class weights", class_w.tolist(), flush=True)
    opt = torch.optim.AdamW(model.parameters(), lr=a.lr, weight_decay=0.01)
    steps = a.epochs * math.ceil(len(train) / a.batch)
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: min(1.0, s / (0.06 * steps)) * max(0.0, (steps - s) / (steps * 0.94)))
    loss_fn = nn.CrossEntropyLoss(weight=class_w, reduction="none", label_smoothing=a.smoothing)
    run = OUT / "models" / a.run
    run.mkdir(parents=True, exist_ok=True)
    best = None
    log = []
    step = 0
    for epoch in range(a.epochs):
        model.train()
        random.shuffle(train)
        t0 = time.time()
        total = 0.0
        for i in range(0, len(train), a.batch):
            b = train[i:i + a.batch]
            enc = tok([r["text"] for r in b], padding=True, truncation=True, max_length=MAX_LEN, return_tensors="pt")
            y = torch.tensor([LABELS.index(r["label"]) for r in b], device=device)
            w = torch.tensor([SOURCE_WEIGHT.get(r["source"], 1.0) for r in b], device=device)
            logits = model(enc["input_ids"].to(device), enc["attention_mask"].to(device))
            loss = (loss_fn(logits, y) * w).sum() / w.sum()
            opt.zero_grad(); loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step(); sched.step(); step += 1
            total += loss.item()
        val_in = [r for r in val if r["source"] in IN_DOMAIN]
        pv = predict(model, tok, [r["text"] for r in val_in], device)
        yv = [r["label"] for r in val_in]
        thr = pick_threshold(pv, yv, a.val_fp)
        vm = evaluate(pv, yv, thr)
        entry = {"epoch": epoch + 1, "loss": total / math.ceil(len(train) / a.batch), "seconds": time.time() - t0, "threshold": thr,
                 "val_recall": vm["recall_any"], "val_fp": vm["fp_rate"], "val_macro_f1": vm["macro_f1"]}
        log.append(entry)
        print(json.dumps(entry), flush=True)
        score = vm["macro_f1"] + vm["recall_any"]
        if best is None or score > best[0]:
            best = (score, epoch + 1, thr)
            torch.save(model.state_dict(), run / "model.pt")
    model.load_state_dict(torch.load(run / "model.pt", map_location=device))
    thr = a.threshold if a.threshold is not None else best[2]
    pd_ = predict(model, tok, [r["text"] for r in dev], device)
    report = {"run": a.run, "base": a.base, "best_epoch": best[1], "threshold": thr, "log": log, "args": {k: str(v) for k, v in vars(a).items()},
              "dev": evaluate(pd_, [r["label"] for r in dev], thr, rows=dev)}
    json.dump(report, open(run / "report.json", "w"), indent=1)
    with open(run / "dev-predictions.jsonl", "w", encoding="utf-8") as f:
        for r, p in zip(dev, pd_):
            f.write(json.dumps({"id": r["id"], "label": r["label"], "probs": [round(float(x), 4) for x in p], "text": r["text"]}, ensure_ascii=False) + "\n")
    tok.save_pretrained(str(run))
    json.dump({"labels": LABELS, "threshold": thr, "max_len": MAX_LEN, "base": a.base}, open(run / "tone-config.json", "w"), indent=1)
    d = report["dev"]
    print(f"DEV at threshold {thr:.2f}: recall {d['recall_any']:.3f}, FP {d['fp_rate']:.4f} ({d['fp']}/{d['neutral']}), per category {d['per_category']}")


if __name__ == "__main__":
    main()
