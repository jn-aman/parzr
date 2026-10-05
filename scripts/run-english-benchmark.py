#!/usr/bin/env python3
"""Run frozen synthetic fixtures against the packaged engine and native NLP path."""
import argparse
import collections
import csv
import datetime
import hashlib
import html
import json
import os
import pathlib
import platform
import statistics
import subprocess
import time
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def validate_edits(text, result):
    groups = collections.Counter(e["group_id"] for e in result["edits"] if e.get("group_id"))
    assert all(n == 2 for n in groups.values())
    data = text.encode("utf-16-le")
    last_end, last_start = 0, -1
    for edit in result["edits"]:
        start, end = edit["start_utf16"], edit["end_utf16"]
        assert 0 <= last_end <= start <= end <= len(data) // 2 and start != last_start
        assert data[start * 2:end * 2].decode("utf-16-le") == edit["original"]
        last_end, last_start = end, start
    for edit in reversed(result["edits"]):
        data = data[:edit["start_utf16"] * 2] + edit["replacement"].encode("utf-16-le") + data[edit["end_utf16"] * 2:]
    assert data.decode("utf-16-le") == result["text"]


def collect(cases, records):
    assert len(records) == len(cases)
    rows = []
    for case, record in zip(cases, records):
        assert case["id"] == record["id"]
        result = record.get("result", {})
        error = record.get("error")
        if not error:
            try:
                validate_edits(case["input"], result)
            except (AssertionError, KeyError, UnicodeError) as failure:
                error = f"Invalid edit plan: {type(failure).__name__}"
        actual = result.get("text", "")
        if error:
            status = "execution_error"
        elif case["kind"] == "clean_control":
            status = "clean_preserved" if actual == case["input"] else "clean_changed"
        elif actual == case["expected"]:
            status = "exact_match"
        elif actual == case["input"]:
            status = "no_suggestions"
        else:
            status = "changed_nonexact"
        rows.append({**case, "status": status, "actual": actual, "edits": result.get("edits", []), "wall_ms": record["wall_ms"], "version": result.get("version"), "error": error})
    return rows


def summarize(rows):
    timings = sorted(r["wall_ms"] for r in rows)
    counts = collections.Counter(r["status"] for r in rows)
    return {"total": len(rows), "counts": dict(counts), "median_ms": round(statistics.median(timings), 3), "p95_ms": round(timings[min(len(timings) - 1, int(len(timings) * .95))], 3), "max_ms": round(max(timings), 3)}


def report(output, runs, metadata, corpus, controls):
    sample_count = sum(r["kind"] == "corrupted_paragraph" for r in runs["native-nlp"])
    clean_count = sum(r["kind"] == "clean_control" for r in runs["native-nlp"])
    base_count = len({r.get("base_id") for r in runs["native-nlp"] if r.get("base_id")})
    summary = {"metadata": metadata, "runs": {name: summarize(rows) for name, rows in runs.items()}}
    for name, rows in runs.items():
        summary["runs"][name]["by_family"] = {key: summarize([r for r in rows if r["family"] == key and r["kind"] != "clean_control"]) for key in sorted({r["family"] for r in rows})}
        summary["runs"][name]["by_combination"] = {key: summarize([r for r in rows if r.get("combination") == key]) for key in sorted({r["combination"] for r in rows if "combination" in r})}
        (output / f"{name}-results.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
        with (output / f"{name}-results.csv").open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=["id", "kind", "family", "combination", "status", "input", "expected", "actual", "wall_ms", "edit_count", "error"])
            writer.writeheader()
            for r in rows:
                writer.writerow({**{k: r.get(k, "") for k in writer.fieldnames if k != "edit_count"}, "edit_count": len(r["edits"])})
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    lines = [f"# Parzr: {sample_count:,}-paragraph challenge results", "", f"{base_count} authored base paragraphs × 10 error combinations, plus {clean_count} clean controls. American English, Fix mode, empty personal dictionary. Every annotated mutation reconstructs its reference; every returned edit plan is validated.", "", "This is a synthetic challenge, not a representative estimate of all English grammar. Exact matching is strict: nonexact outputs require review and can include valid alternatives, partial fixes, or mistakes. Changes to clean text also require review. No human correctness score is claimed.", "", "| Path | Exact / 1,000 | Changed, nonexact | No suggestions | Errors / 1,100 | Clean preserved / 100 | Median ms | p95 ms |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for name, s in summary["runs"].items():
        c = s["counts"]
        lines.append(f"| {name} | {c.get('exact_match', 0)} | {c.get('changed_nonexact', 0)} | {c.get('no_suggestions', 0)} | {c.get('execution_error', 0)} | {c.get('clean_preserved', 0)} | {s['median_ms']} | {s['p95_ms']} |")
    lines += ["", "Native NLP uses the application's actual WritingEngine + Apple NaturalLanguage source with the packaged Rust dylib. This measures analysis and edit plans; it does not measure editor highlighting, clicks, permissions, or Undo. The native harness runs separately without opening or closing the user's app.", "", "## Native NLP by error combination", "", "| Combination | Exact | Changed, nonexact | No suggestions | Errors |", "|---|---:|---:|---:|---:|"]
    for key, s in summary["runs"]["native-nlp"]["by_combination"].items():
        c = s["counts"]
        lines.append(f"| {key} | {c.get('exact_match',0)} | {c.get('changed_nonexact',0)} | {c.get('no_suggestions',0)} | {c.get('execution_error',0)} |")
    lines += ["", "## Native NLP by grammar family", "", "Each family contains 50 corrupted paragraphs; grammar and non-grammar combinations are both included.", "", "| Family | Exact | Changed, nonexact | No suggestions |", "|---|---:|---:|---:|"]
    for key, s in summary["runs"]["native-nlp"]["by_family"].items():
        c = s["counts"]
        lines.append(f"| {key} | {c.get('exact_match',0)} | {c.get('changed_nonexact',0)} | {c.get('no_suggestions',0)} |")
    lines += ["", "## Reproducibility", "", "```json", json.dumps(metadata, indent=2), "```", "", "Full per-case input, expected correction, actual output and edits are in each results JSONL; CSV contains every input/reference/output. The HTML report embeds both runs and works offline."]
    (output / "report.md").write_text("\n".join(lines) + "\n")
    payload = json.dumps(runs, ensure_ascii=False).replace("<", "\\u003c")
    header = "".join(f"<p><strong>{html.escape(name)}</strong> · {s['counts'].get('exact_match',0)}/1,000 exact · {s['counts'].get('no_suggestions',0)} no suggestions · {s['counts'].get('clean_preserved',0)}/100 clean preserved</p>" for name, s in summary["runs"].items())
    page = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Parzr · English challenge</title><style>
body{background:#171b1c;color:#edf2ee;font:15px/1.6 system-ui;margin:0}main{max-width:1100px;margin:auto;padding:40px 24px}h1{font-size:36px;letter-spacing:-1px}p{color:#b2bdb7}strong{color:#99dbba}nav{display:flex;flex-wrap:wrap;gap:12px;position:sticky;top:0;background:#171b1c;padding:16px 0}input,select{background:#252b2c;color:#edf2ee;border:1px solid #46504b;border-radius:8px;padding:12px;font:inherit}input{flex:1;min-width:180px}article{padding:24px 0;border-bottom:1px solid #3b4540}h2{font-size:16px;margin:0}dl{display:grid;grid-template-columns:100px 1fr;gap:12px}dt{color:#99dbba}dd{margin:0;white-space:pre-wrap;overflow-wrap:anywhere}small{color:#abb5af}button{background:#99dbba;color:#171b1c;border:0;border-radius:7px;padding:10px 16px;cursor:pointer}button:disabled{opacity:.4;cursor:default}footer{display:flex;gap:20px;align-items:center;padding:24px 0}@media(max-width:600px){dl{grid-template-columns:1fr;gap:6px}dd{margin-bottom:14px}}
</style><main><h1>Parzr / 1,000 English challenges</h1>HEADER<p>100 base paragraphs × 10 combinations, plus 100 clean controls. Synthetic challenge only. Exact references are not the only valid English corrections. Nonexact changes and clean-text edits require review. This tests analysis, not editor UI.</p><nav><select id="run" aria-label="Analysis path"><option>native-nlp</option><option>rust-cli</option></select><select id="status" aria-label="Result status"><option value="">All results</option><option>exact_match</option><option>changed_nonexact</option><option>no_suggestions</option><option>clean_preserved</option><option>clean_changed</option><option>execution_error</option></select><input id="search" type="search" placeholder="Search paragraphs, family or ID" aria-label="Search results"></nav><p id="count" aria-live="polite"></p><section id="cases"></section><footer><button id="prev">Previous</button><span id="page"></span><button id="next">Next</button></footer></main><script>
const data=PAYLOAD;let page=0;const el=id=>document.getElementById(id);const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function render(){const query=el('search').value.toLowerCase();const rows=data[el('run').value].filter(r=>(!el('status').value||r.status===el('status').value)&&[r.id,r.family,r.input,r.actual].some(s=>s.toLowerCase().includes(query)));const pages=Math.max(1,Math.ceil(rows.length/25));page=Math.min(page,pages-1);el('count').textContent=rows.length+' matching cases';el('page').textContent=(page+1)+' / '+pages;el('prev').disabled=page===0;el('next').disabled=page===pages-1;el('cases').innerHTML=rows.slice(page*25,page*25+25).map(r=>'<article><h2>'+esc(r.id)+' · '+esc(r.status)+'</h2><small>'+esc(r.family)+' / '+esc(r.combination||'clean control')+' · '+r.wall_ms.toFixed(2)+' ms · '+r.edits.length+' edits</small><dl><dt>Input</dt><dd>'+esc(r.input)+'</dd><dt>Reference</dt><dd>'+esc(r.expected)+'</dd><dt>Actual</dt><dd>'+esc(r.actual)+'</dd></dl><details><summary>Returned edits'+(r.error?' / error':'')+'</summary><pre>'+esc(JSON.stringify(r.error||r.edits,null,2))+'</pre></details></article>').join('')}
['run','status','search'].forEach(id=>el(id).addEventListener('input',()=>{page=0;render()}));el('prev').onclick=()=>{page--;render()};el('next').onclick=()=>{page++;render()};render();</script></html>'''
    (output / "report.html").write_text(page.replace("Parzr / 1,000 English challenges", f"Parzr / {sample_count:,} English challenges").replace("100 base paragraphs × 10 combinations, plus 100 clean controls.", f"{base_count} base paragraphs × 10 combinations, plus {clean_count} clean controls.").replace("HEADER", header).replace("PAYLOAD", payload))
    corrupted = [r for r in runs["native-nlp"] if r["kind"] == "corrupted_paragraph"]
    (output / f"{sample_count}-wrong-paragraphs.txt").write_text("\n\n".join(f"{i}. [{r['id']}] {r['family']} / {r['combination']}\n{r['input']}" for i, r in enumerate(corrupted, 1)) + "\n")
    (output / f"{sample_count}-corrections-and-results.txt").write_text("\n\n".join(f"{i}. [{r['id']}] {r['status']}\nINPUT: {r['input']}\nREFERENCE: {r['expected']}\nPARZR: {r['actual']}" for i, r in enumerate(corrupted, 1)) + "\n")
    with zipfile.ZipFile(output / f"parzr-{sample_count}-tests-and-results.zip", "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in [f"{sample_count}-wrong-paragraphs.txt", f"{sample_count}-corrections-and-results.txt", "native-nlp-results.csv", "native-nlp-results.jsonl", "rust-cli-results.csv", "rust-cli-results.jsonl", "summary.json", "report.md", "report.html"]:
            archive.write(output / name, name)
        for path in [corpus, controls, corpus.with_name(corpus.stem + "-manifest.json")]:
            if path.exists(): archive.write(path, f"corpus/{path.name}")
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--app", type=pathlib.Path, default=ROOT / "dist/Parzr.app")
    parser.add_argument("--output", type=pathlib.Path, default=ROOT / "dist/qa/english-1000")
    parser.add_argument("--corpus", type=pathlib.Path, default=ROOT / "benchmarks/english-1000.jsonl")
    parser.add_argument("--controls", type=pathlib.Path, default=ROOT / "benchmarks/english-100-clean.jsonl")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    bad, clean = args.corpus, args.controls
    cases = read_jsonl(bad) + read_jsonl(clean)
    assert cases and len({c["id"] for c in cases}) == len(cases)
    for case in cases:
        if case["kind"] != "clean_control":
            validate_edits(case["input"], {"text": case["expected"], "edits": case["expected_edits"]})
    engine = args.app / "Contents/MacOS/parzr-engine"
    library = args.app / "Contents/Frameworks/libparzr_engine.dylib"
    sources = [ROOT / "mac/Sources/ParzrCore/Models.swift", ROOT / "mac/Sources/ParzrCore/WritingEngine.swift", ROOT / "scripts/benchmark-native.swift"]
    harness = args.output / "native-benchmark"
    subprocess.run(["swiftc", "-O", "-parse-as-library", *map(str, sources), "-o", str(harness)], check=True)
    combined = args.output / "inputs.jsonl"
    combined.write_text("".join(json.dumps(c, ensure_ascii=False) + "\n" for c in cases))
    runs, started = {}, time.time()
    with subprocess.Popen([str(engine)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True) as process:
        records = []
        for index, case in enumerate(cases):
            start = time.perf_counter()
            process.stdin.write(json.dumps({"text": case["input"], "mode": "fix", "dictionary": [], "dialect": "american", "sentence_start": True}) + "\n")
            process.stdin.flush()
            result = json.loads(process.stdout.readline())
            record = {"id": case["id"], "wall_ms": (time.perf_counter() - start) * 1000}
            record.update({"error": result["error"]} if "error" in result else {"result": result})
            records.append(record)
            if (index + 1) % 100 == 0:
                print(f"Packaged Rust engine: {index + 1}/{len(cases)}", flush=True)
        process.stdin.close()
        assert process.wait() == 0
    runs["rust-cli"] = collect(cases, records)
    environment = os.environ.copy()
    environment["PARZR_ENGINE_PATH"] = str(library.resolve())
    print("Running application NLP path...", flush=True)
    with (args.output / "native-raw.jsonl").open("w") as stream:
        subprocess.run([str(harness), str(combined)], env=environment, stdout=stream, check=True)
    runs["native-nlp"] = collect(cases, read_jsonl(args.output / "native-raw.jsonl"))
    metadata = {"utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "platform": platform.platform(), "mode": "fix", "dialect": "american", "dictionary": [], "corpus_sha256": sha(bad), "clean_controls_sha256": sha(clean), "packaged_engine_sha256": sha(engine), "packaged_library_sha256": sha(library), "native_sources_sha256": {str(p.relative_to(ROOT)): sha(p) for p in sources}, "engine_versions": sorted({r["version"] for rows in runs.values() for r in rows if r["version"]}), "total_seconds": round(time.time() - started, 2)}
    summary = report(args.output, runs, metadata, bad, clean)
    for name, s in summary["runs"].items():
        print(name, json.dumps({k: v for k, v in s.items() if not k.startswith("by_")}), flush=True)
    print(f"Full results: {args.output / 'report.html'}")


if __name__ == "__main__":
    main()
