"""Apostrophes: "its'", pronouns with a stray apostrophe, missing possessive apostrophes in fixed frames ("last years
budget", "two weeks notice", "mothers day", "a stones throw"), plural acronyms and family names, verbs given an
apostrophe ("he work's"), spelled-out decades."""
import re
import core

AP = r"['’]"

# --- its' and friends ------------------------------------------------------------------------------------------------
# The apostrophe after "its" is stray when a word follows: "the company and its' results". A quoted "its'" ('its' is a
# pronoun) is not matched: the word must follow a space or an opening bracket, and a word must follow it.


def stray_rules():
    core.add('apostrophe.its_stray', rf"(?i)(?:^|[\s(,;:])(?P<target>its{AP})[ \t]+[a-z]", 'its', 'Punctuation', 0.95,
             '“Its” (the possessive) has no apostrophe.', 'The company announced its\' results today.',
             "The company announced its results today. The word 'its' is a possessive.",
             'The company announced its results today.')
    for w in ('hers', 'ours', 'yours', 'theirs'):
        core.add(f'apostrophe.{w}_stray', rf"(?i)(?:^|[\s(,;:])(?P<target>{w}{AP})(?:[ \t]+[a-z]|[.,;:!?)]|$)", w,
                 'Punctuation', 0.93, f'“{w.capitalize()}” has no apostrophe.',
                 f"That seat is {w}' for today.", f'That seat is {w} for today. The word {w} is a pronoun.',
                 f'That seat is {w} for today.')
    core.add('apostrophe.his_stray', rf"(?i)(?:^|[\s(,;:])(?P<target>his{AP}s)\b", 'his', 'Punctuation', 0.93,
             '“His” is already a possessive: it takes no “’s”.', "That bag is his's now.",
             "That bag is his now. The word 'his' is a pronoun.", 'That bag is his now.')
    core.add('apostrophe.mine_s', rf"(?i)(?:^|[\s(,;:])(?P<target>mine{AP}s)\b", 'mine', 'Punctuation', 0.93,
             '“Mine” is already a possessive: it takes no “’s”.', "That seat is mine's today.",
             'That seat is mine today. The mine shut years ago.', 'That seat is mine today.')


# --- time words: last year's budget ---------------------------------------------------------------------------------
TIME_NOUNS = ('budget results numbers sales revenue report plan model version edition meeting conference event winner '
              'champion data figures performance season fashion trend holiday return bonus review survey issue class '
              'goal profit earnings agenda schedule forecast weather news paper game match score special menu '
              'headline summary update').split()
TIMES = [
    ('this year', 'this years', "this year's"), ('last year', 'last years', "last year's"),
    ('next year', 'next years', "next year's"), ('this week', 'this weeks', "this week's"),
    ('last week', 'last weeks', "last week's"), ('next week', 'next weeks', "next week's"),
    ('this month', 'this months', "this month's"), ('last month', 'last months', "last month's"),
    ('next month', 'next months', "next month's"), ('last night', 'last nights', "last night's"),
    ('this morning', 'this mornings', "this morning's"), 
    ('last summer', 'last summers', "last summer's"), ('last season', 'last seasons', "last season's"),
    ('this season', 'this seasons', "this season's"), ('next season', 'next seasons', "next season's"),
    ('this quarter', 'this quarters', "this quarter's"), ('last quarter', 'last quarters', "last quarter's"),
    ('next quarter', 'next quarters', "next quarter's"), ('last decade', 'last decades', "last decade's"),
]


def time_rules():
    alt = '|'.join(sorted(TIME_NOUNS, key=lambda w: (-len(w), w)))
    for good, bad, fixed in TIMES:
        first, second = bad.split()
        pattern = rf'(?i)\b{first} (?P<target>{second}) (?:{alt})\b'
        fixed_word = fixed.split()[1]
        core.add(f'apostrophe.{first}_{good.split()[1]}s', pattern, fixed_word, 'Possessive', 0.9,
                 f'Add the apostrophe of the possessive: “{fixed}”.',
                 f'We reviewed {bad} budget.', f"We reviewed {fixed} budget. The {bad} were busy.",
                 f"We reviewed {fixed} budget.")
    for good, bad, fixed in (('yesterday', 'yesterdays', "yesterday's"), ('tomorrow', 'tomorrows', "tomorrow's"),
                             ('tonight', 'tonights', "tonight's")):
        pattern = rf'(?i)\b(?P<target>{bad}) (?:{alt})\b'
        core.add(f'apostrophe.{bad}', pattern, fixed, 'Possessive', 0.9,
                 f'Add the apostrophe of the possessive: “{fixed}”.',
                 f'We reviewed {bad} budget.', f"We reviewed {fixed} budget. The {bad} are busy.",
                 f"We reviewed {fixed} budget.")


# --- holidays ----------------------------------------------------------------------------------------------------------
HOLIDAY_LEFT = (r'(?:happy|on|for|at|this|next|last|every|since|before|after|until|till|by|of|during|over|to|from|'
                r'through)')


def holiday_rules():
    items = [
        ('mothers day', "Mother's Day", 'Happy mothers day to all moms!', "Happy Mother's Day to all moms!"),
        ('fathers day', "Father's Day", 'We bought a gift for fathers day.', "We bought a gift for Father's Day."),
        ('valentines day', "Valentine's Day", 'We booked dinner for valentines day.', "We booked dinner for Valentine's Day."),
        ('april fools day', "April Fools' Day", 'He tricked us on april fools day.', "He tricked us on April Fools' Day."),
        ('new years eve', "New Year's Eve", 'We stayed home on new years eve.', "We stayed home on New Year's Eve."),
        ('new years day', "New Year's Day", 'The shops close on new years day.', "The shops close on New Year's Day."),
        ('new years resolution', "New Year's resolution", 'Her new years resolution is to run more.', "Her New Year's resolution is to run more."),
        ('grandparents day', "Grandparents' Day", 'The school holds a party on grandparents day.', "The school holds a party on Grandparents' Day."),
    ]
    for bad, good, pos, fixed in items:
        pattern = rf'(?i)\b(?:{HOLIDAY_LEFT}) (?P<target>{bad})\b' if not bad.startswith('new years resolution') else \
            r"(?i)\b(?:her|his|my|your|our|their|the|a|every|this|last|next) (?P<target>new years resolution)\b"
        neg = fixed + (' The new year starts soon.' if 'new' in bad else ' The day was long.')
        core.add('apostrophe.holiday_' + re.sub(r'\W+', '_', bad), pattern, good, 'Possessive', 0.9,
                 f'Write “{good}” with its apostrophe.', pos, neg, fixed)


# --- fixed phrases and idioms with a missing possessive apostrophe -----------------------------------------------------
# (pattern with a (?P<target>) group, replacement, positive, fixed positive, negative)
IDIOMS = [
    ('stones_throw', r"(?i)\ba (?P<target>stones) throw\b", "stone's", 'It is a stones throw from here.', "It is a stone's throw from here."),
    ('arms_length', r"(?i)\bat (?P<target>arms) length\b", "arm's", 'She kept him at arms length.', "She kept him at arm's length."),
    ('wits_end', r"(?i)\b(?:at|to|from|my|his|her|our|their|your) (?P<target>wits) end\b", "wits'", 'I am at my wits end.', "I am at my wits' end."),
    ('goodness_sake', r"(?i)\bfor (?P<target>goodness) sake\b", "goodness'", 'For goodness sake, sit down.', "For goodness' sake, sit down."),
    ('heavens_sake', r"(?i)\bfor (?P<target>heavens) sake\b", "heaven's", 'For heavens sake, sit down.', "For heaven's sake, sit down."),
    ('gods_sake', r"(?i)\bfor (?P<target>gods) sake\b", "God's", 'Oh, for gods sake, sit down.', "Oh, for God's sake, sit down."),
    ('pities_sake', r"(?i)\bfor (?P<target>pities) sake\b", "pity's", 'For pities sake, listen.', "For pity's sake, listen."),
    ('petes_sake', r"(?i)\bfor pete(?P<target>s) sake\b", "'s", 'For Petes sake, call him.', "For Pete's sake, call him."),
    ('birds_eye', r"(?i)\b(?:a|the|from a|from the) (?P<target>birds eye) view\b", "bird's-eye", 'We got a birds eye view of the city.', "We got a bird's-eye view of the city."),
    ('bulls_eye', r"(?i)\b(?:a|the|hit|hits|hitting) (?P<target>bulls eye)\b", "bull's-eye", 'She hit the bulls eye on her first try.', "She hit the bull's-eye on her first try."),
    ('fools_errand', r"(?i)\ba (?P<target>fools) errand\b", "fool's", 'It was a fools errand.', "It was a fool's errand."),
    ('fools_paradise', r"(?i)\ba (?P<target>fools) paradise\b", "fool's", 'He lives in a fools paradise.', "He lives in a fool's paradise."),
    ('fools_gold', r"(?i)\b(?P<target>fools) gold\b", "fool's", 'It turned out to be fools gold.', "It turned out to be fool's gold."),
    ('devils_advocate', r"(?i)\b(?:play|plays|played|playing|a|the) (?P<target>devils) advocate\b", "devil's", 'Let me play devils advocate for a moment.', "Let me play devil's advocate for a moment."),
    ('lions_share', r"(?i)\bthe (?P<target>lions) share\b", "lion's", 'He took the lions share of the credit.', "He took the lion's share of the credit."),
    ('mans_best_friend', r"(?i)\b(?P<target>mans) best friend\b", "man's", 'A dog is mans best friend.', "A dog is man's best friend."),
    ('writers_block', r"(?i)\b(?:have|has|had|having|with|from|of|cure|beat|overcome|a|the) (?P<target>writers) block\b", "writer's", 'She has a bad case of writers block.', "She has a bad case of writer's block."),
    ('hornets_nest', r"(?i)\ba (?P<target>hornets) nest\b", "hornet's", 'The question stirred up a hornets nest.', "The question stirred up a hornet's nest."),
    ('sheeps_clothing', r"(?i)\bin (?P<target>sheeps) clothing\b", "sheep's", 'He is a wolf in sheeps clothing.', "He is a wolf in sheep's clothing."),
    ('murphys_law', r"(?i)\bmurphy(?P<target>s) law\b", "'s", 'That is just Murphys law at work.', "That is just Murphy's law at work."),
    ('occams_razor', r"(?i)\boccam(?P<target>s) razor\b", "'s", 'Occams razor favors the simpler theory.', "Occam's razor favors the simpler theory."),
    ('pandoras_box', r"(?i)\bpandora(?P<target>s) box\b", "'s", 'That would open Pandoras box.', "That would open Pandora's box."),
    ('bachelors_degree', r"(?i)\b(?:a|the|my|her|his|your|their|earn|earned|earning|hold|holds|holding|with|without) (?P<target>bachelors) degree\b", "bachelor's", 'She holds a bachelors degree.', "She holds a bachelor's degree."),
    ('masters_degree', r"(?i)\b(?:a|the|my|her|his|your|their|earn|earned|earning|hold|holds|holding|with|without) (?P<target>masters) degree\b", "master's", 'She holds a masters degree.', "She holds a master's degree."),
    ('associates_degree', r"(?i)\b(?:an|the|my|her|his|your|their|earn|earned|earning|hold|holds|holding|with|without) (?P<target>associates) degree\b", "associate's", 'She holds an associates degree.', "She holds an associate's degree."),
    ('doctors_orders', r"(?i)\b(?:the|my|your|his|her|our|their|a) (?P<target>doctors) (?:orders|appointment|note|office|advice|recommendation|prescription|instructions|approval|signature|permission)\b", "doctor's", 'He stayed home on the doctors orders.', "He stayed home on the doctor's orders."),
    ('dentists_appointment', r"(?i)\b(?:the|my|your|his|her|our|their|a) (?P<target>dentists) (?:appointment|office|advice|recommendation|chair)\b", "dentist's", 'I have a dentists appointment today.', "I have a dentist's appointment today."),
    ('lawyers_advice', r"(?i)\b(?:the|my|your|his|her|our|their|a) (?P<target>lawyers) (?:advice|office|recommendation|letter|opinion|fee)\b", "lawyer's", 'She followed her lawyers advice.', "She followed her lawyer's advice."),
    ('vets_office', r"(?i)\b(?:the|my|your|his|her|our|their|a) (?P<target>vets) (?:office|appointment|advice|recommendation|bill)\b", "vet's", 'We waited at the vets office.', "We waited at the vet's office."),
    ('landlords_permission', r"(?i)\b(?:the|my|your|his|her|our|their|a) (?P<target>landlords) (?:permission|approval|consent|signature|office|email)\b", "landlord's", 'We need the landlords permission.', "We need the landlord's permission."),
    ('mechanics_shop', r"(?i)\b(?:the|my|your|his|her|our|their|a) (?P<target>mechanics) (?:shop|advice|recommendation|estimate|quote)\b", "mechanic's", 'I took the car to the mechanics shop.', "I took the car to the mechanic's shop."),
]


def idiom_rules():
    for ident, pattern, repl, pos, fixed in IDIOMS:
        neg = fixed + ' The word was spelled correctly.'
        core.add('apostrophe.' + ident, pattern, repl, 'Possessive', 0.9,
                 f'Add the apostrophe: “{repl}”.', pos, neg, fixed)
    heads = ('room clothing clothes shoes wear health league basketball team football suit fashion watch restroom '
             'shirt jacket department section soccer golf rights bathroom toilet shop store style').split()
    alt = '|'.join(sorted(heads, key=lambda w: (-len(w), w)))
    core.add('apostrophe.mens', rf'(?i)\b(?P<target>mens) (?:{alt})\b', "men's", 'Possessive', 0.92,
             'Add the apostrophe of the possessive: “men’s”.', 'The mens room is on the left.',
             "The men's room is on the left. Mens rea is a legal term.", "The men's room is on the left.")
    for bad, good, noun in (('mens', "men's", 'clothes'),):
        core.add(f'apostrophe.{bad}_plural_apostrophe', rf"(?i)\b(?P<target>{bad}{AP})(?: |$)", good, 'Possessive', 0.93,
                 f'The plural “{good[:-2]}” takes “’s”, not “s’”.', f"These are the {bad}' {noun}.",
                 f"These are the {good} {noun}. The {bad[:-1]} {noun} are here.", f"These are the {good} {noun}.")
    core.add('apostrophe.one_anothers', r"(?i)\bone (?P<target>anothers) \w", "another's", 'Possessive', 0.92,
             'Add the apostrophe of the possessive: “one another’s”.', 'They respect one anothers ideas.',
             "They respect one another's ideas. They told one another.", "They respect one another's ideas.")
    core.add('apostrophe.each_others_plural', rf"(?i)\beach (?P<target>others{AP})(?: |$)", "other's", 'Possessive', 0.92,
             'Write “each other’s”: the apostrophe goes before the s.', "They finished each others' sentences.",
             "They finished each other's sentences. Each of the others agreed.", "They finished each other's sentences.")
    core.add('apostrophe.of_mines', r"(?i)\b(?:friend|friends|colleague|cousin|neighbor|neighbour|relative|coworker|"
             r"classmate|acquaintance|buddy|pal|teacher|client) of (?P<target>mines)\b", 'mine', 'Possessive', 0.93,
             'Write “of mine”.', 'She is a friend of mines.', 'She is a friend of mine. The mines closed years ago.',
             'She is a friend of mine.')
    for w in ('someone', 'somebody', 'anyone', 'anybody', 'everyone', 'everybody', 'nobody', 'no one'):
        core.add('apostrophe.' + w.replace(' ', '_') + '_elses', rf'(?i)\b{w} (?P<target>elses)\b', "else's",
                 'Possessive', 0.93, f'Add the apostrophe of the possessive: “{w} else’s”.',
                 f'That is {w} elses problem.', f"That is {w} else's problem. Ask {w} else.", f"That is {w} else's problem.")


# --- time-unit possessives: two weeks' notice ------------------------------------------------------------------------
def unit_possessive_rules():
    nouns = ['notice', 'worth', 'experience', 'vacation', 'holiday', 'salary', 'wages', 'sabbatical']
    count = r'(?:two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty|thirty|\d+|a few|several|many|some|few)'
    for n in nouns:
        core.add('apostrophe.units_' + n, rf'(?i)\b{count} (?P<target>(?P<u>days|weeks|months|years|hours|minutes))'
                 rf' {n}\b', "${u}'", 'Possessive', 0.9,
                 f'Add the apostrophe of the possessive: “two weeks’ {n}”.',
                 f'She gave two weeks {n} before leaving.',
                 f"She gave two weeks' {n} before leaving. She worked for two weeks.",
                 f"She gave two weeks' {n} before leaving.")


# --- plural acronyms and family names ----------------------------------------------------------------------------------
def plural_rules():
    verbs = "are|were|have|can|will|must|should|do|don't|aren't|weren't|haven't|include|contain|allow"
    core.add('apostrophe.family_plural',
             rf"(?-i:\b[Tt]he [A-Z][a-z]{{2,}}[a-rt-z](?P<target>{AP})s) (?:are|were|have|will|arrived|came|live|"
             rf"lived|moved|bought|invited|joined|called)\b", '', 'Possessive', 0.85,
             'A family name in the plural takes no apostrophe: “the Smiths”.', "The Smith's are coming to dinner.",
             "The Smiths are coming to dinner. The Smith's house is on the left.", 'The Smiths are coming to dinner.')


# --- he work's ----------------------------------------------------------------------------------------------------------
VERBS = ('work run look seem feel keep live love hate say use help start want need know think make take give come get '
         'play stay show tell ask call turn move leave bring buy pay meet speak write read sit stand follow change open '
         'close eat drink drive walk talk wait win lose mean hold hear see sell send build break cost grow '
         'include require provide offer allow cause happen sound taste smell depend matter count').split()


def verb_rules():
    for v in VERBS:
        core.add('apostrophe.verb_' + v, rf"(?i)\b(?:he|she|it) (?P<target>(?P<v>{v}){AP}s)\b", '${v}s', 'Punctuation',
                 0.93, f'A verb takes no apostrophe: “{v}s”.', f"We know she {v}'s every day.",
                 f"We know she {v}s every day. He said it's fine and she's going.", f"We know she {v}s every day.")
    core.add('apostrophe.verb_s_apostrophe_s', rf"(?i)\b(?:he|she|it) [a-z]+s(?P<target>{AP}s)\b", '', 'Punctuation', 0.93,
             'A verb ending in s takes no apostrophe.', "Because she works's too hard, we helped.",
             "Because she works too hard, we helped. She thinks the boss's desk is fine.",
             "Because she works too hard, we helped.")


# --- spelled-out decades -----------------------------------------------------------------------------------------------
def decade_rules():
    for stem, plural in (('twenty', 'twenties'), ('thirty', 'thirties'), ('forty', 'forties'), ('fifty', 'fifties'),
                         ('sixty', 'sixties'), ('seventy', 'seventies'), ('eighty', 'eighties'), ('ninety', 'nineties')):
        core.add('apostrophe.decade_' + stem, rf"(?i)\b(?:the|in the|early|late|mid|of the|during the) (?P<target>{stem}{AP}s)\b",
                 plural, 'Punctuation', 0.92, f'A decade takes no apostrophe: “the {plural}”.',
                 f"Music changed in the {stem}'s.", f'Music changed in the {plural}. The {stem} songs aged well.',
                 f'Music changed in the {plural}.')


def build():
    stray_rules()
    time_rules()
    holiday_rules()
    idiom_rules()
    unit_possessive_rules()
    plural_rules()
    verb_rules()
    decade_rules()
