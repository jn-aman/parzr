"""scan.py ENGINE TEMPLATE WORD [WORD...]  (or WORDS via '|'): shows which words the engine already fixes.
TEMPLATE has {w}; the engine must change the text for the word to count as covered."""
import json, os, subprocess, sys
env = dict(os.environ)
env['PARZR_MODEL_RUNTIME'] = '/Users/aman/Desktop/parzr/.claude/worktrees/reports-live/dist/model/libparzr_model.dylib'
env['PARZR_MODELS_DIR'] = os.path.expanduser('~/Library/Application Support/Parzr/Models')
engine, template = sys.argv[1], sys.argv[2]
words = []
for a in sys.argv[3:]:
    words += a.split('|')
p = subprocess.Popen([engine], stdin=subprocess.PIPE, stdout=subprocess.PIPE, env=env, text=True)
covered, open_ = [], []
for w in words:
    t = template.format(w=w)
    p.stdin.write(json.dumps({'text': t}) + '\n')
    p.stdin.flush()
    r = json.loads(p.stdout.readline())
    if r.get('text') != t:
        covered.append((w, r['text']))
    else:
        open_.append(w)
print('covered by engine:', ' '.join(w for w, _ in covered))
print('open:', '|'.join(open_))
if '-v' in os.environ.get('SCANV', ''):
    for w, o in covered:
        print('  ', w, '->', o)
