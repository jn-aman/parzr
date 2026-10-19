#!/usr/bin/env python3
"""Run cargo-audit on engine/Cargo.lock and fail on any advisory that reaches a shipped engine graph.

cargo-audit reads the whole lockfile, which also holds the maintainer-only `baseline-harper` feature's graph
(harper-core and about 500 crates behind the parzr-export-lexicon tool, never built into a release). This script
lists the crates of the two graphs that ship, the default one and the app bundle's (`--features external-tables`),
with `cargo tree`, then:
  - fails on a vulnerability, or an unsound or yanked crate, in a shipped graph;
  - warns (GitHub annotation) about unmaintained crates in a shipped graph and about anything outside them.
Needs cargo and cargo-audit on PATH. CI: the `dependencies` job in .github/workflows/ci-release.yml.
"""
import json, pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
MANIFEST = ROOT/'engine/Cargo.toml'
GRAPHS = {'default': [], 'external-tables': ['--features', 'external-tables']}


def shipped():
    crates = {}
    for graph, flags in GRAPHS.items():
        out = subprocess.run(['cargo', 'tree', '--manifest-path', str(MANIFEST), '--locked', '--target', 'all', '-e', 'normal,build',
                              '--prefix', 'none', '--format', '{p}', *flags], capture_output=True, text=True, check=True).stdout
        for line in out.splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[1].startswith('v'):
                crates.setdefault((parts[0], parts[1][1:]), set()).add(graph)
    return crates


def main():
    crates = shipped()
    print(f'{len(crates)} crates in the shipped graphs ({", ".join(GRAPHS)})')
    result = subprocess.run(['cargo', 'audit', '--json', '--file', str(ROOT/'engine/Cargo.lock')], capture_output=True, text=True)
    try:
        report = json.loads(result.stdout)
    except json.JSONDecodeError:
        sys.exit(f'cargo audit failed without a JSON report (exit {result.returncode}):\n{result.stderr[-2000:]}')
    findings = [('vulnerability', v) for v in report.get('vulnerabilities', {}).get('list', [])]
    for kind, items in (report.get('warnings') or {}).items():
        findings += [(kind, w) for w in items]
    failed = 0
    for kind, item in findings:
        package = item.get('package') or {}
        key = (package.get('name'), package.get('version'))
        advisory = item.get('advisory') or {}
        label = f"{kind} {advisory.get('id', '')} {key[0]} {key[1]}: {advisory.get('title', '')}".replace('  ', ' ')
        if key in crates and kind in ('vulnerability', 'unsound', 'yanked'):
            print(f'::error title=cargo-audit::{label} (shipped graph: {", ".join(sorted(crates[key]))})')
            failed += 1
        elif key in crates:
            print(f'::warning title=cargo-audit::{label} (shipped graph: {", ".join(sorted(crates[key]))})')
        else:
            print(f'  not shipped (baseline-harper only): {label}')
    if failed:
        sys.exit(f'{failed} advisory finding(s) in a shipped engine graph')
    print('cargo-audit: no vulnerable, unsound or yanked crate in a shipped engine graph')


if __name__ == '__main__':
    main()
