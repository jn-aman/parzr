#!/usr/bin/env python3
"""Precision, recall and false alarms of the typing-time slip checker on DEV data (engine/src/slips.rs).

Inputs:
  --items   the evaluation items: {"id", "source", "input", "spans": [{"start", "end", "original", "fix"}]} with character
            offsets; clean items have no spans. Build them with --build from dev data only (below).
  scored    the engine's per-window gains: PARZR_SLIPS_DEV=items.jsonl:scored.jsonl cargo test --release --lib slips_dev -- --ignored
  --model   optional: the writing model's gains for the same swaps (the bake-off's qwen file or the engine's calibrate
            output joined by window), to choose CONFIRM, the explicit check's confirmation margin.

Decision rule = confusion::choose_with: per word, the best (gain - c * slip cost) must reach T and beat the next candidate
by the margin (0.5); then the single strongest word per window. A flag is correct when it hits a gold span with its fix
(case- and apostrophe-insensitive). Precision counts every flag on error and clean items; false alarms are flags on clean
items, per clean sentence and per clean item. "In scope" spans are those whose fix the candidate generator proposes.

Thresholds are chosen on half A of the items (by a hash of the id) and reported on half B, and the other way round, so the
reported numbers are not tuned on themselves; then the shipped operating point is reported on all of DEV.

--build OUT writes the items from DEV sources only: benchmarks/typo-fuzz/dev*.jsonl, benchmarks/english-{100,200}-clean.jsonl,
the dev split of benchmarks/heldout (selected by the input hash of scripts/run-heldout-benchmark.py; test items are skipped
unread past their hash), the everyday regression set and the bake-off's probe slips when present. NEVER point this at a
test split.

    python3 scripts/eval-slips.py --items dist/slips-eval/items.jsonl dist/slips-eval/mlm.jsonl [--model qwen.jsonl]
"""
import argparse, hashlib, json, pathlib
from collections import defaultdict

ERR = {"heldout-dev", "fuzz-rw", "regression", "probe"}
MARGIN = 0.5


def norm(w):
    return w.lower().replace("’", "'")


def half(item_id):
    return "A" if int(hashlib.sha256(item_id.encode()).hexdigest(), 16) % 2 == 0 else "B"


def choose(swaps, T, c, margin=MARGIN):
    words = defaultdict(list)
    for s0, s1, w, cand, cost, g in swaps:
        if g is not None:
            words[(s0, s1)].append((g - c * cost, s0, s1, cand, cost))
    best = None
    for v in words.values():
        v.sort(reverse=True)
        gain = v[0][0]
        nxt = max(v[1][0], 0.0) if len(v) > 1 else 0.0
        if gain >= T and gain - nxt >= margin and (best is None or gain > best[0]):
            best = v[0]
    return best


def prepare(items, scored, model=None):
    out = []
    for c in scored:
        it = items[c["id"]]
        raw = it["input"]
        byte = lambda ch: len(raw[:ch].encode())
        gold = {(byte(s["start"]), byte(s["end"])): norm(s["fix"]) for s in it["spans"]}
        cands = defaultdict(set)
        for row in c["rows"]:
            for s in row["swaps"]:
                cands[(s[0], s[1])].add(norm(s[3]))
        in_scope = {k for k, f in gold.items() if f in cands.get(k, set())}
        if it["source"] == "regression" and not any(k in cands for k in gold):
            continue  # non-word typos only: another layer's job
        out.append({"id": c["id"], "source": it["source"], "half": half(c["id"]), "gold": gold, "in_scope": in_scope,
                    "sentences": c["sentences"], "rows": c["rows"], "clean": not gold, "input": raw,
                    "model": (model or {}).get(c["id"], {})})
    return out


def confirmed(d, ch, T_model, confirm):
    """The explicit check: the writing model's own verdict, else the slip checker's if the model's gain clears `confirm`."""
    g = d["model"].get((ch[1], ch[2], ch[3]))
    return g is not None and g - ch[4] >= confirm


def evaluate(data, T, c, which=None, confirm=None):
    tp = flags = clean_flags = clean_sents = clean_items = clean_items_flagged = gold_n = scope_n = 0
    per = defaultdict(lambda: [0, 0, 0])
    hits = []
    for d in data:
        if which and d["half"] != which:
            continue
        chosen = [ch for ch in (choose(r["swaps"], T, c) for r in d["rows"]) if ch]
        if confirm is not None:
            chosen = [ch for ch in chosen if confirmed(d, ch, None, confirm)]
        if d["clean"]:
            clean_sents += d["sentences"]; clean_items += 1
            clean_flags += len(chosen); flags += len(chosen); clean_items_flagged += bool(chosen)
            if chosen:
                hits.append((d["id"], "FA", [(d["input"].encode()[x[1]:x[2]].decode(), x[3], round(x[0], 2)) for x in chosen]))
            continue
        gold_n += len(d["gold"]); scope_n += len(d["in_scope"])
        per[d["source"]][1] += len(d["gold"]); per[d["source"]][2] += len(d["in_scope"])
        for ch in chosen:
            flags += 1
            if d["gold"].get((ch[1], ch[2])) == norm(ch[3]):
                tp += 1; per[d["source"]][0] += 1
            else:
                hits.append((d["id"], "wrong", (d["input"].encode()[ch[1]:ch[2]].decode(), ch[3], round(ch[0], 2))))
    return {"T": T, "c": c, "confirm": confirm, "tp": tp, "flags": flags, "precision": tp / flags if flags else 1.0,
            "recall": tp / gold_n if gold_n else 0.0, "in_scope_recall": tp / scope_n if scope_n else 0.0,
            "fa_per_1000_sentences": 1000 * clean_flags / max(clean_sents, 1), "clean_flags": clean_flags,
            "clean_sentences": clean_sents, "clean_items": clean_items, "clean_items_flagged": clean_items_flagged,
            "fa_item_rate": clean_items_flagged / max(clean_items, 1), "gold": gold_n, "in_scope": scope_n,
            "per_source": {k: {"tp": v[0], "gold": v[1], "in_scope": v[2]} for k, v in sorted(per.items())}, "errors": hits}


def f05(m):
    p, r = m["precision"], m["recall"]
    return 1.25 * p * r / (0.25 * p + r) if p + r else 0.0


def tune(data, which, costs, grid):
    best = {}
    for c in costs:
        for T in grid:
            m = evaluate(data, T, c, which)
            rules = {"f05": f05(m), "fa1": m["recall"] if m["fa_per_1000_sentences"] <= 1.0 else -1,
                     "p97": m["recall"] if m["precision"] >= 0.97 and m["flags"] else -1}
            for k, v in rules.items():
                if v >= 0 and (k not in best or v > best[k][0]):
                    best[k] = (v, T, c)
    return best


def fmt(m):
    return (f"P {m['precision']:.3f}  R {m['recall']:.3f}  in-scope R {m['in_scope_recall']:.3f}  "
            f"FA {m['fa_per_1000_sentences']:.2f}/1k sentences, {m['fa_item_rate']:.2%} of clean items "
            f"(tp {m['tp']}/{m['gold']}, in scope {m['in_scope']}, flags {m['flags']}, clean flags {m['clean_flags']}/{m['clean_sentences']} sentences)")


def load_model_gains(path, items):
    """{id: {(s0, s1, candidate): gain}} from a scored file in the same format (the bake-off's qwen gains)."""
    out = defaultdict(dict)
    for l in open(path, encoding="utf-8"):
        c = json.loads(l)
        for r in c["rows"]:
            for s in r["swaps"]:
                if s[5] is not None:
                    out[c["id"]][(s[0], s[1], s[3])] = s[5]
    return out


def build(out):
    root = pathlib.Path(__file__).resolve().parent.parent
    load = lambda p: [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
    split = lambda item: "test" if int(hashlib.sha256(item["input"].encode()).hexdigest(), 16) % 10 < 3 else "dev"
    rows = []
    for r in load(root/"benchmarks/heldout/errors.jsonl"):
        if split(r) == "dev" and r["category"] in ("real_word", "word_choice_usage", "contractions"):
            rows.append({"id": r["id"], "source": "heldout-dev", "input": r["input"], "spans": r["spans"]})
    for r in load(root/"benchmarks/heldout/clean.jsonl"):
        if split(r) == "dev":
            rows.append({"id": r["id"], "source": "heldout-clean", "input": r["input"], "spans": []})
    for r in load(root/"benchmarks/typo-fuzz/dev.jsonl"):
        if r["word_class"] == "real-word":
            rows.append({"id": r["id"], "source": "fuzz-rw", "input": r["input"], "spans": r["spans"]})
    for r in load(root/"benchmarks/typo-fuzz/dev-clean.jsonl"):
        rows.append({"id": r["id"], "source": "fuzz-clean", "input": r["input"], "spans": []})
    for name in ("english-100-clean.jsonl", "english-200-clean.jsonl"):
        for r in load(root/"benchmarks"/name):
            rows.append({"id": r["id"] + "@" + name.split("-")[1], "source": "english-clean", "input": r["input"], "spans": []})
    with open(out, "w", encoding="utf-8") as f:
        for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"{len(rows)} dev items in {out}")


def build_prose(out, words):
    """A precision probe of published English prose on this Mac (clean text, false alarms only): sentences of the macOS
    man pages' prose, the Python standard library's docstrings and this repository's docs, up to `words` words."""
    import ast, re, subprocess, sys, sysconfig
    root = pathlib.Path(__file__).resolve().parent.parent
    sentence = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")
    def keep(s):
        s = " ".join(s.split())
        w = s.split()
        return (6 <= len(w) <= 50 and s[0].isupper() and s[-1] in ".!?" and not re.search(r"[{}<>=_\\`$#|\[\]@*/~^]|\(\)|--|\.\w|::", s)
                and sum(c.isalpha() or c in " ,.;:'!?()-\"" for c in s) / len(s) > 0.97 and not any(t.isupper() and len(t) > 3 for t in w)), s
    texts = []
    for i, page in enumerate(sorted(pathlib.Path("/usr/share/man/man1").glob("*.1"))):
        r = subprocess.run(["mandoc", "-T", "utf8", str(page)], capture_output=True, text=True, errors="replace")
        if r.returncode: continue
        plain = re.sub(r".\x08", "", r.stdout)
        paras = re.split(r"\n\s*\n", plain)
        texts += [("man:" + page.stem, p) for p in paras if p.startswith("     ") and not p.startswith("       -")]
    stdlib = pathlib.Path(sysconfig.get_paths()["stdlib"])
    for path in sorted(stdlib.glob("*.py")):
        try: tree = ast.parse(path.read_text(errors="replace"))
        except (SyntaxError, ValueError): continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)) and (doc := ast.get_docstring(node)):
                texts += [("py:" + path.stem, p) for p in re.split(r"\n\s*\n", doc)]
    for path in sorted((root/"docs").glob("*.md")) + [root/"README.md", root/"PRODUCT.md"]:
        paras = re.split(r"\n\s*\n", path.read_text())
        texts += [("doc:" + path.stem, p) for p in paras if not p.lstrip().startswith(("|", "#", "```", "-", "*", ">", "<", "!["))]
    seen, rows, total = set(), [], 0
    for source, para in texts:
        for s in sentence.split(" ".join(para.split())):
            ok, s = keep(s)
            if ok and s not in seen:
                seen.add(s); rows.append({"id": f"prose-{len(rows):05d}", "source": "prose-clean", "origin": source, "input": s, "spans": []})
                total += len(s.split())
    # A fixed, spread-out sample when there is more than asked for.
    rows.sort(key=lambda r: hashlib.sha256(r["input"].encode()).hexdigest())
    picked, n = [], 0
    for r in rows:
        if n >= words: break
        picked.append(r); n += len(r["input"].split())
    with open(out, "w", encoding="utf-8") as f:
        for r in picked: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"{len(picked)} sentences, {n} words (of {total} available) in {out}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--items")
    ap.add_argument("--build")
    ap.add_argument("--build-prose", help="write a precision probe of published prose (clean sentences) here")
    ap.add_argument("--words", type=int, default=300_000)
    ap.add_argument("--model", help="the writing model's gains for the same swaps")
    ap.add_argument("--ship", type=float, nargs=2, metavar=("T", "C"), help="the operating point to report on all of DEV")
    ap.add_argument("--confirm", type=float, nargs="*", default=[0.0, 1.0, 2.0, 3.0, 4.0])
    ap.add_argument("--no-tune", action="store_true", help="skip the half-A/half-B threshold search (clean-only probes)")
    ap.add_argument("--out")
    ap.add_argument("scored", nargs="*")
    a = ap.parse_args()
    if a.build: return build(a.build)
    if a.build_prose: return build_prose(a.build_prose, a.words)
    items = {json.loads(l)["id"]: json.loads(l) for l in open(a.items, encoding="utf-8")}
    model = load_model_gains(a.model, items) if a.model else None
    report = {}
    for path in a.scored:
        scored = [json.loads(l) for l in open(path, encoding="utf-8")]
        data = prepare(items, scored, model)
        grid = [round(x * 0.25, 2) for x in range(0, 121)]  # 0 .. 30 nats
        rep = {}
        print(f"== {pathlib.Path(path).name}: {len(data)} items, {sum(d['clean'] for d in data)} clean")
        for tune_half, test_half in () if a.no_tune else (("A", "B"), ("B", "A")):
            best = tune(data, tune_half, (0.0, 0.5, 1.0), grid)
            for op, (_, T, c) in sorted(best.items()):
                m = evaluate(data, T, c, test_half)
                rep[f"tune{tune_half}-{op}"] = {"T": T, "c": c, "test": m}
                print(f"  tune {tune_half} {op:4} T={T:5.2f} c={c}: test {test_half}: {fmt(m)}")
        if a.ship:
            T, c = a.ship
            m = evaluate(data, T, c)
            rep["ship"] = m
            print(f"  shipped T={T} c={c}, all DEV: {fmt(m)}")
            for s, v in m["per_source"].items(): print(f"    {s}: {v['tp']}/{v['gold']} (in scope {v['in_scope']})")
            if model:
                for confirm in a.confirm:
                    mc = evaluate(data, T, c, confirm=confirm)
                    rep[f"confirm{confirm}"] = mc
                    print(f"  explicit, slip swaps confirmed by the writing model at {confirm}: {fmt(mc)}")
            fa = [e for e in m["errors"] if e[1] == "FA"]
            wrong = [e for e in m["errors"] if e[1] == "wrong"]
            print(f"  false alarms on clean items ({len(fa)}):")
            for e in fa[:40]: print("   ", e[0], e[2])
            print(f"  wrong flags on error items ({len(wrong)}), first 25:")
            for e in wrong[:25]: print("   ", e[0], e[2])
        ms = sorted(r["ms"] for d in data for r in d["rows"])
        if ms:
            rep["latency_ms"] = {"windows": len(ms), "p50": ms[len(ms) // 2], "p95": ms[int(len(ms) * 0.95)]}
            print(f"  latency per window (sentence + the one before): p50 {ms[len(ms) // 2]:.1f} ms, p95 {ms[int(len(ms) * 0.95)]:.1f} ms over {len(ms)} windows")
        report[pathlib.Path(path).stem] = rep
    if a.out:
        with open(a.out, "w") as f: json.dump(report, f, indent=1, default=str)


if __name__ == "__main__":
    main()
