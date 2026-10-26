"""Adjective for adverb after a verb of doing, adverb for adjective after a linking verb, "real" for "really", an
adjective standing in front of a verb, "very" in front of a verb, and the hard/hardly, late/lately, near/nearly,
high/highly, short/shortly pairs."""
from core import add, cover, tail, END, IDS

AD_TAIL = tail()

# (adjective, adverb, verb forms, positive, negative)
ADJ_FOR_ADV = [
    ('perfect', 'perfectly', 'work|works|worked|working|run|runs|ran|running|fit|fits|fitted|function|functions|functioned|match|matches|matched|perform|performs|performed|operate|operates|operated|load|loads|loaded|print|prints|printed|install|installs|installed|compile|compiles|compiled|sync|syncs|synced',
     'The new printer works perfect with my laptop.', 'The new printer works perfectly with my laptop. It is a perfect match. The perfect fit is hard to find.'),
    ('proper', 'properly', 'work|works|worked|working|run|runs|ran|running|function|functions|functioned|load|loads|loaded|display|displays|displayed|install|installs|installed|connect|connects|connected|start|starts|started|behave|behaves|behaved',
     'The website does not load proper on my phone.', 'The website does not load properly on my phone. Proper care is needed. It needs proper tools.'),
    ('smooth', 'smoothly', 'run|runs|ran|running|go|goes|went|going|work|works|worked|working|move|moves|moved|moving|operate|operates|operated|proceed|proceeds|proceeded|flow|flows|flowed',
     'The meeting went smooth from start to finish.', 'The meeting went smoothly from start to finish. The road is smooth. A smooth ride helps.'),
    ('careful', 'carefully', 'drive|drives|drove|driving|listen|listens|listened|listening|read|reads|reading|check|checks|checked|checking|think|thinks|thought|thinking|choose|chooses|chose|choosing|handle|handles|handled|handling|proceed|proceeds|proceeded|plan|plans|planned|planning|step|steps|stepped|stepping|walk|walks|walked|walking|speak|speaks|spoke|speaking|work|works|worked|working|look|looks|looked|looking',
     'Please listen careful to the instructions.', 'Please listen carefully to the instructions. Be careful. A careful driver slows down.'),
    ('quick', 'quickly', 'ran|run|runs|running|walk|walks|walked|walking|move|moves|moved|moving|respond|responds|responded|responding|reply|replies|replied|replying|answer|answers|answered|answering|act|acts|acted|acting|finish|finishes|finished|finishing|learn|learns|learned|learnt|learning|react|reacts|reacted|reacting|decide|decides|decided|deciding|change|changes|changed|changing|spread|spreads|spreading|grow|grows|grew|growing|work|works|worked|working|eat|eats|ate|eating|speak|speaks|spoke|speaking|think|thinks|thought|thinking|get better|gets better|got better',
     'She ran quick to catch the bus.', 'She ran quickly to catch the bus. A quick reply would help. He took a quick walk.'),
    ('easy', 'easily', 'win|wins|won|winning|learn|learns|learned|learnt|learning|break|breaks|broke|breaking|find|finds|found|finding|pass|passes|passed|passing|solve|solves|solved|solving|fix|fixes|fixed|fixing|connect|connects|connected|connecting|access|accesses|accessed|accessing|spot|spots|spotted|spotting|understand|understands|understood|understanding|fail|fails|failed|failing|forget|forgets|forgot|forgetting|adapt|adapts|adapted|adapting|forgive|forgives|forgave|forgiving',
     'The new students learn easy with these videos.', 'The new students learn easily with these videos. Take it easy. The exam was easy.'),
    ('quiet', 'quietly', 'speak|speaks|spoke|speaking|talk|talks|talked|talking|walk|walks|walked|walking|move|moves|moved|moving|sit|sits|sat|sitting|sleep|sleeps|slept|sleeping|work|works|worked|working|sing|sings|sang|singing|whisper|whispers|whispered|whispering|breathe|breathes|breathed|breathing',
     'Please speak quiet in the library.', 'Please speak quietly in the library. Keep quiet. A quiet night helps.'),
    ('honest', 'honestly', 'speak|speaks|spoke|speaking|answer|answers|answered|answering|reply|replies|replied|replying|respond|responds|responded|responding|talk|talks|talked|talking|report|reports|reported|reporting|argue|argues|argued|arguing',
     'You must answer honest in the interview.', 'You must answer honestly in the interview. To be honest, it works. An honest answer is best.'),
    ('polite', 'politely', 'ask|asks|asked|asking|answer|answers|answered|answering|reply|replies|replied|replying|decline|declines|declined|declining|refuse|refuses|refused|refusing|respond|responds|responded|responding|speak|speaks|spoke|speaking|talk|talks|talked|talking|behave|behaves|behaved|behaving|request|requests|requested|requesting|greet|greets|greeted|greeting',
     'He asked polite if he could join us.', 'He asked politely if he could join us. A polite request works. Be polite.'),
    ('patient', 'patiently', 'wait|waits|waited|waiting|listen|listens|listened|listening|work|works|worked|working|sit|sits|sat|sitting',
     'The children waited patient for their turn.', 'The children waited patiently for their turn. Be patient. A patient child waits.'),
    ('fluent', 'fluently', 'speak|speaks|spoke|speaking|write|writes|wrote|writing|read|reads|reading|talk|talks|talked|talking',
     'She speaks fluent now after two years in Spain.', 'She speaks fluently now after two years in Spain. She speaks fluent Spanish. Her Spanish is fluent.'),
    ('regular', 'regularly', 'exercise|exercises|exercised|exercising|visit|visits|visited|visiting|check|checks|checked|checking|attend|attends|attended|attending|meet|meets|met|meeting|update|updates|updated|updating|train|trains|trained|training|practice|practise|practices|practises|practiced|practised|practicing|practising|post|posts|posted|posting|clean|cleans|cleaned|cleaning',
     'You should exercise regular to stay healthy.', 'You should exercise regularly to stay healthy. Regular exercise is healthy. She cleans regular offices.'),
    ('immediate', 'immediately', 'reply|replies|replied|replying|respond|responds|responded|responding|answer|answers|answered|answering|stop|stops|stopped|stopping|leave|leaves|left|leaving|call|calls|called|calling|act|acts|acted|acting|react|reacts|reacted|reacting|notify|notifies|notified|notifying|contact|contacts|contacted|contacting',
     'Please reply immediate if you can attend.', 'Please reply immediately if you can attend. An immediate reply is needed. Our immediate family came.'),
    ('prompt', 'promptly', 'respond|responds|responded|responding|reply|replies|replied|replying|answer|answers|answered|answering|pay|pays|paid|paying|act|acts|acted|acting|arrive|arrives|arrived|arriving',
     'The clinic responds prompt to every request.', 'The clinic responds promptly to every request. A prompt reply is expected. Be prompt.'),
    ('rapid', 'rapidly', 'grow|grows|grew|growing|change|changes|changed|changing|spread|spreads|spreading|move|moves|moved|moving|rise|rises|rose|rising|fall|falls|fell|falling|develop|develops|developed|developing|expand|expands|expanded|expanding|increase|increases|increased|increasing|decrease|decreases|decreased|decreasing|evolve|evolves|evolved|evolving',
     'The company is growing rapid in the north.', 'The company is growing rapidly in the north. Rapid growth is expected. A rapid rise followed.'),
    ('brief', 'briefly', 'explain|explains|explained|explaining|describe|describes|described|describing|say|says|said|saying|mention|mentions|mentioned|mentioning|speak|speaks|spoke|speaking|summarize|summarizes|summarized|summarizing|state|states|stated|stating|outline|outlines|outlined|outlining',
     'Please explain brief at the start of the call.', 'Please explain briefly at the start of the call. Give a brief summary. Please be brief.'),
    ('clear', 'clearly', 'speak|speaks|spoke|speaking|write|writes|wrote|writing|explain|explains|explained|explaining|think|thinks|thought|thinking|communicate|communicates|communicated|communicating|express|expresses|expressed|expressing|state|states|stated|stating|talk|talks|talked|talking',
     'You need to write clear for the customers.', 'You need to write clearly for the customers. Stand clear of the doors. Loud and clear.'),
    ('thorough', 'thoroughly', 'check|checks|checked|checking|clean|cleans|cleaned|cleaning|read|reads|reading|test|tests|tested|testing|review|reviews|reviewed|reviewing|examine|examines|examined|examining|search|searches|searched|searching|research|researches|researched|researching|prepare|prepares|prepared|preparing|plan|plans|planned|planning|explain|explains|explained|explaining',
     'Please check thorough before you sign.', 'Please check thoroughly before you sign. A thorough check is best. Be thorough.'),
    ('efficient', 'efficiently', 'work|works|worked|working|run|runs|ran|running|operate|operates|operated|operating|use|uses|used|using|function|functions|functioned|functioning|perform|performs|performed|performing|manage|manages|managed|managing|handle|handles|handled|handling',
     'The new engine runs efficient at any speed.', 'The new engine runs efficiently at any speed. An efficient engine saves fuel. It is efficient.'),
    ('effective', 'effectively', 'work|works|worked|working|communicate|communicates|communicated|communicating|function|functions|functioned|functioning|operate|operates|operated|operating|lead|leads|led|leading|manage|manages|managed|managing',
     'You must communicate effective with the team.', 'You must communicate effectively with the team. An effective plan helps. It is effective.'),
    ('accurate', 'accurately', 'predict|predicts|predicted|predicting|measure|measures|measured|measuring|report|reports|reported|reporting|record|records|recorded|recording|describe|describes|described|describing|reflect|reflects|reflected|reflecting|work|works|worked|working|estimate|estimates|estimated|estimating',
     'The sensor measures accurate in the dark.', 'The sensor measures accurately in the dark. An accurate sensor is worth it. The sensor is accurate.'),
    ('correct', 'correctly', 'spell|spells|spelled|spelt|spelling|pronounce|pronounces|pronounced|pronouncing|answer|answers|answered|answering|install|installs|installed|installing|configure|configures|configured|configuring|work|works|worked|working|function|functions|functioned|functioning|load|loads|loaded|loading|display|displays|displayed|displaying|apply|applies|applied|applying',
     'Most students answered correct on the test.', 'Most students answered correctly on the test. The correct spelling is here. Give a correct answer.'),
    ('automatic', 'automatically', 'update|updates|updated|updating|sync|syncs|synced|syncing|save|saves|saved|saving|start|starts|started|starting|restart|restarts|restarted|restarting|renew|renews|renewed|renewing|install|installs|installed|installing|download|downloads|downloaded|downloading|lock|locks|locked|locking|shut down|shuts down|backs up|backed up|back up',
     'The app updates automatic when you connect.', 'The app updates automatically when you connect. An automatic update runs at night. Choose automatic mode.'),
    ('gentle', 'gently', 'handle|handles|handled|handling|speak|speaks|spoke|speaking|touch|touches|touched|touching|press|presses|pressed|pressing|push|pushes|pushed|pushing|wash|washes|washed|washing|stir|stirs|stirred|stirring|hold|holds|held|holding|ask|asks|asked|asking',
     'You must press gentle on the screen.', 'You must press gently on the screen. Use a gentle touch. He is gentle with animals.'),
    ('beautiful', 'beautifully', 'sing|sings|sang|singing|write|writes|wrote|writing|dance|dances|danced|dancing|play|plays|played|playing|paint|paints|painted|painting|speak|speaks|spoke|speaking|draw|draws|drew|drawing|cook|cooks|cooked|cooking|perform|performs|performed|performing',
     'The choir sang beautiful at the wedding.', 'The choir sang beautifully at the wedding. It was a beautiful song. She is beautiful.'),
    ('nice', 'nicely', 'speak|speaks|spoke|speaking|talk|talks|talked|talking|sing|sings|sang|singing|write|writes|wrote|writing|dance|dances|danced|dancing|ask|asks|asked|asking',
     'The little girl asked nice for another cookie.', 'The little girl asked nicely for another cookie. Play nice. She has a nice voice.'),
    ('bad', 'badly', 'sing|sings|sang|singing|play|plays|played|playing|perform|performs|performed|performing|behave|behaves|behaved|behaving|treat|treats|treated|treating|write|writes|wrote|writing|dance|dances|danced|dancing|drive|drives|drove|driving|speak|speaks|spoke|speaking|sleep|sleeps|slept|sleeping|handle|handles|handled|handling|manage|manages|managed|managing|communicate|communicates|communicated|communicating',
     'The team played bad in the second half.', 'The team played badly in the second half. A bad game happens. Do not go bad.'),
]


def build():
    # ---- an adjective where a verb needs an adverb
    ids = []
    for adj, adv, verbs, pos, neg in ADJ_FOR_ADV:
        if adj == 'bad':
            # "treated me bad": the object stands between the verb and the adjective
            pat = rf"(?i)\b(?:{verbs})(?: (?:me|him|her|us|them|you|it|everyone|people|customers|staff|workers|others))? (?P<target>{adj}){AD_TAIL}"
        else:
            pat = rf"(?i)\b(?:{verbs}) (?P<target>{adj}){AD_TAIL}"
        ids.append(add(
            f'adv_{adj}', pat, adv, 'Grammar' if adj not in ('nice', 'bad') else 'Word choice',
            0.88 if adj not in ('nice', 'bad', 'quick') else 0.8,
            f'To say how an action is done, use the adverb “{adv}”, not the adjective “{adj}”.', pos, neg))
    cover('Adjective for adverb', 'an adjective after a verb of doing where an adverb is needed: works perfect, loads proper, went smooth, listen careful, ran quick, learn easy, speak quiet, answer honest, ask polite, wait patient, speak fluent, exercise regular, reply immediate, respond prompt, grow rapid, explain brief, write clear, check thorough, runs efficient, measures accurate, spelled correct, updates automatic, press gentle, sang beautiful, asked nice, played bad (only when the adjective ends the clause or a word that cannot be a noun follows; "drive safe", "think different", "hold tight", "go slow", "run free", "feel free" are left alone)', ids)

    # ---- an adverb where a linking verb needs an adjective
    ids = []
    linking = [
        ('taste', r'tastes?|tasted', [('badly', 'bad'), ('nicely', 'nice'), ('deliciously', 'delicious'), ('wonderfully', 'wonderful'),
                                      ('awfully', 'awful'), ('terribly', 'terrible'), ('horribly', 'horrible'), ('amazingly', 'amazing'),
                                      ('perfectly', 'perfect'), ('strangely', 'strange'), ('sweetly', 'sweet'), ('fantastically', 'fantastic')],
         'The coffee tastes {adv}.', 'The coffee tastes {adj}. The chef tasted it {adv}. It tastes {adv} sweet and rich.'),
        ('look', r'looks?|looked', [('beautifully', 'beautiful'), ('nicely', 'nice'), ('wonderfully', 'wonderful'),
                                    ('amazingly', 'amazing'), ('terribly', 'terrible'), ('awfully', 'awful'), ('horribly', 'horrible'),
                                    ('fantastically', 'fantastic'), ('gorgeously', 'gorgeous'), ('perfectly', 'perfect')],
         'Your new office looks {adv}.', 'Your new office looks {adj}. The room looks {adv} decorated.'),
        ('smell', r'smells?|smelled|smelt', [('badly', 'bad'), ('nicely', 'nice'), ('wonderfully', 'wonderful'),
                                             ('deliciously', 'delicious'), ('terribly', 'terrible'), ('horribly', 'horrible'),
                                             ('awfully', 'awful'), ('strangely', 'strange')],
         'The kitchen smells {adv}.', 'The kitchen smells {adj}. The hound smells {adj} too, and the kitchen smells fine.'),
        ('sound', r'sounds?|sounded', [('nicely', 'nice'), ('wonderfully', 'wonderful'), ('amazingly', 'amazing'), ('fantastically', 'fantastic'),
                                       ('badly', 'bad')],
         'That idea sounds {adv}.', 'That idea sounds {adj}. The speakers sound {adv} balanced.'),
        ('feel', r'feels?|felt', [('nicely', 'nice'), ('wonderfully', 'wonderful'), ('comfortably', 'comfortable'), ('smoothly', 'smooth'),
                                  ('softly', 'soft'), ('happily', 'happy'), ('amazingly', 'amazing'), ('fantastically', 'fantastic')],
         'The new sofa feels {adv}.', 'The new sofa feels {adj}. It feels {adv} familiar.'),
        ('seem', r'seems?|seemed', [('nicely', 'nice'), ('wonderfully', 'wonderful')],
         'The plan seems {adv}.', 'The plan seems {adj}. It seemed {adv} balanced.'),
    ]
    for vkey, verbs, pairs, pos_t, neg_t in linking:
        for adv, adj in pairs:
            if vkey == 'smell':
                subj = r"(?:it|this|that|something|everything|there|the (?:food|room|kitchen|house|car|fridge|milk|bathroom|coffee|soup|garden|basement|office))"
                pat = rf"(?i)\b{subj} (?:{verbs}) (?P<target>{adv})(?:[.!?;:)\n\"”]|\s*$)"
            elif vkey == 'look':
                pat = rf"(?i)\b(?:{verbs}) (?P<target>{adv})(?:[.!?;:)\n\"”]|\s*$|\s+(?:in|on|with|today|now|there)\b)"
            else:
                pat = rf"(?i)\b(?:{verbs}) (?P<target>{adv})(?:[.!?;:)\n\"”]|\s*$|\s+(?:to|with|today|now|when|but|for)\b)"
            ids.append(add(
                f'link_{vkey}_{adv}', pat, adj, 'Grammar', 0.9,
                f'After “{vkey}” describe the thing with the adjective “{adj}”, not the adverb “{adv}”.',
                pos_t.format(adv=adv, adj=adj), neg_t.format(adv=adv, adj=adj)))
    cover('Adverb for adjective', 'an adverb after a linking verb where an adjective is needed: tastes badly/nicely/deliciously ..., looks beautifully/nicely/wonderfully ..., smells badly/nicely ..., sounds nicely/wonderfully ..., feels nicely/comfortably/smoothly ..., seems nicely (only when the adverb ends the clause; "looked angrily", "felt terribly sorry", "looks beautifully made" and "feel badly" are left alone)', ids)
