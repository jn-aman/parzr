"""Marks and spacing: doubled spaces, spaces and glued marks the engine does not catch, ellipsis and bracket spacing,
e.g. / i.e. / et al., colons that split a verb from its list, wh-questions ended with a period, stray commas."""
import re
import core

START = r'(?im)(?:^|[.!?]["”’)]*\s+)'

TOP_WORDS = ('the|and|that|with|for|you|this|have|are|was|not|but|from|they|will|your|can|all|were|been|has|our|their|'
             'which|would|about|there|what|when|your|just|more|than')


def spacing_rules():
    core.add('spacing.double_space_after_word', rf'(?i)\b(?:{TOP_WORDS})(?P<target> {{2,}})[A-Za-z]', ' ', 'Style', 0.8,
             'Use a single space between words.', 'We sent the  report today.',
             'We sent the report today. Line one ends here.  \nLine two starts here.')
    core.add('spacing.double_space_before_word', rf'(?i)[A-Za-z](?P<target> {{2,}})(?:{TOP_WORDS})\b', ' ', 'Style', 0.8,
             'Use a single space between words.', 'We sent the report  and the notes.',
             'We sent the report and the notes. Line one ends here.  \nThe next line starts here.')
    core.add('spacing.year_space_comma',
             r'(?i)\b(?:in|on|by|since|until|after|before|during|from|of|around|about|through)\s+(?:19|20)\d\d(?P<target>[ \t]+),',
             '', 'Punctuation', 0.95, 'Remove the space before the comma.', 'We moved in 2019 , right after the merger.',
             'We moved in 2019, right after the merger. We moved in 2019 and then left.')
    core.add('spacing.bracket_space_comma',
             r'\)(?P<target>[ \t]+)(?:,|;)(?: and| but| which| so| or| then)\b', '', 'Punctuation', 0.95,
             'Remove the space before the comma.', 'We booked the hall (the big one) , and then called.',
             'We booked the hall (the big one), and then called. We booked the hall (the big one) and then called.')
    core.add('spacing.year_comma_glued',
             r'(?i)\b(?:19|20)\d\d(?P<target>,)(?:we|it|they|she|he|there|you|our|my|the|an)\b', ', ', 'Punctuation',
             0.94, 'Add a space after the comma.', 'In 2019,we moved to Lisbon.',
             'In 2019, we moved to Lisbon. The total was 2,019 units.')
    core.add('spacing.bracket_comma_glued',
             r'\)(?P<target>,)(?:and|but|so|which|then|or|because|as|when|while)\b', ', ', 'Punctuation', 0.94,
             'Add a space after the comma.', 'We booked the hall (the big one),and then called.',
             'We booked the hall (the big one), and then called.')


# --- a period glued to the next sentence ---------------------------------------------------------------------------------
OPENERS = ('Hello Hi Dear Regards Hopefully Unfortunately Fortunately Anyway Maybe Perhaps Finally Today Tomorrow '
           'Yesterday Tonight Sure Great Kind Best Sincerely Cheers Because Although While Once Unless Until Whether '
           'Whenever Honestly Actually Basically Obviously Apparently Luckily Sadly Thankfully').split()


GREETINGS = {'Hello', 'Hi', 'Dear', 'Regards', 'Best', 'Kind', 'Sincerely', 'Cheers'}
SUBORDINATORS = {'Because', 'Although', 'While', 'Once', 'Unless', 'Until', 'Whether', 'Whenever'}


def glued_period_rules():
    for w in OPENERS:
        tail = 'everyone' if w in GREETINGS else ('we can start, we will call you' if w in SUBORDINATORS else 'we can start')
        core.add('spacing.period_glued_' + w.lower(), rf'\b[a-z]{{2,}}(?P<target>\.){w}(?:[ ,]|$)', '. ', 'Punctuation',
                 0.92, 'Add a space after the period that ends the sentence.',
                 f'The file is ready.{w} {tail}.', f'The file is ready. {w} {tail}.',
                 f'The file is ready. {w} {tail}.', loose=True)


# --- ellipsis --------------------------------------------------------------------------------------------------------------
ELLIPSIS_WORDS = ('well so and but hmm um uh oh wait maybe actually anyway okay ok yeah yes no then just like or if '
                  'because honestly sorry sure fine right').split()


def ellipsis_rules():
    for w in ELLIPSIS_WORDS:
        W = w.capitalize()
        core.add('ellipsis.' + w, rf'(?i)\b{w}(?P<target>\.\.\.)[A-Za-z]', '... ', 'Punctuation', 0.9,
                 'Put a space after an ellipsis that is followed by a word.', f'{W}...later then.',
                 f'{W}... later then. We kept the {w} file...',
                 f'{W}... later then.')
    core.add('ellipsis.unicode', r'(?i)\b(?:hmm|well|so|um|uh|oh|wait|maybe|actually|anyway|okay|yeah|honestly|sorry)(?P<target>…)[A-Za-z]',
             '… ', 'Punctuation', 0.9, 'Put a space after an ellipsis that is followed by a word.', 'Well…maybe tomorrow.',
             'Well… maybe tomorrow. We spoke well.')


# --- brackets ---------------------------------------------------------------------------------------------------------------
def bracket_rules():
    words = 'and|but|or|so|then|because|which|that|we|they|you|also|please|thanks'
    core.add('bracket.closing_glued', rf'\w(?P<target>\))(?:{words})\b', ') ', 'Punctuation', 0.9,
             'Add a space after the closing parenthesis.', 'See the note (page 4)and then call us.',
             'See the note (page 4) and then call us.')
    core.add('bracket.opening_glued_eg', r'(?i)\b[a-z]{2,}(?P<target>)\((?:e\.g\.|i\.e\.)', ' (', 'Punctuation', 0.9,
             'Add a space before the opening parenthesis.', 'We use tools(e.g. Jira) every day.',
             'We use tools (e.g. Jira) every day.', e2e=False)
    core.add('bracket.opening_glued_for_example', r'(?i)\b[a-z]{2,}(?P<target>)\((?:for example|for instance|such as)\b',
             ' (', 'Punctuation', 0.9, 'Add a space before the opening parenthesis.',
             'We use tools(for example Jira) every day.', 'We use tools (for example Jira) every day.', e2e=False)


# --- e.g. / i.e. / et al. ---------------------------------------------------------------------------------------------------------
def abbreviation_rules():
    for bare, good in (('eg', 'e.g.'), ('ie', 'i.e.')):
        core.add(f'abbrev.{bare}_final_period', rf'(?-i:(?:^|[\s(,;])(?P<target>{bare}\.))(?:[ ,)])', good, 'Punctuation', 0.9,
                 f'Write “{good}” with a period after each letter.', f'Use a tool, {bare}. Jira, for tracking.',
                 f'Use a tool, {good} Jira, for tracking.')
        inner = good[:-1]
        core.add(f'abbrev.{bare}_missing_last_period', rf'(?-i:(?:^|[\s(,;])(?P<target>{re.escape(inner)}))(?:[ ,)])', good,
                 'Punctuation', 0.9, f'End “{good}” with a period.', f'Use a common word, {inner} apples, in the sentence.',
                 f'Use a common word, {good} apples, in the sentence.')
        spaced = good[0] + '. ' + good[2] + '.'
        core.add(f'abbrev.{bare}_spaced', rf'(?:^|[\s(,;])(?P<target>{good[0]}\. {good[2]}\.)', good, 'Punctuation', 0.9,
                 f'Write “{good}” without a space inside.', f'Use a tool, {spaced} Jira, for tracking.',
                 f'Use a tool, {good} Jira, for tracking.')
    core.add('abbrev.et_al', r'(?i)\b(?P<target>et al)(?:[,;)]|\s+(?:\(|\d{4}|found|showed|argue|argued|report|reported|'
             r'note|noted|suggest|suggested|show|shows|conclude|concluded|propose|proposed|demonstrate|demonstrated|'
             r'describe|described|have|has|were|also)\b)', 'et al.', 'Punctuation', 0.9,
             'Write “et al.” with a period: it is an abbreviation.', 'Smith et al 2020 found the same effect.',
             'Smith et al. 2020 found the same effect. The case was settled by et alia.')


# --- colons that cut a verb or phrase from its list ---------------------------------------------------------------------------
COLON_LEADS = ['including', 'such as', 'consisting of', 'consists of', 'composed of', 'made up of', 'comprising',
               'comprises', 'includes', 'include', 'contains', 'containing', 'featuring', 'among them']


def colon_rules():
    for lead in COLON_LEADS:
        word = lead.replace(' ', '_')
        core.add('colon.after_' + word, rf'(?-i:\b[a-z]+ {lead}(?P<target>:) [A-Z0-9])', '', 'Punctuation', 0.9,
                 f'No colon after “{lead}”: the list follows directly.', f'The kit has tools {lead}: Jira, Slack and Trello.',
                 f'The kit has tools {lead} Jira, Slack and Trello.\n{lead.capitalize()}: Jira, Slack and Trello.')


# --- wh-questions ended with a period -----------------------------------------------------------------------------------------
SUBJ = r"(?:the|my|your|our|their|his|her|its|this|that|these|those|I|you|we|they|he|she|it|everyone|everybody|someone|anyone|there)"
AUX = r"(?:is|are|was|were|do|does|did|can|could|will|would|should|shall|may|might|has|have|had|am)"
AUX_NEG = r"(?:isn't|aren't|wasn't|weren't|don't|doesn't|didn't|can't|couldn't|won't|wouldn't|shouldn't|haven't|hasn't|hadn't)"
REST = r"[^.!?\n,;:()\"“”]{0,100}"


def question_rules():
    items = [
        ('where', 'Where', AUX, 'Where is the meeting room today.', 'Where is the meeting room today?'),
        ('when', 'When', AUX, 'When did you send the invoice.', 'When did you send the invoice?'),
        ('why', 'Why', AUX, 'Why did you move the deadline.', 'Why did you move the deadline?'),
        ('why_neg', 'Why', AUX_NEG, "Why don't you join the call.", "Why don't you join the call?"),
        ('how', 'How', AUX, 'How are you feeling today.', 'How are you feeling today?'),
        ('what', 'What', AUX, 'What is the capital of Peru.', 'What is the capital of Peru?'),
        ('what_neg', 'What', AUX_NEG, "What don't you like about it.", "What don't you like about it?"),
        ('who', 'Who', AUX, 'Who is the new manager.', 'Who is the new manager?'),
        ('whom', 'Whom', AUX, 'Whom did you invite.', 'Whom did you invite?'),
        ('whose', 'Whose', AUX, 'Whose are these keys.', None),
    ]
    for rid, wh, aux, pos, fixed in items:
        if fixed is None:
            continue
        pattern = rf'{START}{wh} {aux} {SUBJ}\b{REST}(?P<target>\.)(?:\s|$)'
        neg = fixed + f' I know {wh.lower()} it is. {wh} the plan changed is unclear.'
        core.add('question.' + rid, pattern, '?', 'Punctuation', 0.88,
                 'A direct question ends with a question mark.', pos, neg, fixed)
    core.add('question.how_much',
             rf'{START}How (?:much|long|often|far|soon|old|big|tall|fast) {AUX} {SUBJ}\b{REST}(?P<target>\.)(?:\s|$)', '?',
             'Punctuation', 0.88, 'A direct question ends with a question mark.', 'How long is the meeting today.',
             'How long is the meeting today? I know how long it is.')
    core.add('question.how_do_much',
             rf'{START}How (?:much|many) (?:do|does|did|will|would|can|could|should) {SUBJ}\b{REST}(?P<target>\.)(?:\s|$)',
             '?', 'Punctuation', 0.88, 'A direct question ends with a question mark.', 'How much does the plan cost.',
             'How much does the plan cost? I know how much it costs.')
    core.add('question.what_time',
             rf'{START}What (?:time|day|date|year|month|kind of [a-z]+|type of [a-z]+|size) {AUX} {SUBJ}\b{REST}(?P<target>\.)(?:\s|$)',
             '?', 'Punctuation', 0.88, 'A direct question ends with a question mark.', 'What time is the call today.',
             'What time is the call today? I know what time it is.')
    core.add('question.which_noun',
             rf'{START}Which (?:one|ones|[a-z]+) (?:do|does|did|is|are|was|were|will|would|can|could|should) {SUBJ}\b{REST}(?P<target>\.)(?:\s|$)',
             '?', 'Punctuation', 0.86, 'A direct question ends with a question mark.', 'Which option do you prefer.',
             'Which option do you prefer? I know which option you prefer.')


# --- stray commas ---------------------------------------------------------------------------------------------------------------
THAT_VERBS = ('said says think thought believe believed know knew hope hoped explained noted stated mentioned reported '
              'claimed suggested realized realised noticed learned heard feel felt found decided wish wished assume '
              'assumed promise promised ensure ensured confirm confirmed discovered argued announced showed proved').split()
THAT_NEXT = r'(?:the|a|an|we|I|you|they|he|she|our|my|your|their|his|her|there|if|when)'


def stray_comma_rules():
    for v in THAT_VERBS:
        subj = 'She' if v == 'says' else 'We'
        # no earlier comma in the sentence: "It presumes, I believe, that ..." is a parenthetical pair
        core.add('comma.after_' + v + '_that',
                 rf'(?im)(?:^|[.!?]\s+)(?:[^,;:.!?\n]{{0,80}}?\b)?{v}(?P<target>,) that {THAT_NEXT}\b', '', 'Punctuation',
                 0.9, f'No comma between “{v}” and “that”.', f'{subj} {v}, that the plan was ready.',
                 f'{subj} {v} that the plan was ready. It presumes, I {v}, that the rule is clear. '
                 f'Whatever we {v}, that is final.')
    comparatives = ('better worse bigger smaller faster slower higher lower easier harder older younger cheaper longer '
                    'shorter larger greater stronger simpler cleaner').split()
    alt = '|'.join(comparatives)
    core.add('comma.before_than', rf'(?i)\b(?:{alt})(?P<target>,) than\b', '', 'Punctuation', 0.9,
             'No comma before “than” in a comparison.', 'This phone is better, than the old one.',
             'This phone is better than the old one. It is better, he said, than nothing.')


def build():
    spacing_rules()
    glued_period_rules()
    ellipsis_rules()
    bracket_rules()
    abbreviation_rules()
    colon_rules()
    question_rules()
    stray_comma_rules()
