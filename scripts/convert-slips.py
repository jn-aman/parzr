#!/usr/bin/env python3
"""Maintainer tool (not part of the app build): convert distilroberta-base to the Core ML slip checker Parzr downloads.

The typing-time word-choice check (engine/src/slips.rs) asks one question of a masked language model: with a word of the
sentence masked, how likely is each spelling the writer may have meant ("hat" or "hate", "then" or "than")? So the Core ML
model is not a plain fill-mask model: it takes a batch of masked rows and, for each row, the position of its mask and the
token ids to score there, and returns their log-probabilities. The language-model head runs at that one position only,
which halves the work of a full fill-mask pass and returns a few numbers instead of 8 x 64 x 50,265 logits.

Source: distilbert/distilroberta-base at the pinned revision (Apache-2.0; 6 layers, 82M parameters, RoBERTa's byte-level
BPE). The network is written out here in plain torch ops (no transformers modelling code, whose mask builder coremltools
cannot convert), and checked against the reference forward of transformers when it is installed.

Inputs (int32): `ids` [B, L] padded with 1 (the attention mask is derived from the pad id inside the model), `position`
[B] (the masked token of each row), `targets` [B, K] (token ids to score at that position; pad unused slots with 1).
Output: `logp` [B, K] log-probabilities (natural log).

Output (--out, default dist/slips-build/slips): exactly the pack folder the engine reads:
  mlm.mlmodelc/   the compiled model (int8 weight-only, linear_symmetric per channel; fp16 compute)
  vocab.json merges.txt   RoBERTa byte-level BPE, copied from the source revision
  manifest.json   revisions, shapes, sha256 of every file, conversion versions, license
Then the script prints the models.json entries (path, bytes, sha256) for the `slips` pack. A rebuilt model may hash
differently (the compiler comes from the toolchain), so the released assets' hashes are what engine/models.json pins.

Run (a venv with torch, coremltools 9, safetensors, numpy; transformers optional, for the parity check):
  venv/bin/python -I scripts/convert-slips.py --source <folder with the pinned model.safetensors, vocab.json, merges.txt>
or let it download the pinned files from Hugging Face (huggingface_hub): --download
"""
import argparse, hashlib, json, math, pathlib, platform, shutil, subprocess, sys, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
REPO = 'distilbert/distilroberta-base'
REVISION = 'fb53ab8802853c8e4fbdbcd0529f21fc6f459b2b'
PINNED = {'model.safetensors': '2b11ca9cf3d2cbb44cc1a93ad96aedc2894231ae6e33e2d2268c3d7b1ff97663'}
BATCH, LENGTH, TARGETS, PAD = 8, 64, 16, 1
LAYERS, HEADS, HIDDEN, VOCAB, EPS = 6, 12, 768, 50265, 1e-5

parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument('--source', type=pathlib.Path)
parser.add_argument('--download', action='store_true')
parser.add_argument('--out', type=pathlib.Path, default=ROOT/'dist/slips-build/slips')
parser.add_argument('--precision', choices=['int8', 'fp16'], default='int8')
parser.add_argument('--length', type=int, default=LENGTH)
parser.add_argument('--batch', type=int, default=BATCH)
parser.add_argument('--time', action='store_true', help='also time predictions per compute unit')
args = parser.parse_args()


def digest(path):
    with path.open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()


if args.download:
    from huggingface_hub import snapshot_download
    args.source = pathlib.Path(snapshot_download(REPO, revision=REVISION, allow_patterns=['model.safetensors', 'vocab.json', 'merges.txt']))
if not args.source: sys.exit('Give --source or --download.')
for name, sha in PINNED.items():
    if digest(args.source/name) != sha: sys.exit(f'{name} does not match the pinned SHA-256 of {REPO}@{REVISION}.')

import numpy as np, torch, coremltools as ct, coremltools.optimize.coreml as cto
from safetensors.torch import load_file

weights = load_file(str(args.source/'model.safetensors'))


class SlipModel(torch.nn.Module):
    """distilroberta-base with its masked-LM head applied at one position per row, scored for K token ids."""
    def __init__(self, w):
        super().__init__()
        p = lambda name: torch.nn.Parameter(w[name].float(), requires_grad=False)
        self.word = p('roberta.embeddings.word_embeddings.weight')
        # Row 1 (the pad position) is all zeros, which per-channel int8 quantization cannot scale; pads are masked out of
        # attention and never read, so any finite row will do. The one token-type row is all zeros too and is left out.
        position = w['roberta.embeddings.position_embeddings.weight'].float().clone()
        position[PAD] = position[PAD + 1]
        self.position = torch.nn.Parameter(position, requires_grad=False)
        assert not w['roberta.embeddings.token_type_embeddings.weight'].any()
        self.ln_e = (p('roberta.embeddings.LayerNorm.weight'), p('roberta.embeddings.LayerNorm.bias'))
        self.layers = []
        for i in range(LAYERS):
            q = f'roberta.encoder.layer.{i}.'
            names = ['attention.self.query', 'attention.self.key', 'attention.self.value', 'attention.output.dense', 'intermediate.dense', 'output.dense']
            layer = {n: (p(q+n+'.weight'), p(q+n+'.bias')) for n in names}
            layer['ln1'] = (p(q+'attention.output.LayerNorm.weight'), p(q+'attention.output.LayerNorm.bias'))
            layer['ln2'] = (p(q+'output.LayerNorm.weight'), p(q+'output.LayerNorm.bias'))
            self.layers.append(layer)
            for k, v in layer.items():
                self.register_parameter(f'l{i}_{k.replace(".", "_")}_w', v[0]); self.register_parameter(f'l{i}_{k.replace(".", "_")}_b', v[1])
        self.head_dense = (p('lm_head.dense.weight'), p('lm_head.dense.bias'))
        self.head_ln = (p('lm_head.layer_norm.weight'), p('lm_head.layer_norm.bias'))
        self.head_bias = p('lm_head.bias')
        for i, t in enumerate([*self.ln_e, *self.head_dense, *self.head_ln]): self.register_parameter(f'extra{i}', t)

    @staticmethod
    def ln(x, wb):
        return torch.nn.functional.layer_norm(x, (HIDDEN,), wb[0], wb[1], EPS)

    def forward(self, ids, position, targets):
        b, n = self.shape  # fixed at conversion (traced shapes would turn into dynamic size ops)
        real = (ids != PAD).to(torch.float32)                              # [B, L]
        # RoBERTa positions: padding_idx + 1 + index for real tokens (rows are right-padded), padding_idx for pads.
        steps = torch.arange(n, dtype=torch.float32).unsqueeze(0)          # [1, L]
        pos_ids = (real * (steps + 1) + PAD).to(torch.int32)
        x = self.word[ids] + self.position[pos_ids]
        x = self.ln(x, self.ln_e)
        bias = ((1.0 - real) * -10000.0).view(b, 1, 1, n)                  # additive attention mask
        d = HIDDEN // HEADS
        for layer in self.layers:
            lin = lambda t, k: torch.nn.functional.linear(t, *layer[k])
            q = lin(x, 'attention.self.query').view(b, n, HEADS, d).transpose(1, 2)
            k = lin(x, 'attention.self.key').view(b, n, HEADS, d).transpose(1, 2)
            v = lin(x, 'attention.self.value').view(b, n, HEADS, d).transpose(1, 2)
            att = torch.softmax(q @ k.transpose(-1, -2) / math.sqrt(d) + bias, dim=-1)
            ctx = (att @ v).transpose(1, 2).reshape(b, n, HIDDEN)
            x = self.ln(lin(ctx, 'attention.output.dense') + x, layer['ln1'])
            h = torch.nn.functional.gelu(lin(x, 'intermediate.dense'))
            x = self.ln(lin(h, 'output.dense') + x, layer['ln2'])
        # The hidden state at each row's masked position (a one-hot product: no dynamic indexing on the Neural Engine).
        pick = (steps == position.to(torch.float32).unsqueeze(1)).to(torch.float32)   # [B, L]
        at = (pick.unsqueeze(1) @ x).squeeze(1)                                         # [B, H]
        h = self.ln(torch.nn.functional.gelu(torch.nn.functional.linear(at, *self.head_dense)), self.head_ln)
        logits = torch.nn.functional.linear(h, self.word, self.head_bias)               # [B, V]
        # log-softmax written out: in float16 the Neural Engine's log(softmax) floors every probability below
        # e^-16.6 (the smallest half) to log(0); the logit less the log-sum-exp never takes the log of a tiny number.
        top = logits.max(dim=-1, keepdim=True).values
        total = torch.log(torch.exp(logits - top).sum(dim=-1, keepdim=True))
        return torch.gather(logits, 1, targets.to(torch.int64)) - top - total


B, L, K = args.batch, args.length, TARGETS
model = SlipModel(weights).eval()
model.shape = (B, L)
# Sample rows: real sentences with one word masked (RoBERTa ids, <s> ... </s>, right-padded), scored for the model's own
# 16 most likely tokens there, the kind of targets a check compares.
SAMPLES = [
    ([0, 100, 2, 50264, 24, 4, 2], 3),                                   # "I <mask> it."
    ([0, 133, 1012, 16, 50264, 87, 52, 802, 4, 2], 4),                  # "The project is <mask> than we thought."
    ([0, 2387, 2602, 50264, 1007, 4, 2], 3),
    ([0, 100, 581, 28, 50264, 5, 558, 454, 231, 4, 2], 4),             # "I'll be <mask> the office until 6."
    ([0, 9904, 47, 1649, 50264, 10, 2], 4),
    ([0, 133, 2], 1),
    ([0, 50264, 2], 1),
    ([0] + list(range(1000, 1000 + L - 3)) + [50264, 2], L - 2),        # a full-length row
]
ids = torch.full((B, L), PAD, dtype=torch.int32)
for r in range(B):
    row, _ = SAMPLES[r % len(SAMPLES)]
    ids[r, :len(row)] = torch.tensor(row[:L], dtype=torch.int32)
position = torch.tensor([min(SAMPLES[r % len(SAMPLES)][1], L - 2) for r in range(B)], dtype=torch.int32)
for r in range(B): ids[r, position[r]] = 50264
with torch.no_grad():
    everything = model(ids, position, torch.arange(VOCAB, dtype=torch.int32).repeat(B, 1).contiguous())
    # The 8 likeliest tokens and 8 unlikely ones (a typed slip is often far below -17 nats, where float16 is fragile).
    likeliest = everything.topk(K // 2, dim=1).indices.to(torch.int32)
    unlikely = torch.tensor(np.random.default_rng(7).integers(4, VOCAB, (B, K - K // 2)), dtype=torch.int32)
    targets = torch.cat([likeliest, unlikely], dim=1).contiguous()
    reference = model(ids, position, targets).numpy()

# Parity with transformers' reference forward, when it is installed (masked rows, padded batch).
try:
    from transformers import AutoModelForMaskedLM
    hf = AutoModelForMaskedLM.from_pretrained(str(args.source), dtype=torch.float32).eval()
    with torch.no_grad():
        logits = hf(input_ids=ids.long(), attention_mask=(ids != PAD).long()).logits
        lp = torch.log_softmax(logits[torch.arange(B), position.long()], -1)
        hf_ref = torch.gather(lp, 1, targets.long()).numpy()
    print(f'parity with transformers: max |diff| {np.abs(hf_ref - reference).max():.2e} nats')
    assert np.abs(hf_ref - reference).max() < 1e-3
except ImportError:
    print('transformers not installed: parity check skipped')

started = time.time()
with torch.no_grad(): traced = torch.jit.trace(model, (ids, position, targets), strict=False)
ml = ct.convert(traced, inputs=[ct.TensorType(name='ids', shape=(B, L), dtype=np.int32), ct.TensorType(name='position', shape=(B,), dtype=np.int32),
                                ct.TensorType(name='targets', shape=(B, K), dtype=np.int32)],
                outputs=[ct.TensorType(name='logp')], compute_precision=ct.precision.FLOAT16, minimum_deployment_target=ct.target.macOS13, convert_to='mlprogram')
if args.precision == 'int8':
    ml = cto.linear_quantize_weights(ml, cto.OptimizationConfig(global_config=cto.OpLinearQuantizerConfig(mode='linear_symmetric', dtype='int8', granularity='per_channel')))
print(f'converted in {time.time() - started:.0f} s')

out = args.out; work = out.parent/'work'
shutil.rmtree(work, ignore_errors=True); work.mkdir(parents=True)
package = work/'mlm.mlpackage'; ml.save(str(package))
feed = {'ids': ids.numpy(), 'position': position.numpy(), 'targets': targets.numpy()}
units = [('cpu_and_ne', ct.ComputeUnit.CPU_AND_NE)] + ([('cpu_only', ct.ComputeUnit.CPU_ONLY)] if args.time else [])
timing, parity = {}, {}
for name, unit in units:
    m = ct.models.MLModel(str(package), compute_units=unit)
    got = m.predict(feed)['logp']
    err = float(np.abs(got - reference).max())
    likely = reference > -12  # the targets a check decides on (a fitting candidate)
    near = float(np.abs(got - reference)[likely].max()) if likely.any() else 0.0
    parity[name] = {'max_abs_diff_nats': round(err, 4), 'max_abs_diff_above_-12_nats': round(near, 4)}
    print(f'{name}: max |diff| vs fp32 {err:.3f} nats over all targets, {near:.3f} over targets above -12 nats ({int(likely.sum())})')
    if args.time:
        for _ in range(5): m.predict(feed)
        ms = sorted((lambda s: (m.predict(feed), (time.perf_counter() - s) * 1000)[1])(time.perf_counter()) for _ in range(40))
        timing[name] = {'p50_ms': round(ms[20], 2), 'p95_ms': round(ms[38], 2)}
        print(f'  {name}: p50 {ms[20]:.1f} ms, p95 {ms[38]:.1f} ms per batch of {B}')

shutil.rmtree(out, ignore_errors=True); out.mkdir(parents=True)
# Xcode's Core ML compiler (as for GECToR) when it is installed, even if xcode-select names the Command Line Tools; else the
# compiler in the Core ML framework itself.
import os
developer_dirs = [None] + ([{**os.environ, 'DEVELOPER_DIR': '/Applications/Xcode.app/Contents/Developer'}] if pathlib.Path('/Applications/Xcode.app').is_dir() else [])
env = next((e for e in developer_dirs if subprocess.run(['xcrun', '--find', 'coremlcompiler'], capture_output=True, env=e).returncode == 0), False)
if env is not False:
    subprocess.run(['xcrun', 'coremlcompiler', 'compile', str(package), str(work)], check=True, capture_output=True, env=env)
    compiled = work/'mlm.mlmodelc'
else:
    compiled = pathlib.Path(ct.utils.compile_model(str(package), str(work/'mlm.mlmodelc')))
shutil.move(str(compiled), out/'mlm.mlmodelc')
for f in ['vocab.json', 'merges.txt']: shutil.copy2(args.source/f, out/f)
files = sorted(p for p in out.rglob('*') if p.is_file())
manifest = {'name': 'distilroberta-base slip checker', 'source': REPO, 'source_revision': REVISION, 'license': 'Apache-2.0',
            'format': f'Core ML mlprogram, static shapes: ids int32 [{B},{L}] padded with {PAD}, position int32 [{B}], targets int32 [{B},{K}] -> logp [{B},{K}]',
            'batch': B, 'length': L, 'targets': K, 'pad': PAD, 'mask': 50264,
            'quantization': 'int8 weight-only, linear_symmetric per channel; fp16 compute' if args.precision == 'int8' else 'none, compute precision float16',
            'conversion': {'script': 'scripts/convert-slips.py', 'coremltools': ct.__version__, 'torch': torch.__version__, 'numpy': np.__version__, 'deployment_target': 'macOS 13', 'host': platform.platform()},
            'timing': timing, 'parity_vs_fp32_torch': parity, 'files': {str(p.relative_to(out)): digest(p) for p in files}}
(out/'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
shutil.rmtree(work)
entries = []
for p in sorted(p for p in out.rglob('*') if p.is_file()):
    rel = 'slips/' + str(p.relative_to(out))
    entries.append({'path': rel, 'url': 'https://github.com/jn-aman/parzr/releases/download/models-slips-1/' + rel.replace('/', '.'), 'bytes': p.stat().st_size, 'sha256': digest(p)})
print(json.dumps(entries, indent=1))
print(f'total {sum(e["bytes"] for e in entries) / 1e6:.1f} MB in {out}')
