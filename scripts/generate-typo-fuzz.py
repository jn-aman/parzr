#!/usr/bin/env python3
"""Generate the keystroke-noise typo fuzz sets (benchmarks/typo-fuzz) from correct sentences.

Every eligible word of every base sentence gets ONE perturbation of each type (seeded, so the output never changes
for the same inputs):

  drop        a letter left out                   ("this" -> "thi")
  add         an adjacent key typed as well       ("this" -> "thius")
  substitute  an adjacent key instead             ("this" -> "thus")
  transpose   two neighbouring letters swapped    ("this" -> "htis")
  double      a letter typed twice                ("this" -> "thiis")
  undouble    a doubled letter typed once         ("will" -> "wil")
  space_in    a space typed inside the word       ("not" -> "no t")
  space_del   the space after the word left out   ("is not" -> "isnot")
  case_start  the sentence's first letter in lowercase ("This is" -> "this is")
  apostrophe_missing  ("don't" -> "dont", "it's" -> "its")
  apostrophe_extra    ("books" -> "book's", "its" -> "it's")

Skipped: names (a capital inside a sentence, or a lexicon name), numbers, code, URLs, e-mail addresses, @handles,
ALL-CAPS words and words under two letters. A result that is the same word, or a British-only spelling of it, is
dropped. Each item records its type (category), the word's frequency bucket (subcategory: top-100, top-1k, top-10k,
rare by rank in engine/rules/frequency.json), whether the damaged token is a non-word or another real word
(`word_class`; case_start is `case`), the word's position in its sentence (start, middle, end) and the reference.
The output has the shape of benchmarks/heldout, so scripts/run-heldout-benchmark.py scores it; the base sentences are
also written as the clean set, to count false alarms.

usage:
  generate-typo-fuzz.py --split dev   # from the held-out DEV copies in dist/qa/heldout-dev and src/dev-extra.txt
  generate-typo-fuzz.py --split test  # from src/test-sentences.txt only (written after all fixes, never tuned on)
"""
import argparse, hashlib, json, pathlib, random, re, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / 'benchmarks/typo-fuzz'
DEV_DIR = ROOT / 'dist/qa/heldout-dev'
SEED = 'parzr-typo-fuzz-1'

ROWS = ['qwertyuiop', 'asdfghjkl', 'zxcvbnm']
POS = {c: (r, i) for r, row in enumerate(ROWS) for i, c in enumerate(row)}
# Neighbours on a QWERTY keyboard: same row left and right, and the two keys touching it on each adjacent row.
NEIGHBOURS = {}
for c, (r, i) in POS.items():
    near = set()
    for rr, cols in ((r, (i - 1, i + 1)), (r - 1, (i, i + 1)), (r + 1, (i - 1, i))):
        if 0 <= rr < 3:
            near.update(ROWS[rr][j] for j in cols if 0 <= j < len(ROWS[rr]))
    NEIGHBOURS[c] = sorted(near - {c})

TYPES = ['drop', 'add', 'substitute', 'transpose', 'double', 'undouble', 'space_in', 'space_del',
         'case_start', 'apostrophe_missing', 'apostrophe_extra']
WORD = re.compile(r"[A-Za-z]+(?:['’][A-Za-z]+)*")
CONTRACTION_TAILS = ("n't", "'s", "'m", "'re", "'ll", "'ve", "'d")


def lexicon():
    entries = json.loads((ROOT / 'engine/rules/lexicon.json').read_text())
    lower, flags, names = set(), {}, set()
    for word, f in entries:
        if word == word.lower():
            lower.add(word)
            flags[word] = flags.get(word, 0) | f
        else:
            names.add(word.lower())
    freq = json.loads((ROOT / 'engine/rules/frequency.json').read_text())['entries']
    freq.sort(key=lambda e: (-e[1], e[0]))
    rank = {w: i for i, (w, _) in enumerate(freq)}
    return lower, flags, names - lower, rank


LOWER, FLAGS, NAME_ONLY, RANK = lexicon()


def bucket(word):
    w = word.lower().replace('’', "'")
    if "'" in w:
        stem, tail = w.split("'", 1)
        # Contractions of pronouns and auxiliaries are among the most frequent words; a possessive takes its noun's rank.
        if "'" + tail in CONTRACTION_TAILS or w.endswith("n't"):
            if RANK.get(stem.removesuffix('n'), 10**6) < 1000 or stem in ('i', 'won', 'can', 'don', 'ain'):
                return 'top-100'
        w = stem
    r = RANK.get(w, 10**6)
    return 'top-100' if r < 100 else 'top-1k' if r < 1000 else 'top-10k' if r < 10000 else 'rare'


def real_word(token):
    """The damaged text is itself an ordinary dictionary word (or two, for a space typed inside a word)."""
    parts = token.lower().replace('’', "'").split()
    def ok(p):
        if len(p) == 1:
            return p in ('a', 'i')
        if "'" in p:
            stem, tail = p.split("'", 1)
            return p in LOWER or ("'" + tail in CONTRACTION_TAILS and stem in LOWER)
        return p in LOWER
    return all(ok(p) for p in parts)


def british_only(word):
    f = FLAGS.get(word.lower(), 0)
    return f & 128 and not f & 64


def utf16(s):
    return len(s.encode('utf-16-le')) // 2


def sentences(text):
    """(start, end) byte spans of the sentences in `text`: split after . ! ? or a line break followed by space."""
    spans, start = [], 0
    for m in re.finditer(r'[.!?]+["”’)]*\s+|\n+', text):
        spans.append((start, m.end()))
        start = m.end()
    if start < len(text):
        spans.append((start, len(text)))
    return spans


def eligible(text, m, opens):
    word = m.group()
    if len(word.replace("'", '').replace('’', '')) < 2:
        return False
    # The whitespace-delimited chunk: code, URLs, e-mail, handles, numbers and paths are left alone.
    a = text.rfind(' ', 0, m.start()) + 1
    b = text.find(' ', m.end())
    chunk = text[a:b if b >= 0 else len(text)].strip('()[]{}"“”,;:!?')
    if re.search(r'[0-9_@#/\\<>=`*$%&+~|]|://|www\.|\.[A-Za-z]', chunk.rstrip('.')):
        return False
    if '-' in chunk:  # hyphenated compounds and names ("cloud-based", "Jean-Luc") are left whole
        return False
    if word.isupper() and len(word) > 1:
        return False
    if any(c.isupper() for c in word[1:]):
        return False
    lower = word.lower().replace('’', "'")
    stem = lower.split("'")[0]
    if word[0].isupper():
        # A capital inside a sentence is a name; at a sentence start the word must be an ordinary word.
        if not opens or word == 'I' or stem not in LOWER:
            return False
    if stem in NAME_ONLY or (stem not in LOWER and lower not in LOWER):
        return False
    return True


def keep_case(original, damaged):
    """The damage is made on the lowercase word; a capital first letter stays on the first letter."""
    if original[:1].isupper() and damaged:
        return damaged[:1].upper() + damaged[1:]
    return damaged


def perturb(kind, word, rng, nxt=None):
    """The damaged form of `word` (or of `word` + following space + `nxt` for space_del), or None."""
    w = word.lower()
    letters = [i for i, c in enumerate(w) if c.isalpha()]
    if kind == 'drop':
        if len(letters) < 2:
            return None
        i = rng.choice(letters)
        out = w[:i] + w[i + 1:]
        return keep_case(word, out) if out.strip("'’") else None
    if kind in ('add', 'substitute'):
        i = rng.choice(letters)
        key = rng.choice(NEIGHBOURS[w[i]])
        if kind == 'substitute':
            out = w[:i] + key + w[i + 1:]
        else:
            j = i + rng.choice((0, 1))
            out = w[:j] + key + w[j:]
        return keep_case(word, out)
    if kind == 'transpose':
        spots = [i for i in range(len(w) - 1) if w[i].isalpha() and w[i + 1].isalpha() and w[i] != w[i + 1]]
        if not spots:
            return None
        i = rng.choice(spots)
        return keep_case(word, w[:i] + w[i + 1] + w[i] + w[i + 2:])
    if kind == 'double':
        i = rng.choice(letters)
        return keep_case(word, w[:i + 1] + w[i] + w[i + 1:])
    if kind == 'undouble':
        spots = [i for i in range(len(w) - 1) if w[i] == w[i + 1] and w[i].isalpha()]
        if not spots:
            return None
        i = rng.choice(spots)
        return keep_case(word, w[:i] + w[i + 1:])
    if kind == 'space_in':
        spots = [i for i in range(1, len(w)) if w[i - 1].isalpha() and w[i].isalpha()]
        if not spots:
            return None
        i = rng.choice(spots)
        return keep_case(word, w[:i] + ' ' + w[i:])
    w = word
    lw = word.lower()
    if kind == 'space_del':
        return w + nxt if nxt else None
    if kind == 'apostrophe_missing':
        if "'" not in w and '’' not in w:
            return None
        return w.replace("'", '').replace('’', '')
    if kind == 'apostrophe_extra':
        if "'" in w or '’' in w or not lw.endswith('s') or lw.endswith('ss'):
            return None
        stem = lw[:-1]
        if not (len(lw) >= 4 or lw == 'its') or stem not in LOWER:
            return None
        return w[:-1] + "'" + w[-1]
    return None


def items_for(text, sid, rng_seed):
    out = []
    spans = sentences(text)
    words = [(m, s) for s in spans for m in WORD.finditer(text, s[0], s[1])]
    for k, (m, (sa, sb)) in enumerate(words):
        same = [x for x, s in words if s == (sa, sb)]
        idx = same.index(m)
        opens = idx == 0 and text[sa:m.start()].strip('"“(\'‘ \n') == ''
        position = 'start' if idx == 0 else 'end' if idx == len(same) - 1 else 'middle'
        if not eligible(text, m, opens):
            continue
        word = m.group()
        for kind in TYPES:
            rng = random.Random(f'{rng_seed}:{sid}:{k}:{kind}')
            start, end, nxt = m.start(), m.end(), None
            if kind == 'case_start':
                if not opens or not word[0].isupper():
                    continue
                damaged = word[0].lower() + word[1:]
            elif kind == 'space_del':
                if idx + 1 >= len(same):
                    continue
                n = same[idx + 1]
                if text[m.end():n.start()] != ' ' or not eligible(text, n, False):
                    continue
                nxt, end = n.group(), n.end()
                damaged = perturb(kind, word, rng, nxt)
            else:
                damaged = perturb(kind, word, rng)
            if not damaged:
                continue
            original = text[start:end]
            if damaged.lower() == original.lower() and kind != 'case_start':
                continue
            if kind != 'case_start' and british_only(damaged):
                continue
            new = text[:start] + damaged + text[end:]
            if kind == 'case_start':
                cls = 'case'
            else:
                cls = 'real-word' if real_word(damaged) else 'non-word'
            b = bucket(word) if kind != 'space_del' else min((bucket(word), bucket(nxt)), key=['top-100', 'top-1k', 'top-10k', 'rare'].index)
            out.append({
                'category': kind, 'subcategory': b, 'input': new, 'reference': text, 'alternatives': [],
                'spans': [{'start': utf16(text[:start]), 'end': utf16(text[:start]) + utf16(damaged), 'original': damaged, 'fix': original}],
                'word': original, 'damaged': damaged, 'word_class': cls, 'position': position, 'bucket': b, 'base': sid,
            })
    return out


def base_texts(split, limit, seed, dev_dir):
    if split == 'test':
        lines = (OUT / 'src/test-sentences.txt').read_text().splitlines()
        return [(f'test-s{i:03d}', l.strip(), None) for i, l in enumerate(l for l in lines if l.strip() and not l.startswith('#'))]
    pool = []
    for line in (dev_dir / 'clean.jsonl').read_text().splitlines():
        it = json.loads(line)
        pool.append((it['id'], it['input'], it.get('dialect')))
    for line in (dev_dir / 'errors.jsonl').read_text().splitlines():
        it = json.loads(line)
        pool.append((it['id'] + '-ref', it['reference'], it.get('dialect')))
    # en-GB items and multi-line messages make case and dialect noise; keep single-line sentences of everyday length.
    pool = [p for p in pool if '\n' not in p[1] and 20 <= len(p[1]) <= 140 and not p[2]]
    seen, unique = set(), []
    for p in pool:
        if p[1] not in seen:
            seen.add(p[1]); unique.append(p)
    unique.sort(key=lambda p: hashlib.sha256(f'{seed}:{p[1]}'.encode()).hexdigest())
    extra = (OUT / 'src/dev-extra.txt').read_text().splitlines()
    mine = [(f'dev-x{i:03d}', l.strip(), None) for i, l in enumerate(l for l in extra if l.strip() and not l.startswith('#'))]
    return mine + unique[:max(0, limit - len(mine))]


def main():
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--split', choices=['dev', 'test'], required=True)
    p.add_argument('--sentences', type=int, default=320, help='dev: base texts to draw (own sentences first)')
    p.add_argument('--seed', default=SEED)
    p.add_argument('--dev-dir', type=pathlib.Path, default=DEV_DIR, help='the held-out DEV split copies (clean.jsonl, errors.jsonl)')
    a = p.parse_args()
    if a.split == 'dev' and not (a.dev_dir / 'clean.jsonl').exists():
        sys.exit(f'{a.dev_dir} is missing: it holds the held-out DEV split copies (never benchmarks/heldout itself).')
    bases = base_texts(a.split, a.sentences, a.seed, a.dev_dir)
    items, clean = [], []
    for sid, text, dialect in bases:
        clean.append({'id': f'fuzz-{a.split}-{sid}', 'category': 'clean', 'subcategory': 'base', 'input': text})
        for it in items_for(text, sid, a.seed):
            items.append(it)
    for n, it in enumerate(items):
        it['id'] = f'fuzz-{a.split}-{n:05d}'
    OUT.mkdir(parents=True, exist_ok=True)
    order = ['id', 'category', 'subcategory', 'input', 'reference', 'alternatives', 'spans', 'word', 'damaged', 'word_class', 'position', 'bucket', 'base']
    with open(OUT / f'{a.split}.jsonl', 'w') as f:
        f.writelines(json.dumps({k: it[k] for k in order}, ensure_ascii=False) + '\n' for it in items)
    with open(OUT / f'{a.split}-clean.jsonl', 'w') as f:
        f.writelines(json.dumps(c, ensure_ascii=False) + '\n' for c in clean)
    from collections import Counter
    print(f'{a.split}: {len(bases)} base texts, {len(items)} items')
    print(' types:', dict(Counter(i['category'] for i in items)))
    print(' classes:', dict(Counter(i['word_class'] for i in items)))
    print(' buckets:', dict(Counter(i['bucket'] for i in items)))


if __name__ == '__main__':
    main()
