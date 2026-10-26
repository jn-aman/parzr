#!/usr/bin/env python3
"""Runs every positive/negative of the redundancy pack through the built rules-only engine and reports:
  - positives where the rule did not fire, or the corrected text differs from the expected one
  - negatives where any redund. rule fires
  - other rules that also fire on a positive (possible overlap with a base rule or another pack)
usage: e2e.py [--engine PATH] [prefix ...]"""
import json, os, pathlib, subprocess, sys
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
engine = str(ROOT / 'engine/target/release/parzr-engine')
args = sys.argv[1:]
if args[:1] == ['--engine']:
    engine, args = args[1], args[2:]
rules = {r['id']: r for r in json.loads((ROOT / 'engine/rules/packs/redundancy.json').read_text())}
exp = json.loads((HERE / 'expected.json').read_text())
env = {k: v for k, v in os.environ.items() if not k.startswith('PARZR_')}
# The native runtime and model packs, as the gates take them (see engine/rules/packs/README.md).
env.setdefault('PARZR_MODEL_RUNTIME', os.environ.get('PARZR_MODEL_RUNTIME', 'dist/model/libparzr_model.dylib'))
env.setdefault('PARZR_MODELS_DIR', os.environ.get('PARZR_MODELS_DIR', os.path.expanduser('~/Library/Application Support/Parzr/Models')))
proc = subprocess.Popen([engine], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, env=env)

def run(text, mode='fix'):
    proc.stdin.write(json.dumps({'text': text, 'mode': mode}) + '\n'); proc.stdin.flush()
    return json.loads(proc.stdout.readline())

def ids_of(r):
    return [e.get('rule') or e.get('rule_id') or e.get('id') for e in (r.get('edits') or [])]

bad = overlap = 0
first = True
for rid, rule in rules.items():
    if args and not any(a in rid for a in args):
        continue
    mode = (rule.get('modes') or ['fix'])[0]
    r = run(rule['positive'], mode)
    if first:
        first = False
        if '--debug' in os.environ.get('E2E', ''):
            print(json.dumps(r, ensure_ascii=False)[:600])
    fired = ids_of(r)
    if rid not in fired:
        print(f'MISS  {rid}: {rule["positive"]!r} -> {r.get("text")!r} fired={fired}'); bad += 1
    elif r.get('text') not in (exp[rid], exp[rid][:1].upper() + exp[rid][1:]):
        others = [i for i in fired if i != rid]
        print(f'{"NOTE" if others else "DIFF"}  {rid}: {rule["positive"]!r}\n        got      {r.get("text")!r}\n        expected {exp[rid]!r}\n        fired={fired}')
        bad += 0 if others else 1
    others = [i for i in fired if i != rid]
    if others and rid in fired:
        print(f'MULTI {rid}: also {others} on {rule["positive"]!r}'); overlap += 1
    n = run(rule['negative'], mode)
    mine = [i for i in ids_of(n) if i and i.startswith('redund.')]
    if mine:
        print(f'FALSE {rid}: negative fires {mine}: {rule["negative"]!r} -> {n.get("text")!r}'); bad += 1
print(f'{bad} problem(s), {overlap} overlap note(s), {len(rules)} rules')
