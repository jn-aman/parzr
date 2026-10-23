"""Irregular-verb families: perfect + past form, passive + past form, participle as past, did + past,
to + past, have + base (with a perfect cue), overregularized forms, modal + past."""
import json, os
from core import *
from verbs import ALL_ROWS, STRONG_ROWS, SAME_ROWS
from regular import REG_ROWS

G = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data') + '/'
COV = json.load(open(G + 'coverage.json'))
DROPPED = json.load(open(G + 'dropped.json')) if os.path.exists(G + 'dropped.json') else {}


def covered(fam, base):
    return base in COV.get(fam, []) or base in DROPPED.get(fam, [])


NAME_CLASH = {'drew', 'rose', 'ran', 'sang', 'rode', 'wore', 'bore'}


def lower_only(w):
    return f'(?-i:{w})' if w in NAME_CLASH else w


def tails(v, extra=()):
    return [v['tail'], *extra, 'the work', 'to the market', 'home early', 'again', 'the story']


# ---------------------------------------------------------------------------------------------------------------
# V2 forms that are also real words after the auxiliary, so the rule needs a verb-ish follower
P_FOLLOW = {
    'saw': r"(?:the|a|an|it|them|him|her|that|this|these|those|my|your|his|our|their|me|us|you|what|how|who|any|many|"
           r"some|all|enough|everything|nothing|something|anything|anyone|everyone|someone|nobody)",
    'bit': r"(?:me|him|her|them|us|my|his|the|into|off|down|through|a|an|its|our|your|their|by)",
    'rose': r"(?:to|from|above|up|again|sharply|rapidly|steadily|by|over|through|beyond|early|before|against)",
}
P_TAIL = {'saw': 'the movie', 'bit': 'the apple', 'rose': 'to the top'}
P_SKIP = {'lie', 'hide', 'show', 'sew', 'wake', 'tread', 'strive', 'forget', 'weave', 'bite'}   # variant participles are accepted


def perfect_past():
    """has went / would have saw / Have you ever ate / Had I knew  ->  past participle."""
    for v in STRONG_ROWS:
        b, v2, v3 = v['base'], v['past'], v['part']
        if v2 == v3 or b in P_SKIP or b in DROPPED.get('P', []):
            continue
        follow = P_FOLLOW.get(v2)
        pat = (rf"(?i)\b{PERFECT}(?:{SP_SUBJ}{SP_ADV2}| {NP}) (?P<target>{lower_only(v2)})"
               + (rf" {follow}\b" if follow else END))
        tail = P_TAIL.get(v2, v['tail'])
        neg = f"She has {v3} {tail}. Anna {v2} {tail}. Have you {v3} {tail}?"
        if v2 == 'saw':
            neg += " We have saw blades in the shed."
        rule(f"tense.perfect_past.{b}", pat, v3,
             f"After “have”, “has” or “had” the verb takes its past participle: {Q(v3)}, not {Q(v2)}.",
             f"She has {v2} {tail}.", neg, right=f"She has {v3} {tail}.", confidence=0.97,
             more_pos=[(f"Have you ever {v2} {tail}?", f"Have you ever {v3} {tail}?"),
                       (f"They would have {v2} {tail} earlier.", f"They would have {v3} {tail} earlier."),
                       (f"He hasn't {v2} {tail} yet.", f"He hasn't {v3} {tail} yet."),
                       (f"We've already {v2} {tail}.", f"We've already {v3} {tail}.")])


# ---------------------------------------------------------------------------------------------------------------
PS_SKIP = {'wake', 'break', 'shake', 'freeze', 'hide', 'lie', 'come', 'become', 'go', 'run', 'begin', 'fall', 'fly',
           'rise', 'swim', 'spring', 'arise', 'partake', 'overeat', 'tread', 'strive', 'overcome', 'see', 'bite',
           'draw', 'eat', 'drive', 'lay', 'show', 'sew', 'weave', 'forget'}
PS_FOLLOW = (r"(?:by|away|from|in|on|at|out|off|over|down|up|apart|into|for|back|aside|place|part|care|"
             r"seriously|lightly|ill|sick|advantage|with|to)")
PS_ADV = r"(?: (?:not|never|also|already|just|still|finally|recently|always|even|really|only|then|now|quickly|often))?"


def passive_past():
    """It was wrote by him -> It was written by him (only verbs the engine's own passive check misses)."""
    for v in ALL_ROWS:
        b, v2, v3 = v['base'], v['past'], v['part']
        if v2 == v3 or v['kind'] == 'I' or b in PS_SKIP or covered('PS', b):
            continue
        pat = rf"(?i)\b{BE_AUX}{PS_ADV} (?P<target>{lower_only(v2)})(?:{END}| {PS_FOLLOW}\b)"
        neg = f"It was {v3} by the manager. Anna {v2} it. Anna {v2} {v['tail']}."
        rule(f"tense.passive_past.{b}", pat, v3,
             f"A passive takes the past participle: {Q(v3)}, not {Q(v2)}.",
             f"It was {v2} by the manager.", neg, right=f"It was {v3} by the manager.", confidence=0.96,
             more_pos=[(f"The deal has been {v2} away.", f"The deal has been {v3} away."),
                       (f"It is being {v2}.", f"It is being {v3}.")])


# ---------------------------------------------------------------------------------------------------------------
S_SKIP = {'come', 'run', 'become', 'overcome', 'do', 'see', 'lie', 'mistake', 'show', 'hide', 'sew',
          'sink', 'shrink', 'sing', 'ring', 'drink', 'swim', 'spring'}   # "sunk", "sung", "rung", "drunk" ... are accepted pasts
# participles that read as adjectives, so only an object may follow
S_ADJ = {'wear', 'break', 'tear', 'freeze', 'grow', 'shrink', 'drink', 'weave', 'forbid', 'swear', 'steal', 'sink',
         'overdo', 'undo', 'foresee', 'oversee', 'forsake', 'know', 'give', 'draw', 'drive', 'choose', 'eat'}
S_INTRANS = {'go', 'fall', 'rise', 'fly', 'swim', 'spring', 'arise', 'partake', 'tread', 'overeat', 'strive'}
S_ADV = r"(?: (?:also|then|just|already|finally|recently|never|once|later|quickly|actually|really)){0,1}"


def participle_as_past():
    """I gone to the shop -> I went to the shop."""
    for v in STRONG_ROWS:
        b, v2, v3 = v['base'], v['past'], v['part']
        if v2 == v3 or b in S_SKIP:
            continue
        if b in S_INTRANS:
            follow = PARTS
        elif b in S_ADJ:
            follow = DETOBJ
        else:
            follow = rf"(?:{DETOBJ[3:-1]}|{PARTS[3:-1]})"
        subj = r"(?:I|we|they|he|she)" if b == 'give' else r"(?:I|we|you|they|he|she)"
        pat = rf"(?im){STARTS}{subj}{S_ADV} (?P<target>{v3}) {follow}\b"
        sel = pick(pat, [(f"I {v3} {t}.", f"I {v2} {t}.") for t in tails(v, ('up the plan',))])
        if sel is None:
            PROBLEMS.append(f"participle_as_past.{b}: no example"); continue
        pos, right = sel
        tail = pos[len(f"I {v3} "):-1]
        neg = f"I {v2} {tail}. Have you {v3} {tail}? I have {v3} {tail}. Having {v3} {tail}, I left."
        rule(f"tense.participle_as_past.{b}", pat, v2,
             f"Without “have”, the simple past is {Q(v2)}, not {Q(v3)}.",
             pos, neg, right=right, confidence=0.95,
             more_pos=[(f"We tried it and he {v3} {tail}.", f"We tried it and he {v2} {tail}.")])


# ---------------------------------------------------------------------------------------------------------------
D_SKIP = {'lay', 'find', 'bind', 'wind', 'grind', 'lie', 'bear', 'sew'}
D_FOLLOW = {
    'saw': r"(?:him|her|them|me|us|anyone|anybody|anything|something|everything|nothing|that|this|those|these|"
           r"the (?:email|message|news|video|post|game|movie|film|show|report|picture|photo|link|file|result|results|"
           r"sign|memo|notice|point|difference))",
    'fell': r"(?:off|down|asleep|in|into|on|from|ill|sick|over|apart|behind|for|out|short|flat|silent)",
}
D_TAIL = {'saw': 'him', 'fell': 'off the ladder'}
D_NEG = (r"\b(?:didn['’]t|did not|didnt|don['’]t|doesn['’]t|do not|does not)(?: (?:you|he|she|it|we|they|I|even|also|really|ever|just|still|actually|quite|"
         r"always|never)){0,2}")
D_Q = (rf"(?:^|[.!?] |\b(?:why|what|when|where|how|who|whom|which|and|but|so|or) )(?:did|does|do)(?: {PRON}"
       r"(?: (?:ever|also|really|just|still|actually|already|even))?| " + NP + ")")


def did_past():
    """She didn't went / Did you saw  ->  base form."""
    rows = list(ALL_ROWS) + [dict(base='show', third='shows', past='showed', part='shown', ing='showing',
                                  tail='the results', kind='T', flags=set())]
    for v in rows:
        b, v2, v3 = v['base'], v['past'], v['part']
        if v2 == b or b in D_SKIP or covered('D', b):
            continue
        follow = D_FOLLOW.get(v2)
        tail = D_TAIL.get(v2, v['tail'])
        tailre = rf" {follow}\b" if follow else END
        pat = rf"(?im)(?:{D_NEG}|{D_Q}) (?P<target>{lower_only(v2)}){tailre}"
        neg = f"Did you {b} {tail}? She didn't {b} {tail}. Anna {v2} {tail}."
        rule(f"tense.did_past.{b}", pat, b,
             f"After “did”, “do” or “does” (and their negatives) the verb stays in its base form: {Q(b)}, not {Q(v2)}.",
             f"She didn't {v2} {tail}.", neg, right=f"She didn't {b} {tail}.", confidence=0.97,
             more_pos=[(f"Did you {v2} {tail}?", f"Did you {b} {tail}?"),
                       (f"They did not {v2} {tail}.", f"They did not {b} {tail}."),
                       (f"Why didn't he {v2} {tail}?", f"Why didn't he {b} {tail}?"),
                       (f"What did she {v2} {tail}?", f"What did she {b} {tail}?")])


# ---------------------------------------------------------------------------------------------------------------
T_SKIP = {'lay', 'find', 'bind', 'wind', 'grind', 'lie', 'bear', 'bite', 'see', 'fall', 'rise', 'leave', 'shoot',
          'say', 'hold', 'lead', 'show', 'draw', 'feel', 'stick', 'sit', 'sew', 'think', 'win', 'bend'}
T_ADV = r"(?: (?:not|never|also|even|really|just|still|always|all))?"


def to_past():
    """He wants to went -> He wants to go;  Let's went -> Let's go."""
    for v in ALL_ROWS:
        b, v2, v3 = v['base'], v['past'], v['part']
        if v2 == b or b in T_SKIP or covered('T', b):
            continue
        pat = (rf"(?i)\b(?:to|let['’]s|let (?:me|us|him|her|them|you|it)){T_ADV} (?P<target>{lower_only(v2)}){END}")
        tail = v['tail']
        neg = f"He wants to {b} {tail}. Anna {v2} {tail}. She gave it to Anna."
        rule(f"tense.to_past.{b}", pat, b,
             f"After “to” the verb takes its base form: {Q(b)}, not {Q(v2)}.",
             f"He wants to {v2} {tail}.", neg, right=f"He wants to {b} {tail}.", confidence=0.96,
             more_pos=[(f"Let's {v2} {tail} now.", f"Let's {b} {tail} now."),
                       (f"She forgot not to {v2} {tail}.", f"She forgot not to {b} {tail}.")])


# ---------------------------------------------------------------------------------------------------------------
NOUNY = {'fall', 'sink', 'spring', 'swing', 'ring', 'rise', 'wake', 'tear', 'blow', 'bite', 'deal', 'sleep', 'slide',
         'spin', 'stick', 'sting', 'strike', 'hold', 'lead', 'bend', 'bind', 'creep', 'fling', 'grind', 'hang',
         'stand', 'think', 'say', 'win', 'wind', 'feel', 'find', 'keep', 'make', 'dig', 'feed', 'fight', 'mean',
         'pay', 'break', 'drive', 'draw', 'drink', 'fly', 'grow', 'run', 'show', 'swim', 'take', 'throw', 'wear',
         'go', 'give', 'know', 'ride', 'speak', 'bleed', 'breed', 'sit', 'seek', 'teach', 'tell', 'weave', 'wring',
         'overthrow', 'overtake', 'overdo', 'undo', 'redo', 'rewrite', 'retake', 'forbid', 'forget',
         'freeze', 'hide', 'swear', 'steal', 'shake', 'shrink', 'sing', 'write', 'eat', 'do', 'see', 'sweep',
         'lend', 'lose', 'meet', 'build', 'buy', 'catch', 'hear', 'send', 'spend', 'shoot', 'cling', 'kneel',
         'mistake', 'override', 'withdraw', 'oversee', 'foresee', 'outgrow', 'leave', 'shine'}
VERBY = rf"(?:{DETOBJ[3:-1]}|again|twice|there|here|abroad|home|away)"
PB_PLAIN = {'arise', 'undergo', 'undertake', 'forsake', 'slay', 'overeat', 'partake', 'mislead', 'misunderstand',
            'rebuild', 'repay', 'retell', 'rethink', 'foretell', 'uphold', 'withhold', 'overhear', 'forgive',
            'bring', 'flee', 'understand', 'begin', 'choose', 'tread', 'strive'}
PB_SKIP = {'lie', 'come', 'run', 'become', 'overcome', 'shine', 'lay', 'hang', 'wind', 'hide', 'show', 'leave', 'find',
           'sew', 'bind', 'grind'}
CUE = r"(?:already|just|never|ever|yet|recently|finally|lately|previously|once|twice|not)"


def pb_pattern(base, plain):
    return (rf"(?i)\b{PERFECT_NOD}{SP_SUBJ} {CUE}(?: {CUE})? (?P<target>{base})"
            + (END if plain else rf" {VERBY}\b"))


def have_base():
    """I have already go -> I have already gone (a perfect cue between 'have' and the bare verb)."""
    for v in ALL_ROWS:
        b, v2, v3 = v['base'], v['past'], v['part']
        if v3 == b or b in PB_SKIP or covered('PB', b):
            continue
        plain = b in PB_PLAIN
        pat = pb_pattern(b, plain)
        sel = pick(pat, [(f"I have already {b} {t}.", f"I have already {v3} {t}.")
                         for t in tails(v, ('twice',))])
        if sel is None:
            PROBLEMS.append(f"{b}: no PB example"); continue
        pos, right = sel
        tail = pos[len(f"I have already {b} "):-1]
        neg = f"I have already {v3} {tail}. We will {b} {tail}. We had better {b} {tail}."
        rule(f"tense.have_base.{b}", pat, v3,
             f"After “have” and an adverb like “already” the verb takes its past participle: {Q(v3)}, not {Q(b)}.",
             pos, neg, right=right, confidence=0.95,
             more_pos=[(f"She has never {b} {tail}.", f"She has never {v3} {tail}.")])


def regular_have_base():
    """I have already finish -> I have already finished (regular verbs)."""
    for v in REG_ROWS:
        b, p = v['base'], v['part']
        if covered('PBR', b):
            continue
        pat = pb_pattern(b, not v['noun'])
        t = 'the report' if v['noun'] else 'my work'
        rule(f"tense.have_base_reg.{b}", pat, p,
             f"After “have” and an adverb like “already” the verb takes its past participle: {Q(p)}, not {Q(b)}.",
             f"I have already {b} {t}.", f"I have already {p} {t}. We will {b} {t} soon. We had better {b} {t} now.",
             right=f"I have already {p} {t}.", confidence=0.95,
             more_pos=[(f"She has never {b} {t}.", f"She has never {p} {t}.")])


# ---------------------------------------------------------------------------------------------------------------
NONWORD = ['arise', 'bite', 'blow', 'forbid', 'hide', 'mistake', 'overcome', 'override', 'shrink', 'sink', 'spring',
           'undergo', 'undertake', 'undo', 'withdraw', 'overtake', 'rewrite', 'redo', 'outgrow', 'foresee', 'retake',
           'partake', 'forsake', 'overdo', 'overeat', 'overthrow', 'bleed', 'breed', 'cling', 'deal', 'fling',
           'mean', 'shoot', 'slide', 'stick', 'sting', 'strike', 'swing', 'wring', 'withhold', 'uphold', 'mislead',
           'misunderstand', 'rebuild', 'rethink', 'bind']
OR_FORM = {'arise': 'arised', 'bite': 'bited', 'blow': 'blowed', 'forbid': 'forbided', 'hide': 'hided',
           'mistake': 'mistaked', 'overcome': 'overcomed', 'override': 'overrided', 'shrink': 'shrinked',
           'sink': 'sinked', 'spring': 'springed', 'undergo': 'undergoed', 'undertake': 'undertaked',
           'undo': 'undoed', 'withdraw': 'withdrawed', 'overtake': 'overtaked', 'rewrite': 'rewrited',
           'redo': 'redoed', 'outgrow': 'outgrowed', 'foresee': 'foreseed', 'retake': 'retaked',
           'partake': 'partaked', 'forsake': 'forsaked', 'overdo': 'overdoed', 'overeat': 'overeated',
           'overthrow': 'overthrowed', 'bleed': 'bleeded', 'breed': 'breeded', 'cling': 'clinged', 'deal': 'dealed',
           'fling': 'flinged', 'mean': 'meaned', 'shoot': 'shooted', 'slide': 'slided', 'stick': 'sticked',
           'sting': 'stinged', 'strike': 'striked', 'swing': 'swinged', 'wring': 'wringed', 'withhold': 'withholded',
           'uphold': 'upholded', 'mislead': 'misleaded', 'misunderstand': 'misunderstanded',
           'rebuild': 'rebuilded', 'rethink': 'rethinked', 'bind': 'binded'}
OR_SKIP = {'bind', 'retake'}      # the engine's own participle check turns "bound"/"retaken" into "bounded"/"retakened"
OR_ADVW = "also|then|just|already|finally|never|always|really|suddenly|quickly|quietly|again|even|only|once|soon|later|actually"
OR_PERF = r"(?:have|has|had|having|haven['’]t|hasn['’]t|hadn['’]t|['’]ve|['’]d|was|were|is|are|am|been|being|be)"
OR_BASE = (r"(?:did|didn['’]t|don['’]t|doesn['’]t|to|will|would|can|could|should|might|must|may|won['’]t|can['’]t|"
           r"couldn['’]t|wouldn['’]t|shouldn['’]t|let['’]s)")


def regularized():
    """buyed / swinged: an irregular verb given a regular ending, by the form it should take."""
    rows = {v['base']: v for v in ALL_ROWS}
    adv = rf"(?: (?:{OR_ADVW}))?"
    for b in NONWORD:
        if b in OR_SKIP:
            continue
        v = rows[b]
        f = OR_FORM[b]
        v2, v3, tail = v['past'], v['part'], v['tail']
        past = rf"(?i)\b(?:I|we|you|they|he|she|it){adv} (?P<target>{f}){END}"
        part = rf"(?i)\b{OR_PERF}{adv} (?P<target>{f}){END}"
        base = rf"(?i)\b{OR_BASE}{adv} (?P<target>{f}){END}"
        if v2 == v3:
            both = rf"(?i)\b(?:I|we|you|they|he|she|it|{OR_PERF}){adv} (?P<target>{f}){END}"
            rule(f"tense.regularized.past.{b}", both, v2,
                 f"{Q(f)} is not a word: the past of {Q(b)} is {Q(v2)}.",
                 f"He {f} {tail} before.", f"Anna {v2} {tail}. It has {v3} {tail}.",
                 right=f"He {v2} {tail} before.", confidence=0.95,
                 more_pos=[(f"It has {f} {tail}.", f"It has {v3} {tail}.")])
        else:
            rule(f"tense.regularized.past.{b}", past, v2,
                 f"{Q(f)} is not a word: the past of {Q(b)} is {Q(v2)}.",
                 f"He {f} {tail} before.", f"Anna {v2} {tail}. It has {v3} {tail}.",
                 right=f"He {v2} {tail} before.", confidence=0.95)
            rule(f"tense.regularized.part.{b}", part, v3,
                 f"{Q(f)} is not a word: the past participle of {Q(b)} is {Q(v3)}.",
                 f"It has {f} {tail}.", f"Anna {v2} {tail}. It has {v3} {tail}.",
                 right=f"It has {v3} {tail}.", confidence=0.95)
        rule(f"tense.regularized.base.{b}", base, b,
             f"{Q(f)} is not a word: after “did”, “to” or a modal the verb is {Q(b)}.",
             f"She didn't {f} {tail}.", f"She didn't {b} {tail}. Anna {v2} {tail}.",
             right=f"She didn't {b} {tail}.", confidence=0.95,
             more_pos=[(f"He wants to {f} {tail}.", f"He wants to {b} {tail}.")])


# ---------------------------------------------------------------------------------------------------------------
MP_SKIP = {'lay', 'find', 'bind', 'wind', 'grind', 'lie', 'see', 'bear', 'show', 'sew'}


def modal_past():
    """I will went -> I will go (verbs the engine's modal check misses)."""
    for v in ALL_ROWS:
        b, v2, v3 = v['base'], v['past'], v['part']
        if v2 == b or b in MP_SKIP or covered('MP', b):
            continue
        if v2 in ('fell', 'saw', 'bit', 'rose', 'bore'):
            continue
        pat = (rf"(?i)\b(?:I|we|you|they|he|she|it|who) (?:{MODAL}|{MODAL_NEG})"
               rf"(?: (?:not|never|also|always|still|just|really|even))? (?P<target>{lower_only(v2)}){END}")
        tail = v['tail']
        rule(f"tense.modal_past.{b}", pat, b,
             f"After a modal like “will” or “can” the verb takes its base form: {Q(b)}, not {Q(v2)}.",
             f"I will {v2} {tail}.", f"I will {b} {tail}. Anna {v2} {tail}.",
             right=f"I will {b} {tail}.", confidence=0.97,
             more_pos=[(f"She can't {v2} {tail}.", f"She can't {b} {tail}."),
                       (f"You should not {v2} {tail}.", f"You should not {b} {tail}.")])
