"""Families B, C and K: the "to" that is missing, doubled or followed by the wrong verb form.
B  infinitive-only verb + -ing + determiner          "I want going to the beach"   -> "I want to go to the beach"
C  "to" + -ing after a to-infinitive verb             "I want to going home"        -> "I want to go home"
K  infinitive-only verb + bare verb                   "I want go home"              -> "I want to go home"
"""
import core
from core import add, g2b, alt, P1, SUBJ, SUBJ_IT, BE, ADV, DET, NEXT_K, governor_lead
from verbs import ACT, KV2 as KV

DETS = r"\s+(?:the|a|an|my|your|his|her|our|their|him|them|us|me|you|it|some|any|every)\b"

# ------------------------------------------------------------------ B: gerund after an infinitive-only verb
# (id, lead, forms, pos_a, exp_a, pos_e, exp_e, reason, negative, verbs, tail)
B_GOV = [
    ('refuse', governor_lead('refuse', 'refuses', 'refusing', 'refused', 'p1'), ['refuse', 'refuses', 'refusing', 'refused'],
     'She refuses paying the fine.', 'She refuses to pay the fine.',
     'He refused taking the offer.', 'He refused to take the offer.',
     '“Refuse” is followed by “to” and a base verb: “refuse to pay”, not “refuse paying”.',
     'She refuses to pay the fine. The refuse collection is on Monday. Take the refuse bags out.', ACT, DETS),
    ('afford', governor_lead('afford', 'affords', 'affording', 'afforded', 'p1'), ['afford', 'affords', 'affording', 'afforded'],
     "We can't afford buying the house.", "We can't afford to buy the house.",
     'They cannot afford taking the risk.', 'They cannot afford to take the risk.',
     '“Afford” is followed by “to” and a base verb: “afford to buy”, not “afford buying”.',
     "We can't afford to buy the house. The park affords a view of the lake.", ACT, DETS),
    ('plan', governor_lead('plan', 'plans', '', 'planned', 'p1') , ['plan', 'plans', 'planned'],
     'We plan visiting the city in May.', 'We plan to visit the city in May.',
     'They planned taking the train.', 'They planned to take the train.',
     '“Plan” is followed by “to” and a base verb: “plan to go”, not “plan going”.',
     'We plan to go to Rome in May. The plan going forward is clear. Plans changing the schedule are on hold.',
     ACT, DETS),
    ('hope', governor_lead('hope', 'hopes', '', 'hoped', 'p1'), ['hope', 'hopes', 'hoped'],
     'I hope seeing you soon.', 'I hope to see you soon.',
     'We hope receiving your reply soon.', 'We hope to receive your reply soon.',
     '“Hope” is followed by “to” and a base verb: “hope to see”, not “hope seeing”.',
     'I hope to see you soon. I hope seeing patients is not too tiring. Hope springs eternal.',
     ['see', 'meet', 'hear', 'receive', 'have', 'visit', 'join', 'welcome', 'speak', 'talk'],
     r"\s+(?:you|your|from)\b"),
]

def gerund_after():
    for rid, lead, forms, pa, ea, pe, ee, reason, neg, verbs, tail in B_GOV:
        for n, (alt_v, rep) in enumerate(g2b(verbs)):
            pos, exp = (pa, ea) if n == 0 else (pe, ee)
            add(f'togerund.{rid}.{"ae"[n]}', lead + r'(?P<target>(?-i:' + alt_v + r'))' + tail, 'to ' + rep,
                reason, pos, exp, neg, forms, cover=f'{rid} + -ing -> to + base verb ({"plain/doubled" if n == 0 else "silent e"})')

gerund_after()

# ------------------------------------------------------------------ C: "to" + -ing
# (id, base, -s, -ing, -ed, fixture phrase, kind) kind v: a pronoun or auxiliary before the verb; it: "it seems";
# be: "is able"; ought: a pronoun before "ought".
C_GOV = [
    ('want', 'want', 'wants', 'wanting', 'wanted', 'I want', 'v'),
    ('need', 'need', 'needs', 'needing', 'needed', 'You need', 'v'),
    ('try', 'try', 'tries', 'trying', 'tried', 'She tried', 'v'),
    ('plan', 'plan', 'plans', 'planning', 'planned', 'We plan', 'v'),
    ('decide', 'decide', 'decides', 'deciding', 'decided', 'They decided', 'v'),
    ('hope', 'hope', 'hopes', 'hoping', 'hoped', 'I hope', 'v'),
    ('like', 'like', 'likes', '', 'liked', 'I would like', 'v'),
    ('love', 'love', 'loves', '', 'loved', 'We love', 'v'),
    ('hate', 'hate', 'hates', '', 'hated', 'He hates', 'v'),
    ('prefer', 'prefer', 'prefers', 'preferring', 'preferred', 'I prefer', 'v'),
    ('wish', 'wish', 'wishes', 'wishing', 'wished', 'They wish', 'v'),
    ('begin', 'begin', 'begins', 'beginning', 'began', 'He began', 'v'),
    ('start', 'start', 'starts', 'starting', 'started', 'He started', 'v'),
    ('continue', 'continue', 'continues', 'continuing', 'continued', 'We continued', 'v'),
    ('choose', 'choose', 'chooses', 'choosing', 'chose', 'They chose', 'v'),
    ('learn', 'learn', 'learns', 'learning', 'learned', 'She learned', 'v'),
    ('forget', 'forget', 'forgets', 'forgetting', 'forgot', 'I forgot', 'v'),
    ('remember', 'remember', 'remembers', 'remembering', 'remembered', 'Please remember', 'v'),
    ('refuse', 'refuse', 'refuses', 'refusing', 'refused', 'He refused', 'v'),
    ('promise', 'promise', 'promises', 'promising', 'promised', 'I promise', 'v'),
    ('manage', 'manage', 'manages', 'managing', 'managed', 'They managed', 'v'),
    ('fail', 'fail', 'fails', 'failing', 'failed', 'He failed', 'v'),
    ('offer', 'offer', 'offers', 'offering', 'offered', 'She offered', 'v'),
    ('expect', 'expect', 'expects', 'expecting', 'expected', 'We expect', 'v'),
    ('intend', 'intend', 'intends', 'intending', 'intended', 'I intend', 'v'),
    ('attempt', 'attempt', 'attempts', 'attempting', 'attempted', 'He attempted', 'v'),
    ('deserve', 'deserve', 'deserves', 'deserving', 'deserved', 'You deserve', 'v'),
    ('threaten', 'threaten', 'threatens', 'threatening', 'threatened', 'They threatened', 'v'),
    ('arrange', 'arrange', 'arranges', 'arranging', 'arranged', 'We arranged', 'v'),
    ('pretend', 'pretend', 'pretends', 'pretending', 'pretended', 'He pretended', 'v'),
    ('afford', 'afford', 'affords', 'affording', 'afforded', 'We cannot afford', 'v'),
    ('seem', 'seem', 'seems', 'seeming', 'seemed', 'It seems', 'it'),
    ('appear', 'appear', 'appears', 'appearing', 'appeared', 'It appears', 'it'),
    ('tend', 'tend', 'tends', 'tending', 'tended', 'People tend', 'it'),
    ('ought', 'ought', '', '', '', 'You ought', 'ought'),
    ('able', 'able', '', '', '', 'She is able', 'be'),
    ('unable', 'unable', '', '', '', 'She is unable', 'be'),
    ('supposed', 'supposed', '', '', '', 'He is supposed', 'be'),
    ('afraid', 'afraid', '', '', '', 'I am afraid', 'be'),
]

C_NEG = ('I am used to going there. She is committed to making it work. I prefer walking to driving. '
         'We look forward to seeing you. Going to the party was fun. The start to following the plan was slow. '
         'He agreed to being paid. We have a commitment to making it work.')

def to_ing():
    for rid, base, s_, ing, ed, phrase, kind in C_GOV:
        forms = [f for f in (base, s_, ing, ed) if f]
        if kind == 'v':
            lead = governor_lead(base, s_, ing, ed, 'p1')
        elif kind == 'it':
            lead = SUBJ_IT + r'(?:' + alt(forms) + r')\s+'
        elif kind == 'ought':
            lead = SUBJ + r'ought\s+'
        else:
            lead = BE + base + r'\s+'
        for n, (alt_v, rep) in enumerate(g2b(ACT)):
            if n == 0:
                pos, exp = f'{phrase} to going home.', f'{phrase} to go home.'
            else:
                pos, exp = f'{phrase} to making a cake.', f'{phrase} to make a cake.'
            neg = f'{phrase} to go home. {phrase} to make a cake. ' + C_NEG
            add(f'toing.{rid}.{"ae"[n]}', lead + r'to\s+(?P<target>(?-i:' + alt_v + r'))\b', rep,
                f'After “{base} to”, use the base verb: “{phrase.split()[-1]} to go”, not “to going”.',
                pos, exp, neg, forms, conf=0.93,
                cover=f'{rid} to + -ing -> to + base verb ({"plain/doubled" if n == 0 else "silent e"})')

to_ing()

# ------------------------------------------------------------------ K: bare verb where "to" is missing
# (id, lead regex, governor group "gov" forms, phrase pos/exp, reason, negative, verbs)
def K(rid, lead, forms, pos, exp, reason, neg, verbs=KV, conf=0.9):
    alt_f = alt(forms)
    pattern = lead + r'(?P<target>(?P<gov>' + alt_f + r'))\s+(?-i:' + alt(verbs) + r')' + NEXT_K
    add(f'missingto.{rid}', pattern, '${gov} to', reason, pos, exp, neg, forms, conf=conf,
        cover=f'{rid} + bare verb -> {rid} to + verb')

FREE = r'\b'
K('want', P1, ['want', 'wants', 'wanted'], 'I want go home.', 'I want to go home.',
  '“Want” needs “to” before a verb: “want to go”.',
  'I want to go home. I want you to go home. Do you want go-karts? I want help with the report. I want read access '
  'to the repo.')
K('need', P1, ['need', 'needs', 'needed'], 'We need meet early.', 'We need to meet early.',
  '“Need” needs “to” before a verb: “need to leave”.',
  'We need to meet early. You need not leave. The needs go unmet. I need read access to the repo. He need hardly say.')
K('decide', P1, ['decide', 'decides', 'decided'], 'They decided go home.', 'They decided to go home.',
  '“Decide” needs “to” before a verb: “decided to go”.',
  'They decided to go home. The decision decides go or no-go. We decided on the plan.')
K('plan', P1, ['plan', 'plans', 'planned'], 'We plan go there next week.', 'We plan to go there next week.',
  '“Plan” needs “to” before a verb: “plan to go”.',
  'We plan to go there next week. The plan go ahead was approved. Our plan go-live is Monday.')
K('hope', P1, ['hope', 'hopes', 'hoped'], 'I hope see you soon.', 'I hope to see you soon.',
  '“Hope” needs “to” before a verb: “hope to see”.',
  'I hope to see you soon. I hope you see it. Hope springs eternal.')
K('expect', P1, ['expect', 'expects', 'expected'], 'We expect get the parts soon.', 'We expect to get the parts soon.',
  '“Expect” needs “to” before a verb: “expect to get”.',
  'We expect to get the parts soon. I expect you will come. They expect results.')
K('promise', P1, ['promise', 'promises', 'promised'], 'I promise tell you tomorrow.', 'I promise to tell you tomorrow.',
  '“Promise” needs “to” before a verb: “promise to tell”.',
  'I promise to tell you tomorrow. I promise you will love it. A promise made is a promise kept.')
K('agree', P1, ['agree', 'agrees', 'agreed'], 'We agreed meet on Monday.', 'We agreed to meet on Monday.',
  '“Agree” needs “to” before a verb: “agreed to meet”.',
  'We agreed to meet on Monday. I agree with you. They agreed on a date.')
K('refuse', P1, ['refuse', 'refuses', 'refused'], 'They refused tell me the truth.', 'They refused to tell me the truth.',
  '“Refuse” needs “to” before a verb: “refused to pay”.',
  'They refused to tell me the truth. They refused permission. The refuse collection starts early.')
K('manage', P1, ['manage', 'manages', 'managed'], 'I managed get there on time.', 'I managed to get there on time.',
  '“Manage” needs “to” before a verb: “managed to get”.',
  'I managed to get there on time. She manages the team well. They managed it together.')
K('fail', P1, ['fail', 'fails', 'failed'], 'He failed understand the question.', 'He failed to understand the question.',
  '“Fail” needs “to” before a verb: “failed to understand”.',
  'He failed to understand the question. The test failed. He failed the exam.')
K('afford', P1, ['afford', 'affords', 'afforded'], "We can't afford buy the house.", "We can't afford to buy the house.",
  '“Afford” needs “to” before a verb: “afford to buy”.',
  "We can't afford to buy the house. We can't afford the rent. The view affords a glimpse of the sea.")
K('offer', P1, ['offer', 'offers', 'offered'], 'She offered give me a lift.', 'She offered to give me a lift.',
  '“Offer” needs “to” before a verb: “offered to give”.',
  'She offered to give me a lift. She offered me a lift. They offer free shipping.')
K('wish', P1, ['wish', 'wishes', 'wished'], 'I wish see him again.', 'I wish to see him again.',
  '“Wish” needs “to” before a verb: “wish to see”.',
  'I wish to see him again. I wish you well. Make a wish come true. I wish I could go.')
K('learn', P1, ['learn', 'learns', 'learned', 'learnt'], 'I can learn speak the language.', 'I can learn to speak the language.',
  '“Learn” needs “to” before a verb: “learn to speak”.',
  'I want to learn to speak Spanish. Children learn speaking early. We learn from our mistakes.')
K('ought', SUBJ, ['ought'], 'You ought go home now.', 'You ought to go home now.',
  '“Ought” needs “to” before a verb: “ought to go”.',
  'You ought to go home now. He ought not to go.')
