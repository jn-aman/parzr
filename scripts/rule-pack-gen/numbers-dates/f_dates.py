"""Dates and ages: "in the year of 1990", "in June 5th", "in 20th century", "for last 3 years", "has 12 years old"."""
from lib import add, q, MONTHS, CARD2U, ONES, TEENS, TENS, APOS

LEAD = r'(?:^|[^/\s]\s+|\()'

NUMW = r'(?:' + ONES + '|' + TEENS + '|' + TENS + r')'
AGE = r'(?:\d{1,3}|' + NUMW + r'(?:[- ](?:' + ONES + r'))?)'
UNITS_T = r'(?:days|weeks|months|years|hours|minutes|decades|seconds)'
END = r'(?:[.,;:!?)]|$|\s+(?:and|or|but|so|now|today|when|while|since|this|next|last|in|on|at)\b)'

add('date.year_of_digits', r'(?i)\b(?:in|during|since|from|until|by|throughout) the year(?P<target> of) (?:19|20)\d\d\b', '', 'Word choice', 0.88,
    'Say “in the year 1990” (or “in 1990”); “of” is only for names such as “the year of the dragon”.',
    'The firm was founded in the year of 1990.', 'The firm was founded in the year 1990, or in 1990, or in the year of the dragon.',
    'The firm was founded in the year 1990.')
add('date.year_word_after_year',
    r'(?i)\b(?:in|by|until|during|before|after) (?:19|20)\d\d(?P<target> year)(?:[.,;:!?)]|$|\s+(?:and|or|but|when|we|I|he|she|they|it|there|was|were|is|are|had|has)\b)',
    '', 'Redundancy', 0.8,
    'A year number needs no “year” after it: “in 2024”, not “in 2024 year”.',
    'We moved to Pune in 2019 year and stayed.', 'We moved to Pune in 2019 and stayed, and the 2019 year-end report came in 2020 year-end.'.replace(', and the 2019 year-end report came in 2020 year-end', ', and read the 2019 year-end report'),
    'We moved to Pune in 2019 and stayed.')
add('date.in_month_day', r'(?i)\b(?P<target>in) (?:' + MONTHS + r') \d{1,2}(?:st|nd|rd|th)?(?:,? (?:19|20)\d\d)?(?:[.,;:!?)]|$|\s+(?:and|or|but|when|we|I|he|she|they|it|the|a|at|for|to|from|with|will|was|were|is|are|until|through)\b)',
    'on', 'Grammar', 0.9,
    'Use “on” with a date that has a day: “on June 5th”; “in” is for a month or year alone.',
    'The workshop was held in June 5th at the hall.', 'The workshop was held on June 5th at the hall, in June, or in June 2024.',
    'The workshop was held on June 5th at the hall.')
add('date.after_days_later', r'(?i)\bafter (?:\d+|' + NUMW + r'|a few|several|a couple of) ' + UNITS_T + r'(?P<target> later)\b', '', 'Redundancy', 0.8,
    '“After” and “later” say the same thing: “after two days”, or “two days later”.',
    'After 2 days later we left the town.', 'After 2 days we left the town, or 2 days later we left the town.',
    'After 2 days we left the town.')
add('date.in_last_years', r'(?i)\b(?:for|in|over|during|within|throughout) (?P<target>last) (?:\d+|few|couple|several|' + NUMW + r') ' + UNITS_T + r'\b', 'the last', 'Grammar', 0.9,
    'Use “the” before “last” in a span of time: “in the last three years”.',
    'Sales rose in last 3 years sharply.', 'Sales rose in the last 3 years sharply, or in last year.'.replace(', or in last year', ', or last year'),
    'Sales rose in the last 3 years sharply.')
add('date.in_past_years', r'(?i)\b(?:for|in|over|during|within|throughout) (?P<target>past) (?:\d+|few|couple|several|' + NUMW + r') ' + UNITS_T + r'\b', 'the past', 'Grammar', 0.9,
    'Use “the” before “past” in a span of time: “for the past three years”.',
    'Sales rose for past 3 years sharply.', 'Sales rose for the past 3 years sharply, or in past tenses.'.replace(', or in past tenses', ', or in the past'),
    'Sales rose for the past 3 years sharply.')
ORD = (r'(?:\d{1,2}(?:st|nd|rd|th)|first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|eleventh|twelfth|thirteenth|'
       r'fourteenth|fifteenth|sixteenth|seventeenth|eighteenth|nineteenth|twentieth)')
add('date.century_missing_the',
    r'(?i)\b(?:in|during|of|from|since|until|by|throughout) (?P<target>' + ORD + r') century(?:[.,;:!?)]|$|\s+(?:and|or|but|when|where|which|who|was|were|is|are|to|ago|onwards)\b)',
    'the ${target}', 'Grammar', 0.88,
    'A century needs “the”: “in the 20th century”.',
    'The town grew in 19th century and prospered.', 'The town grew in the 19th century and prospered, or in 19th-century style.',
    'The town grew in the 19th century and prospered.')
add('date.decade_missing_the',
    r'(?i)\b(?:in|during|since) (?P<target>(?:19|20)\d0s)(?:[.;:!?)]|$|,\s+(?:he|she|they|it|we|I|there|the|a|an|many|most)\b|\s+(?:when|we|I|he|she|they|it|there|was|were|had)\b)',
    'the ${target}', 'Grammar', 0.85,
    'A decade needs “the” here: “in the 1990s”.',
    'Phones were rare in 1990s when we met.', 'Phones were rare in the 1990s and costly, as in 1990s Britain, or in 1990s, 2000s and 2010s Berlin.',
    'Phones were rare in the 1990s when we met.')
# ages
CORE = AGE + r' years old'
END2 = r'(?:[.,;:!?)]|$|\s+(?:and|but|so|now|today|since|when|while|this|next|last|in|on|at)\b)'
add('date.i_have_years_old', r'(?i)\bI (?P<target>have) ' + CORE + END2, 'am', 'Grammar', 0.93,
    'Age is stated with “be”: “I am 20 years old”.',
    'I have 20 years old and study law.', 'I am 20 years old and study law, and I have 20 cousins.',
    'I am 20 years old and study law.')
add('date.he_has_years_old', r'(?i)\b(?:he|she|it) (?P<target>has) ' + CORE + END2, 'is', 'Grammar', 0.93,
    'Age is stated with “be”: “she is 20 years old”.',
    'She has 12 years old and plays chess.', 'She is 12 years old and plays chess, and she has 12 trophies.',
    'She is 12 years old and plays chess.')
add('date.they_have_years_old', r'(?i)\b(?:we|you|they) (?P<target>have) ' + CORE + END2, 'are', 'Grammar', 0.93,
    'Age is stated with “be”: “they are 20 years old”.',
    'They have 20 years old and study law.', 'They are 20 years old and study law, and they have 20 books.',
    'They are 20 years old and study law.')
add('date.name_has_years_old', r'\b(?-i:[A-Z][a-z]+) (?P<target>(?-i:has)) (?i:' + CORE + r')' + END2, 'is', 'Grammar', 0.9,
    'Age is stated with “be”: “Maria is 20 years old”.',
    'Maria has 12 years old and plays chess.', 'Maria is 12 years old and plays chess, and Maria has 12 trophies.',
    'Maria is 12 years old and plays chess.')
add('date.my_relative_has_years_old',
    r'(?i)\bmy (?:son|daughter|brother|sister|mother|father|mom|dad|wife|husband|friend|cousin|dog|cat|grandfather|grandmother|uncle|aunt|nephew|niece|boyfriend|girlfriend|baby|boss) (?P<target>has) ' + CORE + END2,
    'is', 'Grammar', 0.93,
    'Age is stated with “be”: “my son is 12 years old”.',
    'My son has 12 years old and plays chess.', 'My son is 12 years old and plays chess, and my son has 12 trophies.',
    'My son is 12 years old and plays chess.')
add('date.aged_years_old', r'(?i)\baged ' + AGE + r'(?P<target> years old)\b', '', 'Redundancy', 0.8,
    '“Aged” already says it: “a woman aged 40”, not “aged 40 years old”.',
    'A woman aged 40 years old was found safe.', 'A woman aged 40 was found safe, or a woman of 40 years old.',
    'A woman aged 40 was found safe.')
# a count of times
add('date.times_a_day', r'(?i)' + LEAD + CARD2U + r' (?P<target>time) (?:a|per|each|every) (?:day|week|month|year|hour|minute)\b', 'times', 'Grammar', 0.92,
    'After a number above one it is “times”: “twice a day”, “three times a week”.',
    'I run 3 time a week.', 'I run 3 times a week, or one time a week, and a 3 time winner.',
    'I run 3 times a week.')
add('date.few_time', r'(?i)\b(?:several|a few|multiple) (?P<target>time)(?:[.,;:!?)]|$|\s+(?:before|already|in|per|over|and|but|today|this|last|each)\b)', 'times', 'Grammar', 0.9,
    'After “several”, “a few” or “multiple” it is “times”.',
    'We tried that several time before.', 'We tried that several times before, and spent a long time on it.',
    'We tried that several times before.')
