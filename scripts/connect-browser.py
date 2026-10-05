#!/usr/bin/env python3
"""Register native messaging for an explicitly supplied browser extension identity."""
import argparse, json, pathlib, re, sys
parser = argparse.ArgumentParser()
parser.add_argument('--extension-id', required=True)
parser.add_argument('--browser', choices=['chrome','edge','brave','chromium','firefox'], default='chrome')
parser.add_argument('--app', default='/Applications/Parzr.app')
args = parser.parse_args()
if args.browser == 'firefox':
    if not re.fullmatch(r'[A-Za-z0-9@._-]{3,150}', args.extension_id): sys.exit('Invalid Firefox extension ID.')
else:
    if not re.fullmatch(r'[a-p]{32}', args.extension_id): sys.exit('Supply the 32-character extension ID from your browser extensions page.')
path = pathlib.Path(args.app).resolve() / 'Contents/MacOS/parzr-native-host'
if not path.is_file(): sys.exit('Install Parzr.app first, or supply --app /path/to/Parzr.app.')
locations = {'chrome':'Google/Chrome/NativeMessagingHosts','edge':'Microsoft Edge/NativeMessagingHosts','brave':'BraveSoftware/Brave-Browser/NativeMessagingHosts','chromium':'Chromium/NativeMessagingHosts','firefox':'Mozilla/NativeMessagingHosts'}
directory = pathlib.Path.home() / 'Library/Application Support' / locations[args.browser]
directory.mkdir(parents=True, exist_ok=True)
manifest = {'name':'dev.parzr.engine','description':'Parzr offline writing engine','path':str(path),'type':'stdio'}
manifest['allowed_extensions' if args.browser == 'firefox' else 'allowed_origins'] = [args.extension_id] if args.browser == 'firefox' else [f'chrome-extension://{args.extension_id}/']
target = directory / 'dev.parzr.engine.json'
target.write_text(json.dumps(manifest,indent=2)+'\n')
print(f'Registered local Parzr host: {target}')
