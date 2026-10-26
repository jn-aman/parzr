"""Where adverbs and objects go: frequency adverbs, "very much", manner and time adverbs that split verb and object."""
from lib import *

BOUND = (r'(?:\s*[.,;!?)]|\s*$|\s+(?:but|because|so|before|after|when|while|then|too|again)\b|'
         r'\s+and\s+(?:I|we|he|she|they|it|you|there)\b)')
NP1 = r'(?:the|a|an|this|that|these|those|my|your|his|her|our|their|some|any) [a-z]+'
PRON_OBJ = r'(?:it|them|this|that|him|her|you|these|those|me|us)'


# --- "She is late always" -> "She is always late" ----------------------------------------------------------
def build_always():
    adjs = ['late', 'early', 'busy', 'tired', 'hungry', 'sleepy', 'rude', 'lazy', 'polite', 'noisy', 'nervous',
            'stressed', 'sick', 'angry', 'worried', 'cold', 'on time', 'in a hurry']
    for adj in adjs:
        pat = subst(r'(?i)\b(?P<target>(?P<b>is|are|am|was|were) ' + adj + r' always)\b', )
        key = adj.replace(' ', '_')
        R(f'always_after_adj.{key}', pat, '${b} always ' + adj, 'Grammar', 0.88,
          'A frequency adverb such as “always” goes after “be” and before the adjective.',
          f'My manager is {adj} always.', f'My manager is always {adj}.',
          f'My manager is always {adj}. Is he {adj}? He will be {adj}, always.')
    # He plays never -> He never plays
    verbs = [('go', 'goes', 'went'), ('play', 'plays', 'played'), ('eat', 'eats', 'ate'), ('drink', 'drinks', 'drank'),
             ('come', 'comes', 'came'), ('call', 'calls', 'called'), ('read', 'reads', 'read'),
             ('watch', 'watches', 'watched'), ('visit', 'visits', 'visited'), ('see', 'sees', 'saw'),
             ('use', 'uses', 'used'), ('smoke', 'smokes', 'smoked'), ('drive', 'drives', 'drove'),
             ('travel', 'travels', 'traveled'), ('cook', 'cooks', 'cooked'), ('work', 'works', 'worked'),
             ('study', 'studies', 'studied'), ('exercise', 'exercises', 'exercised'), ('walk', 'walks', 'walked'),
             ('listen', 'listens', 'listened'), ('wake', 'wakes', 'woke')]
    fol = r'(?:\s*[.,!?;]|\s*$|\s+(?:in|on|at|for|with|there|here|out|home)\b)'
    for base, third, past in verbs:
        forms = '|'.join(sorted({base, third, past}, key=len, reverse=True))
        pat = subst(r'(?i)\b(?P<target>(?P<v>' + forms + r') never)<<F>>', F=fol)
        pos = {'go': 'He goes never.', 'wake': 'She wakes never.'}.get(base, f'He {third} never.')
        pat_exp = pos.replace(f'{third} never', f'never {third}')
        R(f'never_after.{base}', pat, 'never ${v}', 'Grammar', 0.88,
          'A frequency adverb such as “never” goes before the main verb.',
          pos, pat_exp, f'He never {third}. Never {base} that. He {third} it, never again.' if base != 'read' else
          'He never reads. Never read that. He reads it, never again.')


# --- "I have seen never this film" -> "I have never seen this film"; "Have you seen ever ..." -----------------
PARTS = ['seen', 'been', 'done', 'gone', 'tried', 'visited', 'eaten', 'heard', 'met', 'read', 'written', 'taken', 'flown',
         'played', 'worked', 'lived', 'used', 'watched', 'travelled', 'traveled', 'spoken', 'driven', 'known', 'felt', 'said',
         'told', 'made', 'given', 'tasted', 'smoked', 'cooked', 'owned', 'worn', 'lost', 'won', 'failed', 'cried', 'lied']


def build_perfect_adverbs():
    pp = '|'.join(PARTS)
    fol = r'(?:\s+(?:in|on|at|for|with|there|here|before|such|the|a|an|any|this|that)\b|\s*[.,!?;]|\s*$)'
    pat = subst(r'(?i)\b(?P<target>(?P<h>have|has|had) (?P<pp>' + pp + r') never)<<F>>', F=fol)
    for h, p, pos, exp in (('have', 'seen', 'I have seen never such a thing.', 'I have never seen such a thing.'),
                           ('has', 'been', 'She has been never there.', 'She has never been there.')):
        pass
    R('have_pp_never', pat, '${h} never ${pp}', 'Grammar', 0.9,
      'A frequency adverb such as “never” goes between “have” and the past participle.',
      'I have seen never such a thing.', 'I have never seen such a thing.',
      'I have never seen such a thing. He has gone, never to return. I have never-ending work.')
    pat = subst(r'(?i)\b(?P<target>(?P<h>have|has|had) (?P<s>you|they|we|he|she|it|I|anyone|anybody) (?P<pp>' + pp +
                r') ever)\s+(?:a|an|the|such|any|so|this|that|my|his|her|their|our|your|one|anything|anyone)\b', )
    R('have_pp_ever', pat, '${h} ${s} ever ${pp}', 'Grammar', 0.9,
      'The adverb “ever” goes between the subject and the past participle in a question.',
      'Have you seen ever such a view?', 'Have you ever seen such a view?',
      'Have you ever seen such a view? Have you been ever since then? I have never known it.')
    pat = subst(r'(?i)\b(?P<target>(?P<h>have|has|had) (?P<s>you|they|we|he|she|it|I|anyone|anybody) been ever)\s+(?:to|in|at|there|here|abroad)\b', )
    R('have_been_ever', pat, '${h} ${s} ever been', 'Grammar', 0.9,
      'The adverb “ever” goes between the subject and “been” in a question.',
      'Have you been ever to Paris?', 'Have you ever been to Paris?',
      'Have you ever been to Paris? Have you been here ever since? She has been in Paris ever since 2010.')
    pat = subst(r'(?i)\b(?P<target>(?P<h>have|has|had) (?P<pp>been|gone|lived|worked|studied|stayed|visited|traveled|travelled) already)\s+(?:there|here|in|at|to|for)\b', )
    R('have_pp_already', pat, '${h} already ${pp}', 'Grammar', 0.88,
      'The adverb “already” goes between “have” and the past participle when something follows.',
      'We have been already there.', 'We have already been there.',
      'We have already been there. We have been there already. Has he gone already?')


# --- "I very like it" -> "I really like it" ----------------------------------------------------------------------
def build_very_like():
    for base in ('like', 'love', 'enjoy', 'appreciate', 'respect', 'admire', 'adore', 'miss', 'hate', 'prefer'):
        forms = f'{base}s?' if base not in ('enjoy', 'admire', 'adore', 'prefer') else f'{base}s?'
        pat = subst(r'(?i)\b(?:I|we|you|they|he|she) (?P<target>very) ' + forms + r'\b')
        pos = f'I very {base} it.' if base not in ('prefer',) else 'I very prefer tea.'
        exp = pos.replace('very', 'really')
        R(f'very_{base}', pat, 'really', 'Grammar', 0.9,
          f'“Very” cannot modify the verb “{base}” directly; say “really” or “very much”.',
          pos, exp, f'I really {base} it. I very much {base} it. Is it very {base}d?')


# --- "I like very much it" -> "I like it very much" (moved) ---------------------------------------------------
def build_degree_move():
    sets = [
        ('very much', ['like', 'love', 'enjoy', 'hate', 'miss', 'appreciate', 'respect', 'admire', 'adore', 'need',
                       'want', 'prefer', 'dislike']),
        ('so much', ['like', 'love', 'enjoy', 'hate', 'miss', 'appreciate']),
        ('a lot', ['like', 'love', 'enjoy', 'hate', 'miss', 'appreciate', 'need', 'want']),
    ]
    for adv, verbs in sets:
        tag = adv.replace(' ', '_')
        for base in verbs:
            forms = {'like': 'like|likes|liked', 'love': 'love|loves|loved', 'enjoy': 'enjoy|enjoys|enjoyed',
                     'hate': 'hate|hates|hated', 'miss': 'miss|misses|missed',
                     'appreciate': 'appreciate|appreciates|appreciated', 'respect': 'respect|respects|respected',
                     'admire': 'admire|admires|admired', 'adore': 'adore|adores|adored', 'need': 'need|needs|needed',
                     'want': 'want|wants|wanted', 'prefer': 'prefer|prefers|preferred',
                     'dislike': 'dislike|dislikes|disliked'}[base]
            past = forms.split('|')[1]
            # a pronoun object
            pat = subst(r'(?i)\b(?:' + forms + r')\s+(?P<target>' + adv + r' )(?P<moved>it|them|this|that|him|her|you|these|those)<<B>>', B=BOUND)
            ex_obj = {'like': 'it', 'love': 'her', 'enjoy': 'this', 'hate': 'that', 'miss': 'you', 'appreciate': 'it',
                      'respect': 'him', 'admire': 'her', 'adore': 'them', 'need': 'this', 'want': 'that',
                      'prefer': 'it', 'dislike': 'it'}[base]
            R(f'degree_pron.{tag}.{base}', pat, ' ' + adv, 'Grammar', 0.92,
              f'The object comes right after the verb; put “{adv}” after it.',
              f'I {base} {adv} {ex_obj}.', f'I {base} {ex_obj} {adv}.',
              f'I {base} {ex_obj} {adv}. I {base} {adv} to hear that. I {base} {adv} that you came.', moved=True)
            # a short noun phrase object
            pat = subst(r'(?i)\b(?:' + forms + r')\s+(?P<target>' + adv + r' )(?P<moved>(?:the|this|that|these|those|my|your|his|her|our|their) [a-z]+)<<B>>', B=BOUND)
            ex_np = {'like': 'this song', 'love': 'my family', 'enjoy': 'the film', 'hate': 'that noise', 'miss': 'my friends',
                     'appreciate': 'your help', 'respect': 'my teacher', 'admire': 'her work', 'adore': 'our dog',
                     'need': 'the money', 'want': 'this job', 'prefer': 'the first one', 'dislike': 'that idea'}[base]
            if base == 'prefer':
                ex_np = 'this plan'
            R(f'degree_np.{tag}.{base}', pat, ' ' + adv, 'Grammar', 0.92,
              f'The object comes right after the verb; put “{adv}” after it.',
              f'She {past} {adv} {ex_np}.',
              f'She {past} {ex_np} {adv}.',
              f'She {past} {ex_np} {adv}. She {past} {adv} the way you sing along. She {past} {adv} to see the plan.', moved=True)


# --- "He opened quickly the door" -> "He opened the door quickly" ---------------------------------------------
ADV = (r'(?:quickly|slowly|carefully|quietly|loudly|gently|easily|clearly|correctly|properly|completely|immediately|'
       r'perfectly|badly|well|fluently|fast|nicely|neatly|calmly|firmly|politely|directly|totally|recently)')


def build_manner():
    verbs = [
        ('open', 'opened', 'the door'), ('close', 'closed', 'the window'), ('answer', 'answered', 'the question'),
        ('read', 'read', 'the letter'), ('write', 'wrote', 'the report'), ('finish', 'finished', 'the work'),
        ('clean', 'cleaned', 'the room'), ('fix', 'fixed', 'the bug'), ('solve', 'solved', 'the problem'),
        ('explain', 'explained', 'the rule'), ('describe', 'described', 'the scene'), ('play', 'played', 'the piano'),
        ('hold', 'held', 'the baby'), ('push', 'pushed', 'the cart'), ('pull', 'pulled', 'the rope'),
        ('carry', 'carried', 'the box'), ('wash', 'washed', 'the car'), ('cook', 'cooked', 'the rice'),
        ('check', 'checked', 'the numbers'), ('handle', 'handled', 'the case'), ('cross', 'crossed', 'the road'),
        ('throw', 'threw', 'the ball'), ('catch', 'caught', 'the ball'), ('kick', 'kicked', 'the door'),
        ('eat', 'ate', 'the soup'), ('drink', 'drank', 'the tea'), ('paint', 'painted', 'the wall'),
        ('tie', 'tied', 'the knot'), ('lift', 'lifted', 'the lid'), ('drop', 'dropped', 'the glass'),
        ('touch', 'touched', 'the screen'), ('press', 'pressed', 'the button'), ('type', 'typed', 'the address'),
        ('pack', 'packed', 'the bags'), ('serve', 'served', 'the guests'),
    ]
    advs = ['quickly', 'slowly', 'carefully', 'quietly', 'gently', 'easily']
    for i, (base, past, obj) in enumerate(verbs):
        adv = advs[i % len(advs)]
        forms = '|'.join(sorted({base, past, base + 's', base + 'ing', base + 'es'}, key=len, reverse=True))
        if base == 'throw':
            forms = 'throw|throws|threw|throwing|thrown'
        if base == 'write':
            forms = 'write|writes|wrote|writing|written'
        if base == 'catch':
            forms = 'catch|catches|caught|catching'
        if base == 'eat':
            forms = 'eat|eats|ate|eating|eaten'
        if base == 'drink':
            forms = 'drink|drinks|drank|drinking|drunk'
        if base == 'read':
            forms = 'read|reads|reading'
        if base == 'hold':
            forms = 'hold|holds|held|holding'
        if base == 'carry':
            forms = 'carry|carries|carried|carrying'
        if base == 'clean':
            forms = 'clean|cleans|cleaned|cleaning'
        pat = subst(r'(?i)\b(?:' + forms + r')\s+(?P<target>(?P<adv><<A>>)\s+)(?P<moved>' + NP1 + r')<<B>>', A=ADV, B=BOUND)
        R(f'manner_split.{base}', pat, ' ${adv}', 'Grammar', 0.88,
          'Keep the verb and its object together; the adverb goes after the object.',
          f'He {past} {adv} {obj}.', f'He {past} {obj} {adv}.',
          f'He {past} {obj} {adv}. He {adv} {past} {obj}. He {past} {adv} for a while.', moved=True)
    # speak well English -> speak English well
    pat = subst(r'(?i)\b(?:speak|speaks|spoke|speaking)\s+(?P<target>(?P<adv>very well|well|fluently|badly|perfectly|quickly|slowly|clearly)\s+)(?P<moved>(?-i:English|French|German|Spanish|Hindi|Arabic|Chinese|Japanese|Italian|Russian|Portuguese|Urdu|Tamil|Bengali))<<B>>', B=BOUND)
    R('manner_split.speak_language', pat, ' ${adv}', 'Grammar', 0.92,
      'Keep the verb and its object together; say “speak English very well”.',
      'I speak very well English.', 'I speak English very well.',
      'I speak English very well. She speaks well of him. He speaks well and clearly.', moved=True)
    pat = subst(r'(?i)\b(?:know|knows|knew|learn|learns|learned|study|studies|studied|teach|teaches|taught)\s+(?P<target>(?P<adv>very well|well|badly|perfectly)\s+)(?P<moved>(?-i:English|French|German|Spanish|Hindi|Arabic|Chinese|Japanese|Italian|Russian|Portuguese|Urdu|Tamil|Bengali))<<B>>', B=BOUND)
    R('manner_split.know_language', pat, ' ${adv}', 'Grammar', 0.92,
      'Keep the verb and its object together; say “know English well”.',
      'She knows very well French.', 'She knows French very well.',
      'She knows French very well. She knows well enough to go. Know well, learn well.', moved=True)


# --- "I met yesterday my friend" -> "I met my friend yesterday" ----------------------------------------------
TIME = (r'(?:yesterday|today|tomorrow|last night|last week|last month|last year|this morning|this afternoon|this evening|'
        r'this week|last (?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)|'
        r'(?:a|one|two|three|four|five|six|several) (?:days?|weeks?|months?|years?|hours?|minutes?) ago)')


def build_time_move():
    verbs = [
        ('meet', 'met', 'my friend'), ('see', 'saw', 'the manager'), ('call', 'called', 'my mother'),
        ('visit', 'visited', 'the office'), ('text', 'texted', 'my brother'), ('email', 'emailed', 'the client'),
        ('phone', 'phoned', 'the doctor'), ('contact', 'contacted', 'the team'), ('invite', 'invited', 'my neighbour'),
        ('help', 'helped', 'my sister'), ('join', 'joined', 'the call'), ('watch', 'watched', 'the match'),
        ('read', 'read', 'the report'), ('buy', 'bought', 'a laptop'), ('sell', 'sold', 'the car'),
        ('finish', 'finished', 'the project'), ('start', 'started', 'a course'), ('clean', 'cleaned', 'the kitchen'),
        ('send', 'sent', 'the invoice'), ('receive', 'received', 'your letter'), ('find', 'found', 'my keys'),
        ('lose', 'lost', 'my phone'), ('pay', 'paid', 'the bill'), ('book', 'booked', 'a table'),
        ('order', 'ordered', 'a pizza'), ('fix', 'fixed', 'the printer'), ('write', 'wrote', 'the email'),
        ('bring', 'brought', 'the files'), ('cook', 'cooked', 'the dinner'), ('open', 'opened', 'an account'),
        ('close', 'closed', 'the shop'), ('hire', 'hired', 'a driver'), ('tell', 'told', 'the teacher'),
        ('ask', 'asked', 'the waiter'), ('thank', 'thanked', 'my boss'), ('hear', 'heard', 'the news'),
        ('forget', 'forgot', 'my wallet'), ('repair', 'repaired', 'the roof'), ('paint', 'painted', 'the door'),
        ('wash', 'washed', 'the car'),
    ]
    times = ['yesterday', 'last night', 'last week', 'this morning', 'two days ago', 'today', 'last Friday', 'last year',
             'this week', 'a month ago']
    forms_irr = {'meet': 'meet|meets|met', 'see': 'see|sees|saw', 'buy': 'buy|buys|bought', 'sell': 'sell|sells|sold',
                 'send': 'send|sends|sent', 'find': 'find|finds|found', 'lose': 'lose|loses|lost', 'pay': 'pay|pays|paid',
                 'write': 'write|writes|wrote', 'bring': 'bring|brings|brought', 'tell': 'tell|tells|told',
                 'hear': 'hear|hears|heard', 'forget': 'forget|forgets|forgot', 'read': 'read|reads',
                 'hire': 'hire|hires|hired', 'fix': 'fix|fixes|fixed', 'wash': 'wash|washes|washed',
                 'finish': 'finish|finishes|finished', 'watch': 'watch|watches|watched', 'push': 'push|pushes|pushed',
                 'contact': 'contact|contacts|contacted'}
    for i, (base, past, obj) in enumerate(verbs):
        t = times[i % len(times)]
        forms = forms_irr.get(base) or f'{base}|{base}s|{base}ed|{base}d'
        # direct objects: a short noun phrase or a pronoun
        pat = subst(r'(?i)\b(?:' + forms + r')\s+(?P<target>(?P<t><<T>>)\s+)(?P<moved>' + NP1 + r'|him|her|them|us|you|it)<<B>>',
                    T=TIME, B=BOUND)
        # the NP1 shape needs a/an/the/my..: make the sample match it
        R(f'time_split.{base}', pat, ' ${t}', 'Grammar', 0.88,
          'Keep the verb and its object together; the time goes after the object.',
          f'I {past} {t} {obj}.', f'I {past} {obj} {t}.',
          f'I {past} {obj} {t}. I {past} {t} for an hour. On {t} I {past} it.', moved=True)


# --- "Give me please the book" -> "Give me the book, please" --------------------------------------------------
def build_please():
    for base in ('give', 'send', 'show', 'tell', 'pass', 'bring', 'lend', 'buy', 'get', 'teach', 'make', 'help'):
        pat = subst(r'(?i)\b' + base + r'\s+(?:me|us)\s+(?P<target>please\s+)(?P<moved>(?:the|a|an|this|that|these|those|my|your|our|his|her|their|some|any|more) [a-z]+(?: [a-z]+)?)\s*(?:[.!?]|$)')
        obj = {'give': 'the book', 'send': 'the file', 'show': 'the map', 'tell': 'the answer', 'pass': 'the salt',
               'bring': 'a glass', 'lend': 'your pen', 'buy': 'a ticket', 'get': 'some water', 'teach': 'this song',
               'make': 'a coffee', 'help': 'the new menu'}[base]
        R(f'please_move.{base}', pat, ', please', 'Grammar', 0.9,
          '“Please” goes at the start or the end of the request, not between the verb and its object.',
          f'{cap(base)} me please {obj}.', f'{cap(base)} me {obj}, please.',
          f'{cap(base)} me {obj}, please. Please {base} me {obj}. {cap(base)} me, please.', moved=True)
    for base, wh in (('tell', 'where'), ('show', 'how'), ('explain', 'what')):
        pat = subst(r'(?i)<<SS>>(?P<target>' + base + r' (?:me|us) please)\s+(?:where|what|how|when|why|who|if|which)\b', SS=SS)
        R(f'please_front.{base}', pat, 'Please ' + base + ' me', 'Grammar', 0.9,
          '“Please” goes at the start of the request: “Please tell me where…”.',
          f'{cap(base)} me please {wh} the station is.', f'Please {base} me {wh} the station is.',
          f'Please {base} me {wh} the station is. {cap(base)} me {wh} it is, please.')
    verbs = ['send', 'check', 'help', 'come', 'find', 'give', 'tell', 'let', 'call', 'see', 'look', 'take', 'make', 'try',
             'wait', 'stay', 'sit', 'open', 'read', 'follow', 'share', 'provide', 'confirm', 'forward', 'update',
             'review', 'approve', 'reply', 'contact', 'do', 'go', 'use', 'add', 'fill', 'sign', 'join', 'ask', 'keep',
             'remember', 'visit', 'bring', 'show', 'advise', 'inform', 'note']
    for v in verbs:
        pat = subst(r'(?im)<<SS>>please (?P<target>you )' + v + r'\b', SS=SS)
        R(f'please_you.{v}', pat, '', 'Grammar', 0.93,
          'A polite command is “Please” and the verb; there is no “you” in between.',
          f'Please you {v} the form.', f'Please {v} the form.',
          f'Please {v} the form. Can you please {v} the form? Please, you {v} first.')


def build():
    build_always()
    build_perfect_adverbs()
    build_very_like()
    build_degree_move()
    build_manner()
    build_time_move()
    build_please()
