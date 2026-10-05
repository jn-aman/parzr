#!/usr/bin/env python3
import json, os, pathlib, plistlib, sys, tomllib
root=pathlib.Path(__file__).resolve().parent.parent
version=tomllib.loads((root/'engine/Cargo.toml').read_text())['package']['version']
info=plistlib.loads((root/'resources/Info.plist').read_bytes())
for label,value in [('app',info['CFBundleShortVersionString']),('browser',json.loads((root/'extensions/browser/manifest.json').read_text())['version']),('vscode',json.loads((root/'extensions/vscode/package.json').read_text())['version'])]:
 if value!=version:sys.exit(f'{label} version {value} does not match engine {version}.')
if os.environ.get('GITHUB_REF_TYPE')=='tag' and os.environ.get('GITHUB_REF_NAME')!='v'+version:sys.exit('Release tag must match the app/engine/extension version: v'+version)
print('Release version verified:',version)
