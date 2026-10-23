"""Part 5: there / here, questions, modal + -s, gerund subjects, bare plurals, this/these."""
from lib import *
from gen2 import (CLN, CLN_SG, WERE_L, ADJ_RX, vpat, vrep, spl, A, POS_PL, SING_OF, POS_SG)
from gen3 import TO_SG, TO_PL, NAMEY, lc_for, DET_P, ADJ_X
from gen4 import grp, POSN
import vocab

F = '(?im)'
NUM = 'two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|twenty'
QUANT = ('several|numerous|various|multiple|a few|few|dozens of|hundreds of|thousands of|millions of|'
         'many(?: of| more| other| different| good| great| big| new| old| small| \\w+s)')
CONT2 = (r"(?:[.,;:!?]|\s+(?:in|on|at|for|to|of|from|with|that|which|here|there|left|available|missing|now|today|yet|already|"
         r"and|or|but|so|because|when|if|inside|under|near|by|about|around|after|before|you|we|I|they)\b|\s*$)")
# ---- there is / there was + plural ------------------------------------------------------------------
PL3 = {'people': vocab.PL_PEOPLE, 'work': vocab.PL_WORK, 'home': vocab.PL_HOME}

def pl_chunks(words):
    return spl(words, 100)

# quantifier without a noun (nothing is a measure unit after these)
for wrong, right, ex in (('is', 'are', 'There is several reasons.'), ('was', 'were', 'There was several reasons.')):
    add('agree.there_' + wrong + '_quantifier', F + r'\bthere (?P<target>' + wrong + r') (?:' + QUANT + r')\b', right, 'Agreement', 0.96,
        q('There') + ' is followed by a plural, so use ' + q('there ' + right) + '.',
        ex, 'There ' + right + ' several reasons. There ' + wrong + ' many a slip. There ' + wrong + ' a reason. There ' + wrong + ' no way. There ' + wrong + ' some water.')
add('agree.there_contraction_quantifier', F + r'\b(?P<target>there[\'’]s) (?:' + QUANT + r')\b', 'there are', 'Agreement', 0.85,
    q('There’s') + ' is followed by a plural, so write ' + q('there are') + '.',
    'There\'s several reasons.', 'There are several reasons. There\'s a reason. There\'s many a slip. There\'s no way.')
add('agree.there_been_quantifier', F + r'\b(?P<target>there (?:has|[\'’]s) been) (?:' + QUANT + r')\b', 'there have been', 'Agreement', 0.9,
    q('There’s been') + ' before a plural should be ' + q('there have been') + '.',
    'There has been several reasons.', 'There have been several reasons. There has been a reason. There\'s been a change.')
add('agree.there_isnt_quantifier', F + r"\bthere (?P<target>isn['’]t) (?:several|numerous|various|multiple|a few|few)\b", 'aren’t', 'Agreement', 0.9,
    'Use a plural verb with a plural: ' + q('there aren’t') + '.',
    'There isn\'t several reasons.', 'There aren\'t several reasons. There isn\'t a reason.')
add('agree.there_wasnt_quantifier', F + r"\bthere (?P<target>wasn['’]t) (?:several|numerous|various|multiple|a few|few)\b", 'weren’t', 'Agreement', 0.9,
    'Use a plural verb with a plural: ' + q('there weren’t') + '.',
    'There wasn\'t several reasons.', 'There weren\'t several reasons. There wasn\'t a reason.')

# number + a listed plural noun (units like "minutes" are not listed on purpose)
for gname, words in PL3.items():
    for ci_, chunk in enumerate(pl_chunks(words)):
        sfx = '' if len(pl_chunks(words)) == 1 else str(ci_ + 1)
        noun = POSN[gname][0] if POSN[gname][0] in chunk else chunk[0]
        for wrong, right in (('is', 'are'), ('was', 'were')):
            pat = F + r'\bthere (?P<target>' + wrong + r') (?:' + NUM + r'|a lot of|lots of|plenty of|a couple of|a number of|a bunch of|a handful of|some|any|no) (?:' + ADJ_RX + r' )?' + grp(chunk) + CONT2
            neg = ('There ' + right + ' two ' + noun + '. There ' + wrong + ' two minutes left. There ' + wrong + ' a ' + (SING_OF.get(noun) or 'file') + '. '
                   'There ' + wrong + ' some water.')
            add('agree.there_' + wrong + '_number_' + gname + sfx, pat, right, 'Agreement', 0.95,
                q('There') + ' is followed by a plural noun, so use ' + q('there ' + right) + '.',
                'There ' + wrong + ' two ' + noun + ' in the room.', neg)
        pat = F + r'\b(?P<target>there[\'’]s) (?:' + NUM + r'|a lot of|lots of|plenty of|a number of|a bunch of|a handful of|some|any|no) (?:' + ADJ_RX + r' )?' + grp(chunk) + CONT2
        add('agree.there_contraction_number_' + gname + sfx, pat, 'there are', 'Agreement', 0.84,
            q('There’s') + ' before a plural noun should be ' + q('there are') + '.',
            'There\'s two ' + noun + ' in the room.',
            'There are two ' + noun + ' in the room. There\'s two minutes left. There\'s a ' + (SING_OF.get(noun) or 'file') + ' in the room.')

# there are + a singular noun (not when a list follows)
CONT = r"(?:[.!?;:]|\s+(?:in|on|at|for|to|that|which|who|with|here|there|now|today|yet|left|available|missing|already|from|inside|under|near|by)\b|$)"
for gname, words in (('people', vocab.SG_PEOPLE), ('work', vocab.SG_WORK), ('home', vocab.SG_HOME)):
    for ci_, chunk in enumerate(spl(words, 100)):
        sfx = '' if len(spl(words, 100)) == 1 else str(ci_ + 1)
        noun = {'people': 'student', 'work': 'file', 'home': 'book'}[gname]
        noun = noun if noun in chunk else chunk[0]
        for wrong, right in (('are', 'is'), ('were', 'was')):
            pat = F + r'\bthere (?P<target>' + wrong + r') (?:a|an|one|another) (?:' + ADJ_RX + r' )?' + grp(chunk) + CONT
            neg = ('There ' + right + ' a ' + noun + ' on the table. There ' + wrong + ' a ' + noun + ' and a pen on the table. '
                   'There ' + wrong + ' a lot of reasons. There ' + wrong + ' a ' + noun + ', a pen and a cup.')
            add('agree.there_' + wrong + '_sg_' + gname + sfx, pat, right, 'Agreement', 0.9,
                q('There') + ' is followed by one thing, so use ' + q('there ' + right) + '.',
                'There ' + wrong + ' a ' + noun + ' on the table.', neg)
        pat = F + r'\bthere (?P<target>have) been (?:a|an|one|another) (?:' + ADJ_RX + r' )?' + grp(chunk) + CONT
        add('agree.there_have_been_sg_' + gname + sfx, pat, 'has', 'Agreement', 0.9,
            q('There has been') + ' goes with one thing.',
            'There have been a ' + noun + ' on the table.',
            'There has been a ' + noun + ' on the table. There have been a ' + noun + ' and a pen on the table.')

# Is there two files? / Was there several?
add('agree.is_there_quantifier', F + r'(?:^|' + END + r'\s+|\b' + WH + r'\s+)(?P<target>is) there (?:several|numerous|various|multiple|a few)\b', 'are', 'Agreement', 0.95,
    'Use ' + q('are there') + ' before a plural.', 'Is there several rooms left?', 'Are there several rooms left? Is there a room left?')
add('agree.was_there_quantifier', F + r'(?:^|' + END + r'\s+|\b' + WH + r'\s+)(?P<target>was) there (?:several|numerous|various|multiple|a few)\b', 'were', 'Agreement', 0.95,
    'Use ' + q('were there') + ' before a plural.', 'Was there several rooms left?', 'Were there several rooms left? Was there a room left?')

# ---- here is / here's + plural -----------------------------------------------------------------------------
for gname, words in PL3.items():
    for ci_, chunk in enumerate(pl_chunks(words)):
        sfx = '' if len(pl_chunks(words)) == 1 else str(ci_ + 1)
        noun = POSN[gname][0] if POSN[gname][0] in chunk else chunk[0]
        sing = SING_OF.get(noun) or 'file'
        for wrong, right, rep, conf in (('is', 'are', 'are', 0.95), ('was', 'were', 'were', 0.95), ("[\\'’]s", None, 'here are', 0.84)):
            if right:
                pat = F + r'\bhere (?P<target>' + wrong + r') (?:the|my|our|your|his|her|their|these|those|some|all the|all my|all your|two|three|four|five) (?:' + ADJ_RX + r' )?' + grp(chunk) + CONT2
                pos = 'Here ' + wrong + ' the ' + noun + ' you asked for.'
                neg = 'Here ' + right + ' the ' + noun + ' you asked for. Here ' + wrong + ' the ' + sing + ' you asked for.'
                add('agree.here_' + wrong + '_' + gname + sfx, pat, rep, 'Agreement', conf,
                    q('Here') + ' is followed by plural things, so use ' + q('here ' + right) + '.', pos, neg)
            else:
                pat = F + r'\b(?P<target>here[\'’]s) (?:the|my|our|your|his|her|their|these|those|some|all the|all my|all your|two|three|four|five) (?:' + ADJ_RX + r' )?' + grp(chunk) + CONT2
                pos = 'Here\'s the ' + noun + ' you asked for.'
                neg = 'Here are the ' + noun + ' you asked for. Here\'s the ' + sing + ' you asked for.'
                add('agree.here_contraction_' + gname + sfx, pat, rep, 'Agreement', conf,
                    q('Here’s') + ' before plural things should be ' + q('here are') + '.', pos, neg)

# ---- questions with the wrong helper --------------------------------------------------------------------
VERBS_ALL = '|'.join(sorted(set(v for v in vocab.VERBS) | {'be', 'not', 'never', 'really', 'also', 'still', 'always', 'usually',
                                                        'actually', 'even', 'ever', 'just', 'already', 'often', 'sometimes', 'have', 'do'}))
QV = ('have|want|know|like|need|think|say|go|come|take|make|give|tell|ask|feel|seem|become|live|eat|drink|sleep|speak|'
      'understand|remember|agree|believe|expect|hope|mean|appear|exist|contain|include|require|allow|provide|belong|depend|'
      'happen|matter|help|learn|teach|stay|leave|start|stop|open|close|see|hear|love|hate|find|get|keep|bring|send|show|sell|buy|pay|'
      'meet|move|turn|wait|walk|win|lose|choose|decide|prefer|enjoy|forget|follow|join|cost|fit|hold|hold|lead|miss|offer|own|pick')
add('agree.q_do_he_she', F + SQ + r'(?P<target>do) (?:he|she) (?:' + VERBS_ALL + r')\b', 'does', 'Agreement', 0.95,
    'Use ' + q('does') + ' with ' + q('he') + ' or ' + q('she') + ' in a question.',
    'Where do she live now?', 'Where does she live now? Do he and she live here? What do they do?')
add('agree.q_does_you_they', F + SQ + r'(?P<target>does) (?:you|we|they|I) (?:' + VERBS_ALL + r')\b', 'do', 'Agreement', 0.96,
    'Use ' + q('do') + ' with ' + q('you') + ', ' + q('we') + ', ' + q('they') + ' or ' + q('I') + ' in a question.',
    'Where does they live now?', 'Where do they live now? This does you good. What does it do to you?')
add('agree.q_do_it', F + SQ + r'(?P<target>do) it (?:work|help|matter|make|cost|take|sound|look|seem|mean|need|require|support|include|cover|apply|change|run|happen|involve|affect|work)\b', 'does', 'Agreement', 0.93,
    'Use ' + q('does') + ' with ' + q('it') + ' in a question.',
    'How do it work?', 'How does it work? Do it now. Do it, then it matters.')
add('agree.q_dont_he_she', F + SQ + r'(?P<target>don[\'’]t) (?:he|she) (?:' + VERBS_ALL + r')\b', 'doesn’t', 'Agreement', 0.95,
    'Use ' + q('doesn’t') + ' with ' + q('he') + ' or ' + q('she') + ' in a question.',
    'Why don\'t she call us?', 'Why doesn\'t she call us? Why don\'t they call us?')
add('agree.q_doesnt_you_they', F + SQ + r'(?P<target>doesn[\'’]t) (?:you|we|they|I)\b', 'don’t', 'Agreement', 0.96,
    'Use ' + q('don’t') + ' with ' + q('you') + ', ' + q('we') + ', ' + q('they') + ' or ' + q('I') + ' in a question.',
    'Why doesn\'t they call us?', 'Why don\'t they call us? Why doesn\'t it work?')
add('agree.q_is_they_we_you', F + SQ + r'(?P<target>is) (?:they|we|you)\b', 'are', 'Agreement', 0.95,
    'Use ' + q('are') + ' with ' + q('they') + ', ' + q('we') + ' or ' + q('you') + '.',
    'Is they coming tonight?', 'Are they coming tonight? That is you in the photo.')
add('agree.q_was_they_we_you', F + SQ + r'(?P<target>was) (?:they|we|you)\b', 'were', 'Agreement', 0.95,
    'Use ' + q('were') + ' with ' + q('they') + ', ' + q('we') + ' or ' + q('you') + '.',
    'Was they at the party?', 'Were they at the party? It was you in the photo.')
CONT_Q = (r'(?:going|coming|ready|here|there|happy|late|sure|still|also|really|not|from|in|at|on|with|doing|being|having|working|'
          r'living|available|able|home|busy|sick|tired|married|new|old|good|bad|right|wrong|correct|serious|alone|free|done|finished|'
          r'gone|leaving|staying|trying|looking|talking|waiting|playing|feeling|thinking|planning|using|taking|making|just|already|now|a|an|the|my|your)')
add('agree.q_are_he_she_it', F + SQ + r'(?P<target>are) (?:he|she|' + IT + r') ' + CONT_Q + r'\b', 'is', 'Agreement', 0.95,
    'Use ' + q('is') + ' with ' + q('he') + ', ' + q('she') + ' or ' + q('it') + '.',
    'Are she coming tonight?', 'Is she coming tonight? Are he and she coming tonight? Are you sure it is ready?')
add('agree.q_am_you_we_they', F + SQ + r'(?P<target>am) (?:you|we|they)\b', 'are', 'Agreement', 0.96,
    q('Am') + ' goes only with ' + q('I') + '.', 'Am you coming tonight?', 'Are you coming tonight? Am I late?')
add('agree.q_am_he_she_it', F + SQ + r'(?P<target>am) (?:he|she|' + IT + r')\b', 'is', 'Agreement', 0.96,
    q('Am') + ' goes only with ' + q('I') + '.', 'Am she coming tonight?', 'Is she coming tonight? Am I late?')
add('agree.q_has_i_you_we_they', F + SQ + r'(?P<target>has) (?:you|we|they|I)\b', 'have', 'Agreement', 0.95,
    'Use ' + q('have') + ' with ' + q('I') + ', ' + q('you') + ', ' + q('we') + ' or ' + q('they') + '.',
    'Has they finished yet?', 'Have they finished yet? Has she finished yet?')
CONT_H = r'(?:gone|been|ever|already|finished|done|seen|called|heard|told|got|taken|made|said|left|come|become|arrived|read|written|sent|received|met|spoken|had|any|a|the|no|just)'
add('agree.q_have_he_she', F + SQ + r'(?P<target>have) (?:he|she) ' + CONT_H + r'\b', 'has', 'Agreement', 0.95,
    'Use ' + q('has') + ' with ' + q('he') + ' or ' + q('she') + '.',
    'Have she finished yet?', 'Has she finished yet? Have he and she finished yet? Have you finished yet?')

# questions with a listed noun
QV_SAFE = ('have|want|know|need|think|say|go|come|give|tell|ask|feel|seem|become|live|eat|drink|sleep|speak|understand|remember|'
           'agree|believe|expect|hope|mean|appear|exist|contain|include|require|allow|provide|belong|depend|happen|matter|learn|stay|'
           'leave|enjoy|prefer|choose|decide|forget|follow|cost|fit')
for gname, words in PL3.items():
    for ci_, chunk in enumerate(pl_chunks(words)):
        sfx = '' if len(pl_chunks(words)) == 1 else str(ci_ + 1)
        noun = POSN[gname][0] if POSN[gname][0] in chunk else chunk[0]
        sing = SING_OF.get(noun) or 'file'
        pat = F + SQ + r'(?P<target>does) (?:the|these|those|my|our|your|their|his|her) (?:' + ADJ_RX + r' )?' + grp(chunk) + r' (?:' + QV_SAFE + r')\b'
        add('agree.q_does_noun_' + gname + sfx, pat, 'do', 'Agreement', 0.94,
            'The subject is plural, so the question starts with ' + q('do') + '.',
            'Does the ' + noun + ' have a deadline?', 'Do the ' + noun + ' have a deadline? Does the ' + sing + ' have a deadline? Does the ' + noun + ' page load?')
for gname, words in (('people', vocab.SG_PEOPLE), ('work', vocab.SG_WORK), ('home', vocab.SG_HOME)):
    for ci_, chunk in enumerate(spl(words, 100)):
        sfx = '' if len(spl(words, 100)) == 1 else str(ci_ + 1)
        noun = {'people': 'student', 'work': 'file', 'home': 'book'}[gname]
        noun = noun if noun in chunk else chunk[0]
        pat = F + SQ + r'(?P<target>do) (?:the|this|that|my|our|your|his|her|their|each|every|a|an) (?:' + ADJ_RX + r' )?' + grp(chunk) + r' (?:' + QV_SAFE + r')\b'
        add('agree.q_do_noun_' + gname + sfx, pat, 'does', 'Agreement', 0.94,
            'The subject is singular, so the question starts with ' + q('does') + '.',
            'Do the ' + noun + ' have a deadline?', 'Does the ' + noun + ' have a deadline? Do the ' + noun + 's have a deadline? Do the ' + noun + ' now.')

# ---- modal / do-support + third-person -s ---------------------------------------------------------------------
REG = ('want like love make take give know say get see look work help think feel tell seem become keep run find leave bring begin '
       'show ask turn start play move live believe hold write stand lose pay meet include continue learn change lead understand '
       'follow stop create speak read allow add spend grow open walk offer remember consider appear buy wait serve send expect '
       'build stay fall kill remain suggest raise sell require report decide pull cause happen mean need hope hate wear win '
       'join call eat drink sleep drive return provide support enjoy hear sit use put let set cut hit').split()
ES = 'watch teach catch reach push wish miss pass discuss finish fix mix guess press express address focus search touch wash'.split()
IES = [('try', 'tr'), ('study', 'stud'), ('carry', 'carr'), ('apply', 'appl'), ('reply', 'repl'), ('copy', 'cop'), ('hurry', 'hurr'),
       ('worry', 'worr'), ('cry', 'cr'), ('deny', 'den'), ('supply', 'suppl'), ('identify', 'identif'), ('fly', 'fl'), ('marry', 'marr'),
       ('rely', 'rel'), ('vary', 'var')]
MODAL = r'(?-i:can|could|will|would|shall|should|may|might|must)'
MODAL_CAP = r'(?:^|' + END + r'\s+)(?-i:Can|Could|Will|Would|Shall|Should|May|Might|Must)'
SUBJ = r'(?:he|she|' + IT + r'|they|we|you|I|who|that|which|there|everyone|everybody|someone|somebody|nobody|anyone|anybody)'
def s_classes():
    yield 'regular', '(?P<stem>' + '|'.join(sorted(REG, key=lambda w: (-len(w), w))) + r')s', r'${stem}', ('goes', 'works')
    yield 'es', '(?P<stem>' + '|'.join(sorted(ES, key=lambda w: (-len(w), w))) + r')es', r'${stem}', ('watches', 'watch')
    yield 'ies', '(?P<stem>' + '|'.join(s for _, s in IES) + r')ies', r'${stem}y', ('tries', 'try')
    yield 'goes', '(?P<stem>go)es', r'${stem}', ('goes', 'go')
    yield 'does', '(?P<stem>do)es', r'${stem}', ('does', 'do')
    yield 'has', 'has', 'have', ('has', 'have')
for cname, rx, rep, (sform, base) in s_classes():
    ex = {'regular': ('works', 'work'), 'es': ('watches', 'watch'), 'ies': ('tries', 'try'), 'goes': ('goes', 'go'),
          'does': ('does', 'do'), 'has': ('has', 'have')}[cname]
    sf, bs = ex
    ci2 = 'regular' == cname
    # (1) subject + modal + -s
    pat = F + r'(?:\b' + SUBJ + r' ' + MODAL + r'|' + MODAL_CAP + r' (?:he|she|' + IT + r'|they|we|you|I)) (?P<target>' + rx + r')\b'
    add('agree.modal_s_' + cname, pat, rep, 'Verb form', 0.96,
        'After a modal verb such as ' + q('can') + ' or ' + q('will') + ' the verb has no ' + q('-s') + ': ' + q(bs) + '.',
        'He can ' + sf + ' with us.' if cname != 'has' else 'She will has a copy.',
        'He can ' + bs + ' with us. The will ' + sf + ' as written. He ' + sf + ' with us. May ' + sf + ' the best.' if cname != 'has' else 'She will have a copy. The will has been read. She has a copy.')
    # (2) do-support + -s : "does he goes", "did she makes"
    if cname == 'does':
        continue
    pat = F + SQ + r'(?:does|did|do) (?:he|she|' + IT + r'|they|we|you|I) (?P<target>' + rx + r')\b'
    add('agree.dosupport_s_' + cname, pat, rep, 'Verb form', 0.96,
        'After ' + q('does') + ' or ' + q('did') + ' the verb has no ' + q('-s') + ': ' + q(bs) + '.',
        'Does he ' + sf + ' with us?' if cname != 'has' else 'Does she has a copy?',
        'Does he ' + bs + ' with us? He ' + sf + ' with us. Did you ' + bs + ' it?' if cname != 'has' else 'Does she have a copy? She has a copy. Did you have it?')
    if cname == 'does':
        continue
    # (3) negated auxiliary + -s
    pat = (F + r"\b(?:doesn['’]t|didn['’]t|don['’]t|does not|did not|do not|can['’]t|cannot|can not|couldn['’]t|wouldn['’]t|won['’]t|shouldn['’]t|"
           r"mustn['’]t|will not|would not|could not|should not|must not|may not|might not) (?P<target>" + rx + r')\b')
    add('agree.negaux_s_' + cname, pat, rep, 'Verb form', 0.96,
        'After a negated helper verb the verb has no ' + q('-s') + ': ' + q(bs) + '.',
        'She doesn\'t ' + sf + ' with us.' if cname != 'has' else 'She doesn\'t has a copy.',
        'She doesn\'t ' + bs + ' with us. She ' + sf + ' with us. Don\'t ' + bs + ' it.' if cname != 'has' else 'She doesn\'t have a copy. She has a copy.')
# ---- gerund subjects ---------------------------------------------------------------------------------------
GER = ('eating|drinking|going|reading|learning|running|exercising|playing|watching|working|studying|speaking|writing|getting|'
       'having|being|using|making|doing|taking|keeping|spending|saving|building|visiting|talking|cooking|driving')
GDET = 'a|an|the|more|your|my|new|good'
for wrong, right, ex in (('are', 'is', 'Learning a new language are hard.'), ('were', 'was', 'Learning a new language were hard.'),
                         ("aren't", "isn't", 'Learning a new language aren\'t easy.')):
    pat = (F + SS + r'(?:' + GER + r') (?:' + GDET + r') (?:\w+ )?\w+ (?P<target>' + vpat(wrong) + r')\b')
    neg = ('Learning a new language ' + right + ' hard. Running shoes ' + wrong + ' on sale. Learning a language and exploring a culture ' + wrong + ' fun. '
           'Reading books and writing notes ' + wrong + ' fun. Eating well and sleeping enough ' + wrong + ' key.')
    add('agree.gerund_subject_' + NAMEY(wrong), pat, vrep(right), 'Agreement', 0.9,
        'An ' + q('-ing') + ' phrase as the subject is singular: ' + q(right) + '.', ex, neg)

# ---- bare plural / mass nouns at a clause start -------------------------------------------------------------------
def bare_patterns(words, verb):
    """two patterns (a capital at a sentence start; lower case after a conjunction): each one a plain literal set for the prefilter"""
    up = '|'.join(sorted((w[0].upper() + w[1:] for w in words), key=lambda w: (-len(w), w)))
    lo = '|'.join(sorted(words, key=lambda w: (-len(w), w)))
    start = F + r'(?:^|[.!?] )(?-i:' + up + r') (?P<target>' + verb + r')\b'
    conj = F + r'\b(?:when|because|if|while|although|though|whereas|unless|whenever) (?-i:' + lo + r') (?P<target>' + verb + r')\b'
    return start, conj
BARE_PL = 'people children men women police criteria bacteria alumni scissors jeans pants trousers clothes goods belongings'.split()
for wrong, right, ex in (('is', 'are', 'People is happy.'), ('was', 'were', 'People was happy.'), ('has', 'have', 'People has arrived.'),
                         ("isn't", "aren't", 'People isn\'t happy.'), ("wasn't", "weren't", 'People wasn\'t happy.'),
                         ("hasn't", "haven't", 'People hasn\'t arrived.'), ("doesn't", "don't", 'People doesn\'t agree.')):
    start, conj = bare_patterns(BARE_PL, vpat(wrong))
    neg = 'People ' + right + ' happy. Each person ' + wrong + ' happy. Jeans ' + right + ' on sale. The Police ' + right + ' a band. looking after children ' + wrong + ' suit you.'
    add('agree.bare_plural_' + NAMEY(wrong), start, vrep(right), 'Agreement', 0.95,
        'The subject is plural, so use ' + q(right) + '.', ex, neg)
    add('agree.bare_plural_conj_' + NAMEY(wrong), conj, vrep(right), 'Agreement', 0.95,
        'The subject is plural, so use ' + q(right) + '.', 'I think when people ' + wrong + ' happy, we know.'.replace(' happy', ' happy'), neg)
BARE_MASS = ('news mathematics physics linguistics genetics robotics measles mumps diabetes information advice equipment furniture research '
             'feedback progress knowledge homework software luggage traffic weather music money water evidence paperwork').split()
for wrong, right, ex in (('are', 'is', 'Information are useful.'), ("aren't", "isn't", 'Information aren\'t useful.'),
                         ('have', 'has', 'Information have changed.'), ("haven't", "hasn't", 'Information haven\'t changed.'),
                         ("don't", "doesn't", 'Information don\'t help.')):
    start, conj = bare_patterns(BARE_MASS, vpat(wrong))
    neg = 'Information ' + right + ' useful. Let information ' + ('have' if wrong == 'have' else 'go') + ' first. People ' + wrong + ' useful. the laws of physics ' + wrong + ' thus required.'
    add('agree.bare_mass_' + NAMEY(wrong), start, vrep(right), 'Agreement', 0.95,
        'This word is singular, so use ' + q(right) + '.', ex, neg)
    add('agree.bare_mass_conj_' + NAMEY(wrong), conj, vrep(right), 'Agreement', 0.95,
        'This word is singular, so use ' + q(right) + '.', 'I wonder if information ' + wrong + ' useful.', neg)

# ---- this / these -----------------------------------------------------------------------------------------------
add('agree.this_are', F + CL + r'this (?P<target>are)\b', 'is', 'Agreement', 0.96, q('This') + ' is singular: ' + q('this is') + '.',
    'I think this are fine.', 'This is fine. These are fine. The files that are missing are fine.')
add('agree.this_have', F + CL + r'this (?P<target>have)\b', 'has', 'Agreement', 0.95, q('This') + ' is singular: ' + q('this has') + '.',
    'I think this have a bug.', 'This has a bug. Does this have a bug? Let this have a go.')
add('agree.these_is', F + CL + r'(?:these|those) (?P<target>is)\b', 'are', 'Agreement', 0.9, 'Use a plural verb with ' + q('these') + ' or ' + q('those') + '.',
    'I think these is fine.', 'These are fine. One of these is fine. Which of these is best?')
add('agree.these_was', F + CL + r'(?:these|those) (?P<target>was)\b', 'were', 'Agreement', 0.9, 'Use a plural verb with ' + q('these') + ' or ' + q('those') + '.',
    'I think these was fine.', 'These were fine. One of these was fine.')
add('agree.these_has', F + CL + r'(?:these|those) (?P<target>has)\b', 'have', 'Agreement', 0.9, 'Use a plural verb with ' + q('these') + ' or ' + q('those') + '.',
    'I think these has a bug.', 'These have a bug. One of these has a bug.')

