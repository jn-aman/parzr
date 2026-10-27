"""Mass nouns used with a plural "s" ("feedbacks", "luggages"): the plural is wrong in standard English. Words that
double as verbs ("stuffs", "traffics", "weathers", "progresses") are left out."""
from lib import R

# (plural, singular, positive sentence, expected, negative sentence, lead pattern or None)
WORDS = [
    ('luggages', 'luggage', 'Please collect your luggages at the airport.', 'Please collect your luggage at the airport.', 'Please collect your luggage at the airport. Pack light.', None),
    ('baggages', 'baggage', 'Keep your baggages near you.', 'Keep your baggage near you.', 'Keep your baggage near you. He carries emotional baggage.', None),
    ('knowledges', 'knowledge', 'He has good knowledges of sales.', 'He has good knowledge of sales.', 'He has good knowledge of sales. Knowledge is power.', None),
    ('hardwares', 'hardware', 'We buy hardwares from two vendors.', 'We buy hardware from two vendors.', 'We buy hardware from two vendors. The hardware is old.', None),
    ('jewelleries', 'jewellery', 'She sold her jewelleries last year.', 'She sold her jewellery last year.', 'She sold her jewellery last year. The shop sells jewellery.', None),
    ('jewelries', 'jewelry', 'She sold her jewelries last year.', 'She sold her jewelry last year.', 'She sold her jewelry last year. The shop sells jewelry.', None),
    ('machineries', 'machinery', 'The factory bought new machineries.', 'The factory bought new machinery.', 'The factory bought new machinery. Heavy machinery is loud.', None),
    ('stationeries', 'stationery', 'We ordered stationeries for the office.', 'We ordered stationery for the office.', 'We ordered stationery for the office. The stationery arrived.', None),
    ('cutleries', 'cutlery', 'Please bring the cutleries to the table.', 'Please bring the cutlery to the table.', 'Please bring the cutlery to the table. The cutlery is clean.', None),
    ('sceneries', 'scenery', 'We loved the sceneries in Kerala.', 'We loved the scenery in Kerala.', 'We loved the scenery in Kerala. The scenery was calm.', None),
    ('garbages', 'garbage', 'Put the garbages in the bin.', 'Put the garbage in the bin.', 'Put the garbage in the bin. The garbage truck came.', None),
    ('applauses', 'applause', 'The speech got loud applauses.', 'The speech got loud applause.', 'The speech got loud applause. The applause was long.', None),
    ('pollutions', 'pollution', 'The city fights air and water pollutions.', 'The city fights air and water pollution.', 'The city fights air and water pollution. Pollution is down.', None),
    ('poetries', 'poetry', 'She reads old poetries at night.', 'She reads old poetry at night.', 'She reads old poetry at night. Poetry slams are fun.', None),
    ('lightnings', 'lightning', 'The lightnings scared the children.', 'The lightning scared the children.', 'The lightning scared the children. The sky was dark.', None),
    ('staffs', 'staff', 'Our staffs are very helpful.', 'Our staff are very helpful.',
     'Our staff are very helpful. The hotel staff were kind. He carried two walking staffs in the pack.',
     r'(?:our|their|his|her|my|your|all|many|other|more|few|several|good|new|senior|junior|support|office|hospital|school)'),
]


def build():
    R('mass.feedback',
      r'(?i)\b(?:your|our|my|his|her|their|customer|client|user|student|employee|peer|team|manager|reviewer|reader|audience|give|gave|giving|gives|share|shared|sharing|send|sent|sending|provide|provided|providing|collect|collected|collecting|receive|received|receiving|get|got|getting|take|took|taking|post|posted|leave|left|read|reading|ask|asked|asking|need|needs|want|wants) (?P<target>feedbacks)\b',
      'feedback', 'Grammar', 0.9, '“Feedback” is not counted: say “feedback”, not “feedbacks”.',
      'Please share your feedbacks by Friday.', 'Please share your feedback by Friday.',
      'Please share your feedback by Friday. The feedback loop is short. Cascading biophysical feedbacks amplify the warming.')
    for plural, singular, pos, exp, neg, lead in WORDS:
        if plural == 'staffs':
            continue
        R(f'mass.{singular}', rf'(?i)\b(?P<target>{plural})\b', singular, 'Grammar', 0.9,
          f'“{singular.capitalize()}” is not counted: say “{singular}”, not “{plural}”.', pos, exp, neg)
    R('mass.staff', r'(?i)\b(?:our|their|his|her|my|your|all|many|other|more|few|several|good|new|senior|junior|support|office|hospital|school) (?P<target>staffs)\b',
      'staff', 'Grammar', 0.88, '“Staff” names the group of workers and takes no plural “s”: “our staff”.',
      'Our staffs are very helpful.', 'Our staff are very helpful.',
      'Our staff are very helpful. The hotel staff were kind. He carried two walking staffs in the pack.')
