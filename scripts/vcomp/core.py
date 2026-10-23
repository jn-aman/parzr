"""Builders and checks shared by the verb-complement tables (see ../gen-verb-complements.py)."""
import re, sys

RULES = []
LITS = {}
EXPECTED = {}
COVER = []
# Constructions the engine's own Rust passes already fix (so a regex here would only repeat them): rule id -> the
# base rule that covers it. The tables still list them; add() records the coverage and writes no rule.
BASE_COVERED = {
    'gerund.enjoy': 'grammar.gerund_complement', 'gerund.avoid': 'grammar.gerund_complement',
    'gerund.finish': 'grammar.gerund_complement', 'gerund.suggest': 'grammar.gerund_complement',
    'missingto.ought': 'grammar.missing_to', 'bare.lets_to': 'grammar.extra_to',
    'idiom.look_forward': 'grammar.prepositional_gerund', 'idiom.accustomed': 'grammar.prepositional_gerund',
    'idiom.opposed': 'grammar.prepositional_gerund',
}
IDS = set()

# ---------------------------------------------------------------- inflection

# Verbs that double their final consonant before -ing (stressed final syllable): base -> doubled letter.
DOUBLE = {
    'run': 'n', 'begin': 'n', 'win': 'n', 'plan': 'n', 'spin': 'n', 'swim': 'm', 'get': 't', 'put': 't', 'sit': 't',
    'set': 't', 'let': 't', 'cut': 't', 'hit': 't', 'quit': 't', 'forget': 't', 'submit': 't', 'permit': 't',
    'admit': 't', 'commit': 't', 'chat': 't', 'stop': 'p', 'shop': 'p', 'drop': 'p', 'skip': 'p', 'ship': 'p',
    'jog': 'g', 'plug': 'g', 'log': 'g', 'refer': 'r', 'prefer': 'r', 'occur': 'r', 'grab': 'b', 'beg': 'g',
}

def kind(v):
    """'p' plain +ing, 'e' drop the final e, 'd<L>' double the final consonant L."""
    if v in DOUBLE:
        return 'd' + DOUBLE[v]
    if v.endswith('e') and not v.endswith(('ee', 'ye', 'oe')) and v != 'be':
        return 'e'
    if v.endswith('ie'):
        raise ValueError(f'ie verb not supported: {v}')
    return 'p'

def gerund(v):
    k = kind(v)
    if k == 'p':
        return v + 'ing'
    if k == 'e':
        return v[:-1] + 'ing'
    return v + k[1] + 'ing'

def alt(words):
    return '|'.join(sorted(set(words), key=lambda w: (-len(w), w)))

def split(verbs):
    by = {}
    for v in verbs:
        by.setdefault(kind(v), []).append(v)
    return by

# ---------------------------------------------------------------- verb to gerund ("to read" -> "reading")

def b2g(verbs):
    """Alternation over base verbs and the replacement text that rebuilds the -ing form."""
    by = split(verbs)
    parts, repl = [], ''
    if 'p' in by:
        parts.append(f'(?P<gp>{alt(by["p"])})')
        repl += '${gp}'
    if 'e' in by:
        parts.append(f'(?P<ge>{alt(v[:-1] for v in by["e"])})e')
        repl += '${ge}'
    for k in sorted(by):
        if k.startswith('d'):
            L = k[1]
            parts.append(f'(?P<ga{L}>{alt(v[:-1] for v in by[k])})(?P<gz{L}>{L})')
            repl += f'${{ga{L}}}${{gz{L}}}${{gz{L}}}'
    return '(?:' + '|'.join(parts) + ')', repl + 'ing'

# ---------------------------------------------------------------- gerund to base ("going" -> "go")

def g2b(verbs):
    """Two (alternation, replacement-tail) pairs over -ing forms: plain/doubled, and silent-e."""
    by = split(verbs)
    main, mrepl, e, erepl = [], '', None, ''
    if 'p' in by:
        main.append(f'(?P<bp>{alt(by["p"])})ing')
        mrepl += '${bp}'
    for k in sorted(by):
        if k.startswith('d'):
            L = k[1]
            main.append(f'(?P<bd{L}>{alt(by[k])}){L}ing')
            mrepl += f'${{bd{L}}}'
    out = []
    if main:
        out.append(('(?:' + '|'.join(main) + ')', mrepl))
    if 'e' in by:
        out.append((f'(?P<be>{alt(v[:-1] for v in by["e"])})ing', '${be}e'))
    return out

# ---------------------------------------------------------------- word fragments

APOS = "[’']"
PRON = r"(?:I|we|you|they|he|she)(?:[’'](?:d|ll|ve))?"
ADV = r"(?:really|just|still|also|always|never|not|already|even|only|now|then|truly|actually|often|usually|probably|definitely|simply|quite|ever|much|both|all|highly|strongly|personally|kindly|generally|normally|certainly|honestly|well|surely|particularly)"
# A pronoun or auxiliary right before the verb: rules the noun use out ("a risk to", "a mind to").
PEOPLE = ("people|everyone|everybody|someone|somebody|nobody|anyone|anybody|users|students|children|kids|customers|friends|"
          "parents|teachers|workers|employees|managers|players|doctors|companies|governments")
P1 = (r"\b(?:" + PRON + r"|who|please|let[’']s|" + PEOPLE + r"|will|would|can|could|should|shall|may|might|must|do|does|did|don[’']t|doesn[’']t|"
      r"didn[’']t|won[’']t|wouldn[’']t|can[’']t|couldn[’']t|shouldn[’']t|cannot)\s+(?:" + ADV + r"\s+)*")
# P1 without "you" as the subject: "what you want you get" is a relative clause, not an object plus a verb.
P1_NY = P1.replace(PRON, r"(?:I|we|they|he|she)(?:[’'](?:d|ll|ve))?")
SUBJ = (r"\b(?:" + PRON + r"|who|" + PEOPLE + r")\s+(?:" + ADV + r"\s+)*")
SUBJ_IT = (r"\b(?:" + PRON + r"|who|" + PEOPLE + r"|it|this|that|there|which|things)\s+(?:" + ADV + r"\s+)*")
BE = (r"\b(?:I[’']m|I am|you[’']re|you are|we[’']re|we are|they[’']re|they are|he[’']s|he is|she[’']s|she is|am|is|are|was|were|be|been|being|"
      r"isn[’']t|aren[’']t|wasn[’']t|weren[’']t)"
      r"\s+(?:" + ADV + r"\s+)*")
# Before a base-form governor: a pronoun or auxiliary, "to", an opening imperative, or a connective ("is recommend
# to" is a missing -ed, not a base form, so "is" is not among them).
PRE_BASE = (r"(?:" + P1 + r"|\bto\s+(?:" + ADV + r"\s+)*|(?:^|[.!?]\s+)(?:" + ADV + r"\s+)*|"
            r"\b(?:please|kindly|never|always|also|and|or|but|then|just|not)\s+)")
DET = r"(?:the|a|an|my|your|his|her|our|their|him|them|us|me|you|it)"

def notword(words):
    """Regex for one whole word that is not one of `words` (no lookahead in the engine's regex crate)."""
    words = [w.lower() for w in words]
    def node(prefix):
        kids = sorted({w[len(prefix)] for w in words if w.startswith(prefix) and len(w) > len(prefix)})
        terminal = prefix in words
        alts = []
        if prefix and not terminal:
            alts.append(r'\b')
        if kids:
            cls = ''.join(k + k.upper() for k in kids)
            alts.append(rf'[^{cls}\W\d_]\w*')
            for k in kids:
                sub = node(prefix + k)
                alts.append(f'[{k}{k.upper()}](?:{sub})')
        if terminal:
            alts.append(r'\w+')
        return '|'.join(alts)
    return '(?:' + node('') + r')\b'

CONJ = notword(['and', 'or', 'but', 'nor', 'then', 'plus'])
# What may follow a converted verb: the end of the sentence, or any word except a coordinator ("to read and write"
# would become "reading and write", a half-fix).
AFTER = r"(?:\s*[.!?;:)]|\s*$|\s+" + CONJ + ")"

# ---------------------------------------------------------------- python mirror of the engine's replacement

def expand(repl, m):
    return re.sub(r'\$\{(\w+)\}', lambda g: m.group(g.group(1)) or '', repl)

def apply(rx, repl, text):
    """Apply a rule once, the way the engine does for a lowercase span."""
    m = rx.search(text)
    if not m:
        return None
    t = m.start('target') if 'target' in rx.groupindex else m.start()
    e = m.end('target') if 'target' in rx.groupindex else m.end()
    return text[:t] + expand(repl, m) + text[e:]

# ---------------------------------------------------------------- registry

ERRORS = []

class Skip(Exception):
    pass

def fail(rid, msg):
    ERRORS.append(f'RULE {rid}: {msg}')
    raise Skip()

def add(*a, **k):
    try:
        _add(*a, **k)
    except Skip:
        pass

def _add(rid, pattern, repl, reason, positive, expected, negative, lits, conf=0.92, cat='Grammar', cover=None,
         flags='(?im)'):
    if rid in BASE_COVERED:
        COVER.append(('vcomp.' + rid, 'covered by base rule ' + BASE_COVERED[rid]))
        return
    rid = 'vcomp.' + rid
    if rid in IDS:
        fail(rid, 'duplicate id')
    IDS.add(rid)
    full = flags + pattern
    try:
        rx = re.compile(full)
    except re.error as e:
        fail(rid, f'pattern does not compile: {e}')
    if '(?P<target>' not in full:
        fail(rid, 'no target group')
    got = apply(rx, repl, positive)
    if got != expected:
        fail(rid, f'positive gives {got!r}, expected {expected!r}')
    if expected == positive:
        fail(rid, 'no change')
    if rx.search(negative):
        fail(rid, f'negative matches: {rx.search(negative).group(0)!r}')
    n = len(rx.findall(positive))
    if n != 1:
        fail(rid, f'positive matches {n} times')
    if not any(l.lower() in positive.lower() for l in lits):
        fail(rid, 'no required word of the rule occurs in the positive')
    RULES.append({
        'id': rid, 'pattern': full, 'replacement': repl, 'category': cat, 'confidence': conf, 'reason': reason,
        'provenance': 'parzr original rule', 'positive': positive, 'negative': negative,
    })
    LITS[rid] = [l.lower() for l in lits]
    EXPECTED[rid] = expected
    COVER.append((rid, cover or ''))

def finish():
    if ERRORS:
        print('\n'.join(ERRORS), file=sys.stderr)
        print(f'{len(ERRORS)} rule(s) failed their own checks', file=sys.stderr)
        raise SystemExit(1)
    return RULES


def governor_lead(base='', s='', ing='', ed='', mode='free'):
    """Regex for "governor + space" with the context that rules out the noun, passive and relative-clause uses.
    mode 'free': -s and -ing forms stand alone, the base form needs PRE_BASE, the -ed form needs P1.
    mode 'p1': base, -s and -ed need P1 (the word is also a noun or an intransitive verb), -ing needs BE or P1."""
    parts = []
    def w(x):
        return alt(x.split())
    if mode == 'free':
        if s or ing:
            parts.append(r'\b(?:%s)\s+' % w(s + ' ' + ing))
        if base:
            parts.append(PRE_BASE + r'(?:%s)\s+' % w(base))
    else:
        if base or s:
            parts.append(P1 + r'(?:%s)\s+' % w(base + ' ' + s))
        if ing:
            parts.append(r'(?:' + BE + '|' + P1 + r')(?:%s)\s+' % w(ing))
    if ed:
        parts.append(P1 + r'(?:%s)\s+' % w(ed))
    return '(?:' + '|'.join(parts) + ')'


NEXT_WORDS = ("to the a an my your his her our their this that these those it them him us me you there here home out up "
              "down back away off on in at for with from by about over around into more some any all again now soon "
              "too also so if whether how what where when why who which together abroad outside inside somewhere "
              "anywhere tomorrow today tonight later early first")
# What may follow a bare verb that was missing its "to": a function word or the end of the clause. A noun right after
# ("need read access", "want call forwarding") would make the verb a noun modifier, so those are left alone.
NEXT_K = r"(?:\s*[.!?;:,)]|\s*$|\s+(?:" + alt(NEXT_WORDS.split()) + r")\b)"


# The start of a clause: "do all they can to help" (a modal that stands for the whole verb phrase) is not a start,
# "I think you can to go" is.
CLAUSE = (r"(?:^|[.!?;:,]\s*|\b(?:and|but|or|so|because|then|maybe|perhaps|also|now|yes|no|well|ok|okay|thanks|please)\s+|"
          r"\b(?:think|thought|know|knew|believe|believed|hope|hoped|guess|say|said|sure|feel|felt|see|hear)\s+(?:that\s+)?)")
