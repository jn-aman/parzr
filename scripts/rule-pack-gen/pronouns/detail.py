"""detail.py CORPUS RULE_ID... : for changed rows where a rule hits, prints the input window and the reference window
(to judge whether the rule's fix disagrees with the annotators). Evaluation only; never copy the text."""
import json, pathlib, re, sys
HERE = pathlib.Path(__file__).resolve().parent
pack = json.loads((HERE.parents[2] / 'engine/rules/packs/pronouns.json').read_text())
want = {('pron.' + a if not a.startswith('pron.') else a) for a in sys.argv[2:]}
rules = [(r, re.compile(r['pattern'])) for r in pack if r['id'] in want]
for line in open(sys.argv[1], encoding='utf-8', errors='replace'):
    try:
        row = json.loads(line)
    except Exception:
        continue
    t, ref = row.get('input'), row.get('reference')
    if not isinstance(t, str) or row.get('clean') is True:
        continue
    for r, x in rules:
        m = x.search(t)
        if m:
            k = m.start()
            print(r['id'], '| IN :', t[max(0, k - 50):m.end() + 50].replace('\n', ' '))
            # crude: show the reference window around the same offset
            print(' ' * len(r['id']), '| REF:', (ref or '')[max(0, k - 50):m.end() + 50].replace('\n', ' '))
