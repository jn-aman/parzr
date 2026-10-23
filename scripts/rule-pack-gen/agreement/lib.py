"""Helpers for the agreement pack generator."""
import json, re

RULES = []
IDS = set()
PROV = 'parzr original rule (agreement pack)'

# Clause-start contexts. A bare-verb or "was/were" subject is only judged where it is surely the subject of a
# finite clause: sentence start, after a comma, after a conjunction, or after a verb of thinking/knowing.
# "that" is left out on purpose (mandative subjunctive: "I insist that he go"), and so are "let/make/help/see".
# "and"/"or"/"nor" are left out of CL: after them the pronoun may belong to a compound subject
# ("Mike and she go", "Mike, Anna, and she go"), where the plural verb is right. CL_PL (for the plural direction,
# where the fix to the plural form is right either way) keeps them.
CONJ = ('but|so|because|since|when|while|although|though|if|whereas|then|until|before|after|once|unless|'
        'whenever|yet')
COG = ('think|thinks|believe|believes|know|knows|guess|hope|hopes|doubt|reckon|realize|realise|understand|'
       'wonder|means|mean|expect|expects')
END = r'[.!?]["”’)]*'
CL = (r'(?:^|' + END + r'\s+|[:;]\s+|,\s+(?:(?:but|so|yet)\s+)?|\b(?:' + CONJ + '|' + COG + r')\s+)')
CL_PL = (r'(?:^|' + END + r'\s+|[:;]\s+|,\s+(?:(?:and|but|so|or|yet|then)\s+)?|\b(?:and|or|' + CONJ + '|' + COG + r')\s+)')
# For "it": the objecty verbs go too ("People who believe it don't care": "it" is the object of "believe").
COG_IT = 'think|thinks|guess|hope|hopes|reckon|wonder'
CL_IT = (r'(?:^|' + END + r'\s+|[:;]\s+|,\s+(?:(?:but|so|yet)\s+)?|\b(?:' + CONJ + '|' + COG_IT + r')\s+)')
# he / she / it with their clause contexts
SGP = CL_IT + r'(?:he|she|(?-i:[Ii]t))'
SGP_HS = CL_IT + r'(?:he|she)'
# finite-only forms ("he are", "she don't"): "that" is fine too, there is no subjunctive of these
CLF = (r'(?:^|' + END + r'\s+|[:;]\s+|,\s+(?:(?:but|so|yet)\s+)?|\b(?:' + CONJ + '|' + COG + r'|that)\s+)')
CLF_IT = (r'(?:^|' + END + r'\s+|[:;]\s+|,\s+(?:(?:but|so|yet)\s+)?|\b(?:' + CONJ + '|' + COG_IT + r'|that)\s+)')
SGP_F = CLF_IT + r'(?:he|she|(?-i:[Ii]t))'
# the same without the conjunctions that can open a subjunctive or an inversion
CL_STRICT = (r'(?:^|' + END + r'\s+|,\s+(?:(?:and|but|so)\s+)?|\b(?:and|but|so|because|since|when|while|'
             r'although|though|whereas|then|until|after|once|unless|whenever)\s+)')
# For a common noun as the subject the prepositions "after / before / since / until / once / as / than" and the
# conjunctions "and / or" are left out: "since children", "as a musician", "between A and the kids ..." are phrases
# whose head noun is not the subject.
CONJ_N = 'but|so|because|when|while|although|though|if|whereas|unless|whenever'
CL_N = (r'(?:^|' + END + r'\s+|[:;]\s+|,\s+(?:(?:but|so|yet)\s+)?|\b(?:' + CONJ_N + '|' + COG + r')\s+)')
CLN = (r'(?:^|' + END + r'\s+|[:;]\s+|,\s+(?:(?:but|so)\s+)?|\b(?:' + CONJ_N + '|' + COG +
       r'|that|whether|how|what|why|where|which)\s+)')
CLN_SG = CLN
WERE_N = r'(?:^|' + END + r'\s+|\b(?:because|when)\s+)'
SS = r'(?:^|' + END + r'\s+)'                  # sentence start only
WH = r'(?:what|where|when|why|how|whenever|wherever)'
SQ = (r'(?:^|' + END + r'\s+|\b' + WH + r'\s+)')   # start of a question

IT = r'(?-i:[Ii]t)'
CAP_I = r'(?-i:I)'

def alt(words):
    ws = sorted(set(words), key=lambda w: (-len(w), w))
    return '(?:' + '|'.join(ws) + ')'

def ci(words):
    """case-sensitive (lower case) group: app names like Files or Messages stay out"""
    ws = sorted(set(words), key=lambda w: (-len(w), w))
    return '(?-i:' + '|'.join(ws) + ')'

def q(s):
    return '“' + s + '”'

def add(rid, pattern, repl, cat, conf, reason, pos, neg, prov=PROV):
    assert rid not in IDS, rid
    IDS.add(rid)
    RULES.append(dict(id=rid, pattern=pattern, replacement=repl, category=cat, confidence=conf,
                      reason=reason, provenance=prov, positive=pos, negative=neg))

def fixed(rule, text):
    """the text after applying one rule once (Python re; ${x} expanded)"""
    rx = re.compile(rule['pattern'])
    m = rx.search(text)
    if not m:
        return text
    rep = re.sub(r'\$\{(\w+)\}', lambda g: m.group(g.group(1)) or '', rule['replacement'])
    t = m.group('target')
    # mimic match_case
    if t and t[0].isupper() and rep:
        rep = rep[0].upper() + rep[1:]
    return text[:m.start('target')] + rep + text[m.end('target'):]

def dump(path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(RULES, f, ensure_ascii=False, indent=2)
        f.write('\n')
