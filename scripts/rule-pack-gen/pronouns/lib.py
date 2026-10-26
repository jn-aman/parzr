"""Helpers for the pronouns pack generator (shared regex pieces, rule registry)."""
import json, re

RULES = []
IDS = set()
PROV = 'parzr original rule (pronouns pack)'

# Clause start: sentence start, after a stop, after a colon, after a comma (optionally "and/but/so/yet").
END = r'[.!?]["”’)]*'
CS = r'(?:^|' + END + r'\s+|[:;]\s+|,\s+(?:(?:and|but|so|yet)\s+)?)'
# Clause start plus the words after which a full clause begins ("because John and me went").
CONJ = ('yesterday|today|tonight|then|later|so|because|when|while|but|and|that|if|once|after|before|since|until|'
        'whenever|though|although|whereas|unless|whether|as soon as|last night|last week|last year|last weekend|'
        'this morning|this weekend|this week|this afternoon|this evening|earlier|afterwards|eventually|finally|recently')
CS2 = r'(?:^|' + END + r'\s+|[:;]\s+|,\s+(?:(?:and|but|so|yet)\s+)?|\b(?:' + CONJ + r')\s+)'
# Capitalised word that is a name (case-sensitive inside the (?i) rules).
NAME = r'(?:(?:Dr|Mr|Mrs|Ms|Mx|Prof)\.? )?(?-i:[A-Z][a-z]+)(?: (?-i:[A-Z][a-z]+))?'
NAME1 = r'(?-i:[A-Z][a-z]+)'
# A noun phrase used as first conjunct in "NP and I" / "NP and he".
POSS = r'(?:my|our|your|his|her|their)'
PERSON_N = (r'(?:wife|husband|partner|spouse|mother|father|mom|mum|dad|parents|parent|son|daughter|kids|kid|children|child|brother|sister|brothers|sisters|'
            r'family|cousin|cousins|uncle|aunt|grandma|grandpa|grandmother|grandfather|grandparents|friend|friends|boyfriend|girlfriend|fiance|fiancee|'
            r'roommate|roommates|colleague|colleagues|coworker|coworkers|neighbor|neighbors|neighbour|neighbours|boss|manager|team|teacher|teachers|'
            r'doctor|student|students|lawyer|assistant|baby|twin|twins|in-laws|crew|staff|group|class|club|committee|board|company)')
NP1P = r'(?:(?:' + POSS + r'|the) (?:[a-z]+ )?' + PERSON_N + r'|you|him|her|them)'      # a person, never a place
NP1 = r'(?:' + NAME + r'|' + NP1P + r')'                                                  # person or name
NP1N = r'(?:' + NAME + r'|(?:' + POSS + r'|the) (?:[a-z]+ )?' + PERSON_N + r')'
NP1W = r'(?:' + NAME + r'|' + POSS + r' (?:[a-z]+ )?[a-z]+|the (?:[a-z]+ )?[a-z]+|you|him|her|them)'   # any noun phrase ("between")
NP1WN = r'(?:' + NAME + r'|' + POSS + r' (?:[a-z]+ )?[a-z]+|the (?:[a-z]+ )?[a-z]+)'
# What may follow an object "me": a stop, the end, or a function word / adverb; never a verb.
FOLLOW = (r'(?:\.["”’)]*(?:\s|$)|[!?,;:]|$|\s+(?:to|for|at|on|in|of|from|with|about|by|today|tonight|tomorrow|yesterday|later|soon)\b)')
# Finite verbs that follow a subject; only unambiguous ones (no word that is also a common noun).
FIN = (r'(?:are|were|was|is|have|has|had|will|would|can|could|should|shall|might|must|went|go|goes|got|did|do|does|'
       r'don[’\']t|didn[’\']t|doesn[’\']t|won[’\']t|can[’\']t|couldn[’\']t|wouldn[’\']t|never|always|just|also|both|'
       r'decided|wanted|needed|started|talked|worked|lived|loved|liked|played|walked|arrived|stayed|visited|called|'
       r'moved|tried|helped|watched|cooked|finished|enjoyed|travelled|traveled|studied|joined|shared|ordered|planned|'
       r'offered|learned|asked|waited|turned|opened|met|took|made|came|built|bought|found|saw|ran|drove|flew|ate|'
       r'spent|wrote|sent|won|lost|grew|began|love|like|live|need|want|plan|work|think|know|believe|agree|hope|'
       r'[’\']re|[’\']ll|[’\']ve|[’\']d)')


def ci(words):
    ws = sorted(set(words), key=lambda w: (-len(w), w))
    return '(?:' + '|'.join(ws) + ')'


def q(s):
    return '“' + s + '”'


def add(rid, pattern, repl, cat, conf, reason, pos, neg, fixes=None, prov=PROV):
    """fixes: the expected text after the rule is applied once to `pos`."""
    rid = 'pron.' + rid
    assert rid not in IDS, rid
    IDS.add(rid)
    r = dict(id=rid, pattern=pattern, replacement=repl, category=cat, confidence=conf, reason=reason,
             provenance=prov, positive=pos, negative=neg)
    if fixes is not None:
        r['_fixes'] = fixes
    RULES.append(r)


def fixed(rule, text):
    """the text after applying one rule once (Python re; ${x} expanded)"""
    rx = re.compile(rule['pattern'])
    m = rx.search(text)
    if not m:
        return text
    rep = re.sub(r'\$\{(\w+)\}', lambda g: m.group(g.group(1)) or '', rule['replacement'])
    if 'moved' in rx.groupindex and m.group('moved') is not None:
        a, b = m.start('target'), m.start('moved')
        return text[:a] + text[b:m.end('moved')] + rep + text[m.end('moved'):]
    if 'target' in rx.groupindex:
        t = m.group('target')
        if t and t[0].isupper() and len(t) > 1 and rep:
            rep = rep[0].upper() + rep[1:]
        return text[:m.start('target')] + rep + text[m.end('target'):]
    return text


def dump(path):
    out = [{k: v for k, v in r.items() if not k.startswith('_')} for r in RULES]
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
        f.write('\n')
