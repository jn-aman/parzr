#!/usr/bin/env python3
"""Write the GitHub release body for a tag: highlights, user-facing changes, downloads with direct links,
install and update steps, checksums, and the internal changes folded away.

usage: release_notes.py --version X.Y.Z [--git-range A..B] [--notes TEXT] [--critical] [--dist DIR] [--out FILE]

Commit subjects read "Area: what changed". An area such as CI, Tests or Docs marks an internal change
(is_internal); make-appcast.py uses the same test so the in-app update notes skip them too."""
import argparse, pathlib, re, subprocess, sys

REPO = 'jn-aman/parzr'
MIN_OS = '13'
# Fixed asset names: releases/latest/download/<name> always serves the newest release's file (website, README, docs).
LATEST = {'dmg': 'Parzr.dmg', 'vscode': 'parzr-vscode.vsix', 'browser': 'parzr-browser-extension.zip'}
INTERNAL = {'ci', 'tests', 'test', 'self tests', 'release workflow', 'docs', 'readme', 'website', 'benchmarks',
            'build', 'scripts', 'repo', 'chore', 'refactor', 'contributing', 'design', 'product'}
DOCS = f'https://github.com/{REPO}/blob/main/docs/integrations.md'


def area(subject):
    """'Menu bar: a window...' -> ('Menu bar', 'a window...'); no short prefix -> (None, subject)."""
    m = re.match(r'^([A-Za-z][\w +./-]{0,28}?):\s+(.+)$', subject)
    return (m.group(1), m.group(2)) if m else (None, subject)


def is_internal(subject):
    a = (area(subject)[0] or '').lower()
    return a in INTERNAL or a.endswith((' test', ' tests'))


def subjects(git_range):
    r = subprocess.run(['git', 'log', '--no-merges', '--format=%s', git_range], capture_output=True, text=True, check=True)
    return [s for s in r.stdout.splitlines() if s and not re.match(r'^Release v\d', s)]


def split_notes(notes):
    items = [re.sub(r'^[-*•]\s*', '', s.strip()) for s in re.split(r'\n| \| ', notes or '')]
    return [s for s in items if s]


def bullet(subject):
    a, rest = area(subject)
    rest = rest if rest.endswith(('.', '!', '?', ')')) else rest + '.'
    return f'- **{a}:** {rest[:1].upper()}{rest[1:]}' if a else f'- {rest}'


def size(dist, name):
    found = [p for p in (dist / name, dist / 'extensions' / name) if p.is_file()]
    if not found:
        return ''
    n = found[0].stat().st_size
    return f'{n / 1e6:.0f} MB' if n >= 1e6 else f'{max(1, round(n / 1e3))} KB'


def render(version, changes, notes=(), critical=False, dist=None, prev=None):
    tag, dl = f'v{version}', f'https://github.com/{REPO}/releases/download/v{version}'
    dist = pathlib.Path(dist) if dist else None
    user = [s for s in changes if not is_internal(s)]
    internal = [s for s in changes if is_internal(s)]
    out = []
    if critical:
        out += ['> [!IMPORTANT]', '> Critical update: Parzr installs it promptly and it cannot be skipped.', '']
    if notes:
        out += ['## Highlights', '', *(f'- {n}' for n in notes), '']
    out += ["## What's new" if not notes else '## All changes', '']
    out += [bullet(s) for s in user] or ['- Fixes and reliability improvements.']
    out.append('')
    if internal:
        out += [f'<details><summary>Under the hood ({len(internal)})</summary>', '', *(bullet(s) for s in internal), '', '</details>', '']

    def row(label, name, what):
        s = size(dist, name) if dist else ''
        return f'| {label} | [`{name}`]({dl}/{name}) | {what}{" · " + s if s else ""} |'
    out += ['## Download', '',
            '| | File | |', '| --- | --- | --- |',
            row('**Parzr for Mac**', f'Parzr-{version}.dmg', f'Apple Silicon · macOS {MIN_OS} or later'),
            row('VS Code extension *(optional)*', f'parzr-vscode-{version}.vsix', 'VS Code and Cursor'),
            row('Browser extension *(optional)*', f'parzr-browser-extension-{version}.zip', 'Chrome, Edge, Brave, Chromium, Firefox 140+'),
            '',
            '**New to Parzr?** Open the DMG, drag **Parzr** to **Applications** and open it. The welcome guide asks for Accessibility.',
            '',
            '**Already using Parzr?** It updates itself. To get this version now, choose **Check for Updates…** in the menu bar.',
            '',
            f'The extensions are never required. Install steps: [VS Code]({DOCS}#vs-code-and-cursor-extension), '
            f'[browser]({DOCS}#browser-extension-chrome-edge-brave-chromium-firefox).',
            '']
    sums = dist / 'SHA256SUMS' if dist else None
    if sums and sums.is_file():
        out += ['<details><summary>SHA-256 checksums</summary>', '', '```', sums.read_text().strip(), '```', '',
                'Check a download with `shasum -a 256 -c SHA256SUMS --ignore-missing` in the folder that holds it.',
                '', '</details>', '']
    if prev:
        out.append(f'**Full changelog:** [`{prev}...{tag}`](https://github.com/{REPO}/compare/{prev}...{tag})')
    return '\n'.join(out).rstrip() + '\n'


def main():
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--version', required=True)
    p.add_argument('--git-range', help='A..B: the commits in this release')
    p.add_argument('--notes', default='', help='highlights, one per line or separated by " | "')
    p.add_argument('--critical', action='store_true')
    p.add_argument('--dist', help='folder with the release files (sizes and SHA256SUMS)')
    p.add_argument('--out', help='write here instead of stdout')
    a = p.parse_args()
    changes = subjects(a.git_range) if a.git_range else []
    prev = a.git_range.split('..')[0] if a.git_range else None
    body = render(a.version, changes, split_notes(a.notes), a.critical, a.dist, prev)
    if a.out:
        pathlib.Path(a.out).write_text(body)
    else:
        sys.stdout.write(body)


if __name__ == '__main__':
    main()
