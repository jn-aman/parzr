"""Runs every pack rule (Python re) over a JSONL corpus of {input, reference, clean} rows.
usage: python3 scan_corpus.py CORPUS.jsonl [PACK.json] [--examples N]
Prints, per rule: hits on clean rows (candidate false alarms: the corpus says the text is right), hits on changed rows,
and how many of those fixes reproduce the reference. Text is only printed for the clean-row hits so they can be judged;
never copy it anywhere."""
import collections, json, multiprocessing as mp, pathlib, re, sys
HERE = pathlib.Path(__file__).resolve().parent
corpus = sys.argv[1]
pack = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 and not sys.argv[2].startswith('--') else HERE.parents[2] / 'engine/rules/packs/pronouns.json'
N_EX = int(sys.argv[sys.argv.index('--examples') + 1]) if '--examples' in sys.argv else 3
rules = json.loads(pack.read_text())
rx = [re.compile(r['pattern']) for r in rules]


def apply(rule, m, text):
    rep = re.sub(r'\$\{(\w+)\}', lambda g: m.group(g.group(1)) or '', rule['replacement'])
    t = m.group('target')
    if 'moved' in m.re.groupindex and m.group('moved') is not None:
        return text[:m.start('target')] + text[m.start('moved'):m.end('moved')] + rep + text[m.end('moved'):]
    if t and t[0].isupper() and len(t) > 1 and rep:
        rep = rep[0].upper() + rep[1:]
    return text[:m.start('target')] + rep + text[m.end('target'):]


def work(lines):
    clean_hits = collections.defaultdict(list)
    chg = collections.Counter()
    ok = collections.Counter()
    for line in lines:
        try:
            r = json.loads(line)
        except Exception:
            continue
        t = r.get('input') or r.get('text')
        if not isinstance(t, str):
            continue
        for i, x in enumerate(rx):
            m = x.search(t)
            if not m:
                continue
            if r.get('clean') is True:
                if len(clean_hits[i]) < 40:
                    clean_hits[i].append((m.group(0), t))
                else:
                    clean_hits[i].append(None)
            else:
                chg[i] += 1
                ref = r.get('reference')
                if isinstance(ref, str) and apply(rules[i], m, t) == ref:
                    ok[i] += 1
    return clean_hits, chg, ok


if __name__ == '__main__':
    lines = pathlib.Path(corpus).read_text(encoding='utf-8', errors='replace').splitlines()
    size = 20000
    chunks = [lines[i:i + size] for i in range(0, len(lines), size)]
    with mp.Pool(10) as pool:
        parts = pool.map(work, chunks)
    clean_hits = collections.defaultdict(list)
    chg, ok = collections.Counter(), collections.Counter()
    for c, g, k in parts:
        for i, v in c.items():
            clean_hits[i] += v
        chg.update(g)
        ok.update(k)
    print(len(lines), 'rows;', sum(len(v) for v in clean_hits.values()), 'hits on clean rows')
    for i in sorted(set(clean_hits) | set(chg), key=lambda i: -len(clean_hits.get(i, []))):
        h = [x for x in clean_hits.get(i, []) if x]
        print(f"{rules[i]['id']}: clean-row hits {len(clean_hits.get(i, []))}; changed-row hits {chg[i]}, fix == reference {ok[i]}")
        for m, t in h[:N_EX]:
            k = t.find(m)
            print('     ', repr(m), '|', t[max(0, k - 60):k + len(m) + 60].replace('\n', ' '))
