"""More adjective/adverb slips: an adverb in front of a noun, "feel tiring", a feeling adjective in front of a
thing, worst/best/good/bad "than", "as more important as", widely open, and non-words (farer, lastest ...)."""
from core import add, cover, pick, IDS

DET2 = r"(?:a|an|the|my|our|your|his|her|their|another|each|every)"

ADV_NOUN = [
    ('quickly', 'quick', 'decision answer reply response fix start look visit break meal check call walk ride trip glance chat summary overview review update learner reader thinker worker solution test'),
    ('easily', 'easy', 'way solution fix answer task job method process option access win target choice recipe step question example'),
    ('slowly', 'slow', 'start motion process pace speed progress cooker growth death learner walk drive reader week day season'),
    ('carefully', 'careful', 'look reading check review plan consideration thought analysis selection choice driver reader listener reply'),
    ('happily', 'happy', 'ending family life marriage couple face birthday'),
    ('successfully', 'successful', 'business career result outcome launch completion student person company project attempt'),
    ('beautifully', 'beautiful', 'day place woman girl house view picture song garden story voice'),
    ('wonderfully', 'wonderful', 'day place time person gift surprise idea experience'),
    ('perfectly', 'perfect', 'day match example fit gift solution place time score circle opportunity'),
    ('quietly', 'quiet', 'place night room voice life street corner morning evening moment type'),
    ('clearly', 'clear', 'view picture answer example explanation message sign winner majority goal instruction'),
    ('completely', 'complete', 'set list guide collection version solution failure stranger waste disaster mess nonsense'),
    ('totally', 'total', 'failure waste disaster mess stranger idiot loss nonsense'),
    ('strongly', 'strong', 'reason case argument position support opinion belief feeling desire performance candidate leader team signal'),
    ('highly', 'high', 'level quality risk price cost rate score standard speed'),
    ('deeply', 'deep', 'breath sleep voice water thought impact'),
    ('rapidly', 'rapid', 'growth increase change rise decline progress pace development expansion response'),
    ('directly', 'direct', 'flight route contact access link answer line result impact'),
    ('fully', 'full', 'refund support access report day house moon story control'),
    ('freely', 'free', 'gift access sample trial shipping delivery'),
    ('hardly', 'hard', 'work worker time decision choice life question'),
    ('greatly', 'great', 'success importance deal effect impact'),
    ('simply', 'simple', 'answer question solution rule task test way method process'),
    ('badly', 'bad', 'day mistake habit idea news weather quality luck feeling result time'),
    ('politely', 'polite', 'request reply answer refusal question way'),
    ('honestly', 'honest', 'opinion answer mistake review attempt person'),
    ('immediately', 'immediate', 'effect action response family attention need reply'),
]

# feeling adjective used of a person after "feel": "I feel tiring" -> tired
FEEL_ING = [('tiring', 'tired'), ('exciting', 'excited'), ('confusing', 'confused'), ('embarrassing', 'embarrassed'),
            ('disappointing', 'disappointed'), ('depressing', 'depressed'), ('frightening', 'frightened'),
            ('shocking', 'shocked'), ('worrying', 'worried'), ('relaxing', 'relaxed'), ('satisfying', 'satisfied'),
            ('terrifying', 'terrified'), ('fascinating', 'fascinated'), ('exhausting', 'exhausted'),
            ('irritating', 'irritated'), ('overwhelming', 'overwhelmed'), ('thrilling', 'thrilled'),
            ('amusing', 'amused'), ('puzzling', 'puzzled'), ('disgusting', 'disgusted'), ('horrifying', 'horrified')]
# a thing that is "bored" or "excited": "a bored lecture" -> boring
ED_THING = [('bored', 'boring'), ('excited', 'exciting'), ('interested', 'interesting'), ('annoyed', 'annoying'),
            ('confused', 'confusing'), ('tired', 'tiring'), ('disappointed', 'disappointing'), ('surprised', 'surprising'),
            ('shocked', 'shocking'), ('frightened', 'frightening'), ('terrified', 'terrifying'), ('exhausted', 'exhausting'),
            ('fascinated', 'fascinating'), ('thrilled', 'thrilling'), ('worried', 'worrying'), ('depressed', 'depressing'),
            ('satisfied', 'satisfying'), ('amazed', 'amazing'), ('irritated', 'irritating'), ('overwhelmed', 'overwhelming'),
            ('relaxed', 'relaxing'), ('puzzled', 'puzzling'), ('disgusted', 'disgusting'), ('scared', 'scary')]
THINGS = 'movie|film|book|story|lesson|lecture|speech|show|game|trip|journey|news|result|experience|process|party|meeting|conversation|topic|subject|idea|class|exam|test|task|documentary|episode'
# "tired" and "satisfied" also describe people at work ("a tired nurse"), so these two are matched only before the
# listed things.


def build():
    # ---- an adverb where the noun needs an adjective
    ids = []
    for adv, adj, nouns in ADV_NOUN:
        first = nouns.split()[0]
        noun_alt = '|'.join(nouns.split())
        ids.append(add(
            f'advnoun_{adv}', rf"(?i)\b{DET2} (?P<target>{adv}) (?:{noun_alt})\b", adj, 'Grammar', 0.93,
            f'A noun is described by an adjective: “{adj} {first}”, not “{adv} {first}”.',
            f'She gave me the {adv} {first}.',
            f'She gave me the {adj} {first}. They {adv} left the room. The {adv} growing {first}s helped.'))
    cover('Adverb in front of a noun', 'determiner + adverb + noun: a quickly reply, the easily way, a happily ending, a totally failure, a deeply breath, a highly level, a directly flight ... -> the adjective (27 adverbs, each with its own noun list)', ids)

    # ---- feel + a thing-adjective
    ids = []
    for ing, ed in FEEL_ING:
        ids.append(add(
            f'feel_{ing}', rf"(?i)\b(?:I|we|you|they|he|she)(?: (?:feel|felt|feels)| (?:am|are|is|was|were) feeling|['’](?:m|re|s) feeling) (?:(?:very|so|really|quite|too|a bit|pretty|extremely|totally|completely) )?(?P<target>{ing})\b",
            ed, 'Grammar', 0.9,
            f'A person who feels something is “{ed}”; “{ing}” describes the thing that causes the feeling.',
            f'We felt {ing} all evening.', f'We felt {ed} all evening. The meeting was {ing}.'))
    cover('Feeling adjectives', 'feel/am feeling + -ing adjective (I feel tiring, we felt confusing, she is feeling depressing ...) -> -ed; the base grammar.participle_adjective covers "I am interesting in", "boring with" etc., usage.participle_ing covers "the movie was bored"', ids)

    # ---- a/the + -ed adjective + thing
    ids = []
    for ed, ing in ED_THING:
        ids.append(add(
            f'thing_{ed}', rf"(?i)\b(?:a|an|the|this|that|such a|so|very|really|another) (?P<target>{ed}) (?:{THINGS})\b", ing, 'Grammar', 0.9,
            f'A thing that causes the feeling is “{ing}”, not “{ed}”.',
            f'It was the {ed} lecture of the week.', f'It was the {ing} lecture of the week. The {ed} crowd left.'))
    cover('Feeling adjectives', 'determiner + -ed adjective + a thing (a bored movie, an excited trip, the tired journey, a scared story -> scary ...); people nouns (a tired nurse, an excited crowd) are left', ids)

    # ---- worst/best/good/bad than
    ids = []
    COP = r"(?:is|are|was|were|looks?|looked|seems?|seemed|feels?|felt|sounds?|sounded|gets?|got|getting|becomes?|became|becoming|tastes?|tasted)"
    MOD = r"(?:(?:much|far|even|a lot|a bit|slightly|way|still|just) )?"
    for wrong, right, ex in [('worst', 'worse', 'The traffic today is worst than yesterday.'),
                             ('best', 'better', 'This phone is best than the old one.'),
                             ('good', 'better', 'The second plan is good than the first.'),
                             ('bad', 'worse', 'The weather is bad than I expected.'),
                             ('goodest', 'better', 'It is goodest than the others.')]:
        if wrong == 'goodest':
            continue
        ids.append(add(
            f'{wrong}_than', rf"(?i)\b{COP} {MOD}(?P<target>{wrong}) than\b", right, 'Grammar', 0.92,
            f'Comparing two things takes “{right} than”, not “{wrong} than”.', ex,
            f'The traffic today is {right} than yesterday. It was the best of days.'))
    ids.append(add('the_worse_thing', r"(?i)\b(?:is|was|'s|that['’]s|this is) the (?P<target>worse) (?:thing|part|case|mistake|nightmare|feeling|decision|idea|moment|day|time)\b",
                   'worst', 'Grammar', 0.8, '“Worst” is the superlative: “the worst thing”.',
                   'That was the worse thing about the trip.', 'That was the worst thing about the trip. Rain is worse than snow.'))
    cover('Comparatives and superlatives', 'worst than / best than / good than / bad than after a be or linking verb -> worse/better/worse; the worse thing -> the worst thing (the base grammar.worst_case covers "worse case"; "the more worse" is grammar.more_comparative)', ids)

    # ---- "as more important as"
    ids = []
    for adj in ['important', 'expensive', 'difficult', 'beautiful', 'useful', 'interesting', 'powerful', 'popular', 'dangerous', 'comfortable']:
        ids.append(add(
            f'as_more_{adj}', rf"(?i)\bas (?P<target>more ){adj} as\b",
            '', 'Grammar', 0.93, f'In “as … as”, use the plain adjective: “as {adj} as”.',
            f'Your job is as more {adj} as mine.', f'Your job is as {adj} as mine. It is more {adj} than mine.'))
    for mult in ['twice', 'half', 'three times', 'two times', 'double', 'triple', 'thrice', 'four times']:
        ids.append(add(
            f'{mult.replace(" ", "_")}_as_more', rf"(?i)\b{mult} as (?P<target>more )(?:expensive|important|difficult|likely|efficient|powerful|beautiful|useful|popular|dangerous|comfortable|interesting)\b",
            '', 'Grammar', 0.93, f'After “{mult} as”, use the plain adjective: “{mult} as expensive”.',
            f'The new model is {mult} as more expensive.', f'The new model is {mult} as expensive. It is more expensive.'))
    cover('As ... as', 'as more important as, twice as more expensive ... -> drop "more"', ids)

    # ---- wide / widely, near-words
    ids = []
    for noun in ['eyes', 'door', 'mouth', 'window', 'arms', 'gate']:
        ids.append(add(
            f'widely_open_{noun}', rf"(?i)\b{noun} (?P<target>widely) (?:open|apart)\b", 'wide', 'Word choice', 0.9,
            f'For something opened fully, use “wide”: “{noun} wide open”.',
            f'She left the {noun} widely open.' if noun in ('door', 'mouth', 'window', 'gate') else f'She lay awake with her {noun} widely open.',
            f'She left the {noun} wide open. The idea is widely accepted.' if noun in ('door', 'mouth', 'window', 'gate') else f'He stared with his {noun} wide open. The idea is widely accepted.'))
    cover('Lookalike adverbs', 'eyes/door/mouth/window/arms/gate widely open -> wide open', ids)

    # ---- non-words
    ids = []
    for wrong, right, pos in [('farer', 'farther', 'The shop is farer from here than the bank.'), ('farest', 'farthest', 'It is the farest point on the map.'),
                              ('badest', 'worst', 'That was the badest storm in years.'),
                              ('mucher', 'more', 'We need mucher time for this.'),
                              ('morer', 'more', 'We need morer time for this.')]:
        ids.append(add(
            f'nonword_{wrong}', rf"(?i)\b(?P<target>{wrong})\b", right, 'Grammar', 0.93,
            f'“{wrong.capitalize()}” is not a word: use “{right}”.', pos, pos.replace(wrong, right)))
    cover('Wrong comparative forms', 'non-words: farer/farest, badest (lastest is a spelling correction in the engine already), mucher, morer', ids)
