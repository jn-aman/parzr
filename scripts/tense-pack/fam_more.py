"""More families found by probing: question without a cue (Have you finish?), was + base, past verb + since."""
from core import *
from verbs import ALL_ROWS
from regular import REG_ROWS
from fam_irreg import PB_PLAIN, PB_SKIP, VERBY, tails
from fam_since import SINCE_VERBS, SWIN, POINT

WH = "why|what|where|when|how|who"
QSTART = rf"(?:^|[.!?] |\b(?:{WH}) )"
QAUX = rf"(?:Have (?:you|they|we|I)|Has (?:he|she|it)|Had {PRON})"


def have_question():
    """Have you finish your homework?  Has he go?  ->  past participle (an inverted perfect question)."""
    for v in ALL_ROWS:
        b, v2, v3 = v['base'], v['past'], v['part']
        if v3 == b or b in PB_SKIP or b in ('retake', 'lay', 'bear'):
            continue
        plain = b in PB_PLAIN
        pat = rf"(?im){QSTART}{QAUX} (?P<target>{b})" + (END if plain else rf" {VERBY}\b")
        sel = pick(pat, [(f"Have you {b} {t}?", f"Have you {v3} {t}?") for t in tails(v, ('twice',))])
        if sel is None:
            PROBLEMS.append(f"have_question.{b}: no example"); continue
        pos, right = sel
        tail = pos[len(f"Have you {b} "):-1]
        neg = f"Have you {v3} {tail}? Will you {b} {tail}? I would have you {b} {tail}."
        rule(f"tense.have_question.{b}", pat, v3,
             f"A question with “have” takes the past participle: {Q(v3)}, not {Q(b)}.",
             pos, neg, right=right, category='Verb form', confidence=0.94,
             more_pos=[(f"Has he {b} {tail}?", f"Has he {v3} {tail}?"),
                       (f"Why have they {b} {tail}?", f"Why have they {v3} {tail}?")])
    for v in REG_ROWS:
        b, p = v['base'], v['part']
        pat = rf"(?im){QSTART}{QAUX} (?P<target>{b})" + (rf" {VERBY}\b" if v['noun'] else END)
        t = 'the report' if v['noun'] else 'my work'
        rule(f"tense.have_question_reg.{b}", pat, p,
             f"A question with “have” takes the past participle: {Q(p)}, not {Q(b)}.",
             f"Have you {b} {t}?", f"Have you {p} {t}? Will you {b} {t}? I would have you {b} {t}.",
             right=f"Have you {p} {t}?", category='Verb form', confidence=0.94,
             more_pos=[(f"Has she {b} {t}?", f"Has she {p} {t}?")])


def was_base():
    """It was happen last week -> It happened last week."""
    for b, p in (('happen', 'happened'), ('occur', 'occurred'), ('arrive', 'arrived'), ('appear', 'appeared'),
                 ('exist', 'existed'), ('vanish', 'vanished')):
        rule(f"tense.was_base.{b}",
             rf"(?i)\b(?P<target>(?:was|were) {b}){END}", p,
             f"A past event takes the past form: {Q(p)}, not “was {b}”.",
             f"It was {b} last night.", f"It {p} last night. The plan is to {b} soon.",
             right=f"It {p} last night.", category='Verb form', confidence=0.93,
             more_pos=[(f"They were {b} yesterday.", f"They {p} yesterday.")])


PAST = {'know': 'knew', 'hold': 'held', 'write': 'wrote', 'keep': 'kept', 'wear': 'wore', 'drive': 'drove',
        'sell': 'sold', 'speak': 'spoke', 'run': 'ran', 'lead': 'led', 'sit': 'sat', 'stand': 'stood',
        'teach': 'taught', 'read': None, 'drink': 'drank'}
STRICT_END = r"(?:\s*[.,;:!?)]|\s*$)"


def since_past():
    """I lived here since 2015 -> I have lived here since 2015."""
    for b, t, p, tail in SINCE_VERBS:
        if b in ('read', 'drink'):
            continue
        v2 = PAST.get(b, p)
        if v2 is None:
            continue
        if b == 'run':
            continue
        for sj, aux, ex_s in (('I|we|you|they', 'have', 'I'), ('he|she', 'has', 'She')):
            rep = f'{aux} {p}'
            pat = rf"(?i)\b(?:{sj}) (?P<target>{v2}) {SWIN}since\s+{POINT}{STRICT_END}"
            tail_ok = tail
            pos = f"{ex_s} {v2} {tail_ok} since 2010."
            if not re.search(pat, pos):
                pos = f"{ex_s} {v2} since 2010."
                tail_ok = ''
            if not re.search(pat, pos):
                PROBLEMS.append(f"since_past.{b}: no example"); continue
            right = pos.replace(f" {v2}", f" {rep}", 1)
            neg = f"{right} {ex_s} {v2} {tail_ok} in 2010.".replace("  ", " ")
            rule(f"tense.since_past.{b}.{'plural' if aux == 'have' else '3sg'}", pat, rep,
                 f"A situation that began in the past and continues takes the present perfect with “since”: “{rep}”.",
                 pos, neg, right=right, category='Tense', confidence=0.9)
