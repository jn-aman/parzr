"""Part 4: partitives with listed nouns, relative clauses, compound subjects, proximity, there/here, questions."""
from lib import *
from gen2 import (BAN_HAS, ADJ_RX, vpat, vrep, spl, A, PLURAL_GROUPS, SINGULAR_GROUPS, POS_PL, SING_OF, POS_SG)
from gen3 import TO_SG, TO_PL, NAMEY, lc_for, DET_P, ADJ_X
import vocab

F = '(?im)'
def grp(words):
    return '(?-i:' + '|'.join(sorted(set(words), key=lambda w: (-len(w), w))) + ')'

PART = (r'(?:half|most|some|all|part|a third|two thirds|a quarter|three quarters|a fifth|a lot|lots|plenty|the majority|'
        r'the rest|the remainder|percent|%|many|several|a few|dozens|hundreds|thousands|millions)')
PART_SG = (r'(?:half|most|some|all|part|much|a third|two thirds|a quarter|three quarters|a fifth|a lot|lots|plenty|'
           r'the majority|the rest|the remainder|percent|%|a little|a bit)')

# ---- partitives: "half of the files IS" -> are -------------------------------------------------------------
PL3 = {'people': vocab.PL_PEOPLE, 'work': vocab.PL_WORK, 'home': vocab.PL_HOME}
POSN = {'people': ('students', 'student'), 'work': ('files', 'file'), 'home': ('books', 'book')}
for gname, words in PL3.items():
    for ci_, chunk0 in enumerate(spl(words, 100)):
        sfx = '' if len(spl(words, 100)) == 1 else str(ci_ + 1)
        for wrong, right, comp in TO_PL[:3] + TO_PL[4:7]:
            chunk = [w for w in chunk0 if w not in BAN_HAS] if wrong == 'has' else chunk0
            pool = [w for w in POS_PL[gname] if w in chunk] or [chunk[0]]
            noun = pool[0]
            pat = (F + r'\b' + PART + r' of (?:' + DET_P + r') (?:' + ADJ_RX + r' )?' + grp(chunk) + r' (?P<target>' + vpat(wrong) + r')\b')
            pos = 'Most of the ' + noun + ' ' + wrong + ' ' + comp + '.'
            sing = SING_OF.get(noun)
            neg = ('Most of the ' + noun + ' ' + right + ' ' + comp + '.' + (' Most of the ' + sing + ' ' + wrong + ' ' + comp + '.' if sing else '') +
                   ' The rest of the ' + noun + ' you sent ' + wrong + ' ' + comp + '. Each of the ' + noun + ' ' + wrong + ' ' + comp + '.')
            add('agree.partitive_pl_' + gname + sfx + '_' + NAMEY(wrong), pat, vrep(right), 'Agreement', 0.95,
                'A share of a plural group takes ' + q(right) + '.', pos, neg)

# "half of the work ARE" -> is  (singular and mass nouns)
SG3 = {'work': vocab.SG_WORK, 'mass': vocab.UNCOUNT, 'people': vocab.SG_PEOPLE, 'home': vocab.SG_HOME}
POSS = {'work': 'report', 'mass': 'information', 'people': 'manager', 'home': 'cake'}
for gname, words in SG3.items():
    chunks = spl(words, 100)
    for ci_, chunk in enumerate(chunks):
        sfx = '' if len(chunks) == 1 else str(ci_ + 1)
        for wrong, right, comp in TO_SG[:3] + TO_SG[4:7]:
            noun = POSS[gname] if POSS[gname] in chunk else chunk[0]
            pat = (F + r'\b' + PART_SG + r' of (?:the|this|that|my|our|your|his|her|their) (?:' + ADJ_RX + r' )?' + grp(chunk) + r' (?P<target>' + vpat(wrong) + r')\b')
            pos = 'Most of the ' + noun + ' ' + wrong + ' ' + comp + '.'
            neg = ('Most of the ' + noun + ' ' + right + ' ' + comp + '. Most of the ' + noun + 's you sent ' + wrong + ' ' + comp + '.')
            add('agree.partitive_sg_' + gname + sfx + '_' + NAMEY(wrong), pat, vrep(right), 'Agreement', 0.94,
                'A share of a singular or mass noun takes ' + q(right) + '.', pos, neg)

# ---- relative clauses -----------------------------------------------------------------------------------
# those who / those that + singular verb
for wrong, right, comp in TO_PL:
    pat = F + r'\bthose (?:who|which) (?P<target>' + vpat(wrong) + r')\b'
    pos = {'is': 'Those who is late must wait.', 'was': 'Those who was late must wait.', 'has': 'Those who has a ticket may enter.',
           'does': 'Those who does the work get paid.', "isn't": 'Those who isn\'t ready must wait.', "wasn't": 'Those who wasn\'t there must wait.',
           "hasn't": 'Those who hasn\'t paid must wait.', "doesn't": 'Those who doesn\'t agree may leave.'}[wrong]
    neg = ('Those who ' + right + ' ' + comp + '. Anyone who ' + wrong + ' ' + comp + '. The one who ' + wrong + ' ' + comp + '. Those people who ' + right + ' ' + comp + '.')
    add('agree.those_who_' + NAMEY(wrong), pat, vrep(right), 'Agreement', 0.97,
        q('Those who') + ' is plural, so use ' + q(right) + '.', pos, neg)

# anyone who ARE -> is, one who have -> has ...
for wrong, right, comp in TO_SG:
    if wrong in ('were', "weren't"):
        continue
    pat = (F + r'\b(?:everyone|everybody|anyone|anybody|someone|somebody|no one|nobody|one|each|anything|everything|something) (?:who|that) (?P<target>' + vpat(wrong) + r')\b')
    pos = {'are': 'Anyone who are late must wait.', 'have': 'Anyone who have a ticket may enter.', 'do': 'Anyone who do the work gets paid.',
           "aren't": 'Anyone who aren\'t ready must wait.', "haven't": 'Anyone who haven\'t paid must wait.',
           "don't": 'Anyone who don\'t agree may leave.'}[wrong]
    neg = ('Anyone who ' + right + ' ' + comp + '. Those who ' + wrong + ' ' + comp + '. Everyone who ' + right + ' ' + comp + '. Ones who ' + wrong + ' ' + comp + '.')
    add('agree.anyone_who_' + NAMEY(wrong), pat, vrep(right), 'Agreement', 0.96,
        q('Anyone who') + ' is singular, so use ' + q(right) + '.', pos, neg)

# a person who ARE -> is
for gname, words in (('people', vocab.SG_PEOPLE), ('work', vocab.SG_WORK)):
    chunks = spl(words, 100)
    for ci_, chunk in enumerate(chunks):
        sfx = '' if len(chunks) == 1 else str(ci_ + 1)
        for wrong, right, comp in TO_SG:
            if wrong in ('were', "weren't"):
                continue
            noun = {'people': 'student', 'work': 'file'}[gname] if {'people': 'student', 'work': 'file'}[gname] in chunk else chunk[0]
            pat = (F + r'\b(?:a|an|the|any|every|each|another|this|that|one) ' + grp(chunk) + r' (?:who|that) (?P<target>' + vpat(wrong) + r')\b')
            pos = {'are': 'I know a ' + noun + ' who are very kind.', 'have': 'I know a ' + noun + ' who have a key.',
                   'do': 'I know a ' + noun + ' who do the work.', "aren't": 'I know a ' + noun + ' who aren\'t ready.',
                   "haven't": 'I know a ' + noun + ' who haven\'t paid.', "don't": 'I know a ' + noun + ' who don\'t agree.'}[wrong]
            neg = ('I know a ' + noun + ' who ' + right + ' ' + comp + '. I know the ' + noun + 's who ' + wrong + ' ' + comp + '. I know two ' + noun + 's that ' + wrong + ' ' + comp + '.')
            add('agree.sg_noun_who_' + gname + sfx + '_' + NAMEY(wrong), pat, vrep(right), 'Agreement', 0.95,
                'The noun before ' + q('who') + ' or ' + q('that') + ' is singular, so use ' + q(right) + '.', pos, neg)

# the students who IS -> are
for gname, words in (('people', vocab.PL_PEOPLE), ('work', vocab.PL_WORK), ('home', vocab.PL_HOME)):
    chunks = spl(words, 100)
    for ci_, chunk in enumerate(chunks):
        sfx = '' if len(chunks) == 1 else str(ci_ + 1)
        for wrong, right, comp in TO_PL[:3] + TO_PL[4:5] + TO_PL[7:]:
            noun = POSN[gname][0] if POSN[gname][0] in chunk else chunk[0]
            sing = SING_OF.get(noun)
            pat = (F + CLN + r'(?:the|these|those|my|our|your|their|his|her|all|some|many|several|few|other|two|three|four|five|six|ten) ' + grp(chunk) + r' (?:who|which) (?P<target>' + vpat(wrong) + r')\b')
            pos = {'is': 'The ' + noun + ' who is late must wait.', 'was': 'The ' + noun + ' who was late left.',
                   'has': 'The ' + noun + ' who has a ticket may enter.', 'does': 'The ' + noun + ' who does the work get paid.',
                   "isn't": 'The ' + noun + ' who isn\'t ready must wait.', "doesn't": 'The ' + noun + ' who doesn\'t agree may leave.'}[wrong]
            neg = ('The ' + noun + ' who ' + right + ' ' + comp + '. ' + ('The ' + sing + ' who ' + wrong + ' ' + comp + '. ' if sing else '') +
                   'One of the ' + noun + ' who ' + wrong + ' ' + comp + '.')
            add('agree.pl_noun_who_' + gname + sfx + '_' + NAMEY(wrong), pat, vrep(right), 'Agreement', 0.95,
                'The noun before ' + q('who') + ' or ' + q('that') + ' is plural, so use ' + q(right) + '.', pos, neg)

# ---- compound subjects ---------------------------------------------------------------------------------
# no comma and no "than/as": ", Blackburn and he was buried" starts a new clause inside a sentence
LCNC = r'(?:^|' + END + r'\s+|\b(?:' + CONJ_N + '|' + COG + r'|that)\s+)'
SUBJ_PRO = r'(?:he|she|I|you|we|they)'
PN = r'(?-i:[A-Z][a-z]+)'
for kind in ('pp', 'np'):
    for wrong, right, comp in TO_PL:
        if kind == 'pp':
            pat = (F + LCNC + SUBJ_PRO + r' and ' + SUBJ_PRO + r' (?P<target>' + vpat(wrong) + r')\b')
        else:
            pat = (F + LCNC + r'(?-i:[A-Z][a-z]+) and (?:he|she|I|you|we|they) (?P<target>' + vpat(wrong) + r')\b')
        pos = {'is': 'My brother says he and I is ready.', 'was': 'My brother says he and I was ready.', 'has': 'Tom and I has finished.',
               'does': 'She and I does the filing.', "isn't": 'Tom and I isn\'t ready.', "wasn't": 'Tom and I wasn\'t ready.',
               "hasn't": 'Tom and I hasn\'t finished.', "doesn't": 'Tom and I doesn\'t mind.'}[wrong]
        if kind == 'pp':
            pos = pos.replace('Tom and I', 'He and I').replace('My brother says he and I', 'I think he and I').replace('She and I', 'She and he')
        else:
            pos = pos.replace('My brother says he and I', 'I think Tom and I').replace('She and I does', 'Tom and she does')
        neg = ('Tom and I ' + right + ' ' + comp + '. Tom and Jerry ' + wrong + ' ' + comp + '. The gift between him and me ' + wrong + ' ' + comp + '. '
               'Marks and Spencer ' + wrong + ' ' + comp + '. He and I ' + right + ' ' + comp + '.')
        add('agree.pron_and_' + kind + '_' + NAMEY(wrong), pat, vrep(right), 'Agreement', 0.96,
            'Two subjects joined by ' + q('and') + ' take ' + q(right) + '.', pos, neg)

DETS = r'(?:the|my|our|your|his|her|their)'
LOW = r'(?-i:[a-z]+)'

# ---- either/neither ... or/nor, not only ... but also: the verb agrees with the nearer subject ---------------
CORR = r'(?:either|neither|not only)'
CONN = r'(?:or|nor|but also)'
for gname, words in (('people', vocab.PL_PEOPLE), ('work', vocab.PL_WORK), ('home', vocab.PL_HOME)):
    chunks = spl(words, 100)
    for ci_, chunk0 in enumerate(chunks):
        sfx = '' if len(chunks) == 1 else str(ci_ + 1)
        for wrong, right, comp in [TO_PL[0], TO_PL[1], TO_PL[2], TO_PL[7]]:
            chunk = [w for w in chunk0 if w not in BAN_HAS] if wrong == 'has' else chunk0
            noun = POSN[gname][0] if POSN[gname][0] in chunk else chunk[0]
            sing = SING_OF.get(noun, 'file')
            pat = (F + r'\b' + CORR + r' [^.!?;,\n]{1,40}? ' + CONN + r' (?:' + DETS + r' )?(?:' + ADJ_RX + r' )?' + grp(chunk) + r' (?P<target>' + vpat(wrong) + r')\b')
            pos = 'Neither the manager nor the ' + noun + ' ' + wrong + ' ' + comp + '.'
            neg = ('Neither the manager nor the ' + noun + ' ' + right + ' ' + comp + '. Neither the ' + noun + ' nor the manager ' + wrong + ' ' + comp + '. '
                   'Either way, the ' + noun + ' ' + right + ' ' + comp + '.')
            add('agree.nearer_pl_' + gname + sfx + '_' + NAMEY(wrong), pat, vrep(right), 'Agreement', 0.88,
                'After ' + q('or') + ', ' + q('nor') + ' or ' + q('but also') + ' the verb agrees with the nearer subject, which is plural: ' + q(right) + '.', pos, neg)
for gname, words in (('people', vocab.SG_PEOPLE), ('work', vocab.SG_WORK), ('home', vocab.SG_HOME)):
    chunks = spl(words, 100)
    for ci_, chunk in enumerate(chunks):
        sfx = '' if len(chunks) == 1 else str(ci_ + 1)
        for wrong, right, comp in [TO_SG[0], TO_SG[2], TO_SG[7]]:
            noun = {'people': 'student', 'work': 'file', 'home': 'book'}[gname]
            noun = noun if noun in chunk else chunk[0]
            pat = (F + r'\b' + CORR + r' [^.!?;,\n]{1,40}? ' + CONN + r' (?:' + DETS + r'|a|an|this|that) (?:' + ADJ_RX + r' )?' + grp(chunk) + r' (?P<target>' + vpat(wrong) + r')\b')
            pos = 'Neither the managers nor the ' + noun + ' ' + wrong + ' ' + comp + '.'
            neg = ('Neither the managers nor the ' + noun + ' ' + right + ' ' + comp + '. Neither the ' + noun + ' nor the managers ' + wrong + ' ' + comp + '.')
            add('agree.nearer_sg_' + gname + sfx + '_' + NAMEY(wrong), pat, vrep(right), 'Agreement', 0.85,
                'After ' + q('or') + ', ' + q('nor') + ' or ' + q('but also') + ' the verb agrees with the nearer subject, which is singular: ' + q(right) + '.', pos, neg)
# pronoun forms: either you or he ARE -> is
add('agree.nearer_pron_sg', F + r'\b(?:either|neither) (?:you|we|they|I) (?:or|nor) (?:he|she|it) (?P<target>are|were|have)\b', 'is', 'Agreement', 0.9,
    'Use the verb that agrees with the nearer subject.', 'Neither you nor he are ready.', 'Neither you nor he is ready. Neither he nor you are ready.')
add('agree.nearer_pron_pl', F + r'\b(?:either|neither) (?:he|she|it) (?:or|nor) (?:you|we|they) (?P<target>is|was|has)\b', 'are', 'Agreement', 0.9,
    'Use the verb that agrees with the nearer subject.', 'Neither he nor you is ready.', 'Neither he nor you are ready. Neither you nor he is ready.')

# ---- "along with / as well as" does not make the subject plural --------------------------------------------
ALONG = r'(?:along with|as well as|together with|in addition to|accompanied by)'
for gname, words in (('people', vocab.SG_PEOPLE), ('work', vocab.SG_WORK)):
    chunks = spl(words, 100)
    for ci_, chunk in enumerate(chunks):
        sfx = '' if len(chunks) == 1 else str(ci_ + 1)
        for wrong, right, comp in [TO_SG[0], TO_SG[2], TO_SG[7]]:
            noun = {'people': 'manager', 'work': 'report'}[gname]
            noun = noun if noun in chunk else chunk[0]
            pat = (F + CLN_SG + r'(?:the|my|our|your|his|her|their|this|that|a|an) (?:' + ADJ_RX + r' )?' + grp(chunk) + r',? ' + ALONG + r' (?:' + DETS + r' )?(?:' + ADJ_RX + r' )?(?-i:\w+),? (?P<target>' + vpat(wrong) + r')\b')
            pos = 'The ' + noun + ', along with the staff, ' + wrong + ' ' + comp + '.'
            pos = 'The ' + noun + ', along with the teams, ' + wrong + ' ' + comp + '.'
            neg = ('The ' + noun + ', along with the teams, ' + right + ' ' + comp + '. The ' + noun + 's, along with the teams, ' + wrong + ' ' + comp + '. '
                   'The ' + noun + ' and the teams ' + wrong + ' ' + comp + '. The ' + noun + ', as well as the teams who ' + wrong + ' ' + comp + ', is here.')
            add('agree.along_with_' + gname + sfx + '_' + NAMEY(wrong), pat, vrep(right), 'Agreement', 0.82,
                q('along with') + ' and ' + q('as well as') + ' do not add a subject: the verb agrees with the first noun, ' + q(right) + '.', pos, neg)

# ---- names ----------------------------------------------------------------------------------------------------
NM = grp(vocab.NAMES)
NAME_CL = r'(?:\b(?:' + CONJ + '|' + COG + r')\s+)'
for wrong, right, comp in [("don't", "doesn't", 'know'), ("haven't", "hasn't", 'finished'), ('are', 'is', 'late'), ('have', 'has', 'a key'), ("aren't", "isn't", 'ready'), ('do', 'does', 'the work')]:
    pat = F + NAME_CL + NM + r' (?P<target>' + vpat(wrong) + r')\b'
    nm = 'Tom'
    pos = 'I think ' + nm + ' ' + wrong + ' ' + comp + '.'
    neg = ('I think ' + nm + ' ' + right + ' ' + comp + '. Tom and Mary ' + wrong + ' ' + comp + '. Let Tom ' + ('have' if wrong == 'have' else 'do' if wrong == 'do' else 'go') + ' first. '
           'Tom ' + wrong + ' ' + comp + ', said the narrator. Thanks Tom ' + wrong + ' ' + comp + '.')
    neg = neg.replace(' Tom ' + wrong + ' ' + comp + ', said the narrator.', '').replace(' Thanks Tom ' + wrong + ' ' + comp + '.', ' Thanks, Tom, and see you.')
    add('agree.name_' + NAMEY(wrong), pat, vrep(right), 'Agreement', 0.93,
        'A single person’s name takes ' + q(right) + '.', pos, neg)
