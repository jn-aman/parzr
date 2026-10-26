"""Doubled linking words: 'Although ... but', 'Because ... so', 'Despite ... but', 'Due to ... so', 'Because ... therefore'.

English joins a subordinate clause to its main clause with ONE linking word. The base Rust pass
(clause_repairs.rs, grammar.double_conjunction) already drops the second word after a sentence-initial
because / since / as / although / though plus a comma. These rules add what it does not read: even though,
even if, despite, in spite of, notwithstanding, because of, due to, owing to, thanks to and so on; the form with no
comma ("Although it rained but we went"); and the second word therefore / thus / hence / however / that's why.
Every rule is anchored to a sentence start, because a mid-sentence "but" after a full main clause is correct.
"""
from core import add, not_in, any_word, START, W

SEC = 'Doubled linking words'

NOM = ['i', 'we', 'he', 'she', 'they', 'there', 'everyone', 'everybody', 'someone', 'somebody', 'nobody', 'anyone']
DETS = ['the', 'a', 'an', 'my', 'our', 'his', 'her', 'their', 'your', 'its', 'this', 'that', 'these', 'those']
w = any_word()
# the subject that opens a subordinate clause: a pronoun, a determiner plus a noun, or a capitalized name
SUBJ = (r"(?:(?:I|we|you|he|she|they|it|there|this|that)"
        r"|(?:the|my|our|his|her|their|your|its|these|those|some|many|most|all|no) " + w + "(?: " + w + ")?"
        r"|(?-i:[A-Z][a-z]+))")
BODY_A = '(?-i:' + not_in(NOM) + ')'                       # a clause word that cannot start a second clause
BODY_B = '(?-i:' + not_in(NOM + DETS + ['and', 'but', 'or']) + ')'   # stricter: no comma to mark the clause end
CLAUSE_A = SUBJ + '(?: ' + BODY_A + '){0,6}'
CLAUSE_B = SUBJ + '(?: ' + BODY_B + '){0,3} '   # then the last word, captured as lastw by the caller
NEXT = r"(?:I|we|you|he|she|they|it|there|the|my|our|his|her|their|your|these|those)\b"
NEXT_PRON = r"(?:I|we|you|he|she|they|it|there)\b"
# after a linking "so" a subject must follow, and not the fixed asides "so they say", "so I hear", "so the story goes"
ASIDE_VERB = ['say', 'says', 'said', 'hear', 'heard', 'seems', 'seem', 'appears', 'appear', 'goes', 'go', 'gather',
              'gathered', 'understand', 'read', 'reckon', 'am']
ASIDE_NOUN = ['story', 'saying', 'legend', 'rumor', 'rumour', 'papers', 'press', 'media', 'news', 'experts', 'doctors',
              'rule', 'joke', 'song', 'proverb', 'book', 'bible', 'report', 'reports']
NEXT_SO = (r"(?:(?:I|we|you|he|she|they|it|there) (?-i:" + not_in(ASIDE_VERB) + r")\b"
           r"|(?:the|my|our|his|her|their|your|these|those) (?-i:" + not_in(ASIDE_NOUN) + r")\b)")
# a prepositional phrase after despite / because of: one word that may be a gerund or a name, then plain words
NP_HEAD = r"(?:(?:" + w + r"|(?-i:[A-Z]" + W + r"*))(?: " + BODY_A + r"){0,4} )?"
NP = r"(?:" + w + r"|(?-i:[A-Z]" + W + r"*))(?: " + BODY_A + "){0,5}"
# words that make "<clause> so" the pro-form ("said so", "told me so", "if so"): not the linking "so"
SO_PROFORM = ['said', 'say', 'says', 'think', 'thinks', 'thought', 'believe', 'believed', 'hope', 'hoped', 'guess',
              'suppose', 'assume', 'expect', 'imagine', 'fear', 'reckon', 'do', 'does', 'did', 'doing', 'done', 'told',
              'tell', 'tells', 'if', 'not', 'me', 'us', 'you', 'him', 'her', 'them', 'it', 'even', 'just', 'quite',
              'very', 'only', 'and', 'but', 'or', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'am', 'so', 'how',
              'why', 'as', 'than', 'too', 'also', 'really', 'always', 'never', 'still']
LAST_SO = '(?-i:' + not_in(NOM + SO_PROFORM + DETS) + ')'
CLAUSE_SO = SUBJ + '(?: ' + BODY_B + '){0,3} '


def sub(words):
    return '(?:' + '|'.join(x.replace(' ', r'\s+') for x in words) + ')'


# ---- concessive: although / though / even though / even if ... , but -------------------------------------------
add('concessive_but.even_though',
    '(?im)' + START + sub(['even though']) + r'\s+' + CLAUSE_A + r',(?P<target> but)\s+' + NEXT,
    '', 'Grammar', 0.9,
    '“Even though” already contrasts the two clauses: drop “but”.',
    'Even though the road was icy, but we reached the village before dark.',
    'Even though the road was icy, we reached the village before dark. We reached the village, but the road was icy. '
    'Even though the road was icy we kept going, but slowly.',
    'Even though the road was icy, we reached the village before dark.', SEC)

add('concessive_but.even_if',
    '(?im)' + START + sub(['even if']) + r'\s+' + CLAUSE_A + r',(?P<target> but)\s+' + NEXT,
    '', 'Grammar', 0.9,
    '“Even if” already carries the contrast: drop “but”.',
    'Even if the offer is generous, but I would still have to think about it.',
    'Even if the offer is generous, I would still have to think about it. The offer is generous, but I still have to think.',
    'Even if the offer is generous, I would still have to think about it.', SEC)

# the same four linking words with no comma: the "but" is replaced by the comma that was missing
for key, words, example in [
    ('although', ['although'], ('Although the soup was cold but he ate every spoonful.',
                                'Although the soup was cold, he ate every spoonful.',
                                'Although the soup was cold, he ate every spoonful. The soup was cold but he ate it. '
                                'Although she was tired she kept working, but only for an hour.')),
    ('though', ['though'], ('Though the hotel was cheap but the rooms were spotless.',
                            'Though the hotel was cheap, the rooms were spotless.',
                            'Though the hotel was cheap, the rooms were spotless. The hotel was cheap but spotless. '
                            'It was a small room, though, but it was clean.')),
    ('even_though', ['even though'], ('Even though it was snowing but the trains kept running.',
                                      'Even though it was snowing, the trains kept running.',
                                      'Even though it was snowing, the trains kept running. It was snowing but the '
                                      'trains ran. Even though he tried hard he failed, but he learned a lot.')),
    ('even_if', ['even if'], ('Even if the test fails but we will still ship on Friday.',
                              'Even if the test fails, we will still ship on Friday.',
                              'Even if the test fails, we will still ship on Friday. The test may fail but we ship. '
                              'Even if you ask twice nobody answers, but try anyway.')),
]:
    add('concessive_but_nocomma.' + key,
        '(?im)' + START + sub(words) + r'\s+' + CLAUSE_B + r'(?P<target>(?P<lastw>' + BODY_B + r') but )' + NEXT,
        '${lastw}, ', 'Grammar', 0.88,
        '“' + words[0].capitalize() + '” already contrasts the two clauses: close the first clause with a comma and drop “but”.',
        example[0], example[2], example[1], SEC)

# ---- concessive: although ... , however, ... -------------------------------------------------------------------
for key, words, pos, neg in [
    ('although', ['although'], ('Although the plan looked solid, however, the budget was too small.',
                                'Although the plan looked solid, the budget was too small.'),
     'Although the plan looked solid, the budget was too small. The plan looked solid; however, the budget was small. '
     'Although the plan looked solid, we had to ask however many people it took.'),
    ('though', ['though'], ('Though the weather was bad, however, we enjoyed the trip.',
                            'Though the weather was bad, we enjoyed the trip.'),
     'Though the weather was bad, we enjoyed the trip. The weather was bad. However, we enjoyed the trip.'),
    ('even_though', ['even though'], ('Even though the team worked late, however, the launch slipped.',
                                      'Even though the team worked late, the launch slipped.'),
     'Even though the team worked late, the launch slipped. The team worked late. However, the launch slipped.'),
    ('even_if', ['even if'], ('Even if the fee is small, however, most people will not pay it.',
                              'Even if the fee is small, most people will not pay it.'),
     'Even if the fee is small, most people will not pay it. The fee is small, however, and still people refuse.'),
]:
    add('concessive_however.' + key,
        '(?im)' + START + sub(words) + r'\s+' + CLAUSE_A + r',(?P<target> however,)\s+' + w,
        '', 'Redundancy', 0.82,
        '“' + words[0].capitalize() + '” already marks the contrast, so “however” repeats it.',
        pos[0], neg, pos[1], SEC)

# ---- concessive with a noun phrase: despite / in spite of / notwithstanding ... , but -----------------------------
for key, words, pos, fixed, neg in [
    ('despite', ['despite'], 'Despite the heavy rain, but the match went ahead as planned.',
     'Despite the heavy rain, the match went ahead as planned.',
     'Despite the heavy rain, the match went ahead as planned. The rain was heavy, but the match went ahead. '
     'Despite the rain we played, but the pitch was soaked.'),
    ('in_spite_of', ['in spite of'], 'In spite of his long illness, but he finished the degree on time.',
     'In spite of his long illness, he finished the degree on time.',
     'In spite of his long illness, he finished the degree on time. He was ill, but he finished the degree.'),
    ('notwithstanding', ['notwithstanding'], 'Notwithstanding the late hour, but the council kept voting.',
     'Notwithstanding the late hour, the council kept voting.',
     'Notwithstanding the late hour, the council kept voting. The hour was late, but the council voted on.'),
]:
    add('despite_but.' + key,
        '(?im)' + START + sub(words) + r'\s+' + NP + r',(?P<target> but)\s+' + NEXT,
        '', 'Grammar', 0.9,
        '“' + ' '.join(words).capitalize() + '” already carries the contrast: drop “but”.',
        pos, neg, fixed, SEC)
    add('despite_but_nocomma.' + key,
        '(?im)' + START + sub(words) + r'\s+' + NP_HEAD + r'(?P<target>(?P<lastw>' + BODY_A + r') but )' + NEXT,
        '${lastw}, ', 'Grammar', 0.86,
        '“' + ' '.join(words).capitalize() + '” already carries the contrast: use a comma, not “but”.',
        pos.replace(', but', ' but'),
        neg, fixed, SEC)

# ---- causal: because / since ... so (no comma), ... therefore / thus / hence, ... that's why ---------------------
for key, word, pos, fixed, neg in [
    ('because', 'because', 'Because the road was flooded so we turned back.', 'Because the road was flooded, we turned back.',
     'Because the road was flooded, we turned back. The road was flooded so we turned back. Because he said so I left. '
     'Because it rained so hard, the match stopped.'),
    ('since', 'since', 'Since the shop was closed so I bought nothing.', 'Since the shop was closed, I bought nothing.',
     'Since the shop was closed, I bought nothing. Since you asked so politely, I will help. '
     'The shop was closed so I bought nothing.'),
]:
    add('causal_so_nocomma.' + key,
        '(?im)' + START + word + r'\s+' + CLAUSE_SO + r'(?P<target>(?P<lastw>' + LAST_SO + r') so )' + NEXT_SO,
        '${lastw}, ', 'Grammar', 0.88,
        '“' + word.capitalize() + '” already gives the reason: close the clause with a comma and drop “so”.',
        pos, neg, fixed, SEC)

ADV = [('therefore', 'therefore', NEXT), ('thus', 'thus', NEXT_PRON), ('hence', 'hence', NEXT_PRON)]
CAUSAL = [
    ('because', 'because', 'Because the printer was jammed, {adv} we sent the file by email.',
     'Because the printer was jammed, we sent the file by email.'),
    ('since', 'since', 'Since the lease had ended, {adv} we had to move out.',
     'Since the lease had ended, we had to move out.'),
    ('as', 'as', 'As the meeting ran long, {adv} we skipped the last item.',
     'As the meeting ran long, we skipped the last item.'),
]
for ckey, cword, ptemplate, ftemplate in CAUSAL:
    for akey, aword, nxt in ADV:
        pos = ptemplate.format(adv=aword)
        neg = (ftemplate + ' ' + {
            'therefore': 'The printer was jammed. Therefore, we used email. The lease ended; therefore we moved.',
            'thus': 'The lease ended. The lease ended, and thus we moved.',
            'hence': 'The meeting ran long, hence the delay. The lease ended; hence we moved.'}[akey])
        add(f'causal_{akey}.{ckey}',
            '(?im)' + START + cword + r'\s+' + CLAUSE_A + r',(?P<target> ' + aword + r',?)\s+' + nxt,
            '', 'Redundancy', 0.82,
            '“' + cword.capitalize() + '” already gives the reason, so “' + aword + '” repeats it.',
            pos, neg, ftemplate, SEC)

for ckey, cword, pos, fixed, neg in [
    ('because', 'because', 'Because the road was closed, that is why we took the ferry.',
     'Because the road was closed, we took the ferry.',
     'Because the road was closed, we took the ferry. The road was closed. That is why we took the ferry.'),
    ('since', 'since', 'Since the lease had ended, that’s why we had to move.',
     'Since the lease had ended, we had to move.',
     'Since the lease had ended, we had to move. The lease ended, and that’s why we moved.'),
    ('as', 'as', 'As the weather turned bad, this is why we cancelled the picnic.',
     'As the weather turned bad, we cancelled the picnic.',
     'As the weather turned bad, we cancelled the picnic. The weather turned bad; this is why we cancelled.'),
]:
    add('causal_thats_why.' + ckey,
        '(?im)' + START + cword + r'\s+' + CLAUSE_A + r',(?P<target> (?:that[’\']s|that\s+is|this\s+is)\s+why)\s+' + NEXT_PRON,
        '', 'Redundancy', 0.82,
        '“' + cword.capitalize() + '” already gives the reason, so “that is why” repeats it.',
        pos, neg, fixed, SEC)

# ---- causal with a noun phrase: because of / due to / owing to / thanks to ... , so ---------------------------------
NP_PREP = [
    ('due_to', ['due to'], 'Due to the fog, so the airport closed for the morning.', 'Due to the fog, the airport closed for the morning.'),
    ('owing_to', ['owing to'], 'Owing to a power cut, so the lab shut early.', 'Owing to a power cut, the lab shut early.'),
    ('thanks_to', ['thanks to'], 'Thanks to your notes, so we passed the audit.', 'Thanks to your notes, we passed the audit.'),
    ('on_account_of', ['on account of'], 'On account of his injury, so the coach rested him.', 'On account of his injury, the coach rested him.'),
    ('in_view_of', ['in view of'], 'In view of the delay, so we moved the launch.', 'In view of the delay, we moved the launch.'),
]
for key, words, pos, fixed in NP_PREP:
    neg = fixed + ' The room was cold, so I left. ' + {
        'due_to': 'Due to the fog, so far nothing has landed.',
        'owing_to': 'Owing to a power cut, so be it.',
        'thanks_to': 'Thanks to your notes, so far so good.',
        'on_account_of': 'On account of his injury, so the story goes, he retired.',
        'in_view_of': 'In view of the delay, so be it.'}[key]
    add('causal_np_so.' + key,
        '(?im)' + START + sub(words) + r'\s+' + NP + r',(?P<target> so)\s+' + NEXT_SO,
        '', 'Grammar', 0.9,
        '“' + ' '.join(words).capitalize() + '” already gives the reason: drop “so”.',
        pos, neg, fixed, SEC)

for key, words, pos, fixed in [
    ('because_of', ['because of'], 'Because of the strike, therefore we rebooked the flight.', 'Because of the strike, we rebooked the flight.'),
    ('due_to', ['due to'], 'Due to the fog, therefore the airport closed for the morning.', 'Due to the fog, the airport closed for the morning.'),
    ('owing_to', ['owing to'], 'Owing to a power cut, therefore the lab shut early.', 'Owing to a power cut, the lab shut early.'),
    ('thanks_to', ['thanks to'], 'Thanks to your notes, therefore we passed the audit.', 'Thanks to your notes, we passed the audit.'),
]:
    neg = fixed + ' The fog came down. Therefore, the airport closed.'
    add('causal_np_therefore.' + key,
        '(?im)' + START + sub(words) + r'\s+' + NP + r',(?P<target> therefore,?)\s+' + NEXT,
        '', 'Redundancy', 0.82,
        '“' + ' '.join(words).capitalize() + '” already gives the reason, so “therefore” repeats it.',
        pos, neg, fixed, SEC)

for key, words, pos, fixed in [
    ('because_of', ['because of'], 'Because of the strike, that is why we rebooked the flight.', 'Because of the strike, we rebooked the flight.'),
    ('due_to', ['due to'], 'Due to the fog, that’s why the airport closed for the morning.', 'Due to the fog, the airport closed for the morning.'),
    ('owing_to', ['owing to'], 'Owing to a power cut, this is why the lab shut early.', 'Owing to a power cut, the lab shut early.'),
    ('thanks_to', ['thanks to'], 'Thanks to your notes, that is why we passed the audit.', 'Thanks to your notes, we passed the audit.'),
]:
    neg = fixed + ' There was a strike. That is why we rebooked the flight.'
    add('causal_np_thats_why.' + key,
        '(?im)' + START + sub(words) + r'\s+' + NP + r',(?P<target> (?:that[’\']s|that\s+is|this\s+is)\s+why)\s+' + NEXT,
        '', 'Redundancy', 0.82,
        '“' + ' '.join(words).capitalize() + '” already gives the reason, so “that is why” repeats it.',
        pos, neg, fixed, SEC)

# ---- more concessive openers: while / whereas / no matter / even when / despite the fact that -----------------------
for key, words, pos, fixed, neg in [
    ('while', ['while'], 'While the proposal has real merit, but the budget is simply too tight.',
     'While the proposal has real merit, the budget is simply too tight.',
     'While the proposal has real merit, the budget is simply too tight. The proposal has merit, but the budget is tight. '
     'While I agree with most of it, my objection stands, but only on one point.'),
    ('whereas', ['whereas'], 'Whereas the north is dry, but the south gets heavy rain every spring.',
     'Whereas the north is dry, the south gets heavy rain every spring.',
     'Whereas the north is dry, the south gets heavy rain every spring. The north is dry, but the south is wet.'),
    ('even_when', ['even when'], 'Even when the forecast looks bad, but we still go out for a short walk.',
     'Even when the forecast looks bad, we still go out for a short walk.',
     'Even when the forecast looks bad, we still go out for a short walk. We still go out, but not when it storms.'),
]:
    add('concessive_but.' + key,
        '(?im)' + START + sub(words) + r'\s+' + CLAUSE_A + r',(?P<target> but)\s+' + NEXT,
        '', 'Grammar', 0.9,
        '“' + ' '.join(words).capitalize() + '” already carries the contrast: drop “but”.',
        pos, neg, fixed, SEC)

for key, words, pos, fixed, neg in [
    ('while', ['while'], 'While the old system was slow but it never lost a record.',
     'While the old system was slow, it never lost a record.',
     'While the old system was slow, it never lost a record. The old system was slow but it never lost a record. '
     'While the old system was slow but safe, nobody complained.'),
    ('whereas', ['whereas'], 'Whereas the north is dry but the south gets heavy rain.',
     'Whereas the north is dry, the south gets heavy rain.',
     'Whereas the north is dry, the south gets heavy rain. The north is dry but the south is wet.'),
    ('even_when', ['even when'], 'Even when the road is icy but he still drives fast.',
     'Even when the road is icy, he still drives fast.',
     'Even when the road is icy, he still drives fast. The road is icy but he drives fast.'),
]:
    add('concessive_but_nocomma.' + key,
        '(?im)' + START + sub(words) + r'\s+' + CLAUSE_B + r'(?P<target>(?P<lastw>' + BODY_B + r') but )' + NEXT,
        '${lastw}, ', 'Grammar', 0.88,
        '“' + ' '.join(words).capitalize() + '” already carries the contrast: close the clause with a comma and drop “but”.',
        pos, neg, fixed, SEC)

add('concessive_but.no_matter_how',
    '(?im)' + START + r'no\s+matter\s+how\s+' + w + r'\s+' + CLAUSE_A + r',(?P<target> but)\s+' + NEXT,
    '', 'Grammar', 0.9,
    '“No matter how” already carries the contrast: drop “but”.',
    'No matter how hard the team trained, but they could not catch the leaders.',
    'No matter how hard the team trained, they could not catch the leaders. The team trained hard, but they could not catch the leaders.',
    'No matter how hard the team trained, they could not catch the leaders.', SEC)

add('concessive_but.no_matter_what',
    '(?im)' + START + r'no\s+matter\s+(?:what|where|who|when|whether|which)\s+' + CLAUSE_A + r',(?P<target> but)\s+' + NEXT,
    '', 'Grammar', 0.9,
    '“No matter what” already carries the contrast: drop “but”.',
    'No matter what the critics said, but she kept on writing.',
    'No matter what the critics said, she kept on writing. The critics objected, but she kept on writing.',
    'No matter what the critics said, she kept on writing.', SEC)

for key, words, pos, fixed, neg in [
    ('despite', ['despite'], 'Despite the fact that he was tired, but he finished the report.',
     'Despite the fact that he was tired, he finished the report.',
     'Despite the fact that he was tired, he finished the report. He was tired, but he finished the report.'),
    ('in_spite_of', ['in spite of'], 'In spite of the fact that the shop was shut, but she left a note.',
     'In spite of the fact that the shop was shut, she left a note.',
     'In spite of the fact that the shop was shut, she left a note. The shop was shut, but she left a note.'),
]:
    add('despite_but.fact_' + key,
        '(?im)' + START + sub(words) + r'\s+the\s+fact\s+that\s+' + CLAUSE_A + r',(?P<target> but)\s+' + NEXT,
        '', 'Grammar', 0.9,
        '“' + ' '.join(words).capitalize() + ' the fact that” already carries the contrast: drop “but”.',
        pos, neg, fixed, SEC)

# ---- more causal openers: now that / given that / seeing that / considering that ... , so ---------------------------
for key, words, pos, fixed, neg in [
    ('now_that', ['now that'], 'Now that the roads are clear, so we can finally deliver the order.',
     'Now that the roads are clear, we can finally deliver the order.',
     'Now that the roads are clear, we can finally deliver the order. The roads are clear, so we can deliver. '
     'Now that I think of it, so they say, it was her idea.'),
    ('given_that', ['given that'], 'Given that the lab was closed, so the samples stayed in storage.',
     'Given that the lab was closed, the samples stayed in storage.',
     'Given that the lab was closed, the samples stayed in storage. The lab was closed, so the samples stayed in storage.'),
    ('seeing_that', ['seeing that'], 'Seeing that no one replied, so I sent a reminder.',
     'Seeing that no one replied, I sent a reminder.',
     'Seeing that no one replied, I sent a reminder. No one replied, so I sent a reminder.'),
    ('considering_that', ['considering that'], 'Considering that the deadline had passed, so the committee made an exception.',
     'Considering that the deadline had passed, the committee made an exception.',
     'Considering that the deadline had passed, the committee made an exception. The deadline passed, so the committee made an exception.'),
]:
    add('causal_so.' + key,
        '(?im)' + START + sub(words) + r'\s+' + CLAUSE_A + r',(?P<target> so)\s+' + NEXT_SO,
        '', 'Grammar', 0.9,
        '“' + ' '.join(words).capitalize() + '” already gives the reason: drop “so”.',
        pos, neg, fixed, SEC)

for key, words, pos, fixed, neg in [
    ('now_that', ['now that'], 'Now that the roads are clear, therefore we can finally deliver the order.',
     'Now that the roads are clear, we can finally deliver the order.',
     'Now that the roads are clear, we can finally deliver the order. The roads are clear. Therefore, we can deliver the order.'),
    ('given_that', ['given that'], 'Given that the lab was closed, therefore the samples stayed in storage.',
     'Given that the lab was closed, the samples stayed in storage.',
     'Given that the lab was closed, the samples stayed in storage. The lab was closed; therefore the samples stayed in storage.'),
]:
    add('causal_therefore.' + key,
        '(?im)' + START + sub(words) + r'\s+' + CLAUSE_A + r',(?P<target> therefore,?)\s+' + NEXT,
        '', 'Redundancy', 0.82,
        '“' + ' '.join(words).capitalize() + '” already gives the reason, so “therefore” repeats it.',
        pos, neg, fixed, SEC)

# ---- "due to the fact that ..., so": the longer openers the base pass does not read ---------------------------------
for key, words, pos, fixed, neg in [
    ('due_to', ['due to'], 'Due to the fact that the road was closed, so we took the ferry.',
     'Due to the fact that the road was closed, we took the ferry.',
     'Due to the fact that the road was closed, we took the ferry. The road was closed, so we took the ferry.'),
    ('owing_to', ['owing to'], 'Owing to the fact that the sales were weak, so the board cut the budget.',
     'Owing to the fact that the sales were weak, the board cut the budget.',
     'Owing to the fact that the sales were weak, the board cut the budget. The sales were weak, so the board cut the budget.'),
    ('on_account_of', ['on account of'], 'On account of the fact that he was ill, so the match was moved.',
     'On account of the fact that he was ill, the match was moved.',
     'On account of the fact that he was ill, the match was moved. He was ill, so the match was moved.'),
    ('in_view_of', ['in view of'], 'In view of the fact that the vote failed, so the plan was dropped.',
     'In view of the fact that the vote failed, the plan was dropped.',
     'In view of the fact that the vote failed, the plan was dropped. The vote failed, so the plan was dropped.'),
]:
    add('causal_so.fact_' + key,
        '(?im)' + START + sub(words) + r'\s+the\s+fact\s+that\s+' + CLAUSE_A + r',(?P<target> so)\s+' + NEXT_SO,
        '', 'Grammar', 0.9,
        '“' + ' '.join(words).capitalize() + ' the fact that” already gives the reason: drop “so”.',
        pos, neg, fixed, SEC)

add('despite_but.fact_notwithstanding',
    '(?im)' + START + r'notwithstanding\s+the\s+fact\s+that\s+' + CLAUSE_A + r',(?P<target> but)\s+' + NEXT,
    '', 'Grammar', 0.9,
    '“Notwithstanding the fact that” already carries the contrast: drop “but”.',
    'Notwithstanding the fact that the fee was paid, but the access stayed blocked.',
    'Notwithstanding the fact that the fee was paid, the access stayed blocked. The fee was paid, but the access stayed blocked.',
    'Notwithstanding the fact that the fee was paid, the access stayed blocked.', SEC)
