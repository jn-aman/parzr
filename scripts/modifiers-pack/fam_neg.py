"""Double negatives: nothing/nobody/nowhere/none/no after a negated verb, hardly/barely with a negative, n't never,
can't hardly, and "no more" after a negative. Chat and dialect forms (ain't got no, don't got no) are left alone."""
from core import add, cover, pick, IDS

# The negated auxiliaries the base rules (grammar.negative_object_anything, grammar.negative_determiner_any) cover
# for a short list of verbs; the pack takes the other auxiliaries and the other verbs.
AUXA = r"(?:did not|do not|does not|didn['’]t|don['’]t|doesn['’]t)"
AUXB = (r"(?:can['’]t|cannot|can not|couldn['’]t|could not|won['’]t|will not|wouldn['’]t|would not|shouldn['’]t|should not|"
        r"haven['’]t|have not|hasn['’]t|has not|hadn['’]t|had not|mustn['’]t|needn['’]t)")
AUXALL = rf"(?:{AUXA}|{AUXB})"
# The auxiliaries grammar.negative_determiner_any does not list (it has can't/couldn't/did/does/do + n't or not).
AUXB2 = (r"(?:won['’]t|will not|wouldn['’]t|would not|shouldn['’]t|should not|haven['’]t|have not|hasn['’]t|has not|"
         r"hadn['’]t|had not|mustn['’]t|needn['’]t)")
BASE_DET = {'find', 'see', 'have', 'need', 'want', 'buy', 'bring', 'take', 'give', 'know', 'expect'}
APOS = "'"


def aux_for(verb):
    """The auxiliaries a rule for this verb may use without repeating a base rule (or "don't got", which the engine
    rewrites to "don't have")."""
    if verb in BASE_DET:
        return AUXB2
    if verb == 'got':
        return AUXB
    return AUXALL


def example_aux(verb):
    if verb in BASE_DET:
        return "won't"
    if verb == 'got':
        return "haven't"
    return "don't"

BASE_NOTHING = ['buy', 'see', 'hear', 'find', 'know', 'eat', 'drink', 'bring', 'take', 'give', 'do', 'want', 'need']
EXTRA_NOTHING = ['have', 'get', 'got', 'say', 'tell', 'mean', 'like', 'understand', 'remember', 'forget', 'expect', 'ask', 'hide',
                 'think', 'notice', 'learn', 'receive', 'make', 'send', 'show', 'offer', 'hold', 'keep', 'change', 'fix', 'order',
                 'read', 'write', 'feel', 'taste', 'smell', 'touch', 'spend', 'pay', 'cost', 'owe', 'miss', 'love', 'hate']

# verb -> the noun that follows "no" in an example, and the example context
NO_NOUNS = 'money|time|idea|clue|choice|option|answer|reason|problem|issue|doubt|chance|luck|sense|point|use|friends|friend|food|water|work|job|space|room|help|rights|control|interest|effect|difference|trouble|fault|business|evidence|proof|information|access|permission|authority|power|hope|plan|energy|patience|respect|trust|intention|desire|regrets|complaints|questions|problems|secrets|reasons|words|signs|plans|answers|ideas|dollars|cash|signal|service|reception|charge|battery|data|internet'
NO_VERBS = {  # verb: noun used in the example
    'have': 'money', 'got': 'time', 'get': 'signal', 'find': 'answer', 'see': 'reason', 'want': 'trouble', 'need': 'help',
    'make': 'difference', 'give': 'reason', 'do': 'harm', 'hear': 'complaints', 'know': 'clue', 'feel': 'regrets',
    'expect': 'help', 'buy': 'food', 'bring': 'water', 'ask': 'questions', 'show': 'interest', 'offer': 'help',
    'keep': 'secrets', 'hold': 'hope', 'spend': 'money', 'pay': 'attention', 'receive': 'answer', 'accept': 'excuses',
}
NO_NOUNS = NO_NOUNS + '|harm|attention|excuses'


def build():
    # ---- nothing
    ids = []
    for v in BASE_NOTHING:
        ids.append(add(
            f'nothing_cant_{v}', rf"(?i)\b{AUXB} {v} (?P<target>nothing)\b", 'anything', 'Grammar', 0.93,
            'Two negatives cancel each other out in standard English: after a negative verb use “anything”.',
            f"They can't {v} nothing about it.", f"They can't {v} anything about it. I {v} nothing about it."))
    for v in EXTRA_NOTHING:
        ids.append(add(
            f'nothing_{v}', rf"(?i)\b{AUXB if v == 'got' else AUXALL} {v} (?P<target>nothing)\b", 'anything', 'Grammar', 0.93,
            'Two negatives cancel each other out in standard English: after a negative verb use “anything”.',
            f"They {example_aux(v) if v == 'got' else chr(100) + 'on' + APOS + 't'} {v} nothing about it.",
            f"They {example_aux(v) if v == 'got' else chr(100) + 'on' + APOS + 't'} {v} anything about it. I {v} nothing about it."))
    cover('Double negatives', 'negated verb + nothing: the base covers did/do/does (n\'t) + buy/see/hear/find/know/eat/drink/bring/take/give/do/want/need; the pack adds can\'t/couldn\'t/won\'t/wouldn\'t/shouldn\'t/haven\'t/hasn\'t/hadn\'t with those verbs, and every auxiliary with have/get/got/say/tell/mean/like/understand/remember/forget/expect/ask/hide/think/notice/learn/receive/make/send/show/offer/hold/keep/change/fix/order/read/write/feel/taste/smell/touch/spend/pay/cost/owe/miss/love/hate; "ain\'t got nothing" and "don\'t got nothing" are dialect/chat and are left', ids)

    # ---- nobody / no one
    ids = []
    for v in ['see', 'know', 'tell', 'trust', 'hear', 'meet', 'call', 'ask', 'hurt', 'blame', 'want', 'need', 'like', 'love',
              'invite', 'help', 'bother', 'have', 'bring', 'expect', 'find', 'give', 'show', 'owe', 'fear', 'blame']:
        if f'mod.nobody_{v}' in IDS:
            continue
        ids.append(add(
            f'nobody_{v}', rf"(?i)\b{AUXALL} {v} (?P<target>nobody)\b", 'anybody', 'Grammar', 0.93,
            'Two negatives cancel each other out in standard English: after a negative verb use “anybody”.',
            f"We don't {v} nobody here.", f"We don't {v} anybody here. Nobody here knows."))
        ids.append(add(
            f'noone_{v}', rf"(?i)\b{aux_for(v)} {v} (?P<target>no one)\b", 'anyone', 'Grammar', 0.93,
            'Two negatives cancel each other out in standard English: after a negative verb use “anyone”.',
            f"We {example_aux(v) if v in BASE_DET else 'can' + APOS + 't'} {v} no one here.",
            f"We {example_aux(v) if v in BASE_DET else 'can' + APOS + 't'} {v} anyone here. No one here knows."))
    cover('Double negatives', 'negated verb + nobody / no one (see, know, tell, trust, hear, meet, call, ask, hurt, blame, want, need, like, love, invite, help, bother, have, bring, expect, find, give, show, owe, fear); base grammar.never_anyone covers "never <perfect participle> no one"', ids)

    # ---- nowhere
    ids = []
    for v, obj in [('go', ''), ('find', ' it'), ('see', ' it'), ('get', ''), ('live', ''), ('stay', ''), ('sleep', ''),
                   ('run', ''), ('hide', ''), ('look', ''), ('put', ' it'), ('park', ''), ('buy', ' it'), ('send', ' it'),
                   ('take', ' it'), ('go', ' it')]:
        key = v + ('_obj' if obj else '')
        if f'mod.nowhere_{key}' in IDS:
            continue
        ids.append(add(
            f'nowhere_{key}', rf"(?i)\b{AUXALL} {v}{obj} (?P<target>nowhere)\b", 'anywhere', 'Grammar', 0.93,
            'Two negatives cancel each other out in standard English: after a negative verb use “anywhere”.',
            f"We can't {v}{obj} nowhere in this town.", f"We can't {v}{obj} anywhere in this town. There is nowhere to go."))
    ids.append(add(
        'nowhere_going', rf"(?i)\b(?:isn['’]t|aren['’]t|wasn['’]t|weren['’]t|am not|is not|are not|was not|were not) going (?P<target>nowhere)\b",
        'anywhere', 'Grammar', 0.9, 'Two negatives cancel each other out in standard English: after a negative verb use “anywhere”.',
        'The car is not going nowhere without a new battery.', 'The car is not going anywhere without a new battery. The road goes nowhere.'))
    cover('Double negatives', 'negated verb + nowhere (go, find it, see it, get, live, stay, sleep, run, hide, look, put it, park, buy it, send it, take it; "is not going nowhere")', ids)

    # ---- none
    ids = []
    for v in ['have', 'want', 'need', 'get', 'got', 'see', 'know', 'like', 'find', 'take', 'give', 'hear']:
        a = "haven't" if v == 'got' else "don't"
        ids.append(add(
            f'none_{v}', rf"(?i)\b{AUXALL if v != 'got' else AUXB} {v} (?P<target>none)(?:[.!?,;:)\n\"”]|\s*$)", 'any', 'Grammar', 0.93,
            'Two negatives cancel each other out in standard English: after a negative verb use “any”.',
            f"I {a} {v} none.", f"I {a} {v} any. I {v} none of them. None of us {v} it."))
    cover('Double negatives', 'negated verb + none at the end of the clause (have, want, need, get, got, see, know, like, find, take, give, hear)', ids)

    # ---- no + noun
    ids = []
    for v, noun in NO_VERBS.items():
        # the base rule covers: AUXA + find/see/have/need/want/buy/bring/take/give/know/expect + (optional adjective) + one word
        aux = aux_for(v)
        ex_aux = example_aux(v)
        ids.append(add(
            f'no_noun_{v}', rf"(?i)\b{aux} {v} (?P<target>no) (?:{NO_NOUNS})\b", 'any', 'Grammar', 0.92,
            'Two negatives cancel each other out in standard English: after a negative verb use “any”.',
            f"They {ex_aux} {v} no {noun} here.", f"They {ex_aux} {v} any {noun} here. They {v} no {noun} here."))
    cover('Double negatives', 'negated verb + "no" + noun (have, got, get, find, see, want, need, make, give, do, hear, know, feel, expect, buy, bring, ask, show, offer, keep, hold, spend, pay, receive, accept); "take no for an answer" and "say no to" are never touched', ids)

    # ---- hardly / barely / scarcely with a negative word
    ids = []
    for adv in ['hardly', 'barely', 'scarcely']:
        for neg, fix, ex_pos, ex_neg in [
            ('never', 'ever', f'We {adv} never see them.', f'We {adv} ever see them. We never see them.'),
            ('nothing', 'anything', f'There was {adv} nothing left.', f'There was {adv} anything left. There was nothing left.'),
            ('nobody', 'anybody', f'{adv.capitalize()} nobody came to the talk.', f'{adv.capitalize()} anybody came to the talk. Nobody came.'),
            ('no one', 'anyone', f'{adv.capitalize()} no one answered the door.', f'{adv.capitalize()} anyone answered the door. No one answered.'),
            ('none', 'any', f'We had {adv} none left.', f'We had {adv} any left. We had none left.'),
        ]:
            ids.append(add(
                f'{adv}_{neg.replace(" ", "")}', rf"(?i)\b{adv} (?P<target>{neg})\b", fix, 'Grammar', 0.93,
                f'“{adv.capitalize()}” is already negative: use “{fix}”, not “{neg}”.', ex_pos, ex_neg))
        ids.append(add(
            f'{adv}_no_noun', rf"(?i)\b{adv} (?P<target>no) (?:{NO_NOUNS})\b", 'any', 'Grammar', 0.93,
            f'“{adv.capitalize()}” is already negative: use “any”, not “no”.',
            f'We had {adv} no time to talk.', f'We had {adv} any time to talk. We had no time to talk.'))
    for adv in ['rarely', 'seldom']:
        ids.append(add(
            f'{adv}_never', rf"(?i)\b{adv} (?P<target>never)\b", 'ever', 'Grammar', 0.93,
            f'“{adv.capitalize()}” is already negative: use “ever”, not “never”.',
            f'They {adv} never call.', f'They {adv} ever call. They never call.'))
    cover('Double negatives', 'hardly/barely/scarcely + never/nothing/nobody/no one/none/no + noun, rarely/seldom never (hardly never -> hardly ever ...)', ids)

    # ---- can't hardly
    ids = []
    for neg, pos_form, ex_pos, ex_neg in [
        (r"can['’]t|cannot|can not", 'can', "I can't hardly wait for the weekend.", 'I can hardly wait for the weekend. I cannot wait.'),
        (r"couldn['’]t|could not", 'could', "She couldn't barely hear him.", 'She could barely hear him. She could not hear him.'),
        (r"won['’]t|will not", 'will', "He won't hardly notice the change.", 'He will hardly notice the change. He will not notice.'),
        (r"wouldn['’]t|would not", 'would', "It wouldn't scarcely matter.", 'It would scarcely matter. It would not matter.'),
    ]:
        ids.append(add(
            f'{pos_form}t_hardly', rf"(?i)\b(?P<target>(?:{neg}) (?P<adv>hardly|barely|scarcely))\b", f'{pos_form} ${{adv}}', 'Grammar', 0.93,
            '“Hardly”, “barely” and “scarcely” are negative already: drop the second negative (“can hardly”, not “can’t hardly”).',
            ex_pos, ex_neg))
    ids.append(add(
        'dont_hardly', r"(?i)\b(?P<target>(?P<s>I|we|you|they) (?:do not|don['’]t) (?P<adv>hardly|barely|scarcely))\b", '${s} ${adv}', 'Grammar', 0.9,
        '“Hardly”, “barely” and “scarcely” are negative already: say “I hardly know”, not “I don’t hardly know”.',
        "They don't hardly know each other.", 'They hardly know each other. They do not know each other.'))
    cover('Double negatives', "can't/couldn't/won't/wouldn't + hardly/barely/scarcely, and I/we/you/they don't hardly ... (he/she doesn't hardly needs a verb change and is left)", ids)

    # ---- n't never
    ids = []
    for aux, ex, subj, rest in [
        ("didn['’]t", "didn't", 'The manager', 'answer us.'), ("don['’]t", "don't", 'The managers', 'answer us.'),
        ("doesn['’]t", "doesn't", 'The manager', 'answer us.'), ("can['’]t", "can't", 'The managers', 'answer us.'),
        ("couldn['’]t", "couldn't", 'The manager', 'answer us.'), ("won['’]t", "won't", 'The managers', 'answer us.'),
        ("wouldn['’]t", "wouldn't", 'The manager', 'answer us.'), ("shouldn['’]t", "shouldn't", 'The managers', 'answer us.'),
        ("haven['’]t", "haven't", 'The managers', 'answered us.'), ("hasn['’]t", "hasn't", 'The manager', 'answered us.'),
        ("hadn['’]t", "hadn't", 'The manager', 'answered us.'), ("isn['’]t", "isn't", 'The manager', 'available.'),
        ("aren['’]t", "aren't", 'The managers', 'available.'), ("wasn['’]t", "wasn't", 'The manager', 'available.'),
        ("weren['’]t", "weren't", 'The managers', 'available.')]:
        ids.append(add(
            f'{ex.replace(chr(39), "")}_never', rf"(?i)\b{aux} (?P<target>never)\b", 'ever', 'Grammar', 0.9,
            'Two negatives cancel each other out: after a negative verb use “ever”.',
            f"{subj} {ex} never {rest}", f"{subj} {ex} ever {rest} It never rains here.")) 
    cover('Double negatives', "n't never (didn't never, can't never, haven't never ... -> ever)", ids)

    # ---- no more / anymore
    ids = []
    # want/need/have/take/buy/give/know/see: grammar.negative_determiner_any already turns "no" into "any" there
    for v, ex in [('get', "They didn't get no more letters."),
                  ('eat', "I can't eat no more sweets."),
                  ('say', "She couldn't say no more than that."), ('hear', "I didn't hear no more noise."),
                  ('do', "You can't do no more today."), ('tell', "He wouldn't tell no more."),
                  ('ask', "I won't ask no more questions.")]:
        ids.append(add(
            f'no_more_{v}', rf"(?i)(?:n['’]t|\bnot) {v} (?P<target>no more)\b", 'any more', 'Grammar', 0.9,
            'Two negatives cancel each other out: after a negative verb use “any more”.',
            ex, ex.replace('no more', 'any more') + ' There is no more of it.'))
    for v, ex in [('live', "She doesn't live here no more."), ('work', "He doesn't work there no more."),
                  ('love', "I don't love you no more."), ('care', "They don't care no more."),
                  ('go', "We do not go there no more."), ('come', "He doesn't come by no more."),
                  ('trust', "I can't trust him no more."), ('talk', "They don't talk no more."),
                  ('stay', "She doesn't stay late no more."), ('play', "The kids don't play outside no more."),
                  ('visit', "We don't visit them no more."), ('matter', "It doesn't matter no more."),
                  ('hurt', "It doesn't hurt no more."), ('worry', "I won't worry no more."),
                  ('wait', "We can't wait no more."), ('smoke', "He doesn't smoke no more."),
                  ('bother', "It doesn't bother me no more."), ('belong', "That does not belong to me no more."),
                  ('exist', "That shop doesn't exist no more."), ('help', "It won't help us no more.")]:
        ids.append(add(
            f'no_more_end_{v}',
            rf"(?i)(?:n['’]t|\bnot) {v}(?: [A-Za-z’']+){{0,3}} (?P<target>no more)(?:[.!?,;:)\n\"”]|\s*$)", 'anymore', 'Grammar', 0.9,
            'Two negatives cancel each other out: after a negative verb use “anymore”.',
            ex, ex.replace('no more', 'anymore') + ' There is no more of it.'))
    cover('Double negatives', 'no more after a negative verb: "do not want no more" -> any more; "does not live here no more" -> anymore', ids)
