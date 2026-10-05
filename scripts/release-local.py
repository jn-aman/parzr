#!/usr/bin/env python3
"""Build an Apple Silicon signed/notarized DMG using credentials in the local keychain."""
import argparse
import os
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--setup-notary', action='store_true', help='Secure interactive setup; enter credentials in your terminal, never source files')
parser.add_argument('--check', action='store_true', help='Check signing and notarization readiness without building')
parser.add_argument('--notary-profile', default=os.environ.get('PARZR_NOTARY_PROFILE', 'parzr-local'))
args = parser.parse_args()

def run(command, **kwargs):
    return subprocess.run(command, cwd=ROOT, check=True, **kwargs)

if args.setup_notary:
    run(['xcrun', 'notarytool', 'store-credentials', args.notary_profile])
    sys.exit(0)

result = subprocess.run(['security', 'find-identity', '-v', '-p', 'codesigning'], capture_output=True, text=True)
identities = re.findall(r'"(Developer ID Application:[^"\n]+)"', result.stdout)
identity = os.environ.get('PARZR_SIGNING_IDENTITY')
if identity and identity not in identities:
    sys.exit('The configured Developer ID Application identity is not valid in this keychain.')
if not identity:
    if not identities:
        sys.exit('Create a Developer ID Application certificate in Xcode Settings → Accounts → your team → Manage Certificates → +. Then rerun this command.')
    if len(identities) != 1:
        sys.exit('Multiple Developer ID Application identities are installed. Select one using PARZR_SIGNING_IDENTITY.')
    identity = identities[0]

try:
    check = subprocess.run(['xcrun', 'notarytool', 'history', '--keychain-profile', args.notary_profile, '--output-format', 'json'], capture_output=True, timeout=45)
except subprocess.TimeoutExpired:
    sys.exit('Notarization credential verification timed out. Check your connection and retry.')
if check.returncode:
    sys.exit('Notarization credentials are unavailable or invalid. Run: python3 scripts/release-local.py --setup-notary')
print('Developer ID signing and notarization credentials are ready. Account details stay in the local keychain.')
if args.check:
    sys.exit(0)
run([sys.executable, 'scripts/audit-public-repo.py'])
run([sys.executable, 'scripts/check-release-version.py'])
environment = os.environ.copy()
environment['PARZR_SIGNING_IDENTITY'] = identity
environment['PARZR_NOTARY_PROFILE'] = args.notary_profile
run([sys.executable, 'scripts/build.py', '--sign'], env=environment)
run([sys.executable, 'scripts/package.py', '--release'], env=environment)
print('Signed and notarized Apple Silicon DMG ready in dist/.')
