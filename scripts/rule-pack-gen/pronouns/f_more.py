"""More pronoun constructions: "a friend of my", "yours friend", "he's own", "theirs a problem", "neither do them",
"seen she", "love he." and the other subject-case pronouns left at the end of a clause."""
from lib import *

B = r'(?:\s|[.,;:!?]|$)'
END_STOP = r'(?:[.!?](?:["”’)]*)(?:\s|$))'

# ---- "a friend of my" -> "a friend of mine" --------------------------------------------------------------------------
FRIENDS = ('friend|friends|cousin|colleague|neighbor|neighbour|buddy|teacher|brother|sister|relative|coworker|classmate|uncle|aunt|boss|student|'
           'enemy|rival|client|customer|partner|acquaintance')
for poss, indep, ex in [('my', 'mine', 'She is a friend of my.'), ('your', 'yours', 'He is a cousin of your.'),
                        ('our', 'ours', 'They are neighbours of our.'), ('her', 'hers', 'He is a colleague of her.'),
                        ('their', 'theirs', 'She is a friend of their.'), ('his', 'his', None)]:
    if ex is None:
        continue
    add('of_' + poss + '_end', r'(?i)\b(?:' + FRIENDS + r')s? of (?P<target>' + poss + r')' + END_STOP, indep, 'Grammar', 0.93,
        'After “of” at the end of a phrase use “' + indep + '”: “a friend of ' + indep + '”.', ex,
        ex.replace(' ' + poss + '.', ' ' + indep + '.') + ' ' + ex.replace(' ' + poss + '.', ' ' + poss + ' sister.'),
        fixes=ex.replace(' ' + poss + '.', ' ' + indep + '.'))

# ---- yours / hers / ours / theirs used as a determiner ----------------------------------------------------------------
YN = ('friend|friends|family|house|car|phone|email|name|address|number|idea|team|company|job|mother|father|brother|sister|wife|husband|son|daughter|kids|'
      'children|parents|boss|dog|cat|home|office|account|password|opinion|decision|help|time|life|work|book')
for w, d, ex in [('yours', 'your', 'I like yours house.'), ('hers', 'her', 'I met hers brother.'), ('ours', 'our', 'We sold ours car.'),
                 ('theirs', 'their', 'I like theirs house.')]:
    add('det_' + w, r'(?i)\b(?P<target>' + w + r') (?:' + YN + r')\b', d, 'Grammar', 0.9,
        '“' + w.capitalize() + '” stands alone; before a noun use “' + d + '”.', ex,
        'The car is ' + w + '. ' + {'yours': 'Yours truly, Sam.', 'hers': 'The red one is hers, not mine.', 'ours': 'The house is ours, we think.', 'theirs': 'The idea was theirs, they said.'}[w],
        fixes=ex.replace(w, d, 1))
add('mine_det_kin', r'(?i)(?:^|[.!?]\s+|\b(?:is|was|are|were|and|with|to|for|of|from|about|like|love|met|see|saw|called|asked|told)\s+)(?P<target>mine) (?:friend|mother|father|brother|sister|wife|husband|family|parents|son|daughter|boss|teacher|kids|children|cousin|uncle|aunt)\b',
    'my', 'Grammar', 0.9, '“Mine” stands alone; before a noun use “my”.', 'I talked with mine mother yesterday.',
    'I talked with my mother yesterday. The red one is mine.', fixes='I talked with my mother yesterday.')

# ---- he's own / she's own; theirs a problem; so/neither do them ----------------------------------------------------
for pr, rep, subj in [('he', 'his', 'He'), ('she', 'her', 'She')]:
    add(pr + 's_own', r"(?i)\b(?P<target>" + pr + r"['’]s) own\b", rep, 'Possessive', 0.96,
        '“' + pr.capitalize() + '’s” means “' + pr + ' is”; for ownership use “' + rep + '”.', subj + ' wants to be ' + pr + '’s own boss.',
        subj + ' wants to be ' + rep + ' own boss. ' + pr.capitalize() + '’s on ' + rep + ' own today.',
        fixes=subj + ' wants to be ' + rep + ' own boss.')
add('theirs_theres', r"(?im)(?:" + CS + r"|\b(?:think|hope|know|guess|says|said|if|because|that|when|so|but)\s+)(?P<target>Theirs) (?:a|an|no|nothing|something|someone|somebody|nobody|anything|lots|plenty|still|only|always|never|not|been|going|one|two|three|many|more|some|enough)\b",
    "There's", 'Word choice', 0.94, 'Here you need “there’s” (“there is”), not “theirs”.', 'Theirs a problem with the printer.',
    'There’s a problem with the printer. The idea was theirs. Theirs is the blue house.', fixes='There\'s a problem with the printer.')
for pn, ob, sb in [('me', 'me', 'I'), ('him', 'him', 'he'), ('her', 'her', 'she'), ('us', 'us', 'we'), ('them', 'them', 'they')]:
    add('neither_do_' + pn, r"(?im)(?:" + CS + r"|\b(?:and|but)\s+)(?:neither|nor) (?:do|did|does|am|is|are|was|were|have|has|can|could|will|would) (?P<target>" + ob + r")" + END_STOP,
        sb, 'Grammar', 0.93, 'After “neither do” the subject takes “' + sb + '”.', 'I never liked it, and neither do ' + ob + '.',
        'I never liked it, and neither do ' + sb + '. Neither do I. Neither of us did.', fixes='I never liked it, and neither do ' + sb + '.')
add('else_s_order', r"(?i)\b(?P<target>(?P<w>someone|somebody|anyone|anybody|everyone|everybody|nobody|no one)['’]s else)\b", "${w} else's", 'Possessive', 0.96,
    'The possessive goes on “else”: “someone else’s”.', 'That is someone’s else problem.', 'That is someone else’s problem.', fixes="That is someone else's problem.")
add('by_its_self', r"(?i)\bby (?P<target>its self)\b", 'itself', 'Spelling', 0.94, 'Write “itself” as one word.', 'The machine runs by its self.',
    'The machine runs by itself. The machine runs by its own self-test.', fixes='The machine runs by itself.')

# ---- a subject-case pronoun at the end of a clause after a verb that needs an object --------------------------------
END_VERBS = [
    ('love', 'love|loves|loved|hate|hates|hated|miss|misses|missed|like|likes|liked|trust|trusts|trusted'),
    ('see', 'see|sees|saw|seen|know|knows|knew|meet|meets|met|hear|hears|heard|find|finds|found|forget|forgot'),
    ('help', 'help|helps|helped|follow|follows|followed|thank|thanks|thanked|invite|invites|invited|join|joins|joined|hug|hugs|hugged|kiss|kisses|kissed'),
    ('bring', 'bring|brings|brought|take|takes|took|hit|hits|beat|beats|want|wants|wanted|need|needs|needed|blame|blames|blamed|leave|leaves|left'),
]
SAMPLE = {
    'love': 'We all love {s}.', 'see': 'Nobody saw {s}.', 'help': 'Maya helped {s}.', 'bring': 'Maya took {s}.',
}
NEGS = {
    'love': 'We all love him. Do you love her? Nobody loved us. Who do you love most? He.',
    'see': 'Nobody saw him. Who saw me? I know. He knew.',
    'help': 'Maya helped them. Who helped? She.',
    'bring': 'Maya took them. Who took it? He.',
}
for gid, verbs in END_VERBS:
    for sub, ob in [('he', 'him'), ('she', 'her'), ('we', 'us'), ('they', 'them')]:
        sbj = sub
        pat = r'(?i)\b(?:I|we|you|they|he|she|it|who|(?-i:[A-Z][a-z]+)|nobody|everybody|everyone|someone|anyone|please) (?:all |never |also |still |really |just |always |already )?(?:' + verbs + r') (?P<target>' + sbj + r')' + END_STOP
        pos = SAMPLE[gid].format(s=sub)
        add('end_' + gid + '_' + sub.lower(), pat, ob, 'Grammar', 0.9, 'After a verb use “' + ob + '”, not “' + sub + '”.', pos, NEGS[gid],
            fixes=pos.replace(' ' + sub + '.', ' ' + ob + '.'))
