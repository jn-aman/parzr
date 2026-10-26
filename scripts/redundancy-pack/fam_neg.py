"""Doubled negatives with hardly, barely and scarcely that the modifiers pack does not take: "isn't hardly",
"wasn't barely", "shouldn't hardly", "didn't hardly see", "doesn't hardly work", "hardly nowhere"."""
from core import add, S, E

SEC = 'Doubled negatives with hardly / barely / scarcely'
ADV = '(?:hardly|barely|scarcely)'


def build():
    ids = []
    be = [
        ('isnt', 'is', r"isn['’]t|is not", 'It isn’t hardly a secret.', 'It is hardly a secret, and it is not a rumour.'),
        ('arent', 'are', r"aren['’]t|are not", 'The roads aren’t barely wide enough.', 'The roads are barely wide enough, and they are not new.'),
        ('wasnt', 'was', r"wasn['’]t|was not", 'It wasn’t hardly raining.', 'It was hardly raining, and it was not cold.'),
        ('werent', 'were', r"weren['’]t|were not", 'We weren’t hardly ready.', 'We were hardly ready, and we were not late.'),
        ('hasnt', 'has', r"hasn['’]t|has not", 'The town hasn’t hardly changed.', 'The town has hardly changed, and it has not grown.'),
        ('havent', 'have', r"haven['’]t|have not", 'They haven’t barely started.', 'They have barely started, and they have not stopped.'),
        ('hadnt', 'had', r"hadn['’]t|had not", 'We hadn’t scarcely sat down.', 'We had scarcely sat down, and we had not eaten.'),
        ('shouldnt', 'should', r"shouldn['’]t|should not", 'You shouldn’t hardly need a map.', 'You should hardly need a map, and you should not worry.'),
    ]
    for rid, aux, pat, pos, neg in be:
        ids.append(add(f'neg.{rid}_hardly', rf'(?im){S}(?P<target>(?:{pat}) (?P<adv>{ADV})){E}', f'{aux} ${{adv}}', 'Grammar', 0.9,
                       f'“Hardly”, “barely” and “scarcely” already make the sentence negative: say “{aux} hardly”, not “{pat.split("|")[1]} hardly”.',
                       pos, neg))
    # didn't / doesn't + hardly + verb: the verb takes the tense the auxiliary carried.
    REG_C = ('talk want work look help ask need walk play call answer listen mention expect visit wait wonder watch miss '
             'finish pass push reach wash fix guess').split()
    REG_E = 'notice recognize use care like love believe change realize imagine receive decide'.split()
    PLAIN_S = [v for v in REG_C if v not in 'watch miss finish pass push reach wash fix guess'.split()] + REG_E
    SIB = 'watch miss finish pass push reach wash fix guess'.split()
    alt = lambda L: '|'.join(sorted(L, key=lambda w: (-len(w), w)))
    DID = r"(?:didn['’]t|did not)"
    DOES = r"(?:doesn['’]t|does not)"
    ids.append(add('neg.didnt_hardly_regular',
                   rf'(?im){S}(?P<target>{DID} (?P<adv>{ADV}) (?P<v>{alt(REG_C)})){E}', '${adv} ${v}ed', 'Grammar', 0.9,
                   '“Hardly”, “barely” and “scarcely” already make the sentence negative: say “hardly talked”, not “didn’t hardly talk”.',
                   'He didn’t hardly talk to anyone.',
                   'He hardly talked to anyone, and he did not talk much.'))
    ids.append(add('neg.didnt_hardly_e',
                   rf'(?im){S}(?P<target>{DID} (?P<adv>{ADV}) (?P<v>{alt(REG_E)})){E}', '${adv} ${v}d', 'Grammar', 0.9,
                   '“Hardly”, “barely” and “scarcely” already make the sentence negative: say “hardly noticed”, not “didn’t hardly notice”.',
                   'She didn’t hardly notice the change.',
                   'She hardly noticed the change, and she did not mind.'))
    ids.append(add('neg.doesnt_hardly_regular',
                   rf'(?im){S}(?P<target>{DOES} (?P<adv>{ADV}) (?P<v>{alt(PLAIN_S)})){E}', '${adv} ${v}s', 'Grammar', 0.9,
                   '“Hardly”, “barely” and “scarcely” already make the sentence negative: say “hardly talks”, not “doesn’t hardly talk”.',
                   'He doesn’t hardly talk to anyone.',
                   'He hardly talks to anyone, and he does not talk much.'))
    ids.append(add('neg.doesnt_hardly_sibilant',
                   rf'(?im){S}(?P<target>{DOES} (?P<adv>{ADV}) (?P<v>{alt(SIB)})){E}', '${adv} ${v}es', 'Grammar', 0.9,
                   '“Hardly”, “barely” and “scarcely” already make the sentence negative: say “hardly watches”, not “doesn’t hardly watch”.',
                   'She doesn’t hardly watch the news.',
                   'She hardly watches the news, and she does not read it.'))
    irregular = [
        ('see', 'saw', 'sees', 'the sign'), ('know', 'knew', 'knows', 'the answer'), ('have', 'had', 'has', 'time to eat'),
        ('get', 'got', 'gets', 'any sleep'), ('hear', 'heard', 'hears', 'the speaker'), ('say', 'said', 'says', 'a word'),
        ('think', 'thought', 'thinks', 'about it'), ('feel', 'felt', 'feels', 'the cold'), ('speak', 'spoke', 'speaks', 'to us'),
        ('come', 'came', 'comes', 'to class'), ('go', 'went', 'goes', 'out'), ('take', 'took', 'takes', 'a break'),
        ('make', 'made', 'makes', 'a sound'), ('give', 'gave', 'gives', 'us a chance'), ('find', 'found', 'finds', 'the time'),
        ('tell', 'told', 'tells', 'a soul'), ('eat', 'ate', 'eats', 'lunch'), ('sleep', 'slept', 'sleeps', 'at night'),
        ('understand', 'understood', 'understands', 'the rules'), ('do', 'did', 'does', 'anything'),
        ('run', 'ran', 'runs', 'in winter'), ('drive', 'drove', 'drives', 'to work'), ('write', 'wrote', 'writes', 'letters'),
        ('buy', 'bought', 'buys', 'clothes'), ('leave', 'left', 'leaves', 'the house'), ('meet', 'met', 'meets', 'friends'),
        ('pay', 'paid', 'pays', 'rent'), ('keep', 'kept', 'keeps', 'receipts'), ('read', 'read', 'reads', 'books'),
    ]
    for base, past, third, obj in irregular:
        ids.append(add(f'neg.didnt_hardly_{base}',
                       rf'(?im){S}(?P<target>{DID} (?P<adv>{ADV}) {base}){E}', f'${{adv}} {past}', 'Grammar', 0.9,
                       f'“Hardly”, “barely” and “scarcely” already make the sentence negative: say “hardly {past}”, not “didn’t hardly {base}”.',
                       f'He didn’t hardly {base} {obj}.' if base != 'think' else 'He didn’t hardly think about it.',
                       f'He hardly {past} {obj}, and he did not {base} much.' if base not in ('think',) else 'He hardly thought about it, and he did not mind.'))
        if base == 'read':
            ids.append(add('neg.doesnt_hardly_read', rf'(?im){S}(?P<target>{DOES} (?P<adv>{ADV}) read){E}', '${adv} reads', 'Grammar', 0.9,
                           '“Hardly”, “barely” and “scarcely” already make the sentence negative: say “hardly reads”, not “doesn’t hardly read”.',
                           'She doesn’t hardly read books.', 'She hardly reads books, and she does not read much.'))
            continue
        ids.append(add(f'neg.doesnt_hardly_{base}',
                       rf'(?im){S}(?P<target>{DOES} (?P<adv>{ADV}) {base}){E}', f'${{adv}} {third}', 'Grammar', 0.9,
                       f'“Hardly”, “barely” and “scarcely” already make the sentence negative: say “hardly {third}”, not “doesn’t hardly {base}”.',
                       f'She doesn’t hardly {base} {obj}.' if base != 'think' else 'She doesn’t hardly think about it.',
                       f'She hardly {third} {obj}, and she does not {base} much.' if base != 'think' else 'She hardly thinks about it, and she does not mind.'))
    ids.append(add('neg.hardly_nowhere', rf'(?im){S}(?P<adv>{ADV}) (?P<target>nowhere){E}', 'anywhere', 'Grammar', 0.9,
                   '“Hardly”, “barely” and “scarcely” already make the sentence negative: say “anywhere”, not “nowhere”.',
                   'There is hardly nowhere to park.',
                   'There is hardly anywhere to park, and nowhere else to turn.'))
    return ids
