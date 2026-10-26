"""Compound modifiers: hyphen between the words of a compound that comes right before a noun it describes."""
import re
import core
import lists
import data_compounds as D

# Compounds that end in a particle read as a verb phrase after "and", "for", "to ..." ("and pick up orders"):
# they are hyphenated only right after a determiner.
PARTICLES = {'up', 'down', 'in', 'out', 'on', 'off', 'through', 'over', 'to', 'back', 'away', 'around', 'along'}
DET_ONLY = {'go to', 'take home', 'work from home', 'do it yourself', 'one time', 'one off', 'one way', 'two way',
            'three way', 'in person', 'built in', 'hands on', 'hands off', 'front line', 'start up', 'walk in'}
# Compounds whose head nouns are all singular (a plural could start a new clause: "the early stage companies often").
SINGULAR_ONLY = {'early stage', 'late stage', 'end stage', 'top level', 'real world', 'real life', 'next level',
                 'high school', 'last second', 'last ditch', 'last gasp', 'old world', 'old time'}


def parse(lines):
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        open_form, heads = [p.strip() for p in line.split('::')]
        yield open_form, heads.split()


def one(open_form, heads, conf=0.9):
    words = open_form.split(' ')
    det_only = open_form in DET_ONLY or words[-1] in PARTICLES
    if open_form in SINGULAR_ONLY:
        heads = [h.rstrip('*') + '*' for h in heads]
    left = lists.LEFT_DET_ALT if det_only else lists.LEFT_ALT
    hyph = '-'.join(words)
    alt = lists.heads_alt(heads)
    if len(words) == 2:
        mid = f'{words[0]}(?P<target> ){words[1]}'
        repl = '-'
    else:
        mid = f'(?P<target>{open_form})'
        repl = hyph
    pattern = rf'(?i)\b{left} {mid} (?:{alt})\b'
    head = lists.first_head(heads)
    article = lists.art(open_form) if not words[0].endswith('s') else 'the'
    positive = f'It is {article} {open_form} {head}.'
    fixed = f'It is {article} {hyph} {head}.'
    negative = f'The {head} is {open_form}. It was {article} {hyph} {head}.'
    core.add(
        'hyphen.' + re.sub(r'[^a-z0-9]+', '_', open_form.lower()) + '_modifier', pattern, repl, 'Punctuation', conf,
        f'Hyphenate “{hyph}” when it comes before the noun it describes.', positive, negative, fixed)


def build():
    for block in (D.PEOPLE_WORK, D.ORIENT, D.FREE, D.GRADES, D.SIZED, D.LEVELS, D.OPEN, D.PREP):
        for open_form, heads in parse(block):
            one(open_form, heads)
    # "English speaking countries"
    heads = 'country world population community customer student audience staff region area nation market user resident employee worker public visitor tourist parent family people'.split()
    for lang in D.LANGS:
        alt = lists.heads_alt(heads)
        core.add(
            'hyphen.' + lang.lower() + '_speaking',
            rf'(?i)\b{lang}(?P<target> )speaking (?:{alt})\b', '-', 'Punctuation', 0.9,
            f'Hyphenate “{lang}-speaking” when it comes before the noun it describes.',
            f'Many {lang}-speaking countries'.replace('-', ' ') + ' joined.',
            f'The group is {lang} speaking. A {lang}-speaking country joined.',
            f'Many {lang}-speaking countries joined.')
    # always hyphenated nouns and adjectives
    for open_form, hyph, left, pos, fixed, neg in D.ALWAYS:
        w0, w1 = open_form.split(' ')
        if w0 == 'u':
            w0 = '(?-i:U)'
        if hyph == open_form.replace(' ', '-'):
            pattern = rf'(?i)\b{left} (?:[a-z]+ )?{w0}(?P<target> ){w1}\b'
            repl = '-'
        else:
            pattern = rf'(?i)\b{left} (?:[a-z]+ )?(?P<target>{w0} {w1})\b'
            repl = hyph
        core.add('hyphen.' + re.sub(r'[^a-z0-9]+', '_', open_form.lower()), pattern, repl, 'Punctuation', 0.88,
                 f'Write “{hyph}” with a hyphen.', pos, neg, fixed)
