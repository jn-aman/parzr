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
                                [--min-fix-rate LAYER=RATE ...] [--max-false-alarm-rate LAYER=RATE ...]

--engine takes the parzr-engine CLI or scripts/heldout-native.swift built with swiftc (the app's path, with Apple
NaturalLanguage hints; see benchmarks/README.md). The gate flags make the run exit 1 when a layer falls below a fix
rate or above a false-alarm rate, so CI can block a release that makes checking worse.
"""
import argparse, collections, hashlib, json, pathlib, subprocess, sys, time, unicodedata

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


class Engine:
    def __init__(self, path, extra):
        self.extra = extra
        self.proc = subprocess.Popen([path], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, encoding='utf-8', bufsize=1)

    def check(self, item):
        req = {'text': item['input'], **self.extra}
        if item.get('dialect'):
            req['dialect'] = item['dialect']
        self.proc.stdin.write(json.dumps(req, ensure_ascii=False) + '\n'); self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        if not line:
            raise RuntimeError('engine exited')
        return json.loads(line)

    def close(self):
        self.proc.stdin.close(); self.proc.wait(timeout=30)


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
    a = p.parse_args()
    errors, clean = load(a.corpus), load(a.clean)
    if a.split != 'all':
        errors, clean = [i for i in errors if split_of(i) == a.split], [i for i in clean if split_of(i) == a.split]
    if a.limit:
        errors, clean = errors[:a.limit], clean[:a.limit]
    a.output.mkdir(parents=True, exist_ok=True)
    summary = {'engine': a.engine, 'split': a.split, 'errors': len(errors), 'clean': len(clean), 'layers': {}}
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
        eng.close()
        total = collections.Counter(); [total.update({k: v for k, v in c.items()}) for k, c in by_cat.items() if '/' not in k]
        summary['layers'][layer] = {
            'seconds': round(time.time() - t0, 1),
            'fixed': total['fixed'], 'flagged': total['flagged'], 'wrong': total['wrong'], 'missed': total['missed'],
            'fix_rate': round(total['fixed'] / max(1, len(errors)), 4),
            'catch_rate': round((total['fixed'] + total['flagged']) / max(1, len(errors)), 4),
            'false_alarm_rate': round(len(false_alarms) / max(1, len(clean)), 4), 'false_alarms': len(false_alarms),
            'categories': {k: dict(c) for k, c in sorted(by_cat.items())},
        }
        with open(a.output / f'{layer}-results.jsonl', 'w') as f:
            f.writelines(json.dumps(r, ensure_ascii=False) + '\n' for r in rows)
        with open(a.output / f'{layer}-false-alarms.jsonl', 'w') as f:
            f.writelines(json.dumps(r, ensure_ascii=False) + '\n' for r in false_alarms)
        s = summary['layers'][layer]
        print(f"{layer}: fixed {s['fix_rate']:.1%}, caught {s['catch_rate']:.1%}, false alarms {s['false_alarm_rate']:.1%} ({s['seconds']}s)")
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
    if failed:
        sys.exit(1)


if __name__ == '__main__':
    main()
