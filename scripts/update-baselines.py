#!/usr/bin/env python3
"""Record new quality baselines in benchmarks/baselines.json, on purpose and with a reason.

The quality gates (scripts/quality_gates.py) fail a run that fixes less, raises more false alarms or gets slower or
bigger than the numbers recorded here. Raise a baseline when a change lifts a score (so later changes cannot quietly
give the gain back); lower one only for a deliberate, explained trade-off, never to let a regression through.

usage: update-baselines.py SUITE SUMMARY --reason TEXT [--quality-only | --performance-only] [--machine KEY]

  SUITE     heldout-test | typo-fuzz-test | names | everyday
  SUMMARY   the run's summary: dist/qa/heldout/summary.json, dist/qa/typo-fuzz/summary.json,
            dist/qa/names/report.json or dist/qa/everyday/summary.json. Sealed test sets are scored only on CI:
            download the verify job's artifact (gh run download RUN -n quality-summaries-SHA) and pass its file.
  --machine the performance baseline to write (default: the one the summary was measured on, "ci" for CI's
            runners). Latency and memory are compared only between runs on the same kind of machine.

The everyday set's per-item labels (benchmarks/everyday/baseline.json) are written by
`scripts/everyday-batch.py gate --update`; this script records its counts and its performance.
"""
import argparse, datetime, json, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import quality_gates  # noqa: E402

SUITES = ('heldout-test', 'typo-fuzz-test', 'names', 'everyday')


def quality(suite, s):
    if suite in ('heldout-test', 'typo-fuzz-test'):
        return {'layers': {layer: {'errors': s['errors'], 'clean': s['clean'], 'fixed': d['fixed'], 'fix_rate': d['fix_rate'],
                                   'false_alarms': d['false_alarms'], 'false_alarm_rate': d['false_alarm_rate']}
                           for layer, d in s['layers'].items()}}
    if suite == 'names':
        breakdown = s['breakdown']
        return {'controls': s['controls'], 'control_fixed': s['control_fixed'], 'control_recall': round(s['control_recall'], 4),
                'errors': s['errors'], 'damaged': {k: breakdown.get(k, {}).get('damaged', 0) for k in ('all', 'case:lower', 'heldout')},
                'names': {k: breakdown.get(k, {}).get('total', 0) for k in ('all', 'case:lower', 'heldout')}}
    return {'items': s['items'], 'paths': {p: {'counts': d['counts'], 'correct_rate': d['correct_rate']} for p, d in s['paths'].items()}}


def performance(suite, s):
    if suite in ('heldout-test', 'typo-fuzz-test'):
        return {layer: {'p50_ms': d['latency']['p50_ms'], 'p95_ms': d['latency']['p95_ms'], 'max_rss_mb': d.get('max_rss_mb')}
                for layer, d in s['layers'].items()}
    if suite == 'names':
        return {'engine': {'p50_ms': s['latency']['p50_ms'], 'p95_ms': s['latency']['p95_ms'], 'max_rss_mb': s.get('max_rss_mb')}}
    return {p: {'p50_ms': d['latency']['p50_ms'], 'p95_ms': d['latency']['p95_ms'], 'max_rss_mb': s.get('max_rss_mb')} for p, d in s['paths'].items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0], formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    parser.add_argument('suite', choices=SUITES)
    parser.add_argument('summary', type=pathlib.Path)
    parser.add_argument('--reason', required=True, help='why the baseline moves (kept in the file)')
    which = parser.add_mutually_exclusive_group()
    which.add_argument('--quality-only', action='store_true')
    which.add_argument('--performance-only', action='store_true')
    parser.add_argument('--machine', help='performance baseline key (default: the summary\'s machine)')
    args = parser.parse_args()
    s = json.loads(args.summary.read_text())
    if args.suite == 'heldout-test' and s.get('split') != 'test':
        sys.exit('heldout-test takes a --split test summary (scored on CI)')
    data = quality_gates.load()
    data.setdefault('suites', {})
    data.setdefault('performance', {})
    stamp = {'updated': datetime.date.today().isoformat(), 'reason': args.reason}
    if not args.performance_only:
        old = data['suites'].get(args.suite)
        data['suites'][args.suite] = {**stamp, **quality(args.suite, s)}
        print(f'{args.suite}: quality baseline {"replaced" if old else "recorded"}')
    if not args.quality_only:
        machine = args.machine or s.get('machine')
        if not machine:
            sys.exit('The summary does not say which machine measured it: pass --machine')
        for key, values in performance(args.suite, s).items():
            data['performance'].setdefault(machine, {})[f'{args.suite}/{key}'] = values
        print(f'{args.suite}: performance baseline for {machine} recorded')
    quality_gates.BASELINES.write_text(json.dumps(data, indent=2) + '\n')


if __name__ == '__main__':
    main()
