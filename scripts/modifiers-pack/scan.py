#!/usr/bin/env python3
"""Fast false-alarm scan of the pack against a plain-text corpus (one sentence per line) with Python's re: for each
rule a literal word prefilters the lines, then the pattern runs on those lines. Prints per-rule hit counts and a few
hits. usage: scan.py CORPUS [--rules SUBSTR ...] [--show N]"""
import json, pathlib, re, sys
HERE = pathlib.Path(__file__).resolve().parent
rules = json.loads((HERE.parent.parent / 'engine/rules/packs/modifiers.json').read_text())
args = sys.argv[1:]
corpus = args.pop(0)
show = 4
sel = []
while args:
    a = args.pop(0)
    if a == '--show':
        show = int(args.pop(0))
    elif a == '--rules':
        sel = args
        break
lines = pathlib.Path(corpus).read_text(encoding='utf-8', errors='replace').split('\n')
text = '\n'.join(lines)
lower = text.lower()
# line start offsets
starts = [0]
for l in lines[:-1]:
    starts.append(starts[-1] + len(l) + 1)
import bisect

def literal(pat):
    p = re.sub(r'\(\?[a-zA-Z]+\)', '', pat)
    prev = None
    while prev != p:
        prev = p
        p = re.sub(r'\((?:\?:|\?P<\w+>)?[^()]*\)', lambda m: ' ' if '|' in m.group(0) else m.group(0), p)
    words = re.findall(r"[a-z]{4,}", p.replace('\\b', ' ').lower())
    words = [w for w in words if w not in ('target', 'ever') or True]
    return max(words, key=len) if words else None

total = 0
for r in rules:
    if sel and not any(s in r['id'] for s in sel):
        continue
    lit = literal(r['pattern'])
    rx = re.compile(r['pattern'])
    hits = []
    seen_lines = set()
    if lit:
        pos = lower.find(lit)
        while pos != -1:
            li = bisect.bisect_right(starts, pos) - 1
            if li not in seen_lines:
                seen_lines.add(li)
                m = rx.search(lines[li])
                if m:
                    hits.append((lines[li], m.group(0)))
            pos = lower.find(lit, pos + 1)
    else:
        for l in lines:
            m = rx.search(l)
            if m:
                hits.append((l, m.group(0)))
    if hits:
        total += len(hits)
        print(f'{len(hits):5d}  {r["id"]}  (literal {lit!r})')
        for l, g in hits[:show]:
            i = l.find(g)
            print('         ...' + l[max(0, i - 60): i + len(g) + 50].replace('\n', ' ') + '...   [' + g + ']')
print('total hits', total)
