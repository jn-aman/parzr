#!/usr/bin/env python3
"""Builds the native model runtime (libparzr_model.dylib: llama.cpp, Core ML and the macOS tagger) into dist/model.

The runtime is code and ships in the app. The model weights do not: they are a pinned model pack
(engine/models.json) that the app downloads on demand; scripts/model-pack.py fetches the same pack
for development and CI."""
import argparse, pathlib, shutil, subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent
REVISION = 'dd266785c2595775001c1c714bd9d92b3ef34cde'
parser = argparse.ArgumentParser(description=__doc__)
args = parser.parse_args()
cache = ROOT/'dist/model'; cache.mkdir(parents=True, exist_ok=True)

def run(command, env=None):
    subprocess.run([str(x) for x in command], cwd=ROOT, env=env, check=True)

source = ROOT/'dist/llama-source'
if not source.exists():
    run(['git', 'clone', '--no-checkout', 'https://github.com/ggml-org/llama.cpp.git', source])
    run(['git', '-C', source, 'checkout', '--detach', REVISION])
if subprocess.check_output(['git', '-C', source, 'rev-parse', 'HEAD'], text=True).strip() != REVISION:
    raise SystemExit('llama.cpp source revision does not match the pinned runtime.')
cmake = shutil.which('cmake')
if not cmake:
    local = ROOT/'dist/qa/frequency-build/bin/cmake'
    if local.exists(): cmake = str(local)
if not cmake: raise SystemExit('Build requires CMake 3.28 or newer.')
architectures = ['arm64']
if subprocess.check_output(['uname','-m'],text=True).strip() != 'arm64': raise SystemExit('Build Parzr on an Apple Silicon Mac.')
outputs = []
for arch in architectures:
    build = ROOT/f'dist/llama-build-{arch}'
    remap = f'-ffile-prefix-map={pathlib.Path.home()}=/build-user'
    run([cmake, '-S', source, '-B', build, '-DCMAKE_BUILD_TYPE=Release', f'-DCMAKE_OSX_ARCHITECTURES={arch}', '-DCMAKE_OSX_DEPLOYMENT_TARGET=13.0', '-DBUILD_SHARED_LIBS=OFF', '-DGGML_NATIVE=OFF', '-DLLAMA_BUILD_TESTS=OFF', '-DLLAMA_BUILD_EXAMPLES=OFF', '-DLLAMA_BUILD_SERVER=OFF', '-DLLAMA_OPENSSL=OFF', '-DGGML_METAL_EMBED_LIBRARY=ON', f'-DCMAKE_C_FLAGS={remap}', f'-DCMAKE_CXX_FLAGS={remap}'])
    run([cmake, '--build', build, '--target', 'llama', '-j', '2'])
    libraries = [build/'src/libllama.a', build/'ggml/src/libggml.a', build/'ggml/src/libggml-cpu.a', build/'ggml/src/ggml-blas/libggml-blas.a']
    libraries.append(build/'ggml/src/ggml-metal/libggml-metal.a')
    libraries.append(build/'ggml/src/libggml-base.a')
    out = cache/f'libparzr_model-{arch}.dylib'; outputs.append(out)
    command = ['clang++', '-std=c++17', '-O3', '-dynamiclib', '-arch', arch, '-mmacosx-version-min=13.0', remap, '-I', source/'include', '-I', source/'ggml/include', ROOT/'native/model.mm', *libraries, '-framework', 'Accelerate', '-framework', 'Foundation', '-framework', 'NaturalLanguage', '-fobjc-arc']
    command += ['-framework', 'Metal', '-framework', 'MetalKit']
    # AppKit: NSSpellChecker tells lowercase names apart from typos (see parzr_model_token_hints).
    command += ['-framework', 'AppKit']
    # CoreML: GECToR on the Neural Engine (parzr_gec_*).
    command += ['-framework', 'CoreML']
    command += ['-Wl,-install_name,@rpath/libparzr_model.dylib', '-o', out]
    run(command)
# Replace, never overwrite in place: macOS caches code signatures per vnode and kills a process
# that loads a library rewritten under it (exit 137, Code Signature Invalid).
(cache/'libparzr_model.dylib').unlink(missing_ok=True); shutil.copy2(outputs[0], cache/'libparzr_model.dylib')
shutil.copy2(source/'LICENSE', cache/'llama-LICENSE.txt')
print('Native model runtime built: dist/model/libparzr_model.dylib (no model weights; see scripts/model-pack.py).')
