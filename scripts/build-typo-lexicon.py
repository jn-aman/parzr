#!/usr/bin/env python3
"""Build engine/rules/typos.txt: misspelling -> correction pairs mined from real edits.

Reads the git-ignored mining corpora of the main checkout (dist/mining, see dist/mining/SOURCES.md): the
normalised pairs in corpus/mining.jsonl and their ERRANT gold edits in gold/. Only the mining split is read;
the frozen 1% test sample (corpus/test-sample.jsonl) is never opened, and gold edits of its ids are skipped.

Only openly licensed sources contribute pairs: WikEd (Wikipedia revisions, CC BY-SA), the GitHub Typo Corpus,
Mitton's Holbrook, Aspell and Wikipedia misspelling lists, and the Wikipedia "Lists of common misspellings".
Birkbeck pairs only count when a natural source also has the pair. The non-commercial learner corpora (FCE,
W&I+LOCNESS, CWEB, JFLEG, CoNLL, LexNorm) contribute nothing; their corrected text is only used to check that a
listed misspelling is not a word people write on purpose.

A pair is kept when every check below passes; each one guards a kind of false alarm:
  * the misspelling is ASCII letters, 4+ long, not a word or name in Parzr's lexicon or bundled names, not
    chat shorthand, and seen in the corrected (reference) text of the corpora, where names, code words and
    rare valid words show up, fewer than 3 times or under a quarter as often as it is corrected (references
    keep the typos their own edit did not touch);
  * a single natural edit is enough only for a misspelling of 5+ letters that keeps the word's ending;
  * the correction is made of lexicon words valid in both British and American English, and at most 2 edits
    away (3 for corrections of 8+ letters; a run-together pair must be the same letters with spaces), so
    renames and rewrites ("Orissa" -> "Odisha") are not typos, and it never drops a negative prefix
    ("untelevised" -> "televised");
  * at least 90% of the edits of the misspelling go to the same correction, and no other frequent word is
    one slip away from it ("revies": "reviews" or "revise") unless five natural edits agree on a word of
    six letters or more;
  * a natural source has it (or a curated list does); a correction that is a proper noun needs two natural
    edits; it is not already a phrase rule or a reviewed misspelling.

usage: python3 scripts/build-typo-lexicon.py [--exclude-half B] [--output engine/rules/typos.txt]
  --exclude-half A|B  leave out the items of one half (sha1(id) parity, as the spelling dev evaluation splits
                      them) to measure how the list generalises to unseen text.
"""
import argparse, collections, hashlib, json, os, pathlib, re, subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
RULES = ROOT / 'engine/rules'


def data_root():
    if os.environ.get('PARZR_DATA_ROOT'):
        return pathlib.Path(os.environ['PARZR_DATA_ROOT'])
    try:
        common = subprocess.run(['git', '-C', str(ROOT), 'rev-parse', '--path-format=absolute', '--git-common-dir'],
                                capture_output=True, text=True, check=True).stdout.strip()
        return pathlib.Path(common).parent
    except (OSError, subprocess.CalledProcessError):
        return ROOT


NATURAL = {'wiked-tagged', 'wiked-other', 'github-typo', 'holbrook'}
CURATED = {'wikipedia-misspellings', 'aspell'}
CORROBORATING = {'birkbeck'}
SHORTHAND = {
    'abt', 'alot', 'bday', 'bruh', 'btw', 'cmon', 'coz', 'cuz', 'dat', 'dem', 'dis', 'dunno', 'gimme', 'gonna',
    'gotta', 'idk', 'imma', 'kinda', 'lemme', 'lil', 'luv', 'nite', 'nvm', 'outta', 'pls', 'plz', 'ppl', 'sorta',
    'tho', 'thru', 'thx', 'tmrw', 'tonite', 'wanna', 'whatcha', 'ya', 'yall', 'yrs', 'yup',
}
WORD = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)*")
DIALECT = [('our', 'or'), ('ise', 'ize'), ('isa', 'iza'), ('yse', 'yze'), ('tre', 'ter'), ('ogue', 'og'),
           ('lled', 'led'), ('lling', 'ling'), ('ller', 'ler'), ('ence', 'ense'), ('ae', 'e'), ('oe', 'e')]


def osa(a, b):
    d = [[i + j if i * j == 0 else 0 for j in range(len(b) + 1)] for i in range(len(a) + 1)]
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (a[i - 1] != b[j - 1]))
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                d[i][j] = min(d[i][j], d[i - 2][j - 2] + 1)
    return d[-1][-1]


def dialect(o, c):
    for a, b in DIALECT:
        for x, y in ((o, c), (c, o)):
            i = x.find(a)
            while i != -1:
                if x[:i] + b + x[i + len(a):] == y:
                    return True
                i = x.find(a, i + 1)
    return False


def edits1(word):
    letters = 'abcdefghijklmnopqrstuvwxyz'
    splits = [(word[:i], word[i:]) for i in range(len(word) + 1)]
    return ({a + b[1:] for a, b in splits if b} | {a + b[1] + b[0] + b[2:] for a, b in splits if len(b) > 1}
            | {a + c + b[1:] for a, b in splits if b for c in letters} | {a + c + b for a, b in splits for c in letters})


def listed(path):
    return {line.split()[0].lower() for line in path.read_text().splitlines() if line.strip() and not line.startswith('#')}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--exclude-half', choices=['A', 'B'])
    ap.add_argument('--output', default=str(RULES / 'typos.txt'))
    ap.add_argument('--min-natural', type=int, default=1)
    a = ap.parse_args()
    mining = data_root() / 'dist/mining'

    flags = collections.defaultdict(int)
    for w, f in json.loads((RULES / 'lexicon.json').read_text()):
        flags[w.lower()] |= f
    ordinary = {w for w, _ in json.loads((RULES / 'lexicon.json').read_text()) if w == w.lower()}
    freq = dict(json.loads((RULES / 'frequency.json').read_text())['entries'])
    names = listed(RULES / 'names.txt')
    taken = listed(RULES / 'misspellings.txt') | {
        r['source'].lower() for r in json.loads((RULES / 'phrases.json').read_text()) if ' ' not in r['source']}

    def half(item_id):
        return 'A' if int(hashlib.sha1(item_id.encode()).hexdigest()[:8], 16) % 2 == 0 else 'B'

    items, refs = {}, collections.Counter()
    with (mining / 'corpus/mining.jsonl').open() as f:
        for line in f:
            r = json.loads(line)
            for w in WORD.findall(r['reference']):
                refs[w.lower()] += 1
            if not r['clean'] and r['source'] in NATURAL | CURATED | CORROBORATING \
                    and half(r['id']) != a.exclude_half:
                items[r['id']] = r['source']

    seen = collections.defaultdict(collections.Counter)      # misspelling -> correction counts
    sources = collections.defaultdict(collections.Counter)   # misspelling -> source counts
    for part in sorted((mining / 'gold').glob('part-*.jsonl')):
        for line in part.open():
            g = json.loads(line)
            source = items.get(g['id'])  # test-sample ids are not in the mining split
            if source is None or 'e' not in g:
                continue
            for o_s, o_e, c_s, c_e, _, o, c in g['e']:
                if o_e - o_s != 1 or not o.isalpha() or not c or not all(WORD.fullmatch(w) for w in c.split()):
                    continue
                seen[o.lower()][c] += 1
                sources[o.lower()][source] += 1

    out, why = [], collections.Counter()
    for o, cs in sorted(seen.items()):
        total = sum(cs.values())
        lower = collections.Counter()
        for c, n in cs.items():
            lower[c.lower()] += n
        target, n = lower.most_common(1)[0]
        forms = collections.Counter({c: k for c, k in cs.items() if c.lower() == target})
        natural = sum(k for s, k in sources[o].items() if s in NATURAL)
        curated = sum(k for s, k in sources[o].items() if s in CURATED)
        words = target.split()
        proper = all(w not in ordinary for w in words)
        # One edit is evidence enough only when it keeps the word's ending ("remeves" is "removes", not
        # "remove") and is no run-together pair ("timeson"); otherwise two edits or a curated list are needed.
        endings = ('s', 'ed', 'ing', 'ly', 'er')
        alike = ' ' not in target and all(o.endswith(e) == target.endswith(e) for e in endings)
        need = 2 if proper else (1 if alike and len(o) >= 5 and a.min_natural <= 1 else max(2, a.min_natural))
        checks = [
            ('shape', o.isascii() and len(o) >= 4 and o != target),
            ('word', o not in flags and o not in names and o not in SHORTHAND and o not in taken),
            ('written', refs[o] < 3 or refs[o] * 4 <= total),
            ('target', all(flags.get(w, 0) & 192 == 192 for w in words) and not dialect(o, target)),
            ('distance', target.replace(' ', '') == o if ' ' in target
             else osa(o, target) <= (3 if len(target) >= 8 else 2)),
            ('agreement', n >= 0.9 * total),
            # "untelevised" -> "televised" drops a negative prefix: an edit of meaning, not a typo.
            ('negation', not any(o == p + target for p in ('un', 'in', 'im', 'il', 'ir', 'non', 'dis', 'a'))),
            # "rethrown" -> "thrown": a prefixed word is a word, not a typo of its stem.
            ('prefix', not any(o == p + target for p in ('re', 'pre', 'de', 'co', 'mis', 'sub', 'over', 'under', 'out'))),
            ('evidence', natural >= need or curated >= 1 and not proper and (alike or natural >= 1)),
        ]
        # Another frequent word one slip away ("revies": "reviews" or "revise") leaves the choice to
        # the sentence, unless the edits agree often enough to settle it.
        rivals = [w for w in edits1(o) if w != target and w in ordinary and freq.get(w, 0) >= 300]
        checks.append(('ambiguous', not rivals or natural >= 5 and len(o) >= 6))
        failed = next((name for name, ok in checks if not ok), None)
        if failed:
            why[failed] += 1
            continue
        # The usual case of the correction: "February", "Caribbean"; ordinary words stay lowercase.
        if proper:
            correction = ' '.join(max(((k, f) for f, k in forms.items()), key=lambda x: x[0])[1].split())
            correction = correction[:1].upper() + correction[1:]
        else:
            correction = target
        out.append((o, correction))

    header = [
        '# Misspellings mined from real corrections, one "misspelling correction" pair per line.',
        '# Generated by scripts/build-typo-lexicon.py from edits in WikEd (Wikipedia revisions, CC BY-SA 3.0; Grundkiewicz',
        '# and Junczys-Dowmunt 2014), the GitHub Typo Corpus v1.0.0 (Hagiwara and Mita 2020), Roger Mitton\'s Holbrook,',
        '# Aspell and Wikipedia misspelling lists (Birkbeck), and Wikipedia:Lists of common misspellings (CC BY-SA 4.0).',
        '# Only word pairs are kept, no text. A pair is listed when the misspelling is not a word or name, is rarely',
        '# written on purpose in corrected text, and is corrected the same way at least 90% of the time; see the script.',
    ]
    pathlib.Path(a.output).write_text('\n'.join(header + [f'{o} {c}' for o, c in out]) + '\n')
    print(f'{len(out)} pairs written to {a.output}; dropped by check: {dict(why)}')


if __name__ == '__main__':
    main()
