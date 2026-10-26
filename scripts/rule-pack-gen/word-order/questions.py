"""Direct questions without inversion or do-support, and the question idioms that learners reorder."""
from lib import *

# (base, third person, past or None, wh word, tail after the verb, pronoun for the 3sg rule, pronoun for the past rule)
VERBS = [
    ('work', 'works', 'worked', 'where', '', 'he', 'she'),
    ('live', 'lives', 'lived', 'where', '', 'she', 'they'),
    ('want', 'wants', 'wanted', 'what', '', 'he', 'we'),
    ('need', 'needs', 'needed', 'what', '', 'she', 'I'),
    ('like', 'likes', 'liked', 'what', '', 'he', 'you'),
    ('love', 'loves', 'loved', 'who', '', 'she', 'he'),
    ('know', 'knows', 'knew', 'how', ' my name', 'he', 'she'),
    ('think', 'thinks', 'thought', 'what', ' about it', 'she', 'they'),
    ('mean', 'means', 'meant', 'what', '', 'he', 'you'),
    ('say', 'says', 'said', 'what', '', 'he', 'they'),
    ('make', 'makes', 'made', 'what', '', 'she', 'they'),
    ('take', 'takes', 'took', 'how long', ' to finish', 'it', 'you'),
    ('go', 'goes', 'went', 'where', '', 'he', 'they'),
    ('come', 'comes', 'came', 'when', ' home', 'he', 'she'),
    ('get', 'gets', 'got', 'where', ' the money', 'she', 'he'),
    ('give', 'gives', 'gave', 'why', ' you that', 'he', 'she'),
    ('see', 'sees', 'saw', 'what', ' there', 'she', 'you'),
    ('look', 'looks', 'looked', 'how', '', 'it', 'she'),
    ('feel', 'feels', 'felt', 'how', '', 'she', 'you'),
    ('sound', 'sounds', 'sounded', 'how', '', 'it', 'it'),
    ('seem', 'seems', 'seemed', 'how', '', 'it', 'it'),
    ('start', 'starts', 'started', 'when', '', 'it', 'they'),
    ('begin', 'begins', 'began', 'when', '', 'it', 'they'),
    ('end', 'ends', 'ended', 'when', '', 'it', 'they'),
    ('open', 'opens', 'opened', 'when', '', 'it', 'she'),
    ('close', 'closes', 'closed', 'when', '', 'it', 'he'),
    ('call', 'calls', 'called', 'who', ' every day', 'he', 'you'),
    ('tell', 'tells', 'told', 'who', ' that', 'she', 'he'),
    ('ask', 'asks', 'asked', 'who', '', 'he', 'you'),
    ('help', 'helps', 'helped', 'how', ' you', 'she', 'he'),
    ('play', 'plays', 'played', 'where', '', 'he', 'they'),
    ('run', 'runs', 'ran', 'where', '', 'he', 'they'),
    ('leave', 'leaves', 'left', 'when', '', 'he', 'they'),
    ('stay', 'stays', 'stayed', 'where', '', 'he', 'you'),
    ('study', 'studies', 'studied', 'where', '', 'she', 'he'),
    ('speak', 'speaks', 'spoke', 'why', ' so loudly', 'he', 'she'),
    ('drive', 'drives', 'drove', 'where', '', 'he', 'she'),
    ('teach', 'teaches', 'taught', 'what', ' you', 'she', 'he'),
    ('eat', 'eats', 'ate', 'what', '', 'he', 'you'),
    ('drink', 'drinks', 'drank', 'what', '', 'she', 'he'),
    ('sleep', 'sleeps', 'slept', 'where', '', 'he', 'you'),
    ('write', 'writes', 'wrote', 'why', ' that', 'he', 'she'),
    ('buy', 'buys', 'bought', 'where', ' it', 'she', 'you'),
    ('sell', 'sells', 'sold', 'what', '', 'he', 'they'),
    ('pay', 'pays', 'paid', 'how much', '', 'she', 'you'),
    ('wait', 'waits', 'waited', 'why', '', 'he', 'they'),
    ('stop', 'stops', 'stopped', 'why', '', 'he', 'they'),
    ('finish', 'finishes', 'finished', 'when', '', 'he', 'they'),
    ('change', 'changes', 'changed', 'why', '', 'he', 'she'),
    ('use', 'uses', None, 'how', ' it', 'she', None),
    ('try', 'tries', 'tried', 'why', '', 'he', 'they'),
    ('move', 'moves', 'moved', 'why', '', 'he', 'they'),
    ('meet', 'meets', 'met', 'where', ' him', 'she', 'you'),
    ('visit', 'visits', 'visited', 'when', ' us', 'he', 'they'),
    ('send', 'sends', 'sent', 'why', ' it', 'she', 'you'),
    ('show', 'shows', 'showed', 'how', ' it', 'he', 'she'),
    ('bring', 'brings', 'brought', 'what', '', 'she', 'he'),
    ('keep', 'keeps', 'kept', 'where', ' it', 'he', 'you'),
    ('hold', 'holds', 'held', 'where', ' it', 'she', 'they'),
    ('check', 'checks', 'checked', 'how often', ' it', 'he', 'they'),
    ('arrive', 'arrives', 'arrived', 'when', '', 'he', 'they'),
    ('return', 'returns', 'returned', 'when', '', 'she', 'they'),
    ('require', 'requires', 'required', 'what', '', 'it', 'it'),
    ('believe', 'believes', 'believed', 'what', '', 'she', 'they'),
    ('find', 'finds', 'found', 'where', ' it', 'he', 'you'),
    ('hear', 'hears', 'heard', 'what', '', 'she', 'you'),
    ('learn', 'learns', 'learned', 'where', ' English', 'he', 'she'),
    ('remember', 'remembers', 'remembered', 'what', '', 'she', 'you'),
    ('forget', 'forgets', 'forgot', 'why', ' it', 'he', 'you'),
    ('lose', 'loses', 'lost', 'how', ' it', 'she', 'he'),
    ('build', 'builds', 'built', 'what', '', 'he', 'they'),
    ('break', 'breaks', 'broke', 'why', ' it', 'he', 'she'),
    ('choose', 'chooses', 'chose', 'why', ' it', 'he', 'they'),
    ('understand', 'understands', 'understood', 'what', '', 'he', 'you'),
    ('decide', 'decides', 'decided', 'when', '', 'she', 'they'),
    ('grow', 'grows', 'grew', 'how', '', 'it', 'they'),
    ('fall', 'falls', 'fell', 'why', '', 'it', 'he'),
    ('sit', 'sits', 'sat', 'where', '', 'he', 'you'),
    ('stand', 'stands', 'stood', 'where', '', 'she', 'you'),
    ('spend', 'spends', 'spent', 'how much', '', 'he', 'you'),
    ('earn', 'earns', 'earned', 'how much', '', 'she', 'you'),
    ('win', 'wins', 'won', 'how', ' it', 'he', 'they'),
    ('do', 'does', 'did', 'what', ' there', 'he', 'they'),
    ('have', 'has', 'had', 'what', '', 'he', 'they'),
    ('watch', 'watches', 'watched', 'what', ' on TV', 'he', 'they'),
    ('read', 'reads', None, 'what', ' daily', 'he', None),
    ('put', 'puts', None, 'where', ' it', 'he', None),
    ('cut', 'cuts', None, 'how', ' it', 'she', None),
    ('cost', 'costs', None, 'how much', ' now', 'it', None),
]

PRON_S3 = r'(?P<s>he|she|it)'
PRON_ALL = r'(?P<s>I|you|he|she|it|we|they)'
FOLLOW = r'(?:\s[^.!?,;:"“”‘’\x27()\n]{0,70})?\?'
FOLLOW_AUX = r'(?:\s*\?|\s+(?:there|here|that|this|it|for|at|in|on|every|all|so|with|about|today|then|now)\b[^.!?,;:"“”‘’\x27()\n]{0,50}\?)'
FOLLOW_HAVE = (r'(?:\s*\?|\s+(?:a|an|the|to|some|any|no|more|my|your|his|her|our|their|this|that|so|many|much|enough)'
               r'\b[^.!?,;:"“”‘’\x27()\n]{0,60}\?)')


def build_verbs():
    for base, third, past, wh, tail, s3, sp in VERBS:
        Wh = cap(wh)
        follow = FOLLOW_AUX if base == 'do' else FOLLOW_HAVE if base == 'have' else FOLLOW
        # present, third person: "Where he works?" -> "Where does he work?"
        pat = subst(r'(?im)<<SS>><<WH>>\s+(?P<target>' + PRON_S3 + ' ' + third + r')\b<<F>>',
                    SS=SS, WH=WHQ, F=follow)
        pos = f'{Wh} {s3} {third}{tail}?'
        exp = f'{Wh} does {s3} {base}{tail}?'
        neg = (f'{Wh} does {s3} {base}{tail}? I know {wh} {s3} {third}{tail}. '
               f'{Wh} {s3} {third}{tail} is not clear. He {third}{tail} {wh}?')
        if base in ('do', 'have'):
            neg = (f'{Wh} does {s3} {base}{tail}? I know {wh} {s3} {third}{tail}. '
                   f'{Wh} {s3} {third}{tail} is not clear.')
        R(f'q3sg.{base}', pat, 'does ${s} ' + base, 'Grammar', 0.9,
          f'A question needs “does” before the subject and the plain verb: “{wh} does {s3} {base}”.',
          pos, exp, neg)
        # simple past: "Why they left?" -> "Why did they leave?"
        if past:
            pat = subst(r'(?im)<<SS>><<WH>>(?P<target>\s' + PRON_ALL + ' ' + past + r')\b<<F>>',
                        SS=SS, WH=WHQ, F=follow)
            pos = f'{Wh} {sp} {past}{tail}?'
            exp = f'{Wh} did {sp} {base}{tail}?'
            neg = (f'{Wh} did {sp} {base}{tail}? I asked {wh} {sp} {past}{tail}. '
                   f'{Wh} {sp} {past}{tail} is not clear. {cap(sp)} {past}{tail} {wh}?')
            if base in ('do', 'have'):
                neg = (f'{Wh} did {sp} {base}{tail}? I asked {wh} {sp} {past}{tail}. '
                       f'{Wh} {sp} {past}{tail} is not clear.')
            R(f'qpast.{base}', pat, ' did ${s} ' + base, 'Grammar', 0.9,
              f'A past question needs “did” before the subject and the plain verb: “{wh} did {sp} {base}”.',
              pos, exp, neg)


# --- a noun phrase subject that stays before its auxiliary: "Why the server is down?" -------------------------
NOUNS = ('website|site|app|server|meeting|class|train|bus|flight|plane|package|order|payment|system|project|team|manager|'
         'boss|teacher|doctor|price|cost|file|document|report|email|message|link|page|button|form|door|shop|store|bank|'
         'office|station|airport|hotel|restaurant|library|school|college|weather|traffic|internet|wifi|battery|phone|'
         'computer|laptop|printer|car|road|game|match|movie|film|show|party|event|exam|test|result|schedule|deadline|plan|'
         'problem|error|issue|bug|software|network|service|line|queue|bill|account|password|card|ticket|key|light|water|food')
DET = r'(?:the|my|your|his|her|our|their|this|that|these|those)'
PARTICIPLES = (r'(?:been|done|become|gone|made|taken|given|shown|happened|stopped|changed|failed|started|finished|arrived|'
               r'left|received|sent|read|seen|used|got|gotten|caused|helped|worked|come|brought|lost|found|written|heard|'
               r'kept|decided|improved|increased|reached|moved|ended|won|died|opened|closed|called|asked|told|said)')
WH_FORMS = {
    'what': r'what(?: time)?',
    'where': 'where',
    'why': 'why',
    'how': r'how(?: (?:much|long|often|far|soon|fast|old))?',
    'when': 'when',
    'who': 'who',
}
WH_EX = {
    'what': ('What the team is doing here?', 'What is the team doing here?'),
    'where': ('Where the server is hosted?', 'Where is the server hosted?'),
    'why': ('Why the website is down?', 'Why is the website down?'),
    'how': ('How the meeting is going?', 'How is the meeting going?'),
    'when': ('When the train was delayed?', 'When was the train delayed?'),
    'who': ('Who the manager is for this project?', 'Who is the manager for this project?'),
}


def build_noun_subject():
    for wh, form in WH_FORMS.items():
        base_neg = lambda q: q
        # be
        pat = subst(r'(?im)<<SS>><<WH>>\s+(?P<target>(?P<np><<DET>> (?:<<N>>)s?) (?P<a>is|are|was|were))\s+[^.!?,;:"“”‘’\x27()\n]{1,60}\?',
                    SS=SS, WH=form, DET=DET, N=NOUNS)
        pos, exp = WH_EX[wh]
        neg = ('Is the team busy? ' + 'I know ' + wh + ' the team is busy. ' + cap(wh) + ' the team is busy is unclear. '
               + cap(wh) + ' the heck is that?') if wh != 'who' else \
              'Is the team busy? I know who the manager is. Who the manager is remains unclear. Who the heck is that?'
        R(f'q_np_be.{wh}', pat, '${a} ${np}', 'Grammar', 0.9,
          'In a question the verb goes before its subject.', pos, exp, neg)
        # modal
        pat = subst(r'(?im)<<SS>><<WH>>\s+(?P<target>(?P<np><<DET>> (?:<<N>>)s?) (?P<a>will|would|can|could|should|must|may|might))\s+[^.!?,;:"“”‘’\x27()\n]{1,60}\?',
                    SS=SS, WH=form, DET=DET, N=NOUNS)
        mp = {
            'what': ('What the team can do about it?', 'What can the team do about it?'),
            'where': ('Where the meeting will be held?', 'Where will the meeting be held?'),
            'why': ('Why the server should restart?', 'Why should the server restart?'),
            'how': ('How the system can help us?', 'How can the system help us?'),
            'when': ('When the meeting will start?', 'When will the meeting start?'),
            'who': ('Who the manager would hire?', 'Who would the manager hire?'),
        }[wh]
        neg = (f'{cap(wh)} will the team do it? I wonder {wh} the team will do it. '
               f'{cap(wh)} the team will do it remains open.')
        R(f'q_np_modal.{wh}', pat, '${a} ${np}', 'Grammar', 0.9,
          'In a question the auxiliary verb goes before its subject.', mp[0], mp[1], neg)
        # perfect
        pat = subst(r'(?im)<<SS>><<WH>>\s+(?P<target>(?P<np><<DET>> (?:<<N>>)s?) (?P<a>has|have|had))\s+<<P>>\b[^.!?,;:"“”‘’\x27()\n]{0,50}\?',
                    SS=SS, WH=form, DET=DET, N=NOUNS, P=PARTICIPLES)
        pp = {
            'what': ('What the team has done so far?', 'What has the team done so far?'),
            'where': ('Where the package has gone?', 'Where has the package gone?'),
            'why': ('Why the server has stopped?', 'Why has the server stopped?'),
            'how': ('How the project has changed?', 'How has the project changed?'),
            'when': ('When the train had left?', 'When had the train left?'),
            'who': ('Who the manager has told?', 'Who has the manager told?'),
        }[wh]
        neg = (f'{cap(wh)} has the team gone? I wonder {wh} the team has gone. {cap(wh)} the store has is unclear.')
        R(f'q_np_perfect.{wh}', pat, '${a} ${np}', 'Grammar', 0.9,
          'In a question the auxiliary verb goes before its subject.', pp[0], pp[1], neg)


# --- "what means this?", "how looks it?", "how much costs it?" -------------------------------------------------
def build_idioms():
    # What means this? -> What does this mean?
    pat = subst(r'(?im)<<SS>>what\s+(?P<target>means (?P<np>this|that|it|(?:the|this|that|my|your) '
                r'(?:word|term|phrase|sentence|expression|abbreviation|acronym|symbol|sign|code|error|message|name|number|'
                r'letter|idiom|proverb|slang|saying|title|logo|icon|colou?r|text|quote|line|slogan|emoji)))\s*\?',
                SS=SS)
    R('what_means', pat, 'does ${np} mean', 'Grammar', 0.93,
      'A question needs “does” before the subject and the plain verb: “What does this mean?”',
      'What means this word?', 'What does this word mean?',
      'What does this word mean? What means the most to you? It means a lot. What means that this works is unclear.')
    pat = subst(r'(?im)<<SS>>what\s+(?P<target>mean (?P<np>this|that|it|(?:the|this|that|my|your) '
                r'(?:word|term|phrase|sentence|expression|abbreviation|acronym|symbol|sign|code|error|message|name|number|'
                r'letter|idiom|proverb|slang|saying|title|logo|icon|colou?r|text|quote|line|slogan|emoji)))\s*\?',
                SS=SS)
    R('what_mean_singular', pat, 'does ${np} mean', 'Grammar', 0.93,
      'A question needs “does” before the subject and the plain verb: “What does this mean?”',
      'What mean this?', 'What does this mean?',
      'What does this mean? You mean this? I mean what I said. Say what you mean.')
    pat = subst(r'(?im)<<SS>>what\s+(?P<target>mean (?P<np>these|those|they|(?:these|those|the|my|your) '
                r'(?:words|terms|phrases|sentences|expressions|abbreviations|acronyms|symbols|signs|codes|errors|messages|'
                r'names|numbers|letters|idioms|lines|icons|emojis|colou?rs)))\s*\?', SS=SS)
    R('what_mean_plural', pat, 'do ${np} mean', 'Grammar', 0.93,
      'A question needs “do” before the subject and the plain verb: “What do these words mean?”',
      'What mean these words?', 'What do these words mean?',
      'What do these words mean? What do they mean? They mean well. What mean the most to us are our friends.')
    # How looks it? -> How does it look?
    for base, third in (('look', 'looks'), ('work', 'works'), ('sound', 'sounds'), ('feel', 'feels'), ('taste', 'tastes'),
                        ('smell', 'smells'), ('seem', 'seems'), ('run', 'runs'), ('start', 'starts'), ('end', 'ends'),
                        ('happen', 'happens'), ('change', 'changes')):
        pat = subst(r'(?im)<<SS>>how\s+(?P<target>' + third + r' (?P<s>it|this|that|he|she))\s*\?', SS=SS)
        R(f'how_inverted.{base}', pat, 'does ${s} ' + base, 'Grammar', 0.93,
          f'A question needs “does” before the subject and the plain verb: “How does it {base}?”',
          f'How {third} it?', f'How does it {base}?',
          f'How does it {base}? I know how it {third}. How it {third} is a secret. How {third} the market?'
          if base not in ('look',) else 'How does it look? I know how it looks. How it looks is a secret. How goes it?')
    # How much costs it? / How much it cost? -> How much does it cost?
    pat = subst(r'(?im)<<SS>>how much\s+(?P<target>costs (?P<np>it|this|that|(?:the|this|that|my|your|our|his|her|their|a|an) [a-z]+))\s*\?', SS=SS)
    R('how_much_costs_inverted', pat, 'does ${np} cost', 'Grammar', 0.93,
      'A question needs “does” before the subject and the plain verb: “How much does it cost?”',
      'How much costs it?', 'How much does it cost?',
      'How much does it cost? How much does the ticket cost? I know how much it costs.')
    pat = subst(r'(?im)<<SS>>how much\s+(?P<target>(?P<np>it|this|that|(?:the|this|that|my|your|our|his|her|their) (?:<<N>>)s?) costs?)\s*\?',
                SS=SS, N=NOUNS)
    R('how_much_np_costs', pat, 'does ${np} cost', 'Grammar', 0.93,
      'A question needs “does” before the subject and the plain verb: “How much does it cost?”',
      'How much it costs?', 'How much does it cost?',
      'How much does it cost? I know how much the ticket costs. How much it costs is unclear.')
    # What time starts the movie? / When the movie starts? -> What time does the movie start?
    for base, third in (('start', 'starts'), ('end', 'ends'), ('open', 'opens'), ('close', 'closes'), ('begin', 'begins'),
                        ('leave', 'leaves'), ('arrive', 'arrives'), ('finish', 'finishes'), ('depart', 'departs')):
        pat = subst(r'(?im)<<SS>>(?:what time|when)\s+(?P<target>' + third +
                    r' (?P<np>(?:the|this|that|my|your|our|his|her|their) (?:<<N>>)s?))\s*\?', SS=SS, N=NOUNS)
        R(f'time_verb_first.{base}', pat, 'does ${np} ' + base, 'Grammar', 0.93,
          f'A question needs “does” before the subject and the plain verb: “What time does the movie {base}?”',
          f'What time {third} the show?', f'What time does the show {base}?',
          f'What time does the show {base}? I know what time the show {third}. When does the train {base}?')
        pat = subst(r'(?im)<<SS>>(?:what time|when)\s+(?P<target>(?P<np>(?:the|this|that|my|your|our|his|her|their) (?:<<N>>)s?) ' +
                    third + r')\s*\?', SS=SS, N=NOUNS)
        R(f'time_noun_first.{base}', pat, 'does ${np} ' + base, 'Grammar', 0.93,
          f'A question needs “does” before the subject and the plain verb: “When does the class {base}?”',
          f'When the class {third}?', f'When does the class {base}?',
          f'When does the class {base}? I know when the class {third}. When the class {third} is unclear.')


# --- "Where is located the station?" -> "Where is the station located?" (moved participle) --------------------
def build_moved():
    parts = ('located', 'situated', 'stored', 'kept', 'saved', 'held', 'placed', 'hosted', 'installed', 'spelled',
             'pronounced', 'abbreviated')
    for p in parts:
        pat = subst(r'(?im)<<SS>>(?:where|how|when|what time)\s+(?:is|are|was|were) (?P<target>' + p + r' )(?P<moved>(?:the|this|that|these|those|my|your|our|his|her|their) [a-z]+(?: [a-z]+){0,3})\s*\?', SS=SS)
        wh = {'located': 'Where', 'situated': 'Where', 'stored': 'Where', 'kept': 'Where', 'saved': 'Where',
              'held': 'Where', 'placed': 'Where', 'hosted': 'Where', 'installed': 'Where', 'spelled': 'How',
              'pronounced': 'How', 'abbreviated': 'How'}[p]
        np_ = 'your name' if wh == 'How' else 'the main office'
        R(f'passive_q.{p}', pat, ' ' + p, 'Grammar', 0.93,
          'In a question the subject goes right after “is” or “was”, and the participle follows it.',
          f'{wh} is {p} {np_}?', f'{wh} is {np_} {p}?',
          f'{wh} is {np_} {p}? I know {wh.lower()} it is {p}. {wh} is it {p}?', moved=True)
    for p, noun in (('found', 'the form'), ('bought', 'these tickets'), ('downloaded', 'the app'), ('seen', 'the results'),
                    ('booked', 'the room'), ('obtained', 'the licence'), ('reached', 'the manager')):
        pat = subst(r'(?im)<<SS>>(?:where|how|when|what time)\s+(?:can|could|should|will|would|may|must) (?P<target>be ' + p +
                    r' )(?P<moved>(?:the|this|that|these|those|my|your|our|his|her|their) [a-z]+(?: [a-z]+){0,2})\s*\?', SS=SS)
        wh = 'Where' if p != 'reached' else 'How'
        R(f'passive_modal_q.{p}', pat, ' be ' + p, 'Grammar', 0.93,
          'In a question the subject goes right after the modal, and “be” with the participle follows it.',
          f'{wh} can be {p} {noun}?', f'{wh} can {noun} be {p}?',
          f'{wh} can {noun} be {p}? I know {wh.lower()} it can be {p}. {wh} can it be {p}?', moved=True)


def build():
    build_verbs()
    build_noun_subject()
    build_idioms()
    build_moved()
