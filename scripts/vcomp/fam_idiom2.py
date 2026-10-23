"""Family G (continued): "to" as a preposition before a verb, set phrases, and verbs that need a preposition."""
import core
from core import add, b2g, g2b, alt, ADV, BE, AFTER, P1, NEXT_K
from verbs import ACT, PREPV
from fam_idiom import drop_to, after_to

PRON_BE = (r"(?:I[’']m|I am|we[’']re|we are|you[’']re|you are|he[’']s|he is|she[’']s|she is)\s+(?:" + ADV + r"\s+)*")

# ---------------------------------------------------------------- be used to / get used to
after_to('idiom.be_used_to', PRON_BE + r'used\s+to\s+', ['used'], PREPV,
         'After “be used to”, use an -ing form: “I am used to eating”, not “I am used to eat”.',
         'I am used to eat late.', 'I am used to eating late.',
         'I am used to eating late. I used to eat late. The tool is used to cut wood. We are used to the noise.',
         cover='be used to + V -> be used to + Ving')
after_to('idiom.get_used_to', r'\b(?:get|gets|got|getting)\s+used\s+to\s+', ['used'], PREPV,
         'After “get used to”, use an -ing form: “get used to speaking”.',
         'You will soon get used to speak English.', 'You will soon get used to speaking English.',
         'You will soon get used to speaking English. We used to get up early. She got used to the cold.',
         cover='get used to + V -> get used to + Ving')

# ---------------------------------------------------------------- "to" is a preposition
PREP_RULES = [
    ('accustomed', r'\baccustomed\s+to\s+', ['accustomed'], 'I am accustomed to get up early.',
     'I am accustomed to getting up early.', 'I am accustomed to getting up early. He grew accustomed to the noise.',
     '“Accustomed to” is followed by an -ing form: “accustomed to getting up”.'),
    ('devoted', r'\bdevoted\s+to\s+', ['devoted'], 'She is devoted to teach children.',
     'She is devoted to teaching children.', 'She is devoted to teaching children. He is devoted to his family.',
     '“Devoted to” is followed by an -ing form: “devoted to teaching”.'),
    ('addicted', r'\baddicted\s+to\s+', ['addicted'], 'He is addicted to eat sweets.',
     'He is addicted to eating sweets.', 'He is addicted to eating sweets. She is addicted to coffee.',
     '“Addicted to” is followed by an -ing form: “addicted to eating”.'),
    ('opposed', r'\bopposed\s+to\s+', ['opposed'], 'We are opposed to take that risk.',
     'We are opposed to taking that risk.', 'We are opposed to taking that risk. They are opposed to the plan.',
     '“Opposed to” is followed by an -ing form: “opposed to taking”.'),
    ('prior', r'(?:(?-i:\bprior)|(?:^|[.!?]\s+)(?-i:Prior))\s+to\s+', ['prior'], 'Prior to make a decision, read the report.',
     'Prior to making a decision, read the report.', 'Prior to making a decision, read the report. Call us prior to the visit. This lets Prior to remember the day.',
     '“Prior to” is followed by an -ing form: “prior to making”.'),
    ('in_addition', r'\bin\s+addition\s+to\s+', ['in addition'], 'In addition to provide support, we offer training.',
     'In addition to providing support, we offer training.',
     'In addition to providing support, we offer training. In addition to the fee, there is a tax.',
     '“In addition to” is followed by an -ing form: “in addition to providing”.'),
    ('resort', core.governor_lead('resort', 'resorts', 'resorting', 'resorted', 'p1') + r'to\s+', ['resort'], 'They resort to sell the house.',
     'They resort to selling the house.', 'They resort to selling the house. They resort to force. It was a last resort to save the town.',
     '“Resort to” is followed by an -ing form: “resort to selling”.'),
    ('comes_to', r'\bwhen\s+it\s+comes\s+to\s+', ['comes to'], 'When it comes to choose a gift, ask her.',
     'When it comes to choosing a gift, ask her.', 'When it comes to choosing a gift, ask her. The bill comes to ten dollars. He comes to see his father every day.',
     '“When it comes to” is followed by an -ing form: “comes to choosing”.'),
    ('view_to', r'\bwith\s+a\s+view\s+to\s+', ['view to'], 'They met with a view to make a deal.',
     'They met with a view to making a deal.', 'They met with a view to making a deal. We have a view to the sea.',
     '“With a view to” is followed by an -ing form: “with a view to making”.'),
    ('object_to', P1 + r'object(?:s|ed)?\s+to\s+', ['object'], 'I object to give them access.',
     'I object to giving them access.', 'I object to giving them access. It is an object to hold. They object to the plan.',
     '“Object to” is followed by an -ing form: “object to giving”.'),
]
for rid, lead, forms, pos, exp, neg, reason in PREP_RULES:
    after_to(f'idiom.{rid}', lead, forms, PREPV, reason, pos, exp, neg, cover=f'{rid} to + V -> Ving')

# ---------------------------------------------------------------- set phrases
CANT = r"\b(?:can[’']t|cannot|can not|couldn[’']t|could not)\s+"
EMOTION = 'cry laugh smile wonder think feel notice worry love admire stare ask say wish hope imagine believe remember compare'.split()
drop_to('idiom.cant_help', CANT + r'help\s+', ['help'], EMOTION,
        '“Can’t help” is followed by an -ing form: “can’t help laughing”.',
        "I can't help to laugh at his jokes.", "I can't help laughing at his jokes.",
        "I can't help laughing at his jokes. I can't help you to fix it.", cover="can't help to V -> can't help Ving")
add('idiom.cant_wait_for', CANT + r'wait\s+(?P<target>for)\s+(?-i:see|meet|hear|try|start|go|get|begin|read|play|watch|visit|join|have|taste|learn|tell|give)' + NEXT_K,
    'to', '“Can’t wait” is followed by “to” and a verb: “can’t wait to see”, not “can’t wait for see”.',
    "I can't wait for see you.", "I can't wait to see you.",
    "I can't wait to see you. I can't wait for summer. I can't wait for the weekend. I can't wait for him to arrive.",
    ['wait'], conf=0.93, cover="can't wait for V -> can't wait to V")
for n, (alt_v, rep) in enumerate(g2b('see meet hear try begin read play watch visit join have get go learn tell give speak share'.split())):
    pos, exp = (("I can't wait seeing you again.", "I can't wait to see you again.") if n == 0
                else ("I can't wait having a holiday.", "I can't wait to have a holiday."))
    add(f'idiom.cant_wait_ing.{"ae"[n]}', CANT + r'wait\s+(?P<target>(?-i:' + alt_v + r'))\b', 'to ' + rep,
        '“Can’t wait” is followed by “to” and a verb: “can’t wait to see”, not “can’t wait seeing”.', pos, exp,
        "I can't wait to see you again. I can't wait for the weekend. I can't wait to have a holiday.", ['wait'],
        conf=0.93, cover="can't wait V-ing -> can't wait to V")
add('idiom.look_forward_for',
    r'(?:' + BE + r'|' + P1 + r')(?:look|looking|looked|looks)\s+forward\s+(?P<target>for)\s+(?:your|our|hearing|seeing|meeting|more|any)\b',
    'to', '“Look forward” takes “to”: “I look forward to your reply”.',
    'I am looking forward for your reply.', 'I am looking forward to your reply.',
    'I am looking forward to your reply. He looked forward for a moment, then turned back.',
    ['forward'], conf=0.93, cover='look forward for -> look forward to')
drop_to('idiom.have_difficulty',
        r'\b(?:have|has|had|having)\s+(?:no\s+|some\s+|great\s+|much\s+)?(?:difficulty|trouble|a\s+hard\s+time|a\s+difficult\s+time)\s+',
        ['difficulty', 'trouble', 'hard time', 'difficult time'], ACT,
        '“Have difficulty” is followed by an -ing form: “have difficulty understanding”.',
        'I have difficulty to understand the form.', 'I have difficulty understanding the form.',
        'I have difficulty understanding the form. It is a hard time to be a student. We have no trouble finding it.',
        cover='have difficulty/trouble to V -> Ving')
add('idiom.prefer_than', r'\bprefer(?:s|red|ring)?\s+[A-Za-z]+ing\s+(?P<target>than)\b', 'to',
    '“Prefer” compares with “to”: “prefer walking to driving”, not “prefer walking than driving”.',
    'I prefer walking than driving.', 'I prefer walking to driving.',
    'I prefer walking to driving. I prefer to walk rather than drive. I prefer spending less than that.',
    ['prefer'], conf=0.93, cover='prefer V-ing than V-ing -> prefer V-ing to V-ing')
add('idiom.discuss_to', r'\bdiscuss(?:es|ed|ing)?\s+(?P<target>to)\s+(?:me|him|her|us|them|you)\b', 'with',
    '“Discuss” is followed by “with” before a person: “discuss with you”.',
    'I will discuss to you tomorrow.', 'I will discuss with you tomorrow.',
    'I will discuss with you tomorrow. We discuss it with them. We discuss to the point.',
    ['discuss'], conf=0.92, cover='discuss to PERSON -> discuss with PERSON')
for rid, lead, forms, pos, exp, neg, reason in [
    ('ask_to', r'\b(?:ask|asks|asked|asking)\s+', ['ask'], 'She asked to him about the form.', 'She asked him about the form.',
     'She asked him about the form. She asked to see him. He asked to be left alone.', '“Ask” takes the person directly: “asked him”, not “asked to him”.'),
    ('inform_to', r'\binform(?:s|ed|ing)?\s+', ['inform'], 'Please inform to me about the delay.', 'Please inform me about the delay.',
     'Please inform me about the delay. He informed us that it was late. A note to inform the team.',
     '“Inform” takes the person directly: “inform me”, not “inform to me”.'),
    ('contact_to', P1 + r'contact(?:s|ed)?\s+', ['contact'], 'Please contact to us for details.', 'Please contact us for details.',
     'Please contact us for details. Our contact to them is good. He keeps contact to the office.',
     '“Contact” takes the person directly: “contact us”, not “contact to us”.'),
    ('join_to', r'\bjoin(?:s|ed|ing)?\s+', ['join'], 'Please join to us for lunch.', 'Please join us for lunch.',
     'Please join us for lunch. Join the pipe to them with a clamp.', '“Join” takes the person directly: “join us”, not “join to us”.')]:
    add(f'idiom.{rid}', lead + r'(?P<target>to\s+)(?:me|us|him|her|them' + ('|you' if rid != 'ask_to' else '') + r')\b', '',
        reason, pos, exp, neg, forms, conf=0.9, cover=f'{rid.split("_")[0]} to PERSON -> {rid.split("_")[0]} PERSON')
add('idiom.without_to', r'\bwithout\s+(?P<target>to\s+(?-i:' + b2g(ACT)[0] + r'))' + AFTER, b2g(ACT)[1].replace('ing', 'ing'),
    '“Without” is followed by an -ing form: “without saying”, not “without to say”.',
    'He left without to say goodbye.', 'He left without saying goodbye.',
    'He left without saying goodbye. They went with or without us. It works without to-do lists.',
    ['without'], conf=0.93, cover='without to V -> without Ving')
drop_to('idiom.how_about', r'\b(?:how|what)\s+about\s+', ['about'], ACT,
        '“How about” is followed by an -ing form: “how about going”, not “how about to go”.',
        'How about to go home?', 'How about going home?',
        'How about going home? What about the plan? How about a break?', cover='how about to V -> how about Ving')
# ---------------------------------------------------------------- verbs that need a preposition before the person
for v, forms, pos, exp, neg in [
        ('suggest', 'suggest|suggests|suggested|suggesting', 'Can you suggest me a good book?', 'Can you suggest to me a good book?',
         'Can you suggest a good book to me? She suggested the plan to us. Please suggest my name to them.'),
        ('describe', 'describe|describes|described|describing', 'Please describe me the problem.', 'Please describe to me the problem.',
         'Please describe the problem to me. He described them as kind.'),
        ('mention', 'mention|mentions|mentioned|mentioning', 'He mentioned me the price.', 'He mentioned to me the price.',
         'He mentioned the price to me. Please mention my name. Mention me in the post.')]:
    add(f'idiom.{v}_person', r'\b(?P<target>(?P<v>' + forms + r')\s+(?P<o>me|us|him|them))\s+(?:the|a|an|some|any|your|my|our|their|his|something|anything)\b',
        '${v} to ${o}', f'“{v.capitalize()}” needs “to” before the person: “{v} to me”.', pos, exp, neg, forms.split('|'),
        conf=0.88, cover=f'{v} PERSON THING -> {v} to PERSON THING')
