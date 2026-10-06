#!/usr/bin/env python3
"""Build and verify the Sparkle update assets for one Parzr release.

  make-appcast.py build  --app dist/Parzr.app --version X.Y.Z --out dist/update
                         [--prev-dir DIR] [--notes TEXT] [--git-range A..B] [--critical]
  make-appcast.py verify --appcast FILE_OR_URL [--version X.Y.Z] [--dir LOCAL_FILES]

build: zips the notarized, stapled app (ditto), makes deltas from up to 3 previous update
zips, signs everything (EdDSA key from $SPARKLE_ED_PRIVATE_KEY via stdin, or --key-file),
writes ONE-item appcast.xml, then verifies its own output and exits non-zero on any mismatch.
verify: re-checks a published appcast (URL or file): XML shape, URLs, lengths, and every
signature against the pinned PUBLIC key, using a stdlib Ed25519 verifier (no Sparkle tools).
"""
import argparse, base64, datetime, email.utils, hashlib, os, pathlib, plistlib, re, shutil, subprocess, sys, tempfile, time
import urllib.request, xml.etree.ElementTree as ET
from xml.sax.saxutils import quoteattr

REPO = 'jn-aman/parzr'
PUBLIC_KEY = 'j0Fo7VqKBmJXHWEzVHZX0KeGWCPpTng6tW8jmcoEVo0='  # SUPublicEDKey in Info.plist
SPARKLE_VERSION = '2.9.5'
SPARKLE_SHA256 = '015336b601493e05c237964954bff6191370003d94edefe663724c88840d73cc'
SPARKLE_URL = f'https://github.com/sparkle-project/Sparkle/releases/download/{SPARKLE_VERSION}/Sparkle-{SPARKLE_VERSION}.tar.xz'
MIN_OS = '13.0'
MAX_DELTAS = 3
NS = {'sparkle': 'http://www.andymatuschak.org/xml-namespaces/sparkle'}
SP = '{%s}' % NS['sparkle']


def die(msg):
    sys.exit(f'make-appcast: FAIL: {msg}')


def check(cond, msg):
    if not cond:
        die(msg)


# ---- Ed25519 verify (RFC 8032, stdlib only; a handful of point operations per file) ----
_P = 2**255 - 19
_Q = 2**252 + 27742317777372353535851937790883648493
_D = -121665 * pow(121666, _P - 2, _P) % _P
_I = pow(2, (_P - 1) // 4, _P)


def _x(y, sign):
    x = pow((y * y - 1) * pow(_D * y * y + 1, _P - 2, _P) % _P, (_P + 3) // 8, _P)
    if (x * x - (y * y - 1) * pow(_D * y * y + 1, _P - 2, _P)) % _P:
        x = x * _I % _P
    return _P - x if x & 1 != sign else x


_B = (_x(4 * pow(5, _P - 2, _P) % _P, 0), 4 * pow(5, _P - 2, _P) % _P)


def _add(a, b):
    (x1, y1), (x2, y2) = a, b
    t = _D * x1 * x2 * y1 * y2 % _P
    return ((x1 * y2 + x2 * y1) * pow(1 + t, _P - 2, _P) % _P, (y1 * y2 + x1 * x2) * pow(1 - t, _P - 2, _P) % _P)


def _mul(p, e):
    r = (0, 1)
    while e:
        if e & 1:
            r = _add(r, p)
        p = _add(p, p)
        e >>= 1
    return r


def _dec(s):
    y = int.from_bytes(s, 'little')
    sign, y = y >> 255, y & (2**255 - 1)
    pt = (_x(y, sign), y)
    if (-pt[0] * pt[0] + pt[1] * pt[1] - 1 - _D * pt[0] * pt[0] * pt[1] * pt[1]) % _P:
        raise ValueError('not on curve')
    return pt


def ed25519_verify(public, sig, msg_path):
    if len(public) != 32 or len(sig) != 64:
        return False
    try:
        a, r = _dec(public), _dec(sig[:32])
    except ValueError:
        return False
    s = int.from_bytes(sig[32:], 'little')
    if s >= _Q:
        return False
    h = hashlib.sha512(sig[:32] + public)
    with open(msg_path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    k = int.from_bytes(h.digest(), 'little') % _Q
    return _mul(_B, s) == _add(r, _mul(a, k))


def self_test():
    # RFC 8032 section 7.1, test 1 (empty message) plus a corrupted signature.
    pub = bytes.fromhex('d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a')
    sig = bytes.fromhex('e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b')
    with tempfile.NamedTemporaryFile() as f:
        assert ed25519_verify(pub, sig, f.name)
        assert not ed25519_verify(pub, sig[:-1] + b'\x0c', f.name)
        f.write(b'x'); f.flush()
        assert not ed25519_verify(pub, sig, f.name)


# ---- tools ----
def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode:
        die(f'{" ".join(map(str, cmd[:3]))} failed: {(r.stderr or r.stdout).strip()[-600:]}')
    return r.stdout


def sparkle_bin(given):
    """Directory with BinaryDelta and sign_update: --sparkle-bin, else the pinned download."""
    if given:
        return pathlib.Path(given)
    cache = pathlib.Path(os.environ.get('RUNNER_TEMP') or tempfile.gettempdir()) / f'parzr-sparkle-{SPARKLE_VERSION}'
    if (cache / 'bin/sign_update').exists():
        return cache / 'bin'
    cache.mkdir(parents=True, exist_ok=True)
    tarball = cache / 'sparkle.tar.xz'
    urllib.request.urlretrieve(SPARKLE_URL, tarball)
    got = hashlib.sha256(tarball.read_bytes()).hexdigest()
    check(got == SPARKLE_SHA256, f'Sparkle tarball sha256 {got} != pinned {SPARKLE_SHA256}')
    run(['tar', '-xJf', str(tarball), '-C', str(cache), './bin/BinaryDelta', './bin/sign_update'])
    return cache / 'bin'


def sign(tools, path, key_file):
    """EdDSA signature (base64) of a file. The key is never printed: file path or stdin."""
    if key_file:
        out = run([str(tools / 'sign_update'), '-p', '--ed-key-file', key_file, str(path)])
    else:
        key = os.environ.get('SPARKLE_ED_PRIVATE_KEY')
        check(key, 'no signing key: set SPARKLE_ED_PRIVATE_KEY or pass --key-file')
        out = run([str(tools / 'sign_update'), '-p', '--ed-key-file', '-', str(path)], input=key)
    sig = out.strip()
    check(len(base64.b64decode(sig)) == 64, 'sign_update did not return a 64 byte signature')
    return sig


# ---- app helpers ----
def info(app):
    return plistlib.loads((pathlib.Path(app) / 'Contents/Info.plist').read_bytes())


def unzip(zip_path, dest):
    run(['ditto', '-x', '-k', str(zip_path), str(dest)])
    apps = list(pathlib.Path(dest).glob('*.app'))
    check(len(apps) == 1, f'{zip_path} must contain exactly one .app at top level')
    return apps[0]


def _sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.digest()


def tree_hash(app):
    """Content hash of a bundle: paths, file bytes, symlink targets and exec bits (not mtimes)."""
    h = hashlib.sha256()
    root = pathlib.Path(app)
    for p in sorted(root.rglob('*')):
        rel = str(p.relative_to(root)).encode()
        if p.is_symlink():
            h.update(b'L' + rel + b'\0' + os.readlink(p).encode() + b'\0')
        elif p.is_file():
            h.update(b'F' + rel + b'\0' + (b'x' if os.access(p, os.X_OK) else b'-') + _sha(p))
        else:
            h.update(b'D' + rel + b'\0')
    return h.hexdigest()


def bullets(notes, git_range):
    items = [re.sub(r'^[-*•]\s*', '', s.strip()) for s in re.split(r'\n| \| ', notes or '')]
    items = [s for s in items if s]
    if not items and git_range:
        r = subprocess.run(['git', 'log', '--no-merges', '--format=%s', git_range], capture_output=True, text=True)
        items = [s for s in r.stdout.splitlines() if s and not s.startswith('Release v')]
    items = [s if len(s) <= 160 else s[:157].rstrip() + '...' for s in items[:6]]
    return items or ['Bug fixes and improvements.']


# ---- appcast ----
def enclosure(url, length, sig, **attrs):
    extra = ''.join(f' {k}={quoteattr(str(v))}' for k, v in attrs.items())
    return f'<enclosure url={quoteattr(url)}{extra} length="{length}" type="application/octet-stream" sparkle:edSignature="{sig}"/>'


def write_appcast(path, version, build, items, notes, critical, interval, now):
    tag = f'v{version}'
    base = f'https://github.com/{REPO}/releases/download/{tag}'
    md = '\n'.join(f'- {n}' for n in notes).replace(']]>', ']]]]><![CDATA[>')
    rollout = '<sparkle:criticalUpdate></sparkle:criticalUpdate>' if critical else f'<sparkle:phasedRolloutInterval>{interval}</sparkle:phasedRolloutInterval>'
    zip_name, zip_len, zip_sig, deltas = items
    d = ''.join(
        '\n        ' + enclosure(f'{base}/{n}', ln, sg, **{'sparkle:version': build, 'sparkle:shortVersionString': version, 'sparkle:deltaFrom': ob})
        for n, ln, sg, ob in deltas)
    d = f'\n      <sparkle:deltas>{d}\n      </sparkle:deltas>' if deltas else ''
    pathlib.Path(path).write_text(f'''<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0" xmlns:sparkle="{NS['sparkle']}">
  <channel>
    <title>Parzr</title>
    <link>https://parzr.app</link>
    <description>Parzr updates</description>
    <language>en</language>
    <item>
      <title>Parzr {version}</title>
      <link>https://github.com/{REPO}/releases/tag/{tag}</link>
      <pubDate>{email.utils.format_datetime(now)}</pubDate>
      <sparkle:version>{build}</sparkle:version>
      <sparkle:shortVersionString>{version}</sparkle:shortVersionString>
      <sparkle:minimumSystemVersion>{MIN_OS}</sparkle:minimumSystemVersion>
      <sparkle:hardwareRequirements>arm64</sparkle:hardwareRequirements>
      {rollout}
      <description sparkle:format="markdown"><![CDATA[{md}]]></description>
      {enclosure(f'{base}/{zip_name}', zip_len, zip_sig, **{'sparkle:version': build, 'sparkle:shortVersionString': version})}{d}
    </item>
  </channel>
</rss>
''')


def verify_appcast(appcast, fetch, public_key, version=None, critical=None, build=None):
    """Return (item facts). fetch(url) -> local path of the enclosure. Dies on any mismatch."""
    root = ET.parse(appcast).getroot()
    items = root.findall('./channel/item')
    check(len(items) == 1, f'appcast must hold exactly one item, found {len(items)}')
    it = items[0]
    text = lambda tag: (it.findtext(f'sparkle:{tag}', namespaces=NS) or '').strip()
    short, bld = text('shortVersionString'), text('version')
    check(re.fullmatch(r'\d+\.\d+\.\d+', short), f'bad shortVersionString {short!r}')
    check(bld.isdigit(), f'bad sparkle:version {bld!r}')
    check(version is None or short == version, f'appcast version {short} != expected {version}')
    check(build is None or bld == str(build), f'appcast build {bld} != expected {build}')
    check(text('minimumSystemVersion') == MIN_OS, 'minimumSystemVersion is not ' + MIN_OS)
    check(text('hardwareRequirements') == 'arm64', 'hardwareRequirements must be arm64 (Parzr is Apple Silicon only)')
    is_crit = it.find('sparkle:criticalUpdate', NS) is not None
    check(critical is None or is_crit == critical, f'criticalUpdate present={is_crit}, expected {critical}')
    phased = text('phasedRolloutInterval')
    check(is_crit != bool(phased), 'exactly one of criticalUpdate or phasedRolloutInterval is required')
    check(not phased or phased.isdigit(), f'bad phasedRolloutInterval {phased!r}')
    desc = it.find('description')
    check(desc is not None and (desc.text or '').strip(), 'missing release notes description')
    check(desc.get(f'{SP}format') == 'markdown', 'description must be markdown')
    base = f'https://github.com/{REPO}/releases/download/v{short}/'
    pub = base64.b64decode(public_key)
    encs = [(it.find('enclosure'), False)] + [(e, True) for e in it.findall('sparkle:deltas/enclosure', NS)]
    for e, is_delta in encs:
        url = e.get('url')
        check(url.startswith(base) and url.count('/') == base.count('/'), f'enclosure URL {url} is not under {base}')
        check(e.get(f'{SP}version') == bld and e.get(f'{SP}shortVersionString') == short, f'enclosure version attrs differ from the item: {url}')
        check(bool(e.get(f'{SP}deltaFrom', '').isdigit()) == is_delta, f'deltaFrom misuse on {url}')
        check(is_delta == url.endswith('.delta') and (is_delta or url.endswith('.zip')), f'unexpected file type {url}')
        local = fetch(url)
        check(os.path.getsize(local) == int(e.get('length')), f'length mismatch for {url}: {os.path.getsize(local)} != {e.get("length")}')
        check(ed25519_verify(pub, base64.b64decode(e.get(f'{SP}edSignature')), local), f'EdDSA signature does NOT verify against the public key: {url}')
        print(f'  ok {url.rsplit("/", 1)[1]}: {e.get("length")} bytes, signature verifies')
    return short, bld, it


def cmd_build(a):
    app, out = pathlib.Path(a.app), pathlib.Path(a.out)
    plist = info(app)
    check(plist['CFBundleShortVersionString'] == a.version, f'app version {plist["CFBundleShortVersionString"]} != {a.version}')
    build = str(plist['CFBundleVersion'])
    check(build.isdigit(), f'CFBundleVersion {build!r} must be an integer for sparkle:version ordering')
    check(plist.get('SUPublicEDKey') == a.public_key, 'app Info.plist SUPublicEDKey does not match the pinned public key')
    check((app / 'Contents/Frameworks/Sparkle.framework').exists(), 'app does not embed Sparkle.framework')
    if not a.skip_gatekeeper:  # the update must be the exact notarized, stapled app users get in the DMG
        run(['xcrun', 'stapler', 'validate', str(app)])
        run(['spctl', '--assess', '--type', 'execute', str(app)])
    tools = sparkle_bin(a.sparkle_bin)
    out.mkdir(parents=True, exist_ok=True)
    for old in list(out.glob('*.zip')) + list(out.glob('*.delta')) + list(out.glob('appcast.xml')):
        old.unlink()
    zip_path = out / f'Parzr-{a.version}.zip'
    run(['ditto', '-c', '-k', '--sequesterRsrc', '--keepParent', str(app), str(zip_path)])
    zip_sig, zip_len = sign(tools, zip_path, a.key_file), zip_path.stat().st_size
    print(f'update zip {zip_path.name}: {zip_len} bytes')

    work = pathlib.Path(tempfile.mkdtemp(prefix='parzr-appcast-'))
    prev = []  # (build, version, app) newest first
    for z in sorted(pathlib.Path(a.prev_dir).glob('Parzr-*.zip')) if a.prev_dir else []:
        d = work / f'prev-{z.stem}'
        pa = unzip(z, d)
        pi = info(pa)
        if int(pi['CFBundleVersion']) < int(build):
            prev.append((int(pi['CFBundleVersion']), pi['CFBundleShortVersionString'], pa))
    prev = sorted(prev, reverse=True)[:MAX_DELTAS]
    deltas = []
    for pb, pv, pa in prev:
        name = f'Parzr-{a.version}-from-{pv}.delta'
        run([str(tools / 'BinaryDelta'), 'create', str(pa), str(app), str(out / name)])
        ln = (out / name).stat().st_size
        if ln >= zip_len * 0.9:
            print(f'  skip delta from {pv}: {ln} bytes is not smaller than the full update'); (out / name).unlink(); continue
        print(f'delta from {pv} (build {pb}): {ln} bytes ({100 * ln / zip_len:.1f}% of the full zip)')
        deltas.append((name, ln, sign(tools, out / name, a.key_file), str(pb)))

    now = datetime.datetime.now(datetime.timezone.utc)
    write_appcast(out / 'appcast.xml', a.version, build, (zip_path.name, zip_len, zip_sig, deltas),
                  bullets(a.notes, a.git_range), a.critical, a.phased_interval, now)

    # Verify our own output from the files on disk, as a client would receive them.
    print('verifying output')
    verify_appcast(out / 'appcast.xml', lambda url: out / url.rsplit('/', 1)[1], a.public_key, a.version, a.critical, build)
    check(not [p for p in out.glob('*.delta')] or len(deltas) == len(list(out.glob('*.delta'))), 'stray delta files in output')
    new_hash = tree_hash(app)
    check(tree_hash(unzip(zip_path, work / 'zipcheck')) == new_hash, 'update zip content differs from the app')
    print('  ok zip extracts to the same bundle content as the app')
    for pb, pv, pa in prev:
        patch = out / f'Parzr-{a.version}-from-{pv}.delta'
        if not patch.exists():
            continue
        patched = work / f'patched-{pv}'
        run([str(tools / 'BinaryDelta'), 'apply', str(pa), str(patched), str(patch)])
        check(tree_hash(patched) == new_hash, f'delta from {pv} does not reproduce the new app')
        print(f'  ok delta from {pv} applies and reproduces the new app')
    shutil.rmtree(work, ignore_errors=True)
    print(f'appcast ok: {out / "appcast.xml"}')


def cmd_verify(a):
    work = pathlib.Path(tempfile.mkdtemp(prefix='parzr-verify-'))
    def fetch(url):
        if a.dir:
            return pathlib.Path(a.dir) / url.rsplit('/', 1)[1]
        dest = work / url.rsplit('/', 1)[1]
        for attempt in range(4):  # the release CDN can lag a few seconds right after publishing
            try:
                urllib.request.urlretrieve(url, dest)
                return dest
            except OSError as e:
                if attempt == 3:
                    die(f'could not download {url}: {e}')
                time.sleep(10)
    src = a.appcast
    local = fetch(src) if src.startswith('https://') else src
    verify_appcast(local, fetch, a.public_key, a.version)
    shutil.rmtree(work, ignore_errors=True)
    print('published appcast verified')


def main():
    self_test()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    for name in ('build', 'verify'):
        s = sub.add_parser(name)
        s.add_argument('--public-key', default=PUBLIC_KEY, help='base64 EdDSA public key (default: the Parzr key; override for tests only)')
        s.add_argument('--version')
        if name == 'build':
            s.add_argument('--app', required=True)
            s.add_argument('--out', required=True)
            s.add_argument('--prev-dir')
            s.add_argument('--key-file', help='private key file; default is $SPARKLE_ED_PRIVATE_KEY on stdin')
            s.add_argument('--sparkle-bin')
            s.add_argument('--notes', default='')
            s.add_argument('--git-range', help='fallback notes: commit subjects in this git range')
            s.add_argument('--critical', action='store_true')
            s.add_argument('--skip-gatekeeper', action='store_true', help='tests only: skip the stapler and spctl checks')
            s.add_argument('--phased-interval', type=int, default=43200, help='seconds between rollout groups (default 12 h)')
        else:
            s.add_argument('--appcast', required=True)
            s.add_argument('--dir', help='read enclosures from this directory instead of downloading their URLs')
    a = ap.parse_args()
    if a.cmd == 'build':
        check(a.version, '--version is required')
        cmd_build(a)
    else:
        cmd_verify(a)


if __name__ == '__main__':
    main()
