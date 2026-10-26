"""'real' for 'really', an adjective in front of a verb, 'very' in front of a verb, and the lookalike pairs
hard/hardly, late/lately, near/nearly, high/highly, short/shortly."""
from core import add, cover, tail, IDS, pick

SUBJ = r"(?:I|we|you|they|he|she|it)"

REAL_BE = r"(?:is|are|was|were|am|['’]s|['’]re|['’]m|feel|feels|felt|look|looks|looked|sound|sounds|sounded|seem|seems|seemed|taste|tastes|tasted|get|gets|got|getting|become|becomes|became)"
REAL_TAIL = r"(?:[.!?,;:)\n\"”]|\s*$|\s+(?:at|for|to|with|about|enough|and|but|today|now|here|there|in|on|lately|too)\b)"
# Feelings people state about themselves ("I was real angry", "I am real sorry") are left out: that is how chat is typed.
REAL_ADJ = '''good bad nice great easy hard cool hot cold late early different important helpful interesting
funny simple clear busy close tough smart beautiful pretty cute sweet kind strong big small fast slow long short young
old expensive cheap difficult useful fun lucky rich smooth quiet loud crazy strange
weird exciting boring awesome amazing comfortable friendly popular special wonderful safe soft bright dark
light well slowly carefully clearly badly nicely'''.split()

# adjective -> (adverb, verbs that may follow "I <adjective>")
PRE_VERB = {
    'real': ('really', 'like|likes|love|loves|hate|hates|appreciate|appreciates|enjoy|enjoys|want|wants|need|needs|miss|misses|hope|hopes|mean|means|believe|believes|wish|wishes|care|cares|understand|understands|liked|loved|hated|appreciated|enjoyed|wanted|needed|missed|hoped|meant|believed|wished|cared|understood',
             'I real appreciate your help.', 'I really appreciate your help. We found the real reason. It is a real problem.'),
    'total': ('totally', 'agree|agrees|agreed|disagree|disagrees|disagreed|understand|understands|understood|forgot|forget|forgets|ignored|ignore|trust|trusts|trusted|love|loves|loved|misunderstood',
              'I total agree with your plan.', 'I totally agree with your plan. We total the bill at noon. The total cost is high.'),
    'complete': ('completely', 'agree|agrees|agreed|disagree|disagrees|disagreed|understand|understands|understood|forgot|forget|forgets|ignored|ignore|trust|trusts|trusted|love|loves|loved|misunderstood|lost|failed',
                 'We complete agree with the decision.', 'We completely agree with the decision. We complete the forms by Friday. It is a complete list.'),
    'absolute': ('absolutely', 'agree|agrees|agreed|disagree|disagrees|disagreed|love|loves|loved|hate|hates|hated|adore|adores|adored|believe|believes|believed|trust|trusted|understand|understands|understood|refuse|refuses|refused|need|needs|needed|insist|insists|insisted',
                 'They absolute refused to move.', 'They absolutely refused to move. It is an absolute disgrace. She has absolute power.'),
    'full': ('fully', 'agree|agrees|agreed|understand|understands|understood|trust|trusts|trusted|expect|expects|expected|intend|intends|intended|realize|realizes|realized|realise|realises|realised|accept|accepts|accepted|recover|recovers|recovered',
             'I full understand your concern.', 'I fully understand your concern. We found a full house. The tank is full.'),
    'strong': ('strongly', 'recommend|recommends|recommended|suggest|suggests|suggested|believe|believes|believed|disagree|disagrees|disagreed|agree|agrees|agreed|advise|advises|advised|urge|urges|urged|oppose|opposes|opposed|encourage|encourages|encouraged|object|objects|objected|feel|feels|felt|doubt|doubts|doubted|support|supports|supported',
              'I strong recommend this course.', 'I strongly recommend this course. He is a strong swimmer. They feel strong.'),
    'high': ('highly', 'recommend|recommends|recommended|value|values|valued|appreciate|appreciates|appreciated|regard|regards|regarded|respect|respects|respected|praise|praises|praised|doubt|doubts|doubted|suggest|suggests|suggested',
             'We high recommend the early train.', 'We highly recommend the early train. The price is high. They fly high.'),
    'great': ('greatly', 'appreciate|appreciates|appreciated|admire|admires|admired|respect|respects|respected|value|values|valued|regret|regrets|regretted|enjoy|enjoys|enjoyed|benefit|benefits|benefited|differ|differs|differed|improve|improves|improved',
              'I great appreciate your time.', 'I greatly appreciate your time. It was a great day. They are great friends.'),
    'deep': ('deeply', 'regret|regrets|regretted|appreciate|appreciates|appreciated|apologize|apologise|apologized|apologised|care|cares|cared|love|loves|loved|respect|respects|respected|admire|admires|admired',
             'We deep regret the delay.', 'We deeply regret the delay. The lake is deep. They dig deep.'),
    'sincere': ('sincerely', 'apologize|apologise|apologized|apologised|hope|hopes|hoped|thank|thanks|thanked|appreciate|appreciates|appreciated|wish|wishes|wished|regret|regrets|regretted|believe|believes|believed',
                'I sincere apologize for the mistake.', 'I sincerely apologize for the mistake. She gave a sincere apology. He is sincere.'),
    'honest': ('honestly', 'think|thinks|thought|believe|believes|believed|feel|feels|felt|mean|means|meant|love|loved|like|liked|enjoy|enjoyed',
               'I honest think we should wait.', 'I honestly think we should wait. He gave an honest answer. She is honest.'),
    'personal': ('personally', 'think|thinks|thought|believe|believes|believed|feel|feels|felt|prefer|prefers|preferred|like|likes|liked|love|loves|loved|hate|hates|hated|recommend|recommends|recommended|know|knows|knew|enjoy|enjoys|enjoyed',
                 'I personal prefer the blue one.', 'I personally prefer the blue one. This is a personal matter. We keep personal data private.'),
    'usual': ('usually', 'go|goes|take|takes|get|gets|eat|eats|drink|drinks|wake|wakes|work|works|start|starts|finish|finishes|leave|leaves|arrive|arrives|walk|walks|ride|rides|read|reads|watch|watches|play|plays|have|has|do|does|come|comes|stay|stays|sleep|sleeps|use|uses|study|studies|travel|travels|visit|visits|meet|meets|call|calls|cook|cooks|run|runs|spend|spends|sit|sits|check|checks|wear|wears|buy|buys|order|orders|pay|pays|write|writes|see|sees|say|says|drive|drives',
              'We usual eat dinner at seven.', 'We usually eat dinner at seven. It was the usual crowd. She came at the usual time.'),
    'normal': ('normally', 'go|goes|take|takes|get|gets|eat|eats|drink|drinks|wake|wakes|work|works|start|starts|finish|finishes|leave|leaves|arrive|arrives|walk|walks|ride|rides|read|reads|watch|watches|play|plays|have|has|do|does|come|comes|stay|stays|sleep|sleeps|use|uses|study|studies|travel|travels|visit|visits|meet|meets|call|calls|cook|cooks|run|runs|spend|spends|sit|sits|check|checks|wear|wears|buy|buys|order|orders|pay|pays|write|writes|see|sees|say|says|drive|drives',
               'I normal wake up at six.', 'I normally wake up at six. Her temperature is normal. This is a normal day.'),
    'rare': ('rarely', 'go|goes|take|takes|get|gets|eat|eats|drink|drinks|see|sees|visit|visits|watch|watches|use|uses|meet|meets|call|calls|talk|talks|read|reads|write|writes|play|plays|travel|travels|come|comes|leave|leaves|miss|misses|forget|forgets|say|says|cook|cooks|drive|drives|check|checks|answer|answers|reply|replies|smile|smiles',
             'They rare visit the old town.', 'They rarely visit the old town. It is a rare coin. A rare bird sat there.'),
    'occasional': ('occasionally', 'go|goes|take|takes|get|gets|eat|eats|drink|drinks|see|sees|visit|visits|watch|watches|use|uses|meet|meets|call|calls|talk|talks|read|reads|write|writes|play|plays|travel|travels|come|comes|leave|leaves|cook|cooks|drive|drives|check|checks',
                   'We occasional meet for lunch.', 'We occasionally meet for lunch. He made an occasional visit. It was an occasional table.'),
    'final': ('finally', 'decided|went|found|got|made|did|came|realized|realised|understood|saw|took|started|finished|managed|arrived|agreed|gave|told|left|met|reached|learned|succeeded|passed|won|quit|stopped|bought|sold|moved|wrote|read|heard|knew|fixed|solved|figured|noticed|admitted|accepted|answered|called|replied|returned|joined|opened|closed|asked|began',
              'I final decided to call her.', 'I finally decided to call her. The final score was close. We reached the final round.'),
    'actual': ('actually', 'did|went|thought|found|saw|got|made|met|took|bought|read|heard|knew|know|think|believe|like|love|want|need|have|had|do|said|mean|means|enjoy|enjoyed|liked|loved|wanted|needed|tried|try|use|used|called|asked|prefer|preferred',
               'I actual thought it was a joke.', 'I actually thought it was a joke. The actual cost was low. What is the actual price?'),
    'sudden': ('suddenly', 'realized|realised|remembered|noticed|felt|saw|heard|understood|decided|stopped|started|went|came|got|found|knew|thought|lost|fell|began|turned',
               'I sudden remembered the key.', 'I suddenly remembered the key. A sudden noise woke us. It was a sudden change.'),
    'immediate': ('immediately', 'realized|realised|knew|noticed|understood|recognized|recognised|called|replied|responded|answered|stopped|left|started|went|came|ran|saw|agreed|said|told|asked|reported|accepted|refused|began|felt',
                  'We immediate knew it was wrong.', 'We immediately knew it was wrong. Our immediate family came. An immediate reply is needed.'),
    'definite': ('definitely', 'will|would|want|wants|wanted|need|needs|needed|plan|plans|planned|think|thought|recommend|recommended|prefer|prefers|preferred|agree|disagree|believe|know|knew|have|has|had|do|did|can|could|should|must',
                 'We definite will come back.', 'We definitely will come back. The definite article is “the”. It is not definite yet.'),
}

# very + verb ("I very like it"): "really" is the intensifier a verb takes
VERY_VERBS = [
    ('like', 'like|likes|liked', 'I very like this song.', 'I really like this song. I like it very much. That is very like her.'),
    ('love', 'love|loves|loved', 'We very love the new office.', 'We really love the new office. We love it very much. She is a very loving mother.'),
    ('hate', 'hate|hates|hated', 'They very hate the morning shift.', 'They really hate the morning shift. They hate it very much.'),
    ('enjoy', 'enjoy|enjoys|enjoyed', 'I very enjoyed the concert.', 'I really enjoyed the concert. I enjoyed it very much.'),
    ('appreciate', 'appreciate|appreciates|appreciated', 'We very appreciate your help.', 'We really appreciate your help. We appreciate your help very much.'),
    ('want', 'want|wants|wanted', 'I very want to meet her.', 'I really want to meet her. I want to meet her very much.'),
    ('need', 'need|needs|needed', 'You very need a rest.', 'You really need a rest. You need a rest very badly.'),
    ('miss', 'miss|misses|missed', 'We very miss our old street.', 'We really miss our old street. We miss it very much.'),
    ('admire', 'admire|admires|admired', 'I very admire her courage.', 'I really admire her courage. I admire her very much.'),
    ('prefer', 'prefer|prefers|preferred', 'I very prefer the second option.', 'I really prefer the second option. I prefer it very much.'),
    ('wish', 'wish|wishes|wished', 'We very wish you could stay.', 'We really wish you could stay. We wish you very well.'),
    ('hope', 'hope|hopes|hoped', 'I very hope it works.', 'I really hope it works. I very much hope it works.'),
    ('care', 'care|cares|cared', 'They very care about the result.', 'They really care about the result. They care very much.'),
    ('agree', 'agree|agrees|agreed', 'I very agree with the plan.', 'I really agree with the plan. I very much agree with the plan.'),
    ('thank', 'thank|thanks|thanked', 'I very thank you for the invitation.', 'I really thank you for the invitation. Thank you very much.'),
    ('adore', 'adore|adores|adored', 'We very adore this little town.', 'We really adore this little town. We adore it very much.'),
]


def build():
    # ---- "real" for "really"
    ids = []
    for a in REAL_ADJ:
        pos_t = pick(['The soup is real {a}.', 'Your new place looks real {a}.', 'That sounds real {a}.',
                      'The movie was real {a} for a cheap film.'], a)
        ids.append(add(
            f'real_{a}', rf"(?i)\b{REAL_BE} (?P<target>real) {a}{REAL_TAIL}", 'really', 'Register', 0.74,
            '“Real” as an intensifier is informal; in writing use “really”.',
            pos_t.format(a=a), f'The soup is really {a}. The real {a} news is here. A real {a} friend helps.'))
    cover('Real for really', '"is/looks/sounds/feels real good" and the other predicate uses with an adjective or adverb: real good, real bad, real nice, real easy, real hard ... (informal register note; "real quick", "real soon", "real time" and "a real good friend" are left alone)', ids)

    # ---- an adjective in front of a verb ("I real appreciate")
    ids = []
    for adj, (adv, verbs, pos, neg) in PRE_VERB.items():
        ids.append(add(
            f'pre_{adj}', rf"(?i)\b{SUBJ} (?P<target>{adj}) (?:{verbs})\b", adv, 'Grammar', 0.9,
            f'A verb is modified by an adverb: “{adv}”, not the adjective “{adj}”.', pos, neg))
    cover('Adjective for adverb', 'a subject pronoun + adjective + verb: I real appreciate, I total agree, we high recommend, I sincere apologize, I personal think, we usual eat, they rare visit, I final decided, I actual thought, I sudden remembered, we definite will ...', ids)

    # ---- "very" in front of a verb
    ids = []
    for key, forms, pos, neg in VERY_VERBS:
        subj = SUBJ if key != 'like' else r"(?:I|we|you|they|he|she)"
        ids.append(add(
            f'very_verb_{key}', rf"(?i)\b{subj} (?P<target>very) (?:{forms})\b", 'really', 'Grammar', 0.88,
            '“Very” modifies adjectives and adverbs, not verbs: say “really”, or put “very much” after the verb.', pos, neg))
    cover('Intensifiers', '"very" directly in front of a verb: I very like, we very appreciate, I very agree ...  -> really', ids)

    # ---- hard / hardly
    ids = []
    HARD_TAIL = r"(?:[.!?,;:)\n\"”]|\s*$|\s+(?:for|on|to|every|since|but|so|and|today|yesterday|this|last|tonight|enough|too|again|now|before|after|during|when|until)\b)"
    ids.append(add(
        'work_hardly',
        rf"(?i)\b(?:work|works|worked|working|study|studies|studied|studying|try|tries|tried|trying|train|trains|trained|training|practise|practice|practises|practices|practised|practiced|practising|practicing|push|pushes|pushed|pushing|fight|fights|fought|fighting|hit|hits|press|presses|pressed|pressing|pray|prays|prayed|praying|rain|rains|rained|raining|snow|snows|snowed|snowing|concentrate|concentrates|concentrated|concentrating|listen|listens|listened|listening) (?P<target>hardly){HARD_TAIL}",
        'hard', 'Grammar', 0.9, '“Hardly” means “almost not”. For effort or force, use “hard”.',
        'You have to study hardly to pass this exam.', 'You have to study hard to pass this exam. I hardly study at all. He can hardly wait.'))
    ids.append(add(
        'hard_ever',
        r"(?i)\b(?:I|we|you|they|he|she|it|people|nobody) (?P<target>hard) ever (?:see|sees|saw|go|goes|went|come|comes|came|get|gets|got|talk|talks|talked|call|calls|called|use|uses|used|eat|eats|ate|drink|drinks|drank|visit|visits|visited|watch|watches|watched|read|reads|write|writes|wrote|answer|answers|answered|reply|replies|replied|speak|speaks|spoke|happen|happens|happened|have|has|had|do|does|did)\b",
        'hardly', 'Grammar', 0.93, '“Hard” is not an adverb of degree: “hardly ever” means “almost never”.',
        'We hard ever see them these days.', 'We hardly ever see them these days. They worked hard ever since. It was hard, ever so hard.'))
    for pat_id, verbs, pos, neg in [
        ('wait', 'wait', 'I can hard wait for the weekend.', 'I can hardly wait for the weekend. It was hard, but I can wait.'),
        ('believe', 'believe', 'We could hard believe the news.', 'We could hardly believe the news. They work hard, and I believe it.'),
        ('see', 'see|hear|breathe', 'I can hard see you in this fog.', 'I can hardly see you in this fog. I can see hard cases here.'),
        ('imagine', 'imagine|remember|recognize|recognise', 'You can hard imagine the noise.', 'You can hardly imagine the noise. You can imagine hard times.'),
    ]:
        ids.append(add(
            f'can_hard_{pat_id}', rf"(?i)\b(?:can|could|can[’']t|couldn[’']t|cannot) (?P<target>hard) (?:{verbs})\b", 'hardly', 'Grammar', 0.93,
            '“Hard” means with effort. For “almost not”, use “hardly”.', pos, neg))
    cover('Hard and hardly', 'study hardly -> hard; hard ever see -> hardly ever; can hard wait/believe/see/imagine -> hardly', ids)

    # ---- late / lately, near / nearly, high / highly, short / shortly
    ids = []
    ids.append(add(
        'came_lately',
        rf"(?i)\b(?:I|we|you|they|he|she|it|who) (?:came|arrived|reached|woke up|got up|stayed up|went to bed) (?P<target>lately)(?:[.!?,;:)\n\"”]|\s*$|\s+(?:and|to|for|at|because|due|today|yesterday|again)\b)",
        'late', 'Word choice', 0.88, '“Lately” means “recently”. For “after the expected time”, use “late”.',
        'I woke up lately and missed the bus.', 'I woke up late and missed the bus. I have not slept well lately.'))
    ids.append(add(
        'am_lately',
        r"(?i)\b(?:I[’']m|I am|you[’']re|you are|we[’']re|we are|they[’']re|they are|he[’']s|he is|she[’']s|she is|it[’']s|it is|was|were|be|am) (?:(?:very|too|always|often|a bit|quite|so) )?(?P<target>lately)(?:[.!?,;:)\n\"”]|\s*$|\s+(?:for|again|today|because)\b)",
        'late', 'Word choice', 0.9, '“Lately” means “recently”. For “after the expected time”, use “late”.',
        'I am sorry, I was lately for the meeting.', 'I am sorry, I was late for the meeting. I have been busy lately. Lately, it rains a lot.'))
    NEAR_NOUNS = 'station|school|office|park|river|beach|sea|airport|hotel|hospital|market|mall|center|centre|city|university|house|home|bank|church|metro|bus stop|bus stand|library|college|museum|shop|supermarket|lake|forest|highway|temple|mosque|border|coast|campus'
    ids.append(add(
        'live_nearly',
        rf"(?i)\b(?:live|lives|lived|living|stay|stays|stayed|staying|located|situated|sits|sit|stand|stands|parked|work|works|worked|working|wait|waits|waited|waiting) (?P<target>nearly) (?:the |a |an |my |our |your |his |her |their |this |that )?(?:{NEAR_NOUNS})\b",
        'near', 'Word choice', 0.88, '“Nearly” means “almost”. For closeness in place, use “near”.',
        'We live nearly the station, so the walk is short.', 'We live near the station, so the walk is short. It took nearly the whole day. We nearly missed the bus.'))
    for verb, forms, pos, neg in [
        ('jump', 'jump|jumps|jumped|jumping', 'The horse jumped highly over the fence.', 'The horse jumped high over the fence. The play was highly praised.'),
        ('fly', 'fly|flies|flew|flying', 'The kite flew highly above the beach.', 'The kite flew high above the beach. The pilot is highly trained.'),
        ('climb', 'climb|climbs|climbed|climbing', 'The goats climbed highly up the cliff.', 'The goats climbed high up the cliff. The route is highly rated.'),
        ('throw', 'throw|throws|threw|throwing', 'He threw the ball highly into the air.', 'He threw the ball high into the air. The idea is highly unlikely.'),
        ('rise', 'rise|rises|rose|rising', 'The smoke rose highly into the sky.', 'The smoke rose high into the sky. Prices rose sharply.'),
        ('soar', 'soar|soars|soared|soaring', 'The eagle soared highly over the valley.', 'The eagle soared high over the valley. It is highly regarded.'),
    ]:
        ids.append(add(
            f'{verb}_highly', rf"(?i)\b(?:{forms})(?: [A-Za-z']+){{0,3}} (?P<target>highly)(?:[.!?,;:)\n\"”]|\s*$|\s+(?:in|above|over|into|up|on|towards|toward|against|beyond)\b)",
            'high', 'Word choice', 0.9, '“Highly” means “very”. For height, use “high”.', pos, neg))
    for adj in ['recommended', 'regarded', 'respected', 'likely', 'unlikely', 'important', 'useful', 'successful',
                'intelligent', 'desirable', 'probable', 'improbable', 'anticipated', 'appreciated', 'praised', 'acclaimed',
                'esteemed', 'doubtful', 'flammable']:
        ids.append(add(
            f'high_{adj}', rf"(?i)\b(?P<target>high) {adj}\b", 'highly', 'Grammar', 0.9,
            f'“High” describes height or level. To intensify “{adj}”, use the adverb “highly”.',
            pick(['The new plan is high {w} in the city.', 'It is a high {w} idea.', 'The book is high {w} by critics.',
                  'We find that result high {w}.'], adj).format(w=adj),
            f'The new plan is highly {adj} in the city. The high tower is old.'))
    ids.append(add(
        'put_it_shortly', r"(?i)\b(?P<target>to put it shortly|put it shortly)\b", 'to put it briefly', 'Word choice', 0.85,
        '“Shortly” means “soon”. To be brief, say “briefly” or “in short”.',
        'To put it shortly, the plan failed.', 'To put it briefly, the plan failed. The doctor will see you shortly.'))
    ids.append(add(
        'shortly_speaking', r"(?i)\b(?P<target>shortly speaking)\b", 'briefly speaking', 'Word choice', 0.85,
        '“Shortly” means “soon”. To be brief, say “briefly speaking” or “in short”.',
        'Shortly speaking, we need more time.', 'Briefly speaking, we need more time. We will speak shortly.'))
    ids.append(add(
        'cut_hair_shortly', r"(?i)\b(?:cut|cuts|cutting|trim|trims|trimmed|trimming) (?:my|his|her|their|your|our|the) hair (?P<target>shortly)\b", 'short', 'Word choice', 0.9,
        '“Shortly” means “soon”. For hair of a short length, use “short”.',
        'He wants to cut his hair shortly this year.', 'He wants to cut his hair short this year. The barber will cut it shortly.'))
    ids.append(add(
        'keep_it_shortly', r"(?i)\b(?:keep|keeps|kept) (?:it|this|that|the message|the email|the report|your answer|answers) (?P<target>shortly)\b", 'short', 'Word choice', 0.88,
        '“Shortly” means “soon”. To keep something brief, use “short”.',
        'Please keep the message shortly and clear.', 'Please keep the message short and clear. We will send it shortly.'))
    cover('Lookalike adverbs', 'late/lately (came lately, was lately), near/nearly (live nearly the station), high/highly (jumped highly; high recommended, high regarded ...), short/shortly (to put it shortly, shortly speaking, cut hair shortly, keep it shortly); "freely/free" and "close/closely" are left (both forms are standard adverbs with different meanings)', ids)
