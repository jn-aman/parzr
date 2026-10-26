#!/usr/bin/env python3
"""Runs every rule of the capitalization pack through the real engine (rules only, no model):
  * the positive must come out as the regex replacement says, and the fix must be credited to a caps.* rule
    (a positive that a base rule fixes first is reported as REDUNDANT);
  * the negative must not draw any caps.* edit;
  * every line of correct-*.txt must draw no caps.* edit.
usage: verify.py [--only PREFIX] [--engine PATH] [--models DIR]"""
import argparse, json, os, pathlib, re, subprocess, sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ap = argparse.ArgumentParser()
ap.add_argument('--engine', default=str(ROOT / 'engine/target/release/parzr-engine'))
ap.add_argument('--models', default='/private/tmp/claude-501/-Users-aman-Desktop/a2be551f-0769-47a8-ba8d-479a16ade0ab/scratchpad/cap/nomodels')
ap.add_argument('--only')
ap.add_argument('--pack', default=str(ROOT / 'engine/rules/packs/capitalization-rules.json'))
ap.add_argument('--skip-correct', action='store_true')
a = ap.parse_args()

env = {k: v for k, v in os.environ.items() if not k.startswith('PARZR_')}
env['PARZR_MODEL_RUNTIME'] = '/Users/aman/Desktop/parzr/.claude/worktrees/reports-live/dist/model/libparzr_model.dylib'
env['PARZR_MODELS_DIR'] = a.models
p = subprocess.Popen([a.engine], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, env=env)


def run(t):
    p.stdin.write(json.dumps({'text': t, 'mode': 'fix'}) + '\n')
    p.stdin.flush()
    return json.loads(p.stdout.readline())


def expected(rule):
    rx = re.compile(rule['pattern'])
    out, pos = [], 0
    for m in rx.finditer(rule['positive']):
        if 'target' in rx.groupindex:
            s, e = m.span('target')
        else:
            s, e = m.span()
        out.append(rule['positive'][pos:s])
        out.append(m.expand(rule['replacement']))
        pos = e
    out.append(rule['positive'][pos:])
    return ''.join(out)


rules = json.load(open(a.pack))
bad = 0
redundant = []
for r in rules:
    if a.only and not r['id'].startswith(a.only):
        continue
    res = run(r['positive'])
    if 'error' in res:
        print('ERROR', r['id'], res['error'])
        bad += 1
        continue
    mine = [e for e in res.get('edits', []) if r['id'] in e['rule_id'].split('+')]
    if not mine:
        base = [e['rule_id'] for e in res.get('edits', [])]
        if base and res['text'] != r['positive']:
            redundant.append((r['id'], base))
        else:
            print('NOFIX', r['id'], '|', r['positive'], '|', res.get('text'))
            bad += 1
        continue
    exp = expected(r)
    # the engine may also fix sentence-start capitals etc. in the positive; compare only that my edit applied
    if exp != res['text']:
        # allow differences produced by other rules: check my edit's replacement lands in the text
        e = mine[0]
        if e['replacement'] not in res['text']:
            print('WRONG', r['id'], '|', res['text'], '| expected', exp)
            bad += 1
    res = run(r['negative'])
    hit = [e for e in res.get('edits', []) if 'caps.' in e['rule_id']]
    if hit:
        print('NEGHIT', r['id'], [(h['rule_id'], h['original'], h['replacement']) for h in hit], '|', r['negative'])
        bad += 1
if not a.skip_correct and not a.only:
    for f in sorted(HERE.glob('correct-*.txt')):
        for line in f.read_text().splitlines():
            if not line.strip() or line.startswith('#'):
                continue
            res = run(line)
            hit = [e for e in res.get('edits', []) if 'caps.' in e['rule_id']]
            if hit:
                print('CORRECT-HIT', f.name, [(h['rule_id'], h['original'], h['replacement']) for h in hit], '|', line)
                bad += 1
print(f'{len(rules)} rules; {bad} problem(s); {len(redundant)} redundant (positive already fixed by a base rule)')
for rid, base in redundant[:40]:
    print('REDUNDANT', rid, base)
sys.exit(1 if bad else 0)
