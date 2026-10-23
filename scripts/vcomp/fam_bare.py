"""Family D: bare infinitive where "to" does not belong (make/let/hear + object, modals, do-support, had better,
would rather, why not), and family E: object + verb where "to" is missing ("want you go")."""
import core
from core import add, alt, P1, SUBJ, ADV, NEXT_K, PRON, CLAUSE
from verbs import ACT, KV

# verbs after which "to" is clearly the infinitive marker (idioms such as "made to order" are not in the list)
BV = [v for v in ACT if v not in ('order', 'measure', 'taste', 'scale', 'fit', 'size', 'print')]
VERB_ALT = '(?-i:' + alt(BV) + ')'
OBJ = r'(?:me|him|her|us|them|you|everyone|everybody|someone|somebody|anyone|anybody)'

# ---------------------------------------------------------------- D
add('bare.make_obj', r'\b(?:make|makes|made|making)\s+' + OBJ + r'\s+(?P<target>to\s+)' + VERB_ALT + r'\b', '',
    '“Make” takes the bare verb: “make him leave”, not “make him to leave”.',
    'The noise made him to leave early.', 'The noise made him leave early.',
    'The noise made him leave early. We made it to see the show. She was made to leave. They make them to order. '
    'Make it to the airport by noon.',
    ['make', 'makes', 'made', 'making'], cover='make + object + to + verb')
add('bare.let_obj', r'\blet(?:s|ting)?\s+(?:' + OBJ + r'|it)\s+(?P<target>to\s+)' + VERB_ALT + r'\b', '',
    '“Let” takes the bare verb: “let me go”, not “let me to go”.',
    'Please let me to know your answer.', 'Please let me know your answer.',
    'Please let me know your answer. They let him go to the store. Let it go to waste. Houses let to students.',
    ['let', 'lets', 'letting'], cover='let + object + to + verb')
add('bare.lets_to', r'\blet[’\']s\s+(?P<target>to\s+)' + VERB_ALT + r'\b', '',
    '“Let’s” is followed by the bare verb: “let’s go”, not “let’s to go”.',
    "Let's to start the meeting.", "Let's start the meeting.",
    "Let's start the meeting. Let's go to the store. Let's talk to Anna.", ["let's", 'let’s'], cover="let's + to + verb")
add('bare.hear_obj',
    r'\b(?:hear|hears|heard|hearing)\s+' + OBJ + r'\s+(?P<target>to\s+)(?-i:say|speak|talk|sing|shout|cry|scream|laugh|whisper|call|tell|ask|mention|complain|announce|play)\b',
    '', '“Hear” takes the bare verb: “heard him say”, not “heard him to say”.',
    'I never heard her to say that.', 'I never heard her say that.',
    'I never heard her say that. We heard them sing. I heard her to be a good teacher.',
    ['hear', 'hears', 'heard', 'hearing'], cover='hear + object + to + verb')

MODALS = [('can', 'She can to swim well.', 'She can swim well.'),
          ('could', 'He could to reach it.', 'He could reach it.'),
          ('may', 'You may to leave now.', 'You may leave now.'),
          ('might', 'They might to come late.', 'They might come late.'),
          ('must', 'We must to finish today.', 'We must finish today.'),
          ('shall', 'We shall to see.', 'We shall see.'),
          ('should', 'You should to ask first.', 'You should ask first.'),
          ('will', 'I will to call you tomorrow.', 'I will call you tomorrow.'),
          ('would', 'She would to help if she could.', 'She would help if she could.')]
for m, pos, exp in MODALS:
    add(f'bare.modal_{m}', CLAUSE + r'(?:I|you|we|they|he|she|it)\s+(?:' + ADV + r'\s+)*' + m + r'\s+(?P<target>to\s+)' + VERB_ALT + r'\b', '',
        f'“{m.capitalize()}” is followed by the bare verb, without “to”.', pos, exp,
        f'{exp} The ability to swim well is useful. A can to hold the paint is on the shelf. His will to live was strong. '
        f'I could not wait to see you.',
        [m], cover=f'{m} + to + verb')
add('bare.contracted_will', r'\b(?:I|you|we|they|he|she|it)[’\']ll\s+(?P<target>to\s+)' + VERB_ALT + r'\b', '',
    '“’ll” is followed by the bare verb: “I’ll call”, not “I’ll to call”.',
    "I'll to call you tomorrow.", "I'll call you tomorrow.",
    "I'll call you tomorrow. We'll go to the park. They'll talk to Anna.", ["'ll", '’ll'], cover="'ll + to + verb")
add('bare.negative_modal',
    r'\b(?:I|you|we|they|he|she|it)\s+(?P<m>can[’\']t|cannot|can not|couldn[’\']t|won[’\']t|wouldn[’\']t|shouldn[’\']t|mustn[’\']t|shan[’\']t)\s+(?P<target>to\s+)' + VERB_ALT + r'\b',
    '', 'A negative modal is followed by the bare verb: “can’t go”, not “can’t to go”.',
    "We can't to leave before noon.", "We can't leave before noon.",
    "We can't leave before noon. I can't wait to see you. They won't talk to him.",
    ["can't", 'can’t', 'cannot', 'can not', "couldn't", "won't", "wouldn't", "shouldn't", "mustn't", "shan't",
     'couldn’t', 'won’t', 'wouldn’t', 'shouldn’t', 'mustn’t', 'shan’t'], cover="can't / won't ... + to + verb")
add('bare.do_support',
    r'\b(?:I|you|we|they|he|she|it|people)\s+(?:' + ADV + r'\s+)*(?:do not|does not|did not|don[’\']t|doesn[’\']t|didn[’\']t)\s+(?P<target>to\s+)' + VERB_ALT + r'\b',
    '', '“Do”, “does” and “did” are followed by the bare verb: “I didn’t go”, not “I didn’t to go”.',
    "I didn't to go there.", "I didn't go there.",
    "I didn't go there. I don't want to go. She does not like to wait. We did not talk to him.",
    ['do not', 'does not', 'did not', "don't", "doesn't", "didn't", 'don’t', 'doesn’t', 'didn’t'], cover="do/does/did + not + to + verb")
add('bare.had_better', r'\b(?:had|[’\']d)\s+better\s+(?P<target>to\s+)' + VERB_ALT + r'\b', '',
    '“Had better” is followed by the bare verb: “you had better go”, not “had better to go”.',
    'You had better to leave now.', 'You had better leave now.',
    'You had better leave now. It is better to leave now. I would feel better to know.',
    ['better'], cover='had better + to + verb')
add('bare.would_rather', r'\b(?:would|[’\']d)\s+(?:' + ADV + r'\s+)*rather\s+(?P<target>to\s+)' + VERB_ALT + r'\b', '',
    '“Would rather” is followed by the bare verb: “I’d rather go”, not “I’d rather to go”.',
    "I'd rather to stay home tonight.", "I'd rather stay home tonight.",
    "I'd rather stay home tonight. I would rather not go. He would rather talk to her.",
    ['rather'], cover='would rather + to + verb')
add('bare.why_not', r'\bwhy\s+not\s+(?P<target>to\s+)' + VERB_ALT + r'\b', '',
    '“Why not” is followed by the bare verb: “why not ask”, not “why not to ask”.',
    'Why not to ask her directly?', 'Why not ask her directly?',
    'Why not ask her directly? He asked why not to the park. Why not both?', ['why not'], cover='why not + to + verb')

