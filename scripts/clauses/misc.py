"""Single constructions in clauses: "the reason is because", "for to", "how come that", "so therefore", "but
however", "Although, I think", "because that", "where ever", "too ... that", "not with standing" and similar.
"""
from core import add, not_in, any_word, START, W

SEC = 'Reasons, connectors and fixed frames'
WORD = r"[a-z'’]+"
SUBJ = r"(?:I|we|you|he|she|they|it|there|the|my|our|his|her|their|this|that)"

# ---- "the reason is because" ---------------------------------------------------------------------------------------
REASON_DET = (r"(?:the|this|that|my|your|his|her|our|their|main|real|only|other|biggest|primary|key|exact|true|actual|"
              r"first|second|simple|obvious|one|another|good|likely) ")
MID = not_in(['is', 'was', 'are', 'were', 'because', 'but', 'so'])
NOT_OF = not_in(['of'])
add('reason.reason_clause_is_because',
    r"(?i)\b" + REASON_DET + r"reasons?(?:\s+" + MID + r"){1,9}\s+(?:is|was)\s+(?P<target>because)\s+" + NOT_OF + r"\b",
    'that', 'Word choice', 0.9,
    '“The reason … is because” says “why” twice: write “is that”.',
    'The reason why the update failed is because the disk was full.',
    'The reason why the update failed is that the disk was full. The update failed because the disk was full. They reason that this is because of the disk. The reason is because of the weather.',
    'The reason why the update failed is that the disk was full.', SEC)

add('reason.reasons_are_because',
    r"(?i)\b" + REASON_DET + r"reasons(?:\s+" + MID + r"){0,9}\s+(?:are|were)\s+(?P<target>because)\s+" + NOT_OF + r"\b",
    'that', 'Word choice', 0.9,
    '“The reasons are because” says “why” twice: write “are that”.',
    'The main reasons for the delay were because the supplier closed and the port flooded.',
    'The main reasons for the delay were that the supplier closed and the port flooded. The delay happened because the supplier closed.',
    'The main reasons for the delay were that the supplier closed and the port flooded.', SEC)

add('reason.reason_being_because',
    r"(?i)\breasons? being (?P<target>because)\s+" + NOT_OF + r"\b",
    'that', 'Word choice', 0.88,
    '“The reason being because” says “why” twice: write “the reason being that”.',
    'We left early, the reason being because the roads were icy.',
    'We left early, the reason being that the roads were icy. We left early because the roads were icy.',
    'We left early, the reason being that the roads were icy.', SEC)

add('reason.reason_modal_because',
    r"(?i)\breasons? (?:will be|would be|has been|had been|could be|might be|may be|must be|should be|can be|seems to be|appears to be) (?P<target>because)\s+" + NOT_OF + r"\b",
    'that', 'Word choice', 0.88,
    '“The reason … is because” says “why” twice: write “that”.',
    'One reason could be because the sensors drift in cold weather.',
    'One reason could be that the sensors drift in cold weather. It could be because the sensors drift in cold weather.',
    'One reason could be that the sensors drift in cold weather.', SEC)

add('reason.reason_because_clause',
    r"(?i)\breasons? (?P<target>because) " + SUBJ + r"\b",
    'why', 'Grammar', 0.88,
    'After “the reason” use “why” (or “that”), not “because”.',
    'That is the reason because I called you this morning.',
    'That is the reason why I called you this morning. I called you because I was worried. The reason, because you asked, is simple.',
    'That is the reason why I called you this morning.', SEC)

# ---- for to / how come / in order for to ---------------------------------------------------------------------------
STRANDS_FOR = ['looking', 'look', 'looks', 'looked', 'searching', 'search', 'searches', 'searched', 'waiting', 'wait', 'waits',
               'waited', 'asking', 'ask', 'asks', 'asked', 'care', 'cared', 'caring', 'pay', 'paying', 'paid', 'apply',
               'applying', 'applied', 'vote', 'voted', 'voting', 'stand', 'standing', 'stood', 'fight', 'fighting', 'fought',
               'pray', 'praying', 'hope', 'hoping', 'hoped', 'wish', 'wishing', 'long', 'longing', 'hunt', 'hunting', 'shop',
               'shopping', 'call', 'calling', 'called', 'account', 'send', 'sending', 'sent', 'what', 'who', 'which', 'one',
               'something', 'anything', 'nothing', 'everything', 'thing', 'things', 'it', 'them', 'that', 'this', 'use', 'used']
add('frame.for_to_infinitive',
    r"(?i)\b" + not_in(STRANDS_FOR) + r"\s+(?P<target>for )(?-i:to) (?-i:" + W + r"+)\b",
    '', 'Grammar', 0.88,
    '“For to” is not standard: use “to” (or “in order to”).',
    'I called the office for to ask about my refund.',
    'I called the office to ask about my refund. I paid for tomatoes. The door is for to-go orders. What is it for? To cut paper. These are the courses you are looking for to help you.',
    'I called the office to ask about my refund.', SEC)

add('frame.in_order_for_to',
    r"(?i)\bin order (?P<target>for )to\b",
    '', 'Grammar', 0.92,
    'Say “in order to” (or “in order for him to”).',
    'We moved the meeting in order for to avoid the strike.',
    'We moved the meeting in order to avoid the strike. We moved the meeting in order for him to join.',
    'We moved the meeting in order to avoid the strike.', SEC)

add('frame.how_come_that',
    r"(?i)\bhow come (?P<target>that )(?:I|you|we|they|he|she|it|there|the|my|our|his|her|their)\b",
    '', 'Grammar', 0.88,
    '“How come” is followed directly by the clause: no “that”.',
    'How come that you never answered my message?',
    'How come you never answered my message? How come that is still open? I know that you answered.',
    'How come you never answered my message?', SEC)

add('frame.how_come_inversion',
    r"(?i)\bhow come (?P<target>(?P<aux>are|is|was|were|am|can|will|would|could|have|has|had) )(?P<moved>you|they|we|he|she|it|I)\b",
    ' ${aux}', 'Grammar', 0.88,
    '“How come” takes statement word order: “how come you are late”.',
    'How come are you so late today?',
    'How come you are so late today? Why are you so late today? How come you were not told?',
    'How come you are so late today?', SEC)

# ---- redundant connectors ---------------------------------------------------------------------------------------------
for key, adv, pos, fixed, neg in [
    ('therefore', 'therefore', 'The shop was closed, so therefore we went home.',
     'The shop was closed, therefore we went home.',
     'The shop was closed, so we went home. It was closed. Therefore we went home.'),
    ('thus', 'thus', 'The lease ended, so thus we had to move out.',
     'The lease ended, thus we had to move out.',
     'The lease ended, so we had to move out. The lease ended and thus we moved out. It is so thus far.'),
    ('hence', 'hence', 'The server was down, so hence we missed the deadline.',
     'The server was down, hence we missed the deadline.',
     'The server was down, so we missed the deadline. The server was down, hence the late report. So hence the name.'),
    ('consequently', 'consequently', 'Sales fell sharply, so consequently we cut the budget.',
     'Sales fell sharply, consequently we cut the budget.',
     'Sales fell sharply, so we cut the budget. Sales fell sharply. Consequently, we cut the budget.'),
]:
    nxt = r"(?:I|we|you|he|she|they|it|there|the|my|our|his|her|their)\b" if adv in ('therefore', 'consequently') else r"(?:I|we|you|he|she|they|it|there)\b"
    add('connector.so_' + key,
        r"(?i)\b(?P<target>so (?P<adv>" + adv + r")) " + nxt,
        '${adv}', 'Redundancy', 0.82,
        '“So” and “' + adv + '” do the same job; use one of them.',
        pos, neg, fixed, SEC)

add('connector.but_however',
    r"(?i)\bbut (?P<target>however,\s+)[a-z]",
    '', 'Redundancy', 0.9,
    '“But” and “however” do the same job; use one of them.',
    'The room was small, but however, it was bright and quiet.',
    'The room was small, but it was bright and quiet. The room was small. However, it was bright and quiet. It was small, but however small it was, it felt calm.',
    'The room was small, but it was bright and quiet.', SEC)

add('connector.addition_also',
    r"(?i)\b(?:in addition|moreover|furthermore|additionally),? (?P<target>also )[a-z]",
    '', 'Redundancy', 0.8,
    '“In addition”, “moreover” and “also” all add a point; one of them is enough.',
    'In addition, also the new rules apply to part-time staff.',
    'In addition, the new rules apply to part-time staff. We also checked the contract. In addition, we also checked the contract.',
    'In addition, the new rules apply to part-time staff.', SEC)

add('connector.stacked_result',
    r"(?i)\b(?:therefore|thus|hence)(?P<target>,? (?:therefore|thus|hence))\b",
    '', 'Redundancy', 0.84,
    'Two words that both mean “as a result” in a row: keep one.',
    'The price rose, thus therefore we stopped buying.',
    'The price rose, therefore we stopped buying. The price rose, and thus we stopped. Hence, we stopped buying.',
    'The price rose, thus we stopped buying.', SEC)

# ---- "Although, I think ..." as a sentence connector ---------------------------------------------------------------
add('connector.although_sentence_adverb',
    r"(?im)" + START + r"(?P<target>although),\s+(?:I|we|you|he|she|they|it|there|this|that|the|my|our|his|her|their)\s+[^,.!?;:\n]{3,80}[.!?]",
    'however', 'Word choice', 0.78,
    '“Although” starts a clause inside a sentence. To contrast with the last sentence, use “however”.',
    'The design is clean. Although, I think the colours are too dark.',
    'The design is clean. Although I think the colours are too dark, the layout works. Although it was late, we stayed. The design is clean. However, I think the colours are too dark.',
    'The design is clean. However, I think the colours are too dark.', SEC)

add('connector.although_stray_comma',
    r"(?im)" + START + r"although(?P<target>,) (?:I|we|you|he|she|they|it|there|(?:the|a|an|my|our|his|her|their|this|that|these|those) " + any_word() + r")[^.!?;:\n,]{12,60},\s",
    '', 'Punctuation', 0.86,
    'No comma after “although” when it opens a clause.',
    'Although, the food was cold, we enjoyed the evening.',
    'Although the food was cold, we enjoyed the evening. The food was cold, although it was fine. Although, as noted above, the food was cold, we enjoyed it.',
    'Although the food was cold, we enjoyed the evening.', SEC)

# ---- "because that" / "although that" ------------------------------------------------------------------------------
add('connector.because_that',
    r"(?i)\bbecause (?P<target>that )(?:I|we|you|he|she|they|it|there|the|my|our|his|her|their)\b",
    '', 'Grammar', 0.88,
    '“Because” needs no “that” before the clause.',
    'She was upset because that her flight had been cancelled twice.',
    'She was upset because her flight had been cancelled twice. She was upset because that was the second time. She said that her flight was cancelled.',
    'She was upset because her flight had been cancelled twice.', SEC)

add('connector.although_that',
    r"(?i)\balthough (?P<target>that )(?:I|we|you|he|she|they|it|there|the|my|our|his|her|their)\b",
    '', 'Grammar', 0.85,
    '“Although” needs no “that” before the clause.',
    'Although that the road was closed, the bus found another way.',
    'Although the road was closed, the bus found another way. Although that is true, the bus found another way. It is worth noting though that the road reopened.',
    'Although the road was closed, the bus found another way.', SEC)

# ---- split-up one-word connectors --------------------------------------------------------------------------------------
add('compound.all_though',
    r"(?i)\b(?P<target>all though) (?:I|we|you|he|she|they|it|there)\b",
    'although', 'Spelling', 0.9,
    'The conjunction is one word: “although”.',
    'All though it was late, the shop stayed open.',
    'Although it was late, the shop stayed open. We walked all through the night. He read all through it twice.',
    'Although it was late, the shop stayed open.', SEC)

add('compound.not_with_standing',
    r"(?i)\b(?P<target>not with standing) (?:the|a|an|his|her|their|my|our|its|that|this)\b",
    'notwithstanding', 'Spelling', 0.88,
    'The preposition is one word: “notwithstanding”.',
    'Not with standing the delay, the build shipped on Friday.',
    'Notwithstanding the delay, the build shipped on Friday. He was not with the group, standing at the back.',
    'Notwithstanding the delay, the build shipped on Friday.', SEC)

for key, split, joined, nxt, pos, neg in [
    ('where_ever', 'where ever', 'wherever', r"(?:you|I|we|they|he|she|it|there|the|this|that|my|our|your|his|her|their)",
     'Where ever you travel, keep a copy of your passport.',
     'Wherever you travel, keep a copy of your passport. Where ever did you put it? Where did you ever see that?'),
    ('when_ever', 'when ever', 'whenever', r"(?:you|I|we|they|he|she|it|there|the|this|that|my|our|your|his|her|their)",
     'Call me when ever you are ready to start.',
     'Call me whenever you are ready to start. When ever will it stop raining? When did you ever see that?'),
    ('what_ever', 'what ever', 'whatever', r"(?:you|I|we|they|he|she|it)",
     'We will support what ever you decide.',
     'We will support whatever you decide. What ever did he say to her? What did you ever do about it?'),
    ('which_ever', 'which ever', 'whichever', r"(?:one|way|you|they|he|she|I|we)",
     'Take which ever route you prefer.',
     'Take whichever route you prefer. Which ever one of them wrote that? Which route did you ever take?'),
]:
    # "which ever one of them wrote that?" is a question: only "which ever one you ..." is a relative
    if key == 'which_ever':
        nxt = r"(?:(?-i:[a-z]+) )?(?:you|they|he|she|I|we)"
    add('compound.' + key,
        r"(?i)\b(?P<target>" + split + r") " + nxt + r"\b",
        joined, 'Spelling', 0.9,
        'The word is one word: “' + joined + '”.',
        pos, neg, pos.replace(split.capitalize(), joined.capitalize()).replace(split, joined), SEC)

# ---- "too ... that I can't" -> "so ... that" -----------------------------------------------------------------------------
ADJ = ['hot', 'cold', 'tired', 'big', 'small', 'hard', 'heavy', 'expensive', 'loud', 'fast', 'slow', 'busy', 'sleepy',
       'angry', 'sad', 'happy', 'tall', 'short', 'long', 'wide', 'narrow', 'dark', 'bright', 'crowded', 'noisy', 'thick',
       'thin', 'complicated', 'difficult', 'confusing', 'nervous', 'shy', 'scared', 'worried', 'excited', 'weak', 'strong',
       'windy', 'rainy', 'steep', 'deep']
add('frame.too_that_result',
    r"(?i)\b(?P<target>too) (?:" + '|'.join(ADJ) + r") that (?:I|we|you|he|she|they|it) (?:can['’]t|cannot|can not|couldn['’]t|could not|won['’]t|didn['’]t|did not|don['’]t|do not)\b",
    'so', 'Grammar', 0.9,
    'A result clause with “that” goes with “so”, not “too”: “so heavy that I could not lift it”.',
    'The box was too heavy that I could not lift it.',
    'The box was so heavy that I could not lift it. The box was too heavy to lift. It is too bad that I cannot come.',
    'The box was so heavy that I could not lift it.', SEC)

# ---- "such as like", "such as for example", "for example such as" -----------------------------------------------------
add('frame.such_as_like',
    r"(?i)\bsuch as (?P<target>(?-i:like) )",
    '', 'Redundancy', 0.82,
    '“Such as” and “like” both introduce examples; use one.',
    'We stock many drinks such as like tea, coffee and juice.',
    'We stock many drinks such as tea, coffee and juice. We stock drinks like tea. We like friends who are like-minded. Films such as Like Water for Chocolate are rare.',
    'We stock many drinks such as tea, coffee and juice.', SEC)

add('frame.such_as_for_example',
    r"(?i)\bsuch as (?P<target>for example )",
    '', 'Redundancy', 0.82,
    '“Such as” and “for example” both introduce examples; use one.',
    'Some tools are free, such as for example the viewer and the editor.',
    'Some tools are free, such as the viewer and the editor. Some tools are free; for example, the viewer is free.',
    'Some tools are free, such as the viewer and the editor.', SEC)

add('frame.for_example_such_as',
    r"(?i)[a-z],? (?P<target>for example )such as\b",
    '', 'Redundancy', 0.82,
    '“For example” and “such as” both introduce examples; use one.',
    'Some tools, for example such as the viewer, are free.',
    'Some tools, such as the viewer, are free. Some tools are free; for example, the viewer is free.',
    'Some tools, such as the viewer, are free.', SEC)
