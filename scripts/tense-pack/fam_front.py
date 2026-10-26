"""A fronted past-time word with a present verb: "Yesterday I go to the market" -> "Yesterday I went ...".
The time word is matched with its capital ((?-i:...)): a sentence that opens with it, never "since last year we use"."""
import json, os
from core import *
G = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data') + '/'
from lex import third
from verbs import ALL_ROWS
from regular import REG_ROWS

FRONT = r"(?-i:Yesterday|Last (?:night|week|weekend|month|year|summer|winter|spring))"
SUBJ = r"(?:I|we|you|they|he|she|it)"
SAME_FORM = {'read', 'put', 'cut', 'set', 'let', 'hit', 'hurt', 'shut', 'quit', 'cost', 'spread', 'beat', 'bet', 'burst',
             'cast', 'shed', 'split', 'broadcast', 'forecast', 'upset', 'rid', 'slit', 'thrust', 'bid'}
EXTRA = [  # base, third, past, example tail
    ('get', 'gets', 'got', 'a new phone'), ('lead', 'leads', 'led', 'the meeting'),
]
# rare verbs whose present form is more often a noun or a different verb than a slip for the past
NO_FRONT = {'lie', 'show', 'sew', 'bear', 'wind', 'found', 'lay', 'bind', 'grind', 'wake', 'hang', 'shine', 'stick',
            'spin', 'sting', 'swing', 'slide', 'sit', 'stand', 'strike', 'bend', 'deal', 'dig', 'feed', 'fight', 'flee',
            'fling', 'creep', 'cling', 'bleed', 'breed', 'kneel', 'wring', 'seek', 'weep', 'withhold', 'uphold', 'mislead',
            'foretell'}
DO_VERBS = ['go', 'know', 'see', 'like', 'have', 'get', 'want', 'work', 'do', 'think', 'feel', 'eat', 'take', 'come',
            'call', 'help', 'tell', 'say', 'make', 'need', 'understand', 'remember']


def front_rows():
    rows = []
    for v in ALL_ROWS:
        if v['base'] in NO_FRONT or v['base'] in SAME_FORM or v['past'] == v['base']:
            continue
        if v['base'] in ('have', 'be', 'bear', 'become', 'overcome', 'run', 'come'):
            continue
        rows.append((v['base'], v['third'], v['past'], v['tail']))
    for b, t, p, tail in EXTRA:
        if all(r[0] != b for r in rows):
            rows.append((b, t, p, tail))
    for v in REG_ROWS:
        if v['base'] in SAME_FORM:
            continue
        rows.append((v['base'], third(v['base']), v['part'], 'the report'))
    # come / run / become: the past differs from the base but the participle equals it
    for b, t, p, tail in (('come', 'comes', 'came', 'home early'), ('run', 'runs', 'ran', 'the test'),
                          ('become', 'becomes', 'became', 'a doctor')):
        rows.append((b, t, p, tail))
    out, seen = [], set()
    for r in rows:
        if r[0] not in seen:
            seen.add(r[0]); out.append(r)
    return out


def past_marker_front():
    for b, t, p, tail in front_rows():
        pat = rf"{FRONT},? {SUBJ} (?P<target>{b}|{t}){END}"
        pos = f"Last night I {b} {tail}."
        right = f"Last night I {p} {tail}."
        neg = (f"Last night I {p} {tail}. Tomorrow I will {b} {tail}. I {b} {tail} every day. "
               f"Since last year we {b} {tail} often.")
        rule(f"tense.past_marker_front.{b}", pat, p,
             f"A time like “yesterday” or “last week” puts the verb in the past: “{p}”, not “{b}”.",
             pos, neg, right=right, category='Tense', confidence=0.95,
             more_pos=[(f"Last week, we {b} {tail}.", f"Last week, we {p} {tail}."),
                       (f"Last night she {t} {tail}.", f"Last night she {p} {tail}.")])
    # do / have / be
    verbs = '|'.join(DO_VERBS)
    rule("tense.past_marker_front.dont",
         rf"{FRONT},? {SUBJ} (?P<target>don['’]t|doesn['’]t) (?:{verbs})\b",
         "didn't", "A time like “yesterday” puts the verb in the past: “didn’t”.",
         "Last night I don't go to school.", "Last night I didn't go to school. I don't go to school.",
         right="Last night I didn't go to school.", category='Tense', confidence=0.95,
         more_pos=[("Last week she doesn't call me.", "Last week she didn't call me.")])
    rule("tense.past_marker_front.do_not",
         rf"{FRONT},? {SUBJ} (?P<target>do not|does not) (?:{verbs})\b",
         "did not", "A time like “yesterday” puts the verb in the past: “did not”.",
         "Last night I do not go to school.", "Last night I did not go to school. I do not go to school.",
         right="Last night I did not go to school.", category='Tense', confidence=0.95,
         more_pos=[("Last night he does not call me.", "Last night he did not call me.")])
    for aux, past, ex, s in (('am', 'was', "Last night I am sick.", r"I"),
                             ('is', 'was', "Last night it is very hot.", r"(?:he|she|it)"),
                             ('are', 'were', "Last year we are in Paris.", r"(?:we|you|they)")):
        right = ex.replace(f" {aux} ", f" {past} ")
        rule(f"tense.past_marker_front.be_{aux}",
             rf"{FRONT},? {s} (?P<target>{aux}){END}", past,
             f"A time like “yesterday” or “last year” puts the verb in the past: “{past}”, not “{aux}”.",
             ex, f"{right} Now it is fine.", right=right, category='Tense', confidence=0.95)
    rule("tense.past_marker_front.have",
         rf"{FRONT},? {SUBJ} (?P<target>have|has) (?:a|an|the|my|some|no|two|three|four|five|many|much|lots|too|so)\b",
         "had", "A time like “yesterday” puts the verb in the past: “had”.",
         "Last night I have a meeting at nine.", "Last night I had a meeting at nine. I have a meeting at nine.",
         right="Last night I had a meeting at nine.", category='Tense', confidence=0.95,
         more_pos=[("Last week she has a fever.", "Last week she had a fever.")])
