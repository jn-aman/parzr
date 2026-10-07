#!/usr/bin/env python3
"""Score Parzr (rules, gec, deep) and LanguageTool on public GEC benchmarks.

Datasets (evaluation only; downloaded into the git-ignored dist/gec-data, never committed):
  conll14      CoNLL-2014 shared task test set, official M2 with both annotators (1,312 sentences)
  jfleg-dev    JFLEG dev (754 sentences, 4 references)
  jfleg-test   JFLEG test (747 sentences, 4 references)
  typo         GitHub Typo Corpus v1.0.0, English prose sentence pairs (fixed random sample, seed 0)
  typo-real    the subset of those pairs whose typo is a real word (both tokens in /usr/share/dict/words)

Systems: parzr-rules, parzr-gec, parzr-deep (one long-lived parzr-engine process each, one JSON line per
item) and languagetool (a local LanguageTool server; every match's first suggestion is applied, skipping
overlaps). On CoNLL-2014 LanguageTool is also run with en-GB to measure the US-spelling artifact.

Tokenization: CoNLL and JFLEG are distributed tokenized ("does n't", "word ,"). Engines get a detokenized
sentence (clitics, punctuation and quotes re-attached, `` and '' turned into "). Outputs are retokenized
back into the source's scheme: every whitespace chunk of the output that also occurs in the detokenized
source reuses the source's own tokens for that chunk (so unchanged text round-trips exactly), and any new or
changed chunk is split with a small PTB-style regex tokenizer that keeps hyphenated words whole, as both
corpora do. Curly quotes and apostrophes are folded to ASCII in every output before scoring.

Scores: ERRANT P/R/F0.5 (span-based correction; references re-annotated with ERRANT from each annotator's
corrected sentence, best reference per sentence as errant_compare does) plus per-ERRANT-type TP/FP/FN;
the official NUS M2 scorer on CoNLL (a Python 3 port lives in dist/gec-tools/m2scorer-py3); GLEU (jfleg's
eval/gleu.py) and ERRANT against each single JFLEG reference; exact and local fix rates on the typo corpus.

usage:
  dist/gec-venv/bin/python scripts/run-public-gec-benchmark.py prepare
  dist/gec-venv/bin/python scripts/run-public-gec-benchmark.py run   [--systems ...] [--datasets ...]
  dist/gec-venv/bin/python scripts/run-public-gec-benchmark.py score
  dist/gec-venv/bin/python scripts/run-public-gec-benchmark.py all
"""
import argparse, collections, concurrent.futures as cf, csv, difflib, gzip, hashlib, json, math, pathlib
import random, re, subprocess, sys, threading, time, unicodedata, urllib.parse, urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / 'dist/gec-data'
RAW = DATA / 'raw'
PROC = DATA / 'processed'
OUT = ROOT / 'dist/qa/public-gec'
M2SCORER = ROOT / 'dist/gec-tools/m2scorer-py3/scripts/m2scorer.py'
DEFAULT_ENGINE = '/Applications/Parzr.app/Contents/MacOS/parzr-engine'
LT_URL = 'http://127.0.0.1:8010/v2/check'
CONLL_M2 = RAW / 'conll/conll14st-test-data/noalt/official-2014.combined.m2'
JFLEG = RAW / 'jfleg'
TYPO_GZ = RAW / 'github-typo-corpus.v1.0.0.jsonl.gz'
DICT = pathlib.Path('/usr/share/dict/words')

PARZR_LAYERS = {'parzr-rules': {}, 'parzr-gec': {'gec': True}, 'parzr-deep': {'gec': True, 'deep': True}}
LT_SYSTEMS = {'languagetool': 'en-US', 'languagetool-en-GB': 'en-GB'}
SYSTEMS = list(PARZR_LAYERS) + list(LT_SYSTEMS)
DATASETS = ['conll14', 'jfleg-dev', 'jfleg-test', 'typo', 'typo-real']
GEC_DATASETS = ['conll14', 'jfleg-dev', 'jfleg-test']
TYPO_SAMPLE, TYPO_REAL_SAMPLE = 3000, 2000


# ---------------------------------------------------------------- tokenization

CLITICS = {"'s", "n't", "'re", "'ve", "'ll", "'d", "'m"}
LEFT_ATTACH = {'.', ',', ';', ':', '?', '!', '%', ')', ']', '}', '...', "'", "''"}
RIGHT_ATTACH = {'(', '[', '{', '$', '``'}
QUOTE_FOLD = str.maketrans({'’': "'", '‘': "'", '“': '"', '”': '"', ' ': ' '})


def fold(s):
    return unicodedata.normalize('NFC', s).translate(QUOTE_FOLD)


def detok(tokens):
    """Tokens -> (sentence, {chunk: [tokens]}). Only whitespace changes, so each chunk maps to source tokens."""
    chunks, open_dq = [], False
    prev_right = True
    for t in tokens:
        disp = '"' if t in ('``', "''") else t
        if t == '"':
            left, right = open_dq, not open_dq
            open_dq = not open_dq
        else:
            left = t in LEFT_ATTACH or t.lower() in CLITICS
            right = t in RIGHT_ATTACH
        if chunks and (left or prev_right):
            chunks[-1][0].append(disp); chunks[-1][1].append(t)
        else:
            chunks.append(([disp], [t]))
        prev_right = right
    cmap = {}
    for disp, toks in chunks:
        cmap.setdefault(''.join(disp), toks)
    return ' '.join(''.join(d) for d, _ in chunks), cmap


ABBREV = re.compile(r"^(?:[A-Za-z]\.){2,}$|^(?:etc|e\.g|i\.e|Mr|Mrs|Ms|Dr|vs|St|Jr|Sr|No)\.$", re.I)
CLITIC_RE = re.compile(r"(?i)^(.+?)(n't|'s|'re|'ve|'ll|'d|'m)$")


def regex_tokenize(chunk):
    """PTB-ish split of one whitespace chunk; hyphenated words and abbreviations stay whole."""
    lead, trail = [], []
    while chunk and chunk[0] in '"\'([{`':
        lead.append(chunk[0]); chunk = chunk[1:]
    while chunk:
        if chunk.endswith('...') and len(chunk) > 3:
            trail.insert(0, '...'); chunk = chunk[:-3]; continue
        c = chunk[-1]
        if c in ',;:?!)]}"%' or (c == "'" and not CLITIC_RE.match(chunk)):
            trail.insert(0, c); chunk = chunk[:-1]; continue
        if c == '.' and len(chunk) > 1 and not ABBREV.match(chunk):
            trail.insert(0, '.'); chunk = chunk[:-1]; continue
        break
    mid = []
    if chunk:
        m = CLITIC_RE.match(chunk)
        if m:
            mid = [m.group(1), m.group(2)]
        else:
            mid = [chunk]
    return lead + mid + trail


def retok(text, cmap):
    toks, fallback = [], 0
    for chunk in fold(text).split():
        if chunk in cmap:
            toks.extend(cmap[chunk])
        else:
            toks.extend(regex_tokenize(chunk)); fallback += 1
    return toks, fallback


# ---------------------------------------------------------------- M2 helpers

def read_m2(path):
    blocks = [b for b in path.read_text(encoding='utf-8').strip().split('\n\n')]
    out = []
    for b in blocks:
        lines = b.split('\n')
        src = lines[0][2:].split(' ') if lines[0][2:] else []
        edits = []
        for l in lines[1:]:
            f = l[2:].split('|||')
            s, e = map(int, f[0].split())
            edits.append((s, e, f[1], f[2], int(f[-1])))
        out.append((src, edits))
    return out


def apply_m2(src, edits):
    toks, off = list(src), 0
    for s, e, cat, cor, _ in sorted(edits, key=lambda x: (x[0], x[1])):
        if cat == 'noop' or s < 0:
            continue
        rep = cor.split() if cor and cor != '-NONE-' else []
        toks[s + off:e + off] = rep
        off += len(rep) - (e - s)
    return toks


_ANN = None


def annotator():
    global _ANN
    if _ANN is None:
        import errant
        _ANN = errant.load('en')
    return _ANN


def errant_block(orig_toks, cors):
    """ERRANT M2 block for orig tokens and a list of corrected token lists (one per annotator)."""
    ann = annotator()
    orig = ann.parse(' '.join(orig_toks), tokenise=False)
    lines = ['S ' + ' '.join(orig_toks)]
    for coder, cor_toks in enumerate(cors):
        if cor_toks == orig_toks:
            lines.append(f'A -1 -1|||noop|||-NONE-|||REQUIRED|||-NONE-|||{coder}')
            continue
        cor = ann.parse(' '.join(cor_toks), tokenise=False) if cor_toks else ann.parse('', tokenise=False)
        for e in ann.annotate(orig, cor):
            lines.append(f'A {e.o_start} {e.o_end}|||{e.type}|||{e.c_str}|||REQUIRED|||-NONE-|||{coder}')
    return '\n'.join(lines)


def write_m2(path, blocks):
    path.write_text('\n\n'.join(blocks) + '\n', encoding='utf-8')


# ---------------------------------------------------------------- prepare

def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def prepare_conll():
    data = read_m2(CONLL_M2)
    items, blocks, coders = [], [], set()
    for src, edits in data:
        coders |= {c for *_, c in edits}
    ncod = max(coders) + 1
    for i, (src, edits) in enumerate(data):
        text, _ = detok(src)
        cors = [apply_m2(src, [e for e in edits if e[4] == c]) for c in range(ncod)]
        items.append({'id': f'conll14-{i}', 'tokens': src, 'input': text,
                      'gold_edit_count': [sum(1 for e in edits if e[4] == c and e[2] != 'noop') for c in range(ncod)]})
        blocks.append(errant_block(src, cors))
        if (i + 1) % 300 == 0:
            print(f'  conll14 ERRANT re-annotation {i + 1}/{len(data)}', file=sys.stderr)
    return items, {'ref': blocks}


def prepare_jfleg(split):
    d = JFLEG / split
    src = d.joinpath(f'{split}.src').read_text(encoding='utf-8').split('\n')[:-1]
    refs = [d.joinpath(f'{split}.ref{k}').read_text(encoding='utf-8').split('\n')[:-1] for k in range(4)]
    assert all(len(r) == len(src) for r in refs), split
    items, blocks, single = [], [], [[] for _ in range(4)]
    ann = annotator()
    for i, s in enumerate(src):
        toks = s.split()
        text, _ = detok(toks)
        rtoks = [refs[k][i].split() for k in range(4)]
        items.append({'id': f'jfleg-{split}-{i}', 'tokens': toks, 'input': text})
        blk = errant_block(toks, rtoks)
        blocks.append(blk)
        head, *alines = blk.split('\n')
        for k in range(4):
            mine = [re.sub(r'\|\|\|\d+$', '|||0', l) for l in alines if l.endswith(f'|||{k}')]
            single[k].append('\n'.join([head] + mine))
        if (i + 1) % 300 == 0:
            print(f'  jfleg-{split} ERRANT re-annotation {i + 1}/{len(src)}', file=sys.stderr)
    return items, {'ref': blocks, **{f'ref{k}': single[k] for k in range(4)}}


WORD_RE = re.compile(r"^[\"'(]?[A-Za-z][A-Za-z'’-]*[.,;:!?)\"']*$")


def is_prose(s):
    if not s or len(s) > 300 or '\n' in s or '\t' in s:
        return False
    if re.search(r'[{}<>\[\]|=_*#\\`~@$^]|://|www\.|\.(?:py|js|md|rb|go|html|json|yml|txt|exe)\b', s):
        return False
    words = s.split()
    if len(words) < 6 or not s[0].isupper() or s[-1] not in '.!?':
        return False
    return sum(1 for w in words if WORD_RE.match(w)) / len(words) >= 0.9


def typo_span(src, tgt):
    p = 0
    while p < min(len(src), len(tgt)) and src[p] == tgt[p]:
        p += 1
    q = 0
    while q < min(len(src), len(tgt)) - p and src[-1 - q] == tgt[-1 - q]:
        q += 1
    a, b = p, len(src) - q
    while a > 0 and src[a - 1].isalnum():
        a -= 1
    while b < len(src) and src[b].isalnum():
        b += 1
    tb = b + (len(tgt) - len(src))
    return a, b, tgt[a:tb]


def lev(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


DIALECT = [('our', 'or'), ('ise', 'ize'), ('isation', 'ization'), ('ising', 'izing'), ('ised', 'ized'), ('yse', 'yze'),
           ('tre', 'ter'), ('lled', 'led'), ('lling', 'ling'), ('ogue', 'og'), ('ence', 'ense'), ('mme', 'm')]


def dialect_only(a, b):
    a, b = a.lower(), b.lower()
    return a != b and any(a.replace(x, y) == b or b.replace(x, y) == a for x, y in DIALECT)


def prepare_typo():
    dropped = collections.Counter()
    words = {w.strip().lower() for w in DICT.read_text().split()}
    seen, pairs = set(), []
    with gzip.open(TYPO_GZ, 'rt', encoding='utf-8') as f:
        for line in f:
            commit = json.loads(line)
            for e in commit['edits']:
                if e['src']['lang'] != 'eng' or e['tgt']['lang'] != 'eng' or not e.get('is_typo'):
                    continue
                s, t = e['src']['text'].strip(), e['tgt']['text'].strip()
                if s == t or s in seen or not is_prose(s) or not is_prose(t):
                    continue
                sw, tw = s.split(), t.split()
                ops = [o for o in difflib.SequenceMatcher(None, sw, tw, autojunk=False).get_opcodes() if o[0] != 'equal']
                if len(ops) != 1 or max(ops[0][2] - ops[0][1], ops[0][4] - ops[0][3]) > 3:
                    continue
                tag, i1, i2, j1, j2 = ops[0]
                a, b, rep = typo_span(s, t)
                if lev(s[a:b], rep) > 3:
                    dropped['edit_distance>3'] += 1; continue
                if s[a:b].lower() == rep.lower():
                    dropped['case_only'] += 1; continue  # mostly brand casing (Github -> GitHub), not grammar
                if dialect_only(s[a:b], rep):
                    dropped['dialect_respelling'] += 1; continue
                seen.add(s)
                item = {'id': f'typo-{len(pairs)}', 'input': s, 'reference': t, 'span': [a, b], 'span_fix': rep,
                        'prob_typo': round(e.get('prob_typo') or 0, 4), 'repo': commit['repo'], 'commit': commit['commit']}
                if tag == 'replace' and i2 - i1 == 1 and j2 - j1 == 1:
                    sw0, tw0 = sw[i1].strip('.,;:!?"\'()'), tw[j1].strip('.,;:!?"\'()')
                    item['src_word'], item['tgt_word'] = sw0, tw0
                    item['real_word'] = (sw0.isalpha() and tw0.isalpha() and sw0.lower() != tw0.lower()
                                         and sw0.lower() in words and tw0.lower() in words and lev(sw0.lower(), tw0.lower()) <= 2)
                else:
                    item['real_word'] = False
                pairs.append(item)
    real = [p for p in pairs if p['real_word']]
    rng = random.Random(0)
    sample = sorted(rng.sample(range(len(pairs)), min(TYPO_SAMPLE, len(pairs))))
    rng = random.Random(0)
    rsample = sorted(rng.sample(range(len(real)), min(TYPO_REAL_SAMPLE, len(real))))
    print(f'  typo filter drops: {dict(dropped)}', file=sys.stderr)
    return pairs, real, [pairs[i] for i in sample], [real[i] for i in rsample]


def cmd_prepare(a):
    PROC.mkdir(parents=True, exist_ok=True)
    stats = {}
    items, m2 = prepare_conll()
    dump_jsonl(PROC / 'conll14.jsonl', items)
    write_m2(PROC / 'conll14.ref.errant.m2', m2['ref'])
    stats['conll14'] = len(items)
    for split in ('dev', 'test'):
        items, m2 = prepare_jfleg(split)
        dump_jsonl(PROC / f'jfleg-{split}.jsonl', items)
        for k, blocks in m2.items():
            write_m2(PROC / f'jfleg-{split}.{k}.errant.m2', blocks)
        stats[f'jfleg-{split}'] = len(items)
    pairs, real, sample, rsample = prepare_typo()
    dump_jsonl(PROC / 'typo-all.jsonl', pairs)
    dump_jsonl(PROC / 'typo-real-all.jsonl', real)
    dump_jsonl(PROC / 'typo.jsonl', sample)
    dump_jsonl(PROC / 'typo-real.jsonl', rsample)
    stats.update({'typo_all': len(pairs), 'typo_real_all': len(real), 'typo': len(sample), 'typo-real': len(rsample)})
    (PROC / 'stats.json').write_text(json.dumps(stats, indent=2) + '\n')
    print(json.dumps(stats))


def dump_jsonl(path, rows):
    with open(path, 'w', encoding='utf-8') as f:
        f.writelines(json.dumps(r, ensure_ascii=False) + '\n' for r in rows)


def load_jsonl(path):
    return [json.loads(l) for l in path.read_text(encoding='utf-8').splitlines() if l.strip()]


# ---------------------------------------------------------------- systems

class Parzr:
    def __init__(self, engine, extra):
        self.extra = extra
        self.proc = subprocess.Popen([engine], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
                                     encoding='utf-8', bufsize=1)

    def correct(self, text):
        self.proc.stdin.write(json.dumps({'text': text, **self.extra}, ensure_ascii=False) + '\n')
        self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        if not line:
            raise RuntimeError('parzr-engine exited')
        r = json.loads(line)
        return r.get('text', text), [{'start': e['start_utf16'], 'end': e['end_utf16'], 'original': e.get('original'),
                                      'replacement': e.get('replacement'), 'rule': e.get('rule_id')} for e in r.get('edits', [])]

    def close(self):
        self.proc.stdin.close(); self.proc.wait(timeout=60)


def utf16_index(text):
    idx, pos = [], 0
    for i, ch in enumerate(text):
        idx.append(pos); pos += 2 if ord(ch) > 0xFFFF else 1
    idx.append(pos)
    return {u: i for i, u in enumerate(idx)}


class LanguageTool:
    def __init__(self, lang):
        self.lang = lang

    def correct(self, text):
        body = urllib.parse.urlencode({'language': self.lang, 'text': text}).encode()
        for attempt in range(5):
            try:
                with urllib.request.urlopen(urllib.request.Request(LT_URL, data=body), timeout=120) as r:
                    res = json.load(r)
                break
            except Exception:
                if attempt == 4:
                    raise
                time.sleep(2 * (attempt + 1))
        u2i = utf16_index(text)
        edits, last = [], -1
        for m in sorted(res['matches'], key=lambda m: (m['offset'], m['length'])):
            if not m.get('replacements'):
                continue
            s, e = u2i.get(m['offset']), u2i.get(m['offset'] + m['length'])
            if s is None or e is None or s < last:
                continue
            edits.append({'start': s, 'end': e, 'original': text[s:e], 'replacement': m['replacements'][0]['value'],
                          'rule': m['rule']['id']})
            last = e
        out = text
        for ed in reversed(edits):
            out = out[:ed['start']] + ed['replacement'] + out[ed['end']:]
        return out, edits

    def close(self):
        pass


def lt_version():
    try:
        body = urllib.parse.urlencode({'language': 'en-US', 'text': 'Test.'}).encode()
        with urllib.request.urlopen(urllib.request.Request(LT_URL, data=body), timeout=30) as r:
            return json.load(r)['software']['version']
    except Exception as e:
        return f'unavailable ({e})'


def parzr_version(engine):
    p = Parzr(engine, {})
    p.proc.stdin.write('{"text":"Test."}\n'); p.proc.stdin.flush()
    v = json.loads(p.proc.stdout.readline()).get('version')
    p.close()
    return v


def out_path(dataset, system):
    return OUT / 'outputs' / f'{dataset}.{system}.jsonl'


def run_system(system, datasets, engine, deep_ids):
    """Correct every item of every dataset with one system; resumable (skips ids already written)."""
    if system in PARZR_LAYERS:
        make = lambda: Parzr(engine, PARZR_LAYERS[system])
    else:
        make = lambda: LanguageTool(LT_SYSTEMS[system])
    log = {}
    for ds in datasets:
        if system == 'languagetool-en-GB' and ds != 'conll14':
            continue
        items = load_jsonl(PROC / f'{ds}.jsonl')
        if system == 'parzr-deep' and deep_ids.get(ds) is not None:
            keep = set(deep_ids[ds]); items = [it for it in items if it['id'] in keep]
        path = out_path(ds, system)
        done = {r['id'] for r in load_jsonl(path)} if path.exists() else set()
        todo = [it for it in items if it['id'] not in done]
        if not todo:
            continue
        t0, n = time.time(), 0
        if system in LT_SYSTEMS:
            lt = make()
            with cf.ThreadPoolExecutor(6) as pool, open(path, 'a', encoding='utf-8') as f:
                for it, (out, edits) in zip(todo, pool.map(lambda it: lt.correct(it['input']), todo)):
                    f.write(json.dumps({'id': it['id'], 'input': it['input'], 'output': out, 'edits': edits}, ensure_ascii=False) + '\n')
                    n += 1
        else:
            eng = make()
            with open(path, 'a', encoding='utf-8') as f:
                for it in todo:
                    t1 = time.time()
                    out, edits = eng.correct(it['input'])
                    f.write(json.dumps({'id': it['id'], 'input': it['input'], 'output': out, 'edits': edits,
                                        'ms': round((time.time() - t1) * 1000, 1)}, ensure_ascii=False) + '\n')
                    f.flush(); n += 1
                    if n % 250 == 0:
                        print(f'  {system} {ds}: {n}/{len(todo)}', file=sys.stderr, flush=True)
            eng.close()
        log[ds] = round(time.time() - t0, 1)
        print(f'{system} {ds}: {n} items in {log[ds]}s', file=sys.stderr, flush=True)
    return log


def plan_deep(a, datasets):
    """Time deep mode on 50 CoNLL sentences; sample (seed 0) if the full run would exceed the budget."""
    plan_file = OUT / 'deep-plan.json'
    if plan_file.exists():
        return json.loads(plan_file.read_text())
    items = load_jsonl(PROC / 'conll14.jsonl')
    probe = random.Random(0).sample(items, 50)
    eng = Parzr(a.engine, PARZR_LAYERS['parzr-deep'])
    t0 = time.time()
    for it in probe:
        eng.correct(it['input'])
    per = (time.time() - t0) / 50
    eng.close()
    total = sum(len(load_jsonl(PROC / f'{ds}.jsonl')) for ds in datasets)
    projected = per * total / 3600
    plan = {'seconds_per_sentence': round(per, 3), 'items': total, 'projected_hours': round(projected, 2),
            'budget_hours': a.deep_budget_hours, 'sampled': projected > a.deep_budget_hours, 'ids': {}}
    if plan['sampled']:
        frac = a.deep_budget_hours / projected
        for ds in datasets:
            its = load_jsonl(PROC / f'{ds}.jsonl')
            k = max(50, int(len(its) * frac))
            plan['ids'][ds] = sorted(it['id'] for it in random.Random(0).sample(its, min(k, len(its))))
    OUT.mkdir(parents=True, exist_ok=True)
    plan_file.write_text(json.dumps(plan, indent=1) + '\n')
    print(f"deep: {plan['seconds_per_sentence']}s/sentence, projected {plan['projected_hours']}h for {total} items"
          f"{' -> sampling' if plan['sampled'] else ''}", file=sys.stderr)
    return plan


def cmd_run(a):
    (OUT / 'outputs').mkdir(parents=True, exist_ok=True)
    systems, datasets = a.systems.split(','), a.datasets.split(',')
    deep_ids = plan_deep(a, datasets)['ids'] if 'parzr-deep' in systems else {}
    timings = {}
    with cf.ThreadPoolExecutor(len(systems)) as pool:
        futs = {pool.submit(run_system, s, datasets, a.engine, deep_ids): s for s in systems}
        for fut in cf.as_completed(futs):
            timings[futs[fut]] = fut.result()
    tf = OUT / 'run-timings.json'
    prev = json.loads(tf.read_text()) if tf.exists() else {}
    for s, d in timings.items():
        prev.setdefault(s, {}).update(d)
    tf.write_text(json.dumps(prev, indent=2) + '\n')


# ---------------------------------------------------------------- scoring

class Args:  # what errant.commands.compare_m2 expects
    dt = ds = cse = single = multi = verbose = False
    filt = []
    beta = 0.5
    cat = None


def m2_blocks(path):
    return path.read_text(encoding='utf-8').strip().split('\n\n')


def errant_compare(hyp_blocks, ref_blocks):
    """errant_compare's algorithm, returning totals, per-type counts and the per-sentence chosen references."""
    from errant.commands import compare_m2 as cm
    args = Args()
    best = collections.Counter({'tp': 0, 'fp': 0, 'fn': 0})
    cats, chosen = {}, []
    for hb, rb in zip(hyp_blocks, ref_blocks):
        hyp = cm.process_edits(cm.simplify_edits(hb), args)
        ref = cm.process_edits(cm.simplify_edits(rb), args)
        bt, bfp, bfn, bf, bref, bcat = 0, 0, 0, -1, 0, {}
        for hid in hyp:
            for rid in ref:
                tp, fp, fn, cd = cm.compareEdits(hyp[hid], ref[rid])
                _, _, f = cm.computeFScore(tp + best['tp'], fp + best['fp'], fn + best['fn'], args.beta)
                if (f > bf) or (f == bf and tp > bt) or (f == bf and tp == bt and fp < bfp) or \
                        (f == bf and tp == bt and fp == bfp and fn < bfn):
                    bt, bfp, bfn, bf, bref, bcat = tp, fp, fn, f, rid, cd
        best += collections.Counter({'tp': bt, 'fp': bfp, 'fn': bfn})
        cats = cm.merge_dict(cats, bcat)
        chosen.append(bref)
    p, r, f = cm.computeFScore(best['tp'], best['fp'], best['fn'], 0.5)
    return {'tp': best['tp'], 'fp': best['fp'], 'fn': best['fn'], 'p': p, 'r': r, 'f05': f}, cats, chosen


def edits_by_coder(block):
    out = collections.defaultdict(list)
    for l in block.split('\n')[1:]:
        f = l[2:].split('|||')
        s, e = map(int, f[0].split())
        if f[1] == 'noop':
            out[int(f[-1])]; continue
        out[int(f[-1])].append((s, e, f[1], f[2]))
    return out


def hyp_m2(ds, system, items, rows):
    """Retokenize a system's outputs and annotate them against the source with ERRANT (cached)."""
    path = OUT / 'm2' / f'{ds}.{system}.m2'
    tok_path = OUT / 'outputs' / f'{ds}.{system}.tok'
    byid = {r['id']: r for r in rows}
    keep = [it for it in items if it['id'] in byid]
    toks_all, fallback = [], 0
    for it in keep:
        _, cmap = detok(it['tokens'])
        toks, fb = retok(byid[it['id']]['output'], cmap)
        toks_all.append(toks); fallback += fb
    tok_path.write_text('\n'.join(' '.join(t) for t in toks_all) + '\n', encoding='utf-8')
    if path.exists() and path.stat().st_mtime > out_path(ds, system).stat().st_mtime:
        return m2_blocks(path), keep, toks_all, fallback
    path.parent.mkdir(parents=True, exist_ok=True)
    blocks = [errant_block(it['tokens'], [t]) for it, t in zip(keep, toks_all)]
    write_m2(path, blocks)
    return blocks, keep, toks_all, fallback


def run_m2scorer(hyp_tok_lines, gold_m2_path, tag):
    tmp = OUT / 'm2' / f'{tag}.m2scorer-input.txt'
    tmp.write_text('\n'.join(hyp_tok_lines) + '\n', encoding='utf-8')
    try:
        r = subprocess.run([sys.executable, str(M2SCORER), str(tmp), str(gold_m2_path)], capture_output=True,
                           text=True, timeout=3600)
        vals = dict(re.findall(r'(Precision|Recall|F_0.5)\s*:\s*([\d.]+)', r.stdout))
        return {'p': float(vals['Precision']), 'r': float(vals['Recall']), 'f05': float(vals['F_0.5'])}
    except Exception as e:
        return {'error': str(e)[:200]}


def run_gleu(split, hyp_tok_lines, tag):
    d = JFLEG / split
    tmp = OUT / 'm2' / f'{tag}.gleu-input.txt'
    tmp.write_text('\n'.join(hyp_tok_lines) + '\n', encoding='utf-8')
    r = subprocess.run([sys.executable, '-I', str(JFLEG / 'eval/gleu.py'), '-r', *[str(d / f'{split}.ref{k}') for k in range(4)],
                        '-s', str(d / f'{split}.src'), '--hyp', str(tmp)], capture_output=True, text=True, timeout=1800)
    m = re.search(r"\[\['([\d.]+)', '([\d.]+)', '\(([\d.]+),([\d.]+)\)'\]\]", r.stdout)
    return {'gleu': float(m.group(1)), 'std': float(m.group(2)), 'ci95': [float(m.group(3)), float(m.group(4))]} if m else {'error': r.stderr[-300:]}


def wtoks(s):
    return re.findall(r"\w+(?:['’]\w+)*|[^\w\s]", fold(s))


def typo_verdict(item, out):
    src, tgt = item['input'], item['reference']
    a, b = item['span']
    exact = ' '.join(fold(out).split()) == ' '.join(fold(tgt).split())
    st, ot, tt = wtoks(src), wtoks(out), wtoks(tgt)
    # token indices of the typo region in src
    pos, spans = 0, []
    s2 = fold(src)
    for t in st:
        i = s2.find(t, pos); spans.append((i, i + len(t))); pos = i + len(t)
    region = {k for k, (i, j) in enumerate(spans) if i < b and j > a} or {k for k, (i, j) in enumerate(spans) if i <= a <= j}
    lo, hi = min(region), max(region) + 1
    local, collateral, cand = False, False, []
    i0 = 0
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, st, ot, autojunk=False).get_opcodes():
        if tag == 'equal':
            continue
        near = (i1 < hi and i2 > lo) or (i1 == i2 and lo <= i1 <= hi)
        if near:
            local = True; cand += st[i0:i1] + ot[j1:j2]; i0 = i2
        else:
            collateral = True
    cand += st[i0:]
    fixed_local = cand == tt
    return {'exact': exact, 'fixed': fixed_local, 'touched': local, 'collateral': collateral,
            'wrong': local and not fixed_local}


def new_double_spaces(rows):
    pat = re.compile(r'\S  +\S')
    return sum(1 for r in rows if pat.search(r['output']) and not pat.search(r['input']))


def score_typo(ds, system):
    items = {it['id']: it for it in load_jsonl(PROC / f'{ds}.jsonl')}
    rows = load_jsonl(out_path(ds, system))
    c, examples = collections.Counter(), []
    for r in rows:
        it = items[r['id']]
        v = typo_verdict(it, r['output'])
        c.update({k: int(x) for k, x in v.items()}); c['n'] += 1
        examples.append({'id': r['id'], 'input': it['input'], 'reference': it['reference'], 'output': r['output'],
                         **v, 'src_word': it.get('src_word'), 'tgt_word': it.get('tgt_word'),
                         'rules': [e.get('rule') for e in r.get('edits', [])]})
    n = max(1, c['n'])
    res = {'n': c['n'], 'exact_fix_rate': round(c['exact'] / n, 4), 'fix_rate': round(c['fixed'] / n, 4),
           'touched_rate': round(c['touched'] / n, 4), 'wrong_fix_rate': round(c['wrong'] / n, 4),
           'collateral_change_rate': round(c['collateral'] / n, 4)}
    dump_jsonl(OUT / 'outputs' / f'{ds}.{system}.verdicts.jsonl', examples)
    return res, examples


def cmd_score(a):
    systems = [s for s in a.systems.split(',')]
    (OUT / 'm2').mkdir(parents=True, exist_ok=True)
    plan = json.loads((OUT / 'deep-plan.json').read_text()) if (OUT / 'deep-plan.json').exists() else {}
    summary = {'parzr_engine': parzr_version(a.engine), 'languagetool_version': lt_version(),
               'deep_plan': {k: v for k, v in plan.items() if k != 'ids'}, 'datasets': {}, 'notes': NOTES}
    if plan.get('sampled'):
        summary['deep_plan']['n'] = {k: len(v) for k, v in plan['ids'].items()}
    timings = OUT / 'run-timings.json'
    summary['timings_seconds'] = json.loads(timings.read_text()) if timings.exists() else {}
    type_rows, edit_level = [], {}
    m2jobs = {}
    pool = cf.ThreadPoolExecutor(6)
    for ds in GEC_DATASETS:
        items = load_jsonl(PROC / f'{ds}.jsonl')
        ref_blocks = m2_blocks(PROC / f'{ds}.ref.errant.m2')
        byid = {it['id']: k for k, it in enumerate(items)}
        dsum = {'n': len(items), 'systems': {}}
        # round-trip check: detok -> retok must give the source tokens back
        bad = sum(1 for it in items if retok(it['input'], detok(it['tokens'])[1])[0] != it['tokens'])
        dsum['tokenization_roundtrip_failures'] = bad
        if ds == 'conll14':
            gold = read_m2(CONLL_M2)
            dsum['official_gold_edits'] = sum(1 for _, ed in gold for e in ed if e[2] != 'noop')
            dsum['no_error_sentences'] = sum(1 for _, ed in gold if all(e[2] == 'noop' for e in ed))
        dsum['errant_gold_edits'] = sum(len(v) for b in ref_blocks for v in edits_by_coder(b).values())
        dia = set()
        for k, b in enumerate(ref_blocks):
            src = b.split('\n')[0][2:].split(' ')
            for v in edits_by_coder(b).values():
                for s_, e_, _, c_ in v:
                    o = ' '.join(src[s_:e_])
                    if o and c_ and ' ' not in o and dialect_only(o, c_):
                        dia.add((k, s_, e_, c_))
        dsum['gold_british_to_american_respellings'] = len(dia)
        for system in systems:
            if not out_path(ds, system).exists():
                continue
            rows = load_jsonl(out_path(ds, system))
            hb, keep, toks, fallback = hyp_m2(ds, system, items, rows)
            idx = [byid[it['id']] for it in keep]
            refs = [ref_blocks[k] for k in idx]
            tot, cats, chosen = errant_compare(hb, refs)
            changed = sum(1 for it, t in zip(keep, toks) if t != it['tokens'])
            art = collections.Counter()
            for b_, r_, ch in zip(hb, refs, chosen):
                src = b_.split('\n')[0][2:].split(' ')
                ref_set = {(x[0], x[1], x[3]) for x in edits_by_coder(r_).get(ch, [])}
                for s_, e_, t_, c_ in edits_by_coder(b_).get(0, []):
                    if (s_, e_, c_) in ref_set:
                        continue
                    o = ' '.join(src[s_:e_])
                    if o.replace(' ', '') == c_.replace(' ', ''):
                        art['fp_whitespace_only'] += 1
                    elif o.lower() == c_.lower():
                        art['fp_case_only'] += 1
            adj_fp = tot['fp'] - art['fp_whitespace_only'] - art['fp_case_only']
            ap = tot['tp'] / (tot['tp'] + adj_fp) if tot['tp'] + adj_fp else 1.0
            ar = tot['r']
            art['p_excluding_those'] = round(ap, 4)
            art['f05_excluding_those'] = round(1.25 * ap * ar / (0.25 * ap + ar), 4) if ap + ar else 0.0
            s = {'n': len(keep), 'errant': tot, 'sentences_changed': changed, 'retok_fallback_chunks': fallback,
                 'outputs_with_new_double_spaces': new_double_spaces(rows),
                 'fp_artifacts': dict(art),
                 'curly_quotes_in_output': sum(1 for r in rows if re.search('[‘’“”]', r['output']))}
            if ds == 'conll14':
                noerr = [k for k, it in enumerate(keep) if all(c == 0 for c in it['gold_edit_count'])]
                s['changed_no_error_sentences'] = sum(1 for k in noerr if toks[k] != keep[k]['tokens'])
                s['no_error_sentences'] = len(noerr)
                tag = f'{ds}.{system}'
                if len(keep) == len(items):
                    m2jobs[(ds, system, 'm2scorer')] = pool.submit(run_m2scorer, [' '.join(t) for t in toks], CONLL_M2, tag)
            if ds.startswith('jfleg'):
                split = ds.split('-')[1]
                s['errant_single_ref'] = {}
                for k in range(4):
                    rb = m2_blocks(PROC / f'{ds}.ref{k}.errant.m2')
                    s['errant_single_ref'][f'ref{k}'] = errant_compare(hb, [rb[i] for i in idx])[0]
                s['errant_single_ref_mean_f05'] = round(sum(v['f05'] for v in s['errant_single_ref'].values()) / 4, 4)
                if len(keep) == len(items):
                    m2jobs[(ds, system, 'gleu')] = pool.submit(run_gleu, split, [' '.join(t) for t in toks], f'{ds}.{system}')
            for cat, (tp, fp, fn) in sorted(cats.items()):
                type_rows.append({'dataset': ds, 'system': system, 'type': cat, 'tp': tp, 'fp': fp, 'fn': fn})
            # edit-level detail against the chosen reference (for misses) and all references (for "LT got it")
            for it, b, rb, ch in zip(keep, hb, refs, chosen):
                hyp_edits = {(s_, e_, c_) for v in edits_by_coder(b).values() for s_, e_, _, c_ in v}
                edit_level.setdefault((ds, it['id']), {'item': it, 'refs': edits_by_coder(rb), 'hyp': {}, 'chosen': {}})
                edit_level[(ds, it['id'])]['hyp'][system] = hyp_edits
                edit_level[(ds, it['id'])]['chosen'][system] = ch
            dsum['systems'][system] = s
        if ds.startswith('jfleg'):
            split = ds.split('-')[1]
            src_lines = [' '.join(it['tokens']) for it in items]
            m2jobs[(ds, 'source (no change)', 'gleu')] = pool.submit(run_gleu, split, src_lines, f'{ds}.source')
        summary['datasets'][ds] = dsum
    for ds in ('typo', 'typo-real'):
        if not (PROC / f'{ds}.jsonl').exists():
            continue
        dsum = {'n': len(load_jsonl(PROC / f'{ds}.jsonl')), 'systems': {}}
        for system in systems:
            if out_path(ds, system).exists():
                dsum['systems'][system] = score_typo(ds, system)[0]
                dsum['systems'][system]['outputs_with_new_double_spaces'] = new_double_spaces(load_jsonl(out_path(ds, system)))
        summary['datasets'][ds] = dsum
    for (ds, system, kind), fut in m2jobs.items():
        summary['datasets'][ds]['systems'].setdefault(system, {})[kind] = fut.result()
    pool.shutdown()
    stats = PROC / 'stats.json'
    summary['data_stats'] = json.loads(stats.read_text()) if stats.exists() else {}
    analysis = analyse(summary, type_rows, edit_level, systems)
    summary['analysis'] = analysis
    with open(OUT / 'per-type-recall.csv', 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['dataset', 'system', 'errant_type', 'tp', 'fp', 'fn', 'precision', 'recall'])
        pooled = collections.defaultdict(lambda: [0, 0, 0])
        for r in type_rows:
            for key in ((r['dataset'], r['system'], r['type']), ('all-gec', r['system'], r['type'])):
                x = pooled[key]; x[0] += r['tp']; x[1] += r['fp']; x[2] += r['fn']
        for (ds, system, cat), (tp, fp, fn) in sorted(pooled.items()):
            w.writerow([ds, system, cat, tp, fp, fn, round(tp / (tp + fp), 4) if tp + fp else '', round(tp / (tp + fn), 4) if tp + fn else ''])
    (OUT / 'summary.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False) + '\n')
    (OUT / 'summary.md').write_text(render_md(summary))
    print(f'Wrote {OUT}/summary.md')


def analyse(summary, type_rows, edit_level, systems):
    parzr = [s for s in ('parzr-deep', 'parzr-gec', 'parzr-rules') if s in systems]
    lt = 'languagetool'
    pooled = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0, 0]))
    for r in type_rows:
        if r['dataset'] in ('conll14', 'jfleg-test', 'jfleg-dev'):
            x = pooled[r['system']][r['type']]; x[0] += r['tp']; x[1] += r['fp']; x[2] += r['fn']
    out = {}
    for p in parzr:
        rows = []
        for cat, (tp, fp, fn) in pooled[p].items():
            ltc = pooled[lt].get(cat, [0, 0, 0])
            rows.append({'type': cat, 'parzr_misses': fn, 'parzr_tp': tp, 'parzr_recall': round(tp / (tp + fn), 3) if tp + fn else None,
                         'lt_tp': ltc[0], 'lt_fn': ltc[2], 'lt_recall': round(ltc[0] / (ltc[0] + ltc[2]), 3) if ltc[0] + ltc[2] else None})
        rows.sort(key=lambda r: -r['parzr_misses'])
        out[f'top_missed_types.{p}'] = rows[:15]
        fps = sorted(((cat, v[1]) for cat, v in pooled[p].items()), key=lambda x: -x[1])[:12]
        out[f'top_false_positive_types.{p}'] = [{'type': c, 'fp': n, 'lt_fp': pooled[lt].get(c, [0, 0, 0])[1]} for c, n in fps]
    fps = sorted(((cat, v[1]) for cat, v in pooled[lt].items()), key=lambda x: -x[1])[:12]
    out['top_false_positive_types.languagetool'] = [{'type': c, 'fp': n} for c, n in fps]
    # gold edits LanguageTool corrects exactly and no Parzr layer does
    examples = []
    for (ds, iid), d in edit_level.items():
        if lt not in d['hyp'] or not all(p in d['hyp'] for p in parzr):
            continue
        golds = {(s, e, c): t for v in d['refs'].values() for s, e, t, c in v}
        for (s, e, c), t in golds.items():
            if (s, e, c) in d['hyp'][lt] and not any((s, e, c) in d['hyp'][p] for p in parzr):
                toks = d['item']['tokens']
                examples.append({'dataset': ds, 'id': iid, 'type': t, 'original': ' '.join(toks[s:e]) or '(insert)',
                                 'correction': c or '(delete)',
                                 'context': ' '.join(toks[max(0, s - 6):s] + ['[' + ' '.join(toks[s:e]) + ' -> ' + (c or '∅') + ']'] + toks[e:e + 6])})
    by_type = collections.Counter(x['type'] for x in examples)
    rng = random.Random(0)
    rng.shuffle(examples)
    picked, per = [], collections.Counter()
    for x in sorted(examples, key=lambda x: -by_type[x['type']]):
        if per[x['type']] < 2 and len(picked) < 20:
            picked.append(x); per[x['type']] += 1
    out['lt_only_fixes_total'] = len(examples)
    out['lt_only_fixes_by_type'] = by_type.most_common(15)
    out['lt_only_examples'] = picked
    dump_jsonl(OUT / 'lt-only-fixes.jsonl', examples)
    return out


def fmt(x, pct=False):
    if x is None or x == '':
        return '-'
    return f'{x * 100:.1f}' if pct else f'{x}'


def render_md(s):
    L = [f"# Public GEC benchmark: Parzr vs LanguageTool", '',
         f"Parzr engine `{s['parzr_engine']}`, LanguageTool {s['languagetool_version']} (local Docker, first suggestion of every match applied).", '']
    dp = s.get('deep_plan') or {}
    if dp:
        L += [f"Deep mode timing probe: {dp.get('seconds_per_sentence')}s/sentence on 50 CoNLL sentences; projected "
              f"{dp.get('projected_hours')}h for {dp.get('items')} items; " +
              (f"sampled (seed 0), n = {dp.get('n')}." if dp.get('sampled') else 'ran on the full sets (no sampling).'), '']
    ds = s['datasets']
    if 'conll14' in ds:
        d = ds['conll14']
        L += ['## CoNLL-2014 test (1,312 sentences, 2 annotators)', '',
              f"ERRANT = span-based correction vs ERRANT re-annotation of both annotators (best per sentence). M2 = official NUS M2 scorer v3.2 (Python 3 port) on `official-2014.combined.m2`. "
              f"No-error sentences: {d.get('no_error_sentences')} where neither annotator changed anything.", '',
              '| System | n | ERRANT P | ERRANT R | ERRANT F0.5 | TP | FP | FN | M2 P | M2 R | M2 F0.5 | sentences changed | changed no-error sentences |',
              '| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |']
        for name, x in d['systems'].items():
            e, m = x['errant'], x.get('m2scorer', {})
            L.append(f"| {name} | {x['n']} | {fmt(e['p'], 1)} | {fmt(e['r'], 1)} | {fmt(e['f05'], 1)} | {e['tp']} | {e['fp']} | {e['fn']} | "
                     f"{fmt(m.get('p'), 1)} | {fmt(m.get('r'), 1)} | {fmt(m.get('f05'), 1)} | {x['sentences_changed']} | {x.get('changed_no_error_sentences')}/{x.get('no_error_sentences')} |")
        L.append('')
    for name in ('jfleg-dev', 'jfleg-test'):
        if name not in ds:
            continue
        d = ds[name]
        L += [f"## JFLEG {name.split('-')[1]} ({d['n']} sentences, 4 references)", '',
              'GLEU from jfleg eval/gleu.py (500 iterations). ERRANT F0.5 "best" picks the best of the 4 references per sentence; "ref0-3" scores against each reference alone.', '',
              '| System | GLEU | ERRANT P | ERRANT R | ERRANT F0.5 (best ref) | F0.5 ref0 | ref1 | ref2 | ref3 | mean single-ref F0.5 | sentences changed |',
              '| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |']
        for sysname, x in d['systems'].items():
            if 'errant' not in x:
                L.append(f"| {sysname} | {fmt(x.get('gleu', {}).get('gleu'), 1)} | - | - | - | - | - | - | - | - | 0 |"); continue
            e, sr = x['errant'], x.get('errant_single_ref', {})
            L.append(f"| {sysname} | {fmt(x.get('gleu', {}).get('gleu'), 1)} | {fmt(e['p'], 1)} | {fmt(e['r'], 1)} | {fmt(e['f05'], 1)} | " +
                     ' | '.join(fmt(sr.get(f'ref{k}', {}).get('f05'), 1) for k in range(4)) +
                     f" | {fmt(x.get('errant_single_ref_mean_f05'), 1)} | {x['sentences_changed']} |")
        L.append('')
    for name, title in (('typo', 'GitHub Typo Corpus, English prose pairs'), ('typo-real', 'GitHub Typo Corpus, real-word typos')):
        if name not in ds:
            continue
        d = ds[name]
        pool_n = s.get('data_stats', {}).get('typo_all' if name == 'typo' else 'typo_real_all')
        L += [f"## {title} (n = {d['n']} of {pool_n} extracted pairs" + (', random sample seed 0)' if pool_n and d['n'] < pool_n else ')'), '',
              'fix = the typo region of the output equals the reference (other changes ignored); exact = whole output equals the reference; '
              'wrong = changed the typo region but not to the reference; collateral = changed something outside the typo region.', '',
              '| System | n | fix rate | exact | touched | wrong fix | collateral change |', '| --- | --- | --- | --- | --- | --- | --- |']
        for sysname, x in d['systems'].items():
            L.append(f"| {sysname} | {x['n']} | {fmt(x['fix_rate'], 1)} | {fmt(x['exact_fix_rate'], 1)} | {fmt(x['touched_rate'], 1)} | "
                     f"{fmt(x['wrong_fix_rate'], 1)} | {fmt(x['collateral_change_rate'], 1)} |")
        L.append('')
    L += ['## Precision with whitespace-only and case-only false positives removed', '',
          'Unmatched system edits that only change spacing (e.g. "situation,it" -> "situation , it", a glued comma in the CoNLL source) '
          'or only change case are often legitimate but absent from the references. This shows how much they move precision.', '',
          '| dataset | system | FP | FP whitespace-only | FP case-only | P | P excl. | F0.5 | F0.5 excl. |', '| --- | --- | --- | --- | --- | --- | --- | --- | --- |']
    for dname in GEC_DATASETS:
        for sysname, x in ds.get(dname, {}).get('systems', {}).items():
            if 'fp_artifacts' not in x:
                continue
            fa, e = x['fp_artifacts'], x['errant']
            L.append(f"| {dname} | {sysname} | {e['fp']} | {fa.get('fp_whitespace_only', 0)} | {fa.get('fp_case_only', 0)} | {fmt(e['p'], 1)} | "
                     f"{fmt(fa['p_excluding_those'], 1)} | {fmt(e['f05'], 1)} | {fmt(fa['f05_excluding_those'], 1)} |")
    L.append('')
    L += ['## Measurement artifacts checked', '',
          '| dataset | source tokenization round-trip failures | gold British->American respellings | outputs with new double spaces (per system) |', '| --- | --- | --- | --- |']
    for dname, d in ds.items():
        dbl = ', '.join(f"{k} {v.get('outputs_with_new_double_spaces', 0)}" for k, v in d['systems'].items() if 'outputs_with_new_double_spaces' in v)
        L.append(f"| {dname} | {d.get('tokenization_roundtrip_failures', '-')} | {d.get('gold_british_to_american_respellings', '-')} | {dbl} |")
    L += ['', 'Double spaces come from Parzr deletions that remove a word but neither adjacent space; they are ignored by scoring '
          '(retokenization and typo comparisons split on whitespace) but are visible in the raw engine output.', '']
    an = s.get('analysis', {})
    for key, rows in an.items():
        if key.startswith('top_missed_types.'):
            L += [f"## Top 15 ERRANT types by misses: {key.split('.', 1)[1]} (CoNLL + JFLEG dev/test pooled)", '',
                  '| ERRANT type | Parzr misses (FN) | Parzr TP | Parzr recall | LT TP | LT recall |', '| --- | --- | --- | --- | --- | --- |']
            for r in rows:
                L.append(f"| {r['type']} | {r['parzr_misses']} | {r['parzr_tp']} | {fmt(r['parzr_recall'], 1)} | {r['lt_tp']} | {fmt(r['lt_recall'], 1)} |")
            L.append('')
    for key, rows in an.items():
        if key.startswith('top_false_positive_types.'):
            L += [f"### False positives by ERRANT type: {key.split('.', 1)[1]}", '', '| type | FP |' + (' LT FP |' if 'parzr' in key else ''),
                  '| --- | --- |' + (' --- |' if 'parzr' in key else '')]
            for r in rows:
                L.append(f"| {r['type']} | {r['fp']} |" + (f" {r['lt_fp']} |" if 'parzr' in key else ''))
            L.append('')
    if an.get('lt_only_examples'):
        L += [f"## Gold edits LanguageTool fixes exactly and no Parzr layer does ({an['lt_only_fixes_total']} total)", '',
              'By type: ' + ', '.join(f'{t} {n}' for t, n in an['lt_only_fixes_by_type']), '',
              '| dataset | type | context [original -> correction] |', '| --- | --- | --- |']
        for x in an['lt_only_examples']:
            L.append(f"| {x['dataset']} | {x['type']} | {x['context'].replace('|', '/')} |")
        L.append('')
    L += ['## Method notes', ''] + [f'- {n}' for n in s['notes']] + ['']
    return '\n'.join(L)


NOTES = [
    'CoNLL-2014 and JFLEG are tokenized. Engines receive a detokenized sentence (clitics such as n\'t and \'s, punctuation and quotes re-attached; `` and \'\' become "). Outputs are retokenized into the source scheme: a whitespace chunk that also occurs in the detokenized source reuses the source tokens, so unchanged text round-trips exactly (round-trip failures are reported per dataset); changed chunks use a PTB-style regex splitter that keeps hyphenated words whole.',
    'Curly quotes/apostrophes and non-breaking spaces are folded to ASCII in every output before scoring, so typographic-quote suggestions are not counted as edits.',
    'ERRANT references are re-annotated from each annotator\'s corrected sentence (orig -> corrected, errant 3.0.2, spaCy en_core_web_sm), so ERRANT types are consistent across gold and system edits. The official NUCLE-typed M2 is scored separately with the M2 scorer.',
    'Per-type counts come from errant_compare\'s per-sentence best reference, which is chosen per system; denominators (TP+FN) therefore differ slightly between systems.',
    'LanguageTool: every match with at least one suggestion contributes its first suggestion; overlapping matches after the first are skipped; no rule categories are disabled (default level, not picky).',
    'Parzr is run with no dialect, so both British and American spellings are accepted; LanguageTool en-US flags British spellings (CoNLL essays are Singaporean/British English). The languagetool-en-GB row on CoNLL measures that artifact.',
    'Typo corpus: English (NanigoNet lang=eng on both sides), is_typo=true edits whose source and target look like single-line prose (6+ words, capitalised, ending in . ! ?, no code/markup characters) and differ in one word-level region of at most 3 tokens with character edit distance <= 3 (drops content rewrites the typo classifier let through), excluding case-only changes (mostly brand casing such as Github -> GitHub) and pure British/American respellings; deduplicated by source. Real-word subset: a single-token substitution where both words (punctuation stripped) are alphabetic, differ beyond case, are within edit distance 2, and appear in /usr/share/dict/words (Webster\'s 2nd, which lacks many inflected forms, so the subset under-represents e.g. plural/tense slips).',
]


def main():
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('command', choices=['prepare', 'run', 'score', 'all'])
    p.add_argument('--engine', default=DEFAULT_ENGINE)
    p.add_argument('--systems', default=','.join(SYSTEMS))
    p.add_argument('--datasets', default=','.join(DATASETS))
    p.add_argument('--deep-budget-hours', type=float, default=2.0)
    a = p.parse_args()
    if a.command in ('prepare', 'all'):
        cmd_prepare(a)
    if a.command in ('run', 'all'):
        cmd_run(a)
    if a.command in ('score', 'all'):
        cmd_score(a)


if __name__ == '__main__':
    main()
