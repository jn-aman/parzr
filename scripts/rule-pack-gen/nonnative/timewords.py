"""Time expressions: "from" or "before" where English says "for", "since" or "ago", and the Hindi "pichle ke pichle"
doubling ("last to last week")."""
from lib import R

NUM = r'(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty|thirty|few|several|many|couple of)'
UNITS = r'(?:years?|months?|weeks?|days?|hours?|minutes?|decades?)'
MID = r'(?: here| there| still| also| already| just| now| continuously| regularly)?'
FOLLOW = r'(?:[.,;!?]|$| (?:and|but|now|so|because|as|till|until)\b)'
PLURAL = r"(?P<s>I|we|you|they)(?: am|['’]m| are|['’]re)"
THIRD = r"(?P<s>he|she|it)(?: is|['’]s)"


def build():
    for who, subj, aux, pos, exp in [
        ('plural', PLURAL, 'have been', 'I am working here from last three years.', 'I have been working here for the last three years.'),
        ('third', THIRD, 'has been', 'She is working here from last three years.', 'She has been working here for the last three years.'),
    ]:
        R(f'from.last_duration.{who}', rf'(?i)\b(?P<target>{subj} (?P<v>[a-z]+ing)(?P<mid>{MID}) from (?:the )?(?P<w>last|past)) (?:{NUM}) (?:{UNITS})\b',
          '${s} ' + aux + ' ${v}${mid} for the ${w}', 'Tense', 0.9,
          'For a time that began in the past and goes on, use the present perfect with “for”: “I have been working here for the last three years”.',
          pos, exp,
          'I am working from the last three pages of the report. I am looking at data from the last three years. I have been working here for the last three years.')
    for who, subj, aux, pos, exp in [
        ('plural', PLURAL, 'have been', 'We are living here from five years.', 'We have been living here for five years.'),
        ('third', THIRD, 'has been', 'He is teaching here from ten years.', 'He has been teaching here for ten years.'),
    ]:
        R(f'from.duration.{who}', rf'(?i)\b(?P<target>{subj} (?P<v>[a-z]+ing)(?P<mid>{MID}) from) (?:{NUM}) (?:{UNITS})\b',
          '${s} ' + aux + ' ${v}${mid} for', 'Tense', 0.9,
          'For a time that began in the past and goes on, use the present perfect with “for”: “we have been living here for five years”.',
          pos, exp, 'We are leaving here from five different doors. We have been living here for five years.')
    times = r'(?:morning|yesterday|last night|last week|last month|last year|this morning|afternoon|evening|noon|dawn|the morning|early morning)'
    states = r'waiting|suffering|trying|struggling|facing|feeling|sitting|standing|sleeping|studying|living|staying|running|searching|looking|calling|messaging|following|asking|requesting|reminding|hoping|thinking|crying|coughing|vomiting'
    for who, subj, aux, pos, exp in [
        ('plural', PLURAL, 'have been', 'I am waiting from morning.', 'I have been waiting since morning.'),
        ('third', THIRD, 'has been', 'He is waiting from morning.', 'He has been waiting since morning.'),
    ]:
        R(f'from.point.{who}', rf'(?i)\b(?P<target>{subj} (?P<v>{states})(?P<mid>{MID}) from (?P<t>{times}))\b',
          '${s} ' + aux + ' ${v}${mid} since ${t}', 'Tense', 0.9,
          'For a time that began in the past and goes on, use the present perfect with “since”: “I have been waiting since morning”.',
          pos, exp, 'I am waiting from the car window. I have been waiting since morning. She is looking from the roof.')
    perf = r"(?:have|has|had)(?: not| never)?(?: been| seen| heard| met| spoken| talked| eaten| slept| gone| received| had| got| taken| used| tried| felt| worked| lived| done)(?: [\w'’]+){0,2}"
    R('from.perfect_last', rf'(?i)\b{perf} (?P<target>from (?:the )?(?P<w>last|past)) (?:{NUM}) (?:{UNITS}){FOLLOW}', 'for the ${w}', 'Tense', 0.9,
      'With the present perfect, “for the last three days” gives the length of time; “from” does not.',
      'I have not seen him from last three days.', 'I have not seen him for the last three days.',
      'I have not seen him for the last three days. We have data from the last three years ago.')
    R('from.perfect_duration', rf'(?i)\b{perf} (?P<target>from) (?:{NUM}) (?:{UNITS}){FOLLOW}', 'for', 'Tense', 0.9,
      'With the present perfect, “for two weeks” gives the length of time; “from” does not.',
      'I have not seen him from two weeks.', 'I have not seen him for two weeks.',
      'I have not seen him for two weeks. We have notes from two weeks ago.')
    R('before.ago',
      r"(?i)\b(?:was|were|had|did|met|saw|joined|started|left|happened|came|got|bought|ordered|sent|told|said|asked|wrote|completed|finished|resigned|released|launched|checked|noticed|received|read|heard|spoke|talked|called|visited|reached|arrived|returned|found|lost|learned|began|ended|worked|lived|stayed|married|passed|graduated|submitted|filed|reported|fixed|booked|paid|cancelled|canceled)\b(?: [\w'’]+){0,5}? (?P<target>before )(?P<moved>(?:\d+|an?|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|few|several|some|couple of) (?:years?|months?|weeks?|days?|hours?|minutes?))(?:[.,;!?]|$| (?:and|but|only|also)\b)",
      ' ago', 'Word choice', 0.88, 'For a time in the past, “two days ago” is the usual form; “before two days” sounds wrong.',
      'I met him before two days.', 'I met him two days ago.',
      'I met him two days ago. I met him before lunch. We started the work before two days of rain.')
    R('last_to_last', r'(?i)\b(?P<target>last to last (?P<u>week|month|year|night))\b', 'the ${u} before last', 'Register', 0.75,
      '“Last to last week” is mainly Indian usage; say “the week before last”.',
      'We met last to last week.', 'We met the week before last.', 'We met the week before last. We met last week.')
