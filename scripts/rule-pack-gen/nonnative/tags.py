"""The invariant tag "isn't it?" after a sentence whose subject is not "it": "You are coming, isn't it?" Each rule
needs the subject first in the sentence and an auxiliary, so the matching tag is known ("aren't you")."""
from lib import R

BODY = {'are': 'coming tomorrow', 'were': 'there yesterday', 'will': 'come tomorrow', 'can': 'join us',
        'have': 'finished the report', 'would': 'like to join', 'is': 'coming tomorrow', 'was': 'there yesterday',
        'has': 'finished the report', 'am': 'coming tomorrow'}
NEG = {'are': "aren't", 'were': "weren't", 'will': "won't", 'can': "can't", 'have': "haven't", 'would': "wouldn't",
       'is': "isn't", 'was': "wasn't", 'has': "hasn't", 'am': "aren't"}


def stem(neg):
    # "aren't" -> "aren${a}t" so a curly apostrophe in the text stays curly
    return neg.replace("'", '${a}')


# A clause with no negative word: no "no", "not" or "n't" (a lone "n" before the comma is fine).
POSITIVE_BODY = r"(?:[^n.,;:!?\n]|n[^ot'’.,;:!?\n]){1,40}n?"


def build():
    combos = []
    for s in ('you', 'we', 'they'):
        for aux in ('are', 'were', 'will', 'can', 'have', 'would'):
            combos.append((s, aux))
    for s in ('he', 'she'):
        for aux in ('is', 'was', 'will', 'can', 'has', 'would'):
            combos.append((s, aux))
    for aux in ('am', 'was', 'will', 'can', 'have', 'would'):
        combos.append(('I', aux))
    for tag in ("isn't it", 'is it'):
        for s, aux in combos:
            flag = '(?im)' if s != 'I' else '(?m)'
            subj = s if s != 'I' else r'(?i:i)'
            if tag == "isn't it":
                target = r"(?P<target>isn(?P<a>['’])t it)"
                stem_ = stem(NEG[aux])
            else:
                target = r'(?P<target>is it)'
                stem_ = NEG[aux]
            pattern = rf"{flag}(?:^|[.!?]\s+){subj} {aux} {POSITIVE_BODY}, {target}\?"
            neg_tag = NEG[aux]
            word = s[0].upper() + s[1:]
            body = BODY[aux]
            wrong = tag
            pos = f"{word} {aux} {body}, {wrong}?"
            exp = f"{word} {aux} {body}, {neg_tag} {s}?"
            negative = (f"{word} {aux} {body}, {neg_tag} {s}? It is nice, {wrong}? {word} {aux} not {body}, {wrong}? "
                        f"{word} {aux} {body}, {wrong} a shame?")
            if tag == 'is it':
                negative = (f"{word} {aux} {body}, {neg_tag} {s}? It is nice, {wrong}? {word} {aux} not {body}, {wrong}? "
                            f"He said {s} {aux} {body}, is it a shame?")
            R(f"tag.{'isnt' if tag != 'is it' else 'isit'}.{s.lower()}.{aux}", pattern, stem_ + ' ' + s, 'Register', 0.75,
              f'The tag must match the sentence: “{word} {aux} …, {neg_tag} {s}?” “{tag[0].upper() + tag[1:]}?” fits only a sentence about “it”.',
              pos, exp, negative)
