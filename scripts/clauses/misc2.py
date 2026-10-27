"""More single constructions: stacked connectors, split-up connectors, "so that to", "the way how", "reason for why",
double negatives with "neither of", "not only ..., also", "so hot than".
"""
from core import add, not_in, any_word, START, W
from misc import ADJ

SEC = 'Reasons, connectors and fixed frames'
PRON = r"(?:I|we|you|he|she|they|it|there)"

add('connector.therefore_so',
    r"(?i)\b(?:therefore|thus|hence),? (?P<target>so )" + PRON + r"\b",
    '', 'Redundancy', 0.82,
    '“Therefore” and “so” do the same job; use one of them.',
    'The road was closed. Therefore so we took the ferry.',
    'The road was closed. Therefore we took the ferry. The road was closed, so we took the ferry. Therefore, so far, nothing has changed.',
    'The road was closed. Therefore we took the ferry.', SEC)

add('connector.as_well_as_also',
    r"(?i)\bas well as (?P<target>also )[a-z]",
    '', 'Redundancy', 0.8,
    '“As well as” already adds the item; “also” repeats it.',
    'She speaks French as well as also Spanish and Italian.',
    'She speaks French as well as Spanish and Italian. She also speaks Spanish. She speaks it as well as I do.',
    'She speaks French as well as Spanish and Italian.', SEC)

add('connector.event_that_if',
    r"(?i)\bin the event that (?P<target>if )",
    '', 'Grammar', 0.9,
    '“In the event that” already means “if”; do not add “if”.',
    'In the event that if the vote fails, the board will meet again.',
    'In the event that the vote fails, the board will meet again. If the vote fails, the board will meet again.',
    'In the event that the vote fails, the board will meet again.', SEC)

add('connector.provided_that_if',
    r"(?i)\bprovided that (?P<target>if )",
    '', 'Grammar', 0.9,
    '“Provided that” already means “if”; do not add “if”.',
    'You may borrow the van, provided that if you refill the tank.',
    'You may borrow the van, provided that you refill the tank. You may borrow the van if you refill the tank.',
    'You may borrow the van, provided that you refill the tank.', SEC)

add('compound.further_more',
    r"(?im)" + START + r"(?P<target>further more)(?:,|\s+(?:we|I|you|he|she|they|it|there|the|our|my|this|these)\b)",
    'furthermore', 'Spelling', 0.9,
    'The connector is one word: “furthermore”.',
    'Further more, the contract limits the supplier’s liability.',
    'Furthermore, the contract limits the supplier’s liability. Further more people signed the petition each day.',
    'Furthermore, the contract limits the supplier’s liability.', SEC)

add('compound.more_over',
    r"(?im)" + START + r"(?P<target>more over),",
    'moreover', 'Spelling', 0.9,
    'The connector is one word: “moreover”.',
    'More over, the new office is closer to the station.',
    'Moreover, the new office is closer to the station. More over the years, the office grew.',
    'Moreover, the new office is closer to the station.', SEC)

add('frame.so_that_to',
    r"(?i)\b(?P<target>so that to)\b",
    'so as to', 'Grammar', 0.9,
    'Say “so as to” or “so that you can”, not “so that to”.',
    'She woke early so that to avoid the traffic.',
    'She woke early so as to avoid the traffic. She woke early so that she could avoid the traffic. She woke early to avoid the traffic.',
    'She woke early so as to avoid the traffic.', SEC)

add('frame.in_order_that_to',
    r"(?i)\bin order (?P<target>that )to\b",
    '', 'Grammar', 0.9,
    'Say “in order to” (or “in order that you can”).',
    'We shortened the form in order that to save time.',
    'We shortened the form in order to save time. We shortened the form in order that people could finish faster.',
    'We shortened the form in order to save time.', SEC)

add('frame.so_adjective_than_result',
    r"(?i)\bso (?:" + '|'.join(ADJ) + r") (?P<target>than|then) (?:I|we|you|he|she|they|it) (?:can['’]t|cannot|can not|couldn['’]t|could not|won['’]t|didn['’]t|did not|don['’]t|do not)\b",
    'that', 'Grammar', 0.9,
    'A result clause after “so” begins with “that”.',
    'The soup was so hot than I could not eat it.',
    'The soup was so hot that I could not eat it. The soup was hotter than I expected. It was so hot then, we left.',
    'The soup was so hot that I could not eat it.', SEC)

add('relative.the_way_how',
    r"(?i)\bthe way (?P<target>how )(?:I|we|you|he|she|they|it|there|the|my|our|his|her|their)\b",
    '', 'Grammar', 0.9,
    'Say “the way he does it” or “how he does it”, not “the way how”.',
    'I like the way how she explains hard topics.',
    'I like the way she explains hard topics. I like how she explains hard topics. Show me the way home. Do not get in the way of how they work.',
    'I like the way she explains hard topics.', SEC)

add('relative.reason_for_why',
    r"(?i)\breasons? (?P<target>for why)\b",
    'why', 'Redundancy', 0.78,
    'Say “the reason why” (or “the reason for it”), not “the reason for why”.',
    'Nobody explained the reason for why the vote was moved.',
    'Nobody explained the reason why the vote was moved. Nobody explained the reason for the move.',
    'Nobody explained the reason why the vote was moved.', SEC)

NEG_AUX = (r"(?:don['’]t|doesn['’]t|didn['’]t|can['’]t|couldn['’]t|won['’]t|wouldn['’]t|haven['’]t|hasn['’]t|hadn['’]t|"
           r"shouldn['’]t|cannot|do not|does not|did not|will not|would not|could not|have not|has not|had not)")
add('negation.neither_of_after_not',
    r"(?i)\b" + NEG_AUX + r"(?: [a-z'’]+){0,2} (?P<target>neither) (?:of|one)\b",
    'either', 'Grammar', 0.88,
    'After “not”, use “either”; “not … neither” is a double negative.',
    'I don’t want neither of the two offers.',
    'I don’t want either of the two offers. I want neither of the two offers. I didn’t stay and neither did they.',
    'I don’t want either of the two offers.', SEC)

add('correlative.not_only_comma_also',
    r"(?i)\bnot only(?:\s+" + not_in(['but', 'and', 'also', 'or']) + r"){1,10},\s+(?P<target>also)\b",
    'but also', 'Grammar', 0.88,
    '“Not only … but also”: add “but” before “also”.',
    'The tool is not only fast, also very easy to learn.',
    'The tool is not only fast but also very easy to learn. The tool is not only fast, but also very easy to learn. The tool is fast, also easy to learn.',
    'The tool is not only fast, but also very easy to learn.', SEC)

# ---- connectors written as two words or with a wrong first word ---------------------------------------------------------
add('compound.bye_the_way',
    r"(?i)\b(?P<target>bye|buy) the way,",
    'by', 'Spelling', 0.9,
    'The phrase is “by the way”.',
    'Bye the way, the invoice is attached.',
    'By the way, the invoice is attached. We said bye. Buy the tickets when you can.',
    'By the way, the invoice is attached.', SEC)

add('compound.hence_forth',
    r"(?i)\b(?P<target>hence forth)\b",
    'henceforth', 'Spelling', 0.9,
    'The word is one word: “henceforth”.',
    'Hence forth, all requests go through the portal.',
    'Henceforth, all requests go through the portal. Hence, forth the argument.',
    'Henceforth, all requests go through the portal.', SEC)

add('compound.any_ways',
    r"(?im)" + START + r"(?P<target>any ways),",
    'anyway', 'Spelling', 0.88,
    'The connector is “anyway”.',
    'Any ways, I will send the file tonight.',
    'Anyway, I will send the file tonight. In any way, shape or form, it works.',
    'Anyway, I will send the file tonight.', SEC)
