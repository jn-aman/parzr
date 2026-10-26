"""Shared builders for the redundancy pack (pleonasms, tautologies, doubled prepositions and negatives).

Every rule is checked as it is added: the positive example must match, the negative must not, the id must be unique,
and the corrected positive is recorded in EXPECTED so the engine run can confirm the edit end to end."""
import re

PREFIX = 'redund.'
RULES = []
IDS = set()
EXPECTED = {}
ERRORS = []
COVER = []  # (section, construction, ids) rows for the coverage document
NOTES = []  # (section, text) rows for the "left out" part of the coverage document

# A word boundary that also refuses a hyphen or apostrophe: "back-end", "free gift's" and "non-free gift" never match.
S = r"(?:^|[^\w'’-])"
E = r"(?:[^\w'’-]|$)"
# A previous word that is neither "a" nor "an": for rules that delete the first word of a pair, so the article that
# agrees with the first word ("an end result") is handled by its own rule and never left behind ("an result").
PW = r"(?:[^\W\d_]{3,}|[b-z]|a[^n\W\d_]|[b-z][^\W\d_])"
NOT_AN = rf"(?:^|[^\w'’\s-]\s*|\b{PW}\s+)"

VOWELS = set('aeiou')
VOWEL_EXC = {'hour', 'honest', 'honour', 'honor', 'heir'}
CONS_EXC = {'one', 'once', 'user', 'unique', 'uni', 'union', 'use', 'used', 'useful', 'european', 'eu', 'unit', 'usual'}


def vowel_sound(word):
    w = word.lower()
    if w in VOWEL_EXC:
        return True
    if w in CONS_EXC or w.startswith(('uni', 'use', 'usu', 'eu', 'one', 'unanim', 'utensil', 'uranium', 'ubiq')):
        return False
    return w[0] in VOWELS


def add(rid, pattern, repl, cat, conf, reason, pos, neg, modes=None):
    full = PREFIX + rid
    if full in IDS:
        ERRORS.append(f'duplicate id {full}')
        return full
    try:
        rx = re.compile(pattern)
    except re.error as e:
        ERRORS.append(f'{full}: bad pattern {e}')
        return full
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


def note(section, text):
    NOTES.append((section, text))


def style(rid, body, repl, conf, reason, pos, neg, pre=S, post=E, cat='Style'):
    """A rule whose edit is the group `target` inside `body`; the pattern is wrapped in the word guards."""
    return add(rid, f'(?im){pre}(?P<target>{body}){post}', repl, cat, conf, reason, pos, neg)


def reason_for(phrase, keep, extra=''):
    return f'“{phrase}” says the same thing twice: “{keep}” is enough.{extra}'


def pair(rid, lead, keep, pos, neg, conf=0.78, phrase=None, kshow=None, plural=True, reason=None, art_pos=None,
         cat='Style', post=E, mass=False):
    """lead + keep, where `lead` is redundant: "free gift" to "gift". A trailing "s" on the keep word is accepted
    (and kept). When deleting the lead would leave the wrong article ("an end result" -> "an result"), a second rule
    "<rid>_art" fixes the article too (`art_pos` is its positive) and the main rule never fires after "a"/"an"."""
    phrase = phrase or f'{lead} {keep}'
    kshow = kshow or keep
    kre = keep + ('s?' if plural else '')
    reason = reason or reason_for(phrase, kshow)
    first = lead.split()[0].split('|')[0].strip('(?:')
    if mass or vowel_sound(first) == vowel_sound(keep.split('|')[0]):
        return [add(rid, f'(?im){S}(?P<target>(?:{lead}) (?P<k>{kre})){post}', '${k}', cat, conf, reason, pos, neg)]
    if art_pos is None:
        ERRORS.append(f'{PREFIX}{rid}: the article changes with the lead word: give art_pos')
        return []
    old = 'an' if vowel_sound(first) else 'a'
    new = 'a' if old == 'an' else 'an'
    return [
        add(rid + '_art', f'(?im){S}(?P<target>{old} (?:{lead}) (?P<k>{kre})){post}', f'{new} ${{k}}', cat, conf,
            reason + ' The article changes with it.', art_pos, neg),
        add(rid, f'(?im){NOT_AN}(?P<target>(?:{lead}) (?P<k>{kre})){post}', '${k}', cat, conf, reason, pos, neg),
    ]


def verb(rid, base, particle, pos, neg, conf=0.78, phrase=None, kshow=None, forms='(?:s|ed|ing)?', reason=None, extra='',
         cat='Style', guard=None):
    """verb + redundant particle: "return back" -> "return" (any inflection of the verb is kept as typed)."""
    phrase = phrase or f'{base} {particle}'
    reason = reason or reason_for(phrase, kshow or base)
    pat = f'(?im){S}(?P<target>(?P<v>{base}{forms}) {particle}){guard or E}'
    return add(rid, pat, '${v}', cat, conf, reason, pos, neg)


# What may follow a pair that could also be the start of a compound noun ("free gift card", "free gift wrapping"): the
# rule fires only when the phrase ends or a function word follows.
AFTER = (r"(?:[^\w'’\s-]|\s*$|\s+(?:and|or|but|with|to|for|when|if|is|was|are|were|that|which|from|in|on|of|at|by|as|so|"
         r"than|will|would|can|could|has|had|have|you|your|they|we|I|it|the|a|an|this|these|those|once|after|before|during|"
         r"while|because|until|since)\b)")


def keep_first(rid, keep, drop, pos, neg, conf=0.78, phrase=None, reason=None, post=E, cat='Style', kre=None):
    """keep + redundant trailing word: "whole entire" -> "whole"."""
    phrase = phrase or f'{keep} {drop}'
    reason = reason or reason_for(phrase, keep)
    return add(rid, f'(?im){S}(?P<target>(?P<k>{kre or keep}) {drop}){post}', '${k}', cat, conf, reason, pos, neg)

AFTER_NOOF = AFTER.replace('|of|', '|')
