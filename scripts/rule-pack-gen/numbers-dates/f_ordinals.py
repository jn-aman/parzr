"""Ordinals: wrong suffix after a digit (1th, 2th, 3th, 4rd), misspelt ordinal words, a missing suffix after
"the 5 of May" / "the 20 century" / "the 3 floor"."""
from lib import add, MONTHS, q

# A digit run just after a space, a bracket or a quote, so "v1th", "0.1th" and identifiers are never read as ordinals.
LEAD = "(?:^|[^/\\d\\s]\\s+|[(“\"'])"
ST_N = r'(?:\d*[02-9])?1'      # 1, 21, 101 (not 11)
ND_N = r'(?:\d*[02-9])?2'
RD_N = r'(?:\d*[02-9])?3'
TH_N = r'(?:\d*[04-9]|\d*1[123])'   # 4-9, 10, 14-20, 11-13, 111 ...

add('ord.th_for_1', r'(?i)' + LEAD + ST_N + r'(?P<target>(?-i:th))\b', 'st', 'Spelling', 0.95,
    'A number ending in 1 (except 11) takes “st”: write “1st”, “21st”, “31st”.',
    'We met on January 1th at noon.', 'She finished 11th, the 111th runner was 21st and he came 1st.',
    'We met on January 1st at noon.')
add('ord.th_for_1b', r'(?i)' + LEAD + r'(?:\d*[02-9])?1(?P<target>(?-i:nd|rd))\b', 'st', 'Spelling', 0.95,
    'A number ending in 1 (except 11) takes “st”: write “1st”, “21st”, “31st”.',
    'It was her 21rd birthday.', 'It was her 21st birthday and his 1st try, then 2nd and 3rd.',
    'It was her 21st birthday.')
add('ord.th_for_2', r'(?i)' + LEAD + ND_N + r'(?P<target>(?-i:th))\b', 'nd', 'Spelling', 0.95,
    'A number ending in 2 (except 12) takes “nd”: write “2nd”, “22nd”.',
    'This is the 2th time I have asked.', 'This is the 2nd time, after the 12th and the 112th, on the 22nd.',
    'This is the 2nd time I have asked.')
add('ord.th_for_2b', r'(?i)' + LEAD + r'(?:\d*[02-9])?2(?P<target>(?-i:st|rd))\b', 'nd', 'Spelling', 0.95,
    'A number ending in 2 (except 12) takes “nd”: write “2nd”, “22nd”.',
    'Her 2st medal came today.', 'Her 2nd medal came on the 22nd day, and she weighs 12st.',
    'Her 2nd medal came today.')
add('ord.th_for_3', r'(?i)' + LEAD + RD_N + r'(?P<target>(?-i:th))\b', 'rd', 'Spelling', 0.95,
    'A number ending in 3 (except 13) takes “rd”: write “3rd”, “23rd”.',
    'He came 3th in the race.', 'He came 3rd, she came 13th, and the 23rd lap was quick.',
    'He came 3rd in the race.')
add('ord.th_for_3b', r'(?i)' + LEAD + r'(?:\d*[02-9])?3(?P<target>(?-i:st|nd))\b', 'rd', 'Spelling', 0.95,
    'A number ending in 3 (except 13) takes “rd”: write “3rd”, “23rd”.',
    'Our 3st attempt was the last.', 'Our 3rd attempt was the 23rd one, and the 13th was last.',
    'Our 3rd attempt was the last.')
add('ord.th_after_teen', r'(?i)' + LEAD + r'\d*1(?:1|2|3)(?P<target>(?-i:nd|rd))\b', 'th', 'Spelling', 0.95,
    'Numbers from 11 to 13 take “th”: write “11th”, “12th”, “13th”.',
    'She came 13rd in the race.', 'She came 13th and he came 12th, and the 22nd and 23rd followed.',
    'She came 13th in the race.')
add('ord.th_after_other', r'(?i)' + LEAD + r'\d*(?:0|4|5|6|7|8|9)(?P<target>(?-i:nd|rd))\b', 'th', 'Spelling', 0.93,
    'Ordinals other than 1st, 2nd and 3rd end in “th”: write “4th”, “5th”, “20th”.',
    'The 4rd floor is closed today.', 'The 4th floor is closed and the 20th is open, near the 2nd and 3rd.',
    'The 4th floor is closed today.')

add('ord.word_twelfth', r'(?i)\b(?P<target>twelveth|twelvth)\b', 'twelfth', 'Spelling', 0.97,
    'The ordinal for 12 is spelt “twelfth”.',
    'It was the twelveth day of the trip.', 'It was the twelfth day of the trip, after the eleventh.',
    'It was the twelfth day of the trip.')
add('ord.word_ieth', r'(?i)\b(?:twent|thirt|fort|fift|sixt|sevent|eight|ninet)(?P<target>yth|yeth|ith)\b', 'ieth', 'Spelling', 0.97,
    'The ordinal of a round ten ends in “-ieth”: “twentieth”, “thirtieth”, “fortieth”.',
    'She celebrated her twentyth birthday.', 'She celebrated her twentieth birthday and his fortieth.',
    'She celebrated her twentieth birthday.')
add('ord.word_fortieth', r'(?i)\b(?P<target>fourtieth)\b', 'fortieth', 'Spelling', 0.97,
    '“Forty” loses the “u”, so the ordinal is “fortieth”.',
    'The fourtieth anniversary was lovely.', 'The fortieth anniversary was lovely.',
    'The fortieth anniversary was lovely.')

SUFFIX = [('st', ST_N, '1st, 21st'), ('nd', ND_N, '2nd, 22nd'), ('rd', RD_N, '3rd, 23rd'), ('th', TH_N, '4th, 11th, 20th')]
DAYS = {'st': (r'(?:1|21|31)', '1', '1st'), 'nd': (r'(?:2|22)', '22', '22nd'), 'rd': (r'(?:3|23)', '3', '3rd'),
        'th': (r'(?:[4-9]|1\d|20|2[4-9]|30)', '5', '5th')}
for suf, _, ex in SUFFIX:
    pat, n, nth = DAYS[suf]
    add(f'ord.day_of_month_{suf}', r'(?i)\bthe ' + pat + r'(?P<target> of (?P<m>' + MONTHS + r'))\b', suf + r' of ${m}',
        'Grammar', 0.93, f'A date such as “the {nth} of May” needs its ordinal ending: “{nth}”.',
        f'We arrive on the {n} of June.', f'We arrive on the {nth} of June, or on 5 June.',
        f'We arrive on the {n}{suf} of June.')
CENT = {'st': r'(?:1|21)', 'nd': r'2', 'rd': r'3', 'th': r'(?:[4-9]|1\d|20)'}
CEX = {'st': ('21', '21st'), 'nd': ('2', '2nd'), 'rd': ('3', '3rd'), 'th': ('20', '20th')}
for suf in ('st', 'nd', 'rd', 'th'):
    n, nth = CEX[suf]
    add(f'ord.century_{suf}', r'(?i)\bthe ' + CENT[suf] + r'(?P<target> century)(?:[,.;:!?)]|$|\s+(?:and|or|but|when|was|were|is|are|to|in|of|ago|onwards|BC|AD|BCE|CE)\b)', suf + r' century',
        'Grammar', 0.93, f'A century is written as an ordinal: “the {nth} century”.',
        f'Printing spread in the {n} century.', f'Printing spread in the {nth} century, and in the 1900s.',
        f'Printing spread in the {n}{suf} century.')
FL = {'st': (ST_N, '1', '1st'), 'nd': (ND_N, '2', '2nd'), 'rd': (RD_N, '3', '3rd'), 'th': (TH_N, '4', '4th')}
for suf in ('st', 'nd', 'rd', 'th'):
    pat, n, nth = FL[suf]
    add(f'ord.floor_{suf}', r'(?i)\b(?:on|to|from|at) the ' + pat + r'(?P<target> floor)(?:[,.;:!?)]|$|\s+(?:of|at|in|and|or|but|is|are|was|were|with|to)\b)', suf + ' floor',
        'Grammar', 0.9, f'A floor is named with an ordinal: “the {nth} floor”.',
        f'Her office is on the {n} floor.', f'Her office is on the {nth} floor, near the lift.',
        f'Her office is on the {n}{suf} floor.')
