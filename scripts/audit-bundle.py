#!/usr/bin/env python3
"""Verify required runtime contents, that no model weights ship in the app, and reject embedded build-machine home paths."""
import argparse
import base64
import hashlib
import json
import os
import pathlib
import plistlib
import re
import subprocess
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('app', type=pathlib.Path)
parser.add_argument('--qa', action='store_true', help='a QA build (scripts/build.py --qa): its self-test modes are expected')
args = parser.parse_args()
app = args.app
required = ['Contents/MacOS/parzr', 'Contents/MacOS/parzr-engine', 'Contents/MacOS/parzr-native-host', 'Contents/MacOS/parzr-lsp', 'Contents/Frameworks/libparzr_engine.dylib', 'Contents/Resources/LICENSE', 'Contents/Resources/THIRD_PARTY_NOTICES', 'Contents/Resources/PrivacyInfo.xcprivacy', 'Contents/Resources/Integrations/extensions/browser/manifest.json', 'Contents/Resources/Integrations/extensions/vscode/package.json']
required += ['Contents/Resources/ThirdParty/EnglishFrequency-data.json', 'Contents/Resources/ThirdParty/EnglishFrequency-NOTICES.md', 'Contents/Resources/ThirdParty/EnglishFrequency-LICENSE.txt']
required += ['Contents/Frameworks/libparzr_model.dylib', 'Contents/Resources/ThirdParty/llama-LICENSE.txt', 'Contents/Resources/ThirdParty/Qwen3.5-LICENSE.txt']
required += ['Contents/Resources/ThirdParty/Pow-LICENSE.txt', 'Contents/Resources/ThirdParty/Sparkle-LICENSE.txt']
required += ['Contents/Resources/ThirdParty/spaCy-MIT-LICENSE.txt', 'Contents/Resources/ThirdParty/RoBERTa-fairseq-MIT-LICENSE.txt', 'Contents/Resources/ThirdParty/similar-2.7.0/LICENSE', 'Contents/Resources/ThirdParty/unicode-segmentation-1.13.3/LICENSE-MIT', 'Contents/Resources/ThirdParty/unicode-segmentation-1.13.3/LICENSE-APACHE']
required += ['Contents/Resources/parzr-tables.dat']
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
# The engine's compiled tables ship once (Contents/Resources/parzr-tables.dat, engine/src/tables.rs):
# no engine binary embeds its own copy, and the bundled engine accepts the bundled file.
for name in ['Contents/MacOS/parzr-engine','Contents/MacOS/parzr-native-host','Contents/MacOS/parzr-lsp','Contents/Frameworks/libparzr_engine.dylib']:
    if (app/name).stat().st_size > 12_000_000:
        sys.exit(f'{name} embeds the engine tables; build the engine with --features external-tables.')
probe = '{"text":"teh","tokens":[{"start_utf16":0,"end_utf16":3,"pos":"Noun"}]}\n'
environment = {k: v for k, v in os.environ.items() if k != 'PARZR_TABLES_PATH'}
answer = subprocess.run([str(app/'Contents/MacOS/parzr-engine')], input=probe, capture_output=True, text=True, env=environment).stdout
if '"error"' in answer or '"text"' not in answer:
    sys.exit('The bundled engine does not accept Contents/Resources/parzr-tables.dat: '+answer[:200])
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
rpaths = re.findall(r'cmd LC_RPATH\n\s+cmdsize \d+\n\s+path (.+?) \(offset \d+\)', subprocess.check_output(['otool','-l',str(app/'Contents/MacOS/parzr')],text=True))
if '@executable_path/../Frameworks' not in rpaths: sys.exit('The app executable cannot find Contents/Frameworks (missing rpath).')
# Nothing beside the executable (@loader_path) or outside the OS and the bundle's Frameworks is searched through @rpath.
if set(rpaths) - {'@executable_path/../Frameworks', '/usr/lib/swift'}: sys.exit('Unexpected LC_RPATH in the app executable: '+', '.join(sorted(set(rpaths) - {'@executable_path/../Frameworks', '/usr/lib/swift'})))
# QA modes are compiled out of a release build (#if DEBUG || PARZR_QA): none of their flags, nor the fixture override, may be in any of its code.
qa_markers = [b'--web-composer-test', b'--docs-test', b'--integration-test', b'--typing-test', b'--paste-test', b'--grammar-typing-test', b'--ui-test',
              b'--editor-typing-test', b'--own-editor-test', b'--click-test', b'--models-test', b'--snapshot', b'--update-test', b'PARZR_FIXTURE_PATH', b'updateTestMode']
if not args.qa:
    found = set()
    for path in sorted(app.rglob('*')):
        if path.is_symlink() or not path.is_file() or path.stat().st_size < 4: continue
        with path.open('rb') as stream: magic = stream.read(4)
        if magic not in (b'\xcf\xfa\xed\xfe', b'\xca\xfe\xba\xbe'): continue
        data = path.read_bytes()
        found |= {(marker.decode(), str(path.relative_to(app))) for marker in qa_markers if marker in data}
    if found: sys.exit('A release build must not carry QA modes: '+', '.join(f'{m} in {p}' for m, p in sorted(found)))
    # The release engine is built without its dev-overrides feature, and the native runtime reads no environment: no PARZR_* name is left in them.
    for name in ['Contents/MacOS/parzr-engine', 'Contents/MacOS/parzr-native-host', 'Contents/MacOS/parzr-lsp', 'Contents/Frameworks/libparzr_engine.dylib', 'Contents/Frameworks/libparzr_model.dylib']:
        if b'PARZR_' in (app/name).read_bytes(): sys.exit(name+' still reads PARZR_* development overrides; build the engine without the dev-overrides feature.')
sparkle_license = (app/'Contents/Resources/ThirdParty/Sparkle-LICENSE.txt').read_text()
for part in ['Andy Matuschak', 'bsdiff', 'sais-lite', 'ed25519', 'SUSignatureVerifier']:
    if part not in sparkle_license: sys.exit('Sparkle-LICENSE.txt is incomplete (missing '+part+')')
# Update trust and privacy settings: HTTPS feed, a 32-byte EdDSA public key, no system profile, an hourly check.
feed, key = info.get('SUFeedURL', ''), info.get('SUPublicEDKey', '')
if not feed.startswith('https://') or len(base64.b64decode(key, validate=True)) != 32: sys.exit('Info.plist needs an https SUFeedURL and a 32-byte SUPublicEDKey.')
# Suggestion reports go only to an HTTPS endpoint (see worker/); a build without the key never reports.
reports = info.get('ParzrReportsURL')
if reports is not None and not str(reports).startswith('https://'): sys.exit('ParzrReportsURL in Info.plist must be an https URL.')
# The feed itself is EdDSA-signed by scripts/make-appcast.py (sign_update), and each archive is verified before it is extracted.
if info.get('SURequireSignedFeed') is not True or info.get('SUVerifyUpdateBeforeExtraction') is not True: sys.exit('Info.plist must set SURequireSignedFeed and SUVerifyUpdateBeforeExtraction (the release feed is signed).')
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
print('Bundle audit passed: complete runtime, no model weights, valid signature, no embedded home paths'+(' (QA build: self-test modes present).' if args.qa else ', no QA modes.'))
