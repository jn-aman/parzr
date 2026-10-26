"""Shared builders for the modifiers pack (adjectives, adverbs, comparatives, negation): see ../gen-modifiers.py.

Every rule is checked as it is added: the positive example must match, the negative must not, the id must be unique,
and the corrected positive is recorded in EXPECTED so the engine run can confirm the edit end to end."""
import re

PREFIX = 'mod.'
RULES = []
IDS = set()
EXPECTED = {}
ERRORS = []
COVER = []  # (section, construction, ids or note) rows for the coverage document

# End of a clause: punctuation or the end of the text. The adverb or adjective being judged is the last word of the
# clause, so a following noun (which would make it an attributive adjective) can never be there.
END = r"(?:[.!?,;:)\n\"”]|\s*$)"
# Words that may follow a manner adverb inside the clause without making the word before them a modifier of a noun.
TAIL_WORDS = ("on|in|at|for|with|to|but|too|now|today|here|there|yesterday|again|since|when|every|after|before|"
              "until|though|so|as|during|while|because|if|than|from|by|like|last|this|tonight|tomorrow")


def alt(words):
    return '|'.join(sorted(set(words), key=lambda w: (-len(w), w)))


def tail(words=TAIL_WORDS):
    return rf"(?:[.!?,;:)\n\"”]|\s*$|\s+(?:{words})\b)"


def add(rid, pattern, repl, cat, conf, reason, pos, neg, modes=None):
    full = PREFIX + rid
    if full in IDS:
        ERRORS.append(f'duplicate id {full}')
        return full
    rx = re.compile(pattern)
    m = rx.search(pos)
    if not m:
        ERRORS.append(f'{full}: positive does not match: {pos!r}')
        return full
    if rx.search(neg):
        ERRORS.append(f'{full}: negative matches: {rx.search(neg).group(0)!r} in {neg!r}')
        return full
    t = m.group('target')
    rep = re.sub(r'\$\{(\w+)\}', lambda g: m.group(g.group(1)) or '', repl)
    if rep == t:
        ERRORS.append(f'{full}: replacement equals the target')
        return full
    EXPECTED[full] = pos[:m.start('target')] + rep + pos[m.end('target'):]
    IDS.add(full)
    rule = {
        'id': full, 'pattern': pattern, 'replacement': repl, 'category': cat, 'confidence': conf,
        'reason': reason, 'provenance': 'parzr original rule', 'positive': pos, 'negative': neg,
    }
    if modes:
        rule['modes'] = modes
    RULES.append(rule)
    return full


def cover(section, construction, ids):
    COVER.append((section, construction, ids))


def pick(options, key):
    """A deterministic choice from a list of example sentences, so generated rules do not all read the same."""
    return options[sum(map(ord, key)) % len(options)]
