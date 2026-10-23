#!/usr/bin/env python3
"""False-alarm hunt: run every tense rule's regex (Python re, the same patterns as the engine) over a corpus of CORRECT
text and list the hits. Far faster than the engine, because a rule is only tried when the word it is about occurs.

    python3 scripts/tense-pack/mine.py CORPUS.jsonl OUT.jsonl [workers]

CORPUS rows: {"input": ..., "clean": true}, or {"reference": ...} (the corrected text), or {"text": ...}.
OUT rows: [rule id, matched word, sentence, offset]. Every hit has to be read: a hit on a correct sentence means the
rule is tightened or dropped (the corpus is not perfectly clean, so a hit can also be a real error).
"""
import json, os, pathlib, re, sys, multiprocessing as mp

HERE = pathlib.Path(__file__).resolve().parent
PACK = HERE.parent.parent / 'engine/rules/packs/tense-aspect.json'
INDEX, ALWAYS = None, None


def target_words(pattern):
    """The words the target group can start with, to decide quickly whether a text can match at all."""
    i = pattern.find('(?P<target>')
    if i < 0:
        return None
    j = i + len('(?P<target>')
    depth, k = 1, j
    while depth:
        c = pattern[k]
        if c == '\\':
            k += 2
            continue
        depth += (c == '(') - (c == ')')
        k += 1
    body = re.sub(r'\(\?-i:|\(\?:|\(\?P<\w+>', '(', pattern[j:k - 1])
    words = []
    for alt in body.split('|'):
        alt = alt.replace('(', '').replace(')', '')
        m = re.match(r"\s*([A-Za-z]{2,})", alt.replace("\\s+", " ").replace("['’]", "'"))
        if not m:
            return None
        words.append(m.group(1).lower())
    return words


def init():
    global INDEX, ALWAYS
    os.nice(10)
    INDEX, ALWAYS = {}, []
    for r in json.load(open(PACK)):
        item = (r['id'], re.compile(r['pattern']))
        words = target_words(r['pattern'])
        if not words:
            ALWAYS.append(item)
        else:
            for w in set(words):
                INDEX.setdefault(w, []).append(item)


def work(chunk):
    out = []
    for t in chunk:
        toks = set(re.findall(r"[a-z]+", t.lower()))
        cands = list(ALWAYS)
        for w in toks:
            cands.extend(INDEX.get(w, ()))
        seen = set()
        for rid, rx in cands:
            if rid in seen:
                continue
            seen.add(rid)
            for m in rx.finditer(t):
                out.append((rid, t[m.start('target'):m.end('target')], t, m.start('target')))
    return out


def texts(path):
    seen = set()
    for line in open(path, encoding='utf-8', errors='replace'):
        try:
            r = json.loads(line)
        except Exception:
            continue
        t = r.get('reference') if not r.get('clean') and r.get('reference') else r.get('input') or r.get('text')
        if isinstance(t, str) and t.strip() and len(t) < 800 and t not in seen:
            seen.add(t)
            yield t


if __name__ == '__main__':
    corpus, outp = sys.argv[1], sys.argv[2]
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    all_texts = list(texts(corpus))
    chunks = [all_texts[i:i + 500] for i in range(0, len(all_texts), 500)]
    n = 0
    with open(outp, 'w') as f, mp.Pool(workers, initializer=init) as pool:
        for hits in pool.imap_unordered(work, chunks):
            n += len(hits)
            for h in hits:
                f.write(json.dumps(h) + '\n')
    print(len(all_texts), 'texts,', n, 'hits ->', outp)
