"""Holidays, festivals and religious seasons (Christmas, Easter, Diwali... are already in the gazetteer)."""
from lib import *

SIMPLE = """Eid|Eid Mubarak|Eid al-Fitr|Eid al-Adha|Eid ul-Fitr|Eid ul-Adha|Bakrid|Muharram|Ashura|Ramzan|Mawlid|Yom Kippur|
Rosh Hashanah|Purim|Sukkot|Shavuot|Simchat Torah|Navratri|Dussehra|Dasara|Holi|Raksha Bandhan|Rakhi|Janmashtami|
Ganesh Chaturthi|Onam|Pongal|Makar Sankranti|Lohri|Baisakhi|Vaisakhi|Durga Puja|Maha Shivaratri|Mahashivratri|
Karva Chauth|Bhai Dooj|Gurpurab|Guru Nanak Jayanti|Chhath Puja|Vijayadashami|Ugadi|Gudi Padwa|Bihu|Deepavali|
Buddha Purnima|Mahavir Jayanti|Ash Wednesday|Palm Sunday|Good Friday|Easter Sunday|Easter Monday|Maundy Thursday|
Holy Week|Pentecost|Christmas Eve|Christmas Day|Boxing Day|New Year's Day|New Year's Eve|Valentine's Day|Mother's Day|
Father's Day|St Patrick's Day|Saint Patrick's Day|April Fools' Day|April Fool's Day|Groundhog Day|Chinese New Year|
Lunar New Year|Mid-Autumn Festival|Dragon Boat Festival|Cinco de Mayo|Mardi Gras|Oktoberfest|Juneteenth|Hogmanay|
Bonfire Night|Guy Fawkes Night|Pancake Day|Black Friday|Cyber Monday|Songkran|Nowruz|Vesak|Obon|
Thanksgiving Day|Advent Sunday|Shrove Tuesday|Holy Saturday|Whit Sunday|
Rama Navami|Hanuman Jayanti|Ganesh Puja|Lakshmi Puja|Kali Puja|Saraswati Puja|Vasant Panchami|
Basant Panchami|Dhanteras|Govardhan Puja|Chhoti Diwali|Naraka Chaturdashi|Thaipusam|Poila Boishakh|Rath Yatra|Muharram|
Shab-e-Barat|Laylat al-Qadr|Isra and Mi'raj|Tu BiShvat|Lag BaOmer|Tisha B'Av|Selichot|Chanukah|Kwanza|Epiphany Eve""".replace('\n', '').split('|')
# "Kwanza" is the Angolan currency; the holiday is already in the gazetteer
SIMPLE = [s for s in SIMPLE if s not in {'Kwanza', 'Epiphany Eve', 'Chanukah', 'Isra and Mi\'raj', 'Selichot'}]

# Holiday names a writer can also use as plain words ("a labor day"): capitalized after a date frame only.
FRAMED = """Independence Day|Labor Day|Labour Day|Memorial Day|Veterans Day|Columbus Day|Republic Day|Canada Day|
Bastille Day|Australia Day|Anzac Day|Remembrance Day|Armistice Day|Earth Day|Presidents' Day|Flag Day|Arbor Day|
Teachers' Day|Children's Day|Women's Day|Gandhi Jayanti|Martin Luther King Day|Victory Day|Thanksgiving Weekend|
Veterans' Day|International Women's Day|World Environment Day|Mother's Day Weekend""".replace('\n', '').split('|')
FRAMED = [f for f in FRAMED if f not in {'Thanksgiving Weekend', 'Mother\'s Day Weekend'}]

FRAME = (r"(?i:\b(?:on|for|this|next|last|every|before|after|until|since|during|over|around|by|at|from|till|through|"
         r"of|to|and|or|the|each|since|till|until|happy|merry|early|late|mid)\s+)")


def build():
    fam = 'Holidays and festivals'
    for x in dict.fromkeys(SIMPLE):
        phrase_rule(f'caps.holiday.{slug(x)}', x, LEFT, RIGHT_H, 0.92,
                    'Names of holidays and festivals take a capital letter.',
                    'The office is closed on {x} this year.', fam)
    for x in dict.fromkeys(FRAMED):
        phrase_rule(f'caps.holiday.{slug(x)}', x, FRAME, RIGHT_H, 0.9,
                    'Names of holidays take a capital letter.',
                    'The office is closed on {x} this year.', fam)
    # Lent and Advent are ordinary words ("lent me", "the advent of"): capital only in a church-year frame.
    emit('caps.holiday.lent',
         r"(?i:\b(?:during|for|before|after|throughout|until|since|through|give up\s+\w+\s+for|giving up\s+\w+\s+for)\s+)(?P<target>(?-i:lent))(?:['’]s)?(?:\s*[,.;:!?)\]\"”’]|\s*$|\s+(?:and|or|this|next|last|every|each|but|so|as|to|in|is|begins|started|starts|ends|ended|season|period|fast|fasting|break|when)\b)",
         'Lent', 'Capitalization', 0.88, 'Lent, the church season, takes a capital letter.',
         'We give up sweets for lent every year.',
         'We give up sweets for Lent every year. She lent me a book, and he has lent us the van for now.', fam)
    emit('caps.holiday.advent_season',
         f"{LEFT}(?P<target>(?-i:advent))\\s+(?:calendar|calendars|wreath|wreaths|season|sunday|candles|candle|service|services)\\b",
         'Advent', 'Capitalization', 0.9, 'Advent, the church season, takes a capital letter.',
         'My daughter opens a chocolate from the advent calendar each morning.',
         'My daughter opens a chocolate from the Advent calendar each morning. The advent of cheap sensors changed the field.', fam)
    for ap, tag in [("'", ''), ('\u2019', '_curly')]:
        emit(f'caps.holiday.new_years_resolution{tag}',
             f"{LEFT}(?P<target>(?-i:new year{ap}s))\\s+(?:resolution|resolutions|party|eve|day|celebration|celebrations|fireworks|wish|wishes|card|cards)\\b",
             f"New Year{ap}s", 'Capitalization', 0.9, 'New Year’s takes capitals in a holiday name.',
             f"She made a new year{ap}s resolution to run daily.",
             f"She made a New Year{ap}s resolution to run daily.", fam)
    emit('caps.holiday.merry_christmas',
         f"{LEFT}(?P<target>(?-i:merry christmas)){RIGHT_H}",
         'Merry Christmas', 'Capitalization', 0.9, 'The greeting “Merry Christmas” takes capitals.',
         'We wish you a merry christmas and a safe trip.',
         'We wish you a Merry Christmas and a safe trip. ' + neg_noise('merry christmas'), fam)
    emit('caps.holiday.happy_holidays',
         f"{LEFT}(?P<target>(?-i:happy holidays)){RIGHT}",
         'Happy Holidays', 'Capitalization', 0.86, 'The seasonal greeting takes capitals.',
         'The card said happy holidays in gold letters.',
         'The card said Happy Holidays in gold letters.', fam)
