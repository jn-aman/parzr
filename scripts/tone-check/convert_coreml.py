#!/usr/bin/env python3
"""Converts a trained tone classifier to Core ML, checks it against PyTorch on DEV, and lays out the tone pack.

  1. trace the PyTorch model (ids and mask, 1 x max_len int32 -> softmax probs) and convert it (fp16, macOS 13)
  2. quantize the weights to 8 bits (linear, per channel)
  3. compile both with coremlcompiler, score DEV with each, and report agreement with PyTorch and DEV metrics
  4. write the pack folder: tone.mlmodelc (the 8-bit model unless --keep-fp16), vocab.txt, tone-config.json

    venv/bin/python -I scripts/tone-check/convert_coreml.py --run v1-minilm6
"""
import argparse
import json
import pathlib
import shutil
import sys
import time

import numpy as np
import torch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from metrics import evaluate  # noqa: E402
from train import LABELS, MODELS, OUT, REPO, ToneClassifier, predict  # noqa: E402


class Exported(torch.nn.Module):
    """The same network written out in plain torch ops (BERT encoder, mean pooling, head, softmax), sharing the trained
    modules' weights. transformers' own mask helpers do not convert with this coremltools, so the export avoids them."""

    def __init__(self, inner, length):
        super().__init__()
        enc = inner.encoder
        # Shapes are fixed Python ints, so the trace holds no size arithmetic (which this converter rejects).
        self.n = length
        self.d = enc.config.hidden_size // enc.config.num_attention_heads
        self.register_buffer("pos", torch.arange(length).unsqueeze(0), persistent=False)
        self.emb = enc.embeddings
        self.layers = enc.encoder.layer
        self.heads = enc.config.num_attention_heads
        self.head = inner.head

    def forward(self, input_ids, attention_mask):
        n, d = self.n, self.d
        e = self.emb
        h = e.word_embeddings(input_ids) + e.position_embeddings(self.pos) + e.token_type_embeddings(torch.zeros_like(input_ids))
        h = e.LayerNorm(h)
        m = attention_mask.to(h.dtype)
        bias = (1.0 - m)[:, None, None, :] * -10000.0
        for layer in self.layers:
            att = layer.attention.self
            q = att.query(h).view(1, n, self.heads, d).transpose(1, 2)
            k = att.key(h).view(1, n, self.heads, d).transpose(1, 2)
            v = att.value(h).view(1, n, self.heads, d).transpose(1, 2)
            w = torch.softmax(q @ k.transpose(-1, -2) / (d ** 0.5) + bias, -1)
            ctx = (w @ v).transpose(1, 2).reshape(1, n, self.heads * d)
            out = layer.attention.output
            h = out.LayerNorm(out.dense(ctx) + h)
            mid = torch.nn.functional.gelu(layer.intermediate.dense(h))
            h = layer.output.LayerNorm(layer.output.dense(mid) + h)
        mm = m.unsqueeze(-1)
        pooled = (h * mm).sum(1) / mm.sum(1).clamp(min=1.0)
        return torch.softmax(self.head(pooled), -1)


def compile_model(package, out_dir):
    """Compiles with Core ML itself (coremltools wraps MLModel.compileModel), which works without Xcode."""
    import coremltools as ct
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / (package.stem + ".mlmodelc")
    shutil.rmtree(target, ignore_errors=True)
    return pathlib.Path(ct.utils.compile_model(str(package), str(target)))


def score(mlmodel, tok, texts, max_len):
    out, ms = [], []
    for t in texts:
        enc = tok(t, padding="max_length", truncation=True, max_length=max_len, return_tensors="np")
        feed = {"input_ids": enc["input_ids"].astype(np.int32), "attention_mask": enc["attention_mask"].astype(np.int32)}
        s = time.perf_counter()
        p = mlmodel.predict(feed)["probs"]
        ms.append((time.perf_counter() - s) * 1000)
        out.append(np.asarray(p).reshape(-1))
    ms.sort()
    return np.stack(out), {"p50": ms[len(ms) // 2], "p95": ms[int(len(ms) * 0.95)]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--keep-fp16", action="store_true")
    ap.add_argument("--threshold", type=float, help="operating point to ship instead of the validation pick (recorded in the report)")
    a = ap.parse_args()
    import coremltools as ct
    from coremltools.optimize.coreml import OpLinearQuantizerConfig, OptimizationConfig, linear_quantize_weights
    from transformers import AutoModel, AutoTokenizer
    run = OUT / "models" / a.run
    cfg = json.load(open(run / "tone-config.json"))
    max_len, thr = cfg["max_len"], (a.threshold if a.threshold is not None else cfg["threshold"])
    tok = AutoTokenizer.from_pretrained(str(run))
    model = ToneClassifier(AutoModel.from_pretrained(str(MODELS[cfg["base"]])))
    model.load_state_dict(torch.load(run / "model.pt", map_location="cpu"))
    model.eval()
    ex = Exported(model, max_len).eval()
    probe = tok("Thanks for finally getting back to me.", padding="max_length", max_length=max_len, return_tensors="pt")
    ids, mask = probe["input_ids"].to(torch.int32), probe["attention_mask"].to(torch.int32)
    with torch.no_grad():
        diff = (ex(ids, mask) - torch.softmax(model(ids.long(), mask.long()), -1)).abs().max().item()
    assert diff < 1e-4, f"the export differs from the trained model by {diff}"
    traced = torch.jit.trace(ex, (ids, mask))
    ml = ct.convert(traced, inputs=[ct.TensorType(name="input_ids", shape=(1, max_len), dtype=np.int32),
                                    ct.TensorType(name="attention_mask", shape=(1, max_len), dtype=np.int32)],
                    outputs=[ct.TensorType(name="probs")], compute_precision=ct.precision.FLOAT16,
                    minimum_deployment_target=ct.target.macOS13, convert_to="mlprogram")
    ml.short_description = "Parzr tone check: neutral, rude, passive-aggressive, curt, over-apologetic"
    ml.license = "Apache-2.0 (fine-tuned from sentence-transformers/all-MiniLM-L6-v2, Apache-2.0)"
    cm = run / "coreml"
    shutil.rmtree(cm, ignore_errors=True); cm.mkdir()
    fp16 = cm / "tone-fp16.mlpackage"
    ml.save(str(fp16))
    q = linear_quantize_weights(ml, OptimizationConfig(global_config=OpLinearQuantizerConfig(mode="linear_symmetric", granularity="per_channel")))
    q8 = cm / "tone-int8.mlpackage"
    q.save(str(q8))
    dev = [json.loads(l) for l in open(REPO / "benchmarks/tone-check/dev.jsonl", encoding="utf-8")]
    texts, labels = [r["text"] for r in dev], [r["label"] for r in dev]
    ref = predict(model, tok, texts, "cpu")
    report = {"run": a.run, "threshold": thr, "validation_threshold": cfg["threshold"], "torch": evaluate(ref, labels, thr)}
    for name, pkg in (("fp16", fp16), ("int8", q8)):
        compiled = compile_model(pkg, cm / f"compiled-{name}")
        size = sum(f.stat().st_size for f in compiled.rglob("*") if f.is_file())
        mlc = ct.models.CompiledMLModel(str(compiled), compute_units=ct.ComputeUnit.CPU_AND_NE)
        probs, lat = score(mlc, tok, texts, max_len)
        agree = float(np.mean([(1 - p[0] >= thr) == (1 - r[0] >= thr) for p, r in zip(probs, ref)]))
        report[name] = {"bytes": size, "latency_ms": lat, "max_abs_diff": float(np.abs(probs - ref).max()), "flag_agreement": agree,
                        "dev": evaluate(probs, labels, thr, rows=dev)}
        d = report[name]["dev"]
        print(f"{name}: {size / 1e6:.1f} MB, p50 {lat['p50']:.2f} ms, max diff {report[name]['max_abs_diff']:.4f}, agreement {agree:.4f}, "
              f"DEV recall {d['recall_any']:.3f} FP {d['fp_rate']:.4f}")
    chosen = "fp16" if a.keep_fp16 else "int8"
    pack = run / "pack/tone"
    shutil.rmtree(pack.parent, ignore_errors=True); pack.mkdir(parents=True)
    shutil.copytree(cm / f"compiled-{chosen}" / f"tone-{chosen}.mlmodelc", pack / "tone.mlmodelc")
    shutil.copy(MODELS[cfg["base"]] / "vocab.txt", pack / "vocab.txt")  # the base model's WordPiece vocabulary, unchanged by fine-tuning
    json.dump({"labels": LABELS, "threshold": thr, "max_len": max_len}, open(pack / "tone-config.json", "w"), indent=1)
    report["pack"] = {"model": chosen, "files": sorted(str(p.relative_to(pack.parent)) for p in pack.rglob("*") if p.is_file())}
    json.dump(report, open(run / "coreml-report.json", "w"), indent=1)
    print("pack:", pack)


if __name__ == "__main__":
    main()
