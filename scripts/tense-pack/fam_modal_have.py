"""modal + have + base form: 'She should have go' -> 'She should have gone'."""
from core import *
from verbs import ALL_ROWS
from regular import REG_ROWS
from fam_irreg import PB_PLAIN, PB_SKIP, VERBY, tails

PRE = (r"(?:(?:would|could|should|might|must|may|will|shall)(?:n['’]t)? have|"
       r"(?:would|could|should|might|must)['’]ve|to have)")
MODAL_SKIP = PB_SKIP | {'lay'}


def modal_have_base():
    for v in ALL_ROWS:
        b, v2, v3 = v['base'], v['past'], v['part']
        if v3 == b or b in MODAL_SKIP or b in ('retake',):
            continue
        plain = b in PB_PLAIN
        pat = rf"(?i)\b{PRE} (?P<target>{b})" + (END if plain else rf" {VERBY}\b")
        sel = pick(pat, [(f"She should have {b} {t}.", f"She should have {v3} {t}.") for t in tails(v, ('twice',))])
        if sel is None:
            PROBLEMS.append(f"modal_have_base.{b}: no example"); continue
        pos, right = sel
        tail = pos[len(f"She should have {b} "):-1]
        neg = f"She should have {v3} {tail}. She will {b} {tail}. We would have you {b} {tail}."
        rule(f"tense.modal_have_base.{b}", pat, v3,
             f"After “have” in a perfect (“should have”, “would have”) the verb takes its past participle: {Q(v3)}, not {Q(b)}.",
             pos, neg, right=right, category='Verb form', confidence=0.95,
             more_pos=[(f"They could've {b} {tail}.", f"They could've {v3} {tail}."),
                       (f"We must have {b} {tail}.", f"We must have {v3} {tail}.")])
    for v in REG_ROWS:
        b, p = v['base'], v['part']
        pat = rf"(?i)\b{PRE} (?P<target>{b})" + (rf" {VERBY}\b" if v['noun'] else END)
        t = 'the report' if v['noun'] else 'my work'
        rule(f"tense.modal_have_base_reg.{b}", pat, p,
             f"After “have” in a perfect (“should have”, “would have”) the verb takes its past participle: {Q(p)}, not {Q(b)}.",
             f"She should have {b} {t}.", f"She should have {p} {t}. She will {b} {t}. We would have you {b} {t}.",
             right=f"She should have {p} {t}.", category='Verb form', confidence=0.95,
             more_pos=[(f"They could've {b} {t}.", f"They could've {p} {t}.")])
