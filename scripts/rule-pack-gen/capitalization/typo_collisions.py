#!/usr/bin/env python3
"""Lists the single-word triggers of the pack that are one edit (insertion, deletion, substitution or transposition) away
from a frequent English word. A typo of "it" ("iit"), "used" ("usd"), "we" ("wwe") or "two" ("wto") must be left to the
spelling pass, so a rule that capitalizes such a trigger is dropped (typo-fuzz DEV caught it).
usage: typo_collisions.py [--zipf 380] [--max-len 6]"""
import argparse, json, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parents[3]
ap = argparse.ArgumentParser()
ap.add_argument('--zipf', type=int, default=380)
ap.add_argument('--max-len', type=int, default=6)
a = ap.parse_args()
freq = json.load(open(ROOT / 'engine/rules/frequency.json'))['entries']
common = {w for w, z in freq if z >= a.zipf and w.isalpha()}
lex = {w.lower() for w, _ in json.load(open(ROOT / 'engine/rules/lexicon.json'))}
by_len = {}
for w in common:
    by_len.setdefault(len(w), set()).add(w)


KEYS = ['qwertyuiop', 'asdfghjkl', 'zxcvbnm']
NEIGH = {}
for r, row in enumerate(KEYS):
    for i, ch in enumerate(row):
        n = set()
        for dr in (-1, 0, 1):
            rr = r + dr
            if 0 <= rr < 3:
                for di in (-1, 0, 1):
                    j = i + di
                    if 0 <= j < len(KEYS[rr]) and (dr or di):
                        n.add(KEYS[rr][j])
        NEIGH[ch] = n


def typos(w):
    out = set()
    for i in range(len(w)):
        out.add(w[:i] + w[i] + w[i:])            # doubled letter
        out.add(w[:i] + w[i + 1:])               # deleted letter
        for n in NEIGH.get(w[i], ()):
            out.add(w[:i] + n + w[i + 1:])       # adjacent key
            out.add(w[:i] + n + w[i:])           # extra adjacent key
        if i + 1 < len(w):
            out.add(w[:i] + w[i + 1] + w[i] + w[i + 2:])  # transposition
    out.discard(w)
    return out


TYPO_OF = {}
for w in common:
    for t in typos(w):
        TYPO_OF.setdefault(t, []).append(w)


def near(c):
    return TYPO_OF.get(c, [])


def near_old(c):
    out = []
    for L in (len(c) - 1, len(c), len(c) + 1):
        for w in by_len.get(L, ()):
            if w == c:
                continue
            if len(w) == len(c):
                d = [i for i in range(L) if w[i] != c[i]]
                if len(d) == 1 or (len(d) == 2 and d[1] == d[0] + 1 and w[d[0]] == c[d[1]] and w[d[1]] == c[d[0]]):
                    out.append(w)
            else:
                s, l = (c, w) if len(c) < len(w) else (w, c)
                for i in range(len(l)):
                    if l[:i] + l[i + 1:] == s:
                        out.append(w)
                        break
    return out


rules = json.load(open(ROOT / 'engine/rules/packs/capitalization-rules.json'))
hits = {}
for r in rules:
    if r['id'].split('.')[1] in ('title', 'stray', 'dir', 'subject', 'unit', 'device'):
        continue
    m = re.search(r'\(\?P<target>\(\?-i:([^)]*)\)\)', r['pattern'])
    if not m:
        continue
    for alt in m.group(1).split('|'):
        if alt.isalpha() and alt == alt.lower() and 2 < len(alt) <= a.max_len and alt not in common:
            n = near(alt)
            if n:
                hits.setdefault(r['id'], []).append((alt, n[:4]))
for rid, v in sorted(hits.items()):
    print(rid, v)
print(len(hits), 'rules')
