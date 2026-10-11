#!/usr/bin/env python3
"""Tone rewrite evaluation: does each rewrite keep the meaning, and how long does it take?

Runs every sentence of benchmarks/tone/tone-eval.jsonl through the engine CLI in each tone mode
(chat sentences are sent as casual, as the app does for chat apps) and judges each answer
against the original sentence with the engine's own meaning check (examples/tone_judge.rs).
Writes per-item results and a summary to --output.

    cargo build --release --manifest-path engine/Cargo.toml --bin parzr-engine --example tone_judge
    PARZR_MODEL_RUNTIME=... PARZR_MODEL_PATH=... python3 scripts/run-tone-eval.py

An engine built before the `casual` field existed rejects it: pass --no-casual to measure one.
The judge is the same check the engine applies, so a sample of the answers should also be read
by a person; the summary lists the rewrites the judge rejected and a sample of those it kept.
"""
import argparse
import json
import pathlib
import statistics
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
MODES = ["professional", "friendly", "concise", "direct"]


def run_engine(engine, requests):
    process = subprocess.run([engine], input="".join(json.dumps(r) + "\n" for r in requests),
                             capture_output=True, text=True, check=False)
    lines = process.stdout.splitlines()
    if len(lines) != len(requests):
        sys.exit(f"engine answered {len(lines)} of {len(requests)} requests: {process.stderr[-2000:]}")
    return [json.loads(line) for line in lines]


def judge(binary, cases):
    process = subprocess.run([binary], input="".join(json.dumps(c) + "\n" for c in cases),
                             capture_output=True, text=True, check=True)
    return [json.loads(line) for line in process.stdout.splitlines()]


def has_emoji(text):
    return any(0x1F300 <= ord(c) <= 0x1FAFF or 0x2600 <= ord(c) <= 0x27BF for c in text)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--engine", default=str(ROOT / "engine/target/release/parzr-engine"))
    parser.add_argument("--judge", default=str(ROOT / "engine/target/release/examples/tone_judge"))
    parser.add_argument("--set", default=str(ROOT / "benchmarks/tone/tone-eval.jsonl"))
    parser.add_argument("--output", default=str(ROOT / "dist/qa/tone-eval"))
    parser.add_argument("--no-casual", action="store_true", help="omit the casual field (older engines)")
    parser.add_argument("--modes", default=",".join(MODES))
    parser.add_argument("--answers", help="judge the answers in an earlier results.jsonl instead of running the engine")
    args = parser.parse_args()
    items = [json.loads(line) for line in open(args.set, encoding="utf-8") if line.strip()]
    modes = args.modes.split(",")
    requests, keys = [], []
    for mode in modes:
        for item in items:
            request = {"text": item["text"], "mode": mode}
            if not args.no_casual:
                request["casual"] = item["kind"] == "chat"
            requests.append(request)
            keys.append((mode, item))
    if args.answers:
        earlier = {(r["mode"], r["id"]): r for r in map(json.loads, open(args.answers, encoding="utf-8"))}
        answers = [{"text": earlier[(m, i["id"])]["output"], "elapsed_ms": earlier[(m, i["id"])]["elapsed_ms"],
                    "edits": [{"original": a, "replacement": b} for a, b in earlier[(m, i["id"])]["edits"]],
                    **({"error": earlier[(m, i["id"])]["error"]} if earlier[(m, i["id"])]["error"] else {})} for m, i in keys]
    else:
        # Warm the model so the first case does not carry the load time.
        run_engine(args.engine, [{"text": "Warm up.", "mode": "friendly"}])
        answers = run_engine(args.engine, requests)
    cases = [{"mode": m, "source": i["text"], "output": a.get("text") or i["text"]} for (m, i), a in zip(keys, answers)]
    verdicts = judge(args.judge, cases)
    out = pathlib.Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for (mode, item), answer, verdict in zip(keys, answers, verdicts):
        rows.append({"id": item["id"], "kind": item["kind"], "typos": item["typos"], "mode": mode,
                     "input": item["text"], "output": answer.get("text"), "error": answer.get("error"),
                     "edits": [(e["original"], e["replacement"]) for e in answer.get("edits", [])],
                     "elapsed_ms": answer.get("elapsed_ms"), "keeps": verdict["keeps"], "reason": verdict["reason"]})
    with open(out / "results.jsonl", "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    lines = ["| Mode | Rewritten | Keeps meaning | Rewritten and keeps | Errors | Emoji | Median ms | p90 ms |", "|---|---|---|---|---|---|---|---|"]
    for mode in modes:
        group = [r for r in rows if r["mode"] == mode]
        changed = [r for r in group if r["output"] and r["output"] != r["input"]]
        keeps = [r for r in group if r["keeps"] and not r["error"]]
        both = [r for r in changed if r["keeps"]]
        times = sorted(r["elapsed_ms"] for r in group if r["elapsed_ms"] is not None)
        p90 = times[int(len(times) * 0.9) - 1] if times else 0
        emoji = sum(1 for r in group if r["output"] and has_emoji(r["output"]) and not has_emoji(r["input"]))
        lines.append(f"| {mode} | {len(changed)}/{len(group)} | {len(keeps)}/{len(group)} | {len(both)}/{len(changed) or 1} | "
                     f"{sum(1 for r in group if r['error'])} | {emoji} | {statistics.median(times) if times else 0:.0f} | {p90:.0f} |")
    lines.append("")
    lines.append("## Rejected by the meaning check")
    for r in rows:
        if not r["keeps"]:
            lines.append(f"- {r['mode']} {r['id']}: {r['input']!r} -> {r['output']!r} ({r['reason']})")
    summary = "\n".join(lines) + "\n"
    (out / "summary.md").write_text(summary, encoding="utf-8")
    print(summary)


if __name__ == "__main__":
    main()
