#!/usr/bin/env python3
"""Model packs: the model files Parzr downloads on demand instead of shipping them in the app.

engine/models.json pins every file of every pack (name, version, URL, SHA-256, size, license,
purpose); the engine compiles it in and the app reads it from there. This script works with the
same manifest:

  check     validate engine/models.json
  stage     gather a pack's files under their release asset names and verify every hash
            (--from-app OLD_PARZR.app, --from-dir DIR, or --derive to rebuild them from the pinned
            upstream sources: the Qwen3.5 Q8_0 GGUF on Hugging Face, quantized with llama.cpp, and the
            gector-v1 Core ML zip)
  publish   create the pack's GitHub release (a pre-release, never "latest") from staged assets
  fetch     download and verify a pack into a models folder laid out as the app's
            (~/Library/Application Support/Parzr/Models/<pack>/<version>/); for development and CI

Typical owner run (see docs/releases.md, "Model packs"):
  python3 scripts/model-pack.py stage --from-app /Applications/Parzr.app   # or --derive
  python3 scripts/model-pack.py publish
"""
import argparse, hashlib, json, os, pathlib, shutil, subprocess, sys, tempfile, time, urllib.error, urllib.parse, urllib.request, zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
MANIFEST = ROOT/'engine/models.json'
RELEASES = 'https://github.com/jn-aman/parzr/releases/download/'
# Upstream sources for --derive (the same pins prepare-model.py used when the weights shipped in the app).
QWEN_SOURCE = ('https://huggingface.co/ggml-org/Qwen3.5-0.8B-GGUF/resolve/8fea620810c4afa23dd6443f999a48574c1611a3/Qwen3.5-0.8B-Q8_0.gguf',
               '37ae482d336108d23516fa35e8e0c4126688d81018b87178a18d752a1357814f')
GECTOR_ZIP = ('https://github.com/jn-aman/parzr/releases/download/gector-v1/gector-roberta-base-5k-coreml-int8.zip',
              '9e3d2c433206b4eea2cb612c1a32765a24bf39ba2eef9a1c51a9ed8942427796')
# Packs --derive can rebuild byte for byte. The slips pack's Core ML model is compiled by the local toolchain, so its pinned
# hashes are those of the published assets: before its release exists, fetch --derive-fallback skips it (its tests skip too).
DERIVABLE = {'essential'}


def load():
    return json.loads(MANIFEST.read_text())


def digest(path):
    with open(path, 'rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


MARKER = '.verified.json'


def identity(path):
    """Size, inode and modification time (ns) of a regular file, as engine/src/packs.rs and the app record them."""
    info = os.stat(path, follow_symlinks=False)
    if not os.path.isfile(path) or os.path.islink(path): raise SystemExit(f'{path} is not a regular file')
    return info.st_size, info.st_ino, info.st_mtime_ns


def mark(pack, folder):
    """The verification marker the engine requires before it uses a pack (engine/src/packs.rs): written only after
    every file matched its pinned SHA-256, naming each file's identity on disk."""
    files = []
    for f in pack['files']:
        size, inode, mtime = identity(folder/f['path'])
        files.append({'path': f['path'], 'sha256': f['sha256'], 'bytes': size, 'inode': inode, 'mtime_ns': mtime})
    (folder/MARKER).write_text(json.dumps({'schema': 1, 'pack': pack['id'], 'version': pack['version'], 'files': files}, indent=2)+'\n')


def marked(pack, folder):
    """The marker still vouches for every file as it is now (no hashing)."""
    try: marker = json.loads((folder/MARKER).read_text())
    except (OSError, ValueError): return False
    if marker.get('schema') != 1 or marker.get('pack') != pack['id'] or marker.get('version') != pack['version']: return False
    entries = {m.get('path'): m for m in marker.get('files', [])}
    for f in pack['files']:
        m = entries.get(f['path'])
        try: now = identity(folder/f['path'])
        except (OSError, SystemExit): return False
        if not m or m.get('sha256') != f['sha256'] or m.get('bytes') != f['bytes'] or now != (m.get('bytes'), m.get('inode'), m.get('mtime_ns')): return False
    return True


def asset_name(file):
    return urllib.parse.unquote(file['url'].rsplit('/', 1)[1])


def tag_of(pack):
    tags = {f['url'][len(RELEASES):].split('/', 1)[0] for f in pack['files']}
    if len(tags) != 1: raise SystemExit(f"Pack {pack['id']} must be hosted on one release tag, found {sorted(tags)}")
    return tags.pop()


def pick(manifest, name):
    packs = [p for p in manifest['packs'] if name in (None, p['id'])]
    if not packs: raise SystemExit(f'No pack named {name}')
    return packs


def check(manifest):
    problems = []
    if manifest.get('schema') != 1: problems.append('schema must be 1')
    ids = set()
    for pack in manifest['packs']:
        if pack['id'] in ids: problems.append('duplicate pack '+pack['id'])
        ids.add(pack['id'])
        names, paths = set(), set()
        for f in pack['files']:
            if not f['url'].startswith(RELEASES): problems.append(f"{f['path']}: URL must be a jn-aman/parzr release asset")
            for key in ['path', 'url', 'sha256', 'bytes', 'name', 'version', 'license', 'purpose']:
                if not f.get(key): problems.append(f"{f.get('path')}: missing {key}")
            parts = f['path'].split('/')
            if f['path'].startswith('/') or any(not p or p.startswith('.') for p in parts): problems.append(f"{f['path']}: unsafe path")
            if len(f['sha256']) != 64: problems.append(f"{f['path']}: bad sha256")
            if asset_name(f) in names: problems.append(f"{f['path']}: asset name {asset_name(f)} is used twice")
            if f['path'] in paths: problems.append(f"{f['path']}: listed twice")
            names.add(asset_name(f)); paths.add(f['path'])
        tag_of(pack)
        for role, relative in pack['provides'].items():
            if not any(f['path'] == relative or f['path'].startswith(relative+'/') for f in pack['files']): problems.append(f'{role}: {relative} is not in the pack')
    if problems: raise SystemExit('engine/models.json:\n  '+'\n  '.join(problems))


def download(url, destination, expected_sha=None, expected_bytes=None, attempts=4):
    """Resumable, verified download: bytes go to <destination>.partial (a later run resumes it with a
    Range request), the hash is checked, then the file is renamed into place."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(destination.name+'.partial')
    for attempt in range(1, attempts+1):
        offset = partial.stat().st_size if partial.exists() else 0
        if expected_bytes and offset > expected_bytes: partial.unlink(); offset = 0
        try:
            request = urllib.request.Request(url, headers={'User-Agent': 'parzr-model-pack'})
            if offset and url.startswith('http'): request.add_header('Range', f'bytes={offset}-')
            with urllib.request.urlopen(request, timeout=90) as source:
                resumed = offset and getattr(source, 'status', 200) == 206
                with partial.open('ab' if resumed else 'wb') as output:
                    shutil.copyfileobj(source, output, 1024*1024)
            if expected_bytes and partial.stat().st_size != expected_bytes:
                raise OSError(f'got {partial.stat().st_size} bytes, expected {expected_bytes}')
            if expected_sha and digest(partial) != expected_sha:
                partial.unlink()
                raise ValueError('SHA-256 mismatch')
            partial.replace(destination)
            return
        except urllib.error.HTTPError as error:
            if error.code in (404, 410): raise
            if error.code == 416: partial.unlink(missing_ok=True)
            problem = error
        except (OSError, ValueError) as error:
            problem = error
        print(f'  {destination.name}: attempt {attempt} failed ({problem}); retrying', file=sys.stderr)
        time.sleep(min(30, 2**attempt))
    raise SystemExit(f'Could not download {url}: {problem}')


def derive(work):
    """Rebuilds the essential pack's files from the pinned upstream sources into `work`, laid out by pack path."""
    work.mkdir(parents=True, exist_ok=True)
    source = work/'Qwen3.5-0.8B-Q8_0.gguf'
    if not source.exists() or digest(source) != QWEN_SOURCE[1]: download(QWEN_SOURCE[0], source, QWEN_SOURCE[1])
    cmake = shutil.which('cmake') or str(ROOT/'dist/qa/frequency-build/bin/cmake')
    build = ROOT/'dist/llama-build-arm64'
    if not (build/'CMakeCache.txt').exists(): subprocess.run([sys.executable, ROOT/'scripts/prepare-model.py'], check=True)
    subprocess.run([cmake, '--build', build, '--target', 'llama-quantize', '-j', '2'], check=True)
    target = work/'Qwen3.5-0.8B-Q5_K_M.gguf'
    if not target.exists(): subprocess.run([build/'bin/llama-quantize', '--allow-requantize', source, target, 'Q5_K_M'], check=True)
    archive = work/'gector.zip'
    if not archive.exists() or digest(archive) != GECTOR_ZIP[1]: download(GECTOR_ZIP[0], archive, GECTOR_ZIP[1])
    shutil.rmtree(work/'gector', ignore_errors=True)
    with zipfile.ZipFile(archive) as z: z.extractall(work/'gector')
    return work


def stage(manifest, args):
    out = pathlib.Path(args.out).resolve(); out.mkdir(parents=True, exist_ok=True)
    packs = pick(manifest, args.pack)
    if not args.from_app and not args.from_dir and any(p['id'] not in DERIVABLE for p in packs):
        raise SystemExit(f"--derive rebuilds only {', '.join(sorted(DERIVABLE))}; stage the others --from-dir "
                         "(the slips pack: scripts/convert-slips.py writes dist/slips-build, then --from-dir dist/slips-build --pack slips)")
    if args.from_app: base = pathlib.Path(args.from_app)/'Contents/Resources/Model'
    elif args.from_dir: base = pathlib.Path(args.from_dir)
    else: base = derive(pathlib.Path(args.work).resolve())
    for pack in packs:
        for f in pack['files']:
            source, target = base/f['path'], out/asset_name(f)
            if not source.is_file(): raise SystemExit(f'Missing {source}')
            if digest(source) != f['sha256'] or source.stat().st_size != f['bytes']:
                raise SystemExit(f"{source} does not match the pinned SHA-256 and size of {f['path']}")
            target.unlink(missing_ok=True); shutil.copy2(source, target)
        print(f"Staged pack {pack['id']} {pack['version']}: {len(pack['files'])} files, {sum(f['bytes'] for f in pack['files'])/1e6:.0f} MB in {out}")


def notes(pack):
    rows = '\n'.join(f"| `{asset_name(f)}` | `{f['path']}` | {f['bytes']:,} | {f['license']} | `{f['sha256']}` |" for f in pack['files'])
    return (f"Model pack **{pack['id']}**, version {pack['version']}: {pack['title']}.\n\n{pack['purpose']}\n\n"
            "Parzr downloads these files on demand (pinned in `engine/models.json`, each checked against its SHA-256 before use). "
            "This is not an app release: download Parzr from the latest release.\n\n"
            f"License: {pack['license']}\n\n| Asset | Path in the pack | Bytes | License | SHA-256 |\n|---|---|---|---|---|\n{rows}\n")


def publish(manifest, args):
    staged = pathlib.Path(args.assets).resolve()
    for pack in pick(manifest, args.pack):
        tag = tag_of(pack)
        files = []
        for f in pack['files']:
            path = staged/asset_name(f)
            if not path.is_file() or digest(path) != f['sha256']: raise SystemExit(f'{path} is missing or does not match the manifest; run stage first')
            files.append(str(path))
        if subprocess.run(['gh', 'release', 'view', tag], capture_output=True).returncode == 0:
            raise SystemExit(f'Release {tag} already exists. Packs are immutable: publish a new version under a new tag (see docs/releases.md).')
        command = ['gh', 'release', 'create', tag, '--title', f"Parzr models: {pack['id']} {pack['version']}", '--notes', notes(pack), '--prerelease', '--latest=false', *files]
        if args.target: command[4:4] = ['--target', args.target]
        if args.dry_run: print(' '.join(command[:9]), f'... ({len(files)} files)'); continue
        subprocess.run(command, check=True)
        print(f'Published {tag}. Check it: python3 scripts/model-pack.py fetch --models-dir "$(mktemp -d)"')


def fetch(manifest, args):
    root = pathlib.Path(args.models_dir).resolve()
    for pack in pick(manifest, args.pack):
        final = root/pack['id']/pack['version']
        if final.is_dir() and all((final/f['path']).is_file() and (final/f['path']).stat().st_size == f['bytes'] for f in pack['files']):
            # The engine uses a pack only with a current marker; without one (an older checkout or cache) the files are hashed first.
            if (marked(pack, final) and not args.verify) or all(digest(final/f['path']) == f['sha256'] for f in pack['files']):
                if not marked(pack, final): mark(pack, final)
                print(f'{final} is installed'); continue
        staging = root/pack['id']/f".download-{pack['version']}"
        base = args.base_url
        try:
            for f in pack['files']:
                target = staging/f['path']
                if target.is_file() and digest(target) == f['sha256']: continue
                url = base.rstrip('/')+'/'+asset_name(f) if base else f['url']
                print(f"  {f['path']} ({f['bytes']/1e6:.1f} MB)")
                download(url, target, f['sha256'], f['bytes'])
        except urllib.error.HTTPError as error:
            if not args.derive_fallback: raise SystemExit(f'{error.url}: HTTP {error.code}. Is the {tag_of(pack)} release published?')
            if pack['id'] not in DERIVABLE:
                print(f"{tag_of(pack)} is not published yet (HTTP {error.code}) and pack {pack['id']} cannot be rebuilt here: skipped "
                      "(Parzr works without it; its tests skip)", file=sys.stderr)
                continue
            print(f'{tag_of(pack)} is not published yet (HTTP {error.code}); rebuilding the pack from its pinned upstream sources', file=sys.stderr)
            assets = pathlib.Path(tempfile.mkdtemp(prefix='parzr-pack-'))
            stage(manifest, argparse.Namespace(out=assets, from_app=None, from_dir=None, work=args.work, pack=pack['id']))
            fetch(manifest, argparse.Namespace(**{**vars(args), 'base_url': assets.as_uri(), 'pack': pack['id'], 'derive_fallback': False}))
            shutil.rmtree(assets, ignore_errors=True)
            continue
        (staging/'pack.json').write_text(json.dumps(pack, indent=2)+'\n')
        if final.exists(): shutil.rmtree(final)
        staging.rename(final)
        mark(pack, final)
        for old in (root/pack['id']).iterdir():
            if old != final and old.is_dir(): shutil.rmtree(old)
        print(f'Installed {final}')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('check')
    s = sub.add_parser('stage'); s.add_argument('--out', default=str(ROOT/'dist/model-pack'))
    source = s.add_mutually_exclusive_group(required=True)
    source.add_argument('--from-app', help='a Parzr.app that still bundles the models (0.4.12 or older)')
    source.add_argument('--from-dir', help='a folder laid out like the pack (for example dist/models/essential/1)')
    source.add_argument('--derive', action='store_true', help='rebuild from the pinned upstream sources')
    p = sub.add_parser('publish'); p.add_argument('--assets', default=str(ROOT/'dist/model-pack')); p.add_argument('--dry-run', action='store_true')
    p.add_argument('--target', help='commit or branch for a new tag (default: the default branch)')
    f = sub.add_parser('fetch'); f.add_argument('--models-dir', default=os.environ.get('PARZR_MODELS_DIR') or str(ROOT/'dist/models'))
    f.add_argument('--base-url', help='download from here instead of the release (for example file:///…/dist/model-pack)')
    f.add_argument('--derive-fallback', action='store_true', help='rebuild the pack from upstream when its release is not published yet')
    f.add_argument('--verify', action='store_true', help='re-hash an installed pack instead of trusting its sizes')
    for command in (s, p, f): command.add_argument('--pack')
    for command in (s, f): command.add_argument('--work', default=str(ROOT/'dist/model-derive'))
    args = parser.parse_args()
    manifest = load(); check(manifest)
    if args.command == 'check': print('engine/models.json is valid.')
    elif args.command == 'stage': stage(manifest, args)
    elif args.command == 'publish': publish(manifest, args)
    else: fetch(manifest, args)


if __name__ == '__main__':
    main()
