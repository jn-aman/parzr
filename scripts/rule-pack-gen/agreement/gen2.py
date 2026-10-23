"""Part 2: noun subjects (listed nouns), uncountables, plural-only and classical plurals."""
from lib import *
import vocab

F = '(?im)'
A = r"(?P<a>['’])"

WERE_L = r'(?:^|' + END + r'\s+|\b(?:because|when|since)\s+)'

DET_PL = ('the|these|those|my|our|your|his|her|their|its|some|many|several|both|all|all the|no|any|few|most|other|'
          'various|numerous|multiple|a few|a couple of|a lot of|lots of|plenty of|dozens of|hundreds of|thousands of|one or two|two or three|'
          'three or four')
DET_SG = 'the|this|that|my|our|your|his|her|their|its|each|every|another|any|no|one|a|an|the same|the other'
DET_UN = 'the|this|that|my|our|your|his|her|their|its|some|much|any|no|most|more|all the|all|less|enough|half the'
ADJ_RX = '(?:' + '|'.join(sorted(set(vocab.ADJ), key=lambda w: (-len(w), w))) + ')'

PLV = [('is', 'are', 'ready', 'is'), ('was', 'were', 'late', 'was'), ('has', 'have', 'arrived', 'has'),
       ('does', 'do', 'the work', 'does'),
       ("isn't", "aren't", 'ready', 'isn\'t'), ("wasn't", "weren't", 'late', 'wasn\'t'),
       ("hasn't", "haven't", 'arrived', 'hasn\'t'), ("doesn't", "don't", 'agree', 'doesn\'t')]
# (wrong singular verb, right plural verb, complement)

def vpat(v):
    """regex for a verb, with the apostrophe captured as ${a}; returns (pattern, replacement template)"""
    if "n't" in v:
        stem = v.split("n't")[0]
        return stem + 'n' + A + 't'
    return v

def vrep(w):
    if "n't" in w:
        stem = w.split("n't")[0]
        return stem + 'n${a}t'
    return w

# Plural nouns after which the engine's own possessive pass and its agreement pass undo each other when the verb is "has"
# ("The cats has arrived." makes the baseline engine report "Corrections did not stabilize"): the "has" rules leave them out.
BAN_HAS = set('cats dogs mothers neighbors neighbours partners roommates sisters sons teachers uncles'.split())

def spl(words, n):
    """split a word list into chunks of at most n"""
    words = sorted(set(words))
    k = (len(words) + n - 1) // n
    size = (len(words) + k - 1) // k
    return [words[i:i + size] for i in range(0, len(words), size)]

PLURAL_GROUPS = {
    'people': vocab.PL_PEOPLE,
    'work': vocab.PL_WORK,
    'home': vocab.PL_HOME,
    'only': vocab.PL_ONLY,
    'classical': vocab.PL_CLASSICAL,
}
SINGULAR_GROUPS = {
    'people': vocab.SG_PEOPLE,
    'work': vocab.SG_WORK,
    'home': vocab.SG_HOME,
}
SG_OF = {n: None for n in []}

def plural_for(n):
    return None

# ---- plural noun + singular verb ------------------------------------------------------------------
# (a representative positive noun per group; the negative uses the singular partner)
POS_PL = {'people': ['students', 'managers', 'customers', 'teachers', 'drivers', 'players', 'doctors', 'voters'],
          'work': ['files', 'reports', 'changes', 'results', 'tickets', 'updates', 'requests', 'settings'],
          'home': ['books', 'shoes', 'windows', 'dishes', 'tickets', 'toys', 'songs', 'letters'],
          'only': ['scissors', 'jeans', 'clothes', 'pajamas', 'stairs', 'goods', 'groceries', 'fireworks'],
          'classical': ['criteria', 'phenomena', 'bacteria', 'alumni', 'analyses', 'hypotheses', 'curricula', 'stimuli']}
SING_OF = {'students': 'student', 'managers': 'manager', 'customers': 'customer', 'teachers': 'teacher',
           'drivers': 'driver', 'players': 'player', 'doctors': 'doctor', 'voters': 'voter',
           'files': 'file', 'reports': 'report', 'changes': 'change', 'results': 'result', 'tickets': 'ticket',
           'updates': 'update', 'requests': 'request', 'settings': 'setting', 'books': 'book', 'shoes': 'shoe',
           'windows': 'window', 'dishes': 'dish', 'toys': 'toy', 'songs': 'song', 'letters': 'letter',
           'criteria': 'criterion', 'phenomena': 'phenomenon', 'bacteria': 'bacterium', 'alumni': 'alumnus',
           'analyses': 'analysis', 'hypotheses': 'hypothesis', 'curricula': 'curriculum', 'stimuli': 'stimulus',
           'scissors': None, 'jeans': None, 'clothes': None, 'pajamas': None, 'stairs': None, 'goods': None,
           'groceries': None, 'fireworks': None}

for gname, words in PLURAL_GROUPS.items():
    chunks = spl(words, 100)
    for ci_, chunk0 in enumerate(chunks):
        suffix = '' if len(chunks) == 1 else str(ci_ + 1)
        for vi, (wrong, right, comp, _) in enumerate(PLV):
            chunk = [w for w in chunk0 if w not in BAN_HAS] if wrong == 'has' else chunk0
            pool = [w for w in POS_PL[gname] if w in chunk] or [chunk[0]]
            noun = pool[vi % len(pool)]
            sing = SING_OF.get(noun)
            pattern = (F + CLN + r'(?:' + DET_PL + r') (?:' + ADJ_RX + r' )?(?-i:' + '|'.join(sorted(chunk, key=lambda w: (-len(w), w)))
                       + r') (?P<target>' + vpat(wrong) + r')\b')
            pos = ('The ' if vi % 2 == 0 else 'I think the ') + noun + ' ' + wrong + ' ' + comp + '.'
            negs = ['The ' + noun + ' ' + right + ' ' + comp + '.']
            if sing and sing != noun:
                negs.append('The ' + sing + ' ' + wrong + ' ' + comp + '.')
            negs.append('The number of ' + noun + ' ' + wrong + ' ' + comp + '.')
            negs.append('One of the ' + noun + ' ' + wrong + ' ' + comp + '.')
            if gname == 'work':
                negs.append('The Files app ' + wrong + ' ' + comp + '.')
            add('agree.pl_noun_' + gname + suffix + '_' + wrong.replace("'", ''),
                pattern, vrep(right), 'Agreement', 0.95,
                'The subject is plural, so use ' + q(right) + '.',
                pos, ' '.join(negs))

# ---- singular noun + plural verb ------------------------------------------------------------------
SGV = [('are', 'is', 'ready'), ('have', 'has', 'arrived'), ('do', 'does', 'the work'),
       ("aren't", "isn't", 'ready'), ("haven't", "hasn't", 'arrived'), ("don't", "doesn't", 'agree'),
       ('were', 'was', 'late'), ("weren't", "wasn't", 'late')]
POS_SG = {'people': ['student', 'manager', 'customer', 'teacher', 'driver', 'player', 'doctor', 'voter'],
          'work': ['file', 'report', 'change', 'result', 'ticket', 'update', 'request', 'setting'],
          'home': ['book', 'shoe', 'window', 'dish', 'ticket', 'toy', 'song', 'letter'],
          'uncount': ['information', 'advice', 'equipment', 'furniture', 'research', 'feedback', 'progress',
                      'knowledge']}
PLUR_OF = {v: k for k, v in SING_OF.items() if v}

def sg_rules(gname, words, det, prefix):
    chunks = spl(words, 100)
    for ci_, chunk in enumerate(chunks):
        suffix = '' if len(chunks) == 1 else str(ci_ + 1)
        for vi, (wrong, right, comp) in enumerate(SGV):
            pool = [w for w in POS_SG[gname] if w in chunk] or [chunk[0]]
            noun = pool[vi % len(pool)]
            # bare forms and "were" need a strict clause start (subjunctive, do-support questions)
            if wrong in ('have', 'do'):
                lc = CL_N
            elif wrong in ('were', "weren't"):
                lc = WERE_N
            else:
                lc = CLN_SG
            pattern = (F + lc + r'(?:' + det + r') (?:' + ADJ_RX + r' )?(?-i:' + '|'.join(sorted(chunk, key=lambda w: (-len(w), w)))
                       + r') (?P<target>' + vpat(wrong) + r')\b')
            lead = 'The ' if vi % 2 == 0 else 'I think the '
            if wrong in ('were', "weren't"):
                lead = 'The '
            pos = lead + noun + ' ' + wrong + ' ' + comp + '.'
            negs = ['The ' + noun + ' ' + right + ' ' + comp + '.']
            pl = PLUR_OF.get(noun)
            if pl:
                negs.append('The ' + pl + ' ' + wrong + ' ' + comp + '.')
            negs.append('Does the ' + noun + ' ' + ('have' if wrong == 'have' else 'do') + ' ' + comp + '?')
            if wrong in ('have', 'do'):
                negs.append('We insist that the ' + noun + ' ' + wrong + ' ' + comp + '.')
            if wrong in ('were', "weren't"):
                negs.append('If the ' + noun + ' ' + wrong + ' ' + comp + ', we would know.')
            add('agree.sg_noun_' + prefix + suffix + '_' + wrong.replace("'", ''),
                pattern, vrep(right), 'Agreement', 0.95,
                'The subject is singular, so use ' + q(right) + '.',
                pos, ' '.join(negs))

for gname, words in SINGULAR_GROUPS.items():
    sg_rules(gname, words, DET_SG, gname)

# ---- uncountable + plural verb -------------------------------------------------------------------
sg_rules('uncount', vocab.UNCOUNT, DET_UN, 'mass')
