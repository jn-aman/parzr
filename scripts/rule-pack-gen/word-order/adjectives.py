"""Adjective position and order: "a car red" -> "a red car", "a red big car" -> "a big red car"."""
from lib import *

THINGS = ('car|bike|bag|shirt|dress|hat|jacket|coat|pen|book|phone|house|table|chair|door|ball|bottle|box|flower|apple|'
          'cup|scarf|umbrella|laptop|sofa|bus|van|truck|balloon|pencil|carpet|curtain|watch|ring|cap|sweater|skirt|tie|'
          'belt|bed|lamp|vase|bowl|plate|basket|backpack|suitcase|wallet')
COLOURS = ['red', 'blue', 'green', 'yellow', 'black', 'white', 'brown', 'grey', 'gray', 'pink', 'purple']
SIZES = ['big', 'small', 'large', 'tiny', 'huge', 'tall', 'new', 'cheap', 'expensive', 'heavy', 'long', 'short', 'young',
         'nice', 'beautiful', 'old']
V_INDEF = (r'(?:have|has|had|own|owns|owned|bought|buy|buys|saw|see|sees|found|find|sold|sell|wore|wear|wears|wearing|'
           r'drive|drives|drove|driving|ordered|order|want|wants|wanted|need|needs|needed|like|likes|liked|love|loves|'
           r'loved|got|get|gets|took|take|takes|chose|choose|picked|pick|carry|carries|carried|carrying|using|use|uses|'
           r'used|purchased|purchase|noticed|notice|bring|brought)')
V_DEF = (r'(?:bought|buy|buys|wore|wear|wears|wearing|drive|drives|drove|driving|sold|sell|sells|ordered|order|owns|own|'
         r'owned|picked|chose|choose)')
FOLL = r'(?:\s*[.;!?)]|\s*$|\s+(?:because|so|that|which|yesterday|today|last|near|outside|by|when)\b)'


def build_postposed():
    for i, c in enumerate(COLOURS):
        noun = THINGS.split('|')[i * 4 % len(THINGS.split('|'))]
        pat = subst(r'(?i)\b<<V>>\s+(?P<target>(?-i:a|an) (?P<n>' + THINGS + r') (?-i:' + c + r'))<<F>>', V=V_INDEF, F=FOLL)
        R(f'colour_after.indef.{c}', pat, 'a ' + c + ' ${n}', 'Grammar', 0.9,
          f'An adjective goes before its noun: “a {c} {noun}”.',
          f'I bought a {noun} {c}.', f'I bought a {c} {noun}.',
          f'I bought a {c} {noun}. I painted the {noun} {c}. I like my coffee {c}. I bought a {noun}, {c} and shiny.')
        pat = subst(r'(?i)\b<<V>>\s+(?P<target>(?P<d>the|my|your|his|her|our|their|this|that) (?P<n>' + THINGS + r') (?-i:' + c + r'))<<F>>',
                    V=V_DEF, F=FOLL)
        R(f'colour_after.def.{c}', pat, '${d} ' + c + ' ${n}', 'Grammar', 0.9,
          f'An adjective goes before its noun: “the {c} {noun}”.',
          f'She wore the {noun} {c} yesterday.', f'She wore the {c} {noun} yesterday.',
          f'She wore the {c} {noun} yesterday. She wanted the {noun} {c}. She painted the {noun} {c}.')
    for i, a in enumerate(SIZES):
        noun = THINGS.split('|')[(i * 3 + 1) % len(THINGS.split('|'))]
        art = 'an' if a == 'old' else 'a'
        pat = subst(r'(?i)\b<<V>>\s+(?P<target>(?-i:a|an) (?P<n>' + THINGS + r') (?-i:' + a + r'))<<F>>', V=V_INDEF, F=FOLL)
        R(f'adj_after.indef.{a}', pat, f'{art} {a} ' + '${n}', 'Grammar', 0.88,
          f'An adjective goes before its noun: “{art} {a} {noun}”.',
          f'We have a {noun} {a}.', f'We have {art} {a} {noun}.',
          f'We have {art} {a} {noun}. We need a {noun} {a} enough for four. I found a {noun} {a} to carry, easy to use.')
        pat = subst(r'(?i)\b<<V>>\s+(?P<target>(?P<d>the|my|your|his|her|our|their|this|that) (?P<n>' + THINGS + r') (?-i:' + a + r'))<<F>>',
                    V=V_DEF, F=FOLL)
        R(f'adj_after.def.{a}', pat, '${d} ' + a + ' ${n}', 'Grammar', 0.88,
          f'An adjective goes before its noun: “the {a} {noun}”.',
          f'He sold the {noun} {a}.', f'He sold the {a} {noun}.',
          f'He sold the {a} {noun}. He sold the {noun} {a} enough for two.')


# --- the order of adjectives: size, age, colour, origin, material -----------------------------------------------
SIZE = ['big', 'small', 'large', 'tiny', 'huge', 'tall']
AGE = ['old', 'young', 'ancient']
AGE_NEW = ['new', 'old', 'young', 'ancient']
COLOUR = ['red', 'blue', 'green', 'yellow', 'black', 'white', 'brown', 'grey', 'gray', 'pink', 'purple']
ORIGIN = ['French', 'Italian', 'Chinese', 'Indian', 'Japanese', 'German', 'Spanish', 'American', 'British', 'English',
          'Russian', 'Mexican', 'Korean', 'Greek', 'Turkish', 'Swiss']
MATERIAL = ['wooden', 'leather', 'plastic', 'cotton', 'silk', 'woolen', 'woollen', 'ceramic']
PAIRS = [
    ('colour_size', COLOUR, SIZE), ('colour_age', COLOUR, AGE), ('material_size', MATERIAL, SIZE),
    ('material_age', MATERIAL, AGE_NEW), ('material_colour', MATERIAL, COLOUR), ('origin_size', ORIGIN, SIZE),
    ('origin_age', ORIGIN, AGE), ('material_origin', MATERIAL, ORIGIN),
]
VOWELS = 'AEIOUaeiou'


def build_order():
    for name, later, earlier in PAIRS:
        cons = [e for e in earlier if e[0] not in VOWELS]
        vow = [e for e in earlier if e[0] in VOWELS]
        l_alt = '|'.join(later)
        l0 = later[0]
        noun = 'house' if 'size' in name or 'age' in name else 'bag'
        # definite determiner: no article to fix
        e_alt = '|'.join(earlier)
        e0 = earlier[0]
        pat = subst(r'(?i)\b(?P<d>the|my|your|his|her|our|their|this|that|these|those)\s+(?P<target>(?P<l>(?-i:' + l_alt +
                    r'))\s+(?P<e>(?-i:' + e_alt + r')))\s+[a-z]+\b')
        pat = r'(?i)\b(?:the|my|your|his|her|our|their|this|that|these|those)\s+(?P<target>(?P<l>(?-i:' + l_alt + r'))\s+(?P<e>(?-i:' + e_alt + r')))\s+[a-z]+\b'
        R(f'adj_order.{name}.def', pat, '${e} ${l}', 'Grammar', 0.88,
          'English adjectives go in a fixed order, so “' + f'{e0} {l0}' + '” comes before the noun, not after another adjective.',
          f'We love the {l0} {e0} {noun}.', f'We love the {e0} {l0} {noun}.',
          f'We love the {e0} {l0} {noun}. We love the {l0} {noun}. We love the {e0} one.')
        for kind, words, art in (('a', cons, 'a'), ('an', vow, 'an')):
            if not words:
                continue
            w_alt = '|'.join(words)
            w0 = words[0]
            pat = (r'(?i)\b[a-z]+ (?P<target>(?-i:a|an) (?P<l>(?-i:' + l_alt + r'))\s+(?P<e>(?-i:' + w_alt + r')))\s+[a-z]+\b')
            R(f'adj_order.{name}.{kind}', pat, f'{art} ' + '${e} ${l}', 'Grammar', 0.88,
              'English adjectives go in a fixed order, so “' + f'{w0} {l0}' + '” comes before the noun, not after another adjective.',
              f'We bought a {l0} {w0} {noun}.', f'We bought {art} {w0} {l0} {noun}.',
              f'We bought {art} {w0} {l0} {noun}. We bought a {l0} {noun}. We bought {art} {w0} one.')


def build():
    build_postposed()
    build_order()
