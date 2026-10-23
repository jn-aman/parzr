#!/usr/bin/env python3
"""Which (family, verb) cells does an engine built WITHOUT the tense pack already fix?  Writes data/coverage*.json.

    python3 scripts/tense-pack/coverage.py --base-engine PATH/to/parzr-engine-without-the-pack
"""
import argparse, json, os, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from verbs import ALL_ROWS
from regular import REG_ROWS
from probe import run


def reg(b):
    return b + 'd' if b.endswith('e') else b + 'ed'


def frames(v):
    d = {}
    if v['past'] != v['part']:
        d['P'] = [(f"She has {v['past']} {v['tail']}.", f"She has {v['part']} {v['tail']}."),
                  (f"Have you ever {v['past']} {v['tail']}?", f"Have you ever {v['part']} {v['tail']}?"),
                  (f"They would have {v['past']} {v['tail']}.", f"They would have {v['part']} {v['tail']}.")]
        if v['kind'] != 'I':
            d['PS'] = [(f"It was {v['past']} by the manager.", f"It was {v['part']} by the manager."),
                       (f"It has been {v['past']} by the manager.", f"It has been {v['part']} by the manager.")]
    if v['past'] != v['base']:
        d['D'] = [(f"She didn't {v['past']} {v['tail']}.", f"She didn't {v['base']} {v['tail']}."),
                  (f"Did you {v['past']} {v['tail']}?", f"Did you {v['base']} {v['tail']}?")]
        d['T'] = [(f"He wants to {v['past']} {v['tail']}.", f"He wants to {v['base']} {v['tail']}.")]
        d['MP'] = [(f"I will {v['past']} {v['tail']}.", f"I will {v['base']} {v['tail']}.")]
    if v['part'] != v['base']:
        d['PB'] = [(f"I have already {v['base']} twice.", f"I have already {v['part']} twice.")]
    d['OR'] = [(f"He {reg(v['base'])} {v['tail']} yesterday.", f"He {v['past']} {v['tail']} yesterday.")]
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base-engine', required=True)
    a = ap.parse_args()
    data = HERE / 'data'
    cases = []
    for v in ALL_ROWS:
        for fam, fr in frames(v).items():
            for w, r in fr:
                cases.append((fam, v['base'], w, r))
    for v in REG_ROWS:
        cases.append(('PBR', v['base'], f"I have already {v['base']} twice.", f"I have already {v['part']} twice."))
    res = run([c[2] for c in cases], a.base_engine)
    ok = {}
    for (fam, b, w, r), (_, out, _) in zip(cases, res):
        ok.setdefault((fam, b), []).append(out == r)
    cov = {}
    for (fam, b), flags in ok.items():
        if all(flags):
            cov.setdefault(fam, []).append(b)
    json.dump(cov, open(data / 'coverage.json', 'w'), indent=1)
    # perfect with a past-time marker: "I have seen it yesterday"
    yt = [(v['base'], f"I have {v['part']} it yesterday.", f"I {v['past']} it yesterday.") for v in ALL_ROWS]
    res = run([c[1] for c in yt], a.base_engine)
    json.dump([b for (b, w, r), (_, o, _) in zip(yt, res) if o == r], open(data / 'coverage_yt.json', 'w'))
    # fronted past time with a present verb: "Last night I go ..."
    import fam_front
    fr = [(b, f"Last night I {b} {tail}.", f"Last night I {p} {tail}.") for b, t, p, tail in fam_front.front_rows()]
    res = run([c[1] for c in fr], a.base_engine)
    json.dump([b for (b, w, r), (_, o, _) in zip(fr, res) if o == r], open(data / 'coverage_front.json', 'w'))
    print({k: len(v) for k, v in cov.items()})


if __name__ == '__main__':
    main()
