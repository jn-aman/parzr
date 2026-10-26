"""Wrong prepositions after feelings and verbs, "eat medicine", mass nouns with an "s", and "from" with a year or
a state: plain errors found by probing the engine with writer-style sentences."""
from lib import R
from timewords import NUM, UNITS, MID, PLURAL, THIRD


def build():
    prepositions()
    collocations()
    time_from_year()


def prepositions():
    R('ashamed.on',
      r"(?i)\b(?:am|is|are|was|were|be|been|feel|feels|felt|feeling|['’]m|['’]s|['’]re|so|very|really|quite|too|also) ashamed (?P<target>on|from) (?:the|this|that|my|your|his|her|their|our|what|how|it|him|them|me|us|you|myself|himself|herself)\b",
      'of', 'Grammar', 0.9, 'You are “ashamed of” something.',
      'She is ashamed on her mistake.', 'She is ashamed of her mistake.',
      'She is ashamed of her mistake. He felt ashamed for you. Shame on the thief.')
    R('upset.with',
      r'(?i)\b(?:dissatisfied|impressed|pleased|annoyed|upset) (?P<target>of|from) (?:the|this|that|these|those|my|your|his|her|their|our|me|him|them|us|you|it)\b',
      'with', 'Grammar', 0.88, 'These feelings go with “with”: “impressed with your work”, “upset with him”.',
      'He is impressed from your work.', 'He is impressed with your work.',
      'He is impressed with your work. She is upset about the delay. We are pleased by the news.')
    R('meet.to', r'(?i)\bmeet(?:s|ing)? (?P<target>to )(?:him|her|them|me|us|you)\b', '', 'Grammar', 0.9,
      '“Meet” takes the person directly: “meet him”.',
      'I will meet to him tomorrow.', 'I will meet him tomorrow.',
      'I will meet him tomorrow. We meet to discuss the plan. They agreed to meet them.')
    R('thank.to', r'(?i)\bthank (?P<target>to )(?:you|him|her|them|everyone|everybody|all|us|me)\b', '', 'Grammar', 0.9,
      '“Thank” takes the person directly: “thank you all”. “Thanks to” is a different phrase.',
      'Thank to you all for coming.', 'Thank you all for coming.',
      'Thank you all for coming. Thanks to you all, we won.')
    R('rid.from', r'(?i)\b(?:get|gets|got|getting|gotten|be|is|are|was|were|am|been|to|help|need) rid (?P<target>from)\b', 'of', 'Grammar', 0.93,
      'The phrase is “get rid of”.', 'We need to get rid from the old system.', 'We need to get rid of the old system.',
      'We need to get rid of the old system. The offer came from the old system.')
    R('holiday.on', r"(?i)\b(?:am|is|are|was|were|be|been|['’]m|['’]s|['’]re) (?P<target>in) (?:holiday|vacation)(?:[.,;!?]|$| (?:till|until|from|for|now|today|tomorrow|since|this|next))",
      'on', 'Grammar', 0.9, 'You are “on holiday” or “on vacation”.',
      'I am in holiday till Monday.', 'I am on holiday till Monday.',
      'I am on holiday till Monday. We are in holiday mood. He lives in vacation homes.')
    R('about.verbs',
      r'(?i)\b(?:highlight|suggest|propose|clarify|narrate|raise|cover|state)(?:ed|es|s|ing)? (?P<target>about )(?:the|this|that|these|those|our|your|his|her|their|my|a|an|it|them)\b',
      '', 'Grammar', 0.9, 'These verbs take their object directly: “highlight the risks”, not “highlight about the risks”.',
      'He highlighted about the risks.', 'He highlighted the risks.',
      'He highlighted the risks. We talked about the risks. She raised concerns about the risks.')
    R('check.about', r'(?i)\bcheck(?:ed|s|ing)? (?P<target>about) (?:the|this|that|these|those|our|your|his|her|their|my)\b', 'on', 'Grammar', 0.88,
      'Say “check on the status” (or “check the status”); “check about” is not used.',
      'Please check about the status.', 'Please check on the status.',
      'Please check on the status. Please check the status. We talked about the status.')
    R('marry.to',
      r"(?i)\b(?:will|would|to|can|could|should|must|may|might|did|do|does|don['’]t|didn['’]t|wants? to|going to|gonna) (?:never |not |also )?marry (?P<target>to )(?:him|her|them|me|us|you|a|an|my|his|their|someone|anyone|somebody)\b",
      '', 'Grammar', 0.9, '“Marry” takes the person directly: “marry him”; “married to” is for the state.',
      'She wants to marry to him.', 'She wants to marry him.',
      'She wants to marry him. She is married to him. They plan to marry in June.')


def collocations():
    why = 'You “take” medicine; you do not eat it.'
    neg = 'He takes the medicine twice a day. I will eat dinner after the tablets. She took her pills.'
    for rid, word, rep, pos, exp in [
        ('medicine.eat', 'eat', 'take', 'Please eat the medicine after food.', 'Please take the medicine after food.'),
        ('medicine.ate', 'ate', 'took', 'He ate the tablets at night.', 'He took the tablets at night.'),
        ('medicine.eating', 'eating', 'taking', 'She is eating some pills for it.', 'She is taking some pills for it.'),
        ('medicine.eaten', 'eaten', 'taken', 'Have you eaten your medicine?', 'Have you taken your medicine?'),
    ]:
        R(rid, rf'(?i)\b(?P<target>{word}) (?:the |some |my |his |her |your |a |this |that )?(?:medicine|medicines|tablet|tablets|pill|pills)\b', rep,
          'Word choice', 0.88, why, pos, exp, neg)
    R('works.lots', r'(?i)\b(?:lots of|a lot of|plenty of|loads of|so much|too much) (?P<target>works)(?: to do| pending| left| today| tomorrow| at home| in the office| here| there|[.,;!?]|$)',
      'work', 'Grammar', 0.88, '“Work” in the sense of tasks is not counted: “lots of work”.',
      'I have lots of works to do.', 'I have lots of work to do.',
      'I have lots of work to do. A lot of works by Picasso hang there. He studied the works of Tagore.')
    R('mass.data', r'(?i)\b(?P<target>datas)\b', 'data', 'Grammar', 0.93, '“Data” is already plural; there is no “datas”.',
      'The datas are ready for review.', 'The data are ready for review.', 'The data are ready for review. The data is ready for review.')
    R('mass.music', r'(?i)\b(?P<target>musics)\b', 'music', 'Grammar', 0.9, '“Music” is not counted: there is no “musics”.',
      'Hindi musics are nice.', 'Hindi music are nice.', 'Hindi music is nice. She likes all kinds of music.')
    R('weekend.on', r'(?i)\b(?P<target>on weekend)(?:[.,;!?]|$| (?:and|but|or|so|then|only|too|also|because|if|when))', 'on the weekend', 'Grammar', 0.88,
      'A weekend needs “the”: “on the weekend” (or “at the weekend”).',
      'I will come on weekend.', 'I will come on the weekend.',
      'I will come on the weekend. We work on weekend days only. The shop opens on weekends.')
    R('in.details_verb',
      r"(?i)\b(?:explain|explained|describe|described|discuss|discussed|elaborate|elaborated|tell|told|write|wrote|mention|mentioned|share|shared|check|checked|read|study|studied|see|saw|look|looked|go|went|cover|covered)(?: [\w'’]+){0,3} in (?P<target>details)(?:[.,;!?]|$)",
      'detail', 'Grammar', 0.88, 'The phrase is “in detail”.',
      'Please explain it in details.', 'Please explain it in detail.',
      'Please explain it in detail. We looked at the details. The devil is in the details.')
    R('in.details_start', r'(?im)(?:^|[.!?]\s+)in (?P<target>details),', 'detail', 'Grammar', 0.88, 'The phrase is “in detail”.',
      'In details, please explain the plan.', 'In detail, please explain the plan.',
      'In detail, please explain the plan. In the details, the plan is sound.')


def time_from_year():
    why = 'For a time that began in the past and goes on, use the present perfect with “since”: “I have been working here since 2018”.'
    year = r'(?:19|20)\d\d'
    mid = r"(?: here| there| still| also| already| just| now| in [a-z]+| at [a-z]+| for [a-z]+| with [a-z]+)?"
    end = r'(?:[.,;!?]|$| (?:and|but|so|because|as|now|today)\b)'
    for who, subj, aux, pos, exp in [
        ('plural', PLURAL, 'have been', 'I am working here from 2018.', 'I have been working here since 2018.'),
        ('third', THIRD, 'has been', 'He is living here from 2015.', 'He has been living here since 2015.'),
    ]:
        R(f'from.year.{who}', rf'(?i)\b(?P<target>{subj} (?P<v>[a-z]+ing)(?P<mid>{mid}) from) {year}{end}', '${s} ' + aux + ' ${v}${mid} since', 'Tense', 0.9, why,
          pos, exp, 'I am working here from 2018 to 2020. I have been working here since 2018. The class runs from 2018.')
    part = r'married|divorced|retired|settled|employed|engaged|based|posted|stationed|separated'
    for who, subj, aux, pos, exp in [
        ('plural', PLURAL, 'have been', 'We are married from five years.', 'We have been married for five years.'),
        ('third', THIRD, 'has been', 'She is settled here from ten years.', 'She has been settled here for ten years.'),
    ]:
        R(f'from.state_duration.{who}', rf'(?i)\b(?P<target>{subj} (?P<v>{part})(?P<mid>{MID}) from) (?:{NUM}) (?:{UNITS})\b', '${s} ' + aux + ' ${v}${mid} for', 'Tense', 0.9,
          'For a state that began in the past and goes on, use the present perfect with “for”: “we have been married for five years”.',
          pos, exp, 'We are married from five different families. We have been married for five years.')
