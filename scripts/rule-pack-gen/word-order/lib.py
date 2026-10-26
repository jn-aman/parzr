"""Shared helpers for the word-order pack generator: rule construction with a Python emulation of the engine's edit
(replace the `target` group, or the two-edit `moved` move) so every generated rule is verified as it is built: its
positive must become exactly the stated correction and its negative must not match at all."""
import json, re

RULES = []
IDS = set()

# A sentence start (optionally after an opening quote): "Where he works?" at the head of a sentence.
SS = r'(?:^|[.!?:]["”’)]*\s+)["“‘(]?'
# Where a clause may begin: sentence start, punctuation, or a conjunction/verb that introduces one.
CS = (r'(?:^|[.!?,;:]["”’)]*\s+|\b(?:and|but|because|if|when|so|while|since|as|though|although|then|yet|or|'
      r'think|thinks|thought|know|knows|knew|say|says|said|believe|hope|guess|feel|bet|suppose)\s+)')
# Question words that open a direct question (the part before the subject).
WHQ = (r'(?:what time|what else|what|where|when|why|who|whom|'
       r'how(?: (?:much|long|often|far|soon|fast|well|old))?)')
# Words that introduce an embedded question after "I know / tell me / wonder ...".
ASK = (r'(?:know|knows|knew|tell|tells|told|ask|asks|asked|asking|wonder|wonders|wondered|wondering|sure|idea|clue|'
       r'remember|remembered|forget|forgot|explain|explained|understand|see|find out|found out|figure out|'
       r'figured out|decide|decided|curious|show|showed|learn|learned|check|guess|imagine|care|mind|notice|'
       r'realize|realise|doubt|inquire|enquire|describe|discover|determine|confirm)')
ASKOBJ = r'(?: (?:me|us|him|her|them|you))?'
# The wh part of an embedded question, with "if" and "whether".
WHX = (r'(?:what time|how (?:much|many|long|often|far|old|soon|fast)|what|where|when|why|how|who|whom|if|whether)')


def subst(template, **frags):
    out = template
    for k, v in frags.items():
        out = out.replace('<<' + k + '>>', v)
    assert '<<' not in out, out
    return out


def py_pattern(pattern):
    """The Rust pattern as Python re (same syntax for what the packs use)."""
    return re.compile(pattern)


def expand(repl, m):
    return re.sub(r'\$\{(\w+)\}', lambda g: m.group(g.group(1)) or '', repl)


def apply(rule, text):
    """First match applied the way the engine applies it; None if no match."""
    rx = py_pattern(rule['pattern'])
    m = rx.search(text)
    if not m:
        return None
    rep = expand(rule['replacement'], m)
    if 'moved' in rx.groupindex and m.group('moved') is not None:
        t = m.group('target')
        ts = m.start('target')
        cut_end = m.start('moved')
        me = m.end('moved')
        return text[:ts] + text[cut_end:me] + rep + text[me:]
    t0, t1 = (m.start('target'), m.end('target')) if 'target' in rx.groupindex else (m.start(), m.end())
    return text[:t0] + rep + text[t1:]


def R(rid, pattern, repl, category, conf, reason, pos, expected, neg, moved=False):
    rid = 'order.' + rid
    assert rid not in IDS, 'duplicate id ' + rid
    rule = {
        'id': rid,
        'pattern': pattern,
        'replacement': repl,
        'category': category,
        'confidence': conf,
        'reason': reason,
        'provenance': 'parzr original rule',
        'positive': pos,
        'negative': neg,
    }
    got = apply(rule, pos)
    assert got == expected, f'{rid}: positive gave {got!r}, wanted {expected!r}'
    assert py_pattern(pattern).search(neg) is None, f'{rid}: negative matches: {py_pattern(pattern).search(neg).group(0)!r} in {neg!r}'
    IDS.add(rid)
    RULES.append(rule)
    return rule


def cap(s):
    return s[0].upper() + s[1:]


def dump(path):
    with open(path, 'w', encoding='utf-8') as f:
        f.write('[\n')
        for i, r in enumerate(RULES):
            f.write('  ' + json.dumps(r, ensure_ascii=False) + (',\n' if i < len(RULES) - 1 else '\n'))
        f.write(']\n')
