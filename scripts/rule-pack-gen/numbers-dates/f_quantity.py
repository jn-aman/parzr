"""Quantity words: "three hundreds", "thousand of people", "20 percents", "one and half hours", "two third of",
"approximately about 100", "ranges from 5 and 10"."""
from lib import add, q, CARD2, CARD, ONES, TEENS, TENS

DEC = r'\d+[.,]\d+'
BIG_D = r'(?:[2-9]\d*|1\d+|' + DEC + r')'
BIG_W = r'(?:two|three|four|five|six|seven|eight|nine|' + TEENS + '|' + TENS + r'|hundred|a few|a couple of)'
# Number words need a word before them that rules out "the two thousands" (the 2000s) and "upper two thousands" (a range).
PRE = (r'(?:of|than|about|around|over|under|only|just|nearly|almost|approximately|roughly|with|for|by|to|are|were|was|is|has|have|had|got|'
       r'sold|cost|costs|paid|earn|earned|spent|lost|killed|at|from|in|and|or|but|so|if|when|that|more|less|another|extra|add|added|worth|'
       r'total|reached|exceeded|several|hundred)')
LEAD = r'(?:^|[^/\s]\s+|\()'   # a number is not read after a slash ("1 / 2 second", "5 / 4 time")

for word, plural, ex in [('hundred', 'hundreds', 'We sold two hundreds copies today.'),
                         ('thousand', 'thousands', 'About 3 thousands people came.'),
                         ('million', 'millions', 'The app has 2 millions users.'),
                         ('billion', 'billions', 'It is worth 3 billions dollars.'),
                         ('trillion', 'trillions', 'The debt passed 30 trillions.'),
                         ('dozen', 'dozens', 'She sold two dozens eggs.')]:
    first = (r'(?i)(?:' + LEAD + BIG_D + r'|\b' + PRE + r' ' + BIG_W + r') (?P<target>' + word + r's)'
             + (r' [a-z]{3,}s\b' if word == 'hundred' else r'\b'))
    fixed = ex.replace(plural, word)
    neg = {'hundred': 'We sold two hundred copies, hundreds of them, three hundred thousand more, and he scored two hundreds in the series.',
           'thousand': 'About 3 thousand people came, and thousands of others watched at home.',
           'million': 'The app has 2 million users and millions of downloads.',
           'billion': 'It is worth 3 billion dollars, and billions more are planned.',
           'trillion': 'The debt passed 30 trillion, and trillions more are owed.',
           'dozen': 'She sold two dozen eggs, then dozens of other things.'}[word]
    add(f'qty.{plural}_after_number', first, word, 'Grammar', 0.92,
        f'After a number, “{word}” stays singular: “two {word}”; the plural “{plural}” is for “{plural} of …”.',
        ex, neg, fixed)

NOUNS = (r'(?:people|users|students|children|kids|families|customers|employees|workers|visitors|fans|years|days|miles|'
         r'times|dollars|books|files|items|messages|emails|videos|photos|pictures|pages|words|songs|animals|birds|cars|'
         r'houses|homes|jobs|companies|stores|shops|cities|towns|villages|countries|species|ways|reasons|ideas|things|'
         r'lines|rows|records|documents|articles|posts|comments|views|requests|calls|tickets|seats|trees|plants|stars|'
         r'lives|soldiers|refugees|participants|members|volunteers|teachers|doctors|patients|women|men|tourists|voters)')
for word, ex in [('hundred', 'There are hundred of people in the hall.'), ('thousand', 'Thousand of fans joined the march.'),
                 ('million', 'There were million of years between them.'),
                 ('billion', 'The video was seen by billion of people.'), ('dozen', 'We have dozen of files to review.')]:
    plural = word + 's'
    pre = r'(?:^|[.!?]\s+|\b(?:are|were|was|is|about|for|with|by|than|over|under|in|from|to|and|only|just|have|has|had)\s+)'
    fixed = ex.replace(word + ' of', plural + ' of') if not ex.startswith('Thousand') else ex.replace('Thousand of', 'Thousands of')
    neg = {'hundred': 'There are hundreds of people in the hall, and a hundred of the seats are free.',
           'thousand': 'Thousands of fans joined the march, and one thousand of the fans sang.',
           'million': 'There were millions of years between them, and a million of the years were cold.',
           'billion': 'The video was seen by billions of people, and a billion of them are new.',
           'dozen': 'We have dozens of files to review, and a dozen of the files are done.'}[word]
    add(f'qty.{word}_of_missing_s', r'(?i)' + pre + r'(?P<target>(?P<u>' + word + r')) of ' + NOUNS + r'\b', '${u}s', 'Grammar', 0.9,
        f'With no number or “a” before it, use the plural: “{plural} of”.', ex, neg, fixed)

add('qty.percents', r'(?i)' + LEAD + r'(?:' + CARD + '|' + DEC + r') (?P<target>percents)\b', 'percent', 'Grammar', 0.93,
    '“Percent” has no plural after a number: “20 percent”.',
    'Prices rose 20 percents last year.', 'Prices rose 20 percent last year, and the percents column is blank.',
    'Prices rose 20 percent last year.')
add('qty.percentage_after_number',
    r'(?i)' + LEAD + r'(?:' + CARD + '|' + DEC + r') (?P<target>percentages?)(?:[.,;:!?)]|$|\s+(?:of|and|or|to|in|on|at|from|more|less|higher|lower)\b)',
    'percent', 'Word choice', 0.88,
    'After a number, use “percent”; “percentage” names a share by itself (“a high percentage”).',
    'About 40 percentage of the staff agreed.', 'About 40 percent of the staff agreed, a 40 percentage point rise.',
    'About 40 percent of the staff agreed.')
add('qty.space_before_percent_sign',
    r'(?i)\b\d+(?:[.,]\d+)?(?P<target> )%(?:[.,;:!?)]|$|\s+(?:of|off|more|less|higher|lower|faster|slower|cheaper|bigger|smaller|better|worse|increase|decrease|growth|interest|discount|tax|and|or|to|in|on|at|from|by|for|is|are|was|were|per|cotton|chance)\b)',
    '', 'Style', 0.7,
    'In English the percent sign follows the number directly: “20%”.',
    'Sales grew by 20 % in a year.', 'Sales grew by 20% in a year, and 17 % 5 is the modulo in code.',
    'Sales grew by 20% in a year.')
add('qty.percent_after_sign', r'(?i)\b\d+(?:[.,]\d+)?%(?P<target> per ?cent)\b', '', 'Redundancy', 0.8,
    'The sign “%” already means percent: write “20%” or “20 percent”, not both.',
    'Sales grew 20% percent last year.', 'Sales grew 20% last year, or 20 percent.',
    'Sales grew 20% last year.')
add('qty.sign_after_percent', r'(?i)\b\d+(?:[.,]\d+)? per ?cent(?P<target> ?%)', '', 'Redundancy', 0.8,
    'The word “percent” already means “%”: write “20 percent” or “20%”, not both.',
    'Sales grew 20 percent % last year.', 'Sales grew 20 percent last year, or 20%.',
    'Sales grew 20 percent last year.')
add('qty.hundred_percent', r'(?i)\b(?:am|is|are|was|were|be|feel|felt|[’\'](?:m|s|re)) (?P<target>hundred) per ?cent\b', 'a hundred', 'Register', 0.75,
    'Standard English says “a hundred percent” (or “100 percent”).',
    'I am hundred percent sure about it.', 'I am a hundred percent sure about it, or 100 percent.',
    'I am a hundred percent sure about it.')

FR = r'third|fourth|fifth|sixth|seventh|ninth|tenth|quarter'
add('qty.fraction_plural', r'(?i)' + LEAD + r'(?:two|three|four|five|six|seven|eight|nine) (?P<target>(?P<f>' + FR + r'))(?: of\b|[,.;:!?)]|$)', '${f}s', 'Grammar', 0.9,
    'A fraction above one is plural: “two thirds”, “three quarters”.',
    'Two third of the class passed.', 'Two thirds of the class passed, and the third of three students left.',
    'Two thirds of the class passed.')
add('qty.fraction_one_plural', r'(?i)' + LEAD + r'one (?:' + FR + r')(?P<target>s) of\b', '', 'Grammar', 0.9,
    'One part is singular: “one third of”, not “one thirds of”.',
    'One thirds of the class passed.', 'One third of the class passed, and two thirds failed.',
    'One third of the class passed.')

UNITS = (r'(?:hours?|days?|weeks?|months?|years?|minutes?|cups?|litres?|liters?|kilos?|miles?|times|percent|million|billion|'
         r'kilometres?|kilometers?|metres?|meters?|feet|inches|pounds|dollars|acres|tons?|tonnes?)')
NUMS = r'(?:one|two|three|four|five|six|seven|eight|nine|ten|[1-9]|10)'
add('qty.and_half_missing_a', r'(?i)\b' + NUMS + r' and (?P<target>half) ' + UNITS + r'\b', 'a half', 'Grammar', 0.92,
    'Say “one and a half hours”: the “a” is needed.',
    'The film runs two and half hours.', 'The film runs two and a half hours, or two and a half times that.',
    'The film runs two and a half hours.')
add('qty.and_a_half_singular',
    r'(?i)\b' + NUMS + r' and a half (?P<target>(?P<u>hour|day|week|month|year|minute|mile|kilometre|kilometer|metre|meter|litre|liter|cup|dollar|pound))(?:[,.;:!?)]|$|\s+(?:ago|later|of|to|and|or|but|in|at|on|for|before|after|from|away|long)\b)',
    '${u}s', 'Grammar', 0.9,
    'The unit after “one and a half” is plural: “one and a half hours”.',
    'The flight took one and a half hour in total.', 'The flight took one and a half hours, or an hour and a half.',
    'The flight took one and a half hours in total.')
add('qty.a_half_an', r'(?i)\b(?P<target>a half an) (?:hour|inch|ounce|acre|apple|orange|onion|avocado|egg)\b', 'half an', 'Grammar', 0.93,
    'Use one article only: “half an hour”, not “a half an hour”.',
    'Wait a half an hour for it.', 'Wait half an hour for it, or a half hour.',
    'Wait half an hour for it.')
add('qty.halfs', r'(?i)\b(?P<target>halfs)\b', 'halves', 'Spelling', 0.95,
    'The plural of “half” is “halves”.',
    'Cut the cake into two halfs.', 'Cut the cake into two halves, then eat half.',
    'Cut the cake into two halves.')

W1 = r'(?:approximately|roughly|approx\.?|circa)'
W2 = r'(?:about|around|approximately|roughly|approx\.?|circa)'
NUMAFTER = r'\s(?:\d|a (?:hundred|thousand|million|dozen)|(?:' + ONES + '|' + TEENS + '|' + TENS + r'|hundred)\b)'
add('qty.approx_doubled_a', r'(?i)\b' + W1 + r'(?P<target> ' + W2 + r')' + NUMAFTER, '', 'Redundancy', 0.8,
    'Two approximating words say the same thing twice: “approximately 100”, not “approximately about 100”.',
    'There were approximately about 100 guests.', 'There were approximately 100 guests, or just about 100, or around about 100.',
    'There were approximately 100 guests.')
add('qty.approx_doubled_b', r'(?i)\b(?:about|around)(?P<target> (?:approximately|roughly|approx\.?|circa))' + NUMAFTER, '', 'Redundancy', 0.8,
    'Two approximating words say the same thing twice: “around 100”, not “around approximately 100”.',
    'There were about roughly 100 guests.', 'There were about 100 guests, or roughly 100, or around about 100.',
    'There were about 100 guests.')
add('qty.approx_about_around', r'(?i)\babout(?P<target> around)' + NUMAFTER, '', 'Redundancy', 0.8,
    'Two approximating words say the same thing twice: “about 100”, not “about around 100”.',
    'There were about around 100 guests.', 'There were about 100 guests, or around 100, or around about 100.',
    'There were about 100 guests.')

AREA = r'meters|metres|kilometers|kilometres|miles|feet|inches|centimeters|centimetres|yards|acres'
add('qty.squared_area', r'(?i)\b(?:\d+|' + ONES + '|' + TEENS + '|' + TENS + r'|hundred) (?P<target>squared) (?:' + AREA + r')\b', 'square', 'Word choice', 0.88,
    'An area is measured in “square” units: “20 square meters”.',
    'The flat is 40 squared meters.', 'The flat is 40 square meters, or 40 meters squared.',
    'The flat is 40 square meters.')
add('qty.cubed_volume', r'(?i)\b(?:\d+|' + ONES + '|' + TEENS + '|' + TENS + r'|hundred) (?P<target>cubed) (?:' + AREA + r')\b', 'cubic', 'Word choice', 0.88,
    'A volume is measured in “cubic” units: “10 cubic meters”.',
    'The tank holds 10 cubed meters.', 'The tank holds 10 cubic meters, or 10 meters cubed.',
    'The tank holds 10 cubic meters.')
add('qty.range_from_and',
    r'(?i)\b(?:range|ranges|ranged|ranging|vary|varies|varied|varying|run|runs|ran|extend|extends|extended|span|spans|spanned|ages|aged)(?: [a-z]+){0,2} from [$£€]?\d[\d,.]*(?: (?:years|days|weeks|months|hours|minutes|percent|degrees|dollars|km|kg|cm|mm))? (?P<target>and) [$£€]?\d',
    'to', 'Grammar', 0.9,
    'A range after “from” is “from … to …”, not “from … and …”.',
    'Prices range from $5 and $10 per item.', 'Prices range from $5 to $10 per item, or between $5 and $10.',
    'Prices range from $5 to $10 per item.')
