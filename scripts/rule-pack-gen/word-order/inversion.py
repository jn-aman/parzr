"""Inversions that learners skip or put in the wrong place: after "rarely", "neither", "under no circumstances", in
"if" clauses and "which one you want?"."""
from lib import *
from questions import VERBS

SUB = ['go', 'come', 'see', 'eat', 'drink', 'work', 'live', 'play', 'speak', 'write', 'watch', 'call', 'use', 'visit',
       'drive', 'sleep', 'study', 'help', 'think', 'know', 'say', 'tell', 'buy', 'leave', 'meet', 'take', 'make', 'get',
       'give', 'run', 'stay', 'wait', 'like', 'want', 'need', 'hear', 'feel', 'find', 'forget']
BYBASE = {v[0]: v for v in VERBS}
NEGADV = r'(?:Rarely|Seldom|Hardly ever|Hardly|Never)'


def build_negative_adverb():
    # Rarely I go -> Rarely do I go (present, not third person)
    verbs = [b for b in SUB if b not in ('feel',)]
    for adv, example in (('Rarely', 'Rarely I go to the cinema.'), ('Seldom', 'Seldom we eat out.'),
                         ('Hardly', 'Hardly I know anyone here.'), ('Never', 'Never you work on Sundays.')):
        alt = '|'.join(verbs)
        pat = subst(r'(?im)<<SS>>' + adv + r'\s+(?P<target>(?P<s>I|we|you|they)) (?:' + alt + r')\b', SS=SS)
        exp = example.replace(adv + ' ' + example.split()[1], adv + ' do ' + example.split()[1], 1)
        R(f'neg_adverb_do.{adv.lower()}', pat, 'do ${s}', 'Grammar', 0.92,
          f'After “{adv.lower()}” at the start of a sentence, the verb and subject swap and “do” is added.',
          example, exp,
          f'{adv} do I go there. I {adv.lower()} go there. {adv} did anyone know. {adv} I was there.')
    # third person and past, per verb
    for base in SUB:
        _, third, past, wh, tail, s3, sp = BYBASE[base]
        pat = subst(r'(?im)<<SS>><<N>>\s+(?P<target>(?P<s>he|she|it) ' + third + r')\b', SS=SS, N=NEGADV)
        R(f'neg_adverb_does.{base}', pat, 'does ${s} ' + base, 'Grammar', 0.92,
          'After “rarely”, “seldom”, “hardly” or “never” at the start of a sentence, the subject and “does” swap.',
          f'Rarely {s3} {third}{tail}.', f'Rarely does {s3} {base}{tail}.',
          f'Rarely does {s3} {base}{tail}. {cap(s3)} rarely {third}{tail}. Never ask why {s3} {third}.')
        if past and base not in ('like', 'want', 'need'):
            pat = subst(r'(?im)<<SS>><<N>>(?P<target> (?P<s>I|we|you|they|he|she|it) ' + past + r')\b', SS=SS, N=NEGADV)
            R(f'neg_adverb_did.{base}', pat, ' did ${s} ' + base, 'Grammar', 0.92,
              'After “rarely”, “seldom”, “hardly” or “never” at the start of a sentence, the subject and “did” swap.',
              f'Seldom {sp} {past}{tail}.', f'Seldom did {sp} {base}{tail}.',
              f'Seldom did {sp} {base}{tail}. {cap(sp)} seldom {past}{tail}. Never say why {sp} {past}.')


def build_fixed():
    # Neither I do. -> Neither do I.
    pat = subst(r'(?im)<<SS>>Neither(?P<target> (?P<s>I|we|you|they|he|she|it) (?P<a>do|does|did|am|is|are|was|were|have|has|had|can|could|will|would|should))\s*[.!?]', SS=SS)
    R('neither_inversion', pat, ' ${a} ${s}', 'Grammar', 0.93,
      'After “neither” the verb comes before the subject: “Neither do I”.',
      'I do not like it. Neither I do.', 'I do not like it. Neither do I.',
      'Neither do I. Neither am I. Neither he nor I could come. Neither he is happy nor she is sad. Me neither.')
    for w in ('Under no circumstances', 'On no account', 'At no time', 'In no way', 'Not for a moment'):
        key = w.lower().replace(' ', '_')
        pat = subst(r'(?im)<<SS>>' + w + r'(?P<target> (?P<s>you|I|we|they|he|she|it) (?P<a>should|must|can|will|would|may|could|might|shall))\b', SS=SS)
        R(f'neg_phrase.{key}', pat, ' ${a} ${s}', 'Grammar', 0.93,
          f'After “{w.lower()}” at the start of a sentence, the verb comes before the subject.',
          f'{w} you should open it.', f'{w} should you open it.',
          f'{w} should you open it. You should not open it {w.lower()}. We know {w.lower()} you can lose.')
    pat = subst(r'(?im)\bNo sooner(?P<target> (?P<s>I|we|you|they|he|she|it) had)\b')
    R('no_sooner', pat, ' had ${s}', 'Grammar', 0.93,
      'After “no sooner” the verb comes before the subject: “No sooner had I arrived”.',
      'No sooner I had arrived than it rained.', 'No sooner had I arrived than it rained.',
      'No sooner had I arrived than it rained. I had no sooner arrived than it rained.')
    pat = subst(r'(?im)\bWhy (?P<target>not you) (?:come|go|try|ask|join|call|take|have|do|use|see|check|read|write|tell|stay|buy|get|give|let|make|send|find|help|start|bring)\b')
    R('why_not_you', pat, 'don’t you', 'Grammar', 0.93,
      'To suggest something, say “Why don’t you …?”.',
      'Why not you come with us?', 'Why don’t you come with us?',
      'Why don’t you come with us? Why not you? Why not you and me?')
    # Why you not coming? -> Why aren't you coming?
    ing = ('coming|going|working|doing|answering|replying|responding|listening|helping|talking|speaking|trying|studying|eating|'
           'sleeping|using|joining|attending|wearing|looking|watching|waiting|calling|texting|reading|writing|playing|staying|'
           'leaving|taking|giving|telling|asking|picking|sending|paying|buying|selling|living|learning|moving|running|'
           'walking|driving|thinking|feeling|saying|getting|having|making|seeing')
    for who, neg, ex in (('you|we|they', 'aren’t', 'you'), ('he|she|it', 'isn’t', 'he'), ('I', 'am I not', 'I')):
        if who == 'I':
            pat = subst(r'(?im)\bWhy(?P<target> I not) (?:<<G>>)\b', G=ing)
            R('why_i_not_ing', pat, ' am I not', 'Grammar', 0.92,
              'In a question the verb “be” goes before the subject: “Why am I not …?”.',
              'Why I not working today?', 'Why am I not working today?',
              'Why am I not working today? Why am I working today? I wonder why I am not working.')
        else:
            tag = 'plural' if who.startswith('you') else 'singular'
            pat = subst(r'(?im)\bWhy (?P<target>(?P<s>' + who + r') not) (?:<<G>>)\b', G=ing)
            R(f'why_you_not_ing.{tag}', pat, neg + ' ${s}', 'Grammar', 0.92,
              f'In a question the verb “be” goes before the subject: “Why {neg} {ex} …?”.',
              f'Why {ex} not coming to the meeting?', f'Why {neg} {ex} coming to the meeting?',
              f'Why {neg} {ex} coming to the meeting? I know why {ex} is coming. Why {ex} coming?')
    # Why you not come? -> Why don't you come?
    pat = subst(r'(?im)\bWhy (?P<target>(?P<s>you|we|they) not) (?:come|go|call|reply|answer|tell|say|help|join|attend|try|ask|check|like|want|eat|talk|speak|study|work|listen|respond|do|take|give|send|stay|read|write)\b')
    R('why_you_not_verb.plural', pat, 'don’t ${s}', 'Grammar', 0.9,
      'To ask “why” about a habit, say “Why don’t you …?”.',
      'Why you not call me?', 'Why don’t you call me?',
      'Why don’t you call me? I know why you call me. Why not call me?')
    pat = subst(r'(?im)\bWhy (?P<target>(?P<s>he|she|it) not) (?:come|go|call|reply|answer|tell|say|help|join|attend|try|ask|check|like|want|eat|talk|speak|study|work|listen|respond|do|take|give|send|stay|read|write)\b')
    R('why_he_not_verb.singular', pat, 'doesn’t ${s}', 'Grammar', 0.9,
      'To ask “why” about a habit, say “Why doesn’t he …?”.',
      'Why he not call me?', 'Why doesn’t he call me?',
      'Why doesn’t he call me? I know why he calls me. Why not call me?')
    # Since when you are here? -> Since when are you here?
    pat = subst(r'(?im)<<SS>>Since when(?P<target> (?P<s>you|he|she|they|we|it|I) (?P<a>are|is|am|were|was|have|has|can|will))\s+[^.!?,;:"“”‘’\x27()\n]{1,60}\?', SS=SS)
    R('since_when', pat, ' ${a} ${s}', 'Grammar', 0.93,
      'In a question the verb goes before the subject: “Since when are you here?”.',
      'Since when you are here?', 'Since when are you here?',
      'Since when are you here? I wonder since when you are here. Since when you left, it rained.')
    # There is any problem? -> Is there any problem?
    for aux, inv in (('is', 'Is'), ('are', 'Are'), ('was', 'Was'), ('were', 'Were')):
        pat = subst(r'(?im)<<SS>>(?P<target>There ' + aux + r') (?:any|anyone|anybody|anything|anywhere)\b[^.!?,;:"“”‘’\x27()\n]{0,50}\?', SS=SS)
        R(f'there_any_question.{aux}', pat, f'{inv} there', 'Grammar', 0.9,
          f'A question with “any” needs “{aux}” before “there”: “{inv} there any …?”.',
          f'There {aux} any problem with it?', f'{inv} there any problem with it?',
          f'{inv} there any problem with it? There {aux} no problem with it. There {aux} any problem, I think.')


def build_if():
    for aux in ('would', 'could', 'should', 'can', 'will', 'must', 'may', 'might', 'have', 'has', 'had', 'am', 'is', 'are',
                'was', 'were'):
        pat = subst(r'(?im)<<SS>>If (?P<target>(?P<a>' + aux + r') (?P<s>I|you|we|they|he|she|it))\b', SS=SS)
        sample = {'am': 'If am I late, call me.', 'is': 'If is it ready, tell me.', 'are': 'If are you free, come.',
                  'was': 'If was it late, say so.', 'were': 'If were they there, ask.'}.get(
            aux, f'If {aux} you come, call me.')
        exp = sample.replace(f'If {aux} ' + sample.split()[2], f'If {sample.split()[2]} {aux}', 1)
        R(f'if_inversion.{aux}', pat, '${s} ${a}', 'Grammar', 0.93,
          'In an “if” clause the subject comes before the verb: “If you can …”.',
          sample, exp, f'{exp} {cap(aux)} you come? Is it ready?')
    pat = subst(r'(?im)<<SS>>If (?P<target>do )(?:you|we|they|I)\b', SS=SS)
    R('if_do', pat, '', 'Grammar', 0.93,
      'In an “if” clause there is no “do” before the subject: “If you like …”.',
      'If do you like it, buy it.', 'If you like it, buy it.',
      'If you like it, buy it. Do you like it? If I do, I will.')


def build_wh_noun():
    verbs = ['want', 'need', 'like', 'prefer', 'choose', 'recommend', 'think', 'use', 'buy', 'order', 'pick', 'suggest',
             'play', 'watch', 'read', 'eat', 'drink', 'say', 'know', 'mean', 'wear', 'take', 'do', 'have', 'study', 'learn',
             'speak', 'drive', 'write', 'see']
    nouns = ('one|ones|colou?r|kind|type|sort|size|day|time|music|food|language|movie|film|book|song|game|sport|car|phone|'
             'job|work|place|country|city|school|class|course|subject|option|way|team|player|model|brand|flavou?r|plan|'
             'dish|drink|shirt|dress|shoes')
    for v in verbs:
        pat = subst(r'(?im)<<SS>>(?:what|which) (?:<<N>>) (?P<target>(?P<s>you|they|we|I)) ' + v + r'\b[^.!?,;:"“”‘’\x27()\n]{0,40}\?', SS=SS, N=nouns)
        ex = {'want': ('Which one you want?', 'Which one do you want?'),
              'need': ('What size you need?', 'What size do you need?'),
              'like': ('What colour you like?', 'What colour do you like?'),
              'prefer': ('Which one you prefer?', 'Which one do you prefer?'),
              'choose': ('Which option you choose?', 'Which option do you choose?'),
              'recommend': ('Which book you recommend?', 'Which book do you recommend?'),
              'think': ('Which team you think will win?', 'Which team do you think will win?'),
              'use': ('Which phone you use?', 'Which phone do you use?'),
              'buy': ('What brand you buy?', 'What brand do you buy?'),
              'order': ('What dish they order?', 'What dish do they order?'),
              'pick': ('Which one we pick?', 'Which one do we pick?'),
              'suggest': ('Which way you suggest?', 'Which way do you suggest?'),
              'play': ('What game you play?', 'What game do you play?'),
              'watch': ('Which movie we watch?', 'Which movie do we watch?'),
              'read': ('What book you read?', 'What book do you read?'),
              'eat': ('What food you eat?', 'What food do you eat?'),
              'drink': ('What drink you drink?', 'What drink do you drink?'),
              'say': ('What way you say it?', 'What way do you say it?'),
              'know': ('Which team you know?', 'Which team do you know?'),
              'mean': ('Which one you mean?', 'Which one do you mean?'),
              'wear': ('Which shirt you wear?', 'Which shirt do you wear?'),
              'take': ('Which course you take?', 'Which course do you take?'),
              'do': ('What work you do?', 'What work do you do?'),
              'have': ('Which model you have?', 'Which model do you have?'),
              'study': ('What subject you study?', 'What subject do you study?'),
              'learn': ('Which language you learn?', 'Which language do you learn?'),
              'speak': ('Which language you speak?', 'Which language do you speak?'),
              'drive': ('Which car you drive?', 'Which car do you drive?'),
              'write': ('What kind you write?', 'What kind do you write?'),
              'see': ('Which movie you see?', 'Which movie do you see?')}[v]
        neg = ex[1] + ' I know which one I ' + v + '.'
        R(f'wh_noun_do.{v}', pat, 'do ${s}', 'Grammar', 0.9,
          'A question about a choice needs “do” before the subject: “Which one do you want?”.',
          ex[0], ex[1], neg)


def build():
    build_negative_adverb()
    build_fixed()
    build_if()
    build_wh_noun()
