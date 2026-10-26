"""Builds engine/rules/packs/numbers-dates.json from the family files. Run from this folder: python3 build.py [--dump]
Each rule is checked here: the positive matches, the fix equals the expected text, the negative does not match."""
import pathlib, re, sys
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lib
import f_ordinals, f_clock, f_quantity, f_money, f_units, f_dates, f_misc  # noqa: F401  (importing registers the rules)

bad = 0
for r in lib.RULES:
    rx = re.compile(r['pattern'])
    if not rx.search(r['positive']):
        print('NO MATCH on positive:', r['id'], '|', r['positive']); bad += 1; continue
    m = rx.search(r['negative'])
    if m:
        print('MATCH on negative:', r['id'], '|', repr(m.group(0)), '|', r['negative']); bad += 1
    got = lib.fixed(r, r['positive'])
    if got != r['_fixes']:
        print('FIX differs:', r['id'], '|', got, '| expected', r['_fixes']); bad += 1
print(len(lib.RULES), 'rules,', bad, 'problems')
if '--dump' in sys.argv and not bad:
    out = HERE.parents[2] / 'engine/rules/packs/numbers-dates.json'
    lib.dump(out)
    print('wrote', out, len(lib.RULES), 'rules')
sys.exit(1 if bad else 0)
