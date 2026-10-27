"""its / it's, your / you're, their / there / they're, he's / his, mine / yours', reflexive forms, each other's."""
from lib import *

B = r'(?:\s|[.,;:!?]|$)'
PREPS_ANY = ('of|in|on|at|by|for|with|from|to|into|onto|under|over|about|through|despite|within|without|around|during|beyond|against|'
             'toward|towards|upon|across|behind|near|beside|among')

# ---- its' and it's own ------------------------------------------------------------------------------------------
add('its_apostrophe', r"(?i)(?:^|\s)(?P<target>its['’])\s+[a-z]", 'its', 'Possessive', 0.97,
    '“Its” has no apostrophe: it is already possessive.', 'The dog wagged its’ tail.',
    "The word 'its' is a possessive. It's here. The dogs' bowls are full.", fixes='The dog wagged its tail.')
add('its_own_contraction', r"(?i)\b(?P<target>it['’]s) own\b", 'its', 'Possessive', 0.96,
    '“It’s” means “it is”; for ownership use “its”.', 'The robot has it’s own voice.',
    'The robot has its own voice. A robot of its own is all she wants.', fixes='The robot has its own voice.')

# ---- "it's" before a noun that only a possessive can introduce ------------------------------------------------------
NOUN_GROUPS = [
    ('parts', 'tail|wings|wing|legs|leg|eyes|eye|head|body|face|skin|fur|coat|nest|paws|paw|feet|ears|nose|mouth|teeth|claws|horns|neck|back|belly|roots|branches|leaves|trunk|lid|handle|label|cover|screen|display|camera|battery|buttons|button|keys|ports|port|cable|charger|case|packaging|surface|edges|edge|corners|interior|exterior|appearance|texture|flavor|flavour|aroma|smell|taste|ingredients',
     'tail', 'eyes', 'I admire it’s eyes in the sun.'),
    ('attrs', 'size|shape|color|colour|weight|length|width|height|depth|price|cost|value|speed|capacity|volume|brightness|resolution|memory|storage|location|position|temperature|age|name|names|owner|owners|creator|creators|maker|makers|parent|parents|mother|offspring|young|habitat|territory|prey',
     'size', 'price', 'I know it’s price is high.'),
    ('abstract', 'kind|sake|entirety|way|purpose|function|features|feature|capabilities|origin|source|home|borders|members|staff|customers|users|employees|leaders|founder|founders|president|citizens|population|goals|goal|mission|charm|appeal|toll|peak|limit|limits|roots|core',
     'purpose', 'function', 'I love it’s function in the plan.'),
]
for gid, nouns, w1, w2, vpos in NOUN_GROUPS:
    pat = r'(?i)\b(?:' + PREPS_ANY + r') (?P<target>it[’\']s) (?:' + nouns + r')' + B
    pos = 'Everyone talked about it’s ' + w1 + '.'
    add('its_after_prep_' + gid, pat, 'its', 'Possessive', 0.95, '“It’s” means “it is”; for ownership use “its”.', pos,
        'It’s a long way. Everyone talked about its ' + w1 + '. It’s time to go.',
        fixes='Everyone talked about its ' + w1 + '.')
VERBS_ITS = ('love|loved|like|liked|hate|hated|read|use|used|know|understand|explain|describe|improve|change|fix|break|broke|remove|replace|clean|'
             'damage|destroy|protect|respect|support|share|explore|visit|lose|lost|gain|reach|serve|justify|judge|measure|test|buy|sell|'
             'own|take|took|give|gave|show|hold|keep|lend|follow|check|checked|see|saw|admire|praise|criticize|notice|noticed|appreciate')
for gid, nouns, w1, w2, vpos in NOUN_GROUPS:
    pat = (r'(?i)\b(?:' + VERBS_ITS + r') (?P<target>it[’\']s) (?:' + nouns + r') (?:is|was|are|were|has|had|will|would|can|could|should|does|did|looks|seems|means|shows|feels|sounds|makes|gives|of|in|on|at|for|to|with|from|by)\b')
    add('its_after_verb_' + gid, pat, 'its', 'Possessive', 0.94, '“It’s” means “it is”; for ownership use “its”.', vpos,
        'I know it’s a big price. I know its price is high. I think it’s time for a break.',
        fixes=vpos.replace('it’s', 'its'))
NOUNS_ALL = '|'.join(g[1] for g in NOUN_GROUPS)
add('its_clause_noun_verb', r'(?im)' + CS + r'(?P<target>It[’\']s) (?:' + NOUNS_ALL + r')(?: [a-z]+)? (?:is|was|are|were|has|had|will|would|can|could|should|does|did|looks|seems|means|shows|feels|sounds|makes|gives)\b',
    'Its', 'Possessive', 0.95, '“It’s” means “it is”; for ownership use “its”.', 'The robot is cute. It’s head is round.',
    'The robot is cute. Its head is round. It’s a cute robot. It’s been a long day.', fixes='The robot is cute. Its head is round.')

# ---- "its" for "it's" before an adjective or adverb ---------------------------------------------------------------------
ITSCTX = (r'(?:^|[.!?]["”’)]*\s+|[:;]\s+|,\s+(?:(?:and|but|so|yet)\s+)?|\b(?:and|but|so|because|if|think|thinks|thought|hope|hopes|know|knows|knew|'
          r'guess|wonder|bet|doubt|sure|glad|afraid|clear|since|maybe|perhaps|probably|obviously|apparently|actually|honestly|yes|no|oh|ok|okay|yeah|hey|well|wow|why|unless|until|once|'
          r'although|though|while|whether)\s+)')
ITS_FOLLOW = r'(?:[.!?;:]|$|\s+(?:to|for|that|because|if|when|enough|too|as|in|on|at|with|about|now|today|tomorrow|tonight|here|there|again|already|yet|lol|haha)(?:\s|[.,;:!?]|$))'
ITS_ADJ = [
    ('weather', 'warm|sunny|windy|cloudy|foggy|bright|humid|chilly|freezing|stormy|rainy|dry|wet', 'I think its sunny in here.'),
    ('evaluation', 'wonderful|cute|ugly|delicious|exciting|frustrating|useless', 'I know its wonderful for kids.'),
    ('kind', 'normal|common|rare|natural|false', 'I think its normal to forget.'),
    ('size', 'big|small|huge|tiny|long|short|quiet|loud|slow|fast|quick|heavy|soft|smooth|rough|dirty|clean', 'Since its small for what you get, buy two.'),
]
for gid, adjs, pos in ITS_ADJ:
    add('its_for_its_adj_' + gid, r'(?i)' + ITSCTX + r'(?P<target>its) (?:' + adjs + r')' + ITS_FOLLOW, "it's", 'Grammar', 0.94,
        '“Its” is possessive; here you mean “it is”: “it’s”.', pos,
        'The bird flapped its cold wings. The dog licked its small paws. Its cold weather is famous. The house lost its open charm. '
        'It is known for its long and narrow body.', fixes=pos.replace('its ', 'it’s ', 1))
ITS_ADV = r'(?:only|pretty|honestly|absolutely|barely|currently|even)'
add('its_for_its_adv', r"(?i)\b(?P<target>its) " + ITS_ADV + r" (?:a|an|the|not|so|too|about|like|my|your|our|his|her|their|going|gonna|been|being|over|done|fine|good|great|ok|okay|true|hard|easy|cold|hot)\b",
    "it's", 'Grammar', 0.93, '“Its” is possessive; here you mean “it is”: “it’s”.', 'I guess its only a phase.',
    'I guess it’s only a phase. The tree lost its only branch. The robot has its pretty colours.', fixes='I guess it’s only a phase.')

# ---- your / you're -------------------------------------------------------------------------------------------------
AN_LIST = 'expert|idiot|angel|adult|amazing|awesome|incredible|honest|excellent|athlete|artist|actor|accountant|engineer|animal|absolute|ugly|old|angry|easy|only'
add('your_an', r'(?i)\b(?P<target>your) an (?:' + AN_LIST + r')\b', "you're", 'Grammar', 0.96, '“Your” is possessive; here you mean “you are”: “you’re”.',
    'I can tell your an expert.', 'I can tell you’re an expert. Bring your own umbrella.', fixes="I can tell you're an expert.")
YOUR_A = ('good|great|bad|nice|real|true|total|complete|big|small|huge|beautiful|wonderful|amazing|terrible|'
          'fantastic|natural|born|fool|friend|genius|star|hero|legend|liar|joke|pain|saint|angel|idiot|jerk|man|woman|person|nurse|doctor|'
          'teacher|student|lawyer|mother|father|dad|mom|fan|member|part|winner|loser|keeper|gem|treasure|blessing|lifesaver|champ|'
          'champion|beast|monster|machine|rock|diamond|queen|king|boss|pro|professional|expert|master|wizard|beauty|sweetheart|piece')
add('your_a', r'(?i)\b(?P<target>your) a (?-i:(?:' + YOUR_A + r'))' + B, "you're", 'Grammar', 0.95,
    '“Your” is possessive; here you mean “you are”: “you’re”.', 'I know your a good cook.',
    'I know you’re a good cook. Your a priori claim is weak. Your A grade is safe.', fixes="I know you're a good cook.")
add('your_the', r'(?i)\b(?P<target>your) (?-i:the) (?:best|worst|one|only|same|greatest|most|boss|king|queen|man|woman|guy|girl|winner|leader|owner|manager|ones)\b', "you're", 'Grammar', 0.94, '“Your” is possessive; here you mean “you are”: “you’re”.',
    'Everyone agrees your the best cook here.', 'Everyone agrees you’re the best cook here. Enter your The Shop login.',
    fixes="Everyone agrees you're the best cook here.")
add('your_not', r'(?i)\b(?P<target>your) not (?:a|an|the|going|sure|alone|able|only|just|really|supposed|allowed|doing|being|there|here|ready|wrong|right|crazy|serious|kidding|joking|too|so|very|even|that|my|their|to|in|on|at|from|coming|looking|gonna|getting)' + B,
    "you're", 'Grammar', 0.95, '“Your” is possessive; here you mean “you are”: “you’re”.', 'Please relax, your not alone.',
    'Please relax, you’re not alone. Bring your not-for-profit paperwork.', fixes="Please relax, you're not alone.")
add('your_going_to', r'(?i)\b(?P<target>your) going to (?:be|have|get|need|want|love|hate|like|miss|regret|enjoy|learn|find|win|lose|see|do|make|take|go|come|call|say|tell|ask|try|help|know|think|feel|laugh|cry|pay|buy|sell|stay|leave|start|stop)\b',
    "you're", 'Grammar', 0.95, '“Your” is possessive; here you mean “you are”: “you’re”.', 'Trust me, your going to love this place.',
    'Trust me, you’re going to love this place. Thanks for your going to the trouble.', fixes="Trust me, you're going to love this place.")
add('your_gonna', r'(?i)\b(?P<target>your) gonna\b', "you're", 'Grammar', 0.96, '“Your” is possessive; here you mean “you are”: “you’re”.',
    'Hurry up or your gonna miss the bus.', 'Hurry up or you’re gonna miss the bus.', fixes="Hurry up or you're gonna miss the bus.")
YOUR_CTX = (r'(?:^|[.!?]["”’)]*\s+|[:;]\s+|,\s+|\b(?:if|when|because|that|think|thinks|hope|hopes|guess|know|knows|sure|since|while|whether|but|so|as|glad|happy|wonder|bet|see|say|said|says|heard|hear|though|although|unless|until|once|why|how|what)\s+)')
YOUR_FOLLOW = r'(?:[.!?;:]|$|\s+(?:to|for|with|about|at|on|in|from|by|too|enough|as|than|today|tonight|now|again|still|already|yet|really|so|lol|haha|though|right|then)(?:\s|[.,;:!?]|$))'
ADJ_GROUPS = [
    ('feel', 'hungry|thirsty|ill|sad|angry|mad|nervous|worried|scared|afraid|stuck|mistaken|upset|annoyed|bored|excited|nuts|insane|drunk|awake|asleep|alone'),
    ('quality', 'silly|smart|clever|rude|nice|cute|pretty|beautiful|gorgeous|handsome|weird|strange|unique|perfect|great|terrible|horrible|wonderful|fantastic|excellent|adorable|generous|honest|brave|lazy'),
    ('status', 'fired|hired|promoted|invited|alive|engaged|divorced|retired|pregnant|offline'),
]
YPOS = {'feel': ('I guess your hungry today.', "I guess you're hungry today."),
        'quality': ('Honestly, your wonderful.', "Honestly, you're wonderful."),
        'status': ('I heard your engaged today.', "I heard you're engaged today.")}
YNEG = {'feel': 'I guess you’re hungry today. Your tired eyes need rest. Check your cold storage.',
        'quality': 'Honestly, you’re wonderful. Your brilliant idea won. I love your funny stories.',
        'status': 'I heard you’re engaged today. Your moving boxes arrived. Your first day is Monday.'}
for gid, adjs in ADJ_GROUPS:
    pos, fx = YPOS[gid]
    add('your_adj_' + gid, r'(?i)' + YOUR_CTX + r'(?P<target>your) (?:' + adjs + r')' + YOUR_FOLLOW, "you're", 'Grammar', 0.94,
        '“Your” is possessive; here you mean “you are”: “you’re”.', pos, YNEG[gid], fixes=fx)
    add('their_adj_' + gid, r'(?i)' + YOUR_CTX + r'(?P<target>their) (?:' + adjs + r')' + YOUR_FOLLOW, "they're", 'Grammar', 0.93,
        '“Their” is possessive; here you mean “they are”: “they’re”.',
        pos.replace('your', 'their'), YNEG[gid].replace('you’re', 'they’re').replace('Your', 'Their').replace('your', 'their'),
        fixes=fx.replace("you're", "they're"))
YR_NOUNS = [
    ('body', 'hair|eyes|smile|face|hands|hand|feet|shoes|hat|dress|shirt|jacket|coat|bag|glasses|voice|laugh|handwriting|skin|nails|teeth|haircut|outfit|tattoo|ring',
     'I love you’re hair.', "I love your hair."),
    ('tech', 'computer|username|website|site|inbox|screen|folder|schedule|software|app|device|network|wifi|connection',
     'Please check you’re inbox.', 'Please check your inbox.'),
    ('life', 'house|home|apartment|flat|family|dog|cat|wife|husband|kids|children|parents|mother|father|sister|brother|boss|team|company|business|job|work|birthday|wedding|address|number|name|age|order|package|ticket|flight|booking|reservation',
     'Is that you’re car in the driveway?', "Is that your car in the driveway?"),
]
YR_VERBS = ('like|love|hate|read|check|share|send|give|use|take|bring|forget|find|lose|need|want|have|got|saw|see|miss|appreciate|is that|is this|are those|are these|'
            'with|from|about|of|for|to|on|in|at|by|into|without|under|near|over|after|before')
for gid, nouns, pos, fx in YR_NOUNS:
    pat = r'(?i)\b(?:' + YR_VERBS + r') (?P<target>you[’\']re) (?:own |new |old |)(?:' + nouns + r')\b'
    if gid == 'life':
        pos, fx = 'Is that you’re bike in the driveway?', 'Is that your bike in the driveway?'
        nouns = nouns + '|bike|bicycle|truck|van|scooter|boat|garage|garden|yard|kitchen|bedroom|bathroom|room'
        pat = r'(?i)\b(?:' + YR_VERBS + r') (?P<target>you[’\']re) (?:own |new |old |)(?:' + nouns + r')\b'
    add('youre_noun_' + gid, pat, 'your', 'Possessive', 0.94, '“You’re” means “you are”; for ownership use “your”.', pos,
        'I know you’re ready. I think you’re right. Tell me you’re coming over.', fixes=fx)
add('youre_own', r"(?i)\b(?P<target>you['’]re) own\b", 'your', 'Possessive', 0.96, '“You’re” means “you are”; for ownership use “your”.',
    'Do it at you’re own pace.', 'Do it at your own pace. You’re on your own.', fixes='Do it at your own pace.')
add('youre_after_prep', r"(?i)\b(?:of|in|on|at|for|with|from|by|about|to|into|onto|under|over|within|without|through|toward|towards|against|across|behind|near|upon|around|during|beyond|among|between|along|inside|outside) (?P<target>you['’]re)\b",
    'your', 'Possessive', 0.93, '“You’re” means “you are”; after a preposition use “your”.', 'Thank you for you’re kindness.',
    'Thank you for your kindness. I know what you’re doing. We will see if you’re ready. In case you’re wondering, yes. Given you’re busy, I wait.',
    fixes='Thank you for your kindness.')

# ---- their / there / they're ----------------------------------------------------------------------------------------
TH_NOUNS = 'kids|children|parents|mother|father|mom|dad|son|daughter|wife|husband|family|friends|names|house|car|cars|dog|cat|boss|teacher|baby|room|phone|neighbors|neighbours|customers|clients|employees|students'
add('there_own', r"(?i)\b(?:on|of|in|for|by|with|to|at) (?P<target>there) own" + B, 'their', 'Word choice', 0.96,
    'Here you need “their”, the possessive.', 'The kids made dinner on there own.',
    'The kids made dinner on their own. Is there own-brand milk? Over there, on their own farm.',
    fixes='The kids made dinner on their own.')
add('there_possessive_start', r'(?im)' + CS + r'(?P<target>There) (?:' + TH_NOUNS + r') (?:is|are|was|were|has|have|had|isn[’\']t|aren[’\']t|wasn[’\']t|weren[’\']t|don[’\']t|doesn[’\']t|didn[’\']t)\b',
    'Their', 'Word choice', 0.94, 'Here you need “their”, the possessive.', 'There kids are noisy.',
    'Their kids are noisy. There are kids outside. There, kids are noisy.', fixes='Their kids are noisy.')
add('there_possessive_prep', r'(?i)\b(?:in|at|on|of|for|with|from|by|about|to|into|under|near) (?P<target>there) (?:' + TH_NOUNS + r')\b',
    'their', 'Word choice', 0.94, 'Here you need “their”, the possessive.', 'We stayed at there house for a week.',
    'We stayed at their house for a week. We stayed at the house over there. I put it in there.',
    fixes='We stayed at their house for a week.')
add('theyre_possessive', r"(?i)\b(?:in|at|on|of|for|with|from|by|about|to|into|under|near) (?P<target>they['’]re) (?:own|" + TH_NOUNS + r')\b',
    'their', 'Word choice', 0.95, '“They’re” means “they are”; for ownership use “their”.', 'They did it on they’re own.',
    'They did it on their own. I know they’re ready.', fixes='They did it on their own.')
add('theyre_possessive_start', r"(?im)" + CS + r"(?P<target>They['’]re) (?:" + TH_NOUNS + r") (?:is|are|was|were|has|have|had|isn[’']t|aren[’']t|wasn[’']t|weren[’']t|don[’']t|doesn[’']t|didn[’']t)\b",
    'Their', 'Word choice', 0.94, '“They’re” means “they are”; for ownership use “their”.', 'They’re kids are noisy.',
    'Their kids are noisy. They’re kids at heart.', fixes='Their kids are noisy.')
add('their_going_to_start_mid', r"(?i)\b(?:think|thinks|thought|hope|hopes|guess|bet|wonder|sure) (?P<target>their) (?:(?:coming|leaving|trying)(?:\s+(?:to|today|tonight|tomorrow|soon|now|late|early|with|for)\b|[.,;:!?]|$)|not (?:coming|going|here|there|ready|sure|late)\b|(?:a|an) (?:nice|good|great|lovely|kind|friendly|happy|big|small|lot)\b|the (?:best|worst|one|only|same|first|last|ones)\b)",
    "they're", 'Grammar', 0.9, '“Their” is possessive; here you mean “they are”: “they’re”.', 'I hope their not coming.',
    'I hope they’re not coming. I regret their leaving early. Their coming was a surprise.', fixes="I hope they're not coming.")

# ---- he's / she's / his for the possessive and the contraction --------------------------------------------------------
HE_NOUNS = ('car|cars|house|home|phone|laptop|bag|keys|wallet|bike|book|books|shoes|hat|coat|jacket|name|mother|father|mom|dad|wife|husband|brother|sister|'
            'boss|team|dog|cat|room|desk|office|email|number|address|password|account|idea|fault|turn|birthday|wedding|family|parents|kids|children|son|daughter|'
            'teacher|manager|company|business|opinion|decision|voice|face|hair|eyes|hands|signature|handwriting|computer|screen|schedule|plan|project|story|work|job')
for pr, pos_, fx_ in [('he', 'He’s car is parked outside.', 'His car is parked outside.'),
                      ('she', 'She’s car is parked outside.', 'Her car is parked outside.')]:
    rep = 'His' if pr == 'he' else 'Her'
    add(pr + 's_possessive_start', r'(?im)' + CS + r'(?P<target>' + pr + r'[’\']s) (?:' + HE_NOUNS + r')(?: [a-z]+)? (?:is|was|are|were|has|had|will|would|can|could|should|does|did|looks|seems|means|shows|feels|sounds|makes|gives)\b',
        rep.lower(), 'Possessive', 0.94, '“' + pr.capitalize() + '’s” means “' + pr + ' is”; for ownership use “' + rep.lower() + '”.', pos_,
        pr.capitalize() + '’s a teacher. ' + rep + ' car is parked outside. ' + pr.capitalize() + '’s been here a week.', fixes=fx_)
    add(pr + 's_possessive_prep', r"(?i)\b(?:of|in|on|at|with|from|to|about|into|under|over|near|behind|beside|within|without|through|against) (?P<target>(?-i:" + pr + r")['’]s) (?:" + HE_NOUNS + r"|life|lives)\b",
        rep.lower(), 'Possessive', 0.94, '“' + pr.capitalize() + '’s” means “' + pr + ' is”; for ownership use “' + rep.lower() + '”.',
        'They are staying at ' + pr + '’s house.',
        'They are staying at ' + rep.lower() + ' house. I know what ' + pr + '’s doing. From now on ' + pr + '’s going home. Tell me why ' + pr + '’s late. The plan in He’s reign.',
        fixes='They are staying at ' + rep.lower() + ' house.')
add('his_a', r'(?i)\b(?P<target>his) a (?-i:(?:' + YOUR_A + r'))' + B, "he's", 'Grammar', 0.94, '“His” is possessive; here you mean “he is”: “he’s”.',
    'I know his a good cook.', 'I know he’s a good cook. His a priori claim is weak.', fixes="I know he's a good cook.")
add('his_an', r'(?i)\b(?P<target>his) an (?:' + AN_LIST + r')\b', "he's", 'Grammar', 0.95, '“His” is possessive; here you mean “he is”: “he’s”.',
    'I can tell his an expert.', 'I can tell he’s an expert. Bring his own umbrella.', fixes="I can tell he's an expert.")
add('his_the', r'(?i)\b(?P<target>his) (?-i:the) (?:best|worst|one|only|same|first|last|boss|owner|manager|leader|winner|man|guy|reason|problem|king)\b', "he's", 'Grammar', 0.94,
    '“His” is possessive; here you mean “he is”: “he’s”.', 'Everyone agrees his the best cook here.',
    'Everyone agrees he’s the best cook here.', fixes="Everyone agrees he's the best cook here.")
add('his_gonna', r'(?i)\b(?P<target>his) (?:gonna|not (?:a|an|the|going|sure|alone|able|ready|here|there|coming)|going to (?:be|have|get|need|want|love|hate|like|miss|win|lose|see|do|make|take|go|come|call|say|tell|ask|try|help|know|stay|leave|start|stop))' + B,
    "he's", 'Grammar', 0.93, '“His” is possessive; here you mean “he is”: “he’s”.', 'Hurry up or his gonna miss the bus.',
    'Hurry up or he’s gonna miss the bus. His going to Paris was a surprise.', fixes="Hurry up or he's gonna miss the bus.")

# ---- mine / yours' / hers' / ours' / theirs' -----------------------------------------------------------------------
add('mines_of', r'(?i)\b(?:friend|cousin|colleague|neighbor|neighbour|buddy|teacher|brother|sister|relative|coworker|co-worker|classmate|uncle|aunt|boss|student) of (?P<target>mines)\b',
    'mine', 'Grammar', 0.96, 'The pronoun is “mine”; there is no “mines”.', 'A friend of mines called yesterday.',
    'A friend of mine called yesterday. The owner of mines in Chile called.', fixes='A friend of mine called yesterday.')
add('mines_pair', r'(?i)\b(?:yours|hers|his|theirs|ours) (?:or|and) (?P<target>mines)\b', 'mine', 'Grammar', 0.95,
    'The pronoun is “mine”; there is no “mines”.', 'Is that bag yours or mines?', 'Is that bag yours or mine?', fixes='Is that bag yours or mine?')
add('mines_is', r'(?i)\b(?:one|ones|seat|bag|book|car|phone|desk|coat|pen|keys|room|bed|turn|idea|fault|job|ticket|laptop|cup|mug|table) (?:is|are|was|were) (?P<target>mines)(?:[.!?,;]|$)',
    'mine', 'Grammar', 0.94, 'The pronoun is “mine”; there is no “mines”.', 'Careful, that seat is mines.',
    'Careful, that seat is mine. The gold mines were a job.', fixes='Careful, that seat is mine.')
for w in ['yours', 'hers', 'ours', 'theirs']:
    pat = r"(?i)\b(?:is|are|was|were|be|been|isn[’']t|aren[’']t|it[’']s|that[’']s|this|these|those) (?:all |just |only |also |not |still )?(?P<target>" + w + r"['’])(?:[.!?,;]|$)"
    add('apostrophe_' + w, pat, w, 'Possessive', 0.95, '“' + w.capitalize() + '” never takes an apostrophe.',
        {'yours': 'This book is yours’.', 'hers': 'The red bag is hers’.', 'ours': 'The decision was ours’.', 'theirs': 'The dog is theirs’.'}[w],
        {'yours': 'This book is yours. He said ‘it is yours’ twice.', 'hers': 'The red bag is hers.', 'ours': 'The decision was ours.', 'theirs': 'The dog is theirs.'}[w],
        fixes={'yours': 'This book is yours.', 'hers': 'The red bag is hers.', 'ours': 'The decision was ours.', 'theirs': 'The dog is theirs.'}[w])

# ---- reflexive spellings the dictionary pass cannot judge ---------------------------------------------------------
add('theirself', r'(?i)\b(?P<target>theirselfs?|themselfs|themselfes|themselve)\b', 'themselves', 'Spelling', 0.95,
    'The plural reflexive is “themselves”.', 'They taught theirself to swim.', 'They taught themselves to swim. A singular they can use themself.',
    fixes='They taught themselves to swim.')
add('hisself', r'(?i)\b(?P<target>hisselfs?|hiself|himselfs|himselves)\b', 'himself', 'Spelling', 0.95, 'The reflexive is “himself”.',
    'He taught hisself to swim.', 'He taught himself to swim.', fixes='He taught himself to swim.')
add('herselfs', r'(?i)\b(?P<target>herselfs|hersef|herselves)\b', 'herself', 'Spelling', 0.95, 'The reflexive is “herself”.',
    'She taught herselfs to swim.', 'She taught herself to swim.', fixes='She taught herself to swim.')
add('myselfs', r'(?i)\b(?P<target>myselfs|myselves|mysef|mysel)\b', 'myself', 'Spelling', 0.95, 'The reflexive is “myself”.',
    'I taught myselfs to swim.', 'I taught myself to swim.', fixes='I taught myself to swim.')
add('ourself', r'(?i)\b(?P<target>ourselfs|ourselfes|ourselve|ourselvs|oursleves)\b', 'ourselves', 'Spelling', 0.95, 'The reflexive is “ourselves”.',
    'We taught ourselfs to swim.', 'We taught ourselves to swim.', fixes='We taught ourselves to swim.')
add('youself', r'(?i)\b(?P<target>youself|yourselfs|yourselve|yourslef|yoursef|yoursel)\b', 'yourself', 'Spelling', 0.94, 'The reflexive is “yourself”.',
    'Please help youself to coffee.', 'Please help yourself to coffee.', fixes='Please help yourself to coffee.')
add('itselfs', r'(?i)\b(?P<target>itselfs|itselves|itsel|itsefl|itlself)\b', 'itself', 'Spelling', 0.95, 'The reflexive is “itself”.',
    'The cat cleaned itselfs.', 'The cat cleaned itself.', fixes='The cat cleaned itself.')

# ---- each other's, one another's ------------------------------------------------------------------------------------
add('each_others', r"(?i)\beach (?P<target>others['’]?)\s", "other’s", 'Possessive', 0.96, 'Say “each other’s”: “each other” takes a singular possessive.',
    'The twins borrow each others toys.', "The twins borrow each other's toys.", fixes='The twins borrow each other’s toys.')
add('one_anothers', r"(?i)\bone (?P<target>anothers['’]?)\s", "another’s", 'Possessive', 0.96, 'Say “one another’s”.',
    'They respect one anothers views.', "They respect one another's views.", fixes='They respect one another’s views.')
