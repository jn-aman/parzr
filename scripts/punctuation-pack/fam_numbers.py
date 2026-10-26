"""Numbers in compound modifiers ("a three-story house", "a 5-minute break"), spelled-out ordinals ("twenty-first") and
the century modifier ("a 19th-century novel")."""
import re
import core
import lists

DET = r'(?:a|an|the|this|that|our|my|your|their|his|her|its)'

# unit :: head nouns (singular only: "the five dollar bills" may mean five one-dollar bills, so plural heads never match)
UNITS = """
digit :: number code pin prefix extension password field
figure :: salary income deal sum bonus paycheck job
story :: building house home tower structure
storey :: building house home tower
room :: apartment house flat suite condo
bed :: house flat apartment home semi
door :: sedan car hatchback fridge truck
seat :: sofa couch car plane bus van aircraft
lane :: road highway street bridge pool track
course :: meal dinner lunch menu
member :: team panel committee crew board
man :: team crew show job band operation race army tent saw
woman :: team crew show
car :: garage family household pileup accident train
wheel :: drive bike cart vehicle
dollar :: bill coin store shop menu
pound :: note bag fine weight
euro :: note coin
ton :: truck load
tonne :: truck load
gallon :: tank bucket jug drum barrel container
liter :: bottle tank bucket engine jug
litre :: bottle tank bucket engine jug
kilogram :: bag box weight package bar dumbbell kettlebell load
ounce :: bottle can serving
yard :: penalty dash line pass run
centimeter :: gap thickness
centimetre :: gap thickness
millimeter :: gap thickness
millimetre :: gap thickness
kilometre :: run walk race trip drive
pixel :: icon border grid font gap image square margin padding radius
hole :: course round
line :: summary poem description message bio
paragraph :: essay summary letter email description
sentence :: summary description answer explanation
slide :: deck presentation summary pitch
item :: list menu checklist bundle pack
tier :: system architecture model structure cake pricing plan
layer :: cake architecture network model
stage :: process rocket approach plan interview launch rollout
phase :: approach plan project rollout power process
factor :: authentication verification login
click :: checkout install purchase solution process setup signup login payment deploy
speed :: manual transmission gearbox automatic fan bike blender drill
ply :: tissue paper roll wood fabric
""".strip().splitlines()

# adjectives made from a number and a suffix word: "a four legged friend"
SUFFIXED = """
sided :: argument story view game coverage debate relationship deal tape
legged :: race friend creature animal stool table chair
pronged :: approach attack strategy fork
""".strip().splitlines()

BITS = ['8', '16', '32', '64', '128', '256']
BIT_HEADS = 'processor system computer version architecture machine integer color colour encryption key cpu build'.split()

ORDINALS = ['first', 'third', 'fourth', 'fifth', 'sixth', 'seventh', 'eighth', 'ninth']
TENS = ['twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty', 'ninety']

CENTURY_HEADS = ('novel painting poet writer author building house church architecture literature art music philosophy '
                 'poem play opera composer artist city town map engraving style design war economy society farmhouse '
                 'mansion castle').split()


def unit_rule(unit, heads):
    alt = '|'.join(sorted(heads, key=lambda w: (-len(w), w)))
    num = rf'(?:{DET} {lists.NUM_ALT}|(?:a|an) one)'
    pattern = rf'(?i)\b{num}(?P<target> ){unit} (?:{alt})\b'
    head = heads[0]
    n = 'three' if unit not in ('digit', 'figure') else 'six'
    if unit in ('hole',):
        n = 'eighteen'
    a = lists.art(n)
    positive = f'We bought {a} {n} {unit} {head}.'
    fixed = f'We bought {a} {n}-{unit} {head}.'
    negative = f'We bought {a} {n}-{unit} {head}. We looked at {n} {unit} {head}s today.'
    core.add(f'hyphen.num_{unit}_modifier', pattern, '-', 'Punctuation', 0.9,
             f'Hyphenate “{n}-{unit}” when it comes before the noun it describes.', positive, negative, fixed)


def suffix_rule(word, heads):
    alt = '|'.join(sorted(heads, key=lambda w: (-len(w), w)))
    nums = 'one|two|three|four|five|six|eight|many|multi|double|single|triple'
    pattern = rf'(?i)\b{DET} (?:{nums})(?P<target> ){word} (?:{alt})\b'
    head = heads[0]
    pre = 'two' if word != 'legged' else 'four'
    positive = f'It is a {pre} {word} {head}.'
    fixed = f'It is a {pre}-{word} {head}.'
    negative = f'The {head} is {pre} {word}. It is a {pre}-{word} {head}.'
    core.add(f'hyphen.num_{word}_modifier', pattern, '-', 'Punctuation', 0.9,
             f'Hyphenate “{pre}-{word}” when it comes before the noun it describes.', positive, negative, fixed)


def time_rules():
    units = ['minute', 'hour', 'day', 'week', 'month', 'year']
    heads = ('break walk drive meeting call delay wait trial course session ride flight nap test video warning window '
             'period plan contract lease loan program tour trip vacation holiday stay cruise class lesson interview '
             'presentation speech demo tutorial workout rest sprint cycle season term ban suspension deadline '
             'extension warranty guarantee subscription pass').split()
    alt = '|'.join(sorted(heads, key=lambda w: (-len(w), w)))
    for u in units:
        # "a 5 minutes break" -> "a 5-minute break"
        core.add(
            f'hyphen.num_{u}s_modifier',
            rf'(?i)\b(?:a|an) {lists.NUM_ALT}(?P<target> {u}s) (?:{alt})\b', f'-{u}', 'Punctuation', 0.9,
            f'Before a noun, use the singular and a hyphen: “5-{u}”.',
            f'We took a 5 {u}s break.',
            f'The break lasted 5 {u}s. We took a 5-{u} break. We took a break of 5 {u}s.',
            f'We took a 5-{u} break.')
        # "a 5-minutes break" -> "a 5-minute break"
        core.add(
            f'hyphen.num_{u}s_plural_hyphen',
            rf'(?i)\b(?:a|an) {lists.NUM_ALT}-(?P<target>{u}s) (?:{alt})\b', u, 'Punctuation', 0.92,
            f'Before a noun, “5-{u}” stays singular.',
            f'We took a 5-{u}s break.',
            f'We took a 5-{u} break. The break lasted 5 {u}s.',
            f'We took a 5-{u} break.')
        # "in 5-minutes" -> "in 5 minutes"
        core.add(
            f'hyphen.num_{u}s_after_preposition',
            rf'(?i)\b(?:in|within|after|for|every|about|over|than|last|next) {lists.NUM_ALT}(?P<target>-){u}s\b', ' ',
            'Punctuation', 0.9,
            f'Write “5 {u}s” without a hyphen when it is not describing a noun.',
            f'It will be ready in 5-{u}s.',
            f'It will be ready in 5 {u}s. We took a 5-{u} break.',
            f'It will be ready in 5 {u}s.')


def ordinal_rules():
    for tens in TENS:
        alt = '|'.join(ORDINALS)
        pattern = rf'(?i)\b{tens}(?P<target> )(?:{alt})(?:[^-\w]|$)'
        ordinal = 'fifth'
        core.add(
            f'hyphen.ordinal_{tens}', pattern, '-', 'Punctuation', 0.93,
            f'Hyphenate a spelled-out ordinal from {tens}-first to {tens}-ninth.',
            f'She finished in {tens} fifth place.',
            f'She finished in {tens}-fifth place. They scored {tens} first-half goals.',
            f'She finished in {tens}-fifth place.')


def century_rules():
    alt = '|'.join(sorted(CENTURY_HEADS, key=lambda w: (-len(w), w)))
    for c, spelled in (('17th', 'seventeenth'), ('18th', 'eighteenth'), ('19th', 'nineteenth'), ('20th', 'twentieth'),
                       ('21st', 'twenty first')):
        a = 'an' if c == '18th' else 'a'
        pattern = rf'(?i)\b(?:a|an|the|this|that|my|your|their|his|her) {c}(?P<target> )century (?:{alt})\b'
        core.add(
            f'hyphen.century_{c}', pattern, '-', 'Punctuation', 0.9,
            f'Hyphenate “{c}-century” when it comes before the noun it describes.',
            f'She wrote {a} {c} century novel.',
            f'The novel is from the {c} century. She wrote {a} {c}-century novel.',
            f'She wrote {a} {c}-century novel.')
    core.add(
        'hyphen.one_size_fits_all',
        rf'(?i)\b{DET} (?P<target>one size fits all) (?:approach|solution|policy|model|strategy|mentality|template|plan)\b',
        'one-size-fits-all', 'Punctuation', 0.9,
        'Hyphenate “one-size-fits-all” when it comes before the noun it describes.',
        'It is a one size fits all solution.',
        'The solution is one size fits all. It is a one-size-fits-all solution.',
        'It is a one-size-fits-all solution.')
    core.add(
        'hyphen.bit_modifier',
        rf'(?i)\b(?:a|an|the|this|that|our|my|your|their) (?:{"|".join(BITS)})(?P<target> )bit (?:{"|".join(BIT_HEADS)})\b',
        '-', 'Punctuation', 0.9,
        'Hyphenate “64-bit” when it comes before the noun it describes.',
        'This is a 64 bit processor.',
        'The processor is 64 bit. This is a 64-bit processor.',
        'This is a 64-bit processor.')


def build():
    for line in UNITS:
        unit, heads = [p.strip() for p in line.split('::')]
        unit_rule(unit, heads.split())
    for line in SUFFIXED:
        word, heads = [p.strip() for p in line.split('::')]
        suffix_rule(word, heads.split())
    time_rules()
    ordinal_rules()
    century_rules()
