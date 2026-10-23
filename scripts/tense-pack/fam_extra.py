"""Families found by reading the DEV misses: got + past form, 'll + past form, will able to, present + for N years,
he is works, had went + past time."""
from core import *
from lex import third
from verbs import ALL_ROWS, STRONG_ROWS
from regular import REG_ROWS
from fam_since import SWIN, MARK, WIN


GET_PASSIVE = [('stole', 'stolen'), ('tore', 'torn'), ('chose', 'chosen'), ('froze', 'frozen'), ('threw', 'thrown'),
               ('blew', 'blown'), ('drew', 'drawn'), ('wore', 'worn'), ('wrote', 'written'), ('forbade', 'forbidden'),
               ('forgave', 'forgiven'), ('undid', 'undone'), ('overtook', 'overtaken'), ('withdrew', 'withdrawn'),
               ('drove', 'driven'), ('rode', 'ridden'), ('gave', 'given'), ('ate', 'eaten')]


def get_passive():
    """My bike got stole -> My bike got stolen."""
    for v2, v3 in GET_PASSIVE:
        t = f"(?-i:{v2})" if v2 in ('drew', 'wore', 'rode') else v2
        rule(f"tense.get_passive.{v2}", rf"(?i)\b(?:got|get|gets|getting) (?P<target>{t}){END}", v3,
             f"A “get” passive takes the past participle: {Q(v3)}, not {Q(v2)}.",
             f"My bike got {v2} last night.", f"My bike got {v3} last night. We get a new one.",
             right=f"My bike got {v3} last night.", category='Verb form', confidence=0.95,
             more_pos=[(f"The window gets {v2} every winter.", f"The window gets {v3} every winter.")])


LL_SKIP = {'saw', 'found', 'lay', 'wound', 'ground', 'bound', 'fell', 'rose', 'bit', 'shone', 'bore', 'sat', 'stood',
           'hung', 'led', 'lent', 'swung', 'spun', 'stuck', 'struck', 'dug', 'bred', 'fed', 'fled', 'met', 'won', 'dealt'}
LL_ADV = "just|also|definitely|probably|really|never|always|still|then|soon|later|certainly|surely"


def ll_past():
    """I'll called you -> I'll call you."""
    rows = [(v['base'], v['past'], v['tail']) for v in ALL_ROWS if v['past'] != v['base'] and v['past'] not in LL_SKIP]
    rows += [(v['base'], v['part'], 'the report') for v in REG_ROWS]
    seen = set()
    for b, v2, tail in rows:
        if b in seen:
            continue
        seen.add(b)
        t = f"(?-i:{v2})" if v2 in ('drew', 'wore', 'rode', 'sang', 'ran') else v2
        pat = rf"(?i)\b(?:I|you|we|they|he|she|it|who|that|there)['’]ll (?P<target>{t}){END}"
        rule(f"tense.ll_past.{b}", pat, b,
             f"After “’ll” (will) the verb takes its base form: {Q(b)}, not {Q(v2)}.",
             f"I'll {v2} {tail}.", f"I'll {b} {tail}. Anna {v2} {tail}.", right=f"I'll {b} {tail}.",
             category='Verb form', confidence=0.96,
             more_pos=[(f"She'll {v2} {tail} now.", f"She'll {b} {tail} now.")])


def modal_able():
    """We will able to ship -> We will be able to ship."""
    rule("tense.modal_able",
         r"(?i)(?:\b(?:will|would|shall|should|must|may|might|won['’]t|wouldn['’]t|shouldn['’]t|mustn['’]t)|['’]ll) (?P<target>able) to\b",
         "be able", "After a modal, “able to” needs “be”: “we will be able to”.",
         "We will able to ship next week.", "We will be able to ship next week. He is able to ship it.",
         right="We will be able to ship next week.", category='Verb form', confidence=0.95,
         more_pos=[("They won't able to join us.", "They won't be able to join us."),
                   ("I'll able to help tomorrow.", "I'll be able to help tomorrow."),
                   ("You must able to log in first.", "You must be able to log in first.")])


FOR_NUM = (r"(?:two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|forty|fifty|a few|several|many|"
           r"[0-9]+)")
FOR_VERBS = [('know', 'knows', 'known', 'each other'), ('own', 'owns', 'owned', 'this house'),
             ('love', 'loves', 'loved', 'her'), ('like', 'likes', 'liked', 'them'), ('hate', 'hates', 'hated', 'it'),
             ('want', 'wants', 'wanted', 'this job'), ('need', 'needs', 'needed', 'this tool'),
             ('belong', 'belongs', 'belonged', 'here')]


def for_duration():
    """We know each other for ten years -> We have known each other for ten years."""
    for b, t, p, tail in FOR_VERBS:
        for sj, aux, vb, ex_s in (('I|we|you|they', 'have', b, 'We'), ('he|she', 'has', t, 'She')):
            rep = f"{aux} {p}"
            pat = rf"(?i)\b(?:{sj}) (?P<target>{vb}) {SWIN}for {FOR_NUM}\s(?:years|decades|months){END}"
            pos = f"{ex_s} {vb} {tail} for ten years."
            if not re.search(pat, pos):
                PROBLEMS.append(f"for_duration.{b}: example"); continue
            right = pos.replace(f" {vb} ", f" {rep} ", 1)
            rule(f"tense.for_duration.{b}.{'plural' if aux == 'have' else '3sg'}", pat, rep,
                 f"A state that has lasted up to now takes the present perfect with “for”: “{rep}”.",
                 pos, f"{right} {ex_s} {vb} {tail} for ten minutes.", right=right, category='Tense', confidence=0.92)


THIRD_FORMS = ("works plays studies goes likes loves wants needs makes takes gives helps teaches drives eats sleeps "
               "stays speaks writes knows thinks feels seems says tells uses owns lives has").split()


def be_before_verb():
    """He is works at Amazon -> He works at Amazon."""
    for t in THIRD_FORMS:
        pat = rf"(?i)\b(?:he|she|who) (?P<target>is ){t}{END}"
        rule(f"tense.be_before_verb.{t}", pat, "",
             f"“{t}” is already the verb: “is” does not belong before it.",
             f"He is {t} at Amazon.", f"He {t} at Amazon. She is happy.",
             right=f"He {t} at Amazon.", category='Verb form', confidence=0.93,
             more_pos=[(f"Who is {t} here?", f"Who {t} here?")])


def had_marker():
    """I had went there last year -> I went there last year (a finished past time takes the simple past)."""
    for v in STRONG_ROWS:
        b, v2, v3 = v['base'], v['past'], v['part']
        if v2 == v3 or b in ('lie', 'hide', 'show', 'sew', 'wake', 'tread', 'strive', 'forget', 'weave', 'bite', 'retake',
                             'become', 'come', 'run', 'overcome', 'begin', 'ring', 'slay'):
            continue
        t = f"(?-i:{v2})" if v2 in ('drew', 'rose', 'ran', 'sang', 'rode', 'wore', 'bore') else v2
        follow = {'saw': r"(?:it|him|her|them|that|this|the [a-z]+)"}.get(v2)
        pat = (rf"(?i)\b(?:I|we|you|they|he|she|it) (?P<target>had {t})" + (rf" {follow}" if follow else '') +
               rf"(?: {WIN})? {MARK}{END}")
        tail = 'it' if v['kind'] != 'I' else 'there'
        pos = f"I had {v2} {tail} last year."
        if not re.search(pat, pos):
            pos = f"I had {v2} {tail} yesterday."
        if not re.search(pat, pos):
            PROBLEMS.append(f"had_marker.{b}: example"); continue
        right = pos.replace(f"had {v2}", v2)
        rule(f"tense.had_marker.{b}", pat, v2,
             f"A finished past time (“last year”, “yesterday”, “ago”) takes the simple past: {Q(v2)}, not “had {v2}”.",
             pos, f"{right} I had {v3} {tail} before then.", right=right, category='Tense', confidence=0.94,
             more_pos=[(pos.replace('last year', 'two days ago').replace('yesterday', 'two days ago'),
                        right.replace('last year', 'two days ago').replace('yesterday', 'two days ago'))])
