#!/usr/bin/env python3
"""Prints positive => corrected for rules whose id contains the argument (or a random sample with --sample N)."""
import json, pathlib, random, sys
HERE = pathlib.Path(__file__).resolve().parent
rules = {x['id']: x for x in json.loads((HERE.parent.parent / 'engine/rules/packs/modifiers.json').read_text())}
exp = json.loads((HERE / 'expected.json').read_text())
args = sys.argv[1:]
if args and args[0] == '--sample':
    random.seed(int(args[2]) if len(args) > 2 else 1)
    keys = random.sample(list(exp), int(args[1]))
else:
    keys = [k for k in exp if any(a in k for a in args)]
for k in keys:
    print(f'{k}\n   {rules[k]["positive"]}\n   => {exp[k]}\n   [{rules[k]["category"]} {rules[k]["confidence"]}] {rules[k]["reason"]}')
