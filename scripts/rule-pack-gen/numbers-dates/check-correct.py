"""Every rule of the generated pack against the correct sentences in correct-*.txt: none may match.
usage (from this folder):  python3 check-correct.py [PACK.json]"""
import json, pathlib, re, sys
HERE = pathlib.Path(__file__).resolve().parent
pack = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parents[2] / 'engine/rules/packs/numbers-dates.json'
rules = json.loads(pack.read_text())
lines = [l.strip() for f in sorted(HERE.glob('correct-*.txt')) for l in f.read_text().splitlines() if l.strip()]
bad = 0
for r in rules:
    rx = re.compile(r['pattern'])
    for l in lines:
        m = rx.search(l)
        if m:
            bad += 1
            print('MATCH', r['id'], repr(m.group(0)), '|', l)
print(len(rules), 'rules,', len(lines), 'correct sentences,', bad, 'matches')
sys.exit(1 if bad else 0)
