#!/usr/bin/env python3
"""Measure how the engine treats names: damaged names, real-typo recall and engine errors.

Streams benchmarks/names/corpus.jsonl (synthetic sentences, no personal data) through the
command-line engine on the automatic path and fails when a threshold in
benchmarks/names/thresholds.json is exceeded. A name is damaged when an edit overlapping it
changes letters or word boundaries; case-only and punctuation-only edits are allowed.
--baseline also compares the run with the "names" suite in benchmarks/baselines.json: typo recall more than
0.5 points lower, more than 2 extra damaged names (overall, lowercase or held-out), or p50/p95 latency or
peak engine memory above 1.5x the baseline fails it (scripts/quality_gates.py).
"""
import argparse, collections, json, pathlib, re, subprocess, sys, time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import quality_gates  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--engine', default=str(ROOT/'engine/target/release/parzr-engine'))
parser.add_argument('--report', default=str(ROOT/'dist/qa/names/report.json'))
parser.add_argument('--no-check', action='store_true', help='Report only; do not enforce thresholds')
parser.add_argument('--gec', action='store_true', help='Also run the on-device grammar model (needs its runtime and files; CI leaves it off)')
parser.add_argument('--baseline', action='store_true', help='Also gate against the "names" suite in benchmarks/baselines.json')
args = parser.parse_args()

rows = [json.loads(line) for line in (ROOT/'benchmarks/names/corpus.jsonl').open()]
# Held-out names appear in no shipped list and not in the corpus: they measure generalisation.
rows += [json.loads(line) for line in (ROOT/'benchmarks/names/heldout.jsonl').open()]
limits = json.loads((ROOT/'benchmarks/names/thresholds.json').read_text())

def letters(s): return ''.join(c for c in s if c.isalnum()).lower()
def harmful(edit):
    # Letters or word boundaries changed; a pure case or punctuation change is fine.
    o, r = edit['original'], edit['replacement']
    return letters(o) != letters(r) or len(r.split()) != len(o.split())
def touches(edit, spans):
    s, e = edit['start_utf16'], edit['end_utf16']
    return any((s < b and e > a) if s != e else a < s < b for a, b, _ in spans)

engine = subprocess.Popen([args.engine], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, env=quality_gates.engine_env())
latency = []
stats = collections.defaultdict(lambda: [0, 0])  # key -> [damaged, total]
fixed = controls = errors = 0
worst = []
for row in rows:
    started = time.perf_counter()
    engine.stdin.write(json.dumps({'text': row['text'], **({'gec': True} if args.gec else {})}) + '\n'); engine.stdin.flush()
    out = json.loads(engine.stdout.readline())
    latency.append((time.perf_counter() - started) * 1000)
    if 'error' in out:
        errors += 1; worst.append({'id': row['id'], 'text': row['text'], 'error': out['error']}); continue
    if row['set'] == 'control':
        controls += 1
        text = out['text']
        fixed += bool(re.search(r'\b' + re.escape(row['fix']) + r'\b', text, re.I)) and not re.search(r'\b' + re.escape(row['name']) + r'\b', text)
        continue
    bad = [e for e in out['edits'] if touches(e, row['spans']) and harmful(e)]
    keys = ('heldout', 'context:heldout:' + row['context']) if row['culture'] == 'heldout' else ('all', 'case:' + row['case'], 'context:' + row['context'], 'culture:' + row['culture'])
    for key in keys:
        stats[key][0] += bool(bad); stats[key][1] += 1
    if bad and len(worst) < 200:
        worst.append({'id': row['id'], 'text': row['text'], 'output': out['text'], 'rules': sorted({e['rule_id'] for e in bad})})
engine.stdin.close(); rss = quality_gates.reap(engine)

rate = lambda key: stats[key][0] / stats[key][1] if stats[key][1] else 0.0
report = {
    'damaged_all': rate('all'), 'damaged_lowercase': rate('case:lower'), 'damaged_heldout': rate('heldout'),
    'control_recall': fixed / controls if controls else 0.0, 'errors': errors,
    'control_fixed': fixed, 'controls': controls, 'machine': quality_gates.machine(),
    'latency': quality_gates.latency(latency), 'max_rss_mb': rss,
    'breakdown': {k: {'damaged': d, 'total': t, 'rate': round(d / t, 4)} for k, (d, t) in sorted(stats.items())},
    'examples': worst,
}
path = pathlib.Path(args.report); path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
print(f"names damaged: {report['damaged_all']:.2%} overall, {report['damaged_lowercase']:.2%} lowercase, {report['damaged_heldout']:.2%} held-out; "
      f"typo recall {report['control_recall']:.2%}; engine errors {errors}; report {path}")

failures = []
if report['damaged_all'] > limits['max_damaged_all']: failures.append(f"overall damage above {limits['max_damaged_all']:.2%}")
if report['damaged_lowercase'] > limits['max_damaged_lowercase']: failures.append(f"lowercase damage above {limits['max_damaged_lowercase']:.2%}")
if report['damaged_heldout'] > limits['max_damaged_heldout']: failures.append(f"held-out damage above {limits['max_damaged_heldout']:.2%}")
if report['control_recall'] < limits['min_control_recall']: failures.append(f"typo recall below {limits['min_control_recall']:.2%}")
if errors > limits['max_errors']: failures.append(f"engine errors above {limits['max_errors']}")
if failures and not args.no_check:
    sys.exit('Name benchmark failed: ' + '; '.join(failures))
if args.baseline:
    gate = quality_gates.Gate('names')
    base = gate.base or {}
    if base:
        gate.rate('typo recall', fixed, controls, base['control_fixed'], base['controls'])
        for key in ('all', 'case:lower', 'heldout'):
            gate.count(f'damaged names ({key})', stats[key][0], base['damaged'][key])
        gate.count('engine errors', errors, base.get('errors', 0))
        gate.performance('engine', {'p50_ms': report['latency']['p50_ms'], 'p95_ms': report['latency']['p95_ms'], 'max_rss_mb': rss})
    if not gate.finish():
        sys.exit(1)
