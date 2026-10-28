#!/usr/bin/env python3
"""Score the engine on the held-out error set (benchmarks/heldout), per category and per layer.

Layers: rules (what runs while you type), gec (rules + Smart grammar), deep (Option+Space Fix: rules,
Smart grammar and the Qwen model). Each layer is one long-lived parzr-engine process fed one JSON line
per item. For every error item it records:
  fixed    the output equals the reference or an accepted alternative
  flagged  some edit touches every error span (the writer is at least told)
  wrong    the text changed, but not to an accepted correction
  missed   no edit touches an error span
and for every clean item whether anything changed (a false alarm).

usage: run-heldout-benchmark.py [--engine PATH] [--layers rules,gec,deep] [--split dev|test|all] [--limit N] [--output DIR]
                                [--min-fix-rate LAYER=RATE ...] [--max-false-alarm-rate LAYER=RATE ...] [--baseline SUITE]

--engine takes the parzr-engine CLI or scripts/heldout-native.swift built with swiftc (the app's path, with Apple
NaturalLanguage hints; see benchmarks/README.md). The gate flags make the run exit 1 when a layer falls below a fix
rate or above a false-alarm rate, so CI can block a release that makes checking worse. --baseline SUITE compares the
run with that suite's entry in benchmarks/baselines.json (scripts/quality_gates.py): a fix rate more than 0.5 points
lower, more than 2 extra false alarms, or p50/p95 latency or peak engine memory above 1.5x the baseline fails it.
Every layer's summary records p50/p95 latency per check and the engine's peak resident memory.

Test sets are sealed: --split test (also --split all on the held-out set, and a typo-fuzz test corpus, test*.jsonl) runs only on CI or with
PARZR_RELEASE_GATE=1, and then writes totals and category counts only, never an item's input or output.
"""
import argparse, collections, hashlib, json, pathlib, subprocess, sys, time, unicodedata

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import quality_gates  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_ENGINE = '/Applications/Parzr.app/Contents/MacOS/parzr-engine'
LAYERS = {'rules': {}, 'gec': {'gec': True}, 'deep': {'gec': True, 'deep': True}}


def norm(s):
    # Curly and straight quotes are both correct; compare them as one.
    s = unicodedata.normalize('NFC', s).replace('’', "'").replace('‘', "'").replace('“', '"').replace('”', '"')
    return ' '.join(s.split())


def load(path):
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def split_of(item):
    # A fixed 30% of items (by input-text hash, stable when the corpus is rebuilt and ids shift) is the test split: fixes are made looking only at dev, test is the score.
    return 'test' if int(hashlib.sha256(item['input'].encode()).hexdigest(), 16) % 10 < 3 else 'dev'


# A typing check (the gec layer) scores short-word swaps within the typing budget and answers "context.pending" when a
# sentence needs the model longer; the app then looks again, three times 0.9 s apart. The runner does the same, so a
# layer scores what the writer ends up with on a fast Mac and on a loaded CI runner alike (on a Mac the first answer
# settles nearly every item: main's sealed gec count moved between 518 and 521 across identical CI runs before this).
# Latency records the first answer, what the writer waits for. The follow-ups are capped per layer so a runner that
# never settles cannot stall the job; the summary records how many follow-ups a layer took.
FOLLOW_UPS, FOLLOW_INTERVAL, FOLLOW_CAP_S = 3, 0.9, 300


class Engine:
    def __init__(self, path, extra):
        self.extra, self.ms, self.follow_ups, self.follow_s = extra, [], 0, 0.0
        self.proc = subprocess.Popen([path], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, encoding='utf-8', bufsize=1,
                                     env=quality_gates.engine_env())

    def ask(self, req):
        self.proc.stdin.write(json.dumps(req, ensure_ascii=False) + '\n'); self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        if not line:
            raise RuntimeError('engine exited')
        return json.loads(line)

    def check(self, item):
        req = {'text': item['input'], **self.extra}
        if item.get('dialect'):
            req['dialect'] = item['dialect']
        started = time.perf_counter()
        resp = self.ask(req)
        self.ms.append((time.perf_counter() - started) * 1000)
        follow = 0
        while 'context.pending' in (resp.get('warnings') or []) and follow < FOLLOW_UPS and self.follow_s < FOLLOW_CAP_S:
            t = time.perf_counter()
            time.sleep(FOLLOW_INTERVAL)
            resp = self.ask(req)
            self.follow_s += time.perf_counter() - t
            follow += 1
        self.follow_ups += follow
        return resp

    def close(self):
        """Ends the engine; returns its peak resident memory in MB."""
        self.proc.stdin.close()
        return quality_gates.reap(self.proc)


def touches(edits, span):
    s, e = span['start'], max(span['end'], span['start'] + 1)
    return any(ed['start_utf16'] < e + 1 and ed['end_utf16'] + 1 > s for ed in edits)


def score(item, resp):
    out = resp.get('text', item['input'])
    edits = resp.get('edits', [])
    accepted = {norm(item['reference']), *(norm(a) for a in item.get('alternatives', []))}
    if norm(out) in accepted:
        return 'fixed', out, edits
    if item.get('spans') and all(touches(edits, sp) for sp in item['spans']):
        return 'flagged', out, edits
    if any(touches(edits, sp) for sp in item.get('spans', [])) or norm(out) != norm(item['input']):
        return 'wrong', out, edits
    return 'missed', out, edits


def main():
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--engine', default=DEFAULT_ENGINE)
    p.add_argument('--corpus', type=pathlib.Path, default=ROOT / 'benchmarks/heldout/errors.jsonl')
    p.add_argument('--clean', type=pathlib.Path, default=ROOT / 'benchmarks/heldout/clean.jsonl')
    p.add_argument('--layers', default='rules,gec,deep')
    p.add_argument('--limit', type=int, default=0)
    p.add_argument('--split', choices=['dev', 'test', 'all'], default='dev', help='dev while fixing; test only to report')
    p.add_argument('--min-fix-rate', action='append', default=[], metavar='LAYER=RATE')
    p.add_argument('--max-false-alarm-rate', action='append', default=[], metavar='LAYER=RATE')
    p.add_argument('--output', type=pathlib.Path, default=ROOT / 'dist/qa/heldout')
    p.add_argument('--baseline', metavar='SUITE', help='gate against this suite in benchmarks/baselines.json (heldout-test, typo-fuzz-test)')
    a = p.parse_args()
    # The held-out set with --split all holds its test split too.
    heldout = any(path.resolve().is_relative_to(ROOT / 'benchmarks/heldout') for path in (a.corpus, a.clean))
    sealed = a.split == 'test' or a.corpus.name.startswith('test') or (a.split == 'all' and heldout)
    if sealed and not quality_gates.release_gate():
        sys.exit(f'{a.corpus.name} ({a.split}) is a sealed test set: it is scored on CI (or with PARZR_RELEASE_GATE=1 for a '
                 'release gate) and reports totals only. Fix against --split dev.')
    errors, clean = load(a.corpus), load(a.clean)
    if a.split != 'all':
        errors, clean = [i for i in errors if split_of(i) == a.split], [i for i in clean if split_of(i) == a.split]
    if a.limit:
        errors, clean = errors[:a.limit], clean[:a.limit]
    a.output.mkdir(parents=True, exist_ok=True)
    summary = {'engine': a.engine, 'corpus': a.corpus.name, 'split': a.split, 'sealed': sealed, 'machine': quality_gates.machine(),
               'errors': len(errors), 'clean': len(clean), 'layers': {}}
    if sealed:
        stale = sorted(p.name for p in a.output.glob('*-results.jsonl')) + sorted(p.name for p in a.output.glob('*-false-alarms.jsonl'))
        if stale:
            print(f'note: {a.output} still holds per-item files from an earlier unsealed run ({", ".join(stale)}); this run writes none', file=sys.stderr)
    for layer in a.layers.split(','):
        eng, t0 = Engine(a.engine, LAYERS[layer]), time.time()
        by_cat = collections.defaultdict(collections.Counter)
        rows = []
        for i, item in enumerate(errors):
            verdict, out, edits = score(item, eng.check(item))
            by_cat[item['category']][verdict] += 1; by_cat[item['category']]['n'] += 1
            by_cat[item['category'] + '/' + item.get('subcategory', '')][verdict] += 1
            by_cat[item['category'] + '/' + item.get('subcategory', '')]['n'] += 1
            rows.append({'id': item['id'], 'category': item['category'], 'subcategory': item.get('subcategory'), 'verdict': verdict,
                         'input': item['input'], 'reference': item['reference'], 'output': out, 'rules': [e.get('rule_id') for e in edits]})
            if (i + 1) % 200 == 0:
                print(f'  {layer}: {i + 1}/{len(errors)}', file=sys.stderr)
        false_alarms = []
        for item in clean:
            resp = eng.check(item)
            if norm(resp.get('text', item['input'])) != norm(item['input']) or resp.get('edits'):
                false_alarms.append({'id': item['id'], 'input': item['input'], 'output': resp.get('text'), 'rules': [e.get('rule_id') for e in resp.get('edits', [])]})
        rss = eng.close()
        total = collections.Counter(); [total.update({k: v for k, v in c.items()}) for k, c in by_cat.items() if '/' not in k]
        summary['layers'][layer] = {
            'seconds': round(time.time() - t0, 1),
            'follow_ups': eng.follow_ups, 'follow_up_seconds': round(eng.follow_s, 1),
            'fixed': total['fixed'], 'flagged': total['flagged'], 'wrong': total['wrong'], 'missed': total['missed'],
            'fix_rate': round(total['fixed'] / max(1, len(errors)), 4),
            'catch_rate': round((total['fixed'] + total['flagged']) / max(1, len(errors)), 4),
            'false_alarm_rate': round(len(false_alarms) / max(1, len(clean)), 4), 'false_alarms': len(false_alarms),
            'latency': quality_gates.latency(eng.ms), 'max_rss_mb': rss,
            'categories': {k: dict(c) for k, c in sorted(by_cat.items())},
        }
        if not sealed:
            with open(a.output / f'{layer}-results.jsonl', 'w') as f:
                f.writelines(json.dumps(r, ensure_ascii=False) + '\n' for r in rows)
            with open(a.output / f'{layer}-false-alarms.jsonl', 'w') as f:
                f.writelines(json.dumps(r, ensure_ascii=False) + '\n' for r in false_alarms)
        s = summary['layers'][layer]
        print(f"{layer}: fixed {s['fix_rate']:.1%}, caught {s['catch_rate']:.1%}, false alarms {s['false_alarm_rate']:.1%} ({s['seconds']}s; "
              f"p50 {s['latency']['p50_ms']} ms, p95 {s['latency']['p95_ms']} ms, peak memory {rss} MB)")
    (a.output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    lines = ['| Category | n | ' + ' | '.join(f'{l} fixed | {l} caught' for l in summary['layers']) + ' |',
             '| --- | --- | ' + ' | '.join('--- | ---' for _ in summary['layers']) + ' |']
    cats = sorted({k for s in summary['layers'].values() for k in s['categories'] if '/' not in k})
    for c in cats:
        cells = []
        for s in summary['layers'].values():
            d = s['categories'].get(c, {}); n = d.get('n', 0) or 1
            cells.append(f"{d.get('fixed', 0) / n:.0%} | {(d.get('fixed', 0) + d.get('flagged', 0)) / n:.0%}")
        lines.append(f"| {c} | {summary['layers'][next(iter(summary['layers']))]['categories'][c]['n']} | " + ' | '.join(cells) + ' |')
    (a.output / 'summary.md').write_text('\n'.join(lines) + '\n')
    print(f'Wrote {a.output}/summary.md')
    failed = []
    for flag, key, worse in (('min_fix_rate', 'fix_rate', lambda v, t: v < t), ('max_false_alarm_rate', 'false_alarm_rate', lambda v, t: v > t)):
        for spec in getattr(a, flag):
            layer, threshold = spec.split('=')
            value = summary['layers'][layer][key]
            if worse(value, float(threshold)):
                failed.append(f'{layer} {key} {value:.4f} is worse than the gate {threshold}')
    for f in failed:
        print(f'GATE FAILED: {f}', file=sys.stderr)
    passed = True
    if a.baseline:
        gate = quality_gates.Gate(a.baseline)
        for layer, s in summary['layers'].items():
            base = (gate.base or {}).get('layers', {}).get(layer)
            if base is None:
                if gate.base is not None:
                    gate.failures.append(f'{a.baseline}: no baseline for layer {layer}')
                continue
            if (base['errors'], base['clean']) != (summary['errors'], summary['clean']):
                gate.failures.append(f"{a.baseline} {layer}: {summary['errors']} errors / {summary['clean']} clean, the baseline counted "
                                     f"{base['errors']} / {base['clean']} (corpus or split changed: update the baseline on purpose)")
                continue
            gate.rate(f'{layer} fixed', s['fixed'], summary['errors'], base['fixed'], base['errors'])
            gate.count(f'{layer} false alarms', s['false_alarms'], base['false_alarms'])
            gate.performance(layer, {'p50_ms': s['latency']['p50_ms'], 'p95_ms': s['latency']['p95_ms'], 'max_rss_mb': s['max_rss_mb']})
        passed = gate.finish()
    if failed or not passed:
        sys.exit(1)


if __name__ == '__main__':
    main()
