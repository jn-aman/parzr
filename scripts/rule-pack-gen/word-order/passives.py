"""Intransitive verbs given a passive: "It is happened", "The package is arrived", "It will be happened"."""
from lib import *

# verbs that never take a passive: base, past participle, and a natural continuation for the examples
PERFECT = [
    ('happen', 'happened', 'The accident', ' on Monday'),
    ('occur', 'occurred', 'An error', ' during the update'),
    ('arrive', 'arrived', 'The parcel', ' at the office'),
    ('appear', 'appeared', 'A message', ' on the screen'),
    ('disappear', 'disappeared', 'My wallet', ' from the desk'),
    ('die', 'died', 'The plant', ' last week'),
    ('vanish', 'vanished', 'The money', ' overnight'),
    ('emerge', 'emerged', 'A new problem', ' in March'),
]


def build_be_participle():
    for base, pp, subj, tail in PERFECT:
        # "It is happened" -> "It happened"; "The parcel is arrived" -> "The parcel has arrived"
        simple = base in ('happen', 'occur', 'emerge', 'appear')
        for be, have in (('is', 'has'), ('are', 'have'), ('am', 'have')):
            if be == 'am' and simple:
                continue  # "I am happened" is not a sentence anyone writes
            fol = r'\b'
            if base == 'arrive':
                # "the conclusion is arrived at" is a real passive; only flag the intransitive uses
                fol = (r'(?:\s*[.,;:!?)]|\s*$|\s+(?:in|on|from|to|there|here|late|early|today|yesterday|safely|home|'
                       r'at (?:[0-9]|noon|midnight|the (?:airport|station|office|hotel|gate)))\b)')
            pat = r'(?i)\b(?P<target>' + be + ' ' + pp + r')' + fol
            rep = pp if simple else f'{have} {pp}'
            if be == 'is':
                pos = f'{subj} is {pp}{tail}.'
                exp = f'{subj} {pp}{tail}.' if simple else f'{subj} has {pp}{tail}.'
                neg = f'{subj} {pp}{tail}. {subj} has {pp}{tail}. What is {base}ing?'
            elif be == 'are':
                s2 = {'The accident': 'The accidents', 'An error': 'Some errors', 'The parcel': 'The parcels',
                      'A message': 'Two messages', 'My wallet': 'My keys', 'The plant': 'The plants',
                      'The money': 'The savings', 'A new problem': 'New problems'}[subj]
                pos = f'{s2} are {pp}{tail}.'
                exp = f'{s2} {pp}{tail}.' if simple else f'{s2} have {pp}{tail}.'
                neg = f'{s2} have {pp}{tail}. {s2} {pp}{tail}. Why are they {base}ing?'
            else:
                pos, exp = f'I am {pp}{tail}.', f'I have {pp}{tail}.'
                neg = f'I have {pp}{tail}. I {pp}{tail}. Am I {base}ing?'
            if base == 'arrive' and be == 'is':
                neg += ' The conclusion is arrived at by logic.'
            R(f'intransitive.{be}_{pp}', pat, rep, 'Verb form', 0.9,
              f'“{base.capitalize()}” cannot be passive; say “{rep}”.',
              pos, exp, neg)
    for base, pp, subj, tail in PERFECT[:3] + PERFECT[4:5]:
        pat = r'(?i)\b(?P<target>(?:got|get|gets|getting) )' + pp + r'\b'
        R(f'intransitive.got_{pp}', pat, '', 'Verb form', 0.9,
          f'“{base.capitalize()}” cannot be passive; drop “got”.',
          f'{subj} got {pp}{tail}.', f'{subj} {pp}{tail}.',
          f'{subj} {pp}{tail}. {subj} has {pp}{tail}. We got there early.')
    # will be happened -> will happen ("to be arrived at" is a real passive, so arrive is left out)
    for base, pp, subj, tail in [x for x in PERFECT if x[0] != 'arrive'] + [('exist', 'existed', 'This problem', ' in older versions')]:
        pat = r'(?i)\b(?:will|would|can|could|may|might|should|must|shall|to) (?P<target>be ' + pp + r')\b'
        R(f'intransitive.be_{pp}_modal', pat, base, 'Verb form', 0.92,
          f'“{base.capitalize()}” cannot be passive; after a modal use “{base}”.',
          f'{subj} will be {pp}{tail}.', f'{subj} will {base}{tail}.',
          f'{subj} will {base}{tail}. {subj} may have {pp}{tail}. We will be there.')


def build_exist_belong():
    for be, rep, exp_s, s_in in (('is', 'exists', 'This option exists in the menu.', 'This option is existed in the menu.'),
                                 ('are', 'exist', 'These options exist in the menu.', 'These options are existed in the menu.')):
        pat = r'(?i)\b(?P<target>' + be + r' existed)\b'
        R(f'intransitive.{be}_existed', pat, rep, 'Verb form', 0.9,
          '“Exist” cannot be passive; say “' + rep + '”.', s_in, exp_s,
          exp_s + ' This option existed before.')
    for be, rep, s_in, exp_s in (('is', 'belongs', 'This phone is belonged to my sister.', 'This phone belongs to my sister.'),
                                 ('are', 'belong', 'These keys are belonged to my sister.', 'These keys belong to my sister.')):
        pat = r'(?i)\b(?P<target>' + be + r' belonged) to\b'
        R(f'intransitive.{be}_belonged', pat, rep, 'Verb form', 0.9,
          '“Belong” cannot be passive; say “' + rep + ' to”.', s_in, exp_s,
          exp_s + ' This phone belonged to her.')
    pat = r'(?i)\b(?P<target>(?:was|were|been) )belonged to\b'
    R('intransitive.was_belonged', pat, '', 'Verb form', 0.9,
      '“Belong” cannot be passive; say “belonged to”.',
      'The house was belonged to my uncle.', 'The house belonged to my uncle.',
      'The house belonged to my uncle. The house has belonged to us.')
    pat = r'(?i)\b(?P<target>(?:was|were) )disappeared(?:\s*[.,;:!?)]|\s*$|\s+(?:from|in|on|at|after|before|yesterday|today|last|suddenly|again|completely|without|when|because|and|but)\b)'
    R('intransitive.was_disappeared', pat, '', 'Verb form', 0.88,
      '“Disappear” cannot be passive; say “disappeared”.',
      'The file was disappeared yesterday.', 'The file disappeared yesterday.',
      'The file disappeared yesterday. The file has disappeared. He was disappeared by the regime.')
    pat = r'(?i)\b(?P<target>been )disappeared(?:\s*[.,;:!?)]|\s*$|\s+(?:from|in|on|at|after|before|yesterday|today|last|suddenly|again|completely|without|when|because|and|but)\b)'
    R('intransitive.been_disappeared', pat, '', 'Verb form', 0.88,
      '“Disappear” cannot be passive; say “has disappeared”.',
      'My bag has been disappeared from the desk.', 'My bag has disappeared from the desk.',
      'My bag has disappeared from the desk. The man has been disappeared by the army.')


def build():
    build_be_participle()
    build_exist_belong()
