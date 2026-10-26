#!/usr/bin/env python3
"""False-alarm gate for the rule packs: runs correct text through the rules-only engine and reports which rules
fire, so a new rule can be tightened before it ships.

usage: false-alarm-gate.py --engine ENGINE_BIN --corpus FILE [--corpus FILE ...] [--baseline JSON] [--save JSON]
                           [--only-rules PREFIX,...] [--show N] [--limit N]

Corpus files are JSONL ({"input": ..., "clean": true} rows are used; other rows skipped) or plain text, one sentence
per line. Output: changed/total, per-rule hit counts, and up to --show example hits per rule (the sentence and the
edit). With --baseline, rules whose hits grew are listed as NEW FALSE ALARMS and the exit code is 1; with --save the
current counts are written for the next run. Text from the corpora never belongs in rules, tests or fixtures.
"""
import argparse, collections, json, pathlib, subprocess, sys
def rows(path):
    p = pathlib.Path(path)
    for line in p.read_text(encoding='utf-8', errors='replace').splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith('{'):
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get('clean') is True and isinstance(r.get('input'), str):
                yield r['input']
            elif 'clean' not in r and isinstance(r.get('text'), str):
                yield r['text']
        else:
            yield line
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--engine', required=True)
    ap.add_argument('--corpus', action='append', required=True)
    ap.add_argument('--baseline'); ap.add_argument('--save')
    ap.add_argument('--only-rules', help='comma-separated rule id prefixes to report (default: all)')
    ap.add_argument('--show', type=int, default=3); ap.add_argument('--limit', type=int)
    a = ap.parse_args()
    texts = [t for c in a.corpus for t in rows(c)]
    if a.limit: texts = texts[:a.limit]
    import os
    env = {k: v for k, v in os.environ.items() if not k.startswith('PARZR_')}
    env.update({k: v for k, v in os.environ.items() if k in ('PARZR_MODEL_RUNTIME', 'PARZR_MODELS_DIR')})
    proc = subprocess.Popen([a.engine], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, env=env)
    hits, examples, changed, errors = collections.Counter(), collections.defaultdict(list), 0, 0
    for t in texts:
        proc.stdin.write(json.dumps({'text': t, 'mode': 'fix'}) + '\n'); proc.stdin.flush()
        r = json.loads(proc.stdout.readline())
        if 'error' in r:
            # "Corrections did not stabilize" is an engine bug (two rules undoing each other): list it.
            if 'stabilize' in r['error']:
                hits['engine.unstable'] += 1
                if len(examples['engine.unstable']) < a.show: examples['engine.unstable'].append((t, '', r['error']))
                continue
            errors += 1
            if errors == 1: print('engine error:', r['error'], file=sys.stderr)
            continue
        edits = r.get('edits') or []
        if r.get('text', t) != t: changed += 1
        for e in edits:
            for rid in e['rule_id'].split('+'):
                hits[rid] += 1
                if len(examples[rid]) < a.show:
                    examples[rid].append((t, e['original'], e['replacement']))
    proc.stdin.close(); proc.wait()
    prefixes = tuple(a.only_rules.split(',')) if a.only_rules else None
    if errors: sys.exit(f'{errors} engine errors; set PARZR_MODEL_RUNTIME (and PARZR_MODELS_DIR) or fix the engine')
    print(f'{changed}/{len(texts)} texts changed ({100*changed/max(1,len(texts)):.2f}%)')
    base = json.loads(pathlib.Path(a.baseline).read_text()) if a.baseline else {}
    new = []
    for rid, n in sorted(hits.items(), key=lambda x: -x[1]):
        if prefixes and not rid.startswith(prefixes): continue
        grew = n > base.get(rid, 0)
        flag = '  NEW FALSE ALARMS' if (base or not a.baseline) and grew and a.baseline else ''
        print(f'{n:6d}  {rid}{flag}')
        for t, o, rep in examples[rid]:
            print(f'          {o!r} -> {rep!r}   in: {t[:140]}')
        if a.baseline and grew: new.append(rid)
    if a.save:
        pathlib.Path(a.save).write_text(json.dumps(dict(hits), indent=1, sort_keys=True) + '\n')
    if new:
        print(f'{len(new)} rule(s) fire more than the baseline: {", ".join(new)}'); sys.exit(1)
if __name__ == '__main__':
    main()
