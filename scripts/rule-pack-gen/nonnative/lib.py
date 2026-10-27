"""Shared helpers for the non-native-transfer pack generator (id prefix `l1.`). Each rule is verified as it is built:
its positive must become exactly the stated correction (a Python emulation of the engine's single edit, including its
case matching: a capitalized or sentence-initial target gets a capitalized replacement) and its negative, one or more
correct sentences, must not match the pattern at all."""
import json, re

RULES = []
IDS = set()
PROVENANCE = 'parzr original rule'


def expand(repl, m):
    return re.sub(r'\$\{(\w+)\}', lambda g: m.group(g.group(1)) or '', repl)


def upper_first(s):
    return s[:1].upper() + s[1:]


def match_case(rep, orig):
    letters = [c for c in orig if c.isalpha()]
    if letters and all(c.isupper() for c in letters) and len(letters) > 1:
        return rep.upper()
    if orig[:1].isupper():
        return upper_first(rep)
    return rep


def starts_sentence(text, i):
    before = text[:i].rstrip(' \t')
    return before == '' or before.endswith(('.', '!', '?', '\n'))


def apply(rule, text):
    rx = re.compile(rule['pattern'])
    m = rx.search(text)
    if not m:
        return None
    rep = expand(rule['replacement'], m)
    if 'moved' in rx.groupindex and m.group('moved') is not None:
        ts = m.start('target')
        return text[:ts] + text[m.start('moved'):m.end('moved')] + rep + text[m.end('moved'):]
    if 'target' in rx.groupindex:
        a, b = m.start('target'), m.end('target')
    else:
        a, b = m.start(), m.end()
    orig = text[a:b]
    if orig != 'I':
        rep = match_case(rep, orig)
    if starts_sentence(text, a) and rep:
        rep = upper_first(rep)
    return text[:a] + rep + text[b:]


def R(rid, pattern, repl, category, conf, reason, pos, expected, neg):
    rid = 'l1.' + rid
    assert rid not in IDS, 'duplicate id ' + rid
    assert '(?P<target>' in pattern, rid
    rule = {
        'id': rid, 'pattern': pattern, 'replacement': repl, 'category': category, 'confidence': conf,
        'reason': reason, 'provenance': PROVENANCE, 'positive': pos, 'negative': neg,
    }

    try:
        got = apply(rule, pos)
        rx = re.compile(pattern)
    except re.error as e:
        ERRORS.append(f'{rid}: bad pattern: {e}')
        return None
    if got != expected:
        ERRORS.append(f'{rid}: positive gave {got!r}, wanted {expected!r}')
    bad = rx.search(neg)
    if bad is not None:
        ERRORS.append(f'{rid}: negative matches {bad.group(0)!r} in {neg!r}')
    if expected == pos:
        ERRORS.append(f'{rid}: expected equals positive')
    IDS.add(rid)
    RULES.append(rule)
    EXPECT[rid] = expected
    return rule


EXPECT = {}
ERRORS = []


def held(rid, prefixes):
    return any(rid == p or rid.startswith(p + '.') for p in prefixes)


def dump(path, expect_path=None, held_path=None, held_prefixes=()):
    # The Indian-English register families run in the Professional rewrite only (modes), where
    # the owner asks for business English; Fix leaves them as typed.
    for r in RULES:
        if held(r['id'], held_prefixes):
            r['modes'] = ['professional']
    active = list(RULES)
    parked = [r for r in RULES if held(r['id'], held_prefixes)]
    for target, rules in ((path, active), (held_path, parked)):
        if not target:
            continue
        with open(target, 'w', encoding='utf-8') as f:
            f.write('[\n')
            for i, r in enumerate(rules):
                f.write('  ' + json.dumps(r, ensure_ascii=False) + (',\n' if i < len(rules) - 1 else '\n'))
            f.write(']\n')
    if expect_path:
        with open(expect_path, 'w', encoding='utf-8') as f:
            json.dump({r['id']: EXPECT[r['id']] for r in active}, f, ensure_ascii=False, indent=0)
    return len(active), len(parked)
