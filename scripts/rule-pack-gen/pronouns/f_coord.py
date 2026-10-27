"""Case in coordination and after prepositions/verbs: "for my wife and I", "John and me went", "between him and I"."""
from lib import *

OBJ_SET = {'I': 'me', 'he': 'him', 'she': 'her', 'we': 'us', 'they': 'them'}

# --- "PREP NP and I" -> "me" -------------------------------------------------------------------------------
# (preposition, positive, negative); the negative carries the preposition used the correct way.
LOC = {'over', 'through', 'behind', 'near', 'across from', 'toward', 'inside', 'on', 'beyond', 'in', 'around', 'among', 'under', 'onto', 'beside', 'upon', 'towards', 'past', 'at', 'into'}
PREPS = [
    ('on', 'You can count on my brother and I.', 'On Sunday my brother and I will cook. Count on my brother and me.'),
    ('at', 'The dog barked at my sister and I.', 'At noon my sister and I left. The dog barked at my sister and me.'),
    ('by', 'The report was written by Sam and I.', 'By Friday Sam and I will finish. The report was written by Sam and me.'),
    ('behind', 'Someone was walking behind my wife and I.', 'Behind the house my wife and I planted roses. Someone walked behind my wife and me.'),
    ('near', 'They parked their car near my wife and I.', 'Near the lake Tom and I found a bench. They parked near my wife and me.'),
    ('beside', 'She sat down beside my uncle and I.', 'Beside the river my uncle and I fished. She sat beside my uncle and me.'),
    ('against', 'Half the board voted against Priya and I.', 'Against all odds Priya and I won. They voted against Priya and me.'),
    ('towards', 'The dog came running towards my sister and I.', 'Towards evening my sister and I went home. The dog ran towards my sister and me.'),
    ('toward', 'The crowd moved toward my brother and I.', 'Toward the end Ben and I left. The crowd moved toward my brother and me.'),
    ('around', 'The children gathered around my parents and I.', 'Around ten Maria and I arrived. The children gathered around my parents and me.'),
    ('over', 'The plane flew right over my parents and I.', 'Over coffee my parents and I talked. The plane flew over my parents and me.'),
    ('under', 'The branch fell just under my cousin and I.', 'Under the bridge my cousin and I waited. The branch fell under my cousin and me.'),
    ('of', 'She is very fond of my husband and I.', 'Of course my husband and I agree. She is fond of my husband and me.'),
    ('in', 'She has a lot of faith in my brother and I.', 'In March Dev and I moved. She has faith in my brother and me.'),
    ('into', 'The cart almost ran into my aunt and I.', 'Into the room my aunt and I walked. The cart ran into my aunt and me.'),
    ('onto', 'The cat jumped onto my brother and I.', 'Onto the stage my brother and I climbed. The cat jumped onto my brother and me.'),
    ('upon', 'They looked down upon my family and I.', 'Upon arrival my family and I checked in. They looked down upon my family and me.'),
    ('across from', 'He sat across from my sister and I.', 'Across the bay Nina and I saw lights. He sat across from my sister and me.'),
    ('besides', 'Besides my colleague and I, nobody knew the code.', 'Besides, my colleague and I knew the code. Besides my colleague and me, nobody knew.'),
    ('except', 'Everybody had left except Lucas and I.', 'Except for rain, Lucas and I enjoyed the trip. Everybody left except Lucas and me.'),
    ('beyond', 'The problem is beyond my team and I.', 'Beyond the hill my team and I camped. The problem is beyond my team and me.'),
    ('inside', 'The secret stays inside my family and I.', 'Inside the tent my family and I slept. The secret stays inside my family and me.'),
    ('among', 'There was little agreement among my partner and I.', 'Among friends my partner and I relax. There was little agreement among my partner and me.'),
    ('through', 'The message went through my manager and I.', 'Through the window Hana and I watched. The message went through my manager and me.'),
    ('past', 'A bus sped past my cousin and I.', 'Past midnight my cousin and I woke. A bus sped past my cousin and me.'),
]
for prep, pos, neg in PREPS:
    pat = r'(?i)\b' + prep + r' ' + (NP1P if prep in LOC else NP1) + r' and (?P<target>(?-i:I))' + FOLLOW
    add('coord_obj_i_' + prep.replace(' ', '_'), pat, 'me', 'Grammar', 0.93,
        'After “' + prep + '” use “me”: “' + prep + ' … and me”.', pos, neg,
        fixes=pos.replace(' and I', ' and me', 1))

# --- verbs + "NP and I" -> "me" (verbs not in the base list) -----------------------------------------------
VERBS = [
    ('contact', 'contact|contacts|contacted|contacting', 'Please contact Dr. Rao and I.', 'Contact me. Dr. Rao and I contacted them.'),
    ('notify', 'notify|notifies|notified|notifying', 'They will notify my manager and I by email.', 'My manager and I were notified. Notify my manager and me.'),
    ('inform', 'inform|informs|informed|informing', 'Please inform my wife and I of any change.', 'My wife and I were informed. Inform my wife and me.'),
    ('visit', 'visit|visits|visited|visiting', 'Come and visit my husband and I in July.', 'My husband and I visited Rome. Visit my husband and me.'),
    ('welcome', 'welcome|welcomes|welcomed|welcoming', 'They warmly welcomed my family and I.', 'My family and I welcomed them. They welcomed my family and me.'),
    ('hire', 'hire|hires|hired|hiring', 'The agency will hire Dana and I tomorrow.', 'Dana and I hired a plumber. The agency hired Dana and me.'),
    ('assist', 'assist|assists|assisted|assisting', 'Our neighbours assisted my wife and I today.', 'My wife and I assisted them. They assisted my wife and me.'),
    ('accompany', 'accompany|accompanies|accompanied|accompanying', 'Will you accompany my sister and I to the airport?', 'My sister and I accompanied them. Accompany my sister and me.'),
    ('greet', 'greet|greets|greeted|greeting', 'The staff greeted my parents and I at the door.', 'My parents and I greeted the staff. They greeted my parents and me.'),
    ('hug', 'hug|hugs|hugged|hugging', 'Grandma hugged my brother and I.', 'My brother and I hugged her. Grandma hugged my brother and me.'),
    ('kiss', 'kiss|kisses|kissed|kissing', 'She kissed my husband and I.', 'My husband and I kissed her goodbye. She kissed my husband and me.'),
    ('surprise', 'surprise|surprises|surprised|surprising', 'The party surprised my wife and I.', 'My wife and I surprised them. The party surprised my wife and me.'),
    ('beat', 'beat|beats|beating', 'They beat my brother and I at chess.', 'My brother and I beat them. They beat my brother and me.'),
    ('defeat', 'defeat|defeats|defeated|defeating', 'They defeated Amir and I in the final.', 'Amir and I defeated them. They defeated Amir and me.'),
    ('impress', 'impress|impresses|impressed|impressing', 'The view impressed my sister and I.', 'My sister and I were impressed. The view impressed my sister and me.'),
    ('annoy', 'annoy|annoys|annoyed|annoying', 'The noise really annoyed my roommate and I.', 'My roommate and I were annoyed. The noise annoyed my roommate and me.'),
    ('disappoint', 'disappoint|disappoints|disappointed|disappointing', 'The result disappointed Leila and I.', 'Leila and I disappointed nobody. The result disappointed Leila and me.'),
    ('forgive', 'forgive|forgives|forgave|forgiven|forgiving', 'Please forgive my husband and I.', 'My husband and I forgave them. Forgive my husband and me.'),
    ('trust', 'trust|trusts|trusted|trusting', 'The bank does not trust my cousin and I.', 'Omar and I trusted the bank. The bank does not trust my cousin and me.'),
    ('hear', 'hear|hears|heard|hearing', 'Nobody could hear my friend and I.', 'My friend and I heard nothing. Nobody could hear my friend and me.'),
    ('watch', 'watch|watches|watched|watching', 'The guards were watching my cousin and I.', 'My cousin and I watched them. They watched my cousin and me.'),
    ('serve', 'serve|serves|served|serving', 'The waiter served my uncle and I.', 'My uncle and I served dinner. The waiter served my uncle and me.'),
    ('guide', 'guide|guides|guided|guiding', 'A local guide guided my wife and I.', 'My wife and I guided them. A guide guided my wife and me.'),
    ('lead', 'led|leads|leading', 'A local guide led my wife and I.', 'My wife and I led the way. A guide led my wife and me.'),
    ('encourage', 'encourage|encourages|encouraged|encouraging', 'Our teacher encouraged Kofi and I to apply.', 'Kofi and I encouraged them. Our teacher encouraged Kofi and me to apply.'),
    ('thank_for', 'thank|thanks|thanked|thanking', 'We want to thank Dr. Rao and I.', 'Thanks, Dr. Rao and I agree. We want to thank Dr. Rao and me.'),
    ('offer', 'offer|offers|offered|offering', 'The shop offered my sister and I.', 'My sister and I offered help. The shop offered my sister and me.'),
    ('ask_for', 'bother|bothers|bothered|bothering', 'The constant noise bothered my roommate and I.', 'My roommate and I bothered nobody. The noise bothered my roommate and me.'),
    ('stop', 'stop|stops|stopped|stopping', 'A police officer stopped my brother and I.', 'My brother and I stopped for gas. A police officer stopped my brother and me.'),
    ('catch', 'catch|catches|caught|catching', 'The rain caught my cousin and I in town.', 'Tomas and I caught the early train. The rain caught my cousin and me in town.'),
]
# the "to/for/with/from/about/without/like" prepositions and the verbs in usage.json (invite, tell, ask, send, give, call,
# email, text, meet, help, join, ...) are already handled by usage.x_and_I_object
NAME_VERBS = {'contact', 'notify', 'inform', 'hire', 'assist', 'accompany', 'greet', 'hug', 'kiss', 'surprise', 'impress', 'annoy', 'disappoint', 'forgive', 'encourage', 'bother', 'thank_for', 'defeat', 'beat'}
seen = set()
for vid, forms, pos, neg in VERBS:
    if vid in seen:
        continue
    seen.add(vid)
    pat = r'(?i)\b' + '(?:' + forms + r') ' + (NP1 if vid in NAME_VERBS else NP1P) + r' and (?P<target>(?-i:I))' + FOLLOW
    add('coord_obj_i_v_' + vid, pat, 'me', 'Grammar', 0.93,
        'After a verb use “me”: “… and me”.', pos, neg, fixes=pos.replace(' and I', ' and me', 1))

# --- "between X and <subject pronoun>" -----------------------------------------------------------------------
for sub, ob in [('he', 'him'), ('she', 'her'), ('they', 'them'), ('we', 'us')]:
    pat = (r'(?i)\bbetween ' + NP1W + r' and (?P<target>' + sub + r')' + FOLLOW)
    pos = {'he': 'It stays between you and he.', 'she': 'It stays between Tom and she.',
           'they': 'There is a deal between the council and they.', 'we': 'Nothing came between the leaders and we.'}[sub]
    neg = 'Between you and ' + ob + ' it stays secret. Between us, he knows. Between Tom and ' + ob + ' there is trust.'
    add('between_x_and_' + sub, pat, ob, 'Grammar', 0.95,
        'After “between” use “' + ob + '”, not “' + sub + '”.', pos, neg, fixes=pos.replace(' and ' + sub, ' and ' + ob))
# "between X and I" with a first conjunct that is not "you" (usage/grammar cover "between you and I")
pat = r'(?i)\bbetween ' + NP1WN + r' and (?P<target>(?-i:I))' + FOLLOW
add('between_x_and_i', pat, 'me', 'Grammar', 0.95, 'After “between” use “me”, not “I”.',
    'It stays between my brother and I.',
    'Between my brother and me the argument ended. Between Tom and me there is trust.',
    fixes='It stays between my brother and me.')
pat = r'(?i)\bbetween (?:him|her|them|us) and (?P<target>(?-i:I))' + FOLLOW
add('between_pron_and_i', pat, 'me', 'Grammar', 0.95, 'After “between” use “me”, not “I”.',
    'There is no secret between him and I.', 'Between him and me there is no secret. Between them and me there is trust.',
    fixes='There is no secret between him and me.')

# --- subject pronoun after a preposition, alone ---------------------------------------------------------------
SUBJ_PREPS = ['to', 'for', 'with', 'from', 'about', 'at', 'by', 'of', 'without', 'behind', 'beside', 'near', 'toward',
              'towards', 'around', 'against', 'upon', 'onto', 'into', 'among', 'under', 'over']
I_PREPS = {'for', 'with', 'from', 'about', 'at', 'without', 'behind', 'beside', 'near', 'around', 'against', 'toward',
           'towards', 'into', 'upon'}
ex = {
    ('to', 'I'): ('Please give the keys to I.', 'to me'), ('for', 'he'): ('The surprise is for he.', 'for him'),
    ('with', 'she'): ('I went to the market with she.', 'with her'), ('from', 'they'): ('We received a gift from they.', 'from them'),
    ('about', 'we'): ('Please talk about we.', 'about us'),
}
SUBJ_FOLLOW = r'(?:\.["”’)]*(?:\s|$)|[!?;:]|$|\s+(?:and|or|but|yesterday|today|tomorrow|tonight|later|soon|again)\b)'
SUBJ_FOLLOW_HE = r'(?:\s+(?:and|or)\b)'
SUBJ_FOLLOW_FOR = r'(?:\.["”’)]*(?:\s|$)|[!?]|\s+(?:and|or)\b)'
# "for" and "to" lead the way; each preposition x each pronoun gets its own rule.
PAIRS = [('I', 'me'), ('he', 'him'), ('she', 'her'), ('we', 'us'), ('they', 'them')]
SENT = {
    'to': 'Please give the keys to {s}.', 'for': 'The surprise party was for {s}.', 'with': 'Nobody wants to work with {s}.',
    'from': 'The message came from {s}.', 'about': 'Everyone was talking about {s}.', 'at': 'The dog barked at {s}.',
    'by': 'The letter was signed by {s}.', 'of': 'Nobody was afraid of {s}.', 'without': 'They left without {s}.',
    'behind': 'The car stopped right behind {s}.', 'beside': 'A stranger sat down beside {s}.', 'near': 'They live near {s}.',
    'toward': 'The crowd moved toward {s}.', 'towards': 'The dog ran towards {s}.', 'around': 'The kids gathered around {s}.',
    'against': 'Nobody voted against {s}.', 'upon': 'Fortune smiled upon {s}.', 'onto': 'The cat jumped onto {s}.',
    'into': 'A truck crashed into {s}.', 'among': 'There was no quarrel among {s}.', 'beyond': 'The plan went beyond {s}.',
    'under': 'The note was slipped under {s}.', 'over': 'The storm hung over {s}.', 'on': 'You can always count on {s}.',
    'in': 'She has complete faith in {s}.',
}
NEG_SUBJ = {
    'to': 'Please give the keys to me. To be or not to be, I decide. I wrote to him.',
    'for': 'The party was for her. For I am sure of it, he said. It is for them.',
    'with': 'Nobody wants to work with us. With he gone, it is quiet.',
    'from': 'The message came from them. From I know, it is fine.',
    'about': 'Everyone was talking about him. About I think, it is fine.',
    'at': 'The dog barked at them. At I think, it is fine.',
    'by': 'The letter was signed by her. By he who dares, it was said.',
    'of': 'Nobody was afraid of him. Of I know, none is true.',
    'without': 'They left without us. Without he knowing, it was done.',
    'behind': 'The car stopped right behind me.', 'beside': 'A stranger sat beside her.', 'near': 'They live near us.',
    'toward': 'The crowd moved toward him.', 'towards': 'The dog ran towards them.', 'around': 'The kids gathered around her.',
    'against': 'Nobody voted against me.', 'upon': 'Fortune smiled upon us.', 'onto': 'The cat jumped onto him.',
    'into': 'A truck crashed into them.', 'among': 'There was no quarrel among us.', 'beyond': 'The plan went beyond her.',
    'under': 'The note was slipped under me.', 'over': 'The storm hung over them.', 'on': 'You can always count on me.',
    'in': 'She has complete faith in him.',
}
for prep in SUBJ_PREPS:
    for sub, ob in PAIRS:
        if sub == 'I':
            continue  # "divided into I, II", "at I.S.O.": Roman numerals and initialisms
        fol = SUBJ_FOLLOW_HE if sub == 'he' else SUBJ_FOLLOW_FOR if prep == 'for' else SUBJ_FOLLOW  # "for he" is a typo of "for the"; "for they, like..." is literary "for"
        pat = r'(?i)\b' + prep + r' (?P<target>' + sub + r')' + fol
        pos = SENT[prep].format(s=sub + (' and Sam' if sub == 'he' else ''))
        neg = NEG_SUBJ[prep]
        add('prep_' + prep + '_' + sub.lower(), pat, ob, 'Grammar', 0.94,
            'After “' + prep + '” use “' + ob + '”, not “' + sub + '”.', pos, neg,
            fixes=pos.replace(' ' + sub + ' and', ' ' + ob + ' and').replace(' ' + sub + '.', ' ' + ob + '.'))

# --- subject-case pronouns after a verb that needs an object --------------------------------------------------
# verb forms never take a clause directly ("told he ..." has no reading)
VOBJ = [
    ('told', 'told|tell|tells|telling', 'to|that|about|how|what|where|why|if|not|everyone|the|a|an|my|our|their|his|her|your|me|us|him|them|it', 'told'),
    ('gave', 'gave|give|gives|giving', 'the|a|an|my|our|their|his|her|your|some|this|that|these|those|me|us|him|them|it|everything|something|nothing|all|no|two|three|another', 'gave'),
    ('sent', 'sent|send|sends|sending', 'the|a|an|my|our|their|his|her|your|some|this|that|these|those|me|us|him|them|it|everything|something|all|no|two|three|another|to', 'sent'),
    ('brought', 'brought|bring|brings|bringing', 'the|a|an|my|our|their|his|her|your|some|this|that|these|those|me|us|him|them|it|everything|something|all|no|two|three|another|to', 'brought'),
    ('helped', 'helped|help|helps|helping', 'to|with|find|fix|move|carry|clean|pack|plan|write|learn|understand|get|build|make|do|pay|choose|decide|solve', 'helped'),
    ('showed', 'showed|show|shows|showing', 'the|a|an|my|our|their|his|her|your|some|this|that|these|those|me|us|him|them|it|everything|something|all|how|where|what|around|to', 'showed'),
    ('asked', 'asked|ask|asks|asking', 'to|for|about|if|whether|why|how|what|where|when|a|the|my|our|their|his|her|your|me|us|him|them|it|the|every|some', 'asked'),
    ('let', 'let|lets|letting', 'go|in|out|know|have|do|be|see|come|stay|finish|leave|try|take|join|help|speak|talk|handle|decide|think|use|borrow|win|play|stand|sleep|rest|read|ride|drive|sit|run|walk|enter|wait|pass|through|off|down|up|alone|know', 'let'),
    ('made', 'made|make|makes|making', 'feel|cry|laugh|smile|do|see|look|sound|wonder|worry|realize|understand|say|speak|pay|leave|wait|stay|wear|think|apologize|promise|clean|work|try|stop|go|come|sit|stand|angry|happy|sad|sick|crazy|nervous|uncomfortable|jealous|mad|late|afraid', 'made'),
]
def vobj_rule(vid, forms, foll, _):
    for sub, ob in [('I', 'me'), ('he', 'him'), ('she', 'her'), ('we', 'us'), ('they', 'them')]:
        pass
for vid, forms, foll, _ in VOBJ:
    for sub, ob in PAIRS:
        if vid in ('told', 'asked') and sub == 'I':
            continue  # the tagger reads "told I" as a name, so the engine never lets the edit through
        sbj = r'(?-i:I)' if sub == 'I' else sub
        # the person before the verb ("She told he ...") rules out the passive ("I was told he ...") and relatives
        pat = (r'(?i)\b(?:I|we|you|they|he|she|it|who|(?-i:[A-Z][a-z]+)|please|just|also|already|never|always|then|to|will|would|'
               r'can|could|should|did not|didn[’\']t|don[’\']t|do not|had|have|has|might|may|must|shall|ll|d|ve) '
               r'(?:' + forms + r') (?P<target>' + sbj + r') (?:' + foll + r')\b')
        sentence = {
            'told': 'She told {s} to wait outside.', 'gave': 'Maya gave {s} the wrong form.',
            'sent': 'Maya sent {s} a long email.', 'brought': 'Aunt Jo brought {s} some cake.',
            'thanked': 'We thanked {s} for all the help.', 'helped': 'Maya helped {s} move the sofa.',
            'invited': 'My cousin invited {s} to the wedding.', 'hired': 'The company hired {s} as a designer.',
            'paid': 'The landlord paid {s} the deposit back.', 'showed': 'Maya showed {s} the old harbour.',
            'asked': 'Maya asked {s} to leave the room.', 'called': 'My sister called {s} about the trip.',
            'met': 'The manager met {s} at the station.', 'joined': 'Our friends joined {s} at the table.',
            'let': 'Her parents never let {s} go out alone.', 'made': 'Maya made {s} feel better.',
            'saw': 'The neighbour saw {s} walking home.',
        }[vid]
        neg = {
            'told': 'I was told he would call. She told him to wait. I have been told they left. He said she told me so.',
            'gave': 'The clerk gave him the wrong form. I gave her a gift. They gave us nothing.',
            'sent': 'My boss sent him a long email. I sent them a note.',
            'brought': 'Aunt Jo brought them some cake. I brought her a book.',
            'thanked': 'We thanked her for all the help. They thanked him.',
            'helped': 'The neighbours helped them move the sofa. We helped her carry it.',
            'invited': 'My cousin invited us to the wedding. Whoever invited he who is late will pay.',
            'hired': 'The company hired her as a designer. When she hired him, I smiled.',
            'paid': 'The landlord paid me the deposit back. I paid him back.',
            'showed': 'The guide showed them the old harbour. The test showed he was healthy. The report showed she had left.',
            'asked': 'The teacher asked him to leave the room. Asked if he could stay, he said no. She asked he come. It asked we wait.',
            'called': 'My sister called him about the trip. The coach called they were late.',
            'met': 'The manager met them at the station. The man I met he is nice.',
            'joined': 'Our friends joined us at the table. The club joined they were there.',
            'let': 'Her parents never let her go out alone. Let he who is without sin cast the first stone.',
            'made': 'The news made her feel better. I made he who laughed pay.',
            'saw': 'The neighbour saw him walking home. I saw she was upset. They saw we were late.',
        }[vid]
        # drop negatives that the pattern would catch (checked later by the generator's assertion)
        pos = sentence.format(s=sub)
        add('vobj_' + vid + '_' + sub.lower(), pat, ob, 'Grammar', 0.9,
            'After “' + vid + '” use “' + ob + '”, not “' + sub + '”.', pos, neg,
            fixes=pos.replace(' ' + sub + ' ', ' ' + ob + ' ', 1))
