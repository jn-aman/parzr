"""Calques from Hindi, Spanish and French that the base and preposition packs leave open."""
from lib import R


def build():
    R('need.not_to', r'(?i)\b(?P<target>need not to)\b', 'need not', 'Grammar', 0.93, '“Need not” is followed by the plain verb: “you need not worry”.',
      'You need not to worry about it.', 'You need not worry about it.',
      'You need not worry about it. You do not need to worry about it. I need not be told.')
    R('need.not_to_contr', r"(?i)\b(?P<target>needn(?P<a>['’])t to)\b", 'needn${a}t', 'Grammar', 0.93, '“Needn’t” is followed by the plain verb: “he needn’t come”.',
      "He needn't to come today.", "He needn't come today.", "He needn't come today. He doesn't need to come today.")
    R('died.got', r'(?i)\b(?P<target>(?:got|get|gets|getting) died)\b', 'died', 'Grammar', 0.93, '“Die” is not passive: “he died”, not “he got died”.',
      'He got died in an accident.', 'He died in an accident.', 'He died in an accident. He got dressed in a hurry.')
    R('born.am', r'(?i)\bI (?P<target>am born) (?:in|on|at)\b', 'was born', 'Tense', 0.93, 'Birth is in the past: “I was born in 1990”.',
      'I am born in Delhi.', 'I was born in Delhi.', 'I was born in Delhi. Babies are born in hospitals. I am born again.')
    for rid, word, rep, pos, exp in [
        ('question.make', 'make', 'ask', 'I want to make a question.', 'I want to ask a question.'),
        ('question.made', 'made', 'asked', 'She made a question about it.', 'She asked a question about it.'),
        ('question.making', 'making', 'asking', 'He is making many questions.', 'He is asking many questions.'),
        ('question.makes', 'makes', 'asks', 'He makes a question every time.', 'He asks a question every time.'),
    ]:
        R(rid, rf'(?i)\b(?P<target>{word}) (?:a |some |many |two |three |the |any |one |another )?questions?(?:[.,;!?]|$| (?:to|about|for|regarding|on|and|but|please|now|today|tomorrow|before|every|again))', rep,
          'Word choice', 0.9, 'You “ask” a question; you do not “make” one.', pos, exp,
          'I want to ask a question. They make question marks out of paper. We made a questionnaire.')
    for rid, word, rep, pos, exp in [
        ('assist.meeting', 'assist', 'attend', 'I will assist to the conference tomorrow.', 'I will attend the conference tomorrow.'),
        ('assisted.meeting', 'assisted', 'attended', 'I assisted the meeting yesterday.', 'I attended the meeting yesterday.'),
        ('assisting.meeting', 'assisting', 'attending', 'She is assisting the class today.', 'She is attending the class today.'),
    ]:
        tail = r'(?:[.,;!?]|$| (?:on|in|at|and|last|this|next|tomorrow|today|yesterday|with|for))'
        R(rid, rf'(?i)\b(?P<target>{word}(?: to)?) (?:the |a |my |our |this |that |his |her |their )(?:meeting|conference|class|lecture|seminar|event|wedding|funeral|webinar|session|concert){tail}',
          rep, 'Word choice', 0.85,
          '“Assist” means help; for being present at an event, say “attend”.', pos, exp,
          'I will attend the conference tomorrow. I will assist the meeting chair. She assisted at the wedding.')
