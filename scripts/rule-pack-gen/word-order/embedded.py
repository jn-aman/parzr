"""Questions inside a sentence keep statement order: "Do you know where is he?" -> "where he is"."""
from lib import *
from questions import VERBS

PREFIXES = [
    ('Do you know', '?'), ('Could you tell me', '?'), ('I wonder', '.'), ('She asked me', '.'), ('I have no idea', '.'),
    ('Please tell me', '.'), ('I am not sure', '.'), ('I do not understand', '.'), ('Let me see', '.'),
    ('He forgot', '.'), ('Nobody knows', '.'), ('We asked', '.'), ('Can you explain', '?'), ('I need to find out', '.'),
    ('I am curious', '.'),
]
WH_OF = {'what': 'what', 'where': 'where', 'when': 'when', 'why': 'why', 'how': 'how', 'who': 'who'}
# Question words that can head the part to restore: the whole wh phrase is the context, never edited.
ASK2 = (r'(?:clue|curious|show|showed|decide|decided|figure out|figured out|learn|learned|care|mind|notice|realize|'
        r'realise|doubt|inquire|enquire|describe|discover|determine|confirm|imagine|matter|depends? on)')


def build_do():
    # "what do you want" -> "what you want": drop the doubled "do"
    for wh, form in (('what', r'(?:what time|what)'), ('where', 'where'), ('when', 'when'), ('why', 'why'),
                     ('how', r'(?:how (?:much|many|long|often|far|old|soon|fast)|how)'), ('who', r'(?:who|whom)'),
                     ('if', 'if'), ('whether', 'whether')):
        pat = subst(r'(?im)\b<<ASK>><<OBJ>>\s+<<WH>>\s+(?P<target>do )(?:you|we|they|I)\b', ASK=ASK, OBJ=ASKOBJ, WH=form)
        pos = {'what': 'Please tell me what do you want.', 'where': 'I wonder where do they live.',
               'when': 'She asked me when do we start.', 'why': 'I do not know why do you ask.',
               'how': 'Could you tell me how do you know that?', 'who': 'I have no idea who do you mean.',
               'if': 'He asked me if do I like it.', 'whether': 'Nobody knows whether do we need it.'}[wh]
        exp = {'what': 'Please tell me what you want.', 'where': 'I wonder where they live.',
               'when': 'She asked me when we start.', 'why': 'I do not know why you ask.',
               'how': 'Could you tell me how you know that?', 'who': 'I have no idea who you mean.',
               'if': 'He asked me if I like it.', 'whether': 'Nobody knows whether we need it.'}[wh]
        neg = {'what': 'What do you want? Please tell me what you want. You know what? Do you want it?',
               'where': 'Where do they live? I wonder where they live. I wonder. Where do you go?',
               'when': 'When do we start? She asked me when we start. I know. When do you leave?',
               'why': 'Why do you ask? I do not know why you ask. I know. Why do I care?',
               'how': 'How do you know that? Could you tell me how you know that? I know. How do they do it?',
               'who': 'Who do you mean? I have no idea who you mean. I know. Who do they call?',
               'if': 'Do I like it? He asked me if I like it. I know. Do you want to?',
               'whether': 'Do we need it? Nobody knows whether we need it. I know. Do you agree?'}[wh]
        R(f'emb_do.{wh}', pat, '', 'Grammar', 0.93,
          'Inside a longer sentence a question keeps statement order, with no “do” before the subject.', pos, exp, neg)


def build_do_verbs():
    for i, (base, third, past, wh, tail, s3, sp) in enumerate(VERBS):
        pref, end = PREFIXES[i % len(PREFIXES)]
        whx = wh
        # does + he/she/it + base -> he/she/it + third person
        fol = r'\b'
        extra = ''
        if base in ('do', 'have'):
            fol = r'\b'
        pat = subst(r'(?im)\b<<ASK>><<OBJ>>\s+<<WHX>>\s+(?P<target>does (?P<s>he|she|it) ' + base + r')\b',
                    ASK=ASK, OBJ=ASKOBJ, WHX=WHX)
        pos = f'{pref} {whx} does {s3} {base}{tail}{end}'
        exp = f'{pref} {whx} {s3} {third}{tail}{end}'
        neg = f'{cap(whx)} does {s3} {base}{tail}? {pref} {whx} {s3} {third}{tail}{end}'
        R(f'emb_does.{base}', pat, '${s} ' + third, 'Grammar', 0.93,
          'Inside a longer sentence a question keeps statement order: “' + f'{whx} {s3} {third}' + '”, with no “does”.',
          pos, exp, neg)
        if past:
            pat = subst(r'(?im)\b<<ASK>><<OBJ>>\s+<<WHX>>\s+(?P<target>did (?P<s>I|you|he|she|it|we|they) ' + base + r')\b',
                        ASK=ASK, OBJ=ASKOBJ, WHX=WHX)
            pos = f'{pref} {whx} did {sp} {base}{tail}{end}'
            exp = f'{pref} {whx} {sp} {past}{tail}{end}'
            neg = f'{cap(whx)} did {sp} {base}{tail}? {pref} {whx} {sp} {past}{tail}{end}'
            R(f'emb_did.{base}', pat, '${s} ' + past, 'Grammar', 0.93,
              'Inside a longer sentence a question keeps statement order: “' + f'{whx} {sp} {past}' + '”, with no “did”.',
              pos, exp, neg)


def build_aux():
    # Asking words the engine's own list lacks: "I have no clue what is he doing" -> "what he is doing"
    ex = [
        ('clue', 'I have no clue what is he doing.', 'I have no clue what he is doing.'),
        ('curious', 'I am curious how is it going.', 'I am curious how it is going.'),
        ('show', 'Show me where is the button.', 'Show me where the button is.'),
    ]
    pat = subst(r'(?im)\b<<ASK2>><<OBJ>>\s+<<WHX>>\s+(?P<target>(?P<a>is|are|was|were|will|can|could|should|would|must|has|have|had) '
                r'(?P<s>he|she|it|they|we|you|I))\b', ASK2=ASK2, OBJ=ASKOBJ, WHX=WHX)
    cases = [
        ('clue', 'I have no clue what is he doing.', 'I have no clue what he is doing.'),
        ('curious', 'I am curious how is it going.', 'I am curious how it is going.'),
        ('show', 'Show me where are they.', 'Show me where they are.'),
        ('decide', 'We must decide when will we leave.', 'We must decide when we will leave.'),
        ('figure out', 'I cannot figure out why was she upset.', 'I cannot figure out why she was upset.'),
        ('learn', 'You will learn how can you help.', 'You will learn how you can help.'),
        ('care', 'I do not care who is he.', 'I do not care who he is.'),
        ('notice', 'Did you notice where have they gone?', 'Did you notice where they have gone?'),
        ('describe', 'Please describe how should we start.', 'Please describe how we should start.'),
        ('imagine', 'Can you imagine what would it cost?', 'Can you imagine what it would cost?'),
        ('doubt', 'I doubt whether can she come.', 'I doubt whether she can come.'),
        ('confirm', 'Please confirm when will you arrive.', 'Please confirm when you will arrive.'),
        ('determine', 'We need to determine why is it slow.', 'We need to determine why it is slow.'),
        ('discover', 'They will discover who are we.', 'They will discover who we are.'),
        ('mind', 'I do not mind where are you.', 'I do not mind where you are.'),
        ('notice2', 'He did not notice what was she doing.', 'He did not notice what she was doing.'),
    ]
    # one rule per asking word so each carries its own examples
    words = {
        'clue': 'clue', 'curious': 'curious', 'show': r'show|showed', 'decide': r'decide|decided',
        'figure out': r'figure out|figured out', 'learn': r'learn|learned', 'care': 'care', 'notice': 'notice',
        'describe': 'describe', 'imagine': 'imagine', 'doubt': 'doubt', 'confirm': 'confirm', 'determine': 'determine',
        'discover': 'discover', 'mind': 'mind',
    }
    for key, pos, exp in cases:
        if key == 'notice2':
            continue
        w = words[key]
        pat = subst(r'(?im)\b(?:' + w + r')<<OBJ>>\s+<<WHX>>\s+(?P<target>(?P<a>is|are|was|were|will|can|could|should|would|must|has|have|had) '
                    r'(?P<s>he|she|it|they|we|you|I))\b', OBJ=ASKOBJ, WHX=WHX)
        neg = exp + ' ' + {'clue': 'What is he doing?', 'curious': 'How is it going?', 'show': 'Where are they?'}.get(
            key, 'Why is it slow?')
        R(f'emb_aux.{key.replace(" ", "_")}', pat, '${s} ${a}', 'Grammar', 0.93,
          'Inside a longer sentence a question keeps statement order: the subject goes before the verb.',
          pos, exp, neg)


def build_if():
    # "Let me know if can you come." / "I wonder if will it rain." -> "if you can come" / "if it will rain"
    cases = [
        ('can', 'Let me know if can you come.', 'Let me know if you can come.'),
        ('could', 'I wonder if could we start earlier.', 'I wonder if we could start earlier.'),
        ('will', 'I wonder if will it rain.', 'I wonder if it will rain.'),
        ('would', 'She asked me if would I join.', 'She asked me if I would join.'),
        ('should', 'He asked whether should we wait.', 'He asked whether we should wait.'),
        ('is', 'Do you know if is he coming?', 'Do you know if he is coming?'),
        ('are', 'Tell me if are you ready.', 'Tell me if you are ready.'),
        ('was', 'I am not sure if was it ready.', 'I am not sure if it was ready.'),
        ('were', 'Nobody knows whether were they there.', 'Nobody knows whether they were there.'),
        ('have', 'I wonder whether have you seen it.', 'I wonder whether you have seen it.'),
        ('has', 'Can you check if has she replied?', 'Can you check if she has replied?'),
        ('had', 'He asked if had I eaten.', 'He asked if I had eaten.'),
        ('must', 'I wonder if must we pay.', 'I wonder if we must pay.'),
    ]
    for a, pos, exp in cases:
        pat = subst(r'(?im)\b<<ASK>><<OBJ>>\s+(?:if|whether)\s+(?P<target>(?P<a>' + a + r') (?P<s>I|you|he|she|it|we|they))\b',
                    ASK=ASK, OBJ=ASKOBJ)
        neg = exp + ' ' + f'{cap(a)} you ready? If {a} is a word, fine.' if a in ('is', 'are', 'was', 'were') else \
            exp + ' ' + f'{cap(a)} we start? Check if they {a} start.'
        # keep the negative simple and correct
        neg = exp + f' {cap(a)} he know? Ask whether it matters.' if a not in ('is', 'are', 'was', 'were') else \
            exp + f' {cap(a)} he ready? Ask whether it matters.'
        R(f'emb_if.{a}', pat, '${s} ${a}', 'Grammar', 0.93,
          'After “if” or “whether” a question keeps statement order: the subject goes before the verb.',
          pos, exp, neg)
    # "if does he like it" -> "if he likes it" (per verb, only for the common ones)
    for base, third, past, wh, tail, s3, sp in VERBS:
        if base in ('do', 'have'):
            continue
        pat = subst(r'(?im)\b<<ASK>><<OBJ>>\s+(?:if|whether)\s+(?P<target>does (?P<s>he|she|it) ' + base + r')\b',
                    ASK=ASK, OBJ=ASKOBJ)
        R(f'emb_if_does.{base}', pat, '${s} ' + third, 'Grammar', 0.92,
          'After “if” or “whether” a question keeps statement order, with no “does”.',
          f'I wonder if does {s3} {base}{tail}.', f'I wonder if {s3} {third}{tail}.',
          f'Does {s3} {base}{tail}? I wonder if {s3} {third}{tail}.')
        if past:
            pat = subst(r'(?im)\b<<ASK>><<OBJ>>\s+(?:if|whether)\s+(?P<target>did (?P<s>I|you|he|she|it|we|they) ' + base + r')\b',
                        ASK=ASK, OBJ=ASKOBJ)
            R(f'emb_if_did.{base}', pat, '${s} ' + past, 'Grammar', 0.92,
              'After “if” or “whether” a question keeps statement order, with no “did”.',
              f'She asked me whether did {sp} {base}{tail}.', f'She asked me whether {sp} {past}{tail}.',
              f'Did {sp} {base}{tail}? She asked me whether {sp} {past}{tail}.')


def build():
    build_do()
    build_do_verbs()
    build_aux()
    build_if()
