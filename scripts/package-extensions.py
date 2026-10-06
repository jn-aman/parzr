#!/usr/bin/env python3
"""Build the optional extension files for a release into dist/extensions (or --out):
parzr-vscode-X.Y.Z.vsix and parzr-browser-extension-X.Y.Z.zip, versioned from the manifests."""
import argparse, json, pathlib, subprocess, sys, zipfile
ROOT = pathlib.Path(__file__).resolve().parents[1]
VSCE = '@vscode/vsce@4.0.0'  # pinned; needs Node 22+
parser = argparse.ArgumentParser()
parser.add_argument('--out', type=pathlib.Path, default=ROOT / 'dist/extensions')
args = parser.parse_args()
out = args.out.resolve(); out.mkdir(parents=True, exist_ok=True)
vscode, browser = ROOT / 'extensions/vscode', ROOT / 'extensions/browser'
version = json.loads((vscode / 'package.json').read_text())['version']
if json.loads((browser / 'manifest.json').read_text())['version'] != version: sys.exit('Extension versions differ; run scripts/check-release-version.py.')
vsix = out / f'parzr-vscode-{version}.vsix'
subprocess.run(['npx', '--yes', VSCE, 'package', '--no-dependencies', '--allow-missing-repository', '--out', str(vsix)], cwd=vscode, check=True)
archive = out / f'parzr-browser-extension-{version}.zip'
with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
    for path in sorted(p for p in browser.rglob('*') if p.is_file() and not p.name.startswith('.')):
        info = zipfile.ZipInfo(str(path.relative_to(browser)), (2026, 1, 1, 0, 0, 0))  # fixed time: the same sources give the same zip
        info.external_attr = 0o644 << 16; info.compress_type = zipfile.ZIP_DEFLATED
        z.writestr(info, path.read_bytes())
for f in (vsix, archive): print(f'{f.name}  {f.stat().st_size} bytes')
