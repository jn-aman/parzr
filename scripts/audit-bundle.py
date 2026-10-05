#!/usr/bin/env python3
"""Verify required runtime contents and reject embedded build-machine home paths."""
import argparse
import hashlib
import json
import pathlib
import plistlib
import re
import subprocess
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('app', type=pathlib.Path)
args = parser.parse_args()
app = args.app
required = ['Contents/MacOS/parzr', 'Contents/MacOS/parzr-engine', 'Contents/MacOS/parzr-native-host', 'Contents/MacOS/parzr-lsp', 'Contents/Frameworks/libparzr_engine.dylib', 'Contents/Resources/LICENSE', 'Contents/Resources/THIRD_PARTY_NOTICES', 'Contents/Resources/PrivacyInfo.xcprivacy', 'Contents/Resources/Integrations/extensions/browser/manifest.json', 'Contents/Resources/Integrations/extensions/vscode/package.json']
required += ['Contents/Resources/ThirdParty/EnglishFrequency-data.json', 'Contents/Resources/ThirdParty/EnglishFrequency-NOTICES.md', 'Contents/Resources/ThirdParty/EnglishFrequency-LICENSE.txt']
required += ['Contents/Frameworks/libparzr_model.dylib', 'Contents/Resources/Model/manifest.json', 'Contents/Resources/Model/llama-LICENSE.txt', 'Contents/Resources/ThirdParty/Qwen3.5-LICENSE.txt']
gector = 'Contents/Resources/Model/gector/'
required += [gector+name for name in ['manifest.json', 'vocab.json', 'merges.txt', 'added_tokens.json', 'labels.txt', 'verb-form-vocab.txt', 'gector.mlmodelc/coremldata.bin', 'gector.mlmodelc/model.mil', 'gector.mlmodelc/weights/weight.bin']]
required += ['Contents/Resources/Integrations/extensions/browser/editor.js', 'Contents/Resources/Integrations/extensions/browser/content.js', 'Contents/Resources/Integrations/extensions/browser/background.js']
for name in required:
    if not (app/name).is_file():
        sys.exit('Missing bundled runtime resource: '+name)
for name in ['Contents/MacOS/parzr','Contents/MacOS/parzr-engine','Contents/MacOS/parzr-native-host','Contents/MacOS/parzr-lsp','Contents/Frameworks/libparzr_engine.dylib','Contents/Frameworks/libparzr_model.dylib']:
    if subprocess.check_output(['lipo','-archs',str(app/name)],text=True).strip() != 'arm64':
        sys.exit('Parzr requires Apple Silicon only: '+name)
info = plistlib.loads((app/'Contents/Info.plist').read_bytes())
model_info = json.loads((app/'Contents/Resources/Model/manifest.json').read_text())
model_path = app/'Contents/Resources/Model'/model_info['file']
with model_path.open('rb') as stream:
    if hashlib.file_digest(stream, 'sha256').hexdigest() != model_info['sha256']:
        sys.exit('Bundled model hash verification failed.')
gector_info = json.loads((app/gector/'manifest.json').read_text())
for name, expected in gector_info['files'].items():
    with (app/gector/name).open('rb') as stream:
        if hashlib.file_digest(stream, 'sha256').hexdigest() != expected:
            sys.exit('Bundled GECToR file hash verification failed: '+name)
if len((app/gector/'labels.txt').read_text().splitlines()) != 5002:
    sys.exit('Bundled GECToR labels.txt must have 5002 lines.')
if info['CFBundleExecutable'] != 'parzr' or info['CFBundleName'] != 'Parzr':
    sys.exit('Unexpected application identity.')
issues=[]
for path in app.rglob('*'):
    if not path.is_file():
        continue
    # Scan large weights in bounded chunks instead of allocating a second model in RAM.
    found = False
    with path.open('rb') as stream:
        tail = b''
        while block := stream.read(1024*1024):
            data = tail + block
            if re.search(rb'(?:/Users/|/home/)[A-Za-z0-9_.-]+/', data): found = True; break
            tail = data[-512:]
    if found:
        issues.append(str(path.relative_to(app)))
if issues:
    for name in issues:
        print('Embedded private build path in '+name+'; value omitted.', file=sys.stderr)
    sys.exit(1)
subprocess.run(['codesign', '--verify', '--deep', '--strict', str(app)], check=True, capture_output=True)
print('Bundle audit passed: complete runtime, valid signature, no embedded home paths.')
