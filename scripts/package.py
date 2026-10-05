#!/usr/bin/env python3
"""Create a local DMG or a verified, signed and notarized distribution DMG."""
import argparse, json, os, pathlib, plistlib, shutil, subprocess, sys
ROOT=pathlib.Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser()
parser.add_argument('--release',action='store_true')
parser.add_argument('--identity',default=os.environ.get('PARZR_SIGNING_IDENTITY'))
parser.add_argument('--notary-profile',default=os.environ.get('PARZR_NOTARY_PROFILE'))
parser.add_argument('--notary-keychain',default=os.environ.get('PARZR_NOTARY_KEYCHAIN'))
args=parser.parse_args()
dist=ROOT/'dist'; app=dist/'Parzr.app'
def run(command,**kwargs): return subprocess.run([str(x) for x in command],check=True,cwd=ROOT,**kwargs)
if not app.exists(): sys.exit('Run scripts/build.py first.')
version=plistlib.loads((app/'Contents/Info.plist').read_bytes())['CFBundleShortVersionString']
signing=subprocess.run(['codesign','-dv','--verbose=4',str(app)],capture_output=True,text=True,check=True).stderr
app_developer_id_signed='Authority=Developer ID Application:' in signing
run(['codesign','--verify','--deep','--strict',app])
if args.release:
    if not args.identity or not args.notary_profile: sys.exit('Release packaging requires a Developer ID identity and a notarytool keychain profile.')
    if 'Authority=Developer ID Application:' not in signing or 'flags=0x10000(runtime)' not in signing: sys.exit('The app must already be Developer ID signed with hardened runtime. Rebuild with --sign.')
    notary_auth=['--keychain-profile',args.notary_profile]
    if args.notary_keychain: notary_auth += ['--keychain',args.notary_keychain]
    archive=dist/'parzr-notarization.zip'
    run(['ditto','-c','-k','--keepParent',app,archive])
    result=run(['xcrun','notarytool','submit',archive,*notary_auth,'--wait','--timeout','30m','--output-format','json'],capture_output=True,text=True)
    submission=json.loads(result.stdout); (dist/'app-notarization.json').write_text(json.dumps(submission,indent=2)+'\n')
    if submission.get('status')!='Accepted': sys.exit('App notarization was not accepted. Review dist/app-notarization.json.')
    run(['xcrun','stapler','staple',app]); run(['xcrun','stapler','validate',app]); run(['spctl','--assess','--type','execute','--verbose=2',app])
staging=dist/'dmg-root'
if staging.exists(): shutil.rmtree(staging)
staging.mkdir(); shutil.copytree(app,staging/'Parzr.app',symlinks=True)
(staging/'Applications').symlink_to('/Applications',target_is_directory=True)
(staging/'Read me.txt').write_text('Parzr\n\nDrag Parzr.app to Applications. Open it, allow Accessibility, then select text and press Option+Space.\n\n'+('Developer ID signed and notarized release.\n' if args.release else ('Local build. Developer ID signed; not notarized.\n' if app_developer_id_signed else 'Local development build. Ad-hoc signed; not notarized or approved for distribution.\n')))
name=f'Parzr-{version}.dmg' if args.release else f'Parzr-{version}-local.dmg'
dmg=dist/name
# The mounted drive shows Parzr's icon: build writable, add .VolumeIcon.icns, flag the custom
# icon in the volume root's FinderInfo (kHasCustomIcon), then compress. No Finder scripting.
writable=dist/'Parzr-writable.dmg'; mount=dist/'dmg-mount'
for stale in (writable,dmg):
    if stale.exists(): stale.unlink()
run(['hdiutil','create','-volname','Parzr','-srcfolder',staging,'-ov','-format','UDRW',writable])
mount.mkdir(exist_ok=True)
run(['hdiutil','attach',writable,'-nobrowse','-noverify','-noautoopen','-mountpoint',mount])
try:
    shutil.copy2(app/'Contents/Resources/AppIcon.icns',mount/'.VolumeIcon.icns')
    run(['xattr','-wx','com.apple.FinderInfo','0000000000000000040000000000000000000000000000000000000000000000',mount])
finally:
    run(['hdiutil','detach',mount])
run(['hdiutil','convert',writable,'-format','UDZO','-o',dmg]); writable.unlink(); mount.rmdir()
if args.identity:
    run(['codesign','--force','--sign',args.identity,'--timestamp',dmg])
    run(['codesign','--verify','--strict',dmg])
if args.release:
    result=run(['xcrun','notarytool','submit',dmg,*notary_auth,'--wait','--timeout','30m','--output-format','json'],capture_output=True,text=True)
    submission=json.loads(result.stdout); (dist/'dmg-notarization.json').write_text(json.dumps(submission,indent=2)+'\n')
    if submission.get('status')!='Accepted': sys.exit('DMG notarization was not accepted. Review dist/dmg-notarization.json.')
    run(['xcrun','stapler','staple',dmg]); run(['xcrun','stapler','validate',dmg]); run(['spctl','--assess','--type','open','--context','context:primary-signature','--verbose=2',dmg])
run(['hdiutil','verify',dmg])
dmg_signing=subprocess.run(['codesign','-dv','--verbose=4',str(dmg)],capture_output=True,text=True)
(dist/'package-report.json').write_text(json.dumps({'dmg':str(dmg),'developer_id_signed':'Authority=Developer ID Application:' in dmg_signing.stderr,'app_developer_id_signed':app_developer_id_signed,'notarized':args.release},indent=2)+'\n')
print(f'Created {dmg}')
