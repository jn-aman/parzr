"""Shared machinery for scripts/gen-clauses-conjunctions.py: the rule list, self-checks and regex fragments.

Every rule is added with `add()`, which refuses it unless (a) the pattern compiles, (b) the positive example changes
to exactly the stated correction when the replacement is applied the way the engine applies it (case matched to the
target, a sentence start capitalized), (c) the negative example does not match at all, and (d) the corrected
sentence does not match the rule again. `cross_check()` then runs every rule over every other rule's negative and
corrected examples, so two rules cannot silently fight.
"""
import re

PREFIX = 'clause.'
RULES = []
COVER = []   # (section, construction, rule ids or note)
SECTIONS = {}  # section -> rule ids, in the order added
_IDS = set()

LETTERS = "abcdefghijklmnopqrstuvwxyz'’"
W = "[a-z'’]"          # a lowercase word character (use inside (?-i:...) so capitals never match)
START = r"(?:^|[.!?]\s+)"   # a sentence start; the pattern is compiled with (?im)


def upper_first(s):
    return s[:1].upper() + s[1:]


def _expand(rep, m):
    return re.sub(r'\$\{(\w+)\}', lambda g: m.group(g.group(1)) or '', rep)


def simulate(pattern, replacement, text):
    """Apply a rule the way engine/src/lib.rs does: the target is replaced, case matched to it, a sentence start
    capitalized. Returns (new text, number of matches)."""
    rx = re.compile(pattern)
    out, last, hits = [], 0, 0
    for m in rx.finditer(text):
        s, e = m.span('target')
        orig = m.group('target')
        rep = _expand(replacement, m)
        if 'moved' in rx.groupindex:
            # the words before `moved` are cut and the replacement follows it (engine/src/lib.rs, linked pair)
            out.append(text[last:s])
            out.append(text[m.start('moved'):m.end('moved')])
            out.append(rep)
            last = m.end('moved')
            hits += 1
            continue
        letters = [c for c in orig if c.isalpha()]
        if letters and len(letters) > 1 and all(c.isupper() for c in letters):
            rep = rep.upper()
        elif orig[:1].isupper():
            rep = upper_first(rep)
        before = text[:s].rstrip(' \t')
        if (before == '' or before[-1] in '.!?\n') and rep:
            rep = upper_first(rep)
        out.append(text[last:s])
        out.append(rep)
        last = e
        hits += 1
    out.append(text[last:])
    return ''.join(out), hits


def add(rid, pattern, replacement, category, confidence, reason, positive, negative, fixed, section=None, note=None):
    full = PREFIX + rid
    assert full not in _IDS, f'duplicate id {full}'
    _IDS.add(full)
    assert '(?P<target>' in pattern, full
    assert not re.search(r'\(\?[=!<]|\\[1-9]', pattern), f'{full}: lookaround or backreference'
    try:
        rx = re.compile(pattern)
    except re.error as e:
        raise SystemExit(f'{full}: bad pattern: {e}')
    got, hits = simulate(pattern, replacement, positive)
    if hits < 1:
        raise SystemExit(f'{full}: the positive does not match: {positive!r}')
    if got != fixed:
        raise SystemExit(f'{full}: positive gives\n   {got!r}\nexpected\n   {fixed!r}')
    if rx.search(negative):
        raise SystemExit(f'{full}: the negative matches: {rx.search(negative).group(0)!r} in {negative!r}')
    if rx.search(fixed):
        raise SystemExit(f'{full}: the corrected sentence matches again: {fixed!r}')
    if len(negative.split('. ')) < 2 and len(negative) < 30:
        raise SystemExit(f'{full}: negative too thin')
    RULES.append({
        'id': full, 'pattern': pattern, 'replacement': replacement, 'category': category,
        'confidence': confidence, 'reason': reason, 'provenance': 'parzr original rule',
        'positive': positive, 'negative': negative,
    })
    FIXED[full] = fixed
    if section:
        COVER.append((section, note or reason, full))
        SECTIONS.setdefault(section, []).append(full)


FIXED = {}


def cross_check():
    """No rule may match another rule's negative or any corrected sentence (those are correct text)."""
    bad = 0
    compiled = [(r['id'], re.compile(r['pattern'])) for r in RULES]
    texts = [(r['id'] + ' negative', r['negative']) for r in RULES] + [(rid + ' fixed', t) for rid, t in FIXED.items()]
    for label, text in texts:
        for rid, rx in compiled:
            if rx.search(text) and not label.startswith(rid + ' '):
                print(f'CROSS: {rid} matches the {label}: {rx.search(text).group(0)!r}')
                bad += 1
    return bad


def not_in(words):
    """A regex for one lowercase word that is none of `words` (the engine's regex has no lookahead, so the
    exclusion is spelled as a trie). Use inside (?-i:...) so a capitalized word never matches."""
    words = sorted({w.lower() for w in words})

    def build(prefix_len, ws):
        children = {}
        terminal = False
        for w in ws:
            if w == '':
                terminal = True
            else:
                children.setdefault(w[0], []).append(w[1:])
        alts = []
        for c in sorted(children):
            alts.append(re.escape(c) + build(prefix_len + 1, children[c]))
        rest = ''.join(ch for ch in LETTERS if ch not in children)
        if rest:
            alts.append(f'[{rest}]{W}*')
        if not terminal and prefix_len > 0:
            alts.append('')
        return '(?:' + '|'.join(alts) + ')'

    return build(0, words)


def any_word():
    return f'(?-i:{W}+)'


def alt(words):
    return '(?:' + '|'.join(re.escape(w) if not re.search(r"[ ']", w) else w.replace(' ', r'\s+') for w in words) + ')'
