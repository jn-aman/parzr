"""A preposition (or a noun-phrase-only linking word) used where a clause follows, and the reverse.

"because of he was late" (needs "because"), "due to he forgot", "despite it rained", "during I was away",
"in case of you need", and "Although the rain, we went" (needs "despite"). A nominative pronoun (I, he, she, we,
they) can never follow a preposition, so "<preposition> he <verb>" is certain: the writer meant a conjunction.
"it", "you" and "there" can follow a preposition, so they are matched only before an auxiliary / be-verb, where the
object reading is impossible.
"""
from core import add, not_in, any_word, START, W

SEC = 'A preposition where a clause follows'

AUX = ['am', 'is', 'are', 'was', 'were', 'has', 'have', 'had', 'will', 'would', 'can', 'could', 'should', 'must', 'may',
       'might', 'shall', 'did', 'do', 'does', "don't", "doesn't", "didn't", "isn't", "aren't", "wasn't", "weren't",
       "hasn't", "haven't", "hadn't", "won't", "wouldn't", "can't", "couldn't", "shouldn't", 'cannot']
IRREG = ['went', 'came', 'saw', 'left', 'took', 'got', 'made', 'said', 'gave', 'ran', 'knew', 'felt', 'thought', 'found',
         'told', 'began', 'wrote', 'lost', 'won', 'paid', 'met', 'sold', 'bought', 'brought', 'kept', 'held', 'stood',
         'sat', 'heard', 'became', 'chose', 'drove', 'spoke', 'broke', 'fell', 'flew', 'grew', 'threw', 'wore', 'sent',
         'spent', 'built', 'caught', 'taught', 'forgot', 'understood', 'slept', 'led', 'read']
BASE = ['need', 'want', 'have', 'get', 'go', 'know', 'think', 'feel', 'like', 'love', 'hate', 'see', 'make', 'take', 'give',
        'try', 'live', 'work', 'forget', 'lose', 'miss', 'prefer', 'believe', 'understand', 'speak', 'leave', 'come',
        'bring', 'find', 'keep', 'meet', 'pay', 'buy', 'sell', 'call', 'ask', 'play', 'wait', 'stay', 'run', 'learn']
THIRD = ['needs', 'wants', 'has', 'gets', 'goes', 'knows', 'thinks', 'feels', 'likes', 'loves', 'hates', 'sees', 'makes',
         'takes', 'gives', 'tries', 'lives', 'works', 'forgets', 'loses', 'misses', 'prefers', 'believes', 'understands',
         'speaks', 'leaves', 'comes', 'brings', 'finds', 'keeps', 'meets', 'pays', 'buys', 'sells', 'calls', 'asks',
         'plays', 'waits', 'stays', 'runs', 'learns']
VERBS = AUX + IRREG + BASE + THIRD
FINITE = '(?:' + '|'.join(sorted({v.replace("'", "['’]") for v in VERBS}, key=lambda s: -len(s))) + '|' + W + '+ed)\\b'
AUX_RE = '(?:' + '|'.join(sorted({v.replace("'", "['’]") for v in AUX}, key=lambda s: -len(s))) + ')\\b'
BE_AUX = r"(?:is|are|was|were|will|would|has|had|isn['’]t|wasn['’]t|can|could)\b"
NOMP = r"(?:I|he|she|they|we)"
# a subject pronoun fused with its auxiliary: "he's", "they're", "I've"
CONTR = r"(?:I|he|she|they|we)['’](?:m|ve|d|ll|s|re)\b"
SUBJ_FINITE = '(?:' + NOMP + ' ' + FINITE + '|' + CONTR + ')'
PRON_OBJ_POS = r"(?:I|he|she|they|we|you|it)"


def cap(words):
    return ' '.join(words).capitalize()


# ---- because of / due to / owing to / on account of + a clause: needs "because" -----------------------------------
add('prep_clause.because_of_subject',
    r"(?im)\bbecause (?P<target>of )" + SUBJ_FINITE,
    '', 'Grammar', 0.93,
    '“Because of” takes a noun; before a subject and verb use “because”.',
    'We missed the bus because of he forgot to set the alarm.',
    'We missed the bus because of him. Because of us, they won. She left because of the storm and because of it all.',
    'We missed the bus because he forgot to set the alarm.', SEC)

add('prep_clause.because_of_it',
    r"(?im)\bbecause (?P<target>of )it " + BE_AUX,
    '', 'Grammar', 0.9,
    '“Because of” takes a noun; before “it was” use “because”.',
    'The match was cancelled because of it was raining all day.',
    'The match was cancelled because it was raining all day. She apologized because of it. Because of it, we waited.',
    'The match was cancelled because it was raining all day.', SEC)

add('prep_clause.because_of_there',
    r"(?im)\bbecause (?P<target>of )there " + BE_AUX,
    '', 'Grammar', 0.93,
    '“Because of” takes a noun; before “there was” use “because”.',
    'The train was late because of there was a fault on the line.',
    'The train was late because there was a fault on the line. The train was late because of the fault. We worried because of there being a fault.',
    'The train was late because there was a fault on the line.', SEC)

# due to / owing to / on account of / thanks to: the writer meant "because"
for key, words, pos, fixed, neg in [
    ('due_to', 'due to', 'The meeting ended early due to she had another call.',
     'The meeting ended early because she had another call.',
     'The meeting ended early due to her other call. Due to us, nothing broke. The loss was due to them.'),
    ('owing_to', 'owing to', 'Owing to they were short of staff, the shop closed at noon.',
     'Because they were short of staff, the shop closed at noon.',
     'Owing to the lack of staff, the shop closed at noon. Owing to him, we finished early.'),
    ('on_account_of', 'on account of', 'He retired on account of he was ill.',
     'He retired because he was ill.',
     'He retired on account of illness. She stayed on account of them.'),
]:
    add('prep_clause.' + key + '_subject',
        r"(?im)\b(?P<target>" + words.replace(' ', r'\s+') + ") " + SUBJ_FINITE,
        'because', 'Grammar', 0.92,
        '“' + cap([words]) + '” takes a noun; before a subject and verb use “because”.',
        pos, neg, fixed, SEC)

add('prep_clause.due_to_there',
    r"(?im)\b(?P<target>due to) there (?:is|are|was|were|will be|would be|has been|had been)\b",
    'because', 'Grammar', 0.9,
    '“Due to” takes a noun; before “there was” use “because”.',
    'Several flights were cancelled due to there was a storm over the coast.',
    'Several flights were cancelled because there was a storm over the coast. Delays due to there being a storm are common. '
    'The cancellations were due to the storm.',
    'Several flights were cancelled because there was a storm over the coast.', SEC)

# ---- in spite of / despite + a clause: needs "although" ------------------------------------------------------------
add('prep_clause.in_spite_of_subject',
    r"(?im)\b(?P<target>in spite of) " + SUBJ_FINITE,
    'although', 'Grammar', 0.92,
    '“In spite of” takes a noun; before a subject and verb use “although”.',
    'In spite of she studied all night, she failed the first paper.',
    'In spite of the late hour, she studied all night. In spite of him, we won. He won in spite of being ill.',
    'Although she studied all night, she failed the first paper.', SEC)

add('prep_clause.in_spite_of_it',
    r"(?im)\b(?P<target>in spite of) it " + BE_AUX,
    'although', 'Grammar', 0.9,
    '“In spite of” takes a noun; before “it was” use “although”.',
    'We walked to the harbour in spite of it was getting dark.',
    'We walked to the harbour although it was getting dark. We walked on in spite of it all. In spite of it, we won.',
    'We walked to the harbour although it was getting dark.', SEC)

add('prep_clause.in_spite_of_there',
    r"(?im)\b(?P<target>in spite of) there " + BE_AUX,
    'although', 'Grammar', 0.9,
    '“In spite of” takes a noun; before “there was” use “although”.',
    'In spite of there was a long queue, the shop served everyone quickly.',
    'Although there was a long queue, the shop served everyone quickly. In spite of there being a queue, it moved fast.',
    'Although there was a long queue, the shop served everyone quickly.', SEC)

add('prep_clause.despite_subject',
    r"(?im)\b(?P<target>despite) " + SUBJ_FINITE,
    'although', 'Grammar', 0.92,
    '“Despite” takes a noun; before a subject and verb use “although”.',
    'Despite he was nervous, he gave a clear talk.',
    'Despite his nerves, he gave a clear talk. Despite him, the plan worked. Despite being nervous, he spoke well.',
    'Although he was nervous, he gave a clear talk.', SEC)

add('prep_clause.despite_it',
    r"(?im)\b(?P<target>despite) it " + BE_AUX,
    'although', 'Grammar', 0.9,
    '“Despite” takes a noun; before “it was” use “although”.',
    'We kept hiking despite it was starting to snow.',
    'We kept hiking although it was starting to snow. We kept hiking despite it all. Despite it, nothing changed.',
    'We kept hiking although it was starting to snow.', SEC)

add('prep_clause.despite_there',
    r"(?im)\b(?P<target>despite) there " + BE_AUX,
    'although', 'Grammar', 0.9,
    '“Despite” takes a noun; before “there was” use “although”.',
    'Despite there was heavy traffic, the courier arrived on time.',
    'Although there was heavy traffic, the courier arrived on time. Despite there being heavy traffic, he arrived.',
    'Although there was heavy traffic, the courier arrived on time.', SEC)

add('prep_clause.despite_you',
    r"(?im)\b(?P<target>despite|in spite of) you " + AUX_RE.replace(r"\b", r"\b"),
    'although', 'Grammar', 0.88,
    '“Despite” takes a noun; before “you are” use “although”.',
    'Despite you are new here, the team trusts your judgement.',
    'Although you are new here, the team trusts your judgement. Despite you, the plan worked. In spite of you, we won.',
    'Although you are new here, the team trusts your judgement.', SEC)

# ---- during + a clause: needs "while" ----------------------------------------------------------------------------
add('prep_clause.during_subject',
    r"(?im)\b(?P<target>during) " + SUBJ_FINITE,
    'while', 'Grammar', 0.9,
    '“During” takes a noun; before a subject and verb use “while”.',
    'Someone called during I was in the shower.',
    'Someone called during the lecture. He fell asleep during it. She sang during our break.',
    'Someone called while I was in the shower.', SEC)

add('prep_clause.during_it_you',
    r"(?im)\b(?P<target>during) (?:it|you|there) " + BE_AUX,
    'while', 'Grammar', 0.88,
    '“During” takes a noun; before a clause use “while”.',
    'The power failed during it was raining heavily.',
    'The power failed while it was raining heavily. He slept during it. During it all, nobody spoke.',
    'The power failed while it was raining heavily.', SEC)

# ---- in case of / in the event of + a clause --------------------------------------------------------------------------
add('prep_clause.in_case_of_clause',
    r"(?im)\bin case (?P<target>of )(?:I|you|we|they|he|she|it|there) " + FINITE,
    '', 'Grammar', 0.9,
    '“In case of” takes a noun; before a clause say “in case”.',
    'Take a coat in case of it gets cold later.',
    'Take a coat in case it gets cold later. In case of rain, stay inside. In case of you, we would be lost.',
    'Take a coat in case it gets cold later.', SEC)

add('prep_clause.in_the_event_of_clause',
    r"(?im)\bin the event (?P<target>of) (?:I|you|we|they|he|she|it|there) " + FINITE,
    'that', 'Grammar', 0.9,
    '“In the event of” takes a noun; before a clause say “in the event that”.',
    'Call me in the event of you need a lift.',
    'Call me in the event that you need a lift. Call me in the event of an emergency. In the event of it, we will meet.',
    'Call me in the event that you need a lift.', SEC)

# ---- although / though / even though / because / while + only a noun phrase ---------------------------------------
ASIDE = ['said', 'say', 'says', 'think', 'thinks', 'thought', 'believe', 'believes', 'feel', 'felt', 'guess', 'know', 'knew',
         'suspect', 'suppose', 'understand', 'hope', 'hoped', 'reckon', 'claim', 'claims', 'claimed', 'argue', 'argued',
         'added', 'told', 'explained', 'noted', 'admit', 'admitted', 'insist', 'insisted', 'turns', 'turned', 'seems',
         'seemed', 'appears', 'appeared', 'looks', 'looked', 'happens', 'happened']
PRON_AFTER = r"(?:I|we|you|he|she|they|it|there) (?-i:" + not_in(ASIDE) + r")"
DET1 = r"(?:the|his|her|their|my|our|your|its|a|an) " + any_word()

for key, words, pos, fixed, neg in [
    ('although', 'although', 'Although his illness, he finished the marathon.',
     'Despite his illness, he finished the marathon.',
     'Although his illness was serious, he finished the marathon. Although the team, they say, was weak, we won. Despite his illness, he finished.'),
    ('though', 'though', 'Though the weather, we enjoyed the picnic.',
     'Despite the weather, we enjoyed the picnic.',
     'Though the weather was awful, we enjoyed the picnic. Though tired, we enjoyed it. Despite the weather, we enjoyed it.'),
    ('even_though', 'even though', 'Even though the delay, we started on time.',
     'Despite the delay, we started on time.',
     'Even though the delay was long, the show started on time. Even though it was late, we stayed.'),
]:
    add('np_after_conjunction.' + key,
        r"(?im)" + START + r"(?P<target>" + words.replace(' ', r'\s+') + r")\s+(?:" + r"(?:the|his|her|their|my|our|your|its) " + any_word() + r"),\s+" + PRON_AFTER + r"\b",
        'despite', 'Grammar', 0.86,
        '“' + cap([words]) + '” needs a clause; before just a noun phrase use “despite”.',
        pos, neg, fixed, SEC)

add('np_after_conjunction.because',
    r"(?im)" + START + r"(?P<target>because)\s+(?:(?:the|his|her|their|my|our|your|its) " + any_word() + r"),\s+" + PRON_AFTER + r"\b",
    'because of', 'Grammar', 0.88,
    '“Because” needs a clause; before just a noun phrase use “because of”.',
    'Because the strike, we rebooked the flight.',
    'Because the strike lasted a week, we rebooked the flight. Because the manager, he said, was away, we waited. Because of the strike, we rebooked.',
    'Because of the strike, we rebooked the flight.', SEC)

add('np_after_conjunction.while',
    r"(?im)" + START + r"(?P<target>while)\s+(?:(?:the|his|her|their|my|our|your|its) " + any_word() + r"),\s+" + PRON_AFTER + r"\b",
    'during', 'Grammar', 0.86,
    '“While” needs a clause; before just a noun phrase use “during”.',
    'While the meeting, he checked his phone twice.',
    'While the meeting went on, he checked his phone twice. During the meeting, he checked his phone. While the cat’s away, the mice play.',
    'During the meeting, he checked his phone twice.', SEC)

add('np_after_conjunction.although_despite',
    r"(?im)\b(?P<target>(?:although|though|even though) (?P<d>despite|in spite of))\b",
    '${d}', 'Grammar', 0.9,
    'Use “despite” or “although”, not both.',
    'Although despite the delay, the show started on time.',
    'Although the delay was long, the show started on time. Despite the delay, the show started on time.',
    'Despite the delay, the show started on time.', SEC)
