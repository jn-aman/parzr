#!/usr/bin/env python3
"""Builds engine/rules/packs/capitalization-rules.json from the family generators in this directory.
usage: python3 build.py"""
import importlib
import sys
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lib

FAMILIES = ['gen_places', 'gen_names', 'gen_holidays', 'gen_brands', 'gen_acronyms', 'gen_titles', 'gen_misc']

if __name__ == '__main__':
    for name in FAMILIES:
        if not (HERE / f'{name}.py').exists():
            continue
        mod = importlib.import_module(name)
        before = len(lib.RULES)
        mod.build()
        print(f'{name}: {len(lib.RULES) - before} rules')
    n = lib.write()
    print(f'wrote {n} rules to {lib.OUT}')
    import collections
    fam = collections.Counter(f for f, _ in lib.COVERAGE)
    other = n - sum(fam.values())
    for f, c in sorted(fam.items(), key=lambda x: -x[1]):
        print(f'  {c:5d}  {f}')
    print(f'  {other:5d}  (rules without a family tag)')
