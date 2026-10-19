#!/usr/bin/env python3
"""Check the publishable tree without exposing detected private values.

  audit-public-repo.py            the current tree: tracked files plus untracked, non-ignored ones (CI runs this)
  audit-public-repo.py --history  also every commit reachable from any ref: file names ever added and every added
                                  line of every patch (`git log -p --all`). Slower; run it before making a repository
                                  public, after rotating a leaked credential, or when a check below gains a pattern.
"""
import fnmatch
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
LOCAL_DIRS = {'.git', '.agents', '.claude', '.codex', '.impeccable', '.vscode', '.build', 'target', 'dist', 'node_modules', '__pycache__', 'test-results', 'playwright-report'}
LOCAL_NAMES = {'.DS_Store', 'skills-lock.json'}
PRIVATE_GLOBS = ['.env', '.env.*', '.dev.vars', '.dev.vars.*', '*.p12', '*.p8', '*.pem', '*.key', '*.cer', '*.keychain-db', '*.mobileprovision', '*.provisionprofile', '*.xcuserstate', '*.pyc', '*.vsix', '*.dmg']

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
    ('Cloudflare API token', re.compile(r'\bcfat_[A-Za-z0-9_-]{20,}')),
    ('AWS access key', re.compile(r'\b(?:AKIA|ASIA)[0-9A-Z]{16}\b')),
    ('Slack token', re.compile(r'\bxox[bpas]-[0-9A-Za-z-]{10,}')),
    ('Hugging Face token', re.compile(r'\bhf_[A-Za-z0-9]{30,}\b')),
    ('npm token', re.compile(r'\bnpm_[A-Za-z0-9]{36}\b')),
]


def skip(path, label):
    # License author credits are legally required public attribution.
    path = pathlib.PurePath(path)
    return label == 'private account address' and (path.parts[:2] == ('resources', 'ThirdParty') or path.name in {'LICENSE', 'THIRD_PARTY_NOTICES'})


def history_issues():
    """(commit, path, line, label) for every private file name ever added and every match in an added patch line."""
    found = []
    names = subprocess.run(['git', 'log', '--all', '--diff-filter=A', '--name-only', '--format=@%H'], cwd=ROOT, capture_output=True, text=True, check=True)
    commit = ''
    for line in names.stdout.splitlines():
        if line.startswith('@'):
            commit = line[1:13]
        elif line and private(pathlib.Path(line)):
            found.append((commit, line, 0, 'private/generated file in history'))
    log = subprocess.Popen(['git', 'log', '--all', '-p', '-U0', '--no-color', '--no-ext-diff', '--format=@%H'], cwd=ROOT, stdout=subprocess.PIPE)
    commit = path = ''
    number = 0
    for raw in log.stdout:
        line = raw.decode('utf-8', errors='replace').rstrip('\n')
        if re.fullmatch(r'@[0-9a-f]{40}', line):
            commit = line[1:13]
        elif line.startswith('+++ '):
            path = line[6:] if line.startswith('+++ b/') else ''
        elif line.startswith('@@'):
            m = re.search(r'\+(\d+)', line)
            number = int(m.group(1)) if m else 0
        elif line.startswith('+') and path:
            for label, pattern in checks:
                if not skip(path, label) and pattern.search(line):
                    found.append((commit, path, number, label))
            number += 1
    log.wait()
    return found


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
        if skip(path, label):
            continue
        for match in pattern.finditer(value):
            issues.append((path, value.count('\n', 0, match.start())+1, label))
history = history_issues() if '--history' in sys.argv[1:] else []
if issues or history:
    for path,line,label in issues:
        print(f'{path}:{line}: {label}; value omitted', file=sys.stderr)
    for commit,path,line,label in history:
        print(f'{commit} {path}:{line}: {label} (history); value omitted', file=sys.stderr)
    sys.exit(1)
print(f'Public-content audit passed ({len(paths)} files; local tools and generated artifacts excluded)'
      + ('; history clean.' if '--history' in sys.argv[1:] else '.'))
