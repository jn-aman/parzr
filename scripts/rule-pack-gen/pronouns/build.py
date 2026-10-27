"""Builds engine/rules/packs/pronouns.json from the family files. Run from this folder: python3 build.py
Each rule is checked here: the positive matches, the fix equals the expected text, the negative does not match."""
import pathlib, re, sys
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lib
import f_coord, f_subj, f_wh, f_poss, f_misc, f_more  # noqa: F401  (importing registers the rules)

skipped = set((HERE / 'skipped-ids.txt').read_text().split()) if (HERE / 'skipped-ids.txt').exists() else set()
bad = 0
for r in lib.RULES:
    rx = re.compile(r['pattern'])
    if not rx.search(r['positive']):
        print('NO MATCH on positive:', r['id'], '|', r['positive']); bad += 1; continue
    if rx.search(r['negative']):
        m = rx.search(r['negative'])
        print('MATCH on negative:', r['id'], '|', repr(m.group(0)), '|', r['negative']); bad += 1
    exp = r.get('_fixes')
    if exp is not None:
        got = lib.fixed(r, r['positive'])
        if got.replace('’', "'") != exp.replace('’', "'"):
            print('FIX differs:', r['id'], '|', got, '| expected', exp); bad += 1
print(len(lib.RULES), 'rules,', bad, 'problems')
if '--dump' in sys.argv and not bad:
    lib.RULES[:] = [r for r in lib.RULES if r['id'] not in skipped]
    out = HERE.parents[2] / 'engine/rules/packs/pronouns.json'
    lib.dump(out)
    print('wrote', out, len(lib.RULES), 'rules (', len(skipped), 'left out: the engine already fixes them)')
sys.exit(1 if bad else 0)
