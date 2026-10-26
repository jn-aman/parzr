"""Shared builders for the nouns-plurals pack (see build.py).

Every rule is checked as it is added: the positive example must match, the negative must not, the id must be unique
(here and against the base rules and the other packs), and the corrected positive is recorded in EXPECTED so the
engine run (e2e.py) can confirm the edit end to end."""
import json, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parents[2]
PREFIX = 'noun.'
RULES, EXPECTED, ERRORS, COVER = [], {}, [], []
IDS = set()


def existing_ids():
    out = set()
    for f in [ROOT / 'engine/rules/grammar.json', ROOT / 'engine/rules/tone.json', ROOT / 'engine/rules/usage.json',
              *sorted((ROOT / 'engine/rules/packs').glob('*.json'))]:
        if f.name == 'nouns-plurals.json':
            continue
        out |= {r['id'] for r in json.loads(f.read_text())}
    return out


OTHER_IDS = existing_ids()

# End of a clause or a word that cannot start a noun phrase: after a noun it proves the noun ends its phrase.
FUNC = ("to|in|on|at|for|from|with|about|that|which|who|are|were|have|had|will|would|can|could|should|must|may|might|"
        "do|did|so|because|when|since|after|before|during|like|than|as|too|now|today|here|there|again|ago|but")
T1 = rf"(?:\s*[,.;:!?)\"”]|\s*$|\s+(?:{FUNC})\b)"
# The same without the prepositions that can also open a modifier phrase.
BOUND = r"(?:\s*[,.;:!?)\"”]|\s*$)"
NUMD = r"(?:[2-9]|[1-9]\d+|\d{1,3}(?:,\d{3})+|\d+\.\d+)"
NUMW = ("(?:two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|"
        "eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|million|billion|dozen)")
NUM = rf"(?:{NUMD}|{NUMW})"
# What may stand before a number that has no preceding word of its own in the pattern: the start of the text, an opening
# mark, or a word. A slash before the number ("1 / 4 mile", "3/4 hour") makes it a fraction, which is not plural.
LEAD = r"(?:^|[(\"“'\[,;:]\s*|[^\s/(\"“'\[,;:]\s+)"


def alt(words):
    return '|'.join(sorted(set(words), key=lambda w: (-len(w), w)))


def add(rid, pattern, repl, cat, conf, reason, pos, neg, fam=None):
    full = PREFIX + rid
    if full in IDS or full in OTHER_IDS:
        ERRORS.append(f'duplicate id {full}')
        return full
    try:
        rx = re.compile(pattern)
    except re.error as e:
        ERRORS.append(f'{full}: bad pattern: {e}')
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
    RULES.append({'id': full, 'pattern': pattern, 'replacement': repl, 'category': cat, 'confidence': conf,
                  'reason': reason, 'provenance': 'parzr original rule', 'positive': pos, 'negative': neg})
    return full


def word_rule(slug, wrong, right, conf, cat, reason, pos, neg):
    """A non-word or plainly wrong plural that is wrong wherever it stands: \\bwrong\\b -> right."""
    return add(slug, rf"(?i)\b(?P<target>{wrong})\b", right, cat, conf, reason, pos, neg)


def cover(section, construction, ids):
    COVER.append((section, construction, ids))

# Words after which the next noun can only be plural.
PQ = (rf"(?:{NUMD}|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|dozens of|hundreds of|thousands of|many|"
      r"several|both|numerous|various|multiple|few|these|those|lots of|a lot of|a few|countless|how many|so many|too many)")
# After a determiner a bare "-s" noun may be a possessive typed without its apostrophe, so only a verb, a conjunction
# or the end of the clause proves it is a plural.
AUX = (r"(?:\s*[,.;:!?)\"”]|\s*$|\s+(?:are|were|have|had|will|can|could|would|should|must|do|did|who|that|which|of|"
       r"and|but|or)\b)")


def plural_pair(slug, wrong, right, conf, pq_pos, pq_neg, t_pos, t_neg, dets=r"the|our|their|some|other|more|most|any|no|your|his|her|my", cat='Grammar'):
    """A wrong -s plural of an irregular noun (knifes, wolfs, wifes ...). The wrong form is also a possessive typed
    without its apostrophe and, for some, a verb, so it is flagged after a plural-forcing quantifier (rule _n) or after
    a determiner when a verb or the clause end follows (rule _t)."""
    reason = f'“{wrong.capitalize()}” is not the plural here: say “{right}”.'
    add(f'irreg.{slug}_n', rf"(?i)\b{PQ}\s+(?P<target>(?-i:{wrong}))\b", right, cat, conf, reason, pq_pos, pq_neg)
    add(f'irreg.{slug}_t', rf"(?i)\b(?:{dets})\s+(?P<target>(?-i:{wrong})){AUX}", right, cat, conf - 0.04, reason, t_pos, t_neg)
