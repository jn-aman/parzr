"""A singular unit or irregular noun after a number or a quantifier; "a bacteria" and the like."""
from core import *

TIME = "second|minute|hour|day|week|month|year|decade"
add('num.time_ago', rf"(?im){LEAD}{NUM}\s+(?P<target>(?P<u>{TIME}))\s+(?:ago|later|earlier|before|from now)\b",
    '${u}s', 'Grammar', 0.93, 'After a number above one, the unit of time is plural.',
    'We moved here 5 year ago.', 'We moved here a year ago, and 5 years ago it was empty.')
add('num.century_ago', rf"(?im){LEAD}{NUM}\s+(?P<target>century)\s+(?:ago|later|earlier|before|from now)\b",
    'centuries', 'Grammar', 0.93, 'After a number above one, the unit of time is plural.',
    'The bridge was built 3 century ago.', 'The bridge was built a century ago, and two centuries ago it was a ford.')
add('num.time_prep',
    rf"(?i)\b(?:for|in|within|after|during|over|past|last|next|every|than|about|around|almost|nearly|approximately|roughly|just|only|another|further|additional|extra|least|up to|of)\s+{NUM}\s+(?P<target>(?P<u>{TIME}))(?:\s*[,.;:!?)\"”]|\s*$|\s+(?:{FUNC}|and|or|of)\b)",
    '${u}s', 'Grammar', 0.9, 'After a number above one, the unit of time is plural.',
    'I waited for 3 month in the hospital.', 'I waited for a month in the hospital, and for 3 months after that; a 3 month contract ended.')
# The target starts at the space before the unit so that it begins where the hyphen pass's first edit does (the number itself
# is untouchable) and, at 0.96, beats that pass's 0.9: "is 5 year old" would otherwise become "is 5-year-old".
add('num.time_old',
    rf"(?i)\b(?:is|am|are|was|were|be|been|being|turned|turns|turning|aged|age|becomes|became|become|gets|got|getting|only|almost|nearly|just|already|now|still)\s+(?P<n>{NUM})(?P<target>\s+(?P<u>year|month|week|day)\s+old)(?:\s*[,.;:!?)\"”]|\s*$|\s+(?:and|but|so|when|while|because|now|today|with|in|on|at|from|to|as|if|then|yet)\b)",
    ' ${u}s old', 'Grammar', 0.96, 'Say how old someone is with the plural: “5 years old”. (The hyphenated “5-year-old” is for a noun: “a 5-year-old girl”.)',
    'My daughter is 5 year old and loves drawing.', 'My daughter is 5 years old, and her brother is a 7 year old with a red kite.')

UNITS = ("kilometer|kilometre|mile|meter|metre|centimeter|centimetre|millimeter|millimetre|yard|kilogram|gram|liter|litre|gallon|"
         "ounce|acre|hectare|kilobyte|megabyte|gigabyte|terabyte")
add('num.measure_away',
    rf"(?im){LEAD}{NUM}\s+(?P<target>(?P<u>{UNITS}))\s+(?:away|apart|from|further|farther|north|south|east|west)\b",
    '${u}s', 'Grammar', 0.9, 'After a number above one, the unit of measure is plural.',
    'The station is 10 kilometer away from here.', 'The station is 1 kilometer away from here, and a 10 kilometer walk follows, then a 5 kilometer per hour limit.')
add('num.measure_verb',
    rf"(?i)\b(?:ran|run|runs|running|walked|walk|walks|walking|drove|drive|drives|driving|cycled|swam|swim|hiked|hike|travelled|traveled|jogged|flew|rode|weigh|weighs|weighed|holds|contains|measures|measured|uses|needs|need|needed|has|have|had|is|are|was|were|about|nearly|almost|roughly|only|just|over|under|another|extra|additional|every|each|within|for)\s+{NUM}\s+(?P<target>(?P<u>{UNITS}))(?:\s*[,.;:!?)\"”]|\s*$|\s+(?:{FUNC}|of)\b)",
    '${u}s', 'Grammar', 0.88, 'After a number above one, the unit of measure is plural.',
    'The file is 5 gigabyte in total.', 'The file is 1 gigabyte in total, and I ran the 10 kilometer race on a 5 gigabyte phone.')
add('num.money',
    rf"(?i)\b(?:cost|costs|costing|worth|paid|pay|pays|paying|spent|spend|spends|charge|charges|charged|only|just|for|about|nearly|almost|over|under|than|is|are|was|were|of)\s+{NUM}\s+(?P<target>(?P<u>dollar|rupee|cent|peso|dirham|riyal|ruble|rouble|shilling|franc|dinar))(?:\s*[,.;:!?)\"”]|\s*$|\s+(?:{FUNC}|a|an|each|apiece|per|less|more|extra|only)\b)",
    '${u}s', 'Grammar', 0.9, 'After a number above one, the currency unit is plural.',
    'The ticket costs 20 dollar at the door.', 'The ticket costs 1 dollar at the door, and I found a 20 dollar bill.')
add('num.times',
    rf"(?im){LEAD}{NUM}\s+(?P<target>time)\s+(?:a|an|per|each|before|already|so far|more|over|in a row|since|last|every|today|yesterday|now)\b",
    'times', 'Grammar', 0.88, 'After a number above one, say “times”.',
    'I called him 5 time already.', 'I called him once already, and five times since; the 5 time zone chart helps.')
add('num.person',
    rf"(?i)\b(?:for|with|of|by|only|about|nearly|almost|over|under|than|around|least|total)\s+{NUM}\s+(?P<target>person)(?:\s*[,.;:!?)\"”]|\s*$|\s+(?:{FUNC}|only|max|maximum|per|each)\b)",
    'people', 'Grammar', 0.88, 'After a number above one, say “people”.',
    'Please book a table for 4 person.', 'Please book a table for 1 person, and a 4 person team joins later.')
for slug, one, many, pos, neg in [
    ('child', 'child', 'children', 'She is raising 3 child on her own.', 'She is raising 1 child on her own, and a 3 child policy was dropped.'),
    ('man', 'man', 'men', 'The crew had 6 man on board.', 'The crew had 1 man on board, and a 6 man tent held them.'),
    ('woman', 'woman', 'women', 'The team had 8 woman on the roster.', 'The team had 1 woman on the roster, and an 8 woman crew rowed.'),
]:
    add(f'num.digit_{slug}',
        rf"(?i)\b(?:have|has|had|having|with|of|only|about|nearly|almost|over|under|than|got|raise|raised|raising|adopt|adopted|support|supports|feed|feeds)\s+(?:{NUMD}|{NUMW})\s+(?P<target>{one})(?:\s*[,.;:!?)\"”]|\s*$|\s+(?:{FUNC})\b)",
        many, 'Grammar', 0.9, f'After a number above one, the plural is “{many}”.', pos, neg)
cover('Plural after a number', 'singular unit of time/measure/money, "time", "person", child/man/woman after a number above one, in contexts where no noun can follow (5 year ago, for 3 month, is 5 year old, 10 kilometer away, 20 dollar, 5 time a week, for 4 person, have 3 child)). "a 5 year plan", "a 10 kilometer race", "a 3 month contract", "a 20 dollar bill" and "1 year" are left alone; the engine already fixes number words two to twelve and "three year ago" (grammar.noun_number)',
      ['num.time_ago', 'num.century_ago', 'num.time_prep', 'num.time_old', 'num.measure_away', 'num.measure_verb', 'num.money', 'num.times', 'num.person', 'num.digit_child', 'num.digit_man', 'num.digit_woman'])

# a lot of / a couple of / a number of / these + a singular count noun.
COUNT = ("problem|issue|question|mistake|error|reason|idea|option|example|friend|student|customer|user|file|book|bug|feature|"
         "benefit|advantage|tip|step|member|employee|teacher|parent|kid|player|fan|project|task|meeting|email|message|"
         "document|article|movie|song|video|app|tool|thing|report|page|rule|group|site|link|plan|goal|skill|result|"
         "photo|picture|ticket|customer|worker|driver|doctor|nurse|patient|visitor|guest|tourist|volunteer|candidate")
add('quant.a_lot_of', rf"(?i)\b(?:a lot of|lots of|plenty of)\s+(?P<target>(?P<n>{COUNT}))(?:\s*[,.;:!?)\"”]|\s*$|\s+(?:{FUNC})\b)",
    '${n}s', 'Grammar', 0.9, 'After “a lot of”, a countable noun is plural.',
    'There are a lot of problem in the old code.', 'There are a lot of problems in the old code, and a lot of problem solving ahead.')
add('quant.couple_of', rf"(?i)\b(?:a couple of)\s+(?P<target>(?P<n>{COUNT}|{TIME}))(?:\s*[,.;:!?)\"”]|\s*$|\s+(?:{FUNC})\b)",
    '${n}s', 'Grammar', 0.9, 'After “a couple of”, a countable noun is plural.',
    'I have a couple of question about the invoice.', 'I have a couple of questions about the invoice, and a couple of question marks.')
add('quant.number_of',
    rf"(?i)\b(?:a number of|a variety of|a range of|a series of|a handful of|a wide range of|a wide variety of|a large number of|a small number of|a huge number of|a great number of|a bunch of|a majority of)\s+(?P<target>(?P<n>{COUNT}))(?:\s*[,.;:!?)\"”]|\s*$|\s+(?:{FUNC})\b)",
    '${n}s', 'Grammar', 0.9, 'After “a number of” and similar phrases, a countable noun is plural.',
    'We tested a variety of option before the launch.', 'We tested a variety of options before the launch, and a range of option menus.')
add('quant.these_those', rf"(?i)\b(?:these|those)\s+(?P<target>(?P<n>{COUNT}))(?:\s*[,.;:!?)\"”]|\s*$|\s+(?:{FUNC})\b)",
    '${n}s', 'Grammar', 0.86, '“These” and “those” go with a plural noun.',
    'These student are ready for the exam.', 'These students are ready for the exam, and those who wait will follow.')
for slug, one, many, pos, neg in [
    ('person', 'person', 'people', 'There were a lot of person in the queue.', 'There were a lot of people in the queue, and one person left.'),
    ('child', 'child', 'children', 'There were lots of child at the fair.', 'There were lots of children at the fair, and one child won.'),
    ('man', 'man', 'men', 'We met plenty of man on the trail.', 'We met plenty of men on the trail, and one man sang.'),
    ('woman', 'woman', 'women', 'The class has a number of woman from abroad.', 'The class has a number of women from abroad, and one woman leads.'),
]:
    add(f'quant.lot_{slug}',
        rf"(?i)\b(?:a lot of|lots of|plenty of|a number of|a large number of|a small number of|a couple of)\s+(?P<target>{one})(?:\s*[,.;:!?)\"”]|\s*$|\s+(?:{FUNC})\b)",
        many, 'Grammar', 0.9, f'After “a lot of” and similar phrases, the plural is “{many}”.', pos, neg)
cover('Plural after a quantifier', 'a lot of / lots of / plenty of / a couple of / a number of / a variety of / a range of / these / those + a singular countable noun (the engine already fixes many, several, few and number words; "a lot of problem solving", "a couple of question marks" are left alone)',
      ['quant.a_lot_of', 'quant.couple_of', 'quant.number_of', 'quant.these_those', 'quant.lot_person', 'quant.lot_child', 'quant.lot_man', 'quant.lot_woman'])

# a/an + the plural of a Latin, Greek or irregular noun: the singular is meant.
T2 = (r"(?:\s*[,.;:!?)\"”]|\s*$|\s+(?:is|was|are|were|has|had|can|could|will|would|may|might|must|that|which|who|of|in|on|"
      r"at|for|from|with|to|and|but|or|as|by|than|called|known)\b)")
# The articles-determiners pack already has det.a_<plural> for stimuli, fungi, cacti, syllabi, larvae, nuclei, radii, analyses,
# hypotheses, diagnoses, theses, crises, indices, matrices, vertices, appendices, children, men, women, mice, teeth, geese, feet,
# oxen, wolves, knives, wives, thieves and loaves; only the plurals it lacks are kept here.
A_PLURAL = [
    ('bacteria', 'a bacterium', 'Each sample held a bacteria that grows fast.', 'Each sample held a bacterium that grows fast, and the bacteria count was low.'),
    ('vertebrae', 'a vertebra', 'The scan showed a vertebrae that was cracked.', 'The scan showed a vertebra that was cracked, and the vertebrae are fine.'),
    ('oases', 'an oasis', 'We found an oases in the desert.', 'We found an oasis in the desert, and the oases are green.'),
    ('parentheses', 'a parenthesis', 'Add a parentheses.', 'Add a parenthesis, and match the parentheses.'),
    ('leaves', 'a leaf', 'She pressed a leaves in the book.', 'She pressed a leaf in the book, and the leaves are red.'),
    ('halves', 'a half', 'Cut it so each side is a halves.', 'Cut it so each side is a half, and the halves match.'),
    ('shelves', 'a shelf', 'We need a shelves for the books.', 'We need a shelf for the books, and the shelves are full.'),
    ('calves', 'a calf', 'The cow had a calves in the spring.', 'The cow had a calf in the spring, and the calves are strong.'),
    ('elves', 'an elf', 'The book has an elves with a bow.', 'The book has an elf with a bow, and the elves are small.'),
]
for plural, single, pos, neg in A_PLURAL:
    add(f'det.a_{plural}', rf"(?i)\b(?P<target>an?\s+(?-i:{plural})){T2}", single, 'Grammar', 0.9,
        f'“A” and “an” go with one: say “{single}”.', pos, neg)
cover('A/an before a plural', 'a/an + a plural that has a singular: bacteria, vertebrae, oases, parentheses, leaves, halves, shelves, calves, elves (the articles-determiners pack has det.a_<plural> for criteria, phenomena, stimuli, fungi, cacti, syllabi, larvae, nuclei, radii, analyses, hypotheses, diagnoses, theses, crises, indices, matrices, vertices, appendices, children, men, women, mice, teeth, geese, feet, oxen, wolves, knives, wives, thieves, loaves; "a media company", "a data scientist", "a people" and "a teeth whitening kit" are left alone because only a verb, preposition, conjunction or the clause end may follow)',
      [f'det.a_{p}' for p, *_ in A_PLURAL])
