"""Shared helpers for the clarity pack generator: rule records, expected texts and the coverage map."""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
PROV = 'parzr original rule'
RULES = []      # rule dicts, in file order
EXPECTED = {}   # rule id -> the whole text the engine must return for the positive
COVER = []      # (section, construction, [rule ids])
_cur = {'sec': '', 'cons': None, 'ids': []}


def q(s):
    return '“' + s + '”'


def section(name):
    flush()
    _cur['sec'] = name


def construction(text):
    flush()
    _cur['cons'] = text


def flush():
    if _cur['cons'] and _cur['ids']:
        COVER.append((_cur['sec'], _cur['cons'], list(_cur['ids'])))
    _cur['cons'] = None
    _cur['ids'] = []


def add(rid, pattern, repl, conf, reason, pos, exp, neg):
    rid = 'clarity.' + rid
    assert rid not in EXPECTED, rid
    # Concise mode only: these rewrite correct, wordy sentences, which Fix (corrections) must leave alone.
    RULES.append({'id': rid, 'pattern': pattern, 'replacement': repl, 'modes': ['concise'], 'category': 'Style',
                  'confidence': conf, 'reason': reason, 'provenance': PROV, 'positive': pos, 'negative': neg})
    EXPECTED[rid] = exp
    _cur['ids'].append(rid)


def phrase(body, follow=''):
    """A whole-word phrase rule whose edited span is the phrase."""
    return '(?i)\\b(?P<target>%s)\\b%s' % (body, follow)


def sw(rid, body, repl, conf, reason, pos, exp, neg, follow=''):
    add(rid, phrase(body, follow), repl, conf, reason, pos, exp, neg)


def join(a, b):
    """a + b with one space unless b starts with punctuation."""
    return a + ('' if b[:1] in '.,;:!?' else ' ') + b


# What may follow a phrase that must end a clause or lead into a clause: punctuation, the end of the text or
# a small word list. "make a decision tree" and "make a decision-making plan" never match.
FOLLOW = ('(?:\\s*[.;:!?)"”’\\n]|\\s*,\\s+(?:and|but|then|so|or|after|before|once|when|while)\\b|\\s*$|\\s+(?:about|on|to|regarding|whether|between|that|if|for|based|soon|now|'
          'today|quickly|later|first|and|or|when|before|after|as|with|from|within|together|here|there|then|again|once|'
          'until|because|but|so|yet)\\b)')

# A noun phrase must follow a "to" that ends the phrase ("provide assistance to the staff"), never a verb
# ("find a solution to make it work").
DETF = ('\\s+(?:the|a|an|this|that|these|those|our|my|your|his|her|their|its|all|any|each|every|them|us|you|him|me|everyone|anyone|'
        'people|students|staff|users|customers|families|children|patients|nations|countries|members|employees|residents|clients|'
        'workers|teachers|parents|others)\\b')
