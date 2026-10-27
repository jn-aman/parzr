#!/usr/bin/env python3
"""Generates engine/rules/packs/clauses-conjunctions.json (the `clause.` rule pack) from the construction tables in
scripts/clauses/*.py. Each rule is checked as it is added (core.add): its positive must change to exactly the stated
correction, its negative must not match, the corrected sentence must not match again; then every rule is run over
every other rule's negative and corrected sentences.

usage: gen-clauses-conjunctions.py [--out PACK.json]"""
import argparse, json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / 'clauses'))
import core  # noqa: E402

MODULES = ['doubles', 'ofclause', 'correl', 'relative', 'misc', 'misc2']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=str(ROOT / 'engine/rules/packs/clauses-conjunctions.json'))
    ap.add_argument('--expected', help='write {rule id: corrected positive} here (for end-to-end checks)')
    ap.add_argument('--doc', default=str(ROOT / 'docs/rule-packs/clauses-conjunctions.md'))
    ap.add_argument('--only', help='comma-separated modules to load (debugging)')
    args = ap.parse_args()
    for name in (args.only.split(',') if args.only else MODULES):
        __import__(name)
    bad = core.cross_check()
    if bad:
        raise SystemExit(f'{bad} cross-check problem(s)')
    pathlib.Path(args.out).write_text(json.dumps(core.RULES, indent=2, ensure_ascii=False) + '\n')
    if args.expected:
        pathlib.Path(args.expected).write_text(json.dumps(core.FIXED, indent=1, ensure_ascii=False))
    import doc  # noqa: E402
    pathlib.Path(args.doc).parent.mkdir(parents=True, exist_ok=True)
    doc.write(args.doc)
    print(f'{len(core.RULES)} rules -> {args.out}')


if __name__ == '__main__':
    main()
