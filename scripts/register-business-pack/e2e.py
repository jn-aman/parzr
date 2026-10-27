#!/usr/bin/env python3
"""Runs every rule's positive and negative through the built engine (rules + base passes, fix mode).
The positive must produce exactly the expected sentence with this rule among the edits; the negative must not
trigger any register.* rule. usage: python3 scripts/register-business-pack/e2e.py [ENGINE] --tone-engine RULES_ONLY_ENGINE [--only SUBSTR]
RULES_ONLY_ENGINE: cargo build --release --no-default-features --bin parzr-engine (the tone rules run only there)"""
import json, os, subprocess, sys, pathlib
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))
import core, fam_wordy, fam_verbs, fam_email, fam_signoff
def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    only = sys.argv[sys.argv.index('--only') + 1] if '--only' in sys.argv else None
    tone = sys.argv[sys.argv.index('--tone-engine') + 1] if '--tone-engine' in sys.argv else None
    engine = args[0] if args and args[0] not in (only, tone) else str(ROOT / 'engine/target/release/parzr-engine')
    for m in (fam_wordy, fam_verbs, fam_email, fam_signoff):
        m.build()
    env = dict(os.environ)
    # The model runtime comes from the caller (PARZR_MODEL_RUNTIME); without it the check runs rules only.
    env.setdefault('PARZR_MODELS_DIR', os.path.expanduser('~/Library/Application Support/Parzr/Models'))
    procs = {}
    def proc(path):
        if path not in procs:
            procs[path] = subprocess.Popen([path], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, env=env)
        return procs[path]
    def run(t, mode='fix'):
        # Fix mode runs on the full engine; the tone modes need the rules-only build (the shipped build hands a tone
        # rewrite to the model and never runs the tone rules).
        p = proc(engine if mode == 'fix' else tone)
        p.stdin.write(json.dumps({'text': t, 'mode': mode}) + '\n'); p.stdin.flush()
        return json.loads(p.stdout.readline())
    bad = 0
    for r in core.RULES:
        if only and only not in r['id']: continue
        mode = (r.get('modes') or ['fix'])[0]
        res = run(r['positive'], mode)
        ids = [e['rule_id'] for e in res.get('edits', [])]
        if res.get('text') != r['_expect'] or not any(r['id'] in i.split('+') for i in ids):
            bad += 1
            print('POSITIVE', r['id']); print('   in :', repr(r['positive'])); print('   out:', repr(res.get('text')), ids, 'want', repr(r['_expect']))
        hit = []
        for m in ('fix', 'concise', 'direct'):
            res = run(r['negative'], m)
            hit += [e['rule_id'] for e in res.get('edits', []) if 'register.' in e['rule_id']]
        if hit:
            bad += 1
            print('NEGATIVE', r['id'], hit); print('   in :', repr(r['negative'])); print('   out:', repr(res.get('text')))
    for p in procs.values():
        p.stdin.close(); p.wait()
    print(f'{len(core.RULES)} rules, {bad} problem(s)')
    sys.exit(1 if bad else 0)
if __name__ == '__main__':
    main()
