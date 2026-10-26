"""One round: generate, drop what the engine already fixes, write the pack, rebuild the engine, verify.
usage: python3 cycle.py [--base ENGINE_WITHOUT_PACK] (run from this folder)"""
import os, pathlib, subprocess, sys
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = '/private/tmp/claude-501/-Users-aman-Desktop/a2be551f-0769-47a8-ba8d-479a16ade0ab/scratchpad/pron/engine-base'
if '--base' in sys.argv:
    BASE = sys.argv[sys.argv.index('--base') + 1]
env = dict(os.environ)
env['PATH'] = os.path.expanduser('~/.cargo/bin') + ':' + env['PATH']


def run(cmd, **kw):
    print('$', ' '.join(cmd))
    r = subprocess.run(cmd, cwd=kw.pop('cwd', HERE), env=env, **kw)
    return r.returncode


if run(['python3', 'build.py']):
    sys.exit(1)
run(['python3', 'measure.py', BASE, '--write', 'skipped-ids.txt'], stdout=subprocess.DEVNULL)
if run(['python3', 'build.py', '--dump']):
    sys.exit(1)
if run(['python3', str(ROOT / 'scripts/check-rule-packs.py'), str(ROOT / 'engine/rules/packs/pronouns.json')], cwd=ROOT):
    sys.exit(1)
if run(['cargo', 'build', '--release', '--manifest-path', str(ROOT / 'engine/Cargo.toml')], cwd=ROOT):
    sys.exit(1)
sys.exit(run(['python3', 'verify.py', str(ROOT / 'engine/target/release/parzr-engine')]))
