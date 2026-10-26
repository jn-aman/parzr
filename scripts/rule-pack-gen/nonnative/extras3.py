""""Thinking to" plus a verb, "for to", and a few doubled words, from probing writer-style sentences."""
from lib import R
from extras2 import FROM_POINT, TP_END


def build():
    wanted_things()
    thinking_to()
    small_redundancies()
    perfect_from_point()


def thinking_to():
    why = 'After “thinking”, use “of” and the “-ing” form: “thinking of buying”, not “thinking to buy”.'
    lead = r"(?:am|is|are|was|were|['’]m|['’]s|['’]re|been|keep|kept|just|also|now) thinking"
    neg = 'I am thinking of buying a car. She thinks to herself that it is late. We were thinking about it.'
    plain = ('buy|go|start|join|apply|visit|learn|try|ask|call|send|open|launch|build|study|travel|order|book|check|add|attend|work|focus|'
             'pursue|switch|shift|enroll|enrol|register|download|install|upgrade|speak|talk|do|see|meet|stay|invest|teach|sell|find')
    edrop = 'tak|mak|mov|chang|relocat|resum|leav|purchas|writ|giv|quit|sav|hir|solv|invit|us|propos|driv|rid|retir|resign|reduc|increas|continu|schedul|prepar|organiz|organis|arrang|replac|releas|choos'
    R('thinking.to_plain', rf'(?i)\b{lead} (?P<target>to (?P<v>{plain}))\b', 'of ${v}ing', 'Grammar', 0.9, why,
      'I am thinking to buy a car.', 'I am thinking of buying a car.', neg)
    R('thinking.to_edrop', rf'(?i)\b{lead} (?P<target>to (?P<v>{edrop})e)\b', 'of ${v}ing', 'Grammar', 0.9, why,
      'She is thinking to change her job.', 'She is thinking of changing her job.', neg)
    for rid, group, last, pos, exp in [
        ('thinking.to_n', 'plan|run|win|begin', 'n', 'We are thinking to plan a trip.', 'We are thinking of planning a trip.'),
        ('thinking.to_p', 'shop|swap|stop', 'p', 'He is thinking to shop online.', 'He is thinking of shopping online.'),
        ('thinking.to_t', 'get|put|set|sit|cut|hit|quit|chat', 't', 'I am thinking to get a dog.', 'I am thinking of getting a dog.'),
    ]:
        R(rid, rf'(?i)\b{lead} (?P<target>to (?P<v>{group}))\b', 'of ${v}' + last + 'ing', 'Grammar', 0.9, why, pos, exp, neg)
    R('looking.for_to',
      r'(?i)\b(?:looking|waiting|hoping|searching|asking|wishing|longing|aiming|working|trying|planning|preparing|ready|eager|keen|willing) (?P<target>for )to (?:buy|get|find|start|join|apply|learn|try|go|do|make|take|see|meet|speak|talk|know|work|hire|move|change|update|check|use|build|test|book|order|purchase|visit|improve|increase|reduce|grow|finish)\b',
      '', 'Grammar', 0.9, 'Say “looking to buy”, not “looking for to buy”.',
      'We are looking for to hire a designer.', 'We are looking to hire a designer.',
      'We are looking to hire a designer. We are looking for a to-do app. I am waiting for it to finish.')


def small_redundancies():
    R('also.too', r'(?i)\b(?P<target>also too)\b(?: [a-z])', 'also', 'Redundancy', 0.85, '“Also” and “too” mean the same; one is enough.',
      'I also too went to the meeting.', 'I also went to the meeting.',
      'I also went to the meeting. I went too. I want it too, also.')
    R('too.also', r'(?i)\b(?P<target>too also)\b(?: [a-z])', 'too', 'Redundancy', 0.85, '“Too” and “also” mean the same; one is enough.',
      'Me too also want to join.', 'Me too want to join.',
      'Me too want to join. She also wants to join.')
    R('like.for_example', r'(?i)\b(?P<target>like for example)\b', 'for example', 'Redundancy', 0.85,
      '“Like” and “for example” do the same job; use one.',
      'Bring snacks, like for example chips.', 'Bring snacks, for example chips.',
      'Bring snacks, for example chips. Bring snacks, like chips.')


def perfect_from_point():
    R('from.perfect_point',
      rf"(?i)\b(?P<target>(?P<w>[a-z]+) (?P<h>have|has|had)(?P<neg>(?: not| never)?) been(?P<m>(?: [a-z]+)?) from) {FROM_POINT}{TP_END}",
      '${w} ${h}${neg} been${m} since', 'Tense', 0.9,
      'For a time that began in the past and goes on, use “since”: “has been absent since yesterday”.',
      'She has been absent from yesterday.', 'She has been absent since yesterday.',
      'She has been absent since yesterday. The pages have been open from morning to night. We have been back from the trip.')


def wanted_things():
    R('looking.object',
      r'(?i)\blook(?:ing|ed|s)? (?P<target>(?P<d>a|an|my|his|her|their|our|new|good)) (?:jobs?|solutions?|answers?|roommates?|partners?|flats?|houses?|rooms?|apartments?|tutors?|teachers?|mentors?|ways?|laptops?|phones?|buyers?|suppliers?|vendors?)\b',
      'for ${d}', 'Grammar', 0.9, 'To say what you want to find, use “look for”: “looking for a flat”.',
      'He is looking a flat near the office.', 'He is looking for a flat near the office.',
      'He is looking for a flat near the office. She looked a long way from the road. They look a good team.')
    R('till.place',
      r'(?i)\b(?:come|came|coming|comes|go|went|going|goes|walk|walked|walking|reach|reached|reaching|bring|brought|take|took|taking|send|sent|sending|follow|followed) (?:me |you |him |her |us |them |it )?(?P<target>till) (?:the |my |your |his |her |our |their )(?:station|airport|office|gate|door|market|house|home|desk|city|hotel|school|college|bus stop|stop|corner|road|park|mall|hospital|metro|junction|temple)\b',
      'to', 'Word choice', 0.88, 'For a place you go to, use “to”; “till” is for time: “I will drop you to the station” or “… at the station”.',
      'Please come till my desk.', 'Please come to my desk.',
      'Please come to my desk. Please wait till the office opens. We worked till the market closed.')
    R('drop.till',
      r'(?i)\bdrop(?:ped|ping|s)? (?:me|you|him|her|us|them) (?P<target>till) (?:the |my |your |his |her |our |their )(?:station|airport|office|gate|door|market|house|home|corner|road|park|mall|hospital|metro|junction|stop)\b',
      'at', 'Word choice', 0.88, 'For the place where someone is left, use “at”; “till” is for time.',
      'I will drop you till the station.', 'I will drop you at the station.',
      'I will drop you at the station. Please wait till the office opens.')
