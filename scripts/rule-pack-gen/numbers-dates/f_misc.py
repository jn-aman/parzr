"""Number words: joined or misspelt number words, "forth" for "fourth", "tens of thousand", "a thousand of people"."""
from lib import add, q, ONES, TEENS, TENS, TAIL, CARD2

add('word.joined_tens',
    r'(?i)\b(?P<target>(?P<a>(?-i:twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety))(?P<b>(?-i:one|two|three|four|five|six|seven|eight|nine)))\b',
    '${a}-${b}', 'Spelling', 0.95,
    'Compound numbers from 21 to 99 are written with a hyphen: “twenty-one”.',
    'She ate twentyone grapes.', 'She ate twenty-one grapes, and twenty grapes more.',
    'She ate twenty-one grapes.')
add('word.fourteen', r'(?i)\b(?P<target>forteen|fourtheen|fourteeen)\b', 'fourteen', 'Spelling', 0.96,
    'The number is spelt “fourteen”.',
    'He turned forteen last week.', 'He turned fourteen last week, and she turned forty.',
    'He turned fourteen last week.')
add('word.seventeen', r'(?i)\b(?P<target>sevnteen|seventen|sevneteen)\b', 'seventeen', 'Spelling', 0.96,
    'The number is spelt “seventeen”.',
    'She turned sevnteen last week.', 'She turned seventeen last week, and he turned seventy.',
    'She turned seventeen last week.')
add('word.fourth_forth', r'(?i)\b(?:the|this is the|for the|a|first|second|third) (?P<target>forth) (?:time|day|week|month|year|quarter|floor|grade|place|row|chapter|person|one|attempt|edition|of)\b', 'fourth', 'Spelling', 0.93,
    'The ordinal for 4 is “fourth”; “forth” means “forward”.',
    'This is the forth time I asked.', 'This is the fourth time I asked, and he walked back and forth.',
    'This is the fourth time I asked.')
add('word.tens_of_thousand', r'(?i)\b(?:tens|hundreds|dozens) of (?P<target>(?P<u>thousand|million|billion))(?: of\b|[.,;:!?)]|$)', '${u}s', 'Grammar', 0.92,
    'After “tens of” or “hundreds of” the big number is plural: “tens of thousands”.',
    'Tens of thousand of people came.', 'Tens of thousands of people came, and hundreds of thousands watched.',
    'Tens of thousands of people came.')
NOUNS = (r'(?:people|users|students|children|kids|families|customers|employees|workers|visitors|fans|years|days|miles|'
         r'times|dollars|books|files|items|messages|emails|videos|photos|pictures|pages|words|songs|animals|birds|cars|'
         r'houses|homes|jobs|companies|stores|shops|cities|towns|villages|countries|species|ways|reasons|ideas|things|'
         r'lines|rows|records|documents|articles|posts|comments|views|requests|calls|tickets|seats|trees|plants|stars|'
         r'lives|soldiers|refugees|participants|members|volunteers|teachers|doctors|patients|women|men|tourists|voters)')
add('word.number_of_before_noun', r'(?i)\b(?:\d+|a|one|two|three|four|five|six|seven|eight|nine|ten|twenty|thirty|forty|fifty|hundred) (?:hundred|thousand|million|billion)(?P<target> of) ' + NOUNS + r'\b', '', 'Grammar', 0.9,
    'After an exact number no “of” is needed: “a thousand people”.',
    'A thousand of people signed it.', 'A thousand people signed it, and a thousand of the people signed it.',
    'A thousand people signed it.')
add('word.couple_of_units', r'(?i)\ba couple of (?P<target>(?P<u>second|minute|hour|day|week|month|year))' + TAIL, '${u}s', 'Grammar', 0.9,
    'After “a couple of” the noun is plural: “a couple of days”.',
    'He left a couple of day ago.', 'He left a couple of days ago, and a couple of day-trips went well.',
    'He left a couple of days ago.')
add('word.half_past_oclock', r'(?i)\b(?:half|quarter|ten|twenty|five|twenty-five) (?:past|to) (?:\d{1,2}|' + ONES + '|' + TEENS + r')(?P<target> o[\'’]clock)\b', '', 'Grammar', 0.93,
    '“o’clock” is only used for a full hour: “half past five”, not “half past five o’clock”.',
    'We left at half past five o\'clock sharp.'.replace("o\\'clock", "o'clock"), 'We left at half past five sharp, or at five o\'clock sharp.',
    'We left at half past five sharp.')
add('word.several_measure', r'(?i)\b(?:several|many|a few|multiple) (?P<target>(?P<u>kilometre|kilometer|metre|meter|mile|kilogram|gram|litre|liter|gallon|ounce|acre|hectare|tonne|yard))' + TAIL, '${u}s', 'Grammar', 0.9,
    'After “several”, “many” or “a few” the unit is plural: “a few miles”.',
    'It is a few mile from here.', 'It is a few miles from here, and a few mile-long queues formed.'.replace(', and a few mile-long queues formed', ', and a mile-long queue formed'),
    'It is a few miles from here.')
