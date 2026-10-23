#!/usr/bin/env python3
"""Generates engine/rules/packs/verb-complements.json (the `vcomp.` rule pack) from the construction tables in
scripts/vcomp/*.py, and checks every rule as it is added: the positive must change to exactly the stated
correction, the negative must not match at all.

Why a generator: a gerund or infinitive fix has to respell the verb ("enjoy to read" to "enjoy reading"), and a
regex replacement cannot compute an inflection. The tables below spell each verb's stem once and the builders
below produce the capture groups that rebuild the right form, so one rule covers plain verbs ("read"), verbs that
drop a final e ("make", "making"), and verbs that double a final consonant ("run", "running").

usage: gen-verb-complements.py [--out PACK.json] [--lits LITS.json]
(--lits writes each rule's required words for the corpus scanner; the pack itself carries no extra fields.)"""
import argparse, json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / 'vcomp'))
import core  # noqa: E402

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=str(ROOT / 'engine/rules/packs/verb-complements.json'))
    ap.add_argument('--lits')
    ap.add_argument('--coverage')
    ap.add_argument('--expected')
    ap.add_argument('--doc', default=str(ROOT / 'docs/rule-packs/verb-complements.md'))
    args = ap.parse_args()
    import tables  # noqa: E402  (registers rules through core.add)
    rules = core.finish()
    pathlib.Path(args.out).write_text(json.dumps(rules, indent=2, ensure_ascii=False) + '\n')
    if args.lits:
        pathlib.Path(args.lits).write_text(json.dumps(core.LITS))
    if args.expected:
        pathlib.Path(args.expected).write_text(json.dumps(core.EXPECTED))
    if args.coverage:
        pathlib.Path(args.coverage).write_text(json.dumps(core.COVER, indent=1))
    import doc  # noqa: E402
    pathlib.Path(args.doc).parent.mkdir(parents=True, exist_ok=True)
    doc.write(args.doc)
    print(f'{len(rules)} rules -> {args.out}')

if __name__ == '__main__':
    main()
