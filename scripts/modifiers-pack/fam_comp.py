"""Comparatives and superlatives: doubled forms, the wrong form for the adjective, and "very" with a comparative."""
from core import add, cover, alt, END, IDS, tail, pick

DOUBLE_LAST = {'big', 'fat', 'hot', 'wet', 'sad', 'mad', 'glad', 'red', 'slim', 'fit', 'thin', 'flat'}


def comp(a):
    if a in DOUBLE_LAST:
        return a + a[-1] + 'er'
    if a.endswith('y'):
        return a[:-1] + 'ier'
    if a.endswith('e'):
        return a + 'r'
    return a + 'er'


def sup(a):
    if a in DOUBLE_LAST:
        return a + a[-1] + 'est'
    if a.endswith('y'):
        return a[:-1] + 'iest'
    if a.endswith('e'):
        return a + 'st'
    return a + 'est'


# Comparatives the base rules (grammar.more_comparative, usage.double_comparative) already delete "more" before.
BASE_MORE = set('''taller bigger smaller faster better worse easier harder older younger cheaper longer shorter higher
lower larger happier busier nicer stronger quicker slower richer closer safer simpler clearer newer greater earlier
weaker smarter'''.split())
BASE_MOST = set('''easiest hardest fastest slowest strongest weakest simplest largest smallest biggest cheapest safest
highest lowest shortest longest'''.split())

# Adjectives whose comparative is a plain -er form and is never a noun (so "more X-er" is always doubled).
# Left out on purpose: cleaner, thinner, lighter, warmer, cooler, fresher, dryer, upper, outer (nouns: "add more
# cleaner", "a few more coolers") and later ("I will tell you more later").
ADJ = '''bright cold deep wide thick fat hot wet dark soft loud quiet calm kind mild rough smooth tight sharp flat plain
proud sweet poor sad mad glad red slim fit fine pure rare rude wise brave cute tiny funny heavy lazy lucky pretty
ugly silly dirty noisy healthy wealthy angry hungry thirsty tasty friendly lively lonely messy risky sunny windy
rainy cloudy shiny sleepy gentle narrow shallow clever pale dull tough crisp fair neat strict mature
polite loose steep'''.split()
MORE_COMPS = {a: comp(a) for a in ADJ}

SUP_ADJ = '''old young tall new busy close clear great early late nice happy rich quick smart near fine bright cold deep
wide thick fat hot wet dark soft loud quiet calm kind mild rough smooth tight sharp flat plain proud sweet poor
sad mad glad red slim fit pure rare rude wise brave cute tiny funny heavy lazy lucky pretty ugly silly dirty noisy
healthy wealthy angry hungry thirsty tasty friendly lively lonely messy risky sunny windy rainy cloudy shiny
sleepy gentle narrow shallow clever pale dull tough crisp fair neat strict mature polite loose steep'''.split()


def build():
    # ---- more + an -er comparative ("more taller")
    ids = []
    for a, c in sorted(MORE_COMPS.items()):
        if c in BASE_MORE:
            continue
        ids.append(add(
            f'more_{c}', rf"(?i)\b(?P<target>more (?P<c>{c}))\b", '${c}', 'Grammar', 0.95,
            f'“{c.capitalize()}” already means “more {a}”: use “{c}” alone, not “more {c}”.',
            pick(['The new model is more {c} than the old one.', 'Everything got more {c} after the update.',
                  'The second room felt more {c} than the first.', 'Our new plan looks more {c} on paper.'], a).format(c=c),
            f'The new model is {c} than the old one, and the shop sells more of them.'))
    for c, pos in (('farther', 'The shop is more farther than the bank.'),
                   ('further', 'We went more further than we planned.'),
                   ('nearer', 'The station is more nearer than the bus stop.'),
                   ('fewer', 'There were more fewer people at the event.'),
                   ):
        ids.append(add(
            f'more_{c}', rf"(?i)\b(?P<target>more (?P<c>{c}))\b", '${c}', 'Grammar', 0.95,
            f'“{c.capitalize()}” is already a comparative: use “{c}” alone, not “more {c}”.', pos,
            f'The shop is {c} than the bank, and the walk takes more minutes.'))
    ids.append(add(
        'more_worser', r"(?i)\b(?P<target>more worser)\b", 'worse', 'Grammar', 0.95,
        '“Worse” is already the comparative of “bad”, and “worser” is not standard: use “worse”.',
        'The traffic got more worser after the rain.', 'The traffic got worse after the rain, and more cars came.'))
    ids.append(add(
        'worser', r"(?i)(?:^|[^-\w])(?P<target>worser)\b", 'worse', 'Grammar', 0.95,
        '“Worser” is not standard: the comparative of “bad” is “worse”.',
        'The weather is worser than I expected.', 'The weather is worse than I expected.'))
    cover('Doubled comparatives', 'more + an -er comparative that the base rules do not list (more brighter, more deeper, more friendlier, more farther, more nearer, more worser ...)', ids)

    # ---- most + an -est superlative ("most tallest")
    ids = []
    seen = set()
    for a in SUP_ADJ:
        s = sup(a)
        if s in BASE_MOST or s in seen:
            continue
        seen.add(s)
        ids.append(add(
            f'most_{s}', rf"(?i)\b(?P<target>most (?P<s>{s}))(?:[\s.,;:!?)]|$)", '${s}', 'Grammar', 0.95,
            f'“{s.capitalize()}” already means “most {a}”: use “{s}” alone, not “most {s}”.',
            pick(['That was the most {s} one in the shop.', 'She is the most {s} person I know.',
                  'It was the most {s} day of the whole trip.', 'This is the most {s} option we have.'], a).format(s=s),
            f'That was the {s} one in the shop, and most of them were cheaper.'))
    for s, pos, neg in (('farthest', 'It is the most farthest town on the map.', 'It is the farthest town on the map, and most roads end there.'),
                        ('furthest', 'This is the most furthest we have walked.', 'This is the furthest we have walked, and most of us are tired.'),
                        ('nearest', 'Where is the most nearest bank?', 'Where is the nearest bank? Most of them close at five.'),
                        ('worst', 'It was the most worst day of my life.', 'It was the worst day of my life, and most of it was spent waiting.'),
                        ('hottest', 'July was the most hottest month of the year.', 'July was the hottest month of the year, and most days were dry.')):
        if 'mod.most_' + s in IDS:
            continue
        ids.append(add(
            f'most_{s}', rf"(?i)\b(?P<target>most (?P<s>{s}))(?:[\s.,;:!?)]|$)", '${s}', 'Grammar', 0.95,
            f'“{s.capitalize()}” already means “most”: use “{s}” alone, not “most {s}”.', pos, neg))
    cover('Doubled superlatives', 'most + an -est superlative or best/worst (most tallest, most oldest, most best, most worst, most nearest ...); the hyphenated "most best-selling" is untouched', ids)

    # ---- "more and more" + a comparative
    ids = []
    for c in ['better', 'bigger', 'smaller', 'faster', 'slower', 'easier', 'harder', 'cheaper', 'stronger', 'weaker',
              'happier', 'higher', 'lower', 'larger', 'longer', 'shorter', 'older', 'younger', 'taller', 'worse',
              'clearer', 'simpler', 'safer', 'richer', 'poorer', 'darker', 'brighter', 'colder', 'hotter', 'heavier',
              'closer', 'louder']:
        ids.append(add(
            f'more_and_more_{c}', rf"(?i)\b(?P<target>more and more (?P<c>{c}))\b", '${c} and ${c}', 'Grammar', 0.93,
            f'With a comparative, repeat it: “{c} and {c}”, not “more and more {c}”.',
            f'The queue is getting more and more {c}.',
            f'The queue is getting {c} and {c}, and more and more people join it.'))
    cover('Doubled comparatives', '"more and more" + a comparative (more and more bigger -> bigger and bigger)', ids)

    # ---- very + a comparative ("very better")
    ids = []
    # Only comparatives where "much" is plainly the intended word; "very younger" may mean "very young".
    for c in ['better', 'worse', 'bigger', 'smaller', 'faster', 'slower', 'easier', 'harder', 'cheaper', 'stronger',
              'weaker', 'greater', 'earlier', 'more']:
        if f'mod.very_{c}' in IDS:
            continue
        pos_extra = ' than before'
        ids.append(add(
            f'very_{c}', rf"(?i)\b(?P<target>very) {c}\b", 'much', 'Grammar', 0.9,
            f'“Very” does not go with a comparative: say “much {c}”.',
            f'This version is very {c}{pos_extra}.',
            f'This version is much {c}{pos_extra}, and the very best one is next.'))
    cover('Intensifiers with comparatives', 'very + a comparative (very better, very worse, very more ...) -> much', ids)

    # ---- long adjectives given -er / -est ("beautifuler")
    ids = []
    longs = '''beautiful careful useful helpful powerful wonderful peaceful successful famous serious interesting important
expensive difficult popular dangerous comfortable efficient effective intelligent boring tired curious complex patient
cautious delicious ridiculous attractive creative reliable flexible impressive thoughtful grateful harmful colorful
valuable suitable reasonable responsible convenient confident ambitious anxious mysterious generous nervous jealous
fearful hopeful faithful forgetful painful'''.split()
    for a in longs:
        e_er = a + 'r' if a.endswith('e') else a + 'er'
        e_est = a + 'st' if a.endswith('e') else a + 'est'
        ids.append(add(
            f'er_{a}', rf"(?i)\b(?P<target>{e_er})\b", f'more {a}', 'Grammar', 0.95,
            f'“{a.capitalize()}” takes “more”, not -er: say “more {a}”.',
            pick(['This one is {w} than the last one.', 'The new design looks {w} to me.',
                  'She seems {w} than her brother.', 'It got {w} over the years.'], a).format(w=e_er),
            f'This one is more {a} than the last one.'))
        ids.append(add(
            f'est_{a}', rf"(?i)\b(?P<target>{e_est})\b", f'most {a}', 'Grammar', 0.95,
            f'“{a.capitalize()}” takes “most”, not -est: say “most {a}”.',
            pick(['This is the {w} one of all.', 'He is the {w} person on the team.',
                  'It was the {w} choice we had.', 'That is the {w} thing I have seen.'], a).format(w=e_est),
            f'This is the most {a} one of all.'))
    cover('Wrong comparative forms', 'long adjectives given -er/-est (beautifuler, importantest ...) -> more/most + adjective', ids)

    # ---- fun, good, bad forms
    ids = []
    ids.append(add('bestest', r"(?i)\b(?P<target>bestest)\b", 'best', 'Style', 0.75,
                   '“Best” is already a superlative; “bestest” reads as playful or as a slip.',
                   'You are my bestest friend in the whole world.', 'You are my best friend in the whole world.'))
    ids.append(add('goodest', r"(?i)\b(?P<target>goodest)\b", 'best', 'Grammar', 0.95,
                   'The superlative of “good” is “best”.', 'He is the goodest player in the league.',
                   'He is the best player in the league.'))
    ids.append(add('worstest', r"(?i)\b(?P<target>worstest)\b", 'worst', 'Grammar', 0.95,
                   '“Worst” is already a superlative.', 'That was the worstest meal I ever had.',
                   'That was the worst meal I ever had.'))
    ids.append(add('more_gooder', r"(?i)\b(?P<target>more gooder)\b", 'better', 'Grammar', 0.95,
                   'The comparative of “good” is “better”.', 'This one is more gooder than that one.',
                   'This one is better than that one.'))
    ids.append(add('funner', r"(?i)\b(?P<target>funner)\b", 'more fun', 'Style', 0.75,
                   '“Funner” is informal; “more fun” is the standard comparative.',
                   'The second game was funner than the first.', 'The second game was more fun than the first.'))
    ids.append(add('funnest', r"(?i)\b(?P<target>funnest)\b", 'most fun', 'Style', 0.75,
                   '“Funnest” is informal; “most fun” is the standard superlative.',
                   'That was the funnest trip we ever took.', 'That was the most fun trip we ever took.'))
    ids.append(add('more_funner', r"(?i)\b(?P<target>more funner)\b", 'more fun', 'Grammar', 0.9,
                   '“Funner” already contains “more”: say “more fun”.', 'Tonight was more funner than last week.',
                   'Tonight was more fun than last week.'))
    ids.append(add('more_gooder_worse', r"(?i)\b(?P<target>more badder)\b", 'worse', 'Grammar', 0.95,
                   'The comparative of “bad” is “worse”.', 'It got more badder every year.',
                   'It got worse every year.'))
    ids.append(add('more_bad_copula',
                   r"(?i)\b(?:is|was|are|were|seems|seemed|looks|looked|sounds|sounded|feels|felt|got|gets|get) (?P<target>more bad)" + tail("today|now|than|again|this|every|each|yesterday|here|for|to"),
                   'worse', 'Grammar', 0.9, 'The comparative of “bad” is “worse”.',
                   'The pain is more bad today.', 'The pain is worse today. There is more bad news than good.'))
    ids.append(add('more_good_than_copula',
                   r"(?i)\b(?:is|was|are|were|seems|seemed|looks|looked|sounds|sounded|feels|felt|got|gets|get) (?P<target>more good) (?:to|for|in|at|with|when)\b",
                   'better', 'Grammar', 0.9, 'The comparative of “good” is “better”.',
                   'The soup is more good with a little salt.', 'The soup is better with a little salt. There is more good news today.'))
    cover('Wrong comparative forms', 'gooder/badder/baddest (base: usage.irregular_*), goodest, worstest, worser, bestest, funner, funnest, more badder, "is more bad", "is more good for"', ids)

    # ---- more + a short adjective instead of its -er form
    ids = []
    shorts = {
        'tall': 'taller', 'fast': 'faster', 'hard': 'harder', 'cheap': 'cheaper', 'big': 'bigger', 'small': 'smaller',
        'large': 'larger', 'strong': 'stronger', 'weak': 'weaker', 'high': 'higher', 'low': 'lower', 'long': 'longer',
        'short': 'shorter', 'hot': 'hotter', 'soft': 'softer', 'thin': 'thinner', 'thick': 'thicker', 'slow': 'slower',
        'near': 'nearer', 'early': 'earlier', 'wide': 'wider', 'bright': 'brighter', 'safe': 'safer', 'sad': 'sadder',
        'mad': 'madder', 'quick': 'quicker', 'smart': 'smarter', 'loud': 'louder', 'proud': 'prouder',
        'tight': 'tighter', 'easy': 'easier', 'old': 'older', 'young': 'younger', 'rich': 'richer', 'deep': 'deeper',
        'clean': 'cleaner', 'warm': 'warmer', 'cool': 'cooler',
    }
    # old, young, rich, deep, clean, warm, cool can be nouns or plain quantities ("more old and new"), so only the
    # monosyllabic adjectives that are never nouns are kept.
    for a in ['old', 'young', 'rich', 'deep', 'clean', 'warm', 'cool', 'hot', 'bright', 'safe', 'sad', 'mad', 'thin', 'soft']:
        shorts.pop(a)
    for a, c in sorted(shorts.items()):
        ids.append(add(
            f'more_{a}_adj',
            rf"(?i)\b(?P<target>more {a})(?:[.!?,;:)\n]|\s*$|\s+(?:to|for|now|today|if|when|again|too|here|there)\b)",
            c, 'Grammar', 0.85,
            f'A short adjective like “{a}” takes -er: “{c}”, not “more {a}”.',
            pick(['Everything feels more {a} now.', 'The second one looks more {a} today.',
                  'The whole thing got more {a} again.'], a).format(a=a),
            f'Everything feels {c} now. We need more {a} ones, and more of them than before. It is more {a} than {"short" if a != "short" else "tall"}.'))
    cover('Wrong comparative forms', 'more + a short adjective where -er is expected (more easy to, more big, more small, more cheap, more fast ...) only when the adjective ends the clause or precedes to/for/now/today/if/when, so "more big than small" and "more cold air" stay', ids)

    # ---- elder
    ids = []
    ids.append(add('more_elder', r"(?i)\b(?P<target>more elder)\b", 'older', 'Grammar', 0.93,
                   '“Elder” is already a comparative: use “older”.', 'My brother is more elder than I am.',
                   'My brother is older than I am. The elder statesman spoke first.'))
    ids.append(add('elder_to', r"(?i)\b(?P<target>elder to) (?:me|him|her|us|them|you)\b", 'older than', 'Grammar', 0.9,
                   'Compare ages with “older than”, not “elder to”.', 'He is elder to me by two years.',
                   'He is older than me by two years. She is my elder sister.'))
    ids.append(add('eldest_than', r"(?i)\b(?P<target>eldest than)\b", 'older than', 'Grammar', 0.85,
                   '“Eldest” is a superlative and cannot take “than”: compare with “older than”.',
                   'She is eldest than all of her cousins.', 'She is older than all of her cousins. She is the eldest of the three.'))
    cover('Wrong comparative forms', 'elder than (base: usage.elder_than), more elder, elder to, eldest than', ids)
