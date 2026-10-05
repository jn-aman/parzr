#!/usr/bin/env python3
"""Check the publishable tree without exposing detected private values."""
import fnmatch
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
LOCAL_DIRS = {'.git', '.agents', '.codex', '.impeccable', '.vscode', '.build', 'target', 'dist', 'node_modules', '__pycache__', 'test-results', 'playwright-report'}
LOCAL_NAMES = {'.DS_Store', 'skills-lock.json'}
PRIVATE_GLOBS = ['.env', '.env.*', '*.p12', '*.p8', '*.pem', '*.key', '*.cer', '*.keychain-db', '*.mobileprovision', '*.provisionprofile', '*.xcuserstate', '*.pyc', '*.vsix', '*.dmg']

def private(path):
    return any(p in LOCAL_DIRS for p in path.parts) or path.name in LOCAL_NAMES or any(fnmatch.fnmatch(path.name, g) for g in PRIVATE_GLOBS) and not path.name.endswith('.example')

tracked = subprocess.run(['git', 'ls-files', '-z'], cwd=ROOT, capture_output=True)
paths = set(pathlib.Path(p) for p in tracked.stdout.decode().split('\0') if p) if tracked.returncode == 0 else set()
for parent, dirs, names in __import__('os').walk(ROOT):
    dirs[:] = [d for d in dirs if d not in LOCAL_DIRS]
    for name in names:
        path = (pathlib.Path(parent) / name).relative_to(ROOT)
        if not private(path):
            paths.add(path)
checks = [
    ('local home path', re.compile(r'(?:/Users/|/home/)[A-Za-z0-9_.-]+/')),
    ('private discussion link', re.compile(r'https?://(?:chatgpt|chat\.openai)\.com/(?:share|c)/', re.I)),
    ('private account address', re.compile(r'[A-Z0-9._%+-]+@(?:gmail|icloud|outlook|hotmail|protonmail)\.com', re.I)),
    ('private key', re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH |ENCRYPTED )?PRIVATE KEY-----')),
    ('credential token', re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|sk-(?:proj-)?[A-Za-z0-9_-]{40,})\b')),
]
issues=[]
for path in sorted(paths):
    if private(path):
        issues.append((path, 0, 'tracked private/generated file'))
        continue
    full=ROOT/path
    if not full.exists():
        continue
    if full.is_symlink():
        issues.append((path, 0, 'public symlink requires review'))
        continue
    data=full.read_bytes()
    if b'\0' in data:
        continue
    value=data.decode('utf-8', errors='replace')
    for label, pattern in checks:
        # License author credits are legally required public attribution.
        if label == 'private account address' and (path.parts[:2] == ('resources', 'ThirdParty') or path.name in {'LICENSE', 'THIRD_PARTY_NOTICES'}):
            continue
        for match in pattern.finditer(value):
            issues.append((path, value.count('\n', 0, match.start())+1, label))
if issues:
    for path,line,label in issues:
        print(f'{path}:{line}: {label}; value omitted', file=sys.stderr)
    sys.exit(1)
print(f'Public-content audit passed ({len(paths)} files; local tools and generated artifacts excluded).')
