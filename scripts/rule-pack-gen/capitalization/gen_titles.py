"""Titles written before a name: "president Obama" is "President Obama", while "the president" stays lowercase."""
from lib import *

FAM = 'Titles before names'

# The word before the title. A title used as a job description ("the president Joe Smith", "former president Obama",
# "our CEO") keeps its lowercase, and so does one after a verb of becoming ("elected president Tuesday"), so the
# title is capitalized only after a word that introduces a person: "with president Obama", "dear professor Smith".
PREPS = (r"with|from|by|for|of|at|on|via|cc|regarding|according to|against|behind|beside|like|unlike|despite|after|"
         r"before|during|under|near|between|dear|hi|hello|hey|thanks|thank|thanked")
# Titles that cannot be a verb also follow these.
VERBY = (r"that|said|says|say|told|tell|tells|ask|asked|asks|met|meet|meets|see|saw|seen|call|called|calls|"
         r"about|to|contact|contacted|email|emailed|message|messaged|wrote to|write to|writes to|spoke to|speak to|"
         r"spoke with|speak with|invite|invited|invites|welcome|welcomed|welcomes|introduce|introduced|introduces|"
         r"praised|criticized|criticised|blamed|supported|visited|visit|visits|ask|asking")

SURNAME = r"(?-i:[A-Z][a-z]{2,}(?:['’]s)?)\b"
START = r"(?:^|[\s(\[\"“‘])"

# (title, canonical, can be a verb or a common noun before a capital: prepositions only)
TITLES = [
    ('president', 'President', False), ('vice president', 'Vice President', False),
    ('prime minister', 'Prime Minister', False), ('chief minister', 'Chief Minister', False),
    ('senator', 'Senator', False), ('governor', 'Governor', False), ('mayor', 'Mayor', False),
    ('congressman', 'Congressman', False), ('congresswoman', 'Congresswoman', False),
    ('chancellor', 'Chancellor', False), ('ambassador', 'Ambassador', False), ('professor', 'Professor', False),
    ('chief justice', 'Chief Justice', False), ('attorney general', 'Attorney General', False),
    ('secretary general', 'Secretary General', False), ('pope', 'Pope', False), ('cardinal', 'Cardinal', False),
    ('bishop', 'Bishop', False), ('rabbi', 'Rabbi', False), ('imam', 'Imam', False), ('reverend', 'Reverend', False),
    ('colonel', 'Colonel', False), ('lieutenant', 'Lieutenant', False), ('sergeant', 'Sergeant', False),
    ('detective', 'Detective', False), ('inspector', 'Inspector', False), ('admiral', 'Admiral', False),
    ('sheriff', 'Sheriff', False), ('commissioner', 'Commissioner', False), ('king', 'King', False),
    ('prince', 'Prince', False), ('princess', 'Princess', False), ('duke', 'Duke', False),
    ('duchess', 'Duchess', False), ('dr', 'Dr', False), ('mr', 'Mr', False), ('mrs', 'Mrs', False),
    ('prof', 'Prof', False),
    ('judge', 'Judge', True), ('captain', 'Captain', True), ('officer', 'Officer', True), ('doctor', 'Doctor', True),
    ('pastor', 'Pastor', True), ('queen', 'Queen', True),
    ('commander', 'Commander', True), ('lord', 'Lord', True), ('lady', 'Lady', True), ('dame', 'Dame', True),
]
VERB_READING = {
    'judge': "She was asked to judge Okafor's entry, then judge the rest.",
    'captain': "He will captain Okafor's team and captain it well.",
    'doctor': "Do not doctor Okafor's report or doctor the figures.",
    'pastor': "He will pastor Okafor's flock and pastor the church.",
    'queen': "They will queen Okafor in the chess game.",
    'lord': "He likes to lord Okafor's win over us.",
}


def build():
    for lower, canon, verby in TITLES:
        intro = PREPS if verby else PREPS + '|' + VERBY
        dot = r'\.?' if lower in ('dr', 'mr', 'mrs', 'prof') else ''
        pat = f"{START}(?i:(?:{intro}),?\\s+)(?P<target>(?-i:{lower})){dot}\\s+{SURNAME}"
        surname = 'Patel' if dot else 'Okafor'
        pos = f'I spoke with {lower} {surname} about the trip.'
        neg = (f'I spoke with {canon} {surname} about the trip. The {lower} arrived late, and our {lower} was kind. '
               f'He was elected {lower} Tuesday, and the former {lower} {surname} agreed.')
        if lower in VERB_READING:
            neg += ' ' + VERB_READING[lower].replace('Okafor', surname)
        emit(f'caps.title.{slug(lower)}', pat, canon, 'Capitalization', 0.86 if verby else 0.88,
             'A title directly before a name takes a capital letter.', pos, neg, FAM)
    # Family titles are not capitalized after "my": "my uncle John". Capitalized only in direct address.
    for lower, canon in [('uncle', 'Uncle'), ('aunt', 'Aunt'), ('auntie', 'Auntie'), ('grandma', 'Grandma'),
                         ('grandpa', 'Grandpa'), ('mom', 'Mom'), ('mum', 'Mum'), ('dad', 'Dad')]:
        pass  # deliberately left out: "my uncle John" is correct, and "Uncle John" needs the speaker's relation.
