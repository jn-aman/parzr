"""Runs every rule's positive and negative through the built engine. usage: python3 verify.py ENGINE_BIN
The positive must come out as the expected fix and carry the rule's id; the negative must carry no edit of the pack."""
import json, os, pathlib, subprocess, sys
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lib
import f_ordinals, f_clock, f_quantity, f_money, f_units, f_dates, f_misc  # noqa: F401
env = dict(os.environ)
env.setdefault('PARZR_MODEL_RUNTIME', '/Users/aman/Desktop/parzr/.claude/worktrees/reports-live/dist/model/libparzr_model.dylib')
env.setdefault('PARZR_MODELS_DIR', os.path.expanduser('~/Library/Application Support/Parzr/Models'))
p = subprocess.Popen([sys.argv[1]], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, env=env)
def run(t):
    p.stdin.write(json.dumps({'text': t, 'mode': 'fix'}) + '\n'); p.stdin.flush()
    r = json.loads(p.stdout.readline())
    return r.get('text', t), [e.get('rule_id') for e in r.get('edits', [])] if 'error' not in r else ['ERROR ' + r['error']]
bad = 0
for r in lib.RULES:
    rid = 'num.' + r['id'][4:] if r['id'].startswith('num.') else r['id']
    out, ids = run(r['positive'])
    if out != r['_fixes'] or r['id'] not in ids:
        bad += 1
        print('POSITIVE', r['id'], '|', r['positive'], '->', out, '| want', r['_fixes'], '|', ids)
    out, ids = run(r['negative'])
    mine = [i for i in ids if i and i.startswith('num.')]
    if mine:
        bad += 1
        print('NEGATIVE', r['id'], '|', r['negative'], '->', out, '|', ids)
print(len(lib.RULES), 'rules,', bad, 'problems')
sys.exit(1 if bad else 0)
