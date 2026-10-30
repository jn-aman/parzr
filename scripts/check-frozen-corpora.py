#!/usr/bin/env python3
"""Fail when a frozen benchmark file changes without its pin in benchmarks/frozen.json changing too.

The English challenge sets, the held-out set (its test split is never read for fixing), the typo-fuzz sets, the
names benchmark and the everyday regression items are frozen so that numbers stay comparable across builds. Every
file under the patterns below is pinned by SHA-256 and size. A changed, missing or new file fails the check; a
deliberate change (a new corpus version, never a quiet edit) is recorded with --update and reviewed in the diff.

usage: check-frozen-corpora.py [--update]
"""
import argparse, hashlib, json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
MANIFEST = ROOT / 'benchmarks/frozen.json'
PATTERNS = [
    'benchmarks/english-*.jsonl', 'benchmarks/english-*-manifest.json',
    'benchmarks/heldout/*.jsonl', 'benchmarks/heldout/TAXONOMY.md', 'benchmarks/heldout/src/*.py', 'benchmarks/heldout/src/**/*.txt',
    'benchmarks/typo-fuzz/*.jsonl', 'benchmarks/typo-fuzz/src/*.txt',
    'benchmarks/names/corpus.jsonl', 'benchmarks/names/heldout.jsonl',
    'benchmarks/everyday/items.jsonl',
    'benchmarks/tone/regression.jsonl', 'benchmarks/tone/regression-2.jsonl',
]


def pins():
    found = {}
    for pattern in PATTERNS:
        for path in sorted(ROOT.glob(pattern)):
            if path.is_file():
                # Hash only: the held-out test split is never opened for reading here, only digested.
                found[path.relative_to(ROOT).as_posix()] = {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'bytes': path.stat().st_size}
    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--update', action='store_true', help='record the current files (a deliberate corpus change)')
    args = parser.parse_args()
    now = pins()
    if args.update:
        MANIFEST.write_text(json.dumps({'about': 'SHA-256 pins of the frozen benchmark corpora; scripts/check-frozen-corpora.py checks them '
                                        '(CI verify) and --update records a deliberate change.', 'patterns': PATTERNS, 'files': now}, indent=2) + '\n')
        print(f'Pinned {len(now)} files in {MANIFEST.relative_to(ROOT)}')
        return
    pinned = json.loads(MANIFEST.read_text())['files']
    problems = [f'{p}: changed (sha256 {now[p]["sha256"][:12]}..., pinned {pinned[p]["sha256"][:12]}...)' for p in sorted(now.keys() & pinned.keys()) if now[p] != pinned[p]]
    problems += [f'{p}: missing' for p in sorted(pinned.keys() - now.keys())]
    problems += [f'{p}: new and not pinned' for p in sorted(now.keys() - pinned.keys())]
    for problem in problems:
        print(f'FROZEN CORPUS: {problem}', file=sys.stderr)
    if problems:
        sys.exit('Frozen benchmark files changed. Corpora are never edited to pass a gate; a deliberate new version is '
                 'pinned with python3 scripts/check-frozen-corpora.py --update (and its baselines updated on purpose).')
    print(f'Frozen corpora unchanged ({len(now)} files pinned).')


if __name__ == '__main__':
    main()
