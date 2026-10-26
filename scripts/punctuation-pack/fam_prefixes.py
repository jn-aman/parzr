"""Rule builders for the prefix and fixed-form hyphens (the word lists live in fam_prefix.py)."""
import re
import core
from fam_prefix import *  # noqa: F401,F403
import fam_prefix as P


def ident(s):
    return re.sub(r'[^a-z0-9]+', '_', s.lower())


def case_flag(word):
    """Stems that are acronyms or mixed-case names keep their case in the pattern."""
    return f'(?-i:{word})' if word.isupper() or word == 'COVID' else word


def self_rules():
    seen = set()
    for line in P.SELF:
        stem, kind = line.split()
        if stem in seen:
            continue
        seen.add(stem)
        frame = 'It is about self {s}.' if kind == 'n' else 'She is very self {s}.'
        pos = frame.format(s=stem)
        fixed = frame.format(s=stem).replace('self ', 'self-')
        neg = f'It is about myself and {stem}. She values her self-{stem}.'
        core.add(f'hyphen.self_{stem}', rf'(?i)\bself(?P<target> ){stem}\b', '-', 'Punctuation', 0.92,
                 f'Write “self-{stem}” with a hyphen.', pos, neg, fixed)


def ex_rules():
    left = r'(?:my|your|his|her|their|our|the|an?|some|many|few|several)'
    for n in P.EX_NOUNS:
        core.add(f'hyphen.ex_{n}', rf'(?i)\b{left} ex(?P<target> ){n}\b', '-', 'Punctuation', 0.88,
                 f'Hyphenate the prefix: “ex-{n}”.', f'He met the ex {n} yesterday.',
                 f'He met the ex-{n} yesterday. My ex likes dogs.', f'He met the ex-{n} yesterday.')
    left = r'(?:my|your|his|her|their|our|the|some|many|few|several)'
    for n in P.EX_PLURALS:
        core.add(f'hyphen.ex_{n}', rf'(?i)\b{left} ex(?P<target> ){n}\b', '-', 'Punctuation', 0.88,
                 f'Hyphenate the prefix: “ex-{n}”.', f'We met his ex {n} yesterday.',
                 f'We met his ex-{n} yesterday. His ex lives nearby.', f'We met his ex-{n} yesterday.')


def co_rules():
    for stem in P.CO:
        core.add(f'hyphen.co_{stem}', rf'(?i)(?-i:\bco)(?P<target> ){stem}\b', '-', 'Punctuation', 0.88,
                 f'Hyphenate the prefix: “co-{stem}”.', f'She is a co {stem} of the book.',
                 f'She is a co-{stem} of the book. Smith and Co {stem} signed.', f'She is a co-{stem} of the book.')


def non_rules():
    for w in P.NON_PROPER:
        core.add(f'hyphen.non_{w.lower()}', rf'(?i)\bnon(?P<target> ){w}\b', '-', 'Punctuation', 0.92,
                 f'Hyphenate “non-” before a proper adjective: “non-{w}”.', f'It is a non {w} audience.',
                 f'It is a non-{w} audience. Their canon {w} club met.', f'It is a non-{w} audience.')
    for w in P.NON_ACRONYMS:
        core.add(f'hyphen.non_{w.lower()}_acronym', rf'(?i)\bnon(?P<target> )(?-i:{w})\b', '-', 'Punctuation', 0.92,
                 f'Hyphenate “non-” before an acronym: “non-{w}”.', f'It is a non {w} company.',
                 f'It is a non-{w} company. The canon {w} list is short.', f'It is a non-{w} company.')


def mid_rules():
    for m in P.MONTHS:
        pat = f'(?-i:{m})' if m == 'May' else m
        core.add(f'hyphen.mid_{m.lower()}', rf'(?i)\bmid(?P<target> ){pat}\b', '-', 'Punctuation', 0.92,
                 f'Hyphenate “mid-{m}”.', f'The launch is in mid {m}.',
                 f'The launch is in mid-{m}. It rained amid {m} storms.', f'The launch is in mid-{m}.')
    core.add('hyphen.mid_year', r'(?i)\bmid(?P<target> )(?:19|20)\d\d\b', '-', 'Punctuation', 0.92,
             'Hyphenate “mid-” before a year: “mid-2019”.', 'It happened in mid 2019.',
             'It happened in mid-2019. The plan is amid 2019 budgets.', 'It happened in mid-2019.')
    core.add('hyphen.mid_decade_digits', r'(?i)\bmid(?P<target> )\d0s\b', '-', 'Punctuation', 0.92,
             'Hyphenate “mid-” before a decade: “mid-30s”.', 'She is in her mid 30s.',
             'She is in her mid-30s. The band formed amid 30s nostalgia.', 'She is in her mid-30s.')
    core.add('hyphen.mid_decade_words',
             r'(?i)\bmid(?P<target> )(?:twenties|thirties|forties|fifties|sixties|seventies|eighties|nineties)\b', '-',
             'Punctuation', 0.92, 'Hyphenate “mid-” before a decade: “mid-thirties”.', 'She is in her mid thirties.',
             'She is in her mid-thirties. The band formed amid thirties nostalgia.', 'She is in her mid-thirties.')
    for n in P.MID_NOUNS:
        core.add(f'hyphen.mid_{n}', rf'(?i)\bmid(?P<target> ){n}\b', '-', 'Punctuation', 0.9,
                 f'Hyphenate “mid-{n}”.', f'It happened in mid {n}.',
                 f'It happened in mid-{n}. It rained amid {n} noise.', f'It happened in mid-{n}.')


def pre_post_rules():
    for line in P.PRE:
        stem, kind, sentence = [p.strip() for p in line.split('::')]
        pat = case_flag(stem)
        fixed = sentence.replace('pre ' + stem, 'pre-' + stem)
        core.add(f'hyphen.pre_{ident(stem)}', rf'(?i)\bpre(?P<target> ){pat}\b', '-', 'Punctuation', 0.9,
                 f'Hyphenate the prefix: “pre-{stem}”.', sentence, fixed + ' We prepare each item first.', fixed)
    core.add('hyphen.pre_year', r'(?i)\bpre(?P<target> )(?:1[5-9]|20)\d\d\b', '-', 'Punctuation', 0.9,
             'Hyphenate “pre-” before a year: “pre-1990”.', 'Rules were looser in the pre 1990 era.',
             'Rules were looser in the pre-1990 era. We prepare each 1990 item first.',
             'Rules were looser in the pre-1990 era.')
    left = r'(?:the|a|an|this|that|our|my|its|their|in|during|since|before|until|with|from|of)'
    for line in P.POST:
        stem, sentence = [p.strip() for p in line.split('::')]
        pat = case_flag(stem)
        fixed = sentence.replace('post ' + stem, 'post-' + stem)
        core.add(f'hyphen.post_{ident(stem)}', rf'(?i)\b{left} post(?P<target> ){pat}\b', '-', 'Punctuation', 0.9,
                 f'Hyphenate the prefix: “post-{stem}”.', sentence,
                 fixed + f' We will post {stem} notes tomorrow.', fixed)


def anti_pro_all_rules():
    for line in P.ANTI:
        stem, sentence = [p.strip() for p in line.split('::')]
        pat = case_flag(stem)
        fixed = sentence.replace('anti ' + stem, 'anti-' + stem)
        core.add(f'hyphen.anti_{ident(stem)}', rf'(?i)\banti(?P<target> ){pat}\b', '-', 'Punctuation', 0.9,
                 f'Hyphenate the prefix: “anti-{stem}”.', sentence, fixed + f' Many Santi {stem} fans came.', fixed)
    left = r'(?:is|are|was|were|be|been|being|very|strongly|staunchly|fiercely|a|an|the|our|their|his|her|its)'
    for line in P.PRO:
        stem, sentence = [p.strip() for p in line.split('::')]
        pat = case_flag(stem)
        fixed = sentence.replace('pro ' + stem, 'pro-' + stem)
        core.add(f'hyphen.pro_{ident(stem)}', rf'(?i)\b{left} pro(?P<target> ){pat}\b', '-', 'Punctuation', 0.88,
                 f'Hyphenate the prefix: “pro-{stem}”.', sentence, fixed + f' The pro {stem}s are waiting.', fixed)
    left = r'(?:a|an|the|our|their|this|that|my|your)'
    for line in P.ALL:
        stem, sentence = [p.strip() for p in line.split('::')]
        fixed = sentence.replace('all ' + stem, 'all-' + stem)
        core.add(f'hyphen.all_{ident(stem)}', rf'(?i)\b{left} all(?P<target> ){stem}\b', '-', 'Punctuation', 0.9,
                 f'Hyphenate “all-{stem}”.', sentence, fixed + f' We bought all {stem}s.', fixed)


def family_rules():
    after = P.IN_LAW_AFTER
    for role in P.IN_LAW_ROLES:
        core.add(f'hyphen.{role}_in_law', rf'(?i)\b{role}(?P<target> in law){after}', '-in-law', 'Punctuation', 0.94,
                 f'Write “{role}-in-law” with hyphens.', f'My {role} in law is visiting.',
                 f'My {role}-in-law is visiting. My {role} in law enforcement is visiting.',
                 f'My {role}-in-law is visiting.')
        core.add(f'hyphen.{role}s_in_law', rf'(?i)\b{role}s(?P<target> in law){after}', '-in-law', 'Punctuation', 0.94,
                 f'Write “{role}s-in-law” with hyphens.', f'Both of my {role}s in law are visiting.',
                 f'Both of my {role}s-in-law are visiting. Her {role}s in law school are visiting.',
                 f'Both of my {role}s-in-law are visiting.')
    core.add('hyphen.in_laws', r'(?i)\b(?:my|your|his|her|our|their|the) (?P<target>in laws)\b', 'in-laws', 'Punctuation',
             0.94, 'Write “in-laws” with a hyphen.', 'We visit my in laws on Sundays.',
             'We visit my in-laws on Sundays. We study the laws of the state.', 'We visit my in-laws on Sundays.')
    core.add('hyphen.parents_in_law', rf'(?i)\bparents(?P<target> in law){after}', '-in-law', 'Punctuation', 0.94,
             'Write “parents-in-law” with hyphens.', 'Her parents in law are visiting.',
             'Her parents-in-law are visiting. Her parents in law school are visiting.',
             'Her parents-in-law are visiting.')
    for role in ('president', 'governor', 'mayor', 'senator', 'prime minister', 'congressman', 'congresswoman',
                 'representative', 'chair', 'speaker', 'secretary', 'premier'):
        core.add(f'hyphen.{ident(role)}_elect',
                 rf'(?i)\b(?:the|a|an|our|new|incoming|then) {role}(?P<target> elect){after}',
                 '-elect', 'Punctuation', 0.92, f'Write “{role}-elect” with a hyphen.',
                 f'The {role} elect is speaking tonight.',
                 f'The {role}-elect is speaking tonight. We elect a {role} each year.',
                 f'The {role}-elect is speaking tonight.')
    to_be_after = r'(?:[,.;:!?)]|$|\s+(?:and|is|was|are|were|will|has|had|received|gets|looked|looks)\b)'
    for role in ('bride', 'groom', 'mother', 'father', 'mom', 'dad', 'wife', 'husband', 'parent'):
        core.add(f'hyphen.{role}_to_be',
                 rf'(?i)\b(?:the|a|my|our|her|his|your|their) {role}(?P<target> to be){to_be_after}',
                 '-to-be', 'Punctuation', 0.88, f'Write “{role}-to-be” with hyphens.', f'The {role} to be is excited.',
                 f'The {role}-to-be is excited. We want the {role} to be happy.', f'The {role}-to-be is excited.')
    for word in ('grandmother', 'grandfather', 'grandparent', 'grandparents', 'grandson', 'granddaughter', 'grandchild',
                 'grandchildren', 'grandma', 'grandpa'):
        core.add(f'hyphen.great_{word}', rf'(?i)\b(?:my|your|his|her|our|their|the late) great(?P<target> ){word}\b', '-',
                 'Punctuation', 0.9, f'Write “great-{word}” with a hyphen.', f'My great {word} was born in Ohio.',
                 f'My great-{word} was born in Ohio. She is a great teacher.', f'My great-{word} was born in Ohio.')
    for word in ('aunt', 'uncle'):
        core.add(f'hyphen.great_{word}', rf'(?i)\b(?:my|your|his|her|our|their) great(?P<target> ){word}\b', '-',
                 'Punctuation', 0.88, f'Write “great-{word}” with a hyphen.', f'My great {word} lives in Ohio.',
                 f'My great-{word} lives in Ohio. She is a great {word}.', f'My great-{word} lives in Ohio.')


def re_rules():
    for w in P.RE_VOWEL:
        core.add(f'hyphen.re_{w}', rf"(?i)(?:^|[^\w'’-])re(?P<target> ){w}\b", '-', 'Punctuation', 0.9,
                 f'Hyphenate “re-{w}”, where the prefix meets the same vowel.', f'You must re {w} the code.',
                 f'You must re-{w} the code. We answered the {w} question.', f'You must re-{w} the code.')
    for w in P.SPLIT_RE_JOIN:
        core.add(f'spelling.re_{w}', rf"(?i)(?:^|[^\w'’-])(?P<target>re {w})(?:s|ed|ing)?\b", f're{w}', 'Spelling', 0.9,
                 f'Write “re{w}” as one word.', f'Please re {w} the form.', f'Please re{w} the form. The form is in {w}.',
                 f'Please re{w} the form.')
    core.add('spelling.e_mail', r'(?i)\b(?P<target>e mail)(?:s|ed|ing)?\b', 'email', 'Spelling', 0.9,
             'Write “email” as one word.', 'Please send me an e mail.', 'Please send me an email. The e-mail arrived.',
             'Please send me an email.')


def build():
    self_rules()
    ex_rules()
    co_rules()
    non_rules()
    mid_rules()
    pre_post_rules()
    anti_pro_all_rules()
    family_rules()
    re_rules()
