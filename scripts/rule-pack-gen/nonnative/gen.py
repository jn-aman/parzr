#!/usr/bin/env python3
"""Generates engine/rules/packs/nonnative.json (id prefix `l1.`). Every rule is verified as it is built (see lib.py).
usage: python3 scripts/rule-pack-gen/nonnative/gen.py [expect.json]"""
import os, sys, importlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lib

MODULES = ['register', 'phrasing', 'complements', 'timewords', 'tags', 'emphasis', 'uncountable', 'extras', 'extras2', 'extras3', 'extras4', 'extras5']


def main():
    for name in MODULES:
        if not os.path.exists(os.path.join(HERE, name + '.py')):
            continue
        mod = importlib.import_module(name)
        before = len(lib.RULES)
        mod.build()
        print(f'{name}: {len(lib.RULES) - before} rules')
    if lib.ERRORS:
        print('\n'.join(lib.ERRORS)); print(f'{len(lib.ERRORS)} problem(s)'); sys.exit(1)
    out = os.path.normpath(os.path.join(HERE, '..', '..', '..', 'engine', 'rules', 'packs', 'nonnative.json'))
    held = os.path.join(HERE, 'held-back.json')
    active, parked = lib.dump(out, sys.argv[1] if len(sys.argv) > 1 else None, held, HELD_BACK)
    print(f'{active} rules written to the pack, {parked} held back in {os.path.basename(held)}')


# Rule families that run only in the Professional rewrite (modes: ["professional"]). Each form below is standard
# Indian English, and the owner's own everyday regression set (benchmarks/everyday/items.jsonl) lists it as correct
# text that must stay unchanged in a Fix check (b002-0135, -0160, -0314, -0408, -0533, -0549, -0563, -0673, -0712,
# -0826, -0904, -0915, -0953, -0954, -0978, b003-0870 and others). A Professional rewrite asks for business English,
# so there "do the needful" becomes "do what is needed". The family stays whole. held-back.json lists them for review.
HELD_BACK = [
    'l1.needful', 'l1.prepone', 'l1.revert.reply', 'l1.revert.reply_past', 'l1.revert.reply_ing', 'l1.revert.noun',
    'l1.kindly.imperative', 'l1.request.start', 'l1.request.kindly_start', 'l1.request.kindly', 'l1.same', 'l1.outofstation',
    'l1.outstation', 'l1.goodname', 'l1.doubt', 'l1.informed.please', 'l1.thanking.you', 'l1.reply.back',
]


if __name__ == '__main__':
    main()
