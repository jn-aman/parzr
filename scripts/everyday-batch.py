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

Build the harness once:
  swiftc -O -parse-as-library mac/Sources/ParzrCore/Models.swift mac/Sources/ParzrCore/WritingEngine.swift \\
    scripts/heldout-native.swift -o dist/batches/tools/native
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

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


class Engine:
    def __init__(self, native, dylib):
        env = dict(os.environ)
        env["PARZR_ENGINE_PATH"] = str(dylib)
        env.setdefault("PARZR_MODEL_RUNTIME", str(DEFAULT_RUNTIME))
        env.setdefault("PARZR_MODEL_PATH", str(DEFAULT_MODEL))
        self.proc = subprocess.Popen([str(native)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     env=env, text=True, bufsize=1)

    def ask(self, text, path, dialect=None):
        self.proc.stdin.write(json.dumps({"text": text, **PATHS[path], **({"dialect": dialect} if dialect else {})}) + "\n")
        self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        if not line:
            raise RuntimeError("engine exited")
        return json.loads(line)

    def check(self, text, path, dialect=None):
        start = time.time()
        result = self.ask(text, path, dialect)
        follow = 0
        while path == "typing" and "context.pending" in (result.get("warnings") or []) and follow < 3:
            time.sleep(0.9)
            result = self.ask(text, path, dialect)
            follow += 1
        return {"text": result.get("text"), "error": result.get("error"),
                "edits": [{k: e.get(k) for k in ("original", "replacement", "rule_id", "start_utf16")} for e in result.get("edits", [])],
                "warnings": result.get("warnings") or [], "followups": follow, "ms": round((time.time() - start) * 1000)}

    def close(self):
        self.proc.stdin.close()
        self.proc.wait(timeout=30)


def run(items, out_path, native, dylib, paths):
    done = set()
    if out_path.exists():
        done = {json.loads(l)["id"] for l in open(out_path)}
    engine = Engine(native, dylib)
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
    engine.close()


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "score"])
    ap.add_argument("--items", required=True, type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--outputs", type=Path)
    ap.add_argument("--native", type=Path, default=DEFAULT_NATIVE)
    ap.add_argument("--engine", type=Path, default=ROOT / "engine/target/release/libparzr_engine.dylib")
    ap.add_argument("--paths", default="typing,deep,friendly,professional")
    ap.add_argument("--baseline", type=Path)
    ap.add_argument("--save", type=Path)
    a = ap.parse_args()
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
