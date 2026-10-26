"""Quantifier and partitive phrases the engine's noun_number pass does not reach: "of the student", "50 percent of the
user", "two hundreds", "one years", "a big problems" ..."""
from core import *
from fam_num import COUNT, TIME

PT = ("student|customer|user|member|employee|teacher|parent|kid|player|fan|worker|driver|patient|visitor|guest|tourist|"
      "volunteer|candidate|voter|citizen|resident|client|participant|respondent|applicant|soldier|doctor|nurse|friend|colleague")
# A tail that proves the noun ends its phrase and is plural-compatible: the clause end, a preposition, "are/were" or a
# past-tense verb. Modals are left out ("all the student can do" can be singular).
TQ = (r"(?:\s*[,.;:!?)\"”]|\s*$|\s+(?:to|in|on|at|for|from|with|about|are|were|but|because|when|since|after|before|during|as|than|"
      r"too|now|today|here|there|again|ago)\b|\s+[a-z]+ed\b)")
PART = "most|many|some|all|both|few|several|none|any|half|plenty|lots|a lot|a few|a number|the rest|the majority|a majority|the minority|a minority"
DETS = "the|these|those|my|our|their|your|his|her"
FRAC = (r"\d+(?:\.\d+)?\s?%|\d+(?:\.\d+)?\s+percent|(?:one|two|three|four|five|six|seven|eight|nine|ten|twenty|thirty|forty|fifty|"
        r"sixty|seventy|eighty|ninety)\s+percent|half|a third|a quarter|a fifth|a tenth|two[- ]thirds|three[- ]quarters|three[- ]fifths")

add('quant.fraction_of', rf"(?i)(?:^|[\s(\"“])(?:{FRAC})\s+of\s+(?:(?:{DETS})\s+)?(?P<target>(?P<n>{PT}))(?:{TQ})",
    '${n}s', 'Grammar', 0.88, 'After a share “of the” people, use the plural noun.',
    'About 40 percent of the student passed on the first try.', "About 40 percent of the students passed on the first try, and half of the student body voted.")
add('quant.of_the_group', rf"(?i)\b(?:{PART})\s+of\s+(?:{DETS})\s+(?P<target>(?P<n>{PT}))(?:{TQ})",
    '${n}s', 'Grammar', 0.88, 'After “most of the”, “many of the” and similar phrases, use the plural noun.',
    'Many of the student attended the meeting.', "Many of the students attended the meeting, and most of the student body stayed home.")
add('quant.of_the_group_verb', rf"(?i)\b(?:{PART})\s+of\s+(?:{DETS})\s+(?P<target>(?P<n>{PT})\s+(?P<v>are|were))\b",
    '${n}s ${v}', 'Grammar', 0.96, 'After “most of the”, “many of the” and similar phrases, use the plural noun.',
    'Most of the customer were happy with the change.', "Most of the customers were happy with the change, and most of the customer data was clean.")
add('quant.each_of_the', rf"(?i)\b(?:each|either|neither|every one)\s+of\s+(?:{DETS})\s+(?P<target>(?P<n>{PT}))(?:\s*[,.;:!?)\"”]|\s*$|\s+(?:to|in|on|at|for|from|with|about|is|was|has|does|gets|needs|wants|knows|can|will|should|must|may|might|said|got|took)\b)",
    '${n}s', 'Grammar', 0.88, 'After “each of the”, use the plural noun.',
    'Each of the student has a pen.', "Each of the students has a pen, and each student has a pen.")
add('quant.all_the_person', rf"(?i)\ball(?:\s+(?:{DETS}))?\s+(?P<target>(?P<n>{PT}))(?:{TQ})",
    '${n}s', 'Grammar', 0.86, '“All” goes with a plural noun here.',
    'All student in the hall stood up.', "All students in the hall stood up, and all the student can do is wait.")
add('quant.both_person', rf"(?i)\bboth(?:\s+of)?(?:\s+(?:{DETS}))?\s+(?P<target>(?P<n>{PT}))(?:{TQ})",
    '${n}s', 'Grammar', 0.88, '“Both” goes with a plural noun.',
    'Both student were late again.', "Both students were late again, and both student and teacher arrived.")
add('quant.the_two_noun', rf"(?i)\b(?:{DETS}|all)\s+(?:two|three|four|five|six|seven|eight|nine|ten)\s+(?P<target>(?P<n>{COUNT}|{PT}))(?:\s*[,.;:!?)\"”]|\s*$|\s+(?:{FUNC})\b)",
    '${n}s', 'Grammar', 0.88, 'After “the two”, “the three” and so on, use the plural noun.',
    'The two student were late.', "The two students were late, and the two student rooms are clean.")
add('quant.hundreds_of', rf"(?i)\b(?:dozens|hundreds|thousands|millions|billions|tens|scores|loads|heaps|piles|tons|stacks)\s+of\s+(?P<target>(?P<n>{COUNT}|{PT}))(?:\s*[,.;:!?)\"”]|\s*$|\s+(?:{FUNC})\b)",
    '${n}s', 'Grammar', 0.9, 'After “hundreds of”, “dozens of” and similar words, use the plural noun.',
    'We have hundreds of customer in the system.', "We have hundreds of customers in the system, and hundreds of customer support tickets.")
add('quant.n_more', rf"(?i)\b(?:{NUM}|a few|several|many|a couple of)\s+more\s+(?P<target>(?P<n>{COUNT}|{PT}|{TIME}))(?:\s*[,.;:!?)\"”]|\s*$|\s+(?:{FUNC})\b)",
    '${n}s', 'Grammar', 0.88, 'After a number or “a few” and “more”, use the plural noun.',
    'I need three more year to finish the degree.', "I need three more years to finish the degree, and one more year of study.")

# The hundreds/thousands family
SCALE = "hundred|thousand|million|billion|dozen"
NUMS = (rf"(?:{NUMD}|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|"
        r"eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)")
NEXTW = r"(?:[a-np-z][a-z]*|o[a-eg-z][a-z]*|of[a-z]+|o\b)"
add('num.scale_plural',
    rf"(?i)\b(?:have|has|had|about|nearly|almost|over|under|than|only|just|around|roughly|approximately|for|of|with|cost|costs|paid|pay|spent|spend|earn|earns|earned|worth|are|were|is|was|total)\s+{NUMS}\s+(?P<target>(?P<u>{SCALE})s)(?:\s*[,.;:!?)\"”]|\s*$|\s+{NEXTW}\b)",
    '${u}', 'Grammar', 0.9, 'After a number, “hundred”, “thousand” and “million” stay singular.',
    'We paid two hundreds dollars for the ticket.', 'We paid two hundred dollars for the ticket, and hundreds of people came; in the two thousands we moved.')
add('num.a_scale_plural',
    rf"(?i)\b(?:a|an)\s+(?P<target>(?P<u>{SCALE})s)(?:\s*[,.;:!?)\"”]|\s*$|\s+{NEXTW}\b)",
    '${u}', 'Grammar', 0.9, 'After “a”, “hundred”, “thousand” and “million” are singular.',
    'It cost a thousands dollars to fix.', 'It cost a thousand dollars to fix, and thousands of people came.')
add('num.percents', rf"(?i)\b{NUM}\s+(?P<target>percents)\b", 'percent', 'Grammar', 0.9,
    '“Percent” has no plural form after a number.',
    'Sales rose 5 percents last year.', 'Sales rose 5 percent last year, and two percentages were wrong.')
add('num.one_plural_time', rf"(?i)\b(?:for|in|of|about|over|within|after|during|last|next|every|than|only|just|almost|nearly|around|another|approximately|roughly|least|is|was|are|were|be|been|took|takes|take|spent|spend|lasted|lasts|lived|waited|worked|stayed|has|have|had|with)\s+(?:one|1)\s+(?P<target>(?P<u>year|month|week|day|hour|minute|second)s)(?:\s*[,.;:!?)\"”]|\s*$|\s+(?:{FUNC}|of)\b)",
    '${u}', 'Grammar', 0.9, 'After “one”, the unit of time is singular.',
    'He worked there for one years.', 'He worked there for one year, then 21 years elsewhere; five and one half years passed; version 2.1 days are logged; event 1 minutes.')
add('num.one_plural_money', rf"(?i)\b(?:cost|costs|costing|worth|paid|pay|pays|for|only|just|about|nearly|almost|over|under|than|is|are|was|were|of|with|spend|spent|gave|give|gives|got|get|receive|received|earn|earned|charged|charge)\s+(?:one|1)\s+(?P<target>(?P<u>dollar|rupee|euro|pound|cent|peso|dinar)s)(?:\s*[,.;:!?)\"”]|\s*$|\s+(?:{FUNC}|of)\b)",
    '${u}', 'Grammar', 0.9, 'After “one”, the unit of money is singular.',
    'The stamp costs one dollars.', 'The stamp costs one dollar, and five dollars for two.')
add('num.per_plural', rf"(?i)\bper\s+(?P<target>(?P<u>hour|day|week|month|year|minute|second|night|kilogram|kilometer|kilometre|mile|meter|metre|liter|litre|gallon|gram|ounce)s)\b",
    '${u}', 'Grammar', 0.9, 'After “per”, the unit is singular: “per hour”.',
    'The car goes 60 kilometers per hours.', 'The car goes 60 kilometers per hour, and the rate per day is fixed.')
ADJ = ("big|small|huge|major|serious|real|good|great|bad|new|old|long|short|nice|simple|common|different|special|useful|important|"
       "interesting|difficult|easy|hard|strong|clear|main|single|minor|tiny|large|little|famous|close|best|better|true|dear|old")
add('det.a_adj_plural', rf"(?i)\b(?:a|an)\s+(?:{ADJ})\s+(?P<target>(?P<n>{COUNT}|{PT})s)(?:\s*[,.;:!?)\"”]|\s*$|\s+(?:of|in|on|at|for|with|from|to|about)\b)",
    '${n}', 'Grammar', 0.9, '“A” and “an” go with one: use the singular noun.',
    'She is a good friends of mine.', "She is a good friend of mine, and a few good friends came.")
add('there.are_a_numbers', r"(?i)\bthere\s+(?P<target>(?P<v>are|were)\s+a\s+numbers)\s+of\b",
    '${v} a number', 'Grammar', 0.96, '“A number of” takes the singular “number”.',
    'There are a numbers of reasons to wait.', 'There are a number of reasons to wait, and the numbers of visitors rose.')
cover('Quantifier and partitive phrases', 'most/many/some/all/half/few of the + a person noun (student, customer, user ...) -> plural, with a version that takes "are/were" along so agree.partitive_sg_people_* cannot undo it; 40 percent/half/a third of the + person noun; each of the; all (the) / both (the) + person noun; the two/three + noun; hundreds/dozens/scores of + noun; three more + noun/unit; "files" and other things are left, because "most of the file" is a valid partitive',
      ['quant.fraction_of', 'quant.of_the_group', 'quant.of_the_group_verb', 'quant.each_of_the', 'quant.all_the_person', 'quant.both_person', 'quant.the_two_noun', 'quant.hundreds_of', 'quant.n_more'])
cover('Numbers', 'two hundreds / three thousands / a thousands -> hundred/thousand (after a verb or preposition, never "in the two thousands"); 5 percents; one years / one dollars; per hours; "there are a numbers of" (also beats grammar.there_agreement)',
      ['num.scale_plural', 'num.a_scale_plural', 'num.percents', 'num.one_plural_time', 'num.one_plural_money', 'num.per_plural', 'there.are_a_numbers'])
cover('A/an before a plural', 'a/an + adjective + a plural noun (a good friends of mine, a big problems); engine grammar.article_number covers a/an directly before the plural', ['det.a_adj_plural'])
