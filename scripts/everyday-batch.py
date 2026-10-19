#!/usr/bin/env python3
"""Everyday-writing batches: run short real-world texts through the app's own paths and score them.

Items (JSONL): {"id", "text", "expected", "accept": [...], "flex": bool, "tones": bool, ...}
  expected  the corrected text (equal to text when it must stay unchanged)
  accept    other acceptable outputs
  flex      chat-style text. true (batches 1 and 2): sentence-initial capitals, a final full stop or
            question mark and "ok"/"OK" are optional, so "see you at 7" may stay lowercase or become
            "See you at 7.". "stop" (from batch 3, where capitals are never optional): only the final full
            stop and the case of "ok"/"OK"/"Ok" are optional.
  dialect   "british" or "american" (the default), sent with every request

Paths, as the app calls the engine (ParzrCore's WritingEngine with Apple NaturalLanguage hints,
through scripts/heldout-native.swift):
  typing  {"gec":true,"capitalize_names":true}; when the answer carries "context.pending" the app
          checks again after 0.9 s, at most three times, and so does this runner
  deep    Option+Space: {"gec":true,"deep":true,"capitalize_names":true}
  friendly / professional (items with "tones"): the tone rewrites, Friendly as in a chat app
  fixcheck (items with "tones"): Option+Space again on the deep output, which should not change

  run    python3 scripts/everyday-batch.py run --items ITEMS --out OUTPUTS [--native BIN] [--engine DYLIB]
  score  python3 scripts/everyday-batch.py score --items dist/batches/regression.jsonl [--native BIN] [--engine DYLIB]
         runs typing and deep on every item and prints label counts; --outputs FILE scores saved outputs.
         --baseline FILE (a previous --save) lists the items whose label changed.
  gate   python3 scripts/everyday-batch.py gate --native dist/qa/heldout-native [--paths typing,deep] [--update]
         CI's everyday gate: scores the committed set (benchmarks/everyday/items.jsonl) on typing (with its
         follow-ups) and, when the writing model is present, Option+Space; fails when an item the committed
         baseline (benchmarks/everyday/baseline.json) had correct is not correct any more, or when p50/p95
         latency or peak memory exceed 1.5x the performance baseline (benchmarks/baselines.json). Writes
         dist/qa/everyday/summary.json and outputs.jsonl. --update records this run as the baseline, on purpose.

Build the harness once:
  swiftc -O -parse-as-library mac/Sources/ParzrCore/Models.swift mac/Sources/ParzrCore/WritingEngine.swift mac/Sources/ParzrCore/LinguisticHints.swift \\
    scripts/heldout-native.swift -o dist/batches/tools/native
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import quality_gates  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
# The checkout whose dist/ holds the batch tools and the model runtime (a worktree can point at the main one).
MAIN = Path(os.environ.get("PARZR_ROOT", ROOT))
DEFAULT_NATIVE = MAIN / "dist/batches/tools/native"
DEFAULT_RUNTIME = MAIN / "dist/final/libparzr_model.dylib"
# The installed app's downloaded model pack (apps up to 0.4.12 bundled it in Resources/Model).
DEFAULT_MODEL = next((p for p in [Path.home() / "Library/Application Support/Parzr/Models/essential/1/Qwen3.5-0.8B-Q5_K_M.gguf",
                                  Path("/Applications/Parzr.app/Contents/Resources/Model/Qwen3.5-0.8B-Q5_K_M.gguf")] if p.exists()),
                     MAIN / "dist/models/essential/1/Qwen3.5-0.8B-Q5_K_M.gguf")
PATHS = {
    "typing": {"gec": True, "capitalize_names": True},
    "deep": {"gec": True, "deep": True, "capitalize_names": True},
    "friendly": {"gec": True, "capitalize_names": True, "mode": "friendly", "casual": True},
    "professional": {"gec": True, "capitalize_names": True, "mode": "professional"},
}


def model_file():
    """The writing model the harness will load: PARZR_MODEL_PATH, else the essential pack in PARZR_MODELS_DIR (as the
    engine finds it), else the default above; None when absent."""
    if os.environ.get("PARZR_MODEL_PATH"):
        path = Path(os.environ["PARZR_MODEL_PATH"])
    elif os.environ.get("PARZR_MODELS_DIR"):
        path = next(iter(sorted(Path(os.environ["PARZR_MODELS_DIR"]).glob("essential/*/*.gguf"))), Path("/nonexistent"))
    else:
        path = DEFAULT_MODEL
    return path if path.is_file() else None


class Engine:
    def __init__(self, native, dylib):
        env = dict(os.environ)
        env["PARZR_ENGINE_PATH"] = str(dylib)
        env.setdefault("PARZR_MODEL_RUNTIME", str(DEFAULT_RUNTIME))
        if not env.get("PARZR_MODELS_DIR"):  # with a models folder the engine finds the pack's own files
            env.setdefault("PARZR_MODEL_PATH", str(DEFAULT_MODEL))
        self.proc = subprocess.Popen([str(native)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     env=quality_gates.engine_env(env), text=True, bufsize=1)
        # Per path: the time of each check's first answer (what the writer waits for), follow-ups excluded.
        self.latency = {}

    def ask(self, text, path, dialect=None):
        self.proc.stdin.write(json.dumps({"text": text, **PATHS[path], **({"dialect": dialect} if dialect else {})}) + "\n")
        self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        if not line:
            raise RuntimeError("engine exited")
        return json.loads(line)

    def check(self, text, path, dialect=None, follow_ups=3):
        start = time.time()
        result = self.ask(text, path, dialect)
        self.latency.setdefault(path, []).append((time.time() - start) * 1000)
        follow = 0
        while path == "typing" and "context.pending" in (result.get("warnings") or []) and follow < follow_ups:
            time.sleep(0.9)
            result = self.ask(text, path, dialect)
            follow += 1
        return {"text": result.get("text"), "error": result.get("error"),
                "edits": [{k: e.get(k) for k in ("original", "replacement", "rule_id", "start_utf16")} for e in result.get("edits", [])],
                "warnings": result.get("warnings") or [], "followups": follow, "ms": round((time.time() - start) * 1000)}

    def close(self):
        """Ends the harness; returns its peak resident memory in MB."""
        self.proc.stdin.close()
        return quality_gates.reap(self.proc)


def run(items, out_path, native, dylib, paths, engine=None):
    done = set()
    if out_path.exists():
        done = {json.loads(l)["id"] for l in open(out_path)}
    engine = engine or Engine(native, dylib)
    with open(out_path, "a") as out:
        for n, it in enumerate(items):
            if it["id"] in done:
                continue
            row = {"id": it["id"]}
            for path in paths:
                if path in ("friendly", "professional") and not it.get("tones"):
                    continue
                try:
                    row[path] = engine.check(it["text"], path, it.get("dialect"))
                except Exception as error:  # noqa: BLE001 - a crash is a finding, not a stop
                    row[path] = {"text": None, "error": f"crash: {error}"}
                    engine = Engine(native, dylib)
            if it.get("tones") and "deep" in row and row["deep"].get("text"):
                try:
                    row["fixcheck"] = engine.check(row["deep"]["text"], "deep", it.get("dialect"))
                except Exception as error:  # noqa: BLE001
                    row["fixcheck"] = {"text": None, "error": f"crash: {error}"}
                    engine = Engine(native, dylib)
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            out.flush()
            if n % 50 == 0:
                print(f"{n}/{len(items)}", file=sys.stderr, flush=True)
    return engine.latency, engine.close()


SENTENCE_START = re.compile(r"(^|[.!?]+[\"')\]]*\s+)([A-Z])")


def flex_norm(s, source, capitals_optional=True):
    s = re.sub(r"\b(?:ok|OK|Ok)\b", "ok", s)
    if capitals_optional:
        s = SENTENCE_START.sub(lambda m: m.group(1) + m.group(2).lower(), s)
    if not re.search(r"[.!?…]\s*$", source):
        s = re.sub(r"[.?]$", "", s.rstrip())
    return s


def label(item, out_text):
    """correct / missed / false_alarm / wrong from the expected outputs alone."""
    if out_text is None:
        return "crash"
    inp = item["text"]
    good = [item["expected"], *item.get("accept", [])]
    flex = item.get("flex")
    norm = (lambda s: flex_norm(s, inp, flex is True)) if flex else (lambda s: s)
    if norm(out_text) in {norm(g) for g in good}:
        return "correct"
    if out_text == inp:
        return "missed"
    if norm(inp) in {norm(g) for g in good}:
        return "false_alarm"
    return "wrong"


def score(items, outputs, baseline=None, save=None, show=40):
    by_id = {o["id"]: o for o in outputs}
    counts = {p: Counter() for p in ("typing", "deep")}
    rows = {}
    for it in items:
        o = by_id.get(it["id"])
        if not o:
            continue
        for p in counts:
            if p in o:
                lab = label(it, o[p].get("text"))
                counts[p][lab] += 1
                rows[f"{it['id']}:{p}"] = (lab, it, o[p].get("text"))
    n = sum(counts["typing"].values())
    for p, c in counts.items():
        clean = sum(1 for it in items if it["expected"] == it["text"] and it["id"] in by_id)
        fa = c["false_alarm"]
        print(f"{p:7s} n={sum(c.values())} " + " ".join(f"{k}={c[k]}" for k in ("correct", "missed", "wrong", "false_alarm", "crash"))
              + f"  exact={c['correct'] / max(1, sum(c.values())):.3f}  false-alarm rate={fa / max(1, clean):.3f}")
    if save:
        json.dump({k: v[0] for k, v in rows.items()}, open(save, "w"), indent=0)
    if baseline:
        old = json.load(open(baseline))
        better = [k for k, v in rows.items() if k in old and old[k] != "correct" and v[0] == "correct"]
        worse = [k for k, v in rows.items() if k in old and old[k] == "correct" and v[0] != "correct"]
        print(f"vs baseline: {len(better)} newly correct, {len(worse)} newly wrong")
        for k in worse[:show]:
            lab, it, out = rows[k]
            print(f"  WORSE {k} [{lab}] {it['text']!r} -> {out!r} (want {it['expected']!r})")
    return counts, n


EVERYDAY = ROOT / "benchmarks/everyday"
WARM_UP = ["This is so bad. I hat it.", "Its late, lets go home.", "She dont know were the meeting is."]


def sample(items, n):
    """A fixed sample of n items (by a hash of the id), the same on every run and machine; all items when n is 0."""
    if not n or n >= len(items):
        return items
    keep = set(sorted((hashlib.sha256(it["id"].encode()).hexdigest(), it["id"]) for it in items)[:n])
    return [it for it in items if (hashlib.sha256(it["id"].encode()).hexdigest(), it["id"]) in keep]


def gate(items, paths, native, dylib, baseline_path, output, update=False, deep_sample=0):
    """Score the committed everyday set and fail on any item that was correct in the baseline and no longer is."""
    output.mkdir(parents=True, exist_ok=True)
    if "deep" in paths and not model_file():
        print("everyday gate: no writing model here, so Option+Space (deep) is not scored", file=sys.stderr)
        paths = [p for p in paths if p != "deep"]
    scored = {p: sample(items, deep_sample) if p == "deep" else items for p in paths}
    engine = Engine(native, dylib)
    # Load the models (and the slip checker's background job) before anything is timed or scored.
    for text in WARM_UP:
        for path in paths:
            engine.check(text, path, follow_ups=10)
    engine.latency = {}
    started, rss, outputs = time.time(), [], {}
    for path in paths:
        for n, it in enumerate(scored[path]):
            try:
                result = engine.check(it["text"], path, it.get("dialect"))
            except Exception as error:  # noqa: BLE001 - a crash is a finding, not a stop
                result = {"text": None, "error": f"crash: {error}"}
                latency = engine.latency
                rss.append(engine.close())
                engine = Engine(native, dylib)
                engine.latency = latency
            outputs.setdefault(it["id"], {"id": it["id"]})[path] = result
            if n % 500 == 0:
                print(f"{path} {n}/{len(scored[path])}", file=sys.stderr, flush=True)
    latency = engine.latency
    rss = max([r for r in [*rss, engine.close()] if r is not None], default=None)
    with open(output / "outputs.jsonl", "w") as stream:
        stream.writelines(json.dumps(o, ensure_ascii=False) + "\n" for o in outputs.values())
    labels = {p: {it["id"]: label(it, outputs[it["id"]][p].get("text")) for it in scored[p]} for p in paths}
    baseline = json.loads(baseline_path.read_text()) if baseline_path.exists() else {}
    summary = {"items": len(items), "machine": quality_gates.machine(), "seconds": round(time.time() - started, 1), "max_rss_mb": rss, "paths": {}}
    failures = []
    by_id = {it["id"]: it for it in items}
    for p in paths:
        counts = Counter(labels[p].values())
        follow_ups = Counter(outputs[i][p].get("followups", 0) for i in labels[p])
        old = baseline.get(p, {})
        worse = sorted(i for i, lab in labels[p].items() if old.get(i) == "correct" and lab != "correct")
        better = sorted(i for i, lab in labels[p].items() if i in old and old[i] != "correct" and lab == "correct")
        unknown = sorted(i for i in labels[p] if i not in old)
        summary["paths"][p] = {"scored": len(labels[p]), "counts": dict(counts), "correct_rate": round(counts["correct"] / max(1, len(labels[p])), 4),
                               "latency": quality_gates.latency(latency.get(p, [])), "follow_ups": dict(follow_ups),
                               "newly_wrong": worse, "newly_correct": better, "not_in_baseline": len(unknown)}
        print(f"{p:7s} n={len(labels[p])} " + " ".join(f"{k}={counts[k]}" for k in ("correct", "missed", "wrong", "false_alarm", "crash"))
              + f"  p50 {summary['paths'][p]['latency']['p50_ms']} ms, p95 {summary['paths'][p]['latency']['p95_ms']} ms"
              + f"  vs baseline: {len(better)} newly correct, {len(worse)} newly wrong")
        for i in worse:
            it = by_id[i]
            print(f"  NEWLY WRONG {p} {i} [{labels[p][i]}] {it['text']!r} -> {outputs[i][p].get('text')!r} (want {it['expected']!r})", file=sys.stderr)
        if worse:
            failures.append(f"everyday {p}: {len(worse)} item(s) the baseline had correct are no longer correct")
        if unknown and not update:
            failures.append(f"everyday {p}: {len(unknown)} item(s) have no baseline label (record one with --update)")
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(f"peak memory {rss} MB; {summary['seconds']} s; summary {output / 'summary.json'}")
    if update:
        merged = {"about": "Per-item labels of the everyday set (benchmarks/everyday/items.jsonl) on the build that set the baseline; "
                           "scripts/everyday-batch.py gate fails when an item labelled correct here is not correct any more."}
        for p in sorted({*paths, *(k for k in baseline if k != "about")}):
            merged[p] = dict(sorted({**baseline.get(p, {}), **labels.get(p, {})}.items()))
        baseline_path.write_text(json.dumps(merged, indent=0) + "\n")
        print(f"Baseline written: {baseline_path}")
        return True
    perf = quality_gates.Gate("everyday")
    perf.failures = failures  # the per-item labels above are the quality baseline; benchmarks/baselines.json adds performance
    for p in paths:
        lat = summary["paths"][p]["latency"]
        perf.performance(p, {"p50_ms": lat["p50_ms"], "p95_ms": lat["p95_ms"], "max_rss_mb": rss})
    return perf.finish()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "score", "gate"])
    ap.add_argument("--items", type=Path, help="required for run and score; gate defaults to benchmarks/everyday/items.jsonl")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--outputs", type=Path)
    ap.add_argument("--native", type=Path, default=DEFAULT_NATIVE)
    ap.add_argument("--engine", type=Path, default=ROOT / "engine/target/release/libparzr_engine.dylib")
    ap.add_argument("--paths", help="default typing,deep,friendly,professional (run) or typing,deep (gate)")
    ap.add_argument("--baseline", type=Path)
    ap.add_argument("--save", type=Path)
    ap.add_argument("--output", type=Path, default=ROOT / "dist/qa/everyday", help="gate: where summary.json and outputs.jsonl go")
    ap.add_argument("--update", action="store_true", help="gate: write this run's labels as the new baseline (on purpose)")
    ap.add_argument("--deep-sample", type=int, default=0, help="gate: score Option+Space on a fixed sample of this many items (0: all)")
    a = ap.parse_args()
    if a.cmd == "gate":
        items = [json.loads(l) for l in open(a.items or EVERYDAY / "items.jsonl") if l.strip()]
        ok = gate(items, (a.paths or "typing,deep").split(","), a.native, a.engine, a.baseline or EVERYDAY / "baseline.json", a.output, a.update,
                  a.deep_sample)
        sys.exit(0 if ok else 1)
    if not a.items:
        ap.error("--items is required")
    a.paths = a.paths or "typing,deep,friendly,professional"
    items = [json.loads(l) for l in open(a.items) if l.strip()]
    if a.cmd == "run":
        run(items, a.out, a.native, a.engine, a.paths.split(","))
        return
    if a.outputs:
        outputs = [json.loads(l) for l in open(a.outputs)]
    else:
        tmp = Path(os.environ.get("TMPDIR", "/tmp")) / f"everyday-score-{os.getpid()}.jsonl"
        run(items, tmp, a.native, a.engine, ["typing", "deep"])
        outputs = [json.loads(l) for l in open(tmp)]
        tmp.unlink()
    score(items, outputs, a.baseline, a.save)


if __name__ == "__main__":
    main()
