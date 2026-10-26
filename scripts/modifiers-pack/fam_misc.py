"""Absolute and extreme adjectives, "enough" before an adjective, very/too/so/much + adjective, "same like", and the
non-word adverb "fastly"."""
from core import add, cover, pick, IDS

ENOUGH_ADJ = '''good big large small strong fast old tall long high hot cold warm safe smart clear loud wide thick rich bright
quick cheap simple deep fresh clean mature capable confident brave heavy light fit healthy beautiful fair careful sharp
skilled experienced qualified comfortable spacious sturdy stable reliable accurate flexible powerful fluent
ready'''.split()

VM_ADJ = '''happy sad hungry thirsty busy late early difficult easy hard nice beautiful big small hot expensive cheap
important kind tall short fast slow clean dirty sleepy lazy shy funny lucky comfortable friendly noisy heavy'''.split()
# adjectives that are also nouns in "too much cold", "so much sweet", "too much light" are left out of the too/so/much sets
TM_ADJ = '''tired hot expensive late early difficult big small busy slow fast heavy tight loose long short noisy crowded
salty spicy sad angry hungry sleepy lazy shy risky dangerous complicated complex boring easy hard'''.split()

ABSOLUTE = ['perfect', 'absolute', 'infinite', 'impossible', 'universal', 'identical', 'ultimate', 'unanimous', 'unique']
EXTREME = ['excellent', 'fantastic', 'terrific', 'enormous', 'gigantic', 'immense', 'huge', 'outstanding', 'magnificent',
           'superb', 'marvelous', 'marvellous', 'freezing', 'boiling', 'starving', 'spotless', 'priceless']


def build():
    # ---- absolute adjectives: "very unique"
    ids = []
    for a in ABSOLUTE:
        ids.append(add(
            f'very_{a}_abs', rf"(?i)\b(?P<target>very ){a}\b", '', 'Style', 0.78,
            f'“{a.capitalize()}” already means “completely so”, so it does not need “very”.',
            pick(['The design is very %s.', 'The result was very %s.', 'Her answer was very %s.'], a) % a,
            f'The design is {a}. He came the very first day.'))
    for mod in ['most', 'more']:
        ids.append(add(
            f'{mod}_unique', rf"(?i)\b(?P<target>{mod} unique)\b", f'{mod} distinctive', 'Style', 0.78,
            '“Unique” means one of a kind and cannot be compared: say “distinctive” or “unusual”.',
            f'It is the {mod} unique shop in town.' if mod == 'most' else 'This design is more unique than the last.',
            'It is the most distinctive shop in town. It is unique.' if mod == 'most' else 'This design is more distinctive than the last. It is unique.'))
    for mod in []:
        ids.append(add(
            f'{mod}_unique', rf"(?i)\b(?P<target>{mod} unique)\b", f'{mod} unusual', 'Style', 0.76,
            '“Unique” means one of a kind and cannot be qualified: say “unusual” or “distinctive”.',
            f'Her style is {mod} unique.', f'Her style is {mod} unusual. Her style is unique.'))
    cover('Absolute adjectives', 'very + perfect/absolute/infinite/impossible/universal/identical/ultimate/unanimous/unique -> drop "very"; most/more unique -> most/more distinctive; "somewhat/relatively/fairly unique", "very complete/essential/ideal", "more perfect" ("a more perfect union"), "quite unique" (= completely) are left: widely used and accepted', ids)

    # ---- extreme adjectives: "very excellent"
    ids = []
    for a in EXTREME:
        ids.append(add(
            f'very_{a}_ext', rf"(?i)\b(?P<target>very ){a}\b", '', 'Style', 0.72,
            f'“{a.capitalize()}” is already extreme, so “very” adds nothing.',
            pick(['The food was very %s.', 'Our evening was very %s.', 'His answer was very %s.'], a) % a,
            f'The food was {a}. The food was really {a}. It was very good.'))
    cover('Extreme adjectives', 'very + excellent/fantastic/terrific/enormous/gigantic/immense/huge/outstanding/magnificent/superb/marvelous/freezing/boiling/starving/spotless/priceless (Style, 0.72); "very delighted/furious/exhausted/hilarious" are in wide use and left; "really"/"absolutely" are untouched', ids)

    # ---- enough before an adjective
    ids = []
    for a in ENOUGH_ADJ:
        pos_t = pick(['This room is not enough {a} for ten people.', 'The rope was not enough {a} to hold him.',
                      'She is enough {a} to apply.', 'The soup is not enough {a} for me.'], a)
        ids.append(add(
            f'enough_{a}',
            rf"(?i)(?:\b(?:am|is|are|was|were|be|been|being|not|looks?|seems?|feels?|sounds?)|['’](?:m|s|re)|n['’]t)\s+(?P<target>enough (?P<a>{a}))(?:[.!?,;:)\n\"”]|\s*$|\s+(?:to|for)\b)",
            '${a} enough', 'Grammar', 0.9,
            f'“Enough” goes after an adjective: “{a} enough”, not “enough {a}”.',
            pos_t.format(a=a),
            f'This room is {a} enough for ten people. There is enough {a} room. We have enough {a} chairs.'))
    cover('Enough', 'enough + adjective in the wrong order after a be/linking verb or "not" (not enough good to -> not good enough to); "enough good reasons" and "enough money" are left', ids)

    # ---- very much / too much / so much / much + adjective
    ids = []
    TAIL = r"(?:[.!?;:)\n\"”]|\s*$|\s+(?:to|for|today|now|here|there|because|so)\b)"
    for a in VM_ADJ:
        ids.append(add(
            f'very_much_{a}', rf"(?i)\b(?P<target>very much) {a}\b", 'very', 'Grammar', 0.9,
            f'Before an adjective use “very”: “very {a}”. “Very much” goes with verbs.',
            pick(['She is very much %s today.', 'We were very much %s after the trip.', 'The room looks very much %s.'], a) % a,
            f'She is very {a} today. She likes it very much. He is very much the leader.'))
    for a in TM_ADJ:
        ids.append(add(
            f'too_much_{a}', rf"(?i)\b(?P<target>too much) {a}{TAIL}", 'too', 'Grammar', 0.9,
            f'Before an adjective use “too”: “too {a}”. “Too much” goes with nouns and verbs.',
            pick(['The soup is too much %s.', 'I am too much %s to go out.', 'The bag is too much %s for me.'], a) % a,
            f'The soup is too {a}. There is too much {a} sauce. I ate too much.'))
        ids.append(add(
            f'so_much_{a}', rf"(?i)\b(?P<target>so much) {a}{TAIL}", 'so', 'Grammar', 0.9,
            f'Before an adjective use “so”: “so {a}”. “So much” goes with nouns and verbs.',
            pick(['The room is so much %s.', 'I am so much %s today.', 'The box was so much %s to carry.'], a) % a,
            f'The room is so {a}. There is so much {a} work. I like it so much.'))
        ids.append(add(
            f'much_{a}',
            rf"(?i)\b(?:am|is|are|was|were|feel|feels|felt|look|looks|looked|seem|seems|seemed|['’]m|['’]s|['’]re) (?P<target>much) {a}{TAIL}",
            'very', 'Grammar', 0.88,
            f'Before an adjective use “very”: “very {a}”. A bare “much” does not modify adjectives.',
            pick(['I am much %s today.', 'The street is much %s now.', 'She looked much %s.'], a) % a,
            f'I am very {a} today. There is much more to see.'))
    cover('Very, too, so and much', 'very much / too much / so much / much + an adjective: very much happy -> very happy, too much tired -> too tired, so much busy -> so busy, is much late -> is very late (only when the adjective ends the clause or precedes to/for/today/now/here/there/because/so, so "too much hot water" and "so much cold air" stay; "very much alive", "very much the same", "very much better" stay)', ids)

    # ---- same like / as same as
    ids = []
    BE = r"(?:is|are|was|were|looks?|looked|sounds?|sounded|feels?|felt|works?|worked|tastes?|tasted|seems?|seemed|stays?|stayed|remains?|remained)"
    ADV = r"(?:(?:almost|exactly|just|nearly|pretty much|roughly|basically|quite|more or less) )?"
    ids.append(add(
        'same_like_be', rf"(?i)\b{BE} {ADV}(?P<target>same like)\b", 'the same as', 'Grammar', 0.92,
        'Say “the same as”, not “same like”.', 'This phone is same like the old one.',
        'This phone is the same as the old one. They look alike. It works like the old one.'))
    ids.append(add(
        'same_like_do',
        r"(?i)\b(?:did|do|does|doing|said|say|says|thought|think|felt|feel|got|get|bought|buy|have|had|made|make|use|used|wanted|ordered|order|wore|wear|asked|ask|told|tell) (?P<target>same like)\b",
        'the same as', 'Grammar', 0.92, 'Say “the same as”, not “same like”.',
        'I bought same like you did.', 'I bought the same as you did. I bought one like yours.'))
    ids.append(add(
        'same_than_be', rf"(?i)\b{BE} {ADV}(?P<target>same than)\b", 'the same as', 'Grammar', 0.92,
        'Say “the same as”, not “same than”.', 'The new plan is same than the old one.',
        'The new plan is the same as the old one. The new plan is better than the old one.'))
    ids.append(add(
        'as_same_as', r"(?i)\b(?P<target>as same as)\b", 'the same as', 'Grammar', 0.93,
        'Say “the same as”, not “as same as”.', 'Your answer is as same as mine.',
        'Your answer is the same as mine. Your answer is as good as mine.'))
    ids.append(add(
        'same_as_like', r"(?i)\b(?P<target>same as like)\b", 'the same as', 'Grammar', 0.9,
        'Say “the same as”.', 'It tastes same as like the one at home.',
        'It tastes the same as the one at home. It tastes like the one at home.'))
    cover('Same', 'same like / same than after a be or linking verb, same like after verbs of doing, as same as, same as like -> the same as (the same like / the same than is base prep.same_like_than)', ids)

    # ---- fastly
    ids = []
    ids.append(add(
        'fastly', r"(?i)\b(?P<target>fastly)\b", 'fast', 'Spelling', 0.93,
        '“Fastly” is not a word: “fast” is both the adjective and the adverb.',
        'He runs fastly when he is late.', 'He runs fast when he is late. It is a fast car.'))
    ids.append(add(
        'hardlier', r"(?i)\b(?P<target>more hardly|most hardly)\b", 'harder', 'Grammar', 0.85,
        '“Hardly” means “almost not”. For more effort, say “harder”.',
        'You must work more hardly this term.', 'You must work harder this term. She can hardly work.'))
    cover('Non-words', 'fastly -> fast (easyly, happyly, luckyly, simplely, truely ... are spelling corrections in the engine already); more hardly -> harder', ids)
