"""Family A: verbs that take only an -ing complement, written with "to" and a base verb ("enjoy to read")."""
import core
from core import add, b2g, alt, SUBJ, ADV, AFTER, governor_lead
from verbs import ACT

NOT_BE_HAVE = [v for v in ACT if v not in ('be', 'have')]

# (id, mode, base, -s, -ing, -ed, verb list, reason, positive, expected, negative)
GERUND_ONLY = [
    ('enjoy', 'free', 'enjoy', 'enjoys', 'enjoying', 'enjoyed', ACT,
     '“Enjoy” is followed by an -ing form: “enjoy walking”, not “enjoy to walk”.',
     'We enjoy to walk in the hills.', 'We enjoy walking in the hills.',
     'Enjoy the show tonight. We enjoy walking in the hills. They enjoyed the trip to Paris. Enjoy to the fullest. '
     'I enjoy to read and write.'),
    ('avoid', 'free', 'avoid', 'avoids', 'avoiding', 'avoided', ACT,
     '“Avoid” is followed by an -ing form: “avoid leaving”, not “avoid to leave”.',
     'Please avoid to leave the door open.', 'Please avoid leaving the door open.',
     'Please avoid leaving the door open. We avoided the highway to save time. Avoid it to be safe. '
     'Strong cleaners should be avoided to protect the finish.'),
    ('finish', 'p1', 'finish', 'finishes', '', 'finished', ACT,
     '“Finish” is followed by an -ing form: “finish reading”, not “finish to read”.',
     'I finished to read the report yesterday.', 'I finished reading the report yesterday.',
     'I finished reading the report. A matte finish to make the table shine. Wait for one test to finish to run '
     'the other.'),
    ('suggest', 'free', 'suggest', 'suggests', 'suggesting', 'suggested', ACT,
     '“Suggest” is followed by an -ing form: “suggest waiting”, not “suggest to wait”.',
     'I suggest to wait until Monday.', 'I suggest waiting until Monday.',
     'I suggest waiting until Monday. She suggested to him that we wait. It is suggested to take a break. '
     'The results suggest to the team a new approach.'),
    ('recommend', 'free', 'recommend', 'recommends', 'recommending', 'recommended', ACT,
     '“Recommend” is followed by an -ing form: “recommend buying”, not “recommend to buy”.',
     'I recommend to buy the larger size.', 'I recommend buying the larger size.',
     'I recommend buying the larger size. It is recommended to buy the larger size. I would recommend it to anyone. '
     'It is recommend to choose the right size.'),
    ('mind', 'p1', 'mind', 'minds', 'minding', 'minded', ACT,
     '“Mind” is followed by an -ing form: “mind waiting”, not “mind to wait”.',
     "I don't mind to wait.", "I don't mind waiting.",
     "I don't mind waiting. Do you mind if I sit here? Never mind to the details. He has a mind to go home."),
    ('miss', 'p1', 'miss', 'misses', '', 'missed', ACT,
     '“Miss” is followed by an -ing form: “miss seeing”, not “miss to see”.',
     'I miss to see my friends every day.', 'I miss seeing my friends every day.',
     'I miss seeing my friends. Please give this to Miss Lee. The train will miss to the north.'),
    ('risk', 'p1', 'risk', 'risks', 'risking', 'risked', ACT,
     '“Risk” is followed by an -ing form: “risk losing”, not “risk to lose”.',
     'They risk to lose the contract.', 'They risk losing the contract.',
     'They risk losing the contract. It is a risk to take. The risk to run the plant is low.'),
    ('delay', 'p1', 'delay', 'delays', 'delaying', 'delayed', ACT,
     '“Delay” is followed by an -ing form: “delay sending”, not “delay to send”.',
     "Don't delay to send the form.", "Don't delay sending the form.",
     "Don't delay sending the form. There was a delay to start the show. A short delay to deliver the parts."),
    ('postpone', 'p1', 'postpone', 'postpones', 'postponing', 'postponed', ACT,
     '“Postpone” is followed by an -ing form: “postpone calling”, not “postpone to call”.',
     'I postponed to call him until Friday.', 'I postponed calling him until Friday.',
     'I postponed calling him until Friday. The meeting was postponed to Friday. The launch is postponed to next week.'),
    ('resist', 'p1', 'resist', 'resists', 'resisting', 'resisted', ACT,
     '“Resist” is followed by an -ing form: “resist opening”, not “resist to open”.',
     'I could not resist to open the box.', 'I could not resist opening the box.',
     'I could not resist opening the box. They resist to the end. The metal can resist to some extent.'),
    ('deny', 'p1', 'deny', 'denies', 'denying', 'denied', ACT,
     '“Deny” is followed by an -ing form: “deny taking”, not “deny to take”.',
     'He denied to take the money.', 'He denied taking the money.',
     'He denied taking the money. They deny access to all users. She denied it to me.'),
    ('imagine', 'free', 'imagine', 'imagines', 'imagining', 'imagined', ACT,
     '“Imagine” is followed by an -ing form: “imagine living”, not “imagine to live”.',
     "I can't imagine to live there.", "I can't imagine living there.",
     "I can't imagine living there. Imagine to yourself a quiet beach. He is imagined to be rich."),
    ('appreciate', 'free', 'appreciate', 'appreciates', 'appreciating', 'appreciated', ACT,
     '“Appreciate” is followed by an -ing form: “appreciate hearing”, not “appreciate to hear”.',
     'I appreciate to hear from you.', 'I appreciate hearing from you.',
     'I appreciate hearing from you. We appreciate your time to help. It would be appreciated to receive advice.'),
    ('dislike', 'free', 'dislike', 'dislikes', 'disliking', 'disliked', ACT,
     '“Dislike” is followed by an -ing form: “dislike waiting”, not “dislike to wait”.',
     'She dislikes to wait in line.', 'She dislikes waiting in line.',
     'She dislikes waiting in line. He felt a dislike to the plan. Her dislike to crowds is well known.'),
    ('detest', 'free', 'detest', 'detests', 'detesting', 'detested', ACT,
     '“Detest” is followed by an -ing form: “detest waiting”, not “detest to wait”.',
     'I detest to wait in traffic.', 'I detest waiting in traffic.',
     'I detest waiting in traffic. She detests the noise to which we are exposed.'),
    ('tolerate', 'free', 'tolerate', 'tolerates', 'tolerating', 'tolerated', ACT,
     '“Tolerate” is followed by an -ing form: “tolerate waiting”, not “tolerate to wait”.',
     "I can't tolerate to wait any longer.", "I can't tolerate waiting any longer.",
     "I can't tolerate waiting any longer. The plant tolerates frost to some degree."),
    ('anticipate', 'free', 'anticipate', 'anticipates', 'anticipating', 'anticipated', ACT,
     '“Anticipate” is followed by an -ing form: “anticipate receiving”, not “anticipate to receive”.',
     'We anticipate to receive the parts soon.', 'We anticipate receiving the parts soon.',
     'We anticipate receiving the parts soon. The tracks are anticipated to be released in May. They are anticipate '
     'to leave flowers.'),
    ('contemplate', 'free', 'contemplate', 'contemplates', 'contemplating', 'contemplated', ACT,
     '“Contemplate” is followed by an -ing form: “contemplate leaving”, not “contemplate to leave”.',
     'He contemplated to leave the company.', 'He contemplated leaving the company.',
     'He contemplated leaving the company. She contemplated to her left.'),
]

# "consider" and "feel like" need their own context (a relative clause: "the man I consider to be", a cleft: "what it
# feels like to be old").
SPECIAL = [
    ('consider', NOT_BE_HAVE,
     r'(?:\bconsidering\s+|\b(?:please|kindly|should|must|may|might|could|can|will|shall|don[’\']t)\s+(?:' + ADV +
     r'\s+)*consider\s+)', ['consider'],
     '“Consider” is followed by an -ing form: “consider buying”, not “consider to buy”.',
     'We are considering to buy a new laptop.', 'We are considering buying a new laptop.',
     'We are considering buying a new laptop. The man I consider to be the best is here. Consider to whom you send '
     'it. I consider him to have won. The face most would consider to look best.'),
    ('feel_like', ACT,
     r'(?:' + SUBJ + r'(?:feel|felt)|\b(?:I[’\']m|we[’\']re|you[’\']re|they[’\']re|he[’\']s|she[’\']s)\s+(?:' + ADV +
     r'\s+)*feeling)\s+like\s+', ['feel', 'felt', 'feeling'],
     '“Feel like” is followed by an -ing form: “feel like going”, not “feel like to go”.',
     'I feel like to go home.', 'I feel like going home.',
     'I feel like going home. What does it feel like to be old? He felt like a stranger.'),
]

def gerund_only():
    for rid, mode, base, s, ing, ed, verbs, reason, pos, exp, neg in GERUND_ONLY:
        alt_v, repl = b2g(verbs)
        lead = governor_lead(base, s, ing, ed, mode)
        forms = ' '.join([base, s, ing, ed]).split()
        pattern = lead + r'(?P<target>to\s+(?-i:' + alt_v + r'))' + AFTER
        add(f'gerund.{rid}', pattern, repl, reason, pos, exp, neg, forms, cover=f'{rid} + to + base verb -> -ing')
    for rid, verbs, lead, forms, reason, pos, exp, neg in SPECIAL:
        alt_v, repl = b2g(verbs)
        pattern = lead + r'(?P<target>to\s+(?-i:' + alt_v + r'))' + AFTER
        add(f'gerund.{rid}', pattern, repl, reason, pos, exp, neg, forms, cover=f'{rid} + to + base verb -> -ing')

gerund_only()
