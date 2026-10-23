"""Family E: governor + person + bare verb, where "to" is missing ("I want you go" -> "I want you to go"),
and family F: "suggest me to go" -> "suggest that I go", "want that you go" -> "want you to go"."""
import core
from core import add, alt, P1, P1_NY, SUBJ, ADV, NEXT_K
from verbs import KV2 as KV, SAFE

PERSON = 'me|him|her|us|them|you'
THING = 'me|him|her|us|them|you|it'
WOULD = r'\b(?:I|we|they|he|she)(?:[’\']d|\s+would)\s+(?:' + ADV + r'\s+)*'

# id, lead, forms, objects, positive, expected, negative, example in the reason
E_LIST = [
    ('allow', r'\b(?:allow|allows|allowed|allowing)\s+', ['allow', 'allows', 'allowed', 'allowing'], THING,
     'They allowed us enter the building.', 'They allowed us to enter the building.',
     'They allowed us to enter the building. They allowed access to the building. Allow me a minute.',
     'allow me to enter'),
    ('want', P1_NY + r'(?:want|wants|wanted)\s+', ['want', 'wants', 'wanted'], PERSON,
     'I want you come with me.', 'I want you to come with me.',
     'I want you to come with me. The things you want do not exist. What you want you get.',
     'want you to come'),
    ('need', P1_NY + r'(?:need|needs|needed)\s+', ['need', 'needs', 'needed'], PERSON,
     'We need you come early.', 'We need you to come early.',
     'We need you to come early. The need you have is real. Everything you need go with you.',
     'need you to come'),
    ('expect', P1_NY + r'(?:expect|expects|expected)\s+', ['expect', 'expects', 'expected'], PERSON,
     'I expect them follow the rules.', 'I expect them to follow the rules.',
     'I expect them to follow the rules. I expect you will pay. They expect him there.',
     'expect them to follow'),
    ('force', r'\b(?:force|forces|forced|forcing)\s+', ['force', 'forces', 'forced', 'forcing'], THING,
     'Nothing can force me tell the truth.', 'Nothing can force me to tell the truth.',
     'Nothing can force me to tell the truth. The force you exert is large.', 'force me to tell'),
    ('enable', r'\b(?:enable|enables|enabled|enabling)\s+', ['enable', 'enables', 'enabled', 'enabling'], THING,
     'This tool enables you create the report sooner.', 'This tool enables you to create the report sooner.',
     'This tool enables you to create the report sooner. Enable them in the settings.', 'enable you to create'),
    ('encourage', r'\b(?:encourage|encourages|encouraged|encouraging)\s+',
     ['encourage', 'encourages', 'encouraged', 'encouraging'], PERSON,
     'We encourage you try it.', 'We encourage you to try it.',
     'We encourage you to try it. We encourage them.', 'encourage you to try'),
    ('cause', P1_NY + r'(?:cause|causes|caused)\s+', ['cause', 'causes', 'caused'], THING,
     'Heat can cause them lose the coating.', 'Heat can cause them to lose the coating.',
     'Heat can cause them to lose the coating. The cause you serve is noble.', 'cause them to lose'),
    ('invite', P1_NY + r'(?:invite|invites|invited)\s+', ['invite', 'invites', 'invited'], PERSON,
     'We invite you join us for dinner.', 'We invite you to join us for dinner.',
     'We invite you to join us for dinner. Send the invite you get to everyone.', 'invite you to join'),
    ('persuade', r'\b(?:persuade|persuades|persuaded|persuading)\s+', ['persuade', 'persuades', 'persuaded', 'persuading'], PERSON,
     'I could persuade him join the team.', 'I could persuade him to join the team.',
     'I could persuade him to join the team. She tried to persuade me.', 'persuade him to join'),
    ('convince', r'\b(?:convince|convinces|convinced|convincing)\s+', ['convince', 'convinces', 'convinced', 'convincing'], PERSON,
     'Nothing will convince them join the team.', 'Nothing will convince them to join the team.',
     'Nothing will convince them to join the team. They convinced me that it was safe.', 'convince them to join'),
    ('urge', P1_NY + r'(?:urge|urges|urged)\s+', ['urge', 'urges', 'urged'], PERSON,
     'We urge you read the notice.', 'We urge you to read the notice.',
     'We urge you to read the notice. There is an urge you feel to run.', 'urge you to read'),
    ('remind', r'\b(?:remind|reminds|reminded|reminding)\s+', ['remind', 'reminds', 'reminded', 'reminding'], PERSON,
     'Please remind me bring the keys.', 'Please remind me to bring the keys.',
     'Please remind me to bring the keys. A reminder you get is helpful.', 'remind me to bring'),
    ('permit', P1_NY + r'(?:permit|permits|permitted)\s+', ['permit', 'permits', 'permitted'], PERSON,
     'They will not permit us enter the building.', 'They will not permit us to enter the building.',
     'They will not permit us to enter the building. You need a permit you show at the gate.', 'permit us to enter'),
    ('order', P1_NY + r'(?:order|orders|ordered)\s+', ['order', 'orders', 'ordered'], PERSON,
     'He ordered them wait outside.', 'He ordered them to wait outside.',
     'He ordered them to wait outside. We order them online. The order you place is shipped.', 'order them to wait'),
    ('teach', r'\b(?:teach|teaches|taught|teaching)\s+', ['teach', 'teaches', 'taught', 'teaching'], PERSON,
     'My mother taught me speak the language.', 'My mother taught me to speak the language.',
     'My mother taught me to speak the language. She taught them Spanish.', 'teach me to speak'),
    ('instruct', r'\b(?:instruct|instructs|instructed|instructing)\s+', ['instruct', 'instructs', 'instructed', 'instructing'], PERSON,
     'I instructed them wait outside.', 'I instructed them to wait outside.',
     'I instructed them to wait outside. I instructed them in the method.', 'instruct them to wait'),
    ('compel', r'\b(?:compel|compels|compelled|compelling)\s+', ['compel', 'compels', 'compelled', 'compelling'], PERSON,
     'The law compels us follow the rules.', 'The law compels us to follow the rules.',
     'The law compels us to follow the rules. It was a compelling story.', 'compel us to follow'),
    ('oblige', r'\b(?:oblige|obliges|obliged|obliging)\s+', ['oblige', 'obliges', 'obliged', 'obliging'], PERSON,
     'Duty obliges me stay.', 'Duty obliges me to stay.',
     'Duty obliges me to stay. He was obliged to stay. They were very obliging.', 'oblige me to stay'),
    ('get', P1_NY + r'(?:get|gets|got)\s+', ['get', 'gets', 'got'], PERSON,
     'I will get them meet you there.', 'I will get them to meet you there.',
     'I will get them to meet you there. I get you. We got them there on time.', 'get them to meet'),
    ('would_like', WOULD + r'(?:like|love|prefer|hate)\s+', ['like', 'love', 'prefer', 'hate'], PERSON,
     "I'd like you come with me.", "I'd like you to come with me.",
     "I'd like you to come with me. Would you like them there? I would love you.", 'like you to come'),
]

def person_to():
    for rid, lead, forms, objs, pos, exp, neg, example in E_LIST:
        pattern = lead + r'(?P<target>(?P<o>' + objs + r'))\s+(?-i:' + alt(KV) + r')' + NEXT_K
        add(f'objto.{rid}', pattern, '${o} to',
            f'After “{forms[0]}” and a person, the verb needs “to”: “{example}”.',
            pos, exp, neg, forms, conf=0.9, cover=f'{rid} + object + bare verb -> object + to + verb')

person_to()

# ---------------------------------------------------------------- F
THAT_VERBS = ('come go tell send help give call check join meet take bring show share explain visit write listen '
              'stay leave pay stop start read review be fix finish wait').split()
for pron, obj, label in (('me', 'I', 'I'), ('us', 'we', 'we'), ('him', 'he', 'he'), ('her', 'she', 'she'),
                         ('them', 'they', 'they'), ('you', 'you', 'you')):
    add(f'suggest_me.{pron}',
        r'\b(?:suggest|suggests|suggested|suggesting)\s+(?P<target>' + pron + r'\s+to)\s+(?-i:' + alt(SAFE) + r')\b',
        f'that {obj}',
        f'“Suggest” does not take “{pron} to” and a verb: “suggested that {obj} go”.',
        f'He suggested {pron} to go home early.', f'He suggested that {obj} go home early.',
        f'He suggested that {obj} go home early. She suggested {pron} to the committee. They suggest to {pron} that we wait.',
        ['suggest', 'suggests', 'suggested', 'suggesting'], conf=0.88, cover=f'suggest {pron} to V -> suggest that {obj} V')

for pron, obj in (('I', 'me'), ('you', 'you'), ('we', 'us'), ('they', 'them')):
    add(f'want_that.{pron.lower()}',
        SUBJ + r'(?:want|wants|wanted|need|needs|needed)\s+(?P<target>that\s+' + pron + r')\s+(?-i:' + alt(THAT_VERBS) + r')' + NEXT_K,
        f'{obj} to',
        f'After “want” or “need”, use a person and “to”: “want {obj} to go”, not “want that {pron} go”.',
        f'She wants that {pron} come early.' if pron not in ('I',) else 'She wants that I come early.',
        f'She wants {obj} to come early.',
        f'She wants {obj} to come early. The thing she wants that {pron} have is a pen.',
        ['want', 'wants', 'wanted', 'need', 'needs', 'needed'], conf=0.88,
        cover=f'want that {pron} V -> want {obj} to V')
