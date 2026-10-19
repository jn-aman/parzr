#!/usr/bin/env python3
"""Verify required runtime contents, that no model weights ship in the app, and reject embedded build-machine home paths."""
import argparse
import base64
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
required += ['Contents/Frameworks/libparzr_model.dylib', 'Contents/Resources/ThirdParty/llama-LICENSE.txt', 'Contents/Resources/ThirdParty/Qwen3.5-LICENSE.txt']
required += ['Contents/Resources/ThirdParty/Pow-LICENSE.txt', 'Contents/Resources/ThirdParty/Sparkle-LICENSE.txt']
required += ['Contents/Resources/Integrations/extensions/browser/editor.js', 'Contents/Resources/Integrations/extensions/browser/content.js', 'Contents/Resources/Integrations/extensions/browser/background.js']
for name in required:
    if not (app/name).is_file():
        sys.exit('Missing bundled runtime resource: '+name)
# Model weights are downloaded on demand (engine/models.json), never bundled: no Model folder, no file the
# manifest pins (by name or by hash), no model format and no large opaque blob anywhere in the app.
if (app/'Contents/Resources/Model').exists(): sys.exit('Contents/Resources/Model must not exist: model weights are downloaded, not bundled.')
manifest = json.loads((pathlib.Path(__file__).resolve().parent.parent/'engine/models.json').read_text())
pinned = {f['sha256'] for pack in manifest['packs'] for f in pack['files']}
names = {pathlib.PurePosixPath(f['path']).name for pack in manifest['packs'] for f in pack['files'] if f['bytes'] > 1_000_000}
weights = []
for path in app.rglob('*'):
    if path.is_symlink() or not path.is_file(): continue
    relative = str(path.relative_to(app))
    if path.suffix.lower() in {'.gguf', '.ggml', '.safetensors', '.mlmodel', '.mlpackage', '.onnx', '.pt', '.bin'} or '.mlmodelc' in relative or path.name in names:
        weights.append(relative); continue
    if path.stat().st_size > 1_000_000:
        with path.open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() in pinned: weights.append(relative)
if weights: sys.exit('Model weights must not ship in the app: '+', '.join(sorted(weights)))
# Without weights the app is code, licences and integrations: keep it well under 100 MB.
size = sum(p.stat().st_size for p in app.rglob('*') if p.is_file() and not p.is_symlink())
if size > 100_000_000: sys.exit(f'The app is {size/1e6:.0f} MB; it must stay under 100 MB (did model weights come back?).')
# The self tests' fixture editor (mac/Sources/ParzrFixture) is test-only and never ships.
if any('ParzrFixture' in path.name for path in app.rglob('*')): sys.exit('The test-only ParzrFixture editor must not be bundled.')
for name in ['Contents/MacOS/parzr','Contents/MacOS/parzr-engine','Contents/MacOS/parzr-native-host','Contents/MacOS/parzr-lsp','Contents/Frameworks/libparzr_engine.dylib','Contents/Frameworks/libparzr_model.dylib']:
    if subprocess.check_output(['lipo','-archs',str(app/name)],text=True).strip() != 'arm64':
        sys.exit('Parzr requires Apple Silicon only: '+name)
info = plistlib.loads((app/'Contents/Info.plist').read_bytes())
# Sparkle: the framework is complete, arm64-only, free of sandbox-only XPC services, and its installer helpers are hardened.
sparkle = app/'Contents/Frameworks/Sparkle.framework'
for name in ['Versions/B/Sparkle', 'Versions/B/Autoupdate', 'Versions/B/Updater.app/Contents/MacOS/Updater']:
    if not (sparkle/name).is_file(): sys.exit('Missing Sparkle component: '+name)
    if subprocess.check_output(['lipo','-archs',str(sparkle/name)],text=True).strip() != 'arm64': sys.exit('Sparkle must be arm64 only: '+name)
if list(sparkle.rglob('*.xpc')) or (sparkle/'XPCServices').exists(): sys.exit('Sparkle XPC services must not ship in a non-sandboxed app.')
for name in ['Versions/B/Autoupdate', 'Versions/B/Updater.app']:
    if 'runtime' not in subprocess.run(['codesign','-dvv',str(sparkle/name)],capture_output=True,text=True).stderr.split('flags=')[-1].split('\n')[0]:
        sys.exit('Sparkle helper is not signed with the hardened runtime: '+name)
if '@executable_path/../Frameworks' not in subprocess.check_output(['otool','-l',str(app/'Contents/MacOS/parzr')],text=True): sys.exit('The app executable cannot find Contents/Frameworks (missing rpath).')
sparkle_license = (app/'Contents/Resources/ThirdParty/Sparkle-LICENSE.txt').read_text()
for part in ['Andy Matuschak', 'bsdiff', 'sais-lite', 'ed25519', 'SUSignatureVerifier']:
    if part not in sparkle_license: sys.exit('Sparkle-LICENSE.txt is incomplete (missing '+part+')')
# Update trust and privacy settings: HTTPS feed, a 32-byte EdDSA public key, no system profile, a daily check.
feed, key = info.get('SUFeedURL', ''), info.get('SUPublicEDKey', '')
if not feed.startswith('https://') or len(base64.b64decode(key, validate=True)) != 32: sys.exit('Info.plist needs an https SUFeedURL and a 32-byte SUPublicEDKey.')
# Suggestion reports go only to an HTTPS endpoint (see worker/); a build without the key never reports.
reports = info.get('ParzrReportsURL')
if reports is not None and not str(reports).startswith('https://'): sys.exit('ParzrReportsURL in Info.plist must be an https URL.')
if info.get('SUEnableSystemProfiling') is not False or info.get('SUEnableAutomaticChecks') is not True or info.get('SUScheduledCheckInterval') != 3600: sys.exit('Update settings in Info.plist differ from the privacy decisions (no profile, hourly automatic checks).')
# Every Mach-O in the bundle must carry a valid signature of its own (a deep verify alone would not name an unsigned helper).
for path in sorted(app.rglob('*')):
    if path.is_symlink() or not path.is_file() or path.stat().st_size < 4: continue
    with path.open('rb') as stream: magic = stream.read(4)
    if magic in (b'\xcf\xfa\xed\xfe', b'\xca\xfe\xba\xbe') and subprocess.run(['codesign','--verify','--strict',str(path)],capture_output=True).returncode != 0:
        sys.exit('Unsigned or invalidly signed nested code: '+str(path.relative_to(app)))
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
print('Bundle audit passed: complete runtime, no model weights, valid signature, no embedded home paths.')
