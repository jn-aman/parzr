#!/usr/bin/env python3
"""Compile the hand-authored held-out corpus from inline-markup source files.

Source format (src/errors/*.txt and src/clean/*.txt):

    # category/subcategory           section header
    <reg><flags>|<text>              one item per line

<reg> is one letter: c=chat, e=email, d=doc, s=social, t=technical.
Flags: "!" marks a style-level issue (errors), "@gb" marks en-GB (clean).

Errors are marked inline as [[original=>fix]] or [[original=>fix|alt1|alt2]].
An empty original is an insertion, an empty fix is a deletion. Alternatives
are other acceptable fixes for that span; each yields one full-sentence entry
in "alternatives" (other spans kept at their primary fix).

Usage: python3 build.py   (writes ../errors.jsonl and ../clean.jsonl)
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
REG = {"c": "chat", "e": "email", "d": "doc", "s": "social", "t": "technical"}
LINE = re.compile(r"^([cedst])([!@a-z]*)\|(.*)$")
MARK = re.compile(r"\[\[(.*?)=>(.*?)\]\]")


def u16(s):
    return len(s.encode("utf-16-le")) // 2


def parse_marked(text):
    """Return (input, spans, choices) where choices[i] = [fix, alt...]."""
    inp, spans, choices, pos = "", [], [], 0
    for m in MARK.finditer(text):
        inp += text[pos:m.start()]
        orig = m.group(1)
        opts = m.group(2).split("|")
        start = u16(inp)
        inp += orig
        spans.append({"start": start, "end": u16(inp), "original": orig, "fix": opts[0]})
        choices.append(opts)
        pos = m.end()
    inp += text[pos:]
    return inp, spans, choices


def render(text, picks):
    out, pos = "", 0
    for i, m in enumerate(MARK.finditer(text)):
        out += text[pos:m.start()] + m.group(2).split("|")[picks[i]]
        pos = m.end()
    return out + text[pos:]


def read_dir(sub):
    items = []
    d = os.path.join(HERE, sub)
    for name in sorted(os.listdir(d)):
        if not name.endswith(".txt"):
            continue
        cat = sub_cat = None
        for ln, raw in enumerate(open(os.path.join(d, name), encoding="utf-8"), 1):
            line = raw.rstrip("\n")
            if not line.strip():
                continue
            if line.startswith("# "):
                cat, _, sub_cat = line[2:].strip().partition("/")
                continue
            m = LINE.match(line)
            if not m:
                sys.exit(f"{name}:{ln}: bad line: {line!r}")
            items.append((name, ln, cat, sub_cat, m.group(1), m.group(2), m.group(3)))
    return items


def main():
    errors = []
    for name, ln, cat, sub, reg, flags, text in read_dir("errors"):
        inp, spans, choices = parse_marked(text)
        if not spans:
            sys.exit(f"{name}:{ln}: no error markup")
        ref = render(text, [0] * len(choices))
        alts = []
        for i, opts in enumerate(choices):
            for k in range(1, len(opts)):
                picks = [0] * len(choices)
                picks[i] = k
                a = render(text, picks)
                if a != ref and a not in alts:
                    alts.append(a)
        item = {
            "id": f"heldout-e-{len(errors) + 1:04d}",
            "category": cat,
            "subcategory": sub,
            "input": inp,
            "reference": ref,
            "alternatives": alts,
            "spans": spans,
            "register": REG[reg],
            "source": "authored",
        }
        if "!" in flags:
            item["severity"] = "style"
        errors.append(item)

    clean = []
    for name, ln, cat, sub, reg, flags, text in read_dir("clean"):
        if "[[" in text:
            sys.exit(f"{name}:{ln}: markup in clean item")
        item = {
            "id": f"heldout-c-{len(clean) + 1:04d}",
            "category": "clean",
            "subcategory": sub,
            "input": text,
            "register": REG[reg],
            "source": "authored",
        }
        if "@gb" in flags:
            item["dialect"] = "en-GB"
        clean.append(item)

    for fname, rows in (("errors.jsonl", errors), ("clean.jsonl", clean)):
        with open(os.path.join(OUT, fname), "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"errors={len(errors)} clean={len(clean)}")


if __name__ == "__main__":
    main()
