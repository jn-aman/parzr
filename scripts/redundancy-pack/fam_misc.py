"""Fixed phrases that say a thing twice and have one shorter form: "each and every", "about 50
or so", "also too", "enclosed herewith", "7 am in the morning", "in spite of the fact that"."""
from core import add, style, keep_first, pair, S, E, AFTER

SEC = 'Fixed phrases'
PUNCT = r"(?:[.,;:!?)]|$)"
MONTHS = 'January|February|March|April|May|June|July|August|September|October|November|December'


def build():
    ids = []
    ids.append(style('misc.each_and_every', 'each and every', 'every', 0.76,
                     '“Each and every” says the same thing twice: “every” (or “each”) is enough.',
                     'We thank each and every volunteer.',
                     'We thank each volunteer and every guest who came, and each of them replied.'))
    ids.append(style('misc.in_spite_of_the_fact_that', 'in spite of the fact that', 'although', 0.76,
                     '“In spite of the fact that” is a long way to say “although”.',
                     'In spite of the fact that it rained, we went.',
                     'In spite of the rain, we went, and the fact that it ended was a relief.'))
    # Times: the hour already names the part of the day.
    PM_PART = r'(?: in the (?:afternoon|evening)| at night)'
    AM = r'(?-i:am|AM)'
    PM = r'(?-i:pm|PM)'
    HOUR = r'\d{1,2}(?::\d{2})?\s?'
    ids.append(add('time.am_in_the_morning', rf'(?im){S}{HOUR}{AM}(?P<target> in the morning){AFTER}', '', 'Style', 0.78,
                   '“AM” already means morning: “7 am in the morning” can be “7 am”.',
                   'The bus leaves at 7 am in the morning.',
                   'The bus leaves at 7 am. The morning rush starts at six, and we ate in the morning.'))
    ids.append(add('time.pm_in_the_evening', rf'(?im){S}{HOUR}{PM}(?P<target>{PM_PART}){AFTER}', '', 'Style', 0.78,
                   '“PM” already says it is afternoon, evening or night: drop “in the evening”.',
                   'The class starts at 6 pm in the evening.',
                   'The class starts at 6 pm. Come in the evening if you can, or at night.'))
    DAM = r'\d{1,2}(?::\d{2})?\s?[aA]\.[mM]\.'
    DPM = r'\d{1,2}(?::\d{2})?\s?[pP]\.[mM]\.'
    ids.append(add('time.dotted_am_in_the_morning', rf'(?im){S}{DAM}(?P<target> in the morning)(?:[,;:!?)]|\s+(?:and|or|but|with|to|for|when|if|is|was|are|were|that|which|from|in|on|at|by|as|so|than|will|would|can)\b)',
                   '', 'Style', 0.78,
                   '“a.m.” already means morning: “7 a.m. in the morning” can be “7 a.m.”.',
                   'The bus leaves at 7 a.m. in the morning, and we follow.',
                   'The bus leaves at 7 a.m., and the morning crowd follows.'))
    ids.append(add('time.dotted_am_in_the_morning_end', rf'(?im){S}{DAM}(?P<target> in the morning\.)(?:\s|$)',
                   '', 'Style', 0.78,
                   '“a.m.” already means morning: “7 a.m. in the morning” can be “7 a.m.”.',
                   'We left at 7 a.m. in the morning.',
                   'We left at 7 a.m. The morning was cold.'))
    ids.append(add('time.dotted_pm_in_the_evening', rf'(?im){S}{DPM}(?P<target>{PM_PART})(?:[,;:!?)]|\s+(?:and|or|but|with|to|for|when|if|is|was|are|were|that|which|from|in|on|at|by|as|so|than|will|would|can)\b)',
                   '', 'Style', 0.78,
                   '“p.m.” already says it is afternoon, evening or night: drop “in the evening”.',
                   'The class starts at 6 p.m. in the evening on Fridays.',
                   'The class starts at 6 p.m. on Fridays, and the evening group meets later.'))
    ids.append(add('time.dotted_pm_in_the_evening_end', rf'(?im){S}{DPM}(?P<target>{PM_PART}\.)(?:\s|$)',
                   '', 'Style', 0.78,
                   '“p.m.” already says it is afternoon, evening or night: drop “in the evening”.',
                   'We arrived at 9 p.m. at night.',
                   'We arrived at 9 p.m. The night was calm.'))
    ids.append(add('misc.consecutive_in_a_row', rf'(?im){S}consecutive [a-z]+(?P<target> in a row){E}', '', 'Style', 0.78,
                   '“Consecutive” already means one after another: “in a row” says it again.',
                   'She won three consecutive titles in a row.',
                   'She won three titles in a row, and a consecutive run followed.'))
    ids.append(add('misc.both_of_the_two', rf'(?im){S}(?P<target>both (?P<o>of (?:the|these|those|my|our|your|their|his|her)) two){E}', 'both ${o}',
                   'Style', 0.78,
                   '“Both” already means two: say “both of the”, without “two”.',
                   'Both of the two teams scored.',
                   'Both of the teams scored, and the two coaches shook hands.'))
    ids.append(add('misc.about_or_so', rf'(?im){S}(?:about|around|approximately|roughly|some|nearly|over|almost)\s+\d[\d,.]*(?P<target> or so){E}', '',
                   'Style', 0.76,
                   '“About” and “or so” both mean the number is approximate: use one.',
                   'About 50 or so people came.',
                   'About 50 people came, and a dozen or so stayed late.'))
    ids.append(add('misc.postponed_until_later', rf'(?im){S}postpon(?:e|es|ed|ing)(?P<target> until (?:a )?later(?: date| time)?){E}', '', 'Style', 0.74,
                   'To postpone is already to put off until later: drop “until a later date”.',
                   'The vote was postponed until a later date.',
                   'The vote was postponed, and we will meet again at a later date.'))
    # Pairs of words that say it twice.
    ids.append(add('misc.kindly_please', rf'(?im){S}(?P<target>kindly please){E}', 'please', 'Style', 0.76,
                   '“Kindly” and “please” both ask politely: use one.',
                   'Kindly please send the report today.',
                   'Please send the report today, and be kind to the new staff.'))
    ids.append(add('misc.please_kindly', rf'(?im){S}(?P<target>please kindly){E}', 'please', 'Style', 0.76,
                   '“Please” and “kindly” both ask politely: use one.',
                   'Please kindly find the file attached.',
                   'Please find the file attached, and kindly keep it private.'))
    ids.append(add('misc.also_too', rf'(?im){S}(?P<target>also too){PUNCT}', 'too', 'Style', 0.8,
                   '“Also” and “too” mean the same: use one.',
                   'I want to come also too.',
                   'It is also too late to book, and I am too tired also.'))
    ids.append(add('misc.also_as_well', rf'(?im){S}(?P<target>also as well){PUNCT}', 'as well', 'Style', 0.8,
                   '“Also” and “as well” mean the same: use one.',
                   'She sings also as well.',
                   'She also sings as well as dances, and also as well as you.'))
    ids.append(add('misc.too_as_well', rf'(?im){S}(?P<target>too as well){PUNCT}', 'too', 'Style', 0.8,
                   '“Too” and “as well” mean the same: use one.',
                   'I am coming too as well.',
                   'I am coming too, and she is coming as well.'))
    ids.append(add('misc.as_well_too', rf'(?im){S}(?P<target>as well too){PUNCT}', 'as well', 'Style', 0.8,
                   '“As well” and “too” mean the same: use one.',
                   'He is invited as well too.',
                   'He is invited as well, and she is invited too.'))
    ids.append(add('misc.enclosed_herewith', rf'(?im){S}(?P<target>(?P<v>enclosed|attached) herewith){E}', '${v}', 'Style', 0.76,
                   '“Herewith” says “with this letter”, which “enclosed” already says.',
                   'The invoice is attached herewith.',
                   'The invoice is attached, and I sign herewith as agreed.'))
    ids.append(add('misc.herewith_enclosed', rf'(?im){S}(?P<target>herewith (?P<v>enclosed|attached)){E}', '${v}', 'Style', 0.76,
                   '“Herewith” says “with this letter”, which “enclosed” already says.',
                   'Please see the form herewith enclosed.',
                   'Please see the form enclosed, and I sign herewith as agreed.'))
    ids.append(add('misc.enclose_herewith', rf'(?im){S}(?P<target>(?P<v>enclos(?:e|es|ing)|attach(?:es|ing)?) herewith){E}', '${v}', 'Style', 0.76,
                   '“Herewith” says “with this letter”, which “enclose” already says.',
                   'I enclose herewith a copy of the contract.',
                   'I enclose a copy of the contract, and sign herewith as agreed.'))
    ids.append(add('misc.cacophony_of_sounds', rf'(?im){S}(?P<target>cacophony of sounds?){E}', 'cacophony', 'Style', 0.76,
                   'A cacophony is already a harsh mix of sounds: “cacophony of sounds” says it twice.',
                   'A cacophony of sounds filled the hall.',
                   'A cacophony filled the hall, and a cacophony of voices rose from the street.'))
    ids.append(add('misc.round_circle', rf'(?im){S}(?P<target>round (?P<k>circles?)){E}', '${k}', 'Style', 0.78,
                   'A circle is round: “round circle” says it twice.',
                   'Draw a round circle on the page.',
                   'Draw a circle on the page, and make the round table smaller.'))
    ids.append(add('misc.same_identical', rf'(?im){S}(?P<target>same (?P<k>identical)){E}', '${k}', 'Style', 0.74,
                   '“Same” and “identical” both mean alike: use one.',
                   'Both parts have the same identical shape.',
                   'Both parts have the same shape, and the twins are identical.'))
    ids.append(add('misc.pre_in_advance', rf'(?im){S}(?P<target>(?P<v>pre-?(?:order|book|register|pay|plan|schedule|arrange|purchase|record|approve|screen|load|select|determine|decide)(?:s|ed|d|ing)?|pre-?plann(?:ed|ing)|pre-?(?:book|order|pay)(?:ed|ing)?) in advance){E}',
                   '${v}', 'Style', 0.78,
                   'The prefix “pre-” already means in advance: “pre-order in advance” can be “pre-order”.',
                   'You can pre-order in advance online.',
                   'You can order it in advance, and the pre-order bonus ships first.'))
    ids.append(add('misc.re_again', rf'(?im){S}(?P<target>(?P<v>re-?(?:try|check|visit|think|consider|submit|apply|evaluate|examine|assess)(?:s|ed|ing|ies|ied)?) again)(?:[^\w\'’\s-]|\s*$|\s+(?:what|that|the|your|my|his|her|our|their|please|for|because|so|if|when|how|where|why|to|in|on|at|with|before|after|but|next|this|later|soon|tomorrow|tonight|today|within|by|from|over|as|is|will)\b)',
                   '${v}', 'Style', 0.72,
                   'The prefix “re-” already means again: “retry again” can be “retry”.',
                   'Please retry again in a few minutes.',
                   'Please retry in a few minutes. Try again, and then reconsider the plan.'))
    return ids
