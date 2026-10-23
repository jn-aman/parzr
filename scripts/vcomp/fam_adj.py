"""Family H: adjective, noun or question word + "to" + -ing ("nice to meeting you" -> "nice to meet you"), and
family I: adjective + bare verb where "to" is missing ("I am happy see you" -> "I am happy to see you")."""
import core
from core import add, g2b, alt, BE, ADV, NEXT_K, P1
from verbs import ACT, KV2

# ---------------------------------------------------------------- H: "to" + -ing after an adjective or noun
H_GROUPS = [
    ('feeling', 'nice|glad|pleased|happy|great|lovely|good|sorry|sad|delighted|thrilled|excited|proud|eager',
     'Nice', 'It was nice to meeting you.', 'It was nice to meet you.'),
    ('readiness', 'ready|prepared|willing|reluctant|afraid|ashamed|likely|unlikely|determined|keen',
     'Ready', 'We are ready to starting the work.', 'We are ready to start the work.'),
    ('difficulty', 'difficult|hard|easy|impossible|possible|safe|dangerous|wise|interesting|fun',
     'Hard', 'It is hard to finding a good plumber.', 'It is hard to find a good plumber.'),
    ('noun', 'chance|opportunity|attempt|ability|desire|tendency|failure|decision|wish|intention|capacity',
     'Chance', 'It was their decision to going home.', 'It was their decision to go home.'),
]
H_NEG = ('It was nice to meet you. We look forward to meeting you. The first step to becoming a nurse is training. '
         'He is committed to making it work. Welcome to being a parent.')

for rid, words, _, pos_a, exp_a in H_GROUPS:
    forms = words.split('|')
    for n, (alt_v, rep) in enumerate(g2b(ACT)):
        if n == 0:
            pos, exp = pos_a, exp_a
        else:
            first = forms[0]
            pos = {'feeling': 'It was nice to making your acquaintance.',
                   'readiness': 'We are ready to taking the exam.',
                   'difficulty': 'It is hard to making a good cake.',
                   'noun': 'It was their decision to taking a break.'}[rid]
            exp = pos.replace('to making', 'to make').replace('to taking', 'to take')
        add(f'adjto.{rid}.{"ae"[n]}', r'\b(?:' + words + r')\s+to\s+(?P<target>(?-i:' + alt_v + r'))\b', rep,
            f'After “{forms[0]} to”, use the base verb: “{forms[0]} to meet”, not “{forms[0]} to meeting”.',
            pos, exp, H_NEG, forms, conf=0.9,
            cover=f'{rid} adjective/noun + to + -ing -> to + base verb ({"plain/doubled" if n == 0 else "silent e"})')

# wh-words and "in order" / "so as" + to + -ing
WH = [
    ('wh', r'\b(?:how|what|where|when|whether|who|which)\s+to\s+', ['how', 'what', 'where', 'when', 'whether', 'who', 'which'],
     ('She explained how to making a cake.', 'She explained how to make a cake.'),
     ('She explained how to going home.', 'She explained how to go home.'),
     'She explained how to make a cake. We look forward to meeting you. I know what to do. Welcome to training day.'),
    ('order', r'\bin\s+order\s+to\s+', ['order'],
     ('In order to taking the exam, register first.', 'In order to take the exam, register first.'),
     ('In order to getting a refund, call us.', 'In order to get a refund, call us.'),
     'In order to get a refund, call us. In order to be safe, wear a helmet.'),
    ('soas', r'\bso\s+as\s+to\s+', ['so as'],
     ('Leave early so as to taking the first seat.', 'Leave early so as to take the first seat.'),
     ('Leave early so as to missing the bus.', 'Leave early so as to miss the bus.'),
     'Leave early so as to avoid the traffic. Leave early so as to get a seat.'),
]
for rid, lead, forms, e_case, a_case, neg in WH:
    for n, (alt_v, rep) in enumerate(g2b(ACT)):
        pos, exp = a_case if n == 0 else e_case
        add(f'adjto.{rid}.{"ae"[n]}', lead + r'(?P<target>(?-i:' + alt_v + r'))\b', rep,
            '“To” is followed by the base verb, not an -ing form: “how to make”, “in order to get”.',
            pos, exp, neg, forms, conf=0.92, cover=f'{rid} + to + -ing -> to + base verb')

# ---------------------------------------------------------------- I: adjective + bare verb, "to" missing
ADJ = [
    ('able', 'able|unable', 'She is able go there alone.', 'She is able to go there alone.',
     'She is able to go there alone. He was unable to go. She is able and willing.'),
    ('willing', 'willing|unwilling', 'They are willing give us a discount.', 'They are willing to give us a discount.',
     'They are willing to give us a discount. They are willing and ready.'),
    ('likely', 'likely|unlikely', 'He is likely win the race.', 'He is likely to win the race.',
     'He is likely to win the race. She will likely win the race. He is likely the best choice.'),
    ('supposed', 'supposed', 'You are supposed know the rules.', 'You are supposed to know the rules.',
     'You are supposed to know the rules. The supposed leader left.'),
    ('glad', 'glad|happy|pleased|delighted', 'I am glad see you here.', 'I am glad to see you here.',
     'I am glad to see you here. I am glad you came. We are a happy family.'),
    ('sorry', 'sorry', 'I am sorry hear that news.', 'I am sorry to hear that news.',
     'I am sorry to hear that news. I am sorry about the delay. Sorry for the noise.'),
    ('eager', 'eager|reluctant|afraid|ashamed|proud', 'He is eager join the team.', 'He is eager to join the team.',
     'He is eager to join the team. He is afraid of heights. She is proud of him.'),
    ('prepared', 'prepared|determined', 'We are determined win the game.', 'We are determined to win the game.',
     'We are determined to win the game. The prepared speech was short.'),
]
for rid, words, pos, exp, neg in ADJ:
    forms = words.split('|')
    adj_verbs = KV2 if rid != 'glad' else [v for v in KV2 if v != 'go']
    add(f'adjmissing.{rid}', BE + r'(?P<target>(?P<a>' + words + r'))\s+(?-i:' + alt(adj_verbs) + r')' + NEXT_K, '${a} to',
        f'“{forms[0].capitalize()}” needs “to” before a verb: “{forms[0]} to go”.', pos, exp, neg, forms, conf=0.9,
        cover=f'{rid} + bare verb -> {rid} to + verb')

add('adjmissing.going', BE + r'(?P<target>going)\s+(?-i:' + alt(KV2) + r')' + NEXT_K, 'going to',
    '“Going” needs “to” before a verb: “going to see”.', 'I am going see my mother today.', 'I am going to see my mother today.',
    'I am going to see my mother today. I am going home. Keep going and get the report done.', ['going'],
    conf=0.9, cover='be going + bare verb -> be going to + verb')
