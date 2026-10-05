#!/usr/bin/env python3
"""Maintainer tool (not part of the app build): convert GECToR to the Core ML directory Parzr bundles.

Source: gotutiyan/gector-roberta-base-5k at the pinned revision (RoBERTa base plus two linear heads, 5001 edit labels).
Output (--out, default dist/gector-build): for each variant (fp16, int8) a `gector-roberta-base-5k-coreml-<variant>/` directory and
a deterministic `.zip` of its contents (no top level folder). The directory holds exactly what native/model.mm and the engine read:
  gector.mlmodelc/     static 80 token model, one int32 input `input_ids` [1,80] padded with pad id 1 (the attention mask is
                       derived from the pad id inside the model), outputs `logits_labels` [1,80,5001] and `logits_d` [1,80,2]
  vocab.json merges.txt added_tokens.json   RoBERTa byte level BPE ($START = 50265)
  labels.txt           5002 lines, config.json id2label in id order
  verb-form-vocab.txt  grammarly/gector data/, pinned by commit and sha256
  manifest.json        revisions, sha256 of every file, versions, licence notes
Variants: fp16 (macOS 13 mlprogram, compute precision FLOAT16) and int8 (the same with linear_symmetric per channel int8
weight-only quantization). Measured against torch fp32 on 300 sentences: tag identity about 98.7% (fp16), about 93% (int8).
Flexible shapes crash or are slow on the Neural Engine, hence the single static shape. Compiled with `xcrun coremlcompiler compile`.
The zip is byte for byte reproducible from a given directory (sorted entries, fixed time stamps and modes); the compiled model
itself comes from the toolchain, so a rebuilt model may hash differently: the released zip's sha256 is what prepare-model.py pins.

Requirements (a venv with exactly these; transformers 5 breaks tracing):
  pip install coremltools==9.0 torch==2.7.0 transformers==4.46.3 numpy==2.2.6 safetensors huggingface_hub
Run: python3 scripts/convert-gector.py [--out DIR] [--variants fp16 int8]
"""
import argparse, hashlib, json, pathlib, platform, shutil, subprocess, sys, urllib.request, zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
REPO = 'gotutiyan/gector-roberta-base-5k'
REVISION = 'adaac6fb919431fb5a038b1e449055ae638613a4'
GECTOR_COMMIT = '4ad259f25c6bb408a99788d468cd8958845e647e'
VERB_URL = f'https://raw.githubusercontent.com/grammarly/gector/{GECTOR_COMMIT}/data/verb-form-vocab.txt'
VERB_SHA = '5906804ec8a1acd8cbfc2918522bf429ce5edded8bbc46ffc2be861d280d3abf'
LENGTH, PAD = 80, 1
parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument('--out', type=pathlib.Path, default=ROOT/'dist/gector-build')
parser.add_argument('--variants', nargs='+', default=['fp16', 'int8'], choices=['fp16', 'int8'])
args = parser.parse_args()

def digest(path):
    with path.open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()

import numpy as np, torch, coremltools as ct, coremltools.optimize.coreml as cto, transformers
from huggingface_hub import snapshot_download
from safetensors.torch import load_file
from transformers import AutoConfig, AutoModel

checkpoint = pathlib.Path(snapshot_download(REPO, revision=REVISION, allow_patterns=['config.json', 'model.safetensors', 'vocab.json', 'merges.txt', 'added_tokens.json']))
config = json.loads((checkpoint/'config.json').read_text())

class GECToR(torch.nn.Module):
    """The checkpoint's architecture: RoBERTa base (embedding extended by $START), a label head and a detection head."""
    def __init__(self):
        super().__init__()
        # The roberta-base config.json values (layer_norm_eps is 1e-5, not the library default).
        roberta = AutoConfig.for_model('roberta', vocab_size=50266, hidden_size=768, num_hidden_layers=12, num_attention_heads=12, intermediate_size=3072, hidden_act='gelu', max_position_embeddings=514, type_vocab_size=1, layer_norm_eps=1e-5, pad_token_id=PAD, bos_token_id=0, eos_token_id=2)
        self.bert = AutoModel.from_config(roberta, add_pooling_layer=False)
        self.label_proj_layer = torch.nn.Linear(768, config['n_labels'] - 1)  # the last label is <PAD>, never predicted
        self.d_proj_layer = torch.nn.Linear(768, config['n_d_labels'] - 1)
    def forward(self, input_ids):
        hidden = self.bert(input_ids, attention_mask=(input_ids != PAD).long()).last_hidden_state
        return self.label_proj_layer(hidden), self.d_proj_layer(hidden)

model = GECToR().eval()
state = {k: v for k, v in load_file(str(checkpoint/'model.safetensors')).items() if 'position_ids' not in k}
print('load_state_dict', model.load_state_dict(state, strict=False))
sample = torch.tensor([[0, 50265, 713, 16, 10, 1296, 4, 2] + [PAD] * (LENGTH - 8)])
with torch.no_grad(): traced = torch.jit.trace(model, (sample,), strict=False)

args.out.mkdir(parents=True, exist_ok=True)
work = args.out/'work'; shutil.rmtree(work, ignore_errors=True); work.mkdir()
verb = work/'verb-form-vocab.txt'
with urllib.request.urlopen(VERB_URL, timeout=120) as source: verb.write_bytes(source.read())
if digest(verb) != VERB_SHA: sys.exit('verb-form-vocab.txt failed SHA-256 verification.')
labels = [label for _, label in sorted(config['id2label'].items(), key=lambda item: int(item[0]))]
assert len(labels) == 5002 and labels[1] == '$KEEP' and labels[-1] == '<PAD>'

ml = ct.convert(traced, inputs=[ct.TensorType(name='input_ids', shape=(1, LENGTH), dtype=np.int32)],
                outputs=[ct.TensorType(name='logits_labels'), ct.TensorType(name='logits_d')],
                compute_precision=ct.precision.FLOAT16, minimum_deployment_target=ct.target.macOS13, convert_to='mlprogram')
models = {'fp16': ml}
if 'int8' in args.variants:
    models['int8'] = cto.linear_quantize_weights(ml, cto.OptimizationConfig(global_config=cto.OpLinearQuantizerConfig(mode='linear_symmetric', dtype='int8', granularity='per_channel')))

for variant in args.variants:
    name = f'gector-roberta-base-5k-coreml-{variant}'
    directory = args.out/name; shutil.rmtree(directory, ignore_errors=True); directory.mkdir()
    package = work/f'{variant}.mlpackage'; models[variant].save(str(package))
    subprocess.run(['xcrun', 'coremlcompiler', 'compile', str(package), str(work)], check=True)
    shutil.move(str(work/f'{variant}.mlmodelc'), directory/'gector.mlmodelc')
    for file in ['vocab.json', 'merges.txt', 'added_tokens.json']: shutil.copy2(checkpoint/file, directory/file)
    shutil.copy2(verb, directory/'verb-form-vocab.txt')
    (directory/'labels.txt').write_text('\n'.join(labels) + '\n')
    files = sorted(p for p in directory.rglob('*') if p.is_file())
    manifest = {'name': 'gector-roberta-base-5k', 'variant': variant, 'format': 'Core ML mlprogram, static 80 tokens, input_ids int32 [1,80] padded with 1',
                'quantization': 'none, compute precision float16' if variant == 'fp16' else 'int8 weight-only, linear_symmetric per channel',
                'source': REPO, 'source_revision': REVISION, 'base_model': 'roberta-base (MIT, Facebook AI)',
                'verb_form_vocab': {'source': 'grammarly/gector data/verb-form-vocab.txt', 'commit': GECTOR_COMMIT, 'sha256': VERB_SHA, 'license': 'Apache-2.0'},
                'conversion': {'script': 'scripts/convert-gector.py', 'coremltools': ct.__version__, 'torch': torch.__version__, 'transformers': transformers.__version__, 'numpy': np.__version__, 'deployment_target': 'macOS 13', 'host': platform.platform()},
                'license_notes': 'Weights: model card of gotutiyan/gector-roberta-base-5k says "Only non-commercial purposes". Omelianchuk et al. 2020, GECToR (Grammarly), Apache-2.0 code and vocabularies. RoBERTa tokenizer files MIT.',
                'files': {str(p.relative_to(directory)): digest(p) for p in files if p.name != 'manifest.json'}}
    (directory/'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    archive = args.out/f'{name}.zip'; archive.unlink(missing_ok=True)
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in sorted(p for p in directory.rglob('*') if p.is_file()):
            info = zipfile.ZipInfo(str(p.relative_to(directory)), (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED; info.external_attr = 0o644 << 16
            z.writestr(info, p.read_bytes(), compresslevel=9)
    print(f'{archive.name} {archive.stat().st_size} bytes sha256 {digest(archive)}')
shutil.rmtree(work)
