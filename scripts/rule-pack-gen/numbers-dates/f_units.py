"""Units: singular after a count, plural after "1", "kms", "kilometre per hours", "10 meters length"."""
from lib import add, q, CARD2U, TAIL, ONES, TEENS, TENS

LEAD = r'(?:^|[^/\s]\s+|\()'   # a number is not read after a slash ("1 / 2 second", "5 / 4 time")
NUMW = r'(?:' + ONES + '|' + TEENS + '|' + TENS + r'|hundred)'

TIME = ['second', 'minute', 'hour', 'day', 'week', 'month', 'year']
MEASURE = ['kilometre', 'kilometer', 'metre', 'meter', 'centimetre', 'centimeter', 'millimetre', 'millimeter', 'mile',
           'kilogram', 'gram', 'litre', 'liter', 'gallon', 'ounce', 'acre', 'hectare', 'tonne', 'yard']
COUNT = {'second': '30', 'minute': '15', 'hour': '2', 'day': '3', 'week': '4', 'month': '6', 'year': '10'}
# A natural sentence for each unit; the unit closes the phrase (a function word follows), so a modifier such as "a 5 mile walk" never matches.
SENT = {'second': 'The clip lasts {n} {u} in total.', 'minute': 'The video runs {n} {u} in total.', 'hour': 'The trip took {n} {u} in total.',
        'day': 'The trip took {n} {u} in total.', 'week': 'The course runs {n} {u} in total.', 'month': 'The contract runs {n} {u} in total.',
        'year': 'The lease runs {n} {u} in total.',
        'kilometre': 'The village is {n} {u} away.', 'kilometer': 'The village is {n} {u} away.',
        'metre': 'The shed is {n} {u} away.', 'meter': 'The shed is {n} {u} away.',
        'centimetre': 'Cut it {n} {u} from the edge.', 'centimeter': 'Cut it {n} {u} from the edge.',
        'millimetre': 'Cut it {n} {u} from the edge.', 'millimeter': 'Cut it {n} {u} from the edge.',
        'mile': 'The beach is {n} {u} away.', 'kilogram': 'The parcel weighs {n} {u} in total.', 'gram': 'Add {n} {u} of sugar.',
        'litre': 'The tank holds {n} {u} of oil.', 'liter': 'The tank holds {n} {u} of oil.', 'gallon': 'The tank holds {n} {u} of fuel.',
        'ounce': 'Add {n} {u} of butter.', 'acre': 'The farm covers {n} {u} in total.', 'hectare': 'The farm covers {n} {u} in total.',
        'tonne': 'The truck carries {n} {u} of sand.', 'yard': 'The goal is {n} {u} away.'}
for u in TIME + MEASURE:
    n = COUNT.get(u, '5')
    pos = SENT[u].format(n=n, u=u)
    ok = SENT[u].format(n=n, u=u + 's')
    add(f'unit.{u}_after_count',
        r'(?i)' + LEAD + CARD2U + r' (?P<target>(?P<u>(?-i:' + u + r')))' + TAIL, '${u}s', 'Grammar', 0.9,
        f'After a number above one the unit is plural: “{n} {u}s”.',
        pos, ok + f' A {n} {u} walk and a 1 {u} wait are fine.', ok)

add('unit.inch_after_count', r'(?i)' + LEAD + CARD2U + r' (?P<target>(?-i:inch))' + TAIL, 'inches', 'Grammar', 0.9,
    'After a number above one the plural of “inch” is “inches”: “5 inches”.',
    'The track is 5 inch away.', 'The track is 5 inches away. A 5 inch heel and a 1 inch gap are fine.',
    'The track is 5 inches away.')
add('unit.time_plural_after_one', r'(?i)' + LEAD + r'1 (?P<target>(?P<u>(?-i:second|minute|hour|day|week|month|year))s)\b', '${u}', 'Grammar', 0.9,
    'Exactly 1 takes the singular: “1 hour”, “1 week”.',
    'It takes 1 hours to get there.', 'It takes 1 hour to get there, or 1.5 hours, or 10 hours.',
    'It takes 1 hour to get there.')
add('unit.measure_plural_after_one',
    r'(?i)' + LEAD + r'1 (?P<target>(?P<u>(?-i:kilometre|kilometer|metre|meter|centimetre|centimeter|millimetre|millimeter|mile|kilogram|gram|litre|liter|gallon|ounce|acre|hectare|tonne|yard))s)\b',
    '${u}', 'Grammar', 0.9,
    'Exactly 1 takes the singular: “1 mile”, “1 kilogram”.',
    'The shop is 1 miles from here.', 'The shop is 1 mile from here, or 1.5 miles, or 10 miles.',
    'The shop is 1 mile from here.')
add('unit.inches_after_one', r'(?i)' + LEAD + r'1 (?P<target>(?-i:inches))\b', 'inch', 'Grammar', 0.9,
    'Exactly 1 takes the singular: “1 inch”.',
    'The gap is 1 inches wide.', 'The gap is 1 inch wide, or 12 inches.',
    'The gap is 1 inch wide.')
add('unit.feet_after_one', r'(?i)' + LEAD + r'1 (?P<target>(?-i:feet))\b', 'foot', 'Grammar', 0.9,
    'Exactly 1 takes the singular: “1 foot”.',
    'The gap is 1 feet wide.', 'The gap is 1 foot wide, or 6 feet, or 5 feet 1 inch.',
    'The gap is 1 foot wide.')
add('unit.foots', r'(?i)' + LEAD + r'(?:' + CARD2U + r') (?P<target>foots)\b', 'feet', 'Spelling', 0.95,
    'The plural of “foot” is “feet”.',
    'He is 6 foots tall.', 'He is 6 feet tall, or 6 foot tall.',
    'He is 6 feet tall.')
add('unit.degree_singular',
    r'(?i)\b(?:is|was|are|were|reached|hit|at|about|around|from|below|above) ' + CARD2U + r' (?P<target>(?-i:degree))(?: (?:celsius|centigrade|fahrenheit)(?:[.,;:!?)]|$|\s+(?:outside|inside|out|today|there|here)\b)|[.,;:!?)]|$| (?:outside|inside|out|today|there|here|below|above)\b)',
    'degrees', 'Grammar', 0.9,
    'After a number above one, “degrees” is plural: “20 degrees Celsius”.',
    'It was 30 degree Celsius outside.', 'It was 30 degrees Celsius outside, and a 30 degree slope is steep.',
    'It was 30 degrees Celsius outside.')

# Abbreviated units take no plural "s"
for ab, full, ex in [('kms', 'km', 'The trip is 5 kms long.'), ('cms', 'cm', 'Add 10 cms of water.'), ('mms', 'mm', 'The rain was 8 mms deep.'),
                     ('kgs', 'kg', 'The bag weighs 70 kgs in total.'), ('gms', 'g', 'Add 200 gms of sugar.')]:
    add(f'unit.abbr_{ab}', r'(?i)\b\d+(?:[.,]\d+)? (?P<target>(?-i:' + ab + r'))\b', full, 'Register', 0.75,
        f'A unit symbol has no plural “s”: write “{full}”.',
        ex, ex.replace(ab, full) + f' The {ab.upper()} team met too.',
        ex.replace(ab, full))
add('unit.kmph', r'(?i)\b\d+(?:[.,]\d+)? (?P<target>(?-i:kmph))\b', 'km/h', 'Register', 0.75,
    'The standard symbol for kilometres per hour is “km/h”.',
    'The limit is 60 kmph here.', 'The limit is 60 km/h here, or 40 mph, or 60 kph.',
    'The limit is 60 km/h here.')
add('unit.per_hours', r'(?i)\b(?:miles|kilometres|kilometers|metres|meters|feet|km|mi|mph) per (?P<target>(?P<u>hour|second|minute)s)\b', '${u}', 'Grammar', 0.93,
    'After “per” the unit is singular: “miles per hour”, “metres per second”.',
    'The car does 90 miles per hours.', 'The car does 90 miles per hour, and 3 meters per second.',
    'The car does 90 miles per hour.')
add('unit.count_per_hour', r'(?i)\b' + CARD2U + r' (?P<target>(?P<u>(?-i:kilometre|kilometer|mile|metre|meter))) per (?:hour|second|minute)\b', '${u}s', 'Grammar', 0.9,
    'After a number above one the unit is plural: “100 kilometres per hour”.',
    'The car does 100 kilometre per hour.', 'The car does 100 kilometres per hour, or 1 mile per hour.',
    'The car does 100 kilometres per hour.')
UNITS = r'(?:meters|metres|feet|miles|inches|km|kilometers|kilometres|yards|centimeters|centimetres|cm|mm|m)'
for noun, adj in [('length', 'long'), ('width', 'wide'), ('height', 'high'), ('depth', 'deep')]:
    add(f'unit.{noun}_for_{adj}',
        r'(?i)\b(?:is|are|was|were) (?:about |around |roughly |nearly |almost |only )?(?:\d+|' + NUMW + r') ' + UNITS + r' (?P<target>' + noun + r')(?:[.,;:!?)]|$)',
        adj, 'Grammar', 0.9,
        f'Use the adjective “{adj}” after a measurement: “10 meters {adj}”.',
        f'The pool is 25 meters {noun}.', f'The pool is 25 meters {adj}, and a 25 meters {noun} of rope is long.'.replace(f'a 25 meters {noun} of rope is long', 'the rope is 25 meters in ' + noun),
        f'The pool is 25 meters {adj}.')
add('unit.lasts_long', r'(?i)\b(?:lasts?|lasted|takes?|took|taking) (?:about |around |nearly |almost |roughly |approximately |only |just )?(?:\d+|' + NUMW + r') (?:hours?|minutes?|days?|weeks?|months?|years?|seconds?)(?P<target> long)\b', '', 'Redundancy', 0.75,
    '“Lasts” already measures time: “it lasts three hours”, not “three hours long”.',
    'The session lasts 3 hours long.', 'The session lasts 3 hours, and the film runs two hours long.'.replace(', and the film runs two hours long', ', and the film is 2 hours long'),
    'The session lasts 3 hours.')

# Computing, cooking and electrical units
for u_, n, ctx in [('pixel', '300', 'The border is {n} {u} from the edge.'), ('byte', '64', 'The header is {n} {u} in total.'),
                   ('kilobyte', '20', 'The file is {n} {u} in total.'), ('megabyte', '50', 'The file is {n} {u} in total.'),
                   ('gigabyte', '16', 'The laptop has {n} {u} of memory.'), ('terabyte', '2', 'The drive holds {n} {u} of data.'),
                   ('calorie', '200', 'The snack has {n} {u} in total.'), ('watt', '60', 'The lamp uses {n} {u} of power.'),
                   ('volt', '12', 'The battery gives {n} {u} of power.'), ('kilowatt', '5', 'The motor draws {n} {u} of power.'),
                   ('cup', '2', 'Add {n} {u} of flour.'), ('tablespoon', '3', 'Add {n} {u} of oil.'), ('teaspoon', '2', 'Add {n} {u} of salt.')]:
    pos = ctx.format(n=n, u=u_)
    add(f'unit.{u_}_after_count', r'(?i)' + LEAD + CARD2U + r' (?P<target>(?P<u>(?-i:' + u_ + r')))' + TAIL, '${u}s', 'Grammar', 0.9,
        f'After a number above one the unit is plural: “{n} {u_}s”.',
        pos, ctx.format(n=n, u=u_ + 's') + f' A {n} {u_} gap is fine.', ctx.format(n=n, u=u_ + 's'))

# Capitalised or abbreviated symbols
add('unit.km_capital', r'(?i)\b\d+(?:[.,]\d+)?(?P<target> (?-i:Km|Kms))\b', ' km', 'Capitalization', 0.9,
    'The symbol for kilometre is lowercase: “5 km”.',
    'The house is 5 Km from here.', 'The house is 5 km from here, near the KM office.',
    'The house is 5 km from here.')
add('unit.kg_capital', r'(?i)\b\d+(?:[.,]\d+)?(?P<target> (?-i:Kg|Kgs))\b', ' kg', 'Capitalization', 0.9,
    'The symbol for kilogram is lowercase: “5 kg”.',
    'The box weighs 5 Kg in total.', 'The box weighs 5 kg in total, and the Kg label is old.',
    'The box weighs 5 kg in total.')
add('unit.abbr_mtrs', r'(?i)\b\d+(?:[.,]\d+)? (?P<target>(?-i:mtrs?))\b', 'm', 'Register', 0.75,
    'The symbol for metre is “m”: write “12 m” or “12 metres”.',
    'The pool is 12 mtrs long.', 'The pool is 12 m long, or 12 metres long.',
    'The pool is 12 m long.')
