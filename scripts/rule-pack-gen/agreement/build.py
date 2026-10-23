"""Generates engine/rules/packs/agreement.json from the word lists (vocab.py, verbobj.py) and the construction templates (gen*.py).

usage (from this folder):  python3 build.py [--out FILE] [--all]
Checks every rule with Python's re (positive matches and is changed, negative never matches), then writes the pack without the
ids in skipped-ids.txt: rules whose positive and word-list variants the engine without this pack already fixed completely.
--all keeps them. correct-*.txt are correct sentences no rule may match: python3 check-correct.py.
"""
import json, pathlib, re, sys
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lib
from lib import RULES, dump, fixed
import gen1, gen2, gen3, gen4, gen5, gen6   # noqa: F401  (importing a module adds its rules)

out = HERE.parents[2] / 'engine/rules/packs/agreement.json'
keep_all = '--all' in sys.argv
if '--out' in sys.argv:
    out = pathlib.Path(sys.argv[sys.argv.index('--out') + 1])
bad = 0
for r in RULES:
    rx = re.compile(r['pattern'])
    if not rx.search(r['positive']):
        print('positive does not match', r['id']); bad += 1
    if rx.search(r['negative']):
        print('negative matches', r['id']); bad += 1
    if fixed(r, r['positive']) == r['positive']:
        print('positive unchanged', r['id']); bad += 1
if bad:
    sys.exit(1)
skipped = set((HERE / 'skipped-ids.txt').read_text().split()) if not keep_all else set()
lib.RULES[:] = [r for r in RULES if r['id'] not in skipped]
dump(str(out))
print(len(RULES), 'rules written to', out)
