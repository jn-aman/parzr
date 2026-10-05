#!/usr/bin/env python3
"""Prepare ephemeral GitHub-runner signing credentials without printing secret commands."""
import base64, os, pathlib, secrets, subprocess, sys
if os.environ.get('GITHUB_ACTIONS')!='true':sys.exit('This helper is restricted to GitHub Actions. Use your local keychain for local signing.')
required=['PARZR_CERTIFICATE_BASE64','PARZR_CERTIFICATE_PASSWORD','PARZR_SIGNING_IDENTITY','PARZR_NOTARY_KEY_BASE64','PARZR_NOTARY_KEY_ID','PARZR_NOTARY_ISSUER']
missing=[name for name in required if not os.environ.get(name)]
if missing:sys.exit('Missing release secrets: '+', '.join(missing))
identity=os.environ['PARZR_SIGNING_IDENTITY']
if not identity.startswith('Developer ID Application:'):sys.exit('A Developer ID Application identity is required.')
temporary=pathlib.Path(os.environ['RUNNER_TEMP']);keychain=temporary/'parzr-signing.keychain-db';cert=temporary/'parzr-signing.p12';key=temporary/'parzr-notary.p8'
for name,path in [('PARZR_CERTIFICATE_BASE64',cert),('PARZR_NOTARY_KEY_BASE64',key)]:
 try:data=base64.b64decode(os.environ[name],validate=True)
 except ValueError:sys.exit('Invalid base64 in '+name)
 path.touch(mode=0o600,exist_ok=False);path.write_bytes(data)
password=secrets.token_urlsafe(32)
print('::add-mask::'+password,flush=True)
def run(command,label):
 result=subprocess.run(command,capture_output=True)
 if result.returncode:sys.exit(label+' failed. Credentials and command arguments are omitted from logs.')
run(['security','create-keychain','-p',password,str(keychain)],'Keychain creation')
run(['security','set-keychain-settings','-lut','21600',str(keychain)],'Keychain setup')
run(['security','unlock-keychain','-p',password,str(keychain)],'Keychain unlock')
run(['security','import',str(cert),'-P',os.environ['PARZR_CERTIFICATE_PASSWORD'],'-A','-t','cert','-f','pkcs12','-k',str(keychain)],'Certificate import')
run(['security','set-key-partition-list','-S','apple-tool:,apple:,codesign:','-s','-k',password,str(keychain)],'Signing-key access')
run(['security','list-keychains','-d','user','-s',str(keychain)],'Keychain search-list setup')
run(['xcrun','notarytool','store-credentials','parzr-ci','--key',str(key),'--key-id',os.environ['PARZR_NOTARY_KEY_ID'],'--issuer',os.environ['PARZR_NOTARY_ISSUER'],'--keychain',str(keychain)],'Notarization credential validation')
cert.unlink();key.unlink()
with open(os.environ['GITHUB_ENV'],'a') as env:env.write('PARZR_NOTARY_PROFILE=parzr-ci\nPARZR_NOTARY_KEYCHAIN='+str(keychain)+'\n')
print('Ephemeral Developer ID and notarization credentials are ready.')
