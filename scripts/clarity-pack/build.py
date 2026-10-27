#!/usr/bin/env python3
"""Builds engine/rules/packs/clarity-style.json, scripts/clarity-pack/expected.json and docs/rule-packs/clarity-style.md.
usage: python3 scripts/clarity-pack/build.py"""
import json, pathlib, sys
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import core, swaps, lexical, light, check_negatives, doc


def main():
    swaps.build()
    lexical.build_basis(); lexical.build_manner(); lexical.build_be(); lexical.build_my(); lexical.build_drops(); lexical.build_stacks()
    light.build()
    core.flush()
    check_negatives.run(core.RULES)
    out = core.ROOT / 'engine/rules/packs/clarity-style.json'
    out.write_text(json.dumps(core.RULES, indent=2, ensure_ascii=False) + '\n')
    (HERE / 'expected.json').write_text(json.dumps(core.EXPECTED, indent=1, ensure_ascii=False, sort_keys=True) + '\n')
    doc.write()
    print(len(core.RULES), 'rules written')


if __name__ == '__main__':
    main()
