#!/usr/bin/env python3
"""Fail when `swift test` skipped a test that is not on the allowlist (mac/Tests/expected-skips.txt).

A test that needs a model, the engine library or a pack skips itself when they are missing. On CI everything is
fetched, so a skip there means a check silently stopped running (a renamed variable, a pack that did not install).
Only the tests listed in the allowlist, each with its reason, may skip.

usage: swift test ... 2>&1 | tee dist/qa/swift-test.log; python3 scripts/check-xctest-skips.py dist/qa/swift-test.log
"""
import argparse, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKIPPED = re.compile(r"Test Case '-\[(\w+)\.(\w+) (\w+)\]' skipped")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('log', type=pathlib.Path)
    parser.add_argument('--allow', type=pathlib.Path, default=ROOT / 'mac/Tests/expected-skips.txt')
    args = parser.parse_args()
    log = args.log.read_text(errors='replace')
    if not re.search(r"Test Suite '(All|Selected) tests' (passed|failed)", log):
        sys.exit(f'{args.log}: no XCTest summary found (did swift test run?)')
    allowed = {line.split('#', 1)[0].strip() for line in args.allow.read_text().splitlines()} - {''}
    skipped = {f'{m[0]}.{m[1]}/{m[2]}' for m in SKIPPED.findall(log)}
    unexpected = sorted(skipped - allowed)
    for name in sorted(allowed - skipped):
        print(f'note: {name} is allowed to skip but ran', file=sys.stderr)
    for name in unexpected:
        print(f'UNEXPECTED SKIP: {name}', file=sys.stderr)
    if unexpected:
        sys.exit(f'{len(unexpected)} test(s) skipped that should run here: give them what they need, or add them to '
                 f'{args.allow.relative_to(ROOT)} with the reason.')
    print(f'XCTest skips as expected ({len(skipped)} skipped, all on the allowlist).')


if __name__ == '__main__':
    main()
