"""More redundancies: absolutes with an intensifier, "foresee in advance", "please RSVP", "more superior"."""
from core import add, style, pair, keep_first, S, E, AFTER

SEC = 'Intensified absolutes and other pleonasms'
# The auxiliaries that can stand directly before the adverb without a "not" in between ("will not completely
# eliminate" means something else, so the pattern never fires there).
AUX = r"(?:will|would|shall|should|must|may|might|can|could|has|had|is|are|was|were)"
FUT = (r"(?:[.,;:!?)]|$|\s+(?:and|or|but|to|for|so|if|when|that|by|with|what|how|why|whether|because)\b)")


def build():
    ids = []
    ids.append(add('abs.completely_eliminate',
                   rf'(?im){S}{AUX} (?P<target>(?P<adv>completely|totally|entirely|utterly) (?P<v>eliminat(?:e|ed)|eradicat(?:e|ed)|annihilat(?:e|ed)|obliterat(?:e|ed)|exterminat(?:e|ed))){E}',
                   '${v}', 'Style', 0.72,
                   '“Eliminate”, “eradicate”, “annihilate” and “obliterate” already mean completely: drop the intensifier.',
                   'The new policy will completely eliminate the fee.',
                   'The new policy will not completely eliminate the fee. It almost completely eliminated the risk, and it did not totally eradicate it.'))
    ids += pair('abs.completely_unique', 'completely|totally', 'unique',
                'The design is completely unique to this region.',
                'The design is unique to this region, and the result is not totally new.', plural=False,
                conf=0.74, phrase='completely unique', kshow='unique')
    ids += pair('abs.completely_unanimous', 'completely|totally', 'unanimous',
                'The vote was completely unanimous.',
                'The vote was unanimous, and the result was not totally clear.', plural=False,
                conf=0.74, phrase='completely unanimous', kshow='unanimous')
    ids += pair('abs.completely_identical', 'completely|totally', 'identical',
                'The two samples were completely identical.',
                'The two samples were identical, and the result was not totally clear.', plural=False,
                art_pos='We bought a completely identical copy.', conf=0.74, phrase='completely identical',
                kshow='identical')
    ids += pair('abs.exactly_identical', 'exactly', 'identical',
                'The two samples were exactly identical.',
                'The two samples were identical, and the weights matched exactly.', plural=False,
                conf=0.74, phrase='exactly identical', kshow='identical')
    ids += pair('abs.most_optimum', 'most', 'optimum',
                'This is the most optimum route.',
                'This is the optimum route, and the most scenic one.', plural=False,
                art_pos='It is a most optimum choice.', conf=0.78, phrase='most optimum', kshow='optimum')
    ids.append(add('abs.more_superior', rf'(?im){S}(?P<target>more (?P<k>superior)){E}', '${k}', 'Grammar', 0.88,
                   '“Superior” already means “more”: say “superior”, not “more superior”.',
                   'This tool is more superior to the old one.',
                   'This tool is superior to the old one, and the shop sells more of them.'))
    ids += pair('abs.more_inferior', 'more', 'inferior',
                'This copy is more inferior to the first.',
                'This copy is inferior to the first, and the shop sells more of them.',
                art_pos='It is a more inferior product.', conf=0.88, plural=False, cat='Grammar',
                reason='“Inferior” already means “more”: say “inferior”, not “more inferior”.')
    ids += pair('pair.free_complimentary', 'free', 'complimentary',
                'Guests get a free complimentary breakfast.',
                'Guests get a complimentary breakfast, and parking is free.', plural=False)
    ids += pair('pair.final_culmination', 'final', 'culmination',
                'The treaty was the final culmination of years of talks.',
                'The treaty was the culmination of years of talks, and the final session was short.',
                plural=False, art_pos='It was a final culmination of years of effort.')
    ids += pair('pair.temporary_interim', 'temporary', 'interim',
                'We need the temporary interim solution.',
                'We need an interim solution, and the temporary desk is closed.', plural=False,
                art_pos='We need a temporary interim solution.')
    ids.append(add('verb.in_advance',
                   rf'(?im){S}(?P<target>(?P<v>foresee|foresees|foresaw|foreseen|foreseeing|forecast(?:s|ed|ing)?|predict(?:s|ed|ing)?|anticipat(?:e|es|ed|ing)|forewarn(?:s|ed|ing)?) in advance){FUT}',
                   '${v}', 'Style', 0.78,
                   'To foresee, predict or anticipate is already to do it in advance: drop “in advance”.',
                   'No one could predict in advance what would happen.',
                   'No one could predict what would happen, and we booked in advance of the trip.'))
    ids.append(add('misc.please_rsvp', rf'(?im){S}(?P<target>please (?P<r>(?-i:R\.?S\.?V\.?P\.?))){E}', '${r}', 'Style', 0.74,
                   '“RSVP” already means “please reply”: drop “please”.',
                   'If you can come, please RSVP by Friday.',
                   'If you can come, RSVP by Friday. Please reply to the invitation.'))
    ids.append(add('misc.rsvp_please',
                   rf'(?im){S}(?P<target>(?P<r>(?-i:R\.?S\.?V\.?P\.?)) please)(?:[^\w\'’\s-]|\s*$|\s+(?:by|before|on|at|to|for|via|with|within|until|today|tomorrow|ASAP)\b)',
                   '${r}', 'Style', 0.74,
                   '“RSVP” already means “please reply”: drop “please”.',
                   'RSVP please by Friday.',
                   'RSVP by Friday. To RSVP please add your name to the list.'))
    DET = r"(?:the|a|an|my|your|his|her|our|their|this|that|these|those)"
    PREP = r"(?:in|on|at|for|to|with|by|from)"
    NAME = r"(?-i:[A-Z])[a-z'’]+(?:\s+(?-i:[A-Z])[a-z'’]+)?"
    ids.append(add('misc.both_as_well_as_mid',
                   rf"(?i)[a-z,;:]\s+both\s+(?:(?:{DET}|{PREP})\s+[a-z'’]+(?:\s+[a-z'’]+){{0,2}}|{NAME})\s+(?P<target>as well as)\s+(?:{DET}|{PREP}|(?-i:[A-Z])|\d)",
                   'and', 'Grammar', 0.86,
                   '“Both” pairs with “and”, not “as well as”.',
                   'He teaches both in Delhi as well as in Mumbai.',
                   'He teaches in Delhi as well as in Mumbai. She did both tasks as well as she could, and covered both of them as well as the others.'))
    return ids
