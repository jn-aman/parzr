"""Helpers for the numbers-and-dates pack generator (shared regex pieces, rule registry)."""
import json, re

RULES = []
IDS = set()
APOS = "['’]"
PROV = 'parzr original rule (numbers-and-dates pack)'

ONES = 'one|two|three|four|five|six|seven|eight|nine'
TEENS = 'ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen'
TENS = 'twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety'
# A count above one, as digits or words ("5", "12", "two", "twenty five"); never "1", "0.5" or "1.5".
# The same for a unit: no four-digit numbers ("2012 year", "2004 Cup" are labels, not counts).
CARD2U = (r'(?:[2-9]\d{0,2}|1\d{1,2}|two|three|four|five|six|seven|eight|nine|' + TEENS + '|' + TENS + r'|hundred|thousand|million)')
CARD2 = (r'(?:[2-9]\d*|1\d+|two|three|four|five|six|seven|eight|nine|' + TEENS + '|' + TENS + r'|hundred|thousand|million)')
# Any whole count from words or digits, 1 included.
CARD = r'(?:\d+|' + ONES + '|' + TEENS + '|' + TENS + r'|hundred)'
MONTHS = 'January|February|March|April|May|June|July|August|September|October|November|December'
# Function words that may follow a unit that closes a phrase ("takes 2 hour and", "5 mile away"); never a noun,
# so "a 5 hour trip" (a modifier) is left alone.
TAIL = (r'(?:[.!?]|$|\s+(?:ago|later|away|apart|each|but|so|from|of|in|at|for|by|before|after|until|'
        r'till|since|than|when|while|if|because|as|with|without|is|are|was|were|will|would|can|could|should|must|now|then|'
        r'earlier|late|early|total|straight|only|more)\b)')


def q(s):
    return '“' + s + '”'


def add(rid, pattern, repl, cat, conf, reason, pos, neg, fixes=None, prov=PROV, modes=None):
    """fixes: the expected text after the rule is applied once to `pos`."""
    rid = 'num.' + rid
    assert rid not in IDS, rid
    IDS.add(rid)
    r = dict(id=rid, pattern=pattern, replacement=repl, category=cat, confidence=conf, reason=reason,
             provenance=prov, positive=pos, negative=neg)
    assert fixes is not None, rid
    r['_fixes'] = fixes
    if modes:
        r['modes'] = modes
    RULES.append(r)


def fixed(r, text):
    """Emulates the engine's single edit: the `target` group replaced by the expanded replacement."""
    m = re.search(r['pattern'], text)
    if not m:
        return text
    t = m.span('target') if 'target' in re.compile(r['pattern']).groupindex else m.span()
    rep = re.sub(r'\$\{(\w+)\}', lambda g: m.group(g.group(1)) or '', r['replacement'])
    return text[:t[0]] + rep + text[t[1]:]


def dump(path):
    out = [{k: v for k, v in r.items() if not k.startswith('_')} for r in RULES]
    out.sort(key=lambda r: r['id'])
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + '\n')
