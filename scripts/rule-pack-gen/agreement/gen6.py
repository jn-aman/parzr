"""Part 6: wh-questions with a mismatched noun, is/are there, 'Me and X was', both ... and."""
from lib import *
from gen2 import (CLN, CLN_SG, CL_N, BAN_HAS, ADJ_RX, vpat, vrep, spl, A, POS_PL, SING_OF, POS_SG)
from gen3 import TO_SG, TO_PL, NAMEY, lc_for, DET_P, ADJ_X
from gen4 import grp, POSN
import vocab

F = '(?im)'
# the noun is the last word of the question or is followed by a function word, never by another noun
CONT3 = (r"(?:[.,;:!?]|\s+(?:in|on|at|for|to|of|from|with|that|which|here|there|left|available|missing|now|today|yet|already|"
         r"because|when|if|inside|under|near|by|about|around|after|before|you|we|I|they)\b|\s*$)")
CONT2 = (r"(?:[.,;:!?]|\s+(?:in|on|at|for|to|of|from|with|that|which|here|there|left|available|missing|now|today|yet|already|"
         r"and|or|but|so|because|when|if|inside|under|near|by|about|around|after|before|you|we|I|they)\b|\s*$)")
PL3 = {'people': vocab.PL_PEOPLE, 'work': vocab.PL_WORK, 'home': vocab.PL_HOME}
SG3 = {'people': vocab.SG_PEOPLE, 'work': vocab.SG_WORK, 'home': vocab.SG_HOME}
PLUR_OF_SG = {v: k for k, v in SING_OF.items() if v}
WHQ = r'(?:what|who|where|which)'

# "What are the problem?" -> is ;  "Where is the files?" -> are
for gname, words in SG3.items():
    for ci_, chunk in enumerate(spl(words, 100)):
        sfx = '' if len(spl(words, 100)) == 1 else str(ci_ + 1)
        noun = {'people': 'manager', 'work': 'file', 'home': 'book'}[gname]
        noun = noun if noun in chunk else chunk[0]
        for wrong, right in (('are', 'is'), ('were', 'was')):
            pat = F + SQ + WHQ + r' (?P<target>' + wrong + r') (?:the|your|my|our|his|her|their|this|that|a|an) (?:' + ADJ_RX + r' )?' + grp(chunk) + CONT3
            pat = F + r'(?:^|' + END + r'\s+)' + WHQ + r' (?P<target>' + wrong + r') (?:the|your|my|our|his|her|their|this|that|a|an) (?:' + ADJ_RX + r' )?' + grp(chunk) + CONT3
            add('agree.wh_' + wrong + '_sg_' + gname + sfx, pat, right, 'Agreement', 0.93,
                'Only one thing is asked about, so use ' + q(right) + '.',
                'Where ' + wrong + ' the ' + noun + '?',
                'Where ' + right + ' the ' + noun + '? Where ' + wrong + ' the ' + noun + ' and the ' + ('pen' if noun != 'pen' else 'cup') + '? Where ' + wrong + ' the ' + noun + ' types?')
for gname, words in PL3.items():
    for ci_, chunk in enumerate(spl(words, 100)):
        sfx = '' if len(spl(words, 100)) == 1 else str(ci_ + 1)
        noun = POSN[gname][0] if POSN[gname][0] in chunk else chunk[0]
        for wrong, right in (('is', 'are'), ('was', 'were')):
            pat = F + r'(?:^|' + END + r'\s+)' + WHQ + r' (?P<target>' + wrong + r') (?:the|your|my|our|his|her|their|these|those|some|any) (?:' + ADJ_RX + r' )?' + grp(chunk) + CONT3
            add('agree.wh_' + wrong + '_pl_' + gname + sfx, pat, right, 'Agreement', 0.93,
                'More than one thing is asked about, so use ' + q(right) + '.',
                'Where ' + wrong + ' the ' + noun + '?',
                'Where ' + right + ' the ' + noun + '? Where ' + wrong + ' the ' + noun + ' folder? Where ' + wrong + ' the ' + (SING_OF.get(noun) or 'file') + '?')

# "Is there two files?" -> Are there ; "Are there a problem?" -> Is there
for gname, words in PL3.items():
    for ci_, chunk in enumerate(spl(words, 100)):
        sfx = '' if len(spl(words, 100)) == 1 else str(ci_ + 1)
        noun = POSN[gname][0] if POSN[gname][0] in chunk else chunk[0]
        for wrong, right in (('is', 'are'), ('was', 'were')):
            pat = F + SQ + r'(?P<target>' + wrong + r') there (?:two|three|four|five|six|seven|eight|nine|ten|any|some|many|a lot of|lots of|plenty of|a few|several) (?:' + ADJ_RX + r' )?' + grp(chunk) + CONT3
            add('agree.' + wrong + '_there_pl_' + gname + sfx, pat, right, 'Agreement', 0.93,
                'A plural follows, so ask with ' + q(right + ' there') + '.',
                {'is': 'Is', 'was': 'Was'}[wrong] + ' there any ' + noun + ' left?',
                {'is': 'Are', 'was': 'Were'}[wrong] + ' there any ' + noun + ' left? ' + {'is': 'Is', 'was': 'Was'}[wrong] + ' there any water left?')
for gname, words in SG3.items():
    for ci_, chunk in enumerate(spl(words, 100)):
        sfx = '' if len(spl(words, 100)) == 1 else str(ci_ + 1)
        noun = {'people': 'manager', 'work': 'file', 'home': 'book'}[gname]
        noun = noun if noun in chunk else chunk[0]
        for wrong, right in (('are', 'is'), ('were', 'was')):
            pat = F + SQ + r'(?P<target>' + wrong + r') there (?:a|an|one|another) (?:' + ADJ_RX + r' )?' + grp(chunk) + CONT3
            add('agree.' + wrong + '_there_sg_' + gname + sfx, pat, right, 'Agreement', 0.92,
                'One thing follows, so ask with ' + q(right + ' there') + '.',
                {'are': 'Are', 'were': 'Were'}[wrong] + ' there a ' + noun + ' left?',
                {'are': 'Is', 'were': 'Was'}[wrong] + ' there a ' + noun + ' left? ' + {'are': 'Are', 'were': 'Were'}[wrong] + ' there a ' + noun + ' and a pen left?')

# "Me and Tom was late" -> were
SG_PEOPLE_RX = grp(vocab.SG_PEOPLE)
for wrong, right, comp in TO_PL[:3] + TO_PL[4:7]:
    pat = (F + SS + r'(?:me|him|her|us) and (?:(?-i:[A-Z][a-z]+)|him|her|you|them|(?:my|your|his|her|their|our) ' + SG_PEOPLE_RX + r') (?P<target>' + vpat(wrong) + r')\b')
    pos = {'is': 'Me and Tom is ready.', 'was': 'Me and Tom was ready.', 'has': 'Me and Tom has a car.',
           "isn't": 'Me and Tom isn\'t ready.', "wasn't": 'Me and Tom wasn\'t ready.', "hasn't": 'Me and Tom hasn\'t a car.'}[wrong]
    neg = 'Me and Tom ' + right + ' ' + comp + '. Tom and Sam ' + wrong + ' ' + comp + '. Between him and me ' + wrong + ' ' + comp + '.'
    add('agree.me_and_' + NAMEY(wrong), pat, vrep(right), 'Agreement', 0.95,
        'Two people joined by ' + q('and') + ' take ' + q(right) + '.', pos, neg)

# ---- Where's / What's / How's + a plural ("Where's my keys?") ---------------------------------------------------
for gname, words in PL3.items():
    for ci_, chunk in enumerate(spl(words, 100)):
        sfx = '' if len(spl(words, 100)) == 1 else str(ci_ + 1)
        noun = POSN[gname][0] if POSN[gname][0] in chunk else chunk[0]
        sing = SING_OF.get(noun) or 'file'
        pat = (F + r'(?:^|' + END + r'\s+)(?P<target>(?:where|what|who|how)[\'’]s) (?:the|your|my|our|his|her|their|these|those|some|any) (?:' + ADJ_RX + r' )?' + grp(chunk) + CONT3)
        add('agree.wh_contraction_pl_' + gname + sfx, pat, '${target}', 'Agreement', 0.84,
            'A plural follows, so use ' + q('are') + ' instead of ' + q('’s') + '.',
            'Where\'s the ' + noun + ' you mentioned?',
            'Where are the ' + noun + ' you mentioned? Where\'s the ' + sing + ' you mentioned? Where\'s the ' + noun + ' folder?')
        RULES[-1]['pattern'] = (F + r'(?:^|' + END + r'\s+)(?P<target>(?P<w>where|what|who|how)[\'’]s) (?:the|your|my|our|his|her|their|these|those|some|any) (?:' + ADJ_RX + r' )?' + grp(chunk) + CONT3)
        RULES[-1]['replacement'] = '${w} are'


# ---- a prepositional phrase between the subject and the verb: "The files in the folder IS" ---------------------------
PREP = r'(?:in|on)'
for gname, words in PL3.items():
    for ci_, chunk0 in enumerate(spl(words, 100)):
        sfx = '' if len(spl(words, 100)) == 1 else str(ci_ + 1)
        for wrong, right, comp in [TO_PL[0], TO_PL[1], TO_PL[2], TO_PL[7]]:
            chunk = [w for w in chunk0 if w not in BAN_HAS] if wrong == 'has' else chunk0
            noun = POSN[gname][0] if POSN[gname][0] in chunk else chunk[0]
            sing = SING_OF.get(noun) or 'file'
            pat = (F + CLN + r'(?:the|these|those|my|our|your|their|his|her|some|many|several|all) (?:' + ADJ_RX + r' )?' + grp(chunk) + r' ' + PREP +
                   r' (?:the|this|that|my|our|your|his|her|their|a|an) (?:' + ADJ_RX + r' )?(?-i:[a-z]+) (?P<target>' + vpat(wrong) + r')\b')
            pos = 'The ' + noun + ' in the room ' + wrong + ' ' + comp + '.'
            neg = ('The ' + noun + ' in the room ' + right + ' ' + comp + '. The ' + sing + ' in the room ' + wrong + ' ' + comp + '. '
                   'The ' + noun + ' in the room you cleaned ' + wrong + ' ' + comp + '. The key to the ' + noun + ' ' + wrong + ' ' + comp + '.')
            add('agree.pl_noun_pp_' + gname + sfx + '_' + NAMEY(wrong), pat, vrep(right), 'Agreement', 0.9,
                'The subject is the plural noun before ' + q('in') + ' and the like, so use ' + q(right) + '.', pos, neg)
for gname, words in SG3.items():
    for ci_, chunk in enumerate(spl(words, 100)):
        sfx = '' if len(spl(words, 100)) == 1 else str(ci_ + 1)
        for wrong, right, comp in [TO_SG[0], TO_SG[3], TO_SG[7]]:
            if gname == 'mass':
                continue
            noun = {'people': 'student', 'work': 'file', 'home': 'book'}[gname]
            noun = noun if noun in chunk else chunk[0]
            pl = PLUR_OF_SG.get(noun, noun + 's')
            lc = CL_N if wrong in ('have', 'do') else CLN_SG
            pat = (F + lc + r'(?:the|this|that|my|our|your|his|her|their|each|every|a|an) (?:' + ADJ_RX + r' )?' + grp(chunk) + r' ' + PREP +
                   r' (?:the|these|those|my|our|your|his|her|their|some|many|several|all) (?:' + ADJ_RX + r' )?(?-i:[a-z]+s) (?P<target>' + vpat(wrong) + r')\b')
            pos = 'The ' + noun + ' in the rooms ' + wrong + ' ' + comp + '.'
            neg = ('The ' + noun + ' in the rooms ' + right + ' ' + comp + '. The ' + pl + ' in the rooms ' + wrong + ' ' + comp + '. '
                   'The ' + noun + ' in the rooms you cleaned ' + wrong + ' ' + comp + '. Does the ' + noun + ' in the rooms ' + ('have' if wrong == 'have' else 'do' if wrong == 'do' else 'go') + ' ' + comp + '?')
            add('agree.sg_noun_pp_' + gname + sfx + '_' + NAMEY(wrong), pat, vrep(right), 'Agreement', 0.9,
                'The subject is the singular noun before ' + q('in') + ' and the like, so use ' + q(right) + '.', pos, neg)
