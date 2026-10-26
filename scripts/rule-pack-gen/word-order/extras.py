"""Smaller families: "the question is where is he", "haven't still", "has yet not", "I also not like", names after
an embedded "is"."""
from lib import *
from negation import GROUPS

APOS = r'[’\']'


def build_noun_is():
    # "The question is where is he." -> "The question is where he is."
    nouns = ['question', 'problem', 'issue', 'point', 'trouble', 'mystery', 'secret', 'difficulty', 'puzzle', 'doubt']
    for n in nouns:
        pat = subst(r'(?i)\b' + n + r' (?:is|was) <<WHX>>\s+(?P<target>(?P<a>is|are|was|were|will|can|could|should|would|must|has|have) '
                    r'(?P<s>he|she|it|they|we|you|I))\b', WHX=WHX)
        R(f'noun_is_question.{n}', pat, '${s} ${a}', 'Grammar', 0.92,
          'Inside a longer sentence a question keeps statement order: the subject goes before the verb.',
          f'The {n} is where is he.' if n != 'doubt' else 'The doubt is whether can we finish.',
          f'The {n} is where he is.' if n != 'doubt' else 'The doubt is whether we can finish.',
          f'The {n} is where he is. Where is he? The {n} was clear.' if n != 'doubt' else
          'The doubt is whether we can finish. Can we finish?')
    # "Do you know who is Sarah?" -> "who Sarah is" (a name that is the subject)
    for a in ('is', 'was'):
        pat = subst(r'(?im)\b<<ASK>><<OBJ>>\s+<<WHX>>\s+(?P<target>(?P<a>' + a + r') (?P<s>(?-i:[A-Z])[a-z]+))(?:\s*[.,!?)]|\s*$)',
                    ASK=ASK, OBJ=ASKOBJ, WHX=WHX)
        R(f'emb_name.{a}', pat, '${s} ${a}', 'Grammar', 0.9,
          'Inside a longer sentence a question keeps statement order: the subject goes before “' + a + '”.',
          f'Do you know who {a} Sarah?', f'Do you know who Sarah {a}?',
          f'Do you know who Sarah {a}? Who {a} Sarah? I know what {a} Python used for. Tell me what {a} Docker doing.')


def build_adverb_order():
    for aux, ex in (('haven', 'I haven’t still finished the report.'), ('hasn', 'She hasn’t still replied to me.'),
                    ('hadn', 'We hadn’t still decided.')):
        pp = (r'(?:finished|replied|decided|received|started|done|seen|heard|found|read|paid|sent|answered|called|'
              r'completed|signed|checked|talked|spoken|understood|learned|learnt|written|submitted|cleaned|booked)')
        pat = subst(r'(?i)\b(?P<target>(?P<n>' + aux + r'[’\']t) still) <<P>>\b', P=pp)
        exp = ex.replace(f'{aux}’t still', f'still {aux}’t')
        exp = exp.replace('I haven’t still', 'I still haven’t')
        R(f'still_after_negative.{aux}nt', pat, 'still ${n}', 'Grammar', 0.9,
          '“Still” goes before the negative auxiliary: “I still haven’t finished”.',
          ex, exp, exp + f' It {aux}’t been long. We are still waiting.')
    pat = subst(r'(?i)\b(?P<target>(?P<h>have|has|had) yet not)\b')
    R('yet_not', pat, '${h} not yet', 'Grammar', 0.9,
      '“Not yet” keeps its order: “has not yet arrived”.',
      'The parcel has yet not arrived.', 'The parcel has not yet arrived.',
      'The parcel has not yet arrived. The best has yet to come. We have yet another plan.')
    allv = sorted({v for vs in GROUPS.values() for v in vs})
    alt = '|'.join(allv)
    pat = subst(r'(?i)<<CS>>(?:I|we|you|they) also (?P<target>not) (?:' + alt + r')\b', CS=CS)
    R('also_not_do', pat, 'do not', 'Grammar', 0.9,
      'To make a verb negative, use “do not”: “I also do not like it”.',
      'I also not like spicy food.', 'I also do not like spicy food.',
      'I also do not like spicy food. I also like it. I also, not you, know.')
    pat = subst(r'(?i)<<CS>>(?:he|she|it) also (?P<target>not) (?:' + alt + r')\b', CS=CS)
    R('also_not_does', pat, 'does not', 'Grammar', 0.9,
      'To make a verb negative, use “does not”: “She also does not like it”.',
      'She also not like spicy food.', 'She also does not like spicy food.',
      'She also does not like spicy food. She also likes it. She also said no.')


def build():
    build_noun_is()
    build_adverb_order()
