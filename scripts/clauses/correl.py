"""Paired (correlative) conjunctions and the fixed frames around them.

neither ... nor, either ... or, between ... and, no sooner ... than, hardly ... when, not only ... but also, not so much
... as, the more ..., the more ...; and the "if / whether / in case / unless" family ("if or not", "whether if",
"unless if", "if in case", "in the event if"). Each rule fires only where the frame is complete in the sentence, so a
second "or" that belongs to a different structure ("neither of them is good or bad") is never touched.
"""
from core import add, not_in, any_word, START, W

SEC = 'Paired conjunctions and fixed frames'

DETN = r"(?:the|a|an|my|your|his|her|our|their|this|that|these|those)"
WORD = r"[a-z'’]+"
PRON = r"(?:he|she|it|they|we|I|you|him|her|them|us|me)"
NAME = r"(?-i:[A-Z][a-z]+)"
PRON2 = r"(?:he|she|it|they|we|I|you|him|her|them|us|me|this|that|these|those)"
AUXV = r"(?:am|is|are|was|were|be|been|being|can|could|will|would|do|does|did|should|must|may|might|shall|has|have|had|to)"
PREP = r"(?:in|on|at|by|for|with|from|to|about|through|under|over)"
NOT_FIRST = ['of', 'is', 'are', 'was', 'were', 'do', 'does', 'did', 'can', 'could', 'will', 'would', 'has', 'have', 'had',
             'should', 'must', 'may', 'might', 'one', 'the', 'a', 'an', 'to', 'in', 'on', 'at', 'by', 'for', 'with', 'from',
             'about', 'nor', 'as', 'be', 'been', 'being', 'am', 'my', 'your', 'his', 'her', 'our', 'their', 'this', 'that',
             'these', 'those', 'through', 'under', 'over']
FIRST = not_in(NOT_FIRST)

# ---- neither ... or  ->  neither ... nor ------------------------------------------------------------------------------
add('correlative.neither_or_noun_phrase',
    r"(?i)\bneither\s+" + DETN + r"\s+" + WORD + r"(?:\s+" + WORD + r")?\s+(?P<target>or)\s+" + DETN + r"\b",
    'nor', 'Grammar', 0.9,
    '“Neither” pairs with “nor”, not “or”.',
    'Neither the manager or the clerk had seen the memo.',
    'Neither the manager nor the clerk had seen the memo. The manager or the clerk will sign it. Neither of the two will sign or reply.',
    'Neither the manager nor the clerk had seen the memo.', SEC)

add('correlative.neither_or_pronoun',
    r"(?i)\bneither\s+" + PRON2 + r"\s+(?P<target>or)\s+" + WORD + r"\b",
    'nor', 'Grammar', 0.9,
    '“Neither” pairs with “nor”, not “or”.',
    'Neither he or his sister knew about the surprise party.',
    'Neither he nor his sister knew about the surprise party. He or she will call. Neither is ready or willing.',
    'Neither he nor his sister knew about the surprise party.', SEC)

add('correlative.neither_or_name',
    r"(?i)\bneither\s+" + NAME + r"\s+(?P<target>or)\s+(?-i:[A-Z])",
    'nor', 'Grammar', 0.9,
    '“Neither” pairs with “nor”, not “or”.',
    'Neither Maria or Jonas answered the phone.',
    'Neither Maria nor Jonas answered the phone. Maria or Jonas will answer. Neither of them answered or called back.',
    'Neither Maria nor Jonas answered the phone.', SEC)

add('correlative.neither_or_after_verb',
    r"(?i)\b" + AUXV + r"\s+neither\s+(?-i:" + FIRST + r")\s+(?P<target>or)\s+" + WORD + r"\b",
    'nor', 'Grammar', 0.88,
    '“Neither” pairs with “nor”, not “or”.',
    'The spokesperson can neither confirm or deny the report.',
    'The spokesperson can neither confirm nor deny the report. The result is neither good nor bad. She can confirm or deny it. He is neither of them.',
    'The spokesperson can neither confirm nor deny the report.', SEC)

add('correlative.neither_or_preposition',
    r"(?i)\bneither\s+" + PREP + r"\s+(?:" + DETN + r"\s+)?" + WORD + r"\s+(?P<target>or)\s+" + PREP + r"\b",
    'nor', 'Grammar', 0.9,
    '“Neither” pairs with “nor”, not “or”.',
    'The keys were neither in the drawer or on the shelf.',
    'The keys were neither in the drawer nor on the shelf. The keys were in the drawer or on the shelf.',
    'The keys were neither in the drawer nor on the shelf.', SEC)

# ---- either ... nor  ->  either ... or ------------------------------------------------------------------------------
add('correlative.either_nor_noun_phrase',
    r"(?i)\beither\s+" + DETN + r"\s+" + WORD + r"(?:\s+" + WORD + r")?\s+(?P<target>nor)\s+" + DETN + r"\b",
    'or', 'Grammar', 0.9,
    '“Either” pairs with “or”, not “nor”.',
    'You may pay either the full fee nor the deposit today.',
    'You may pay either the full fee or the deposit today. You may pay neither the full fee nor the deposit today.',
    'You may pay either the full fee or the deposit today.', SEC)

add('correlative.either_nor_pronoun',
    r"(?i)\beither\s+" + PRON + r"\s+(?P<target>nor)\b",
    'or', 'Grammar', 0.9,
    '“Either” pairs with “or”, not “nor”.',
    'Either he nor she will attend the review.',
    'Either he or she will attend the review. Neither he nor she will attend the review. Neither he nor she liked it.',
    'Either he or she will attend the review.', SEC)

add('correlative.either_nor_name',
    r"(?i)\beither\s+" + NAME + r"\s+(?P<target>nor)\s+(?-i:[A-Z])",
    'or', 'Grammar', 0.9,
    '“Either” pairs with “or”, not “nor”.',
    'Either Priya nor Sam can cover the Friday shift.',
    'Either Priya or Sam can cover the Friday shift. Neither Priya nor Sam can cover the Friday shift.',
    'Either Priya or Sam can cover the Friday shift.', SEC)

add('correlative.either_nor_after_verb',
    r"(?i)\b" + AUXV + r"\s+either\s+(?-i:" + FIRST + r")\s+(?P<target>nor)\s+" + WORD + r"\b",
    'or', 'Grammar', 0.88,
    '“Either” pairs with “or”, not “nor”.',
    'You can either stay nor leave, but you cannot wait here.',
    'You can either stay or leave, but you cannot wait here. You can neither stay nor leave.',
    'You can either stay or leave, but you cannot wait here.', SEC)

add('correlative.either_and_noun_phrase',
    r"(?i)\beither\s+" + DETN + r"\s+" + WORD + r"\s+(?P<target>and)\s+" + DETN + r"\b",
    'or', 'Grammar', 0.86,
    '“Either” pairs with “or”, not “and”.',
    'Please bring either the original and the copy to the desk.',
    'Please bring either the original or the copy to the desk. Please bring both the original and the copy. She sat on either side and watched.',
    'Please bring either the original or the copy to the desk.', SEC)

# ---- both ... as well as / and also ------------------------------------------------------------------------------------
add('correlative.both_as_well_as',
    r"(?i)" + START + r"both\s+" + DETN + r"\s+" + WORD + r"\s+(?P<target>as well as)\s+" + DETN + r"\b",
    'and', 'Grammar', 0.88,
    '“Both” pairs with “and”, not “as well as”.',
    'Both the manager as well as the team were pleased with the result.',
    'Both the manager and the team were pleased with the result. The manager as well as the team was pleased. She did both tasks as well as she could.',
    'Both the manager and the team were pleased with the result.', SEC)

# ---- between ... or  ->  between ... and ----------------------------------------------------------------------------
DET_ART = r"(?:the|a|an|my|your|his|her|our|their)"
add('correlative.between_or_noun_phrase',
    r"(?i)\bbetween\s+" + DETN + r"\s+" + WORD + r"(?:\s+" + WORD + r")?\s+(?P<target>or)\s+" + DET_ART + r"\s+" + WORD + r"\b",
    'and', 'Grammar', 0.88,
    '“Between” pairs with “and”, not “or”.',
    'She could not choose between the red coat or the blue one.',
    'She could not choose between the red coat and the blue one. She could choose the red coat or the blue one. Pick between two or three options. There was no relationship between the two or that kind of link.',
    'She could not choose between the red coat and the blue one.', SEC)

add('correlative.between_or_pronoun',
    r"(?i)\bbetween\s+(?:him|her|them|us|me|you|it|this|that|these|those)\s+(?P<target>or)\s+(?:him|her|them|us|me|you|it|this|that|these|those)\b",
    'and', 'Grammar', 0.88,
    '“Between” pairs with “and”, not “or”.',
    'It is hard to choose between this or that when both are cheap.',
    'It is hard to choose between this and that when both are cheap. You can take this or that. It stays between you and me.',
    'It is hard to choose between this and that when both are cheap.', SEC)

add('correlative.between_or_name',
    r"(?i)\bbetween\s+" + NAME + r"\s+(?P<target>or)\s+(?-i:[A-Z][a-z])",
    'and', 'Grammar', 0.85,
    '“Between” pairs with “and”, not “or”.',
    'The vote is between Lena or Marcus, and nobody else.',
    'The vote is between Lena and Marcus, and nobody else. The vote goes to Lena or Marcus. Choose between Option A or Option B.',
    'The vote is between Lena and Marcus, and nobody else.', SEC)

add('correlative.between_or_clock',
    r"(?i)\bbetween\s+\d{1,2}(?::\d\d)?\s?(?:a\.?m\.?|p\.?m\.?)\s+(?P<target>or)\s+\d{1,2}",
    'and', 'Grammar', 0.9,
    '“Between” pairs with “and”, not “or”.',
    'The courier comes between 9 am or 11 am on weekdays.',
    'The courier comes between 9 am and 11 am on weekdays. The courier comes at 9 am or 11 am on weekdays.',
    'The courier comes between 9 am and 11 am on weekdays.', SEC)

# ---- no sooner ... than, hardly / scarcely / barely ... when, not so much ... as -----------------------------------
NOT_THAN = not_in(['than', 'when', 'then', 'but', 'and', 'or'])
add('correlative.no_sooner_when',
    r"(?i)\bno sooner(?:\s+" + NOT_THAN + r"){1,8}\s+(?P<target>when)\b",
    'than', 'Grammar', 0.92,
    '“No sooner” pairs with “than”, not “when”.',
    'No sooner had we sat down when the lights went out.',
    'No sooner had we sat down than the lights went out. She wanted it no sooner than Friday. We left no sooner than they did.',
    'No sooner had we sat down than the lights went out.', SEC)

COMPARATIVE = ['more', 'less', 'better', 'worse', 'rather', 'other', 'greater', 'bigger', 'smaller', 'older', 'younger',
               'longer', 'shorter', 'higher', 'lower', 'faster', 'slower', 'harder', 'easier', 'larger', 'taller', 'any',
               'than', 'when', 'but', 'and', 'or', 'much', 'many', 'few', 'little', 'sooner', 'later', 'earlier',
               'different', 'differently', 'else', 'otherwise', 'same', 'instead', 'nearer', 'closer', 'further', 'farther',
               'cheaper', 'brighter', 'louder', 'quieter', 'wiser', 'safer', 'stronger', 'weaker', 'happier', 'busier',
               'heavier', 'lighter', 'deeper', 'richer', 'poorer', 'newer', 'fewer', 'worse', 'less']
for adv in ['hardly', 'scarcely', 'barely']:
    pos = {'hardly': 'Hardly had the meeting started than the fire alarm rang.',
           'scarcely': 'Scarcely had she opened the door than the dog bolted out.',
           'barely': 'Barely had they landed than the storm hit the airport.'}[adv]
    fixed = pos.replace(' than ', ' when ')
    neg = {'hardly': 'Hardly had the meeting started when the fire alarm rang. It was hardly more than a rumour. Hardly anyone knew more than that.',
           'scarcely': 'Scarcely had she opened the door when the dog bolted out. It cost scarcely more than before.',
           'barely': 'Barely had they landed when the storm hit the airport. She was barely taller than her brother.'}[adv]
    add('correlative.' + adv + '_than',
        r"(?i)\b" + adv + r"\s+(?:had|did|have|has)\s+(?:I|you|he|she|we|they|it|the\s+" + WORD + r")(?:\s+" + not_in(COMPARATIVE) + r"){1,6}\s+(?P<target>than)\b",
        'when', 'Grammar', 0.9,
        '“' + adv.capitalize() + ' … ” pairs with “when”, not “than”.',
        pos, neg, fixed, SEC)

add('correlative.not_so_much_than',
    r"(?i)\bnot so much\s+(?:the|a|an|that|this|my|our|your|his|her|their|because|what|who|how|why|when|where|for|in|on|at|by|with|to|about|from)(?:\s+" + not_in(['than', 'as', 'but', 'more', 'less', 'and', 'or', 'better', 'worse']) + r"){1,8}\s+(?P<target>than)\b",
    'as', 'Grammar', 0.88,
    '“Not so much … as” takes “as”, not “than”.',
    'It was not so much the price than the poor service that annoyed us.',
    'It was not so much the price as the poor service that annoyed us. She is not so much shy as quiet. It cost no more than that.',
    'It was not so much the price as the poor service that annoyed us.', SEC)

NOT_BUT = not_in(['but', 'and', 'also', 'or'])
for key, lead in [('not_only', 'not only'), ('not_just', 'not just')]:
    pos = {'not_only': 'The course is not only cheap, and also very practical.',
           'not_just': 'He is not just a coach and also a close friend.'}[key]
    fixed = {'not_only': 'The course is not only cheap, but also very practical.',
             'not_just': 'He is not just a coach but also a close friend.'}[key]
    neg = {'not_only': 'The course is not only cheap but also very practical. The course is cheap, and also practical. It is not only cheap and not only quick.',
           'not_just': 'He is not just a coach but also a close friend. He is a coach and also a friend.'}[key]
    add('correlative.' + key + '_and_also',
        r"(?i)\b" + lead + r"(?:\s+" + NOT_BUT + r",?){1,10}?\s+(?P<target>and)\s+also\b",
        'but', 'Grammar', 0.9,
        '“' + lead.capitalize() + '” pairs with “but also”, not “and also”.',
        pos, neg, fixed, SEC)

# ---- the more ..., more ...  ->  the more ..., the more ... --------------------------------------------------------
add('correlative.the_more_missing_the',
    r"(?i)\bthe (?:more|less) [^.!?;,\n]{3,50}, (?P<target>more|less) (?:I|you|we|they|he|she|it)\b",
    'the ${target}', 'Grammar', 0.88,
    'The pattern “the more …, the more …” needs “the” in both halves.',
    'The more you practice, more you improve.',
    'The more you practice, the more you improve. The more the merrier. We practice more, you improve more.',
    'The more you practice, the more you improve.', SEC)

COMP2 = ['sooner', 'earlier', 'better', 'faster', 'harder', 'longer', 'bigger', 'higher', 'lower', 'worse', 'easier',
         'cheaper', 'later', 'larger', 'stronger', 'quicker', 'smaller']
add('correlative.the_comparative_missing_the',
    r"(?i)\bthe (?:" + '|'.join(COMP2) + r") [^.!?;,\n]{3,50}, (?P<target>" + '|'.join(COMP2) + r") (?:I|you|we|they|he|she|it)\b",
    'the ${target}', 'Grammar', 0.88,
    'The pattern “the sooner …, the better …” needs “the” in both halves.',
    'The sooner you start, better you will feel.',
    'The sooner you start, the better you will feel. The sooner the better. If you run faster, you will feel better.',
    'The sooner you start, the better you will feel.', SEC)

# ---- if / whether / in case / unless / event / condition -----------------------------------------------------------
add('conditional.if_or_not',
    r"(?i)\b(?P<target>if or not)\b",
    'whether or not', 'Grammar', 0.93,
    'Say “whether or not”; “if or not” is not a set phrase.',
    'I wonder if or not the shop is open on Sundays.',
    'I wonder whether or not the shop is open on Sundays. Tell me if the shop is open. I will go whether or not it rains.',
    'I wonder whether or not the shop is open on Sundays.', SEC)

SUBJ_NEXT = r"(?:you|I|we|they|he|she|it|there|the|this|that|my|our|his|her|their|your|someone|anyone|somebody|anybody)"
add('conditional.whether_if',
    r"(?i)\bwhether (?P<target>if )" + SUBJ_NEXT + r"\b",
    '', 'Grammar', 0.92,
    'Use “whether” or “if”, not both.',
    'We have not decided whether if the event will move indoors.',
    'We have not decided whether the event will move indoors. We have not decided if the event will move indoors.',
    'We have not decided whether the event will move indoors.', SEC)

add('conditional.if_whether',
    r"(?i)\b(?:wonder|wondering|wondered|know|knows|knew|ask|asks|asked|asking|see|check|checking|checked|sure|unsure|doubt|decide|decided|determine|determined|tell|confirm|confirmed|understand|remember|clear|unclear|certain) (?P<target>if )whether\b",
    '', 'Grammar', 0.92,
    'Use “whether” or “if”, not both.',
    'Please check if whether the invoice was paid.',
    'Please check whether the invoice was paid. Please check if the invoice was paid. What if whether is a variable name?',
    'Please check whether the invoice was paid.', SEC)

add('conditional.unless_if',
    r"(?i)\bunless (?P<target>if )" + SUBJ_NEXT + r"\b",
    '', 'Grammar', 0.9,
    '“Unless” already means “if not”, so “if” is not needed.',
    'We will start at nine unless if the trains are delayed.',
    'We will start at nine unless the trains are delayed. We will start at nine if the trains run. I cannot go unless I finish early.',
    'We will start at nine unless the trains are delayed.', SEC)

add('conditional.if_in_case',
    r"(?i)\b(?P<target>if in case)\s+(?:you|I|we|they|he|she|it|there|the|any|someone|something|my|our|your|his|her|their)\b",
    'in case', 'Grammar', 0.92,
    'Say “in case” or “if”, not “if in case”.',
    'Keep a copy of the receipt, if in case the shop asks for it.',
    'Keep a copy of the receipt in case the shop asks for it. Keep a copy if the shop asks for it. Ask what to do in case of fire.',
    'Keep a copy of the receipt, in case the shop asks for it.', SEC)

add('conditional.in_the_event_if',
    r"(?i)\bin the event (?P<target>if)\b",
    'that', 'Grammar', 0.92,
    'Say “in the event that” (or “if”).',
    'In the event if the power fails, the generator starts automatically.',
    'In the event that the power fails, the generator starts automatically. If the power fails, the generator starts.',
    'In the event that the power fails, the generator starts automatically.', SEC)

add('conditional.in_the_case_if',
    r"(?i)\bin the case (?P<target>if)\b",
    'that', 'Grammar', 0.9,
    'Say “in the case that” (or “if”).',
    'In the case if the form is rejected, you may apply again.',
    'In the case that the form is rejected, you may apply again. In the case of a rejection, apply again.',
    'In the case that the form is rejected, you may apply again.', SEC)

add('conditional.on_condition_if',
    r"(?i)\bon (?:the )?condition (?P<target>if)\b",
    'that', 'Grammar', 0.9,
    'Say “on condition that” (or “if”).',
    'They agreed on the condition if the report is ready by Monday.',
    'They agreed on the condition that the report is ready by Monday. They agreed on condition that it is ready.',
    'They agreed on the condition that the report is ready by Monday.', SEC)

add('conditional.like_as_if',
    r"(?i)\b(?P<target>like )as (?:if|though)\b",
    '', 'Grammar', 0.9,
    'Use “as if” (or “like”), not “like as if”.',
    'It looks like as if the meeting will run late.',
    'It looks as if the meeting will run late. It looks like the meeting will run late. He talks as if he knew her.',
    'It looks as if the meeting will run late.', SEC)

# ---- even it rains ...  ->  even if it rains ------------------------------------------------------------------------
add('conditional.even_it_weather_present',
    r"(?i)\b(?P<target>even) it (?:rains|snows|is raining|is snowing|[’']s raining|[’']s snowing|will rain|will snow|would rain|would snow)\b",
    'even if', 'Grammar', 0.9,
    'Add “if”: “even if it rains”.',
    'We will hold the picnic even it rains tomorrow.',
    'We will hold the picnic even if it rains tomorrow. We will hold the picnic even when it rains. It rains even in July.',
    'We will hold the picnic even if it rains tomorrow.', SEC)

add('conditional.even_it_weather_past',
    r"(?i)\b(?P<target>even) it (?:rained|snowed|was raining|was snowing)\b",
    'even though', 'Grammar', 0.88,
    'Add “though”: “even though it rained”.',
    'The match went ahead even it rained all morning.',
    'The match went ahead even though it rained all morning. The match went ahead even when it rained. It rained even in the shelter.',
    'The match went ahead even though it rained all morning.', SEC)

add('conditional.even_it_costs',
    r"(?i)\b(?P<target>even) it (?:costs|takes|hurts|means|requires|needs) \S",
    'even if', 'Grammar', 0.86,
    'Add “if”: “even if it costs”.',
    'I will finish the course even it takes all year.',
    'I will finish the course even if it takes all year. Even this takes all year. I read even it, and it takes all year.',
    'I will finish the course even if it takes all year.', SEC)

add('conditional.even_it_adjective_comma',
    r"(?i)" + START + r"(?P<target>even) it(?: is|[’']s) (?:hard|difficult|expensive|late|early|risky|dangerous|cold|hot|raining|snowing|windy|true),",
    'even if', 'Grammar', 0.88,
    'Add “if”: “even if it is hard”.',
    'Even it is difficult, we should try the new method.',
    'Even if it is difficult, we should try the new method. Even it is a hard sell. Even this is difficult, but we try.',
    'Even if it is difficult, we should try the new method.', SEC)
