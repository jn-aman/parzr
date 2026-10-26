"""Shared helpers for the punctuation pack generator: the rule list, Python-side checks of every rule against its own
positive and negative sentence, and the end-to-end cases that build.py can run through the engine."""
import re

RULES = []
PROBLEMS = []
# (rule id, input sentence, expected whole output) and (rule id, sentence that must not be touched by a punct. rule)
E2E = []
NEG = []
IDS = set()

PROVENANCE = 'parzr original rule'

# Determiners that put a modifier right before its noun ("a long-term plan"). "the" is in the list: in "in the
# long term" the noun after the compound is what rules the match out (heads are nouns that cannot start a clause).
DET = r'(?:a|an|the|this|that|our|my|your|their|his|her|its|every|each|another)'
DET_LIST = ['a', 'an', 'the', 'this', 'that', 'our', 'my', 'your', 'their', 'his', 'her', 'its', 'every', 'each', 'another']


def rust_ok(pattern):
    if re.search(r'\(\?[=!<]|\\[1-9]|\\p\{|\\P\{', pattern):
        raise ValueError('lookaround, backreference or \\p{} class (the pack checker compiles with Python re)')
    return re.compile(pattern)


def expand(rx, m, template):
    return re.sub(r'\$\{(\w+)\}', lambda g: m.group(g.group(1)) or '', template)


def apply(rx, text, template):
    """What the engine does with the match: the target group is replaced by the expanded template."""
    m = rx.search(text)
    if not m:
        return None
    g = 'target' if 'target' in rx.groupindex else None
    s, e = (m.start(g), m.end(g)) if g else (m.start(), m.end())
    return text[:s] + expand(rx, m, template) + text[e:]


def add(rid, pattern, replacement, category, confidence, reason, positive, negative, fixed=None, e2e=True, loose=False):
    """Adds one rule. `positive` must match and become `fixed` when the target is replaced; `negative` (several
    sentences joined by spaces) must not match at all."""
    rid = 'punct.' + rid
    if rid in IDS:
        PROBLEMS.append(f'duplicate id {rid}')
        return
    IDS.add(rid)
    try:
        rx = rust_ok(pattern)
    except Exception as ex:  # noqa: BLE001
        PROBLEMS.append(f'{rid}: pattern: {ex}')
        return
    out = apply(rx, positive, replacement)
    if out is None:
        PROBLEMS.append(f'{rid}: positive does not match: {positive!r}')
        return
    if fixed is not None and out != fixed:
        PROBLEMS.append(f'{rid}: positive becomes {out!r}, expected {fixed!r}')
        return
    if rx.search(negative):
        PROBLEMS.append(f'{rid}: negative matches: {negative!r}')
        return
    if out == positive:
        PROBLEMS.append(f'{rid}: replacement equals target')
        return
    RULES.append({
        'id': rid, 'pattern': pattern, 'replacement': replacement, 'category': category,
        'confidence': confidence, 'reason': reason, 'provenance': PROVENANCE,
        'positive': positive, 'negative': negative,
    })
    if e2e:
        E2E.append((rid, positive, out, loose))
        for sentence in re.split(r'(?<=[.!?])\s+(?=[A-Z"“])', negative):
            NEG.append((rid, sentence))


def a_an(word):
    """The indefinite article for the word as it is said."""
    return 'an' if re.match(r'(?i)[aeiou]|hour|heir|honest|honor', word) and not re.match(r'(?i)uni(?![a-z]*n)|use|one|eu', word) else 'a'


def alt(words):
    return '|'.join(re.escape(w) if not re.fullmatch(r"[A-Za-z' -]+", w) else w for w in words)
