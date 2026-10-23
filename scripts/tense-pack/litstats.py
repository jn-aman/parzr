#!/usr/bin/env python3
"""How often each rule's prefilter literal fires on ordinary text.  A rule that is a candidate in many texts costs a regex
compile (about a millisecond) every time, so the pack is kept near 0.3 candidate rules per sentence.

    python3 scripts/tense-pack/litstats.py CORPUS.jsonl [n-texts]    # rows with "input"/"reference"/"text"
"""
import collections, json, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from literals import required

ROOT = HERE.parent.parent
PACK = ROOT / 'engine/rules/packs/tense-aspect.json'
N = int(sys.argv[2]) if len(sys.argv) > 2 else 20000
texts = []
for line in open(sys.argv[1], encoding='utf-8', errors='replace'):
    r = json.loads(line)
    t = r.get('reference') if not r.get('clean') else r.get('input')
    t = t or r.get('text')
    if isinstance(t, str) and len(t) < 400:
        texts.append(t.lower())
    if len(texts) >= N:
        break
res = []
for r in json.load(open(PACK)):
    lits = required(r['pattern'])
    n = len(texts) if not lits else sum(1 for t in texts if any(l in t for l in lits))
    res.append((n / len(texts), r['id'], sorted(lits)[:4] if lits else None))
res.sort(reverse=True)
print('expected candidate rules per text:', round(sum(x[0] for x in res), 2), 'of', len(res))
for f, rid, lits in res[:25]:
    print(f'{f:6.3f}', rid, lits)
