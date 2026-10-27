"""Statements about a state that began in the past, verbs that need "how to" or an object, and small redundancy
patterns, found by probing writer-style sentences."""
from lib import R

STATES = (r'down|pending|stuck|blocked|broken|slow|absent|sick|ill|unwell|locked|unavailable|offline|not working|not responding|not loading|'
          r'not opening|not available|not reachable|not well|not coming|failing|crashing|freezing|hanging|raining|snowing|closed')
SINCE_POINT = (r'(?:morning|yesterday|last (?:night|week|month|year|monday|tuesday|wednesday|thursday|friday|saturday|sunday)|this (?:morning|week|month|year)|'
               r'the morning|monday|tuesday|wednesday|thursday|friday|saturday|sunday|noon|dawn|then|\d)')
FROM_POINT = r'(?:morning|yesterday|last night|last week|last month|last year|this morning|afternoon|the morning|early morning)'
TP_END = r'(?:[.,;!?]|$| (?:and|but|so|because|as|now|today|still|also|please|due|only)\b)'


def build():
    states_since()
    verbs_and_objects()
    redundancy()


def states_since():
    why = 'A state that began in the past and still holds takes the present perfect: “has been down since morning”.'
    for rid, aux, rep, pos, exp in [
        ('since.is', 'is', 'has been', 'The server is down since morning.', 'The server has been down since morning.'),
        ('since.are', 'are', 'have been', 'The servers are down since yesterday.', 'The servers have been down since yesterday.'),
    ]:
        R(rid, rf'(?i)\b(?P<target>{aux}) (?:{STATES}) since {SINCE_POINT}', rep, 'Tense', 0.9, why, pos, exp,
          'The server has been down since morning. The server is down because the disk is full. The server is down since we deployed. '
          'The servers have been down since yesterday. The servers are down because of the storm.')
    for rid, aux, rep, pos, exp in [
        ('from.state_is', 'is', 'has', 'The payment is pending from last month.', 'The payment has been pending since last month.'),
        ('from.state_are', 'are', 'have', 'The servers are down from yesterday.', 'The servers have been down since yesterday.'),
    ]:
        R(rid, rf'(?i)\b(?P<target>(?P<w>[a-z]+) {aux} (?P<st>{STATES}) from) {FROM_POINT}{TP_END}', '${w} ' + rep + ' been ${st} since', 'Tense', 0.9, why, pos, exp,
          'The payment has been pending since last month. The shop is open from morning to night. The data is down from the old system.')


def verbs_and_objects():
    R('told.that', r'(?i)\b(?:I|he|she|they|we|you|who)(?: (?:also|just|already|then|only|even|once|again|clearly|quickly|firmly|simply))* (?P<target>told) that (?:he|she|they|I|we|you|it|there|everyone|everybody|someone|nobody|the|my|our|his|her|their)\b',
      'said', 'Word choice', 0.88, '“Tell” needs a person after it: “told him that…”. Without one, say “said that…”.',
      'He told that he will come.', 'He said that he will come.',
      'He told me that he will come. He told that story twice. I was told that he will come. We were told that she left. I have been told that it is late. She said that she would come.')
    R('much.adj', r"(?i)\b(?:am|is|are|was|were|['’]m|['’]s|['’]re|feel|feels|felt|feeling|looks?|looked|seems?|seemed) (?P<target>much) (?:happy|glad|sorry|tired|busy|angry|hungry|sad|sure|scared|nervous|proud|thankful|grateful|keen|big|small|fast|slow|easy|difficult|important|useful|helpful|clear|nice|beautiful|cold|hot|tall)\b(?:[.,;!?]|$| (?:today|now|about|with|to|for|and|but|that|because))",
      'very', 'Grammar', 0.88, 'Use “very” before an adjective: “very happy”. “Much” goes before comparatives (“much better”).',
      'I am much happy today.', 'I am very happy today.',
      'I am very happy today. She is much better now. It is much too cold.')
    R('know.how_to', r'(?i)\b(?:know|knows|knew|known|knowing) (?P<target>to) (?:swim|drive|cook|dance|sing|ride|fly|cycle|sew|paint|draw|ski|skate|surf|row|sail|bake|dive|juggle|knit|speak|type|code|program)\b',
      'how to', 'Grammar', 0.9, 'To say you have a skill, use “know how to”: “I know how to swim”.',
      'Do you know to swim?', 'Do you know how to swim?',
      'Do you know how to swim? Let me know to whom I should write. I know to expect delays.')
    R('reply.back', r'(?i)\b(?P<target>(?P<v>reply|replied|replying|replies|respond|responded|responding|responds) back)\b', '${v}', 'Redundancy', 0.72,
      '“Back” is not needed: “reply” and “respond” already mean answering.',
      'Please reply back soon.', 'Please reply soon.',
      'Please reply soon. I will write back soon. He answered back.')
    R('takes.time', r'(?i)\b(?:take|takes|took|taking|taken) (?:about |around |nearly |almost |only |just |at least |roughly |another |some )?(?:\d+|a few|a|an|one|two|three|four|five|six|seven|eight|nine|ten|twelve|few|half an|half a|several)(?: or (?:two|three|four|five))? (?:hours?|minutes?|days?|weeks?|months?|years?)(?P<target> time)\b',
      '', 'Redundancy', 0.85, '“Two hours” already says how long; “time” is not needed after it.',
      'It takes two days time to deliver.', 'It takes two days to deliver.',
      "It takes two days to deliver. It takes two days' time to deliver. It takes some time.")


def redundancy():
    R('same.prep', r'(?i)\b(?:on|about|regarding|with|for) (?P<target>the same)(?:[.,;!?]|$)', 'it', 'Style', 0.64,
      '“The same” is not a pronoun in everyday English. Say “it” (or “them” for more than one thing).',
      'Please share an update on the same.', 'Please share an update on it.',
      'Please share an update on the same day. We tested more of the same. I use the same laptop.')
