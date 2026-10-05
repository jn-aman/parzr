#!/usr/bin/env python3
"""Build-time preparation only. The installed app never downloads its runtime or model."""
import argparse, hashlib, json, os, pathlib, shutil, subprocess, urllib.request, zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
REVISION = 'dd266785c2595775001c1c714bd9d92b3ef34cde'
MODEL_REVISION = '8fea620810c4afa23dd6443f999a48574c1611a3'
SOURCE_NAME = 'Qwen3.5-0.8B-Q8_0.gguf'
MODEL_NAME = 'Qwen3.5-0.8B-Q5_K_M.gguf'
# GECToR (Core ML, built by scripts/convert-gector.py), published as assets of the jn-aman/parzr release `gector-v1`.
# PARZR_GEC_SOURCE=<local zip> replaces the download (the zip must still match one of the pinned hashes below).
GEC_VARIANT = 'int8'
GEC_URL = 'https://github.com/jn-aman/parzr/releases/download/gector-v1/'
GEC_ZIPS = {
    'fp16': ('gector-roberta-base-5k-coreml-fp16.zip', 'e82d046295ab2bc939776dc0b44ed7a4e83fd0de7b67e511fc2c0b822f48dcea'),
    'int8': ('gector-roberta-base-5k-coreml-int8.zip', '9e3d2c433206b4eea2cb612c1a32765a24bf39ba2eef9a1c51a9ed8942427796'),
}
MODEL_SHA = '7c4692492a3f74a4678ee31f9ab15e14341a1fea4bf9aca975c73f7f5b3884a4'
SOURCE_SHA = '37ae482d336108d23516fa35e8e0c4126688d81018b87178a18d752a1357814f'
parser = argparse.ArgumentParser(description=__doc__)
args = parser.parse_args()
cache = ROOT/'dist/model'; cache.mkdir(parents=True, exist_ok=True)

def digest(path):
    with path.open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()
def run(command, env=None):
    subprocess.run([str(x) for x in command], cwd=ROOT, env=env, check=True)
def download(url, destination, expected=None):
    temporary = destination.with_suffix('.partial')
    with urllib.request.urlopen(url, timeout=90) as source, temporary.open('wb') as output:
        shutil.copyfileobj(source, output, 1024*1024)
    if expected and digest(temporary) != expected:
        temporary.unlink(); raise SystemExit('Downloaded model failed SHA-256 verification.')
    temporary.replace(destination)

model = cache/SOURCE_NAME
if not model.exists():
    candidate = ROOT/'dist/qa/qwen35'/SOURCE_NAME
    if candidate.exists() and digest(candidate) == SOURCE_SHA: shutil.copy2(candidate, model)
    else: download(f'https://huggingface.co/ggml-org/Qwen3.5-0.8B-GGUF/resolve/{MODEL_REVISION}/{SOURCE_NAME}', model, SOURCE_SHA)
if digest(model) != SOURCE_SHA: raise SystemExit('Cached model failed SHA-256 verification.')
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
quantized = cache/MODEL_NAME
if not quantized.exists():
    candidate = ROOT/'dist/qa/qwen35'/MODEL_NAME
    if candidate.exists() and digest(candidate) == MODEL_SHA: shutil.copy2(candidate, quantized)
    else:
        host_arch = subprocess.check_output(['uname','-m'], text=True).strip()
        host_build = ROOT/f'dist/llama-build-{host_arch}'
        run([cmake, '--build', host_build, '--target', 'llama-quantize', '-j', '2'])
        run([host_build/'bin/llama-quantize', '--allow-requantize', model, quantized, 'Q5_K_M'])
if digest(quantized) != MODEL_SHA: raise SystemExit('Derived Q5 model failed SHA-256 verification.')
model = quantized
# Replace, never overwrite in place: macOS caches code signatures per vnode and kills a process
# that loads a library rewritten under it (exit 137, Code Signature Invalid).
(cache/'libparzr_model.dylib').unlink(missing_ok=True); shutil.copy2(outputs[0], cache/'libparzr_model.dylib')
shutil.copy2(source/'LICENSE', cache/'llama-LICENSE.txt')
license_path = ROOT/'resources/ThirdParty/Qwen3.5-LICENSE.txt'
if not license_path.is_file(): raise SystemExit('Missing Qwen3.5 Apache 2.0 license.')
(cache/'manifest.json').write_text(json.dumps({'name':'Qwen3.5-0.8B', 'quantization':'Q5_K_M', 'conversion':'llama-quantize --allow-requantize Q5_K_M', 'source_sha256':SOURCE_SHA, 'file':MODEL_NAME, 'bytes':model.stat().st_size, 'sha256':MODEL_SHA, 'source_revision':MODEL_REVISION, 'source':'ggml-org/Qwen3.5-0.8B-GGUF', 'runtime_revision':REVISION, 'offline':True}, indent=2)+'\n')

# GECToR directory beside the Qwen model: dist/model/gector (gector.mlmodelc, vocabularies, labels, manifest.json). Unpacked once per zip hash.
gec_name, gec_sha = GEC_ZIPS[GEC_VARIANT]
gec_zip = pathlib.Path(os.environ['PARZR_GEC_SOURCE']).resolve() if os.environ.get('PARZR_GEC_SOURCE') else cache/gec_name
gec_dir, gec_marker = cache/'gector', cache/'gector.sha256'
if gec_marker.is_file() and gec_marker.read_text().strip() == gec_sha and (gec_dir/'manifest.json').is_file():
    pass
else:
    if not gec_zip.exists(): download(GEC_URL+gec_name, gec_zip, gec_sha)
    if digest(gec_zip) != gec_sha: raise SystemExit(f'GECToR archive failed SHA-256 verification (expected the {GEC_VARIANT} build).')
    shutil.rmtree(gec_dir, ignore_errors=True); gec_marker.unlink(missing_ok=True)
    with zipfile.ZipFile(gec_zip) as archive: archive.extractall(gec_dir)
    listed = json.loads((gec_dir/'manifest.json').read_text())['files']
    for name, sha in listed.items():
        if not (gec_dir/name).is_file() or digest(gec_dir/name) != sha: raise SystemExit('Unpacked GECToR file failed SHA-256 verification: '+name)
    gec_marker.write_text(gec_sha+'\n')
print('Bundled offline model and native runtime prepared; hashes verified.')
