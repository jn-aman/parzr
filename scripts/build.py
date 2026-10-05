#!/usr/bin/env python3
"""Reproducible macOS app builder. Never silently downgrade a requested release signature."""
import argparse, hashlib, json, os, pathlib, plistlib, shutil, subprocess, sys, shlex
ROOT = pathlib.Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser()
parser.add_argument('--sign', action='store_true', help='Require Developer ID Application signing')
parser.add_argument('--identity', default=os.environ.get('PARZR_SIGNING_IDENTITY'))
parser.add_argument('--bundle-id', default=os.environ.get('PARZR_BUNDLE_ID','app.parzr.desktop'))
parser.add_argument('--skip-build', action='store_true')
args = parser.parse_args()
if args.sign and (not args.identity or not args.identity.startswith('Developer ID Application:')):
    sys.exit('Developer ID signing requires --identity "Developer ID Application: Name (TEAMID)". No unsigned fallback will be produced.')
def run(command, **kwargs):
    subprocess.run([str(x) for x in command], cwd=ROOT, check=True, **kwargs)
version = plistlib.loads((ROOT/'resources/Info.plist').read_bytes())['CFBundleShortVersionString']
for name in ['THIRD_PARTY_NOTICES', 'LICENSE', 'engine/rules/frequency.json']:
    if not (ROOT/name).is_file(): sys.exit('Missing required build source: '+name)
dist = ROOT/'dist'; dist.mkdir(exist_ok=True)
app = dist/'Parzr.app'
architectures = ['aarch64-apple-darwin']
if not args.skip_build:
    model_command = [sys.executable, ROOT/'scripts/prepare-model.py']
    run(model_command)
    for target in architectures:
        if target: run(['rustup','target','add',target])
        command = ['cargo','build','--release','--locked','--manifest-path','engine/Cargo.toml']
        if target: command += ['--target',target]
        environment = os.environ.copy(); environment['MACOSX_DEPLOYMENT_TARGET']='13.0'
        rustflags = environment.get('CARGO_ENCODED_RUSTFLAGS', '').split('\x1f') if environment.get('CARGO_ENCODED_RUSTFLAGS') else shlex.split(environment.get('RUSTFLAGS', ''))
        rustflags += [f'--remap-path-prefix={ROOT}=/parzr', f'--remap-path-prefix={pathlib.Path.home()}=/build-user']
        environment['CARGO_ENCODED_RUSTFLAGS'] = '\x1f'.join(rustflags)
        run(command,env=environment)
    swift = ['swift','build','-c','release','--package-path','mac', '-Xswiftc', '-file-prefix-map', '-Xswiftc', f'{pathlib.Path.home()}=/build-user']
    # Pin the Swift Build engine: the deprecated native one (Swift 6.3 default) embeds the
    # absolute build path in package resource accessors, which the bundle audit rejects.
    swift += ['--arch','arm64','--build-system','swiftbuild']
    run(swift)
# Build into a staging bundle then replace only this builder's named artifact.
stage = dist/'Parzr-staging.app'
if stage.exists(): shutil.rmtree(stage)
for directory in ['Contents/MacOS','Contents/Frameworks','Contents/Resources']:
    (stage/directory).mkdir(parents=True,exist_ok=True)
command = ['swift','build','-c','release','--package-path','mac','--show-bin-path']
command += ['--arch','arm64','--build-system','swiftbuild']
bin_path = pathlib.Path(subprocess.check_output(command,cwd=ROOT,text=True).strip())
shutil.copy2(bin_path/'parzr', stage/'Contents/MacOS/parzr')
for bundle in bin_path.glob('*.bundle'):
    shutil.copytree(bundle, stage/'Contents/Resources'/bundle.name)
shutil.copytree(ROOT/'resources/Brand', stage/'Contents/Resources/Brand')
model_cache = dist/'model'
model_info = json.loads((model_cache/'manifest.json').read_text())
shutil.copy2(model_cache/'libparzr_model.dylib', stage/'Contents/Frameworks/libparzr_model.dylib')
model_resources = stage/'Contents/Resources/Model'; model_resources.mkdir()
for name in [model_info['file'], 'manifest.json', 'llama-LICENSE.txt']:
    shutil.copy2(model_cache/name, model_resources/name)
for name, destination in [('libparzr_engine.dylib','Contents/Frameworks'),('parzr-engine','Contents/MacOS'),('parzr-native-host','Contents/MacOS'),('parzr-lsp','Contents/MacOS')]:
    files = [ROOT/'engine/target'/target/'release'/name if target else ROOT/'engine/target/release'/name for target in architectures]
    shutil.copy2(files[0],stage/destination/name)
run(['install_name_tool','-id','@rpath/libparzr_engine.dylib',stage/'Contents/Frameworks/libparzr_engine.dylib'])
for binary in ['Contents/MacOS/parzr', 'Contents/MacOS/parzr-engine', 'Contents/MacOS/parzr-native-host', 'Contents/MacOS/parzr-lsp', 'Contents/Frameworks/libparzr_engine.dylib', 'Contents/Frameworks/libparzr_model.dylib']:
    run(['strip', '-S', stage/binary])
info = plistlib.loads((ROOT/'resources/Info.plist').read_bytes()); info['CFBundleIdentifier']=args.bundle_id
revision = hashlib.sha256()
for source in sorted([*ROOT.glob('mac/Sources/**/*.swift'), *ROOT.glob('engine/src/**/*.rs'), ROOT/'native/model.mm']):
    revision.update(str(source.relative_to(ROOT)).encode()); revision.update(source.read_bytes())
info['ParzrBuildRevision'] = revision.hexdigest()[:12]
(stage/'Contents/Info.plist').write_bytes(plistlib.dumps(info))
shutil.copy2(ROOT/'resources/PrivacyInfo.xcprivacy',stage/'Contents/Resources')
iconset = dist/'AppIcon.iconset'
run(['swift',ROOT/'scripts/make-icon.swift',iconset]); run(['iconutil','-c','icns',iconset,'-o',stage/'Contents/Resources/AppIcon.icns'])
for name in ['THIRD_PARTY_NOTICES','LICENSE']:
    shutil.copy2(ROOT/name,stage/'Contents/Resources'/name)
if (ROOT/'resources/ThirdParty').exists(): shutil.copytree(ROOT/'resources/ThirdParty',stage/'Contents/Resources/ThirdParty')
shutil.copy2(ROOT/'engine/rules/frequency.json',stage/'Contents/Resources/ThirdParty/EnglishFrequency-data.json')
integrations = stage/'Contents/Resources/Integrations'; integrations.mkdir()
shutil.copytree(ROOT/'extensions',integrations/'extensions', ignore=shutil.ignore_patterns('node_modules', '.git', '.DS_Store', '*.vsix', '.env', '.env.*', '*.p12', '*.p8', '*.key', '*.pem'))
shutil.copy2(ROOT/'scripts/connect-browser.py',integrations/'connect-browser.py')
if (ROOT/'docs/integrations.md').exists(): shutil.copy2(ROOT/'docs/integrations.md',integrations/'README.md')
identity = args.identity if args.sign else '-'
options = ['--options','runtime','--timestamp'] if args.sign else []
for binary in ['Contents/Frameworks/libparzr_model.dylib','Contents/Frameworks/libparzr_engine.dylib','Contents/MacOS/parzr-engine','Contents/MacOS/parzr-native-host','Contents/MacOS/parzr-lsp']:
    run(['codesign','--force','--sign',identity,*options,stage/binary])
run(['codesign','--force','--sign',identity,*options,'--entitlements',ROOT/'resources/Parzr.entitlements',stage])
run(['codesign','--verify','--deep','--strict',stage])
run([sys.executable, ROOT/'scripts/audit-bundle.py', stage])
if app.exists(): shutil.rmtree(app)
stage.rename(app)
report = {'app':str(app),'version':version,'architectures':'arm64','signature':'Developer ID Application' if args.sign else 'ad-hoc (local development only)','notarized':False,'bundle_id':args.bundle_id}
(dist/'build-report.json').write_text(json.dumps(report,indent=2)+'\n')
print(f'Built {app} · {report["signature"]}')
