#!/usr/bin/env python3
"""Runs every positive/negative of the clarity pack through the built engine and reports:
  - positives where the rule did not fire, or the corrected text differs from the expected one
  - negatives where any clarity. rule fires
  - other rules that also fire on a positive
usage: e2e.py [--engine PATH] [substring ...]"""
import json, os, pathlib, subprocess, sys
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
engine = str(ROOT / 'engine/target/release/parzr-engine')
args = sys.argv[1:]
if args[:1] == ['--engine']:
    engine, args = args[1], args[2:]
rules = {r['id']: r for r in json.loads((ROOT / 'engine/rules/packs/clarity-style.json').read_text())}
exp = json.loads((HERE / 'expected.json').read_text())
env = {k: v for k, v in os.environ.items() if not k.startswith('PARZR_')}
env['PARZR_MODEL_RUNTIME'] = os.environ.get('PARZR_MODEL_RUNTIME', '')
env['PARZR_MODELS_DIR'] = os.environ.get('PARZR_MODELS_DIR', '')
proc = subprocess.Popen([engine], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, env=env)


def run(text):
    proc.stdin.write(json.dumps({'text': text, 'mode': 'fix'}) + '\n'); proc.stdin.flush()
    return json.loads(proc.stdout.readline())


def ids_of(r):
    out = []
    for e in r.get('edits') or []:
        out += e['rule_id'].split('+')
    return out


bad = notes = 0
for rid, rule in rules.items():
    if args and not any(a in rid for a in args):
        continue
    r = run(rule['positive'])
    fired = ids_of(r)
    if rid not in fired:
        print(f'MISS  {rid}: {rule["positive"]!r} -> {r.get("text")!r} fired={fired}'); bad += 1
    elif r.get('text') != exp[rid]:
        print(f'DIFF  {rid}: {rule["positive"]!r}\n        got      {r.get("text")!r}\n        expected {exp[rid]!r}\n        fired={fired}'); bad += 1
    others = [i for i in fired if i != rid]
    if others and rid in fired:
        notes += 1
        print(f'MULTI {rid}: also {others} on {rule["positive"]!r}')
    n = run(rule['negative'])
    mine = [i for i in ids_of(n) if i.startswith('clarity.')]
    if mine:
        print(f'FALSE {rid}: negative fires {mine}: {rule["negative"]!r} -> {n.get("text")!r}'); bad += 1
print(f'{bad} problem(s), {notes} note(s), {len(rules)} rules')
sys.exit(1 if bad else 0)
