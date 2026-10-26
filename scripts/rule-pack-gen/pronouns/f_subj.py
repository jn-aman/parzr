"""Subject case ("John and me went", "Him is"), reflexives used for I/me, double subjects."""
from lib import *

# A boundary after a verb: never "made-up", "went-"...
B = r'(?:\s|[.,;:!?]|$)'
FIN_STRICT = (r'(?:are|were|was|is|have|has|had|did|do|does|went|came|got|took|made|met|ran|drove|flew|ate|spent|wrote|sent|'
              r'won|grew|began|decided|wanted|talked|lived|loved|played|walked|arrived|stayed|visited|moved|helped|watched|'
              r'enjoyed|travelled|traveled|waited|opened|bought|built|don[’\']t|didn[’\']t|doesn[’\']t|won[’\']t|'
              r'can[’\']t|couldn[’\']t|wouldn[’\']t|isn[’\']t|aren[’\']t|wasn[’\']t|weren[’\']t|hasn[’\']t|haven[’\']t|'
              r'would|could|should|never|always|[’\']re|[’\']ll|[’\']ve|[’\']d)')
FIN_HER = (r'(?:are|were|was|is|have|has|had|did|do|does|went|came|got|took|met|ran|drove|flew|ate|spent|wrote|sent|won|grew|'
           r'began|decided|wanted|talked|lived|loved|played|walked|arrived|stayed|visited|moved|helped|watched|'
           r'enjoyed|traveled|travelled|waited|opened|bought|don[’\']t|didn[’\']t|doesn[’\']t|won[’\']t|'
           r'can[’\']t|couldn[’\']t|wouldn[’\']t|isn[’\']t|aren[’\']t|wasn[’\']t|weren[’\']t|hasn[’\']t|haven[’\']t|'
           r'would|could|should|[’\']re|[’\']ll|[’\']ve)')
CS3 = r'(?:,\s+(?:(?:and|but|so|yet)\s+)?|\b(?:' + CONJ + r')\s+)'
NPS = {
    'name': NAME,
    'poss': r'(?:my|our|his|her|their|your) [a-z]+',
    'the': r'the [a-z]+',
    'pron': r'(?:he|she|they|we)',
}
SENT_ME = {
    'name': ('Last week Dana and me went to the lake.', 'Last week Dana and I went to the lake.'),
    'poss': ('Yesterday my sister and me cooked dinner.', 'Yesterday my sister and I cooked dinner.'),
    'the': ('Then the manager and me talked about it.', 'Then the manager and I talked about it.'),
    'pron': ('Later she and me went home.', 'Later she and I went home.'),
}
NEG_ME = (' Tom and I went home. Call Tom and me tomorrow. Between Dana and me it is fine. He saw Dana and me leave. '
          'Dana and me are an odd pair, I joke. Thanks, Dana and me.')
for typ, (pos, fx) in SENT_ME.items():
    ctx = CS2 if typ in ('poss', 'the') else CS3  # name/my/our/pronoun at a sentence start: usage.x_and_me_subject
    pat = r'(?im)' + ctx + NPS[typ] + r' and (?P<target>me) ' + FIN + r'\b'
    add('x_and_me_subject_' + typ, pat, 'I', 'Grammar', 0.94, 'In the subject, use “I”: “… and I”.', pos,
        {'name': 'Dana and I went to the lake. Last week she called Dana and me.',
         'poss': 'My sister and I cooked dinner. Yesterday they invited my sister and me.',
         'the': 'The manager and I talked. Then they called the manager and me.',
         'pron': 'She and I went home. Later they called her and me.'}[typ], fixes=fx)

# "me and X" mid-sentence
ME_AND = [
    ('him', r'him', 'he and I', 'We left early, so me and him went to the lake.', 'We left early, so he and I went to the lake.'),
    ('her', r'her', 'she and I', 'We left early, so me and her talked it over.', 'We left early, so she and I talked it over.'),
    ('them', r'them', 'they and I', 'We left early, so me and them went out.', 'We left early, so they and I went out.'),
    ('you', r'you', 'you and I', 'We left early, so me and you went out.', 'We left early, so you and I went out.'),
    ('poss', r'(?:my|our|his|her|their|your) [a-z]+', '${other} and I', 'We left early, so me and my sister cooked dinner.', 'We left early, so my sister and I cooked dinner.'),
    ('the', r'the [a-z]+', '${other} and I', 'We left early, so me and the manager talked.', 'We left early, so the manager and I talked.'),
]
for typ, np, rep, pos, fx in ME_AND:
    sub = typ in ('him', 'her', 'them', 'you')
    pat = (r'(?im)' + CS3 + r'(?P<target>me and ' + (r'(?:' + np + r')' if sub else r'(?P<other>' + np + r')') + r') ' + FIN + r'\b')
    if sub:
        pat = r'(?im)' + CS3 + r'(?P<target>me and ' + np + r') ' + FIN + r'\b'
    add('me_and_' + typ + '_subject_mid', pat, rep, 'Grammar', 0.94, 'In the subject, put the other person first and use “I”.',
        pos, 'Tell me and ' + (np if sub else 'Dana') + ' later. They saw me and ' + (np if sub else 'Dana') + ' leave. Then he and I went out.'
        if typ not in ('poss', 'the') else 'They saw me and the team leave. Thanks, it is up to me and my sister.', fixes=fx)

add('me_and_name_subject_mid', r'(?im)' + CS3 + r'(?P<target>me and )(?P<moved>' + NAME + r') ' + FIN + r'\b', ' and I', 'Grammar', 0.94,
    'In the subject, put the other person first and use “I”.', 'We left early, so me and Dana went to the lake.',
    'Tell me and Dana later. They saw me and Dana leave. Then Dana and I went out.', fixes='We left early, so Dana and I went to the lake.')

# "X and him/her/them" as a subject
HIM = [
    ('him', 'him', 'he', FIN_STRICT, 'Dana and him went to the lake.', 'Dana and he went to the lake.'),
    ('her', 'her', 'she', FIN_HER, 'Dana and her went to the lake.', 'Dana and she went to the lake.'),
    ('them', 'them', 'they', FIN_STRICT, 'Dana and them went to the lake.', 'Dana and they went to the lake.'),
]
for typ, ob, sb, fin, pos, fx in HIM:
    for nt, np in [('name', NAME), ('poss', r'(?:my|our|your|his|their) [a-z]+'), ('the', r'the [a-z]+'), ('pron', r'(?:he|she|they|we)')]:
        if nt == 'name':
            ps, f2 = pos, fx
        elif nt == 'poss':
            ps, f2 = pos.replace('Dana', 'my cousin'), fx.replace('Dana', 'my cousin')
        elif nt == 'the':
            ps, f2 = pos.replace('Dana', 'the manager'), fx.replace('Dana', 'the manager')
        else:
            first = 'she' if typ in ('him', 'them') else 'he'
            ps = 'We left early, so ' + first + ' and ' + ob + ' went home.'
            f2 = 'We left early, so ' + first + ' and ' + sb + ' went home.'
        if nt in ('poss', 'the'):
            ps, f2 = ps[0].upper() + ps[1:], f2[0].upper() + f2[1:]
        pat = r'(?im)' + CS2 + np + r' and (?P<target>' + ob + r') ' + fin + B
        neg = ('Tell Dana and ' + ob + ' later. They called Dana and ' + ob + ' yesterday. Dana and ' + sb + ' went home. '
               'Between Dana and ' + ob + ' there is trust.')
        add('x_and_' + ob + '_subject_' + nt, pat, sb, 'Grammar', 0.93,
            'In the subject, use “' + sb + '”: “… and ' + sb + '”.', ps, neg, fixes=f2)

# object-case pronoun as the subject: "Him is", "Her was", "Them are", "Us are"
OBJ_SUBJ = [
    ('him', r'Him', 'He', r'(?:is|was|has|had|does|did|isn[’\']t|wasn[’\']t|hasn[’\']t|doesn[’\']t|didn[’\']t|went|came|will|would|can|could|should|said|says|knows|thinks|goes|got|gets|took|takes|made|makes|wouldn[’\']t|couldn[’\']t|won[’\']t|can[’\']t)',
     'Him is a good teacher.', 'Him and his friends, they left.'),
    ('them_are', r'Them', 'They', r'(?:are|were|have|had|do|did|aren[’\']t|weren[’\']t|haven[’\']t|don[’\']t|didn[’\']t|will|would|can|could|should|went|came|said|say|know|think|want|need|like|love|live|work|won[’\']t|can[’\']t)',
     'Them are my neighbours.', 'Them boots are great. Them and us, we are friends.'),
    ('us', r'Us', 'We', r'(?:are|were|have|had|do|did|aren[’\']t|weren[’\']t|haven[’\']t|don[’\']t|didn[’\']t|will|would|can|could|should|went|came|know|think|want|need|like|love|live|work|must|won[’\']t|can[’\']t)',
     'Us are late again.', 'The US have sent aid. Us nurses need support. Let us have lunch.'),
]
for typ, w, rep, verbs, pos, neg in OBJ_SUBJ:
    if typ == 'us':
        pat = r'(?im)' + CS + r'(?P<target>(?-i:Us)) ' + verbs + B
    elif typ == 'him':
        pat = r'(?im)' + CS + r'(?P<target>(?-i:Him)) ' + verbs + B
    elif typ == 'her':
        pat = r'(?im)' + CS + r'(?P<target>(?-i:Her)) ' + verbs + B
    else:
        pat = r'(?im)' + CS + r'(?P<target>(?-i:Them)) ' + verbs + B
    add('subject_' + typ, pat, rep, 'Grammar', 0.94, 'A subject takes “' + rep.lower() + '”, not “' + w.lower() + '”.', pos,
        neg + ' Give it to ' + w.lower() + '.', fixes=pos.replace(w + ' ', rep + ' ', 1))
# Them is / Us was: the verb changes too
for typ, w, tgt, rep, pos in [('them_is', 'Them', 'Them (?:is|was)', None, 'Them is my neighbours.')]:
    pass
add('subject_them_is', r'(?im)' + CS + r'(?P<target>(?-i:Them) is)' + B, 'They are', 'Grammar', 0.94,
    'A subject takes “they”: “They are”.', 'Them is my neighbours.', 'They are my neighbours. Them boots is old.',
    fixes='They are my neighbours.')
add('subject_them_was', r'(?im)' + CS + r'(?P<target>(?-i:Them) was)' + B, 'They were', 'Grammar', 0.94,
    'A subject takes “they”: “They were”.', 'Them was my neighbours.', 'They were my neighbours. Them boots was old.',
    fixes='They were my neighbours.')

# mid-clause "think him is", "because her was", "that them are"
MID_CTX = r'(?:because|that|if|when|whether|think|thinks|thought|know|knows|knew|guess|hope|hopes|believe|believes|says|said|heard|since|while|although|though|until|once|unless|wonder)'
MID = [
    ('him_is', 'him', 'he', r'(?:is|was|has|had|isn[’\']t|wasn[’\']t|hasn[’\']t|hadn[’\']t)', 'I think him is the best.', 'I think he is the best. I told him that I know him. Everyone but him is happy.'),
    ('them_are', 'them', 'they', r'(?:are|were|have|had|aren[’\']t|weren[’\']t|haven[’\']t|hadn[’\']t)', 'I hope them are on time.', 'I hope they are on time. I told them that we are late.'),
    ('us_are', 'us', 'we', r'(?:are|were|have|had|aren[’\']t|weren[’\']t|haven[’\']t|hadn[’\']t)', 'I guess us are late.', 'I guess we are late. Please tell us are you free. Let us have lunch.'),
]
for typ, ob, sb, verbs, pos, neg in MID:
    # "him is" / "her is" / "them are" ...: the verb is already right, only the pronoun changes
    pat = r'(?i)\b' + MID_CTX + r' (?P<target>' + ob + r') ' + verbs + B
    add('mid_' + typ, pat, sb, 'Grammar', 0.93, 'A subject takes “' + sb + '”, not “' + ob + '”.', pos, neg,
        fixes=pos.replace(' ' + ob + ' ', ' ' + sb + ' ', 1))
for typ, ob, sb, vb, new, pos in [('them_is', 'them', 'they', 'is', 'they are', 'I think them is late.'),
                                  ('them_was', 'them', 'they', 'was', 'they were', 'I think them was late.'),
                                  ('us_was', 'us', 'we', 'was', 'we were', 'I guess us was late.'),
                                  ('us_is', 'us', 'we', 'is', 'we are', 'I guess us is late.')]:
    pat = r'(?i)\b' + MID_CTX + r' (?P<target>' + ob + ' ' + vb + r')' + B
    add('mid_' + typ, pat, new, 'Grammar', 0.93, 'A subject takes “' + sb + '”.', pos,
        'I think they are late. I told them that was fine.', fixes=pos.replace(ob + ' ' + vb, new))

# --- reflexive used in place of I / me ---------------------------------------------------------------------------
add('myself_and_start', r'(?im)' + CS + r'(?P<target>(?-i:Myself) and )(?P<moved>' + NAME + r') ' + FIN + r'\b', ' and I',
    'Grammar', 0.94, '“Myself” cannot be a subject: say “… and I”.', 'Myself and Dana will present the results.',
    'Dana and I will present the results. Myself, I would wait.', fixes='Dana and I will present the results.')
add('myself_and_start_poss', r'(?im)' + CS + r'(?P<target>(?-i:Myself) and (?P<other>(?:my|our|the) [a-z]+)) ' + FIN + r'\b',
    '${other} and I', 'Grammar', 0.94, '“Myself” cannot be a subject: say “… and I”.',
    'Myself and my sister will present the results.', 'My sister and I will present the results.',
    fixes='My sister and I will present the results.')
add('myself_alone_start', r'(?im)' + CS + r'(?P<target>(?-i:Myself)) (?:am|was|will|would|have|had|can|could|should|did|do)\b', 'I',
    'Grammar', 0.93, '“Myself” cannot be a subject: use “I”.', 'Myself will handle the booking.',
    'I will handle the booking. Myself, I would wait. Did myself say that?', fixes='I will handle the booking.')
add('x_and_myself_subject_mid', r'(?i)' + CS3 + NP1N.replace('(?:', '(?:', 1) + r' and (?P<target>myself) ' + FIN + r'\b', 'I',
    'Grammar', 0.93, '“Myself” cannot be a subject: use “I”.', 'Yesterday my sister and myself went to the lake.',
    'Yesterday my sister and I went to the lake. They saw my sister and myself leave.',
    fixes='Yesterday my sister and I went to the lake.')
add('x_and_myself_subject_the', r'(?im)' + CS2 + r'(?:the [a-z]+|you|he|she|they) and (?P<target>myself) ' + FIN + r'\b', 'I',
    'Grammar', 0.93, '“Myself” cannot be a subject: use “I”.', 'The manager and myself will review the plan.',
    'The manager and I will review the plan. I told the manager and myself.', fixes='The manager and I will review the plan.')

# "myself" for "me" after a preposition or verb. Only where the subject of the clause is plainly not "I":
# "I bought it for Nora and myself" is a correct reflexive, "She bought it for Nora and myself" is not.
SUBJ0 = (r'(?:He|She|They|It|Everyone|Everybody|Nobody|Someone|Somebody|Anyone|Anybody|(?:The|My|Our|His|Her|Their) [a-z]+|'
         + NAME1 + r')')
LOWW = r"(?:(?-i:a|[a-z][a-z’']+))"
MYSELF_PREPS = ['between', 'for', 'to', 'with', 'from', 'about', 'by', 'at', 'of', 'on', 'behind', 'near', 'without', 'among', 'beside']
MP_SENT = {
    'between': 'The deal was strictly between the vendor and myself.', 'for': 'She saved a seat for Nora and myself.',
    'to': 'She gave the report to Hugo and myself.', 'with': 'The team met with Priya and myself.',
    'from': 'They will hear from Priya and myself.', 'about': 'He never worried about Hugo and myself.',
    'by': 'The case was handled by Mei and myself.', 'at': 'Several people stared at Nora and myself.',
    'of': 'They were very fond of Hugo and myself.', 'on': 'Maya relies on Mei and myself.',
    'behind': 'The line formed behind Nora and myself.', 'near': 'They sat down near Hugo and myself.',
    'without': 'They left without Mei and myself.', 'among': 'It was a secret among Priya and myself.',
    'beside': 'He stood beside Nora and myself.',
}
for prep in MYSELF_PREPS:
    pos = MP_SENT[prep]
    pat = r'(?im)' + CS + SUBJ0 + r'(?: ' + LOWW + r'){0,5} ' + prep + ' ' + (NP1W if prep == 'between' else NP1) + r' and (?P<target>myself)' + FOLLOW
    add('myself_obj_' + prep, pat, 'me', 'Grammar', 0.9, 'After “' + prep + '” use “me”, not “myself”.', pos,
        'I saved a seat for Nora and myself. I split it ' + prep + ' Nora and myself. She said I worked it out for Nora and myself. She sat ' + prep + ' me.',
        fixes=pos.replace(' and myself', ' and me'))
MYSELF_VERBS = [
    ('ask', 'asked|asks', 'The board asked Hugo and myself to lead.'),
    ('tell', 'told|tells', 'She told Priya and myself yesterday.'),
    ('invite', 'invited|invites', 'They invited Nora and myself to dinner.'),
    ('thank', 'thanked|thanks', 'The mayor thanked Mei and myself.'),
    ('call', 'called|calls', 'Maya called Hugo and myself today.'),
    ('email', 'emailed|emails', 'Maya emailed Priya and myself today.'),
    ('text', 'texted|texts', 'Maya texted Nora and myself tonight.'),
    ('remind', 'reminded|reminds', 'She reminded Nora and myself yesterday.'),
    ('join', 'joined|joins', 'He joined Hugo and myself for lunch.'),
    ('help', 'helped|helps', 'He helped Priya and myself with the move.'),
    ('meet', 'met|meets', 'She met Nora and myself at the station.'),
    ('see', 'saw|sees', 'Nobody saw Hugo and myself yesterday.'),
    ('contact', 'contacted|contacts', 'She contacted Priya and myself today.'),
    ('support', 'supported|supports', 'Everyone supported Mei and myself.'),
    ('pick', 'picked|picks', 'The driver picked Hugo and myself up at six.'),
    ('drive', 'drove|drives', 'Anna drove Priya and myself to the airport.'),
]
for vid, forms, pos in MYSELF_VERBS:
    pat = r'(?im)' + CS + SUBJ0 + r'(?: ' + LOWW + r'){0,3} (?:' + forms + ') ' + NP1 + r' and (?P<target>myself)' + FOLLOW.replace('|about|by|', '|about|by|up|')
    add('myself_obj_v_' + vid, pat, 'me', 'Grammar', 0.9, 'After a verb use “me”, not “myself”.', pos,
        'I will ask myself. I ' + forms.split('|')[0] + ' Hugo and myself. I told Nora and myself it was fine. She told me.',
        fixes=pos.replace(' and myself', ' and me'))
# "please contact myself"
for vid, forms, pos in [
    ('contact', 'contact|call|email|e-mail|text|message|ping|reach|notify|inform', 'Please contact myself if anything breaks.'),
    ('ask', 'ask|tell|thank|remind|update|copy|cc', 'Feel free to ask myself anything about the project.'),
    ('see', 'see|find|meet|join|visit|speak to|talk to|write to|get in touch with|reach out to', 'Please speak to myself or my manager first.'),
]:
    pat = (r'(?i)\b(?:please|kindly|pls|plz|feel free to|don[’\']t hesitate to|do not hesitate to) '
           r'(?:also |directly |just )?(?:' + forms + r') (?P<target>myself)(?:[.!?,;]|$| (?:at|on|via|by|with|for|if|before|directly|anytime|to|about|regarding|or|and|first|when|any|instead))')
    add('myself_contact_' + vid, pat, 'me', 'Grammar', 0.93, 'Use “me” as the object here, not “myself”.', pos,
        'Please contact me if anything breaks. I will just ask myself. Please do not blame myself, she said.',
        fixes=pos.replace('myself', 'me'))
add('myself_send', r'(?i)\b(?:please|kindly|pls|plz|feel free to|don[’\']t hesitate to|do not hesitate to) (?:send|forward|give|pass|show|bring|hand|mail) (?P<target>myself) (?:a|an|the|your|any|some|all|it|that|this|these|those|one|two|copies|copy|updates|details)\b',
    'me', 'Grammar', 0.93, 'Use “me” as the object here, not “myself”.', 'Please send myself a copy of the file.',
    'Please send me a copy of the file. I will just send myself a reminder.', fixes='Please send me a copy of the file.')
add('yourself_subject', r'(?i)\b(?:if|when|whether|should|unless|once|that|because|while) (?P<target>yourself) (?:or|and) (?:your|a|an|any|someone|anyone|somebody|another|other|the|our|my)\b',
    'you', 'Grammar', 0.88, '“Yourself” cannot be a subject: use “you”.', 'If yourself or a family member needs help, call us.',
    'If you or a family member needs help, call us. Do it yourself or ask a friend. Ask yourself and your team.',
    fixes='If you or a family member needs help, call us.')
add('himself_start', r'(?im)' + CS + r'(?P<target>(?-i:Himself)) and (?:his|the|my|our|(?-i:[A-Z][a-z]+)) ', 'He', 'Grammar', 0.9,
    '“Himself” cannot be a subject: use “he”.', 'Himself and his wife attended the party.',
    'He and his wife attended the party. He himself and his wife came. Himself, he would never say.',
    fixes='He and his wife attended the party.')
add('herself_start', r'(?im)' + CS + r'(?P<target>(?-i:Herself)) and (?:her|the|my|our|(?-i:[A-Z][a-z]+)) ', 'She', 'Grammar', 0.9,
    '“Herself” cannot be a subject: use “she”.', 'Herself and her sister attended the party.',
    'She and her sister attended the party. She herself came. Herself, she would never say.',
    fixes='She and her sister attended the party.')

# --- double subject: "My brother he is" ---------------------------------------------------------------------------
KIN_M = 'brother|father|dad|uncle|husband|son|boyfriend|grandfather|grandpa|nephew|stepfather|stepson'
KIN_F = 'sister|mother|mom|mum|mama|aunt|wife|daughter|girlfriend|grandmother|grandma|niece|stepmother|stepdaughter'
KIN_N = 'friend|boss|teacher|doctor|cousin|neighbor|neighbour|manager|colleague|coworker|professor|landlord|supervisor|partner|roommate'
KIN_P = 'parents|kids|children|friends|brothers|sisters|cousins|neighbors|neighbours|teachers|grandparents|colleagues|coworkers'
VSET = (r'(?:is|was|isn[’\']t|wasn[’\']t|has|had|hasn[’\']t|will|won[’\']t|can[’\']t|lives|works|lived|worked|goes|went|always|never|also|'
        r'loves|likes|wants|needs|says|said|thinks|knows|doesn[’\']t|didn[’\']t|does|did)')
VSET_P = (r'(?:are|were|aren[’\']t|weren[’\']t|have|had|haven[’\']t|will|won[’\']t|can[’\']t|live|work|lived|worked|go|went|always|never|also|'
          r'love|like|want|need|say|said|think|know|don[’\']t|didn[’\']t|do|did)')
for gid, kin, pr, vset, sent in [
    ('m', KIN_M, 'he', VSET, 'My brother he is a doctor in Leeds.'),
    ('f', KIN_F, 'she', VSET, 'My sister she works at the bank.'),
    ('n_he', KIN_N, 'he', VSET, 'My boss he was very kind to us.'),
    ('n_she', KIN_N, 'she', VSET, 'My teacher she was very kind to us.'),
    ('p', KIN_P, 'they', VSET_P, 'My parents they live near the coast.'),
]:
    pat = r'(?im)' + CS + r'(?:my|our|his|her|their|your) (?:' + kin + r')(?P<target> ' + pr + r') ' + vset + B
    pos = sent
    add('double_subject_' + gid, pat, '', 'Grammar', 0.84, 'The subject is already named: drop the extra “' + pr + '”.', pos,
        'My brother, he is a doctor in Leeds. My brother is a doctor in Leeds. My brother he met is a doctor. Is my boss he?',
        fixes=pos.replace(' ' + pr + ' ', ' ', 1))
