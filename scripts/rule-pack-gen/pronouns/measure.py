"""Runs every rule's positive through a built engine (default: the engine WITHOUT the pack) and reports which the engine
already fixes completely.  usage: python3 measure.py ENGINE [--write skipped-ids.txt]"""
import json, os, subprocess, sys, pathlib
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lib
import f_coord, f_subj, f_wh, f_poss, f_misc, f_more  # noqa
env = dict(os.environ)
env['PARZR_MODEL_RUNTIME'] = '/Users/aman/Desktop/parzr/.claude/worktrees/reports-live/dist/model/libparzr_model.dylib'
env['PARZR_MODELS_DIR'] = os.path.expanduser('~/Library/Application Support/Parzr/Models')
engine = sys.argv[1]
p = subprocess.Popen([engine], stdin=subprocess.PIPE, stdout=subprocess.PIPE, env=env, text=True)


def run(t):
    p.stdin.write(json.dumps({'text': t}) + '\n')
    p.stdin.flush()
    return json.loads(p.stdout.readline())


norm = lambda s: s.replace('’', "'")
covered, partial, miss = [], [], []
for r in lib.RULES:
    exp = r.get('_fixes')
    res = run(r['positive'])
    out = res.get('text', '')
    ids = [e.get('rule_id') for e in res.get('edits', [])]
    if exp is None:
        miss.append((r['id'], out, ids))
        continue
    if norm(out) == norm(exp):
        covered.append((r['id'], ids))
    elif norm(out) != norm(r['positive']):
        partial.append((r['id'], r['positive'], out, ids))
    else:
        miss.append((r['id'], out, ids))
print('covered by engine:', len(covered))
for c in covered:
    print('  ', c)
print('partly changed:', len(partial))
for c in partial:
    print('  ', c)
print('not touched:', len(miss))
if '--write' in sys.argv:
    pathlib.Path(sys.argv[sys.argv.index('--write') + 1]).write_text('\n'.join(c[0] for c in covered) + '\n')
