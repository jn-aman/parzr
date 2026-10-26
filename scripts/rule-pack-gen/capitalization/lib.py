"""Shared helpers for the capitalization pack generator.

A rule is a lowercase (or half-capitalized) spelling of a proper noun, brand or acronym and the right spelling. The
engine's own gazetteer (engine/rules/proper-nouns.txt) already fixes most places, languages, holidays and brands that
are never ordinary words; the pack adds the rest. Rule edits are case-only, so they pass the name guard.
"""
import itertools
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[3]
OUT = ROOT / 'engine/rules/packs/capitalization-rules.json'

RULES = []
IDS = set()
COVERAGE = []  # (family, description, ids)

PROV = 'parzr original rule'

# The word may follow a space or an opening parenthesis, or open the sentence; it may not follow a path character,
# "#", "@", "." or "_" (a hashtag, a handle, a file name), nor a quote or a square bracket (a JSON key, a TOML table).
LEFT = r'(?:^|[\s(])'
# A name that starts with a lowercase letter ("eBay", "iOS") must not open a sentence: the engine forces a capital
# there. Needs a word or a comma before it.
LEFT_MID = r'(?:[A-Za-z0-9,;] )'
# After the word: a space or mark, a possessive, the sentence's end.  Not "_", "." plus a letter, "/" or "@".
RIGHT = r"(?:['’]s)?(?:[\s,;:!?)\]\"”’]|\.(?:\s|$)|$)"
# Names that are also written with a hyphen as a modifier ("poland-based", "london-style").
RIGHT_H = r"(?:['’]s)?(?:[\s,;:!?)\]\"”’]|\.(?:\s|$)|-[a-z]|$)"
# Technical words stay lowercase in a package name, a flag or a config key, so no hyphen and no colon after them.
RIGHT_T = r"(?:['’]s)?(?:[\s,;!?)\]\"”’]|\.(?:\s|$)|$)"


GAZ = set()
for _line in (ROOT / 'engine/rules/proper-nouns.txt').read_text().splitlines():
    if _line and not _line.startswith('#'):
        GAZ.add(_line.lower())


# Families dropped after the everyday gate: the owner's reference keeps "call mom", "the wifi", "Hello Ana, Hope you're well"
# and "login id" as typed, so a rule for them is a false alarm however formal the style guides are.
SKIP_PREFIX = ('caps.family.', 'caps.brand.wi_fi', 'caps.stray.after_greeting_', 'caps.stray.thank_you_after_comma',
               'caps.acr.id_prefix', 'caps.acr.id_noun')
SKIP = set()
_skip = pathlib.Path(__file__).resolve().parent / 'skipped-ids.txt'
if _skip.exists():
    SKIP = {l.split('#')[0].strip() for l in _skip.read_text().splitlines() if l.split('#')[0].strip()}


# Function words that may follow a name that is also a command or a module ("import json" is code, "convert it to json
# and send it" is prose): the list has no "as" and no "import", so "import numpy as np" and "from json import loads" stay.
FN_WORDS = ('and|or|but|for|with|to|from|on|at|in|inside|into|is|are|was|were|has|have|had|will|would|can|could|may|might|'
            'if|when|while|then|once|since|because|so|by|about|instead|again|first|too|also|now|today|tomorrow|tonight|'
            'later|please|anyway|before|after|until|that|which|who|last|next|this|yesterday|soon|earlier|just|only|every|'
            'each|over|than|via|per|all|both|still|already|always|never|really|the|a|an|our|your|my|their')
DEV_NOUNS = ('server|servers|cluster|clusters|database|databases|framework|library|libraries|project|projects|app|apps|'
             'application|applications|team|developer|developers|community|docs|documentation|tutorial|course|version|'
             'release|instance|instances|setup|stack|ecosystem|engineer|engineers|user|users|admin|admins|install|'
             'installation|node|nodes|job|jobs|pipeline|pipelines|plugin|plugins|dashboard|console|support|api|sdk|cli|'
             'file|files|data|format|response|responses|payload|payloads|object|objects|string|strings|schema|document|'
             'documents|output|input|parser|parsing|export|exports|template|templates|dump|body|array|arrays|key|keys|'
             'value|values|column|columns|row|rows|report|reports|table|tables|record|records|request|requests|'
             'syntax|code|script|scripts|service|services|endpoint|endpoints|config|configuration|bug|bugs|issue|issues')
RIGHT_DEV = (r"(?:['’]s)?(?:\s*[,;!?)\]\"”’]|\s*\.(?:\s|$)|\s*$|\s+(?:" + FN_WORDS + '|' + DEV_NOUNS + r")\b)")
# A word before a name that is also a module or tool: "use django", "built with firebase", "to json". Never "import".
FRAME_DEV = (r"(?i:\b(?:use|uses|used|using|with|in|on|via|for|the|a|an|our|your|my|their|his|her|and|or|like|of|learn|"
             r"learning|learned|about|than|by|to|from|into|between|plus|without|migrate to|switch to|switched to|moved to|"
             r"moving to|built with|built on|written in|running on|runs on|hosted on|deployed to|deployed on|deploy to|"
             r"deploy on|top of|instead of|convert|converts|converted|converting|parse|parses|parsed|parsing|export|"
             r"exports|exported|exporting|save|saves|saved|saving|read|reads|reading|write|writes|writing|send|sends|"
             r"sending|return|returns|returning|load|loads|loading|open|opens|opened|edit|edits|editing|generate|generates|"
             r"generated|generating|download|downloads|downloaded|downloading|upload|uploads|uploaded|uploading|attach|"
             r"attached|attaching|encode|encoded|decode|decoded|format|formatted|valid|invalid|raw|plain|nested|broken|"
             r"empty|large|small|big|new|old|this|that|these|those|any|some|every|each)\s+)")


def emit(rid, pattern, repl, cat, conf, reason, pos, neg, family=None):
    if rid in SKIP or rid.startswith(SKIP_PREFIX):
        return
    assert rid not in IDS, rid
    assert re.fullmatch(r'caps\.[a-z0-9_.]+', rid), rid
    IDS.add(rid)
    RULES.append({
        'id': rid, 'pattern': pattern, 'replacement': repl, 'category': cat, 'confidence': conf,
        'reason': reason, 'provenance': PROV, 'positive': pos, 'negative': neg,
    })
    if family:
        COVERAGE.append((family, rid))


def slug(s):
    return re.sub(r'[^a-z0-9]+', '_', s.lower()).strip('_')


def esc(s):
    """Regex-escape a literal (spaces and hyphens stay as they are; apostrophes are matched exactly as given)."""
    out = []
    for ch in s:
        if ch in '.+*?()[]{}|^$\\':
            out.append('\\' + ch)
        else:
            out.append(ch)
    return ''.join(out)


def variants(canon, lower_first_ok=True):
    """Every wrong casing of a phrase: each capitalized word of the canonical form either lower or Capitalized."""
    words = canon.split(' ')
    options = []
    for w in words:
        if w != w.lower():
            options.append([w, w.lower()])
        else:
            options.append([w])
    out = []
    for combo in itertools.product(*options):
        s = ' '.join(combo)
        if s != canon:
            out.append(s)
    return out


def neg_noise(lower):
    """Near misses every proper-noun rule must ignore: a file, a hashtag, a handle, an identifier, a URL."""
    s = slug(lower)
    return f'See {s}.csv, #{s}, @{s}_team, the {s}_id column and https://example.com/{s}.'


# First words that another rule of the pack (or the gazetteer) already fixes when typed lowercase: a phrase starting with
# one of them is shown in its half-capitalized form ("Eid mubarak") so its own rule is the one that fires.
HEADS = {'eid', 'vatican', 'nintendo', 'santa', 'easter', 'microsoft', 'google', 'apple', 'amazon', 'adobe', 'windows',
         'dar', 'jammu', 'kashmir', 'krishna', 'father', 'christmas', 'disney', 'photoshop', 'office', 'google', 'ho', 'pro'}


def shown_form(canon):
    """The wrong spelling shown in a rule's positive: all lowercase, or half-capitalized when the first word is one
    that another rule already fixes on its own."""
    words = canon.split(' ')
    if len(words) > 1 and (words[0].lower() in HEADS or words[0].lower() in GAZ):
        return ' '.join([words[0]] + [w.lower() for w in words[1:]])
    return canon.lower()


def phrase_rule(rid, canon, left, right, conf, reason, sentence, family, extra_neg='', cat='Capitalization', strict=False):
    """A name written in lowercase (or half lowercase): every wrong casing of `canon` in one rule.
    A name with an apostrophe gets a second rule for the curly apostrophe, so the writer's quotes are kept."""
    forms = [(canon, rid)]
    if "'" in canon:
        forms.append((canon.replace("'", "\u2019"), rid + '_curly'))
    for c, r in forms:
        # strict: only the all-lowercase spelling is an error (a descriptor like "river" or "prize" is often left
        # lowercase in careful writing: "Amazon river", "Nobel prize")
        alts = [c.lower()] if strict else variants(c)
        if not alts or alts == [c]:
            return
        while r in IDS:
            r += '_b'
        body = '|'.join(esc(x) for x in alts)
        pat = f'{left}(?P<target>(?-i:{body})){right}'
        shown = c.lower() if strict else shown_form(c)
        pos = sentence.format(x=shown)
        neg = sentence.format(x=c) + ' ' + neg_noise(c.lower()) + (' ' + extra_neg if extra_neg else '')
        emit(r, pat, c, cat, conf, reason, pos, neg, family)


def write():
    OUT.write_text('[\n' + ',\n'.join('  ' + json.dumps(r, ensure_ascii=False) for r in RULES) + '\n]\n')
    return len(RULES)
