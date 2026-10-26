#!/usr/bin/env python3
"""Generates engine/rules/packs/word-order.json (id prefix `order.`). Every rule is verified as it is built (see
lib.py). usage: python3 scripts/rule-pack-gen/word-order/gen.py"""
import os, sys, importlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lib

MODULES = ['questions', 'embedded', 'adverbs', 'negation', 'inversion', 'passives', 'phrases', 'adjectives', 'extras']


def main():
    for name in MODULES:
        path = os.path.join(HERE, name + '.py')
        if not os.path.exists(path):
            continue
        mod = importlib.import_module(name)
        before = len(lib.RULES)
        mod.build()
        print(f'{name}: {len(lib.RULES) - before} rules')
    out = os.path.join(HERE, '..', '..', '..', 'engine', 'rules', 'packs', 'word-order.json')
    lib.dump(os.path.normpath(out))
    print(f'{len(lib.RULES)} rules written')


if __name__ == '__main__':
    main()
