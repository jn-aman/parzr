#!/usr/bin/env python3
"""Generates engine/rules/packs/tense-aspect.json from the verb tables in this folder.

    python3 scripts/tense-pack/build.py              # write the pack
    python3 scripts/tense-pack/build.py --e2e ENGINE # also run every positive and negative sentence through the engine
                                                     # (PARZR_MODEL_RUNTIME and PARZR_MODELS_DIR must be set)

The generator checks each rule against its own sentences with Python's re module before it writes anything (the
engine's regex crate accepts the same patterns); the Rust tests then check them again. data/*.json hold what the
engine without this pack already fixed (written by coverage.py), so no rule is generated for a context that is
already handled; dropped.json lists verbs left out of a family because an existing check rewrites their correct form.
"""
import argparse, collections, json, os, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ROOT = HERE.parent.parent
import core
import fam_irreg
import fam_constr

STEPS = [
    fam_irreg.perfect_past, fam_irreg.passive_past, fam_irreg.participle_as_past, fam_irreg.did_past,
    fam_irreg.to_past, fam_irreg.have_base, fam_irreg.regularized, fam_irreg.modal_past,
    fam_irreg.regular_have_base,
] + fam_constr.STEPS


def generate():
    for step in STEPS:
        step()
    ids = collections.Counter(r['id'] for r in core.RULES)
    core.PROBLEMS += [f'duplicate id {i}' for i, c in ids.items() if c > 1]
    return core.RULES


def e2e(engine):
    sys.path.insert(0, str(HERE))
    from probe import run
    bad = 0
    res = run([c[1] for c in core.E2E], engine)
    for (rid, wrong, right), (_, out, edits) in zip(core.E2E, res):
        if out != right:
            bad += 1
            print('POS', rid, '|', wrong, '->', out, '| want', right)
    res = run([c[1] for c in core.NEG], engine)
    for (rid, s), (_, out, edits) in zip(core.NEG, res):
        if out != s and any('tense.' in e[0] for e in edits):
            bad += 1
            print('NEG', rid, '|', s, '->', out)
    print(f'{len(core.E2E)} positives, {len(core.NEG)} negatives through the engine: {bad} wrong')
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=str(ROOT / 'engine/rules/packs/tense-aspect.json'))
    ap.add_argument('--e2e', metavar='ENGINE')
    a = ap.parse_args()
    rules = generate()
    if core.PROBLEMS:
        print('\n'.join(core.PROBLEMS[:80]))
        print(len(core.PROBLEMS), 'problems')
        sys.exit(1)
    with open(a.out, 'w') as f:
        json.dump(rules, f, indent=2, ensure_ascii=False)
        f.write('\n')
    fam = collections.Counter(r['id'].split('.')[1] for r in rules)
    print(len(rules), 'rules;', dict(fam))
    if a.e2e:
        sys.exit(1 if e2e(a.e2e) else 0)


if __name__ == '__main__':
    main()
