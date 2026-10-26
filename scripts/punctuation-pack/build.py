#!/usr/bin/env python3
"""Generates engine/rules/packs/punctuation-rules.json from the word lists in this folder.

    python3 scripts/punctuation-pack/build.py                 # write the pack
    python3 scripts/punctuation-pack/build.py --e2e           # also run every positive and negative through the engine
                                                              # (PARZR_MODEL_RUNTIME and PARZR_MODELS_DIR as for the gates)

Each rule is checked against its own positive and negative sentence with Python's re module before anything is written
(the engine's regex crate accepts the same patterns; the pack checker and the Rust tests check them again).
"""
import argparse, collections, json, os, pathlib, subprocess, sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ROOT = HERE.parent.parent
import core
import fam_compound

FAMILIES = [fam_compound]
for name in ('fam_numbers', 'fam_prefixes', 'fam_apostrophe', 'fam_marks', 'fam_misc'):
    try:
        FAMILIES.append(__import__(name))
    except ModuleNotFoundError as e:
        if e.name != name:
            raise


def generate():
    for fam in FAMILIES:
        fam.build()
    return core.RULES


def run_engine(texts):
    env = {k: v for k, v in os.environ.items() if not k.startswith('PARZR_')}
    env.setdefault('PARZR_MODEL_RUNTIME', '/Users/aman/Desktop/parzr/.claude/worktrees/reports-live/dist/model/libparzr_model.dylib')
    env.setdefault('PARZR_MODELS_DIR', os.path.expanduser('~/Library/Application Support/Parzr/Models'))
    eng = str(ROOT / 'engine/target/release/parzr-engine')
    p = subprocess.Popen([eng], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, env=env)
    out = []
    for t in texts:
        p.stdin.write(json.dumps({'text': t, 'mode': 'fix'}) + '\n')
        p.stdin.flush()
        out.append(json.loads(p.stdout.readline()))
    p.stdin.close()
    p.wait()
    return out


def rule_ids(r):
    return [e.get('rule_id') or e.get('ruleId') or e.get('rule') or '' for e in r.get('edits', [])]


def e2e():
    bad = 0
    res = run_engine([c[1] for c in core.E2E])
    for (rid, wrong, right, loose), r in zip(core.E2E, res):
        if 'error' in r:
            print('ERR', rid, wrong, r['error'])
            bad += 1
            continue
        same = r['text'].replace(',', '') == right.replace(',', '') if loose else r['text'] == right
        if not same:
            bad += 1
            print('POS', rid, '|', wrong, '->', r['text'], '| want', right, rule_ids(r))
    res = run_engine([c[1] for c in core.NEG])
    for (rid, s), r in zip(core.NEG, res):
        if any(rid in i.split('+') for i in rule_ids(r)):
            bad += 1
            print('NEG', rid, '|', s, '->', r.get('text'), rule_ids(r))
    print(f'{len(core.E2E)} positives, {len(core.NEG)} negative sentences through the engine: {bad} wrong')
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=str(ROOT / 'engine/rules/packs/punctuation-rules.json'))
    ap.add_argument('--e2e', action='store_true')
    a = ap.parse_args()
    rules = generate()
    if core.PROBLEMS:
        print('\n'.join(core.PROBLEMS[:100]))
        print(len(core.PROBLEMS), 'problems')
        sys.exit(1)
    with open(a.out, 'w') as f:
        json.dump(rules, f, indent=2, ensure_ascii=False)
        f.write('\n')
    fam = collections.Counter(r['id'].split('.')[1] for r in rules)
    print(len(rules), 'rules;', dict(fam))
    if a.e2e:
        sys.exit(1 if e2e() else 0)


if __name__ == '__main__':
    main()
