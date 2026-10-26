"""Plurals written with an apostrophe."""
from core import *

QW = "two|three|four|five|six|seven|eight|nine|ten|many|several|few|these|those|both|various|numerous|multiple|dozens of|hundreds of|thousands of|lots of|a lot of|a number of|a couple of"
OF = "lots of|a lot of|number of|variety of|range of|series of|couple of|pair of|bunch of|kinds of|types of|sorts of|collection of|set of|list of|dozens of|hundreds of|thousands of|millions of"
ACR = r"(?-i:[A-Z]{2,6})"
add('apos.acronym_after_quant', rf"(?i)\b(?:two|three|four|five|six|seven|eight|nine|ten|many|several|few|these|those|both|various|numerous|multiple)\s+(?P<target>(?P<a>{ACR})['’]s)\b",
    '${a}s', 'Punctuation', 0.88, 'A plural needs no apostrophe: “CDs”.',
    'We fixed several ATM\'s last week.', 'We fixed several ATMs last week, and the ATM\'s screen cracked, and the iPhone 12 XR\'s screen is bright.')
add('apos.acronym_after_of', rf"(?i)\b(?:{OF})\s+(?P<target>(?P<a>{ACR})['’]s)(?:\s*[,.;:!?)\"”]|\s*$|\s+(?:and|or|are|were|have|had|in|on|at|for|from|with|to|that|which|who|as|but)\b)",
    '${a}s', 'Punctuation', 0.88, 'A plural needs no apostrophe: “PCs”.',
    'The lab has a lot of ATM\'s from the old days.', 'The lab has a lot of ATMs from the old days, and a list of ATM\'s settings is attached.')
add('apos.acronym_plural_verb', rf"\b(?P<target>(?P<a>{ACR})['’]s)\s+(?:are|were|have|had|can|could|will|would|should|may|might|must|do|did)\b",
    '${a}s', 'Punctuation', 0.86, 'A plural needs no apostrophe: “ATMs”.',
    'The ATM\'s are out of cash.', 'The ATMs are out of cash, and the ATM\'s screen is cracked.')

NOUNS_S = ("apple|banana|orange|egg|book|car|bike|phone|laptop|ticket|plant|flower|cake|cookie|burger|bag|shoe|shirt|kitten|pie|"
           "bun|fruit|vegetable|friend|student|teacher|customer|user|file|bug|tip|step|member|employee|parent|kid|player|fan|"
           "project|task|meeting|email|message|document|article|movie|song|video|app|tool|thing|report|page|rule|group|site|"
           "link|plan|goal|skill|result|photo|picture|idea|option|example|question|mistake|reason|dog|cat|house|room|game")
# punctuation.apostrophe (engine) already fixes "two/many/several/these/both friend's"; the "lots of" phrases are not covered.
add('apos.noun_after_of_phrase',
    rf"(?i)\b(?:lots of|a lot of|plenty of|a number of|a couple of|a variety of|a range of|a series of|a bunch of|a handful of|dozens of|hundreds of|thousands of)\s+(?P<target>(?P<n>{NOUNS_S})['’]s)(?:\s*[,.;:!?)\"”]|\s*$|\s+(?:{FUNC})\b)",
    '${n}s', 'Punctuation', 0.85, 'A plain plural needs no apostrophe.',
    'Lots of friend\'s are coming to the party.', 'Lots of friends are coming to the party, and a friend\'s car is outside.')
add('apos.sign_style',
    rf"(?im)(?:^|[.!?]\s+)(?:fresh|cheap|new|used|free|hot|cold|organic|homemade|handmade|local|tasty|delicious|quality|assorted|discount|bargain|big|small|large|ripe|sweet)\s+(?P<target>(?P<n>apple|banana|orange|egg|book|car|bike|phone|laptop|ticket|plant|flower|cake|cookie|burger|bag|shoe|shirt|kitten|pie|bun|fruit|vegetable|mango|pear|peach|plum|lemon|carrot|onion|bean|nut|roll|toy|game)['’]s)\s+(?:for sale|on sale|available|here|today|now|inside|in stock|wanted|needed|sold)\b",
    '${n}s', 'Punctuation', 0.8, 'A plain plural needs no apostrophe.',
    'Fresh apple\'s for sale at the gate.', 'Fresh apples for sale at the gate. The fresh apple\'s on sale in the shop.')
add('apos.lots_of', rf"(?i)\b(?:there are|there were|there['’]s|there is|have|has|had|having|with|got|get|gets|see|saw|find|found|make|makes|made|take|takes|took|need|needs|learn|learned|many|so|and|but|are|were|enjoy|like|love)\s+(?P<target>lot['’]s)\s+of\b",
    'lots', 'Punctuation', 0.88, '“Lots of” is a plural, so it takes no apostrophe.',
    'There are lot\'s of reasons to try it.', 'There are lots of reasons to try it, and the lot\'s of no use to anyone.')
cover('Apostrophe plurals', 'acronym + \'s after a plural quantifier, after "lots of / a list of ...", or before a plural verb (many DVD\'s, a lot of ATM\'s, the ATM\'s are; acronyms the tagger takes for names, such as PC and CD, are left to punctuation.apostrophe); a plain noun + \'s after a "lots of" phrase (lots of friend\'s are); sign-style "Fresh apple\'s for sale"; "lot\'s of" -> "lots of". Possessives ("the CD\'s case", "a friend\'s car") and model numbers ("iPhone 12 XR\'s screen") are left alone. Decades (1990\'s) and "two week\'s notice" are already fixed by punctuation.apostrophe',
      ['apos.acronym_after_quant', 'apos.acronym_after_of', 'apos.acronym_plural_verb', 'apos.noun_after_of_phrase', 'apos.sign_style', 'apos.lots_of'])
