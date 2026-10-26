"""With the pack built into ENGINE: every positive must come out as the expected text with the pack rule among the edits,
and every sentence in correct-*.txt (and every negative) must not be touched by a pron.* rule.
usage: python3 verify.py ENGINE"""
import json, os, subprocess, sys, pathlib
HERE = pathlib.Path(__file__).resolve().parent
pack = json.loads((HERE.parents[2] / 'engine/rules/packs/pronouns.json').read_text())
sys.path.insert(0, str(HERE))
import lib
import f_coord, f_subj, f_wh, f_poss, f_misc, f_more  # noqa
expected = {r['id']: r.get('_fixes') for r in lib.RULES}
env = dict(os.environ)
env['PARZR_MODEL_RUNTIME'] = os.environ.get('PARZR_MODEL_RUNTIME', 'dist/model/libparzr_model.dylib')
env['PARZR_MODELS_DIR'] = os.path.expanduser('~/Library/Application Support/Parzr/Models')
p = subprocess.Popen([sys.argv[1]], stdin=subprocess.PIPE, stdout=subprocess.PIPE, env=env, text=True)


def run(t):
    p.stdin.write(json.dumps({'text': t}) + '\n')
    p.stdin.flush()
    return json.loads(p.stdout.readline())


norm = lambda s: s.replace('’', "'")
bad = 0
for r in pack:
    res = run(r['positive'])
    ids = [e.get('rule_id') for e in res.get('edits', [])]
    exp = expected.get(r['id'])
    ok_text = exp is None or norm(res.get('text', '')) == norm(exp)
    fired = r['id'] in ids
    if not fired or not ok_text:
        bad += 1
        print('POSITIVE', r['id'], '| fired' if fired else '| NOT FIRED', '|', r['positive'], '->', res.get('text'), ids)
# negatives and correct sentences: no pron.* rule may fire
lines = []
for r in pack:
    lines += [s.strip() for s in r['negative'].replace('? ', '?\n').replace('. ', '.\n').replace('! ', '!\n').split('\n') if s.strip()]
for f in sorted(HERE.glob('correct-*.txt')):
    lines += [l.strip() for l in f.read_text().splitlines() if l.strip()]
seen = set()
for l in lines:
    if l in seen:
        continue
    seen.add(l)
    res = run(l)
    hit = [e.get('rule_id') for e in res.get('edits', []) if (e.get('rule_id') or '').startswith('pron.')]
    if hit:
        bad += 1
        print('FALSE ALARM', hit, '|', l, '->', res.get('text'))
print(len(pack), 'rules,', len(seen), 'correct/negative sentences,', bad, 'problems')
sys.exit(1 if bad else 0)
