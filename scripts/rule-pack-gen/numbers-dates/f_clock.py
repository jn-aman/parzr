"""Clock times: redundant parts (5 pm in the evening, 5 o'clock pm, 17:00 pm, 12 am midnight), spacing, a.m./p.m. mixes."""
from lib import add, q, APOS

T = r'\d{1,2}(?::\d\d)?'
AM = r'(?:a\.m\.|(?:am|a\.m)\b)'
PM = r'(?:p\.m\.|(?:pm|p\.m)\b)'
# the clock time with its marker, then a gap; \b after the marker so "5 amazing" and "5 pmo" never match
def mark(m):
    return T + r'\s?' + m

add('clock.am_in_the_morning', r'(?i)\b' + mark(AM) + r'(?P<target> in the morning)\b', '', 'Redundancy', 0.8,
    '“am” already means morning: say “9 am” or “9 in the morning”, not both.',
    'We start at 9 am in the morning.', 'We start at 9 am, or at nine in the morning, then lunch in the morning.',
    'We start at 9 am.')
add('clock.pm_in_the_afternoon', r'(?i)\b' + mark(PM) + r'(?P<target> in the afternoon)\b', '', 'Redundancy', 0.8,
    '“pm” already means afternoon: say “3 pm” or “3 in the afternoon”, not both.',
    'The call is at 3 pm in the afternoon.', 'The call is at 3 pm, or at three in the afternoon, and lunch is in the afternoon.',
    'The call is at 3 pm.')
add('clock.pm_in_the_evening', r'(?i)\b' + mark(PM) + r'(?P<target> in the evening)\b', '', 'Redundancy', 0.8,
    '“pm” already places the time in the evening: say “7 pm” or “7 in the evening”, not both.',
    'Dinner is at 7 pm in the evening.', 'Dinner is at 7 pm, or at seven in the evening, then a walk in the evening.',
    'Dinner is at 7 pm.')
add('clock.pm_at_night', r'(?i)\b' + mark(PM) + r'(?P<target> (?:at|in the) night)\b', '', 'Redundancy', 0.8,
    '“pm” already places the time at night: say “11 pm” or “11 at night”, not both.',
    'The shop closes at 11 pm at night.', 'The shop closes at 11 pm, or at eleven at night, and stays dark at night.',
    'The shop closes at 11 pm.')
add('clock.oclock_pm', r'(?i)\b' + T + r'(?P<target> o' + APOS + r'clock)\s?' + r'(?:a\.m\.|p\.m\.|(?:am|pm)\b)', '', 'Redundancy', 0.8,
    '“o’clock” cannot be combined with “am” or “pm”: write “5 pm” or “5 o’clock”.',
    "Dinner is at 7 o'clock pm tonight.", "Dinner is at 7 o'clock tonight, or at 7 pm.",
    'Dinner is at 7 pm tonight.')
add('clock.oclock_after_minutes', r'(?i)\b\d{1,2}:(?:0[1-9]|[1-5]\d)(?P<target> o' + APOS + r'clock)\b', '', 'Grammar', 0.93,
    '“o’clock” is only used for a full hour: write “5:30”, not “5:30 o’clock”.',
    "The meeting starts at 10:30 o'clock sharp.", "The meeting starts at 10:30 sharp, or at 10 o'clock sharp.",
    'The meeting starts at 10:30 sharp.')
add('clock.oclock_after_00', r'(?i)\b\d{1,2}:00(?P<target> o' + APOS + r'clock)\b', '', 'Redundancy', 0.8,
    '“8:00” and “8 o’clock” say the same thing: write one of them.',
    "The meeting starts at 8:00 o'clock sharp.", "The meeting starts at 8:00 sharp, or at 8 o'clock sharp.",
    'The meeting starts at 8:00 sharp.')
add('clock.noon_pm', r'(?i)\b12(?::00)?(?P<target>\s?(?:p\.m\.|pm)) noon\b', '', 'Redundancy', 0.8,
    '“noon” already means 12 midday: write “12 noon” or “12 pm”, not both.',
    'Lunch is at 12 pm noon today.', 'Lunch is at 12 noon today, or at 12 pm, or at 12 pm sharp.',
    'Lunch is at 12 noon today.')
add('clock.midnight_am', r'(?i)\b12(?::00)?(?P<target>\s?(?:a\.m\.|am)) midnight\b', '', 'Redundancy', 0.8,
    '“midnight” already means 12 at night: write “12 midnight” or “12 am”, not both.',
    'The deadline is 12 am midnight on Friday.', 'The deadline is 12 midnight on Friday, or 12 am on Friday.',
    'The deadline is 12 midnight on Friday.')
add('clock.24h_pm', r'(?i)\b(?:1[3-9]|2[0-3]):\d\d(?P<target>\s?(?:pm|am)\b)', '', 'Grammar', 0.93,
    'A 24-hour time such as 17:00 does not take “am” or “pm”: write “17:00” or “5 pm”.',
    'The train leaves at 17:00 pm today.', 'The train leaves at 17:00 today, or at 5 pm, or at 7:30 pm.',
    'The train leaves at 17:00 today.')
add('clock.zero_am', r'(?i)\b00:\d\d(?P<target>\s?(?:am|pm)\b)', '', 'Grammar', 0.93,
    'A 24-hour time such as 00:30 does not take “am” or “pm”: write “00:30” or “12:30 am”.',
    'The backup runs at 00:30 am daily.', 'The backup runs at 00:30 daily, or at 12:30 am daily.',
    'The backup runs at 00:30 daily.')
add('clock.clock_missing_apostrophe', r'(?i)\b(?:at|by|before|after|around|until|till) (?:\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve) (?P<target>clock)(?:[,.;:!?)]|$|\s+(?:sharp|in|on|and|or|but|tomorrow|today|tonight|exactly|am|pm)\b)', 'o’clock', 'Spelling', 0.9,
    'The word is “o’clock” (of the clock): “at 5 o’clock”.',
    'Please arrive at 5 clock sharp.', "Please arrive at 5 o'clock sharp, by the town clock, or at the clock tower.",
    'Please arrive at 5 o’clock sharp.')
# a.m./p.m. written two ways in one range; the first marker sets the style, the second follows it
def mixed(rid, first, second, target, new, pos, neg, fix, tail=''):
    add(rid, r'(?i)\b' + T + r'\s?' + first + r'\s(?:to|until|till|and|-)\s' + T + r'\s?(?P<target>' + target + r')' + tail,
        new, 'Style', 0.7, reason_for(new), pos, neg, fix)
def reason_for(new):
    return 'Write both times of the range the same way: ' + q(new) + ' to match the first.'
mixed('clock.dots_mixed_pm', r'(?:a\.m\.|p\.m\.)', '', r'pm', 'p.m.',
      'Open from 9 a.m. to 5 pm daily.', 'Open from 9 a.m. to 5 p.m. daily, or from 9 am to 5 pm.',
      'Open from 9 a.m. to 5 p.m. daily.', r'(?:[\s,;)]|$)')
mixed('clock.dots_mixed_am', r'(?:a\.m\.|p\.m\.)', '', r'am', 'a.m.',
      'Open from 6 p.m. to 2 am daily.', 'Open from 6 p.m. to 2 a.m. daily, or from 6 pm to 2 am.',
      'Open from 6 p.m. to 2 a.m. daily.', r'(?:[\s,;)]|$)')
mixed('clock.plain_mixed_pm', r'(?:am|pm)', '', r'p\.m\.', 'pm',
      'Open from 9 am to 5 p.m. for guests.', 'Open from 9 am to 5 pm for guests, or from 9 a.m. to 5 p.m. for guests.',
      'Open from 9 am to 5 pm for guests.', r'(?:,| [a-z])')
mixed('clock.plain_mixed_am', r'(?:am|pm)', '', r'a\.m\.', 'am',
      'Open from 6 pm to 2 a.m. for guests.', 'Open from 6 pm to 2 am for guests, or from 6 p.m. to 2 a.m. for guests.',
      'Open from 6 pm to 2 am for guests.', r'(?:,| [a-z])')
