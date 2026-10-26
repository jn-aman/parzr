"""Compound modifiers with a number: "a three years old daughter" -> "a three-year-old daughter", "a 10 minutes walk"
-> "a 10-minute walk", "a 20 dollar bill" -> "a 20-dollar bill". The engine's own hyphen pass (marks.rs) already joins
a number, a singular unit from its list and a noun ("a 30 day trial", "a 5 year old"); the pack adds what that pass
leaves: plural units, ages written with "years old", and units it does not know."""
from core import add, cover, IDS

DET = r"(?:a|an|the|my|your|his|her|our|their|this|that|another|each|every|one|any|its)"
WORD_NUM = ('one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|'
            'eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|'
            '(?:twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)-(?:one|two|three|four|five|six|seven|eight|nine)')
NUM = rf"(?:\d{{1,3}}|{WORD_NUM})"
TENS = 'twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety'
UNITS9 = 'one|two|three|four|five|six|seven|eight|nine'

# unit (singular) -> (head nouns that follow it in a compound modifier, example sentence)
TIME_UNITS = {
    'minute': ('walk|drive|ride|break|delay|wait|video|call|meeting|speech|presentation|interview|session|nap|tour|flight|trip|trek|read|test|quiz|task|intro|clip|segment|commute|shower|workout|lesson|talk|chat',
               'It is a {n} {u} walk from here.'),
    'hour': ('drive|flight|ride|trip|meeting|session|workshop|class|lecture|course|shift|delay|wait|journey|tour|walk|hike|call|nap|video|movie|film|show|test|exam|commute|training|layover',
             'We had a {n} {u} drive to the coast.'),
    'day': ('trip|tour|course|workshop|event|festival|journey|holiday|vacation|hike|trek|retreat|conference|training|cruise|delay|trial|ban|sale|fast|cleanse|diet|program|programme|plan|challenge|itinerary|weekend|break',
            'They booked a {n} {u} trip to the lake.'),
    'week': ('course|trip|vacation|holiday|program|programme|plan|challenge|trial|delay|period|cycle|break|training|internship|workshop|bootcamp|sprint|hiatus',
             'She joined a {n} {u} course in the city.'),
    'month': ('contract|lease|trial|period|plan|course|program|programme|subscription|warranty|internship|probation|ban|delay|sentence|cycle|break|leave|wait|timeline',
              'He signed a {n} {u} contract with the club.'),
    'year': ('contract|lease|plan|warranty|program|programme|course|degree|term|period|sentence|ban|loan|mortgage|deal|cycle|strategy|gap|high|low|investment|trend|forecast|guarantee|project|study',
             'They offer a {n} {u} warranty on the engine.'),
    'mile': ('run|walk|hike|drive|race|trek|trip|radius|stretch|journey|commute|ride',
             'We went on a {n} {u} hike before lunch.'),
    'page': ('report|document|essay|paper|letter|brochure|manual|book|article|proposal|thesis|summary|guide|pdf|spreadsheet|story|contract|agreement|memo|booklet',
             'He wrote a {n} {u} report on the trip.'),
    'word': ('essay|limit|summary|article|story|post|poem|paragraph|document|abstract',
             'She wrote a {n} {u} essay about the river.'),
    'dollar': ('bill|fee|fine|bonus|coupon|voucher|gift|charge|bet|ticket|increase|raise|discount|refund|deposit|payment|donation|note|coin|tip',
               'He gave the boy a {n} {u} bill.'),
    'pound': ('note|coin|fee|fine|bag|box|bonus|bet|increase|raise|discount|refund|deposit|payment|donation|ticket|tip|gift|voucher',
              'She paid a {n} {u} fee at the gate.'),
    'euro': ('note|coin|fee|fine|bonus|bet|increase|raise|discount|refund|deposit|payment|donation|ticket|tip|gift|voucher',
             'He paid a {n} {u} fee at the gate.'),
    'person': ('team|room|tent|table|boat|sofa|crew|band|panel|committee|group|bus',
               'We booked a {n} {u} tent for the weekend.'),
    'man': ('team|crew|band|job|show|squad', 'They sent a {n} {u} crew to fix the line.'),
    'seat': ('sofa|car|plane|van|bus|minibus|jet', 'They rented a {n} {u} van for the trip.'),
    'room': ('apartment|flat|house|suite|hotel|cottage|bungalow|villa', 'We found a {n} {u} apartment near the park.'),
    'storey': ('building|house|tower|apartment|block|structure|car park|garage|hotel', 'They built a {n} {u} building by the river.'),
    'story': ('building|house|tower|apartment|block|structure|car park|garage|hotel', 'They built a {n} {u} building by the river.'),
    'lane': ('road|highway|motorway|street|pool', 'They widened it to a {n} {u} road.'),
    'piece': ('suit|set|band|puzzle|jigsaw|bucket|meal|orchestra|combo', 'He wore a {n} {u} suit to the interview.'),
    'course': ('meal|dinner|lunch|menu|tasting', 'We had a {n} {u} dinner at the inn.'),
    'door': ('sedan|car|hatchback|fridge|cabinet|wardrobe', 'They drive a {n} {u} sedan.'),
    'cylinder': ('engine|motor', 'It has a {n} {u} engine.'),
    'speed': ('gearbox|bike|transmission|fan|blender', 'She bought a {n} {u} bike.'),
    'ton': ('truck|crane|weight|bomb|load|press', 'A {n} {u} truck blocked the road.'),
    'kilo': ('bag|weight|dumbbell|box|parcel', 'He carried a {n} {u} bag up the hill.'),
    'kilogram': ('bag|weight|dumbbell|box|parcel', 'He carried a {n} {u} bag up the hill.'),
    'litre': ('bottle|tank|engine|jug|barrel|bucket', 'She filled a {n} {u} bottle at the tap.'),
    'liter': ('bottle|tank|engine|jug|barrel|bucket', 'She filled a {n} {u} bottle at the tap.'),
    'gallon': ('tank|bucket|jug|drum', 'He bought a {n} {u} tank for the garden.'),
    'megapixel': ('camera|sensor|photo|image', 'The phone has a {n} {u} camera.'),
    'inch': ('screen|display|pipe|nail|blade|heel|wheel|pan|pizza', 'He bought a {n} {u} screen for the desk.'),
    'metre': ('wall|fence|drop|pole|ladder|rope|plank|hedge|tunnel|race|sprint', 'They built a {n} {u} fence around the yard.'),
    'meter': ('wall|fence|drop|pole|ladder|rope|plank|hedge|tunnel|race|sprint', 'They built a {n} {u} fence around the yard.'),
}
# Units that are compound modifiers whether or not a noun follows: "a 4 digit code", "a six figure salary".
BARE_UNITS = {
    'bathroom': 'The cabin has a {n} {u} layout.', 'digit': 'Enter a {n} {u} code.', 'figure': 'She earns a {n} {u} salary.',
}
NUMBER_SAMPLES = {'minute': '10', 'hour': 'two', 'day': 'three', 'week': '6', 'month': 'six', 'year': 'five', 'mile': '5',
                  'page': '20', 'word': '500', 'dollar': '20', 'pound': '10', 'euro': '50', 'person': 'four', 'man': 'three',
                  'seat': '7', 'room': 'two', 'storey': 'three', 'story': '5', 'lane': 'four', 'piece': 'three', 'course': 'three',
                  'door': '4', 'cylinder': 'six', 'speed': '21', 'ton': '10', 'kilo': '5', 'kilogram': '10', 'litre': '2',
                  'liter': '5', 'gallon': '5', 'megapixel': '12', 'inch': '12', 'metre': '2', 'meter': '2',
                  'bathroom': '2', 'digit': '4', 'figure': 'six'}
# Units the engine's own hyphen pass (marks.rs, UNITS) already joins when the unit is singular and a number comes
# first ("a 30 day trial", "a 3 bedroom flat", "a 5 year old").
BASE_UNITS = {'second', 'minute', 'hour', 'day', 'night', 'week', 'month', 'year', 'mile', 'kilometer', 'meter', 'metre',
              'foot', 'inch', 'page', 'step', 'person', 'bedroom', 'star', 'point', 'piece', 'word'}


def build():
    # ---- age: the forms the engine's pass leaves ("a 3 years old", "a five-year old", "a five year-old")
    ids = []
    for unit in ['year', 'month', 'week', 'day']:
        age = rf"(?: {unit}-old|-{unit} old|[ -]{unit}s[ -]old)"
        ids.append(add(
            f'age_{unit}', rf"(?i)\b{DET} {NUM}(?P<target>{age})\b", f'-{unit}-old', 'Punctuation', 0.88,
            f'Before a noun, an age is hyphenated and singular: “a five-{unit}-old child”.',
            {'year': 'My three years old daughter loves the zoo.', 'month': 'The 6 months old puppy is very calm.',
             'week': 'Their two week-old kitten sleeps all day.', 'day': 'A three-day old chick was in the box.'}[unit],
            {'year': 'My three-year-old daughter loves the zoo. She is three years old.',
             'month': 'The 6-month-old puppy is very calm. The puppy is six months old.',
             'week': 'Their two-week-old kitten sleeps all day. It is two weeks old.',
             'day': 'A three-day-old chick was in the box. It is three days old.'}[unit]))
        ids.append(add(
            f'age_tens_{unit}',
            rf"(?i)\b{DET} (?:{TENS})[ -](?:{UNITS9})(?P<target>(?: {unit}-old|-{unit} old|[ -]{unit}s[ -]old))\b",
            f'-{unit}-old', 'Punctuation', 0.88,
            f'Before a noun, an age is hyphenated and singular: “a twenty-five-{unit}-old”.',
            {'year': 'He met a twenty five years old nurse.', 'month': 'She has a twenty four months old son.',
             'week': 'They adopted a thirty two weeks old calf.', 'day': 'It was a twenty one days old chick.'}[unit],
            {'year': 'He met a twenty-five-year-old nurse. She is twenty-five years old.',
             'month': 'She has a twenty-four-month-old son. He is twenty-four months old.',
             'week': 'They adopted a thirty-two-week-old calf. It is thirty-two weeks old.',
             'day': 'It was a twenty-one-day-old chick. It is twenty-one days old.'}[unit]))
    cover('Numbers as compound modifiers', "ages before a noun that the engine's own hyphen pass (marks.rs) leaves: a 3 years old, a 6 months old, a 5-years-old, a three-day old, a five year-old -> five-year-old (the plain \"a 5 year old\" is joined by the engine already); the canonical \"a five-year-old\" is never touched", ids)

    # ---- unit compounds the engine's pass does not join
    ids = []
    for unit, (nouns, ex) in TIME_UNITS.items():
        n = NUMBER_SAMPLES[unit]
        plural_unit = unit + 's'
        if unit in BASE_UNITS:
            # the engine joins "10 minute walk"; the plural unit ("10 minutes walk") is left to the pack
            ids.append(add(
                f'unit_plural_{unit}', rf"(?i)\b{DET} {NUM}(?P<target> (?P<u>{unit})s) (?:{nouns})\b",
                '-${u}', 'Punctuation', 0.85,
                f'When a number and a unit describe a noun, hyphenate them and keep the unit singular: “a {n}-{unit} …”.',
                ex.format(n=n, u=plural_unit),
                ex.format(n=n, u=unit).replace(f'{n} {unit}', f'{n}-{unit}') + f' It was {n} {plural_unit} long.'))
        else:
            ids.append(add(
                f'unit_{unit}', rf"(?i)\b{DET} {NUM}(?P<target> (?P<u>{unit})s?) (?:{nouns})\b",
                '-${u}', 'Punctuation', 0.85,
                f'When a number and a unit describe a noun, hyphenate them and keep the unit singular: “a {n}-{unit} …”.',
                ex.format(n=n, u=unit),
                ex.format(n=n, u=unit).replace(f'{n} {unit}', f'{n}-{unit}') + f' It was {n} {plural_unit} long.'))
    for unit, ex in BARE_UNITS.items():
        n = NUMBER_SAMPLES[unit]
        ids.append(add(
            f'unit_{unit}', rf"(?i)\b{DET} {NUM}(?P<target> (?P<u>{unit}))\b", '-${u}', 'Punctuation', 0.85,
            f'When a number and a unit describe a noun, hyphenate them: “a {n}-{unit}”.',
            ex.format(n=n, u=unit), ex.format(n=n, u=unit).replace(f'{n} {unit}', f'{n}-{unit}') + f' It has {n} {unit}s.'))
    cover('Numbers as compound modifiers', "a number + unit before a noun that the engine's own pass leaves: the plural unit (a 10 minutes walk, a two hours drive, a 3 days trip, a six months contract ...), and units it does not know: dollar, pound, euro, man, seat, room, storey, story, lane, course, door, cylinder, speed, ton, kilo, litre, gallon, megapixel, bathroom, digit, figure, seater (a 20 dollar bill, a four person tent, a three storey building, a 4 digit code, a six figure salary ...). The singular forms the engine joins (a 10 minute walk, a 3 bedroom flat, a 5 star hotel, a 30 day trial) are covered by its own pass", ids)
