#!/usr/bin/env python3
"""Bump the Parzr version in every file check-release-version.py compares.

Usage: bump-version.py <patch|minor|major|X.Y.Z> [--dry-run]
Targeted text edits only, so file formatting is preserved. All edits are
validated in memory first; nothing is written unless every file checks out.
"""
import difflib, json, pathlib, plistlib, re, subprocess, sys, tomllib

ROOT = pathlib.Path(__file__).resolve().parent.parent
SEMVER = re.compile(r'(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)')


def parse(v):
    if not SEMVER.fullmatch(v):
        sys.exit(f'Not a plain X.Y.Z version: {v!r}')
    return tuple(int(p) for p in v.split('.'))


def sub_once(text, pattern, repl, label):
    out, n = re.subn(pattern, repl, text, count=1, flags=re.S)
    if n != 1:
        sys.exit(f'Could not locate the version in {label}.')
    return out


def main():
    args = [a for a in sys.argv[1:] if a != '--dry-run']
    dry = '--dry-run' in sys.argv[1:]
    if len(args) != 1:
        sys.exit(__doc__)
    cargo_path = ROOT / 'engine/Cargo.toml'
    cargo = cargo_path.read_text()
    old = tomllib.loads(cargo)['package']['version']
    ma, mi, pa = parse(old)
    arg = args[0]
    new = {'patch': f'{ma}.{mi}.{pa + 1}', 'minor': f'{ma}.{mi + 1}.0', 'major': f'{ma + 1}.0.0'}.get(arg, arg)
    if parse(new) <= parse(old):
        sys.exit(f'Refusing to go backwards or stand still: {old} -> {new}')
    tags = subprocess.run(['git', 'tag', '-l', f'v{new}'], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    if tags.strip():
        sys.exit(f'Git tag v{new} already exists.')

    edits = {}  # relative path -> new text
    # engine/Cargo.toml: first `version = "..."` after [package], before the next table.
    edits['engine/Cargo.toml'] = sub_once(
        cargo, r'(\[package\][^\[]*?\nversion\s*=\s*")[^"]*(")', rf'\g<1>{new}\g<2>', 'engine/Cargo.toml')
    # engine/Cargo.lock: only the parzr-engine package entry.
    lock = (ROOT / 'engine/Cargo.lock').read_text()
    edits['engine/Cargo.lock'] = sub_once(
        lock, r'(\[\[package\]\]\nname = "parzr-engine"\nversion = ")[^"]*(")', rf'\g<1>{new}\g<2>', 'engine/Cargo.lock')
    # Info.plist: short version string; CFBundleVersion is a build counter, so increment it.
    plist = (ROOT / 'resources/Info.plist').read_text()
    plist = sub_once(plist, r'(<key>CFBundleShortVersionString</key>\s*<string>)[^<]*(</string>)', rf'\g<1>{new}\g<2>', 'Info.plist')
    m = re.search(r'(<key>CFBundleVersion</key>\s*<string>)([^<]*)(</string>)', plist)
    if m:
        build = m.group(2).strip()
        if build.isdigit():  # monotonically increasing integer convention
            plist = plist[:m.start(2)] + str(int(build) + 1) + plist[m.end(2):]
        else:  # dotted convention: mirror the marketing version
            plist = plist[:m.start(2)] + new + plist[m.end(2):]
    edits['resources/Info.plist'] = plist
    # JSON files: first top-level "version" key ("manifest_version" does not match the quoted pattern).
    for rel in ('extensions/browser/manifest.json', 'extensions/vscode/package.json'):
        text = (ROOT / rel).read_text()
        edits[rel] = sub_once(text, r'("version"\s*:\s*")[^"]*(")', rf'\g<1>{new}\g<2>', rel)

    # Validate every edit parses and carries the new version before touching disk.
    assert tomllib.loads(edits['engine/Cargo.toml'])['package']['version'] == new
    assert plistlib.loads(edits['resources/Info.plist'].encode())['CFBundleShortVersionString'] == new
    for rel in ('extensions/browser/manifest.json', 'extensions/vscode/package.json'):
        assert json.loads(edits[rel])['version'] == new, rel
    locked = [p for p in tomllib.loads(edits['engine/Cargo.lock'])['package'] if p['name'] == 'parzr-engine']
    assert len(locked) == 1 and locked[0]['version'] == new

    for rel, text in edits.items():
        before = (ROOT / rel).read_text()
        diff = ''.join(difflib.unified_diff(before.splitlines(True), text.splitlines(True), f'a/{rel}', f'b/{rel}', n=0))
        print(diff, end='' if diff.endswith('\n') else '\n')
        if not dry:
            (ROOT / rel).write_text(text)
    if dry:
        print(f'Dry run: {old} -> {new}, no files written.')
    else:
        subprocess.run([sys.executable, str(ROOT / 'scripts/check-release-version.py')], check=True)
    print(new)


if __name__ == '__main__':
    main()
