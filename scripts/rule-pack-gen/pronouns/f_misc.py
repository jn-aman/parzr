"""let/make + "X and I", anyone of, them as a determiner, "for we students", someone elses."""
from lib import *

B = r'(?:\s|[.,;:!?]|$)'
BARE = (r'(?:go|handle|do|see|know|have|take|try|think|discuss|talk|finish|decide|figure|work|check|look|sort|deal|speak|explain|show|be|pay|make|get|come|'
        r'stay|leave|join|run|start|plan|review|fix|read|write|call|send|give|bring|ask|tell|meet|continue|begin|sit|sort|choose|pick|prepare|cook|clean|'
        r'help|pass|win|lose|feel|smile|laugh|cry|wonder|worry|shout|dance|jump|stop|wait|rest|sleep|eat|drive|walk|play|relax|try|keep|put|set|move|open|close|build|find|use|say|hear|sing)')
for verb, forms, pos, neg in [
    ('let', 'let|lets|letting', 'Please let my wife and I handle the booking.', 'Please let my wife and me handle the booking. Let’s go, my wife and I.'),
    ('make', 'make|makes|made|making', 'That song made Tom and I smile all day.', 'That song made Tom and me smile all day. My wife and I smile.'),
]:
    for pn, np in [('name', NP1N)]:
        pat = r'(?i)\b(?:' + forms + r') ' + np + r' and (?P<target>(?-i:I)) ' + BARE + r'\b'
        p = pos if pn == 'name' else pos.replace('my wife', 'him').replace('Tom', 'her')
        n = neg if pn == 'name' else neg.replace('my wife', 'him').replace('Tom', 'her')
        add('obj_' + verb + '_x_and_i_' + pn, pat, 'me', 'Grammar', 0.94, 'After “' + verb + '” use “me”, not “I”.', p, n, fixes=p.replace(' and I ', ' and me ', 1))

add('anyone_of', r'(?i)\b(?P<target>anyone) of (?:them|us|you|these|those)\b', 'any one', 'Word choice', 0.84,
    'Write “any one of” when you mean a single one of several.', 'Anyone of these three candidates could win.',
    'Any one of the three candidates could win. Anyone can win. I never told anyone of the events.',
    fixes='Any one of these three candidates could win.')
add('everyone_of', r'(?i)\b(?P<target>everyone) of (?:them|us|you|these|those)\b', 'every one', 'Word choice', 0.84,
    'Write “every one of” when you mean each single one of several.', 'Everyone of them brought a gift.',
    'Every one of them brought a gift. Everyone in the room brought a gift. She told everyone of the changes.', fixes='Every one of them brought a gift.')

THEM_NOUNS = 'boys|girls|kids|guys|shoes|cookies|books|cars|dogs|cats|flowers|trees|pants|jeans|clothes|files|things|birds|houses|bags|chairs|tables|toys|games|songs|movies|photos|pictures|boots|socks|hats'
THEM_VERBS = 'like|love|hate|see|saw|want|need|eat|ate|watch|watched|check|checked|fix|fixed|use|used|clean|cleaned|try|tried|wear|wore|keep|kept'
add('them_det_verb', r'(?i)\b(?:' + THEM_VERBS + r') (?P<target>them) (?:' + THEM_NOUNS + r')' + B, 'those', 'Grammar', 0.88,
    'Before a noun, use “those”, not “them”.', 'I really need them boots for the trip.',
    'I really need those boots for the trip. How do you like them apples? I saw them boys yesterday, I mean the boys.'.replace(' I saw them boys yesterday, I mean the boys.', ''),
    fixes='I really need those boots for the trip.')
WE_N = 'guys|girls|students|teachers|women|men|kids|folks|people|all|two|three|both|nurses|doctors|drivers|workers|parents|musicians|artists|writers|boys|ladies|programmers|engineers|managers|fans|players'
for prep, pos in [
    ('for', 'This is really hard for we students.'), ('to', 'It matters to we teachers.'), ('with', 'Please be patient with we beginners.'.replace('beginners', 'nurses')),
    ('from', 'Nothing was hidden from we parents.'), ('about', 'They never ask about we drivers.'), ('between', 'There is no secret between we two.'),
    ('among', 'It was quiet among we three.'), ('at', 'They laughed at we players.'), ('by', 'It was decided by we managers.'),
    ('of', 'They are afraid of we fans.'.replace('fans', 'engineers')), ('without', 'They left without we two.'), ('against', 'It is against we artists.'),
    ('on', 'You can count on we musicians.'), ('behind', 'The crowd stood behind we writers.'), ('near', 'Sit near we ladies.')
]:
    pat = r'(?i)\b' + prep + r' (?P<target>we) (?:' + WE_N + r')' + B
    add('prep_' + prep + '_we_noun', pat, 'us', 'Grammar', 0.94, 'After “' + prep + '” use “us”, not “we”.', pos,
        'We students are tired. It is hard for us students. ' + prep.capitalize() + ' we go.',
        fixes=pos.replace(' we ', ' us ', 1))
add('elses_possessive', r"(?i)\b(?P<target>(?P<w>someone|somebody|anyone|anybody|everyone|everybody|nobody|no one) elses)" + B, "${w} else’s", 'Possessive', 0.95,
    'The possessive is “else’s”.', 'That is someone elses problem.', 'That is someone else’s problem. Nobody else is here.',
    fixes='That is someone else’s problem.')
