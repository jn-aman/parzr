#!/usr/bin/env python3
"""Matrices for a typo fuzz run: fixed % by perturbation type x frequency bucket, by word class and by position.

usage: typo-fuzz-report.py CORPUS.jsonl RESULTS_DIR [RESULTS_DIR ...]

RESULTS_DIR is a scripts/run-heldout-benchmark.py --output folder; every <layer>-results.jsonl in it is read. Several
folders (for example a before and an after run) are shown side by side as "before -> after".
"""
import collections, json, pathlib, sys

BUCKETS = ['top-100', 'top-1k', 'top-10k', 'rare']
TYPES = ['drop', 'add', 'substitute', 'transpose', 'double', 'undouble', 'space_in', 'space_del', 'case_start',
         'apostrophe_missing', 'apostrophe_extra']


def load(path):
    return [json.loads(l) for l in pathlib.Path(path).read_text().splitlines() if l.strip()]


def rates(corpus, results):
    """{(row, col): (fixed, n)} for the three tables of one layer."""
    meta = {it['id']: it for it in corpus}
    t = collections.defaultdict(lambda: [0, 0])
    for r in results:
        it = meta[r['id']]
        fixed = r['verdict'] == 'fixed'
        for key in ((it['category'], it['bucket']), (it['category'], 'all'), ('all', it['bucket']), ('all', 'all'),
                    ('class', it['word_class']), ('position', it['position']),
                    ('class-type', (it['category'], it['word_class']))):
            t[key][0] += fixed
            t[key][1] += 1
    return t


def cell(tables, key):
    parts = []
    for t in tables:
        f, n = t.get(key, (0, 0))
        parts.append(f'{100 * f / n:.0f}' if n else '-')
    n = tables[-1].get(key, (0, 0))[1]
    return (' -> '.join(parts) + '%' if n else '-') + (f' ({n})' if n else '')


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    corpus = load(sys.argv[1])
    dirs = [pathlib.Path(d) for d in sys.argv[2:]]
    layers = [l for l in ('rules', 'gec', 'deep') if all((d / f'{l}-results.jsonl').exists() for d in dirs)]
    for layer in layers:
        tables = [rates(corpus, load(d / f'{layer}-results.jsonl')) for d in dirs]
        last = tables[-1]
        print(f'\n### {layer}: fixed %, type x frequency bucket (items)\n')
        print('| Type | ' + ' | '.join(BUCKETS) + ' | all |')
        print('| --- |' + ' --- |' * (len(BUCKETS) + 1))
        for ty in TYPES + ['all']:
            if (ty, 'all') in last:
                print(f'| {ty} | ' + ' | '.join(cell(tables, (ty, b)) for b in BUCKETS + ['all']) + ' |')
        print(f'\n{layer} by word class: ' + ', '.join(f'{c} {cell(tables, ("class", c))}' for c in ('non-word', 'real-word', 'case')))
        print(f'{layer} by position: ' + ', '.join(f'{p} {cell(tables, ("position", p))}' for p in ('start', 'middle', 'end')))
        print(f'\n| {layer}: type | non-word | real-word |\n| --- | --- | --- |')
        for ty in TYPES:
            if (ty, 'all') in last:
                print(f'| {ty} | {cell(tables, ("class-type", (ty, "non-word")))} | {cell(tables, ("class-type", (ty, "real-word")))} |')
    for d in dirs:
        s = json.loads((d / 'summary.json').read_text())
        print(f'\n{d}: ' + ', '.join(f"{l} fixed {v['fix_rate']:.1%} caught {v['catch_rate']:.1%} false alarms {v['false_alarms']}/{s['clean']}"
                                    for l, v in s['layers'].items()))


if __name__ == '__main__':
    main()
