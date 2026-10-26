"""who / whom / whoever / whomever / whose / who's / which-for-people."""
from lib import *

PERSON = (r'(?:man|men|woman|women|person|people|guy|guys|girl|boy|lady|gentleman|friend|friends|colleague|colleagues|teacher|'
          r'doctor|student|students|manager|someone|somebody|anyone|anybody|everyone|everybody|nobody|those|candidate|'
          r'employee|customer|client|neighbor|neighbour|woman|child|children|kids|author|writer|artist|player|boss|partner)')
PRON = r'(?:I|we|you|they|he|she)'
SUBJV = (r'(?:can|could|would|will|should|might|may|must|cannot|do|did|does|have|had|always|never|often|usually|only|just|also|bought|borrowed|received|rented|hired|confided|ran|told|heard|inherited|spoke|speak|talked|talk|work|worked|works|gave|give|sent|send|wrote|write|trust|trusted|rely|relied|depend|care|cared|'
         r'play|played|argued|agreed|danced|travelled|traveled|shared|lent|owe|owed|sold|showed|reported|complained|applied|'
         r'voted|live|lived|stayed|went|go|did|learned|studied|trained|turned|looked|listened|waited|met|meet|asked|spent|'
         r'live|lived|share|shared|ask|sat|stood|walked|walk|came|come|live|fight|fought|compete|competed|negotiate|negotiated)')

# --- preposition + "who" after a person noun --------------------------------------------------------------------
WPREPS = [
    ('to', 'The woman to who I spoke was very kind.', 'The woman to whom I spoke was kind. I know who I spoke to. The man who spoke to me left.'),
    ('for', 'The candidate for who I voted lost.', 'The candidate for whom I voted lost. I like you for who you are.'),
    ('with', 'The colleague with who I work is away.', 'The colleague with whom I work is away. Be honest about who you are with.'),
    ('from', 'The person from who I bought it was rude.', 'The person from whom I bought it was rude. I know who I bought it from.'),
    ('about', 'The friend about who I spoke called.', 'The friend about whom I spoke called. I told you about who I met.'),
    ('by', 'The teacher by who we sat retired.', 'The teacher by whom we sat retired. Pick who I was taught by.'),
    ('of', 'The man of who we spoke has left.', 'The man of whom we spoke has left. Think of who we know.'),
    ('against', 'The player against who we competed won.', 'The player against whom we competed won. See who we played against.'),
    ('on', 'The friend on who I rely lives far away.', 'The friend on whom I rely lives far away. Decide who I can rely on.'),
    ('upon', 'The people upon who we depend are here.', 'The people upon whom we depend are here.'),
    ('behind', 'The people behind who we sat were loud.', 'The people behind whom we sat were loud. Find who we sat behind.'),
    ('among', 'The students among who I studied are famous.', 'The students among whom I studied are famous.'),
    ('without', 'The people without who we could not finish are thanked.', 'The people without whom we could not finish are thanked.'),
    ('near', 'The neighbour near who we live is away.', 'The neighbour near whom we live is away.'),
    ('toward', 'The people toward who we ran were friendly.', 'The people toward whom we ran were friendly.'),
    ('beside', 'The man beside who we sat was friendly.', 'The man beside whom we sat was friendly.'),
    ('under', 'The manager under who I trained has retired.', 'The manager under whom I trained has retired.'),
    ('in', 'The person in who I confided kept the secret.', 'The person in whom I confided kept the secret.'),
]
for prep, pos, neg in WPREPS:
    pat = r'(?i)\b' + PERSON + ' ' + prep + ' (?P<target>who) ' + PRON + ' ' + SUBJV + r'\b'
    add('whom_after_' + prep, pat, 'whom', 'Grammar', 0.93, 'After “' + prep + '” use “whom”.', pos, neg,
        fixes=pos.replace(' who ', ' whom ', 1))

# Sentence-start questions: "At who did you look?" (To/For/With/From/By/Of/About with pronoun subjects are in usage.to_whom)
AUX = r'(?:should|do|did|does|shall|would|will|can|could|must|might|am|are|is|was|were|have|has|had)'
SUBJ_Q = r'(?:this|that|it|these|those|the|my|your|his|her|their|our|everyone|anyone|someone|nobody|everybody|anybody|somebody|(?-i:[A-Z][a-z]+))'
SQ = {
    'At': 'At who did you look?', 'In': 'In who do you trust?', 'On': 'On who can I rely?', 'Against': 'Against who did they play?',
    'Among': 'Among who did you sit?', 'Between': 'Between who did you choose?', 'Behind': 'Behind who did they stand?',
    'Beside': 'Beside who did you sit?', 'Near': 'Near who do you live?', 'Toward': 'Toward who did they run?',
    'Towards': 'Towards who did she turn?', 'Without': 'Without who can you work?', 'Under': 'Under who did you study?',
    'Over': 'Over who did he rule?', 'Through': 'Through who did you hear?', 'Into': 'Into who did he crash?',
    'Around': 'Around who do you feel safe?',
}
for prep, ex in SQ.items():
    pat = r'(?im)' + CS + prep + r' (?P<target>who (?P<aux>' + AUX + ')) ' + r'(?:' + PRON + '|' + SUBJ_Q + r')\b'
    add('whom_start_' + prep.lower(), pat, 'whom ${aux}', 'Grammar', 0.93, 'After “' + prep.lower() + '” use “whom”.', ex,
        prep + ' whom did you look? Who did you see? ' + prep + ' who knows what.', fixes=ex.replace(' who ', ' whom ', 1))

# "Whom" as a subject
WHOM_SUBJ = r'(?:is|was|has|have|had|will|would|can|could|should|might|may|shall)'
add('whom_is_ing', r'(?im)' + CS + r'(?P<target>Whom) (?:is|was) (?:[a-z]+ing|there|here|next|responsible|available|in charge)\b', 'Who',
    'Grammar', 0.94, 'The question asks for the subject of the verb: use “who”.', 'Whom is calling at this hour?',
    'Who is calling at this hour? Whom is she calling? Whom was he talking to?', fixes='Who is calling at this hour?')
add('whom_has_sub', r'(?im)' + CS + r'(?P<target>Whom) (?:has|have|had|will|would|can|could|should|might|may|shall) (?:been|be|come|go|won|left|done|made|taken|got|become|gone|arrived|called|replied|answered|signed|joined|applied|volunteered|agreed|said|told|seen|heard|read|written|finished|started|managed|paid|helped|asked)\b',
    'Who', 'Grammar', 0.94, 'The question asks for the subject of the verb: use “who”.', 'Whom will be there tomorrow?',
    'Who will be there tomorrow? Whom will you call tomorrow? Whom can we ask?', fixes='Who will be there tomorrow?')
MIDV = r'(?:know|knows|knew|ask|asked|asks|wonder|wondered|wonders|guess|see|tell|decide|decided|determine|say|sure|unsure|idea|clue|certain|remember|forget|find out|found out|figure out|learn)'
add('whom_mid_is', r'(?i)\b' + MIDV + r' (?P<target>whom) (?:is|was) (?:[a-z]+ing|there|here|next|responsible|available|in charge|going|the (?:best|worst|boss|manager|owner|author|winner|leader))\b',
    'who', 'Grammar', 0.93, 'Use “who” when it is the subject of the verb.', 'I wonder whom is coming to dinner.',
    'I wonder who is coming to dinner. I wonder whom he is inviting. Tell me whom she called.',
    fixes='I wonder who is coming to dinner.')
add('whom_mid_modal', r'(?i)\b' + MIDV + r' (?P<target>whom) (?:will|would|can|could|should|might|may|shall|has|have|had) (?:be|come|go|win|lead|help|join|attend|pay|take|get|handle|run|manage|answer|decide|make|do|work|replace|follow|speak|present|represent|serve|arrive|been|become|left|won|done|gone|taken|made|signed|applied|agreed)\b',
    'who', 'Grammar', 0.93, 'Use “who” when it is the subject of the verb.', 'Nobody knows whom will win the vote.',
    'Nobody knows who will win the vote. Nobody knows whom they will choose. I asked whom he can trust.',
    fixes='Nobody knows who will win the vote.')
add('whom_do_you_think', r'(?im)(?:' + CS + r'|\b(?:wonder|wondered|ask|asked|tell me|guess|know|knows|say|said)\s+)(?P<target>Whom) (?:do|did|would|will|should|can) (?:you|they|we|people|he|she|I) (?:think|believe|say|suppose|expect|guess|reckon|suspect|imagine|know) (?:is|was|will|would|can|could|has|had|should|might|may|are|were)\b',
    'Who', 'Grammar', 0.93, 'Here “who” is the subject of the verb that follows: use “who”.', 'Whom do you think will win the prize?',
    'Who do you think will win the prize? Whom do you think we should hire? Whom did you say they chose? I wonder who you think will win.',
    fixes='Who do you think will win the prize?')

# whoever / whomever
WE_V = r'(?:is|was|wants|needs|likes|wishes|asks|comes|has|can|will|would|could|should|may|might|did|does|chooses|decides|volunteers|arrives|gets|takes|makes|knows|says|thinks|believes|feels|plans|prefers|sees|hears|reads|works|lives|helps|loves|hates|enjoys|attends|joins|signs|enters|applies|qualifies|wins|finishes|answers|replies|responds|calls|shows|stays|goes|cares|tries|handles|owns|runs|leads|follows|gives|needs|remains|happens|signs|pays|fixes|breaks|starts|stops)'
for gid, verbs, pos, neg in [
    ('aux', r'(?:is|was|can|will|would|could|should|may|might|did|does|has|had)', 'Give the prize to whomever is first in line.',
     'Give the prize to whoever is first in line. Give it to whomever you like. Invite whomever she picks.'),
    ('s1', r'(?:wants|needs|likes|wishes|asks|comes|chooses|decides|volunteers|arrives|gets|takes|makes|knows|says|thinks|believes|feels|plans|prefers)', 'We will hire whomever wants the job.',
     'We will hire whoever wants the job. We will hire whomever they recommend. Hire whomever you want.'),
    ('s2', r'(?:sees|hears|reads|works|lives|helps|loves|hates|enjoys|attends|joins|signs|enters|applies|qualifies|wins|finishes|answers|replies|responds|calls|shows|stays|goes|cares|tries|handles|owns|runs|leads|follows|gives|remains|happens|pays|fixes|breaks|starts|stops)', 'Send the invitation to whomever wins the contest.',
     'Send the invitation to whoever wins the contest. Send it to whomever the judges select.'),
]:
    pat = r'(?i)\b(?P<target>whomever) ' + verbs + r'\b'
    add('whomever_' + gid, pat, 'whoever', 'Grammar', 0.93, '“Whomever” is an object; here the word is the subject of the next verb, so use “whoever”.', pos, neg,
        fixes=pos.replace('whomever', 'whoever'))
add('whom_to_whomever_subject_pronoun', r'(?i)\b(?P<target>whomsoever) (?:is|was|wants|needs|likes|wishes|asks|comes|has|can|will|would|could|should|may|might)\b',
    'whosoever', 'Grammar', 0.9, '“Whomsoever” is an object; here the word is the subject, so use “whosoever”.',
    'Give it to whomsoever wants it.', 'Give it to whosoever wants it. Give it to whomsoever you choose.', fixes='Give it to whosoever wants it.')

# --- whose / who's ----------------------------------------------------------------------------------------------
POSSNOUN_A = ('car|cars|house|houses|home|name|names|idea|ideas|fault|turn|job|jobs|phone|phones|dog|dogs|cat|cats|mother|father|mom|dad|son|'
              'daughter|wife|husband|brother|sister|parents|kids|children|bag|bags|coat|jacket|keys|key|wallet|bike|laptop|office|desk|seat|'
              'team|company|family|business|opinion|decision|responsibility|problem|signature|handwriting|voice|face|picture|photo|'
              'book|books|pen|pens|cup|mug|glass|plate|shoes|hat|umbrella|bottle|ticket|tickets|room|apartment|flat|table|chair|boat|'
              'computer|tablet|charger|passport|license|licence|address|number|email|account|password|profile|page|site|website|'
              'blog|channel|video|song|music|album|band|movie|film|show|story|article|post|comment|question|answer|point|mistake|'
              'choice|plan|project|code|work|money|birthday|wedding|party|class|lesson|grade|score|vote|side|role|place|spot|'
              'kitchen|garden|yard|garage|gym|school|college|university|city|country|town|village|street|shirt|dress|bed|toy|toys|'
              'luggage|suitcase|package|parcel|order|invoice|file|document|folder|report|draft|proposal')
WHOS_NOUN_GROUPS = [
    ('family', 'mother|father|mom|mum|dad|son|daughter|wife|husband|brother|sister|parents|kids|children|grandmother|grandfather|aunt|uncle|cousin|baby|dog|dogs|cat|cats|pet|family|house|home|car|cars',
     'Who’s daughter is that girl by the door?', 'Whose daughter is that girl by the door'),
    ('things', 'bag|bags|coat|jacket|keys|key|wallet|bike|laptop|office|desk|seat|phone|phones|computer|tablet|charger|passport|book|books|pen|cup|mug|glass|umbrella|bottle|ticket|tickets|luggage|suitcase|package|parcel|shoes|hat|shirt|dress|bed|toy|toys',
     'Who’s umbrella is this by the door?', 'Whose umbrella is this by the door?'),
    ('abstract', 'idea|ideas|fault|turn|name|names|job|jobs|opinion|decision|responsibility|problem|signature|handwriting|voice|face|picture|photo|mistake|choice|plan|project|code|birthday|wedding|party|class|lesson|grade|score|vote|side|role|place|spot|point|question|answer|story|article|post|comment|song|album|band|movie|film|show|blog|channel|video|page|site|website|profile|account|password|email|address|number|license|licence|team|company|business',
     'Who’s idea was it to leave early?', 'Whose idea was it to leave early?'),
]
for gid, nouns, pos, ok in WHOS_NOUN_GROUPS:
    pat = r'(?i)\b(?P<target>who[’\']s) (?:' + nouns + r')\b'
    add('whos_possessive_' + gid, pat, 'whose', 'Grammar', 0.94, '“Who’s” means “who is”; for ownership use “whose”.',
        pos, 'Who’s coming to the party? Who’s got the keys? ' + ok + '. Who’s been here before?',
        fixes=pos.replace('Who’s', 'Whose').replace('who’s', 'whose'))
# a few more frames
add('whos_after_person', r'(?i)\b(?:the|a|an|that|this|my|our) (?:man|woman|person|guy|girl|boy|lady|student|teacher|doctor|child|friend|neighbor|neighbour|customer|client|colleague|owner|author|artist) (?P<target>who[’\']s) (?:car|house|home|name|idea|fault|job|phone|dog|cat|mother|father|mom|dad|son|daughter|wife|husband|brother|sister|parents|kids|children|bag|bike|laptop|office|desk|seat|team|company|business|opinion|decision|voice|face|book|work|birthday|wedding|ticket|room|apartment|flat|computer|account|email|address|number)\b',
    'whose', 'Grammar', 0.95, '“Who’s” means “who is”; for ownership use “whose”.', 'I met a man who’s daughter plays the violin.',
    'I met a man whose daughter plays the violin. I met a man who’s tired. I met a man who’s got a violin.',
    fixes='I met a man whose daughter plays the violin.')
WHOSE_C = (r'(?:going to|gonna|going (?:tonight|with|too|first|home|out|there|along)|coming (?:tonight|today|with|to|over|along|too|later|tomorrow)|'
           r'been|got|there|here|ready|next|that|your|the (?:best|worst|boss|owner|manager|author|winner|leader|one|first|last|oldest|youngest)|he|she|they)')
add('whose_start_contraction', r'(?im)' + CS + r'(?P<target>Whose) ' + WHOSE_C + r'(?:\s|[.,;:!?]|$)', "Who's", 'Grammar', 0.94,
    '“Whose” asks about ownership; here you mean “who is” or “who has”: “who’s”.', 'Whose coming to the party tonight?',
    'Who’s coming to the party tonight? Whose idea was it? Whose is this? Whose keys are these? Whose coming-of-age story is it? Whose home is this?',
    fixes='Who’s coming to the party tonight?')
add('whose_mid_contraction', r'(?i)\b(?:know|knows|knew|ask|asked|wonder|wondered|guess|see|tell me|sure|idea|clue|care|matter) (?P<target>whose) ' + WHOSE_C.replace('been|got|', 'been|got|responsible for|') + r'(?:\s|[.,;:!?]|$)',
    "who's", 'Grammar', 0.93, '“Whose” asks about ownership; here you mean “who is” or “who has”: “who’s”.',
    'I wonder whose coming to the party.', 'I wonder who’s coming to the party. I wonder whose idea it was. I know whose keys these are. I know whose going rate this is.',
    fixes='I wonder who’s coming to the party.')
add('whose_after_someone', r'(?i)\b(?:someone|somebody|anyone|anybody|everyone|everybody|nobody|person|man|woman|guy|girl|people|those|friend|colleague|student|child|kid|neighbor|neighbour) (?P<target>whose) (?:been|got|gonna|ready|never|always|already)(?:\s|[.,;:!?]|$)',
    "who's", 'Grammar', 0.93, '“Whose” asks about ownership; here you mean “who is” or “who has”: “who’s”.',
    'Is there anyone whose been to Japan?', 'Is there anyone who’s been to Japan? Is there anyone whose dog is lost?',
    fixes='Is there anyone who’s been to Japan?')

# --- "which" for people --------------------------------------------------------------------------------------------
PERS = (r'(?:man|men|woman|women|guy|guys|girl|girls|boy|boys|friend|friends|colleague|colleagues|brother|sister|mother|father|'
        r'doctor|doctors|nurse|nurses|student|students|lady|ladies|gentleman|brother|sister|mother|father|neighbor|neighbour|neighbors|neighbours|'
        r'someone|somebody|anyone|anybody|everyone|everybody|nobody|employee|employees|customer|customers|boss|'
        r'professor|lawyer|volunteer|volunteers|candidate|candidates|artist|singer|actor|actress)')
WHV = (r'(?:is|was|are|were|has|have|had|will|would|can|could|should|may|might|did|does|lives|live|works|work|helped|helps|asked|asks|told|tells|'
       r'came|comes|went|goes|called|calls|wrote|writes|said|says|knows|knew|wants|wanted|needs|needed|loves|loved|likes|liked|saw|sees|'
       r'took|takes|gave|gives|made|makes|joined|joins|left|leaves|won|wins|lost|loses|owns|owned|runs|ran|teaches|taught|sat|stood|plays|played|'
       r'lent|sold|bought|found|opened|answered|replied|helped|stayed|arrived|attended|applied|signed|moved)')
add('which_for_people_det', r'(?i)\b(?:the|a|an|my|our|your|his|her|their|this|that|those|these|some|every|each|no|one|another) (?:[a-z]+ )?' + PERS + r' (?P<target>which) ' + WHV + r'\b',
    'who', 'Grammar', 0.9, 'Use “who” for people, not “which”.', 'The woman which called you is waiting outside.',
    'The woman who called you is waiting outside. The woman, which means “mother” in that language, is a loanword. Which woman called you?',
    fixes='The woman who called you is waiting outside.')
add('which_for_people_pron', r'(?i)\b(?:someone|somebody|anyone|anybody|everyone|everybody|nobody|people) (?P<target>which) ' + WHV + r'\b',
    'who', 'Grammar', 0.9, 'Use “who” for people, not “which”.', 'Anybody which wants a ticket should apply today.',
    'Anybody who wants a ticket should apply today. Choose anyone, which is fine.',
    fixes='Anybody who wants a ticket should apply today.')
