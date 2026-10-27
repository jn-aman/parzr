"""Emphasis words that Hindi "hi" and "bhi" leave behind: "itself" after a time or place, and "only" after a time."""
from lib import R

END = r'(?:[.,;!?]|$| (?:and|but|so|then|or|only|otherwise|if|before|as)\b)'


def build():
    why = '“Itself” adds nothing here; English just says the time or place: “today”, “here”.'
    R('itself.time', rf'(?i)\b(?:today|tomorrow|tonight|now|yesterday|immediately|right now|right away)(?P<target> itself){END}', '', 'Register', 0.7, why,
      'I will send it today itself.', 'I will send it today.',
      'Today itself is a holiday. I will send it today. The day itself was calm.')
    R('itself.period', rf'(?i)\b(?:this|next|last|tomorrow|today|yesterday) (?:week|month|year|morning|evening|afternoon|weekend|quarter|night)(?P<target> itself){END}', '', 'Register', 0.7, why,
      'We will finish it tomorrow morning itself.', 'We will finish it tomorrow morning.',
      'This week itself brought three launches. We will finish it this week. The week itself was calm.')
    R('itself.place', rf'(?i)\b(?:here|there|home|office|inside|outside|upstairs|downstairs)(?P<target> itself){END}', '', 'Register', 0.7, why,
      'I will finish it here itself.', 'I will finish it here.',
      'I will finish it here. The office itself is small. The house itself needs paint.')
    R('itself.start',
      rf'(?i)\b(?:in|at|from|on|within|by) the (?:very )?(?:beginning|start|first (?:day|week|month|attempt|round|step|stage|meeting|call|session|go|try|instance))(?P<target> itself){END}',
      '', 'Register', 0.7, '“Itself” adds nothing here; “at the start” already says it.',
      'We should have fixed it at the start itself.', 'We should have fixed it at the start.',
      'We should have fixed it at the start. The start itself was slow.')
    R('itself.same', rf'(?i)\bthe same (?:day|week|month|year|time|place|night)(?P<target> itself){END}', '', 'Register', 0.7,
      '“Itself” adds nothing here; “the same day” already says it.',
      'I replied the same day itself.', 'I replied the same day.',
      'I replied the same day. The same day itself was a surprise.')
    R('only.just_time',
      r"(?i)\b(?:got|received|saw|joined|reached|came|started|finished|completed|noticed|heard|learned|arrived|woke|landed|left|sent|submitted|checked|read|realized|realised|understood|discovered|returned)\b(?: [\w'’]+){0,4}? (?P<target>(?P<w>now|yesterday|today|last (?:week|month|year|night)|this morning) only)(?:[.,;!?]|$)",
      'just ${w}', 'Register', 0.68, 'In English, “just now” or “only yesterday” puts the emphasis before the time word, not “only” after it.',
      'I received your mail now only.', 'I received your mail just now.',
      'I received your mail just now. Tickets are on sale today only. The offer ends today only.')
    R('only.right_here',
      r"(?i)\b(?:I am|I['’]m|we are|we['’]re|he is|he['’]s|she is|she['’]s|they are|they['’]re|you are|you['’]re|it is|it['’]s) (?P<target>(?P<w>here|there) only)(?:[.,;!?]|$)",
      'right ${w}', 'Register', 0.68, 'In English, “right here” or “right there” is the emphatic form; “here only” is mainly Indian usage.',
      'He is there only.', 'He is right there.', 'He is right there. He is here only for the demo.')
