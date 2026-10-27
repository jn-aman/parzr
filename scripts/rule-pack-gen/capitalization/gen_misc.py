"""Dates, weekdays, directions, school subjects, stray capitals, planets, history and organizations."""
from lib import *

# ----------------------------------------------------------------------------------------------------------------
# Months and weekdays
# ----------------------------------------------------------------------------------------------------------------

MONTHS = [('jan', 'Jan'), ('feb', 'Feb'), ('mar', 'Mar'), ('apr', 'Apr'), ('jun', 'Jun'), ('jul', 'Jul'),
          ('aug', 'Aug'), ('sep', 'Sep'), ('sept', 'Sept'), ('oct', 'Oct'), ('nov', 'Nov'), ('dec', 'Dec')]
MONTH_ANY = r"(?i:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec|january|february|march|april|june|july|august|september|october|november|december)"
WEEKDAY_SHORT = [('mon', 'Mon'), ('tue', 'Tue'), ('tues', 'Tues'), ('thu', 'Thu'), ('thur', 'Thur'),
                 ('thurs', 'Thurs'), ('fri', 'Fri'), ('sat', 'Sat'), ('sun', 'Sun')]
WEEKDAYS = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']


def build_dates():
    fam = 'Months, weekdays and dates'
    for lower, canon in MONTHS:
        rid = f'caps.date.{lower}'
        emit(rid + '_day', f"{LEFT}(?P<target>(?-i:{lower}))\\.?\\s+\\d{{1,2}}(?:st|nd|rd|th)?(?:\\s*[,.;:!?)\\]]|\\s|$)",
             canon, 'Capitalization', 0.9, 'Months take a capital letter, abbreviated or not.',
             f'The meeting moved to {lower} 14 because of the holiday.',
             f'The meeting moved to {canon} 14 because of the holiday. ' + neg_noise(lower), fam)
        emit(rid + '_after_day', f"\\d(?:st|nd|rd|th)?\\s+(?:of\\s+)?(?P<target>(?-i:{lower}))\\.?(?:\\s*[,.;:!?)\\]]|\\s|$)",
             canon, 'Capitalization', 0.9, 'Months take a capital letter, abbreviated or not.',
             f'The deadline is 14 {lower} at noon.',
             f'The deadline is 14 {canon} at noon. ' + neg_noise(lower), fam)
    for lower, canon in WEEKDAY_SHORT:
        emit(f'caps.date.weekday_{lower}',
             f"{LEFT}(?P<target>(?-i:{lower}))\\.?,?\\s+(?:\\d{{1,2}}(?:st|nd|rd|th)?\\s+{MONTH_ANY}\\b|{MONTH_ANY}\\.?\\s+\\d{{1,2}}\\b)",
             canon, 'Capitalization', 0.9, 'Days of the week take a capital letter, abbreviated or not.',
             f'The flight leaves {lower} 14 March at noon.',
             f'The flight leaves {canon} 14 March at noon. The cat sat on the mat, and we sat in March.', fam)
    for d in WEEKDAYS:
        plural = d + 's'
        canon = plural.capitalize()
        emit(f'caps.date.{plural}', f"{LEFT}(?P<target>(?-i:{plural}))" + RIGHT_T, canon, 'Capitalization', 0.93,
             'Days of the week take a capital letter.', f'The shop is closed on {plural} in winter.',
             f'The shop is closed on {canon} in winter. ' + neg_noise(plural), fam)
        emit(f'caps.date.{d}_possessive', f"{LEFT}(?P<target>(?-i:{d}))['’]s(?:\\s|[,.;:!?)]|$)", d.capitalize(), 'Capitalization', 0.93,
             'Days of the week take a capital letter.', f"See you at {d}'s meeting.",
             f"See you at {d.capitalize()}'s meeting. " + neg_noise(d), fam)
    # BC / BCE after a year, AD before one
    emit('caps.date.bc', r"\b\d{3,4}\s*(?P<target>(?-i:bc|Bc))\b(?:\s|[,.;:!?)]|$)", 'BC', 'Capitalization', 0.9,
         'BC and AD are written in capitals.', 'The temple was built in 450 bc by the river.',
         'The temple was built in 450 BC by the river. Please reply bc I am away.', 'Months, weekdays and dates')
    emit('caps.date.bce', r"\b\d{3,4}\s*(?P<target>(?-i:bce|Bce))\b(?:\s|[,.;:!?)]|$)", 'BCE', 'Capitalization', 0.9,
         'BCE is written in capitals.', 'The temple was built in 450 bce by the river.',
         'The temple was built in 450 BCE by the river.', 'Months, weekdays and dates')
    emit('caps.date.ad',
         r"(?i:\b(?:in|from|of|until|around|circa|by|since|before|after|year)\s+)(?P<target>(?-i:ad|Ad))\s+\d{3,4}\b",
         'AD', 'Capitalization', 0.9, 'BC and AD are written in capitals.', 'The abbey was founded in ad 800 by monks.',
         'The abbey was founded in AD 800 by monks. We ran an ad 300 times last week.', 'Months, weekdays and dates')


# ----------------------------------------------------------------------------------------------------------------
# Compass directions and school subjects: capitals the writer added by mistake. The target starts with the space (or
# the comma) before the word, so the engine does not put the capital back.
# ----------------------------------------------------------------------------------------------------------------

DIRECTIONS = ['North', 'South', 'East', 'West', 'Northeast', 'Northwest', 'Southeast', 'Southwest']
TRAVEL_VERBS = (r"head|heads|headed|heading|drive|drives|drove|driving|walk|walks|walked|walking|turn|turns|turned|"
                r"turning|fly|flies|flew|flying|sail|sailed|sailing|ride|rode|riding|continue|continued|continuing|bear|"
                r"bearing|cycle|cycled|cycling|hike|hiked|hiking|veer|veered|veering")
DIR_FOLLOW = (r"(?:\s+(?i:on|for|along|until|toward|towards|to|from|at|then|and|via|by|past|through|across|up|down|over|"
              r"about|a|an|the|onto|into|after|before)\b|\s*[,.;:!?)]|\s*$)")
DIST = (r"miles?|kilometers?|kilometres?|km|blocks?|meters?|metres?|feet|yards?|just|due|slightly|directly|far|further|"
        r"farther|located|lies|lying|sits|sitting|situated|is|are|was|were")


def build_directions():
    fam = 'Compass directions (lowercase)'
    for d in DIRECTIONS:
        lower = d.lower()
        emit(f'caps.dir.{lower}_travel',
             f"(?i:\\b(?:{TRAVEL_VERBS}))(?P<target>(?-i: {d})){DIR_FOLLOW}",
             f' {lower}', 'Capitalization', 0.87,
             'A compass direction is lowercase unless it names a region.',
             f'Then head {d} for two miles.',
             f'Then head {lower} for two miles. The South is warm, and the Pacific North is wet. '
             f'He moved to the South and loves the West.', fam)
        emit(f'caps.dir.{lower}_of',
             f"(?i:\\b(?:{DIST}))(?P<target>(?-i: {d})) of\\b",
             f' {lower}', 'Capitalization', 0.87,
             'A compass direction is lowercase unless it names a region.',
             f'The lake is two miles {d} of the town.',
             f'The lake is two miles {lower} of the town. The old South of the novel is gone.', fam)


SUBJECTS = ['Physics', 'Chemistry', 'Biology', 'Mathematics', 'Maths', 'Geography', 'History', 'Economics', 'Sociology',
            'Psychology', 'Philosophy', 'Literature', 'Astronomy', 'Geology', 'Anthropology', 'Linguistics', 'Algebra',
            'Calculus', 'Geometry', 'Trigonometry', 'Statistics', 'Biochemistry', 'Neuroscience', 'Zoology', 'Botany',
            'Archaeology', 'Theology', 'Accounting']
SUBJECT_VERBS = (r"studying|study|studies|studied|teach|teaches|teaching|taught|failed|passed|flunked|aced|hate|hates|"
                 r"love|loves|like|likes|enjoy|enjoys|good at|bad at|great at|terrible at|struggle with|struggled with|"
                 r"learn|learns|learning|learned|major in|majored in|majoring in|minor in|minored in")
SUBJECT_FOLLOW = (r"(?:\s*[,.;:!?)]|\s*$|\s+(?:and|or|but|at|in|for|with|to|from|on|since|because|so|as|by|last|next|"
                  r"this|every|each|during|before|after|until|when|while|if|than|too|also|again|now|today|tomorrow|"
                  r"yesterday|class|classes|course|courses|lesson|lessons|homework|exam|exams|test|tests|teacher|"
                  r"teachers|professor|professors|degree|major|minor|textbook|textbooks|lab|labs|all|every|really|"
                  r"more|better|well|instead)\b)")


def build_subjects():
    fam = 'School subjects (lowercase)'
    for s in SUBJECTS:
        lower = s.lower()
        emit(f'caps.subject.{lower}',
             f"(?i:\\b(?:{SUBJECT_VERBS}))(?P<target>(?-i: {s})){SUBJECT_FOLLOW}",
             f' {lower}', 'Style', 0.78,
             'A school subject is usually written in lowercase (only languages keep a capital).',
             f'We study {s} every day.',
             f'We study {lower} every day. She teaches {s} 101 and History of Art. '
             f'She also studied English and French.', fam)


# ----------------------------------------------------------------------------------------------------------------
# Stray capitals inside a sentence
# ----------------------------------------------------------------------------------------------------------------

GREETING = (r"(?i:hi|hello|hey|good morning|good afternoon|good evening|dear all|dear team|hi there|hello there|"
            r"hey there|hi all|hello all|hi everyone|hello everyone|hey everyone|hey guys|hi guys|hello guys|"
            r"hi team|hello team|hey team|hi folks|hello folks|dear sir|dear madam|dear sirs)")
AFTER_GREETING = ['How', 'What', 'Where', 'When', 'Why', 'Who', 'Can', 'Could', 'Would', 'Will', 'Do', 'Does', 'Did',
                  'Is', 'Are', 'Was', 'Were', 'Have', 'Has', 'Hope', 'Hoping', 'Just', 'Wanted', 'Wondering', 'Thanks',
                  'Please', 'Looking', 'Trying', 'Following', 'Checking', 'My', 'Our', 'We', 'You', 'Your', 'They',
                  'The', 'This', 'That', 'These', 'Those', 'It', 'There', 'Here', 'Sorry', 'Apologies', 'Quick',
                  'Thank', 'Welcome', 'Congratulations', 'Happy', 'Great', 'Good', 'Nice']
BAD_AFTER = {'Thank'}  # handled with "Thank You" below


GREETING_TAIL = {
    'How': 'are you doing this week?', 'What': 'time is the meeting?', 'Where': 'should we meet?',
    'When': 'can we talk?', 'Why': 'is the link broken?', 'Who': 'is joining us?', 'Can': 'you send the file?',
    'Could': 'you check this?', 'Would': 'you like to join?', 'Will': 'you be there?', 'Do': 'you have a minute?',
    'Does': 'tomorrow work for you?', 'Did': 'you see my message?', 'Is': 'the file ready?', 'Are': 'you free today?',
    'Was': 'the call recorded?', 'Were': 'you at the office?', 'Have': 'you seen the report?',
    'Has': 'the form arrived?', 'Hope': 'you are well.', 'Hoping': 'you can help.',
    'Just': 'checking in on the report.', 'Wanted': 'to confirm the time.', 'Wondering': 'if you can join.',
    'Thanks': 'for the quick reply.', 'Please': 'see the file attached.', 'Looking': 'forward to the call.',
    'Trying': 'to reach you.', 'Following': 'up on my last email.', 'Checking': 'in on the plan.',
    'My': 'name is Sam.', 'Our': 'team will join.', 'We': 'will join at noon.', 'You': 'are invited to the event.',
    'Your': 'order has shipped.', 'They': 'will join at noon.', 'The': 'meeting is at noon.',
    'This': 'is the final version.', 'That': 'works for me.', 'These': 'are the files.', 'Those': 'are due today.',
    'It': 'was good to meet you.', 'There': 'is a delay today.', 'Here': 'is the report.',
    'Sorry': 'for the late reply.', 'Apologies': 'for the delay.', 'Quick': 'question about the invoice.',
    'Welcome': 'to the team.', 'Congratulations': 'on the launch.', 'Happy': 'to help anytime.',
    'Great': 'to meet you.', 'Good': 'to hear from you.',
}


def build_stray():
    fam = 'Stray capitals mid-sentence'
    for w, tail in GREETING_TAIL.items():
        lower = w.lower()
        emit(f'caps.stray.after_greeting_{lower}',
             f"{LEFT}{GREETING}(?:\\s+(?-i:[A-Z][a-z]+))?(?P<target>(?-i:, {w}))\\s+(?-i:[a-z]+)\\b",
             f', {lower}', 'Capitalization', 0.9,
             'The sentence goes on after the comma, so the next word is lowercase.',
             f'Hi, {w} {tail}',
             f'Hi, {lower} {tail} Hi, I hope you are well. Hi, The Verge is here. '
             f'Hi John,\n{w} we start the meeting soon.', fam)
    emit('caps.stray.thank_you_after_comma',
         r"(?-i:[a-z])(?P<target>(?-i:, Thank You))\s+(?-i:[a-z]+)\b",
         ', thank you', 'Capitalization', 0.9, 'The sentence goes on after the comma, so “thank you” is lowercase.',
         'Hi John, Thank You for the quick reply.',
         'Hi John, thank you for the quick reply. Thank You Notes and Cards: Thank You for Smoking is a film.', fam)
    for w in ['But', 'Which', 'Because', 'Although', 'Though', 'Whereas', 'Unless', 'Since', 'So']:
        lower = w.lower()
        emit(f'caps.stray.comma_{lower}',
             f"(?-i:[a-z])(?P<target>(?-i:, {w}))\\s+(?-i:[a-z]+)\\b",
             f', {lower}', 'Capitalization', 0.88,
             'A word after a comma that continues the sentence is lowercase.',
             f'We tried the new route, {w} it was closed again today.',
             f'We tried the new route, {lower} it was closed again today. Fast, {w} Not Cheap is a title.', fam)
    for w in ['We', 'They', 'She']:
        lower = w.lower()
        emit(f'caps.stray.conj_{lower}',
             f"(?:^|[\\s(\\[])(?i:that|if|because|when|while|since|so|but|and|though|although|unless|until|as|whether|than)(?P<target>(?-i: {w}))\\s+(?-i:[a-z]+)\\b",
             f' {lower}', 'Capitalization', 0.88,
             'A pronoun inside a sentence is lowercase.',
             f'I think that {w} should leave early.',
             f'I think that {lower} should leave early. People Say That {w} Should Leave Early.', fam)
    # a quotation after a speech verb opens with a capital: He said, "we should go." -> "We should go."
    # Only when no quote came earlier in the sentence: '"I think," she said, "we should go."' continues one sentence.
    verbs = (r"said|asked|replied|answered|shouted|whispered|exclaimed|yelled|explained|announced|declared|responded|"
             r"remarked|murmured|muttered|cried|added|told me|told us|told him|told her|told them")
    words = {'a': ('all', 'of us agree'), 'b': ('both', 'of us agree'), 'c': ('come', 'with us tonight'),
             'd': ("don't", 'wait for me'), 'e': ('every', 'one of us agrees'), 'f': ('fine', 'let us begin'),
             'g': ('good', 'to see you'), 'h': ('here', 'is the plan'), 'j': ('just', 'wait a minute'),
             'k': ('keep', 'going until noon'), 'l': ("let's", 'go home now'), 'm': ('my', 'plan is simple'),
             'n': ('never', 'mind the rest'), 'o': ('our', 'plan is simple'), 'p': ('please', 'wait for me'),
             'q': ('quiet', 'down for now'), 'r': ('really', 'good to see you'), 's': ('sure', 'we can try'),
             't': ('thanks', 'for coming today'), 'u': ('until', 'we meet again'), 'v': ('very', 'good to see you'),
             'w': ('we', 'should go now'), 'y': ('you', 'should go now'), 'z': ('zero', 'chance of rain')}
    for letter, (word, rest) in words.items():
        up = letter.upper()
        cap = up + word[1:]
        emit(f'caps.stray.quote_{letter}',
             r'^[^"“”]*?(?i:\b(?:' + verbs + r')(?:,|:)\s+["“])(?P<target>(?-i:' + letter + r"))(?-i:[a-z'’]*)\b\s+(?-i:[a-z'’]+)",
             up, 'Capitalization', 0.86,
             'A quoted sentence starts with a capital letter.',
             f'She said, "{word} {rest}," and left.',
             f'She said, "{cap} {rest}," and left. He said "no way" and left. The sign said, "Please close the door." '
             f'They call it "well done" work. "I think," she said, "{word} {rest}."', fam)


# ----------------------------------------------------------------------------------------------------------------
# Planets, zodiac, history, organizations, universities
# ----------------------------------------------------------------------------------------------------------------

PLANETS = ['Jupiter', 'Saturn', 'Neptune', 'Uranus', 'Venus', 'Pluto', 'Milky Way', 'Halley\'s Comet']
ZODIAC = ['Aries', 'Taurus', 'Virgo', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces']
HISTORY = """American Civil War|Vietnam War|Korean War|Gulf War|Iraq War|Crimean War|Boer War|Napoleonic Wars|
Hundred Years' War|Wars of the Roses|Great Depression|Great Recession|Industrial Revolution|French Revolution|
American Revolution|Russian Revolution|Cultural Revolution|Middle Ages|Dark Ages|
Roman Empire|Ottoman Empire|British Empire|Byzantine Empire|Mughal Empire|Holy Roman Empire|Brexit|
Magna Carta|Berlin Wall|Iron Curtain|Silk Road|Black Death|
Boston Tea Party|Trail of Tears|Underground Railroad|Arab Spring|
Manhattan Project|Marshall Plan""".replace('\n', '').split('|')
ORGS = """World Health Organization|World Bank|Red Cross|Red Crescent|European Commission|European Parliament|
World Trade Organization|Federal Reserve|Security Council|Ivy League|Nobel Prize|Olympic Games|
Premier League|Champions League|La Liga|Serie A|Bundesliga|Tour de France|Formula One|Stanley Cup|
Wimbledon|Oscars|Grammy Awards|Booker Prize|Pulitzer Prize|Fields Medal|Turing Award|Peace Corps|
Doctors Without Borders|Amnesty International|Greenpeace|Habitat for Humanity|Boy Scouts|Girl Scouts|Rotary Club|
Lions Club|Supreme Court of India|Lok Sabha|Rajya Sabha|House of Commons|House of Lords|
Scotland Yard|Interpol|Europol|NASA|Hubble Telescope|Large Hadron Collider|Harvard|Stanford|Princeton|Cornell|
Berkeley|Caltech|Georgetown|Carnegie Mellon|Johns Hopkins|Yale University|Duke University|Columbia University|
Brown University|Oxford University|Cambridge University|Northwestern University|Purdue|Vanderbilt|Rutgers|Georgia Tech|
University of Oxford|University of Cambridge|London School of Economics|Sorbonne|
Delhi University|Jawaharlal Nehru University|Anna University|Mumbai University""".replace('\n', '').split('|')
ORGS = [o for o in ORGS if o not in {'NASA', 'Greenpeace', 'Interpol', 'Europol'}] + ['Greenpeace', 'Interpol']


def build_world():
    for p in PLANETS:
        phrase_rule(f'caps.world.{slug(p)}', p, LEFT, RIGHT, 0.9, 'Names of planets and celestial bodies take a capital letter.',
                    'We watched {x} rise over the hills last night.', 'Planets, zodiac, history, organizations', strict=True)
    for z in ZODIAC:
        phrase_rule(f'caps.world.zodiac_{slug(z)}', z, LEFT, RIGHT, 0.86, 'Zodiac signs take a capital letter.',
                    'She says she is a {x} through and through.', 'Planets, zodiac, history, organizations')
    for h in dict.fromkeys(HISTORY):
        phrase_rule(f'caps.world.{slug(h)}', h, LEFT, RIGHT_H, 0.9,
                    'Historical events, periods and documents take capitals.',
                    'The teacher covered the {x} in class on Tuesday.', 'Planets, zodiac, history, organizations', strict=True)
    for o in dict.fromkeys(ORGS):
        phrase_rule(f'caps.world.{slug(o)}', o, LEFT, RIGHT_H, 0.9,
                    'Names of organizations, institutions and awards take capitals.',
                    'She works with the {x} on a new project.', 'Planets, zodiac, history, organizations', strict=True)
    # World War II, World War 2 (the digit is protected, so only the words are edited)
    emit('caps.world.world_war',
         f"{LEFT}(?P<target>(?-i:world war|World war|world War))\\s+(?:II|ii|2|Two|two|One|one|1|III|3|iii)\\b",
         'World War', 'Capitalization', 0.9, 'Historical events and wars take capitals.',
         'My grandfather served in world war II as a pilot.',
         'My grandfather served in World War II as a pilot. The world was at war in 1914, a word war of letters.',
         'Planets, zodiac, history, organizations')


FAMILY = ['mom', 'dad', 'mum', 'mommy', 'daddy', 'mama', 'papa', 'grandma', 'grandpa', 'granny']
FAMILY_VERBS = (r"told|tell|tells|asked|ask|asks|called|call|calls|thank|thanks|thanked|love|loves|miss|misses|missed|"
                r"hug|hugged|kissed|texted|texts|visited|visit|visits|saw|see|sees|met|meet|helped|help|helps|ask|"
                r"hi|hello|hey|dear|bye|goodbye|congratulate|congratulated|surprised|surprise|obey|obeyed|listen to|"
                r"listened to|talk to|talked to|talking to|speak to|spoke to|speaking to|write to|wrote to|writing to")
FAMILY_FOLLOW = (r"(?:\s*[,.;:!?)]|\s*$|\s+(?:about|to|for|if|that|when|what|where|why|how|and|or|but|because|so|"
                 r"yesterday|today|tomorrow|tonight|again|first|later|too|at|in|on|with|from|before|after|now|then)\b)")


def build_family():
    fam = 'Family names used as names'
    for w in FAMILY:
        canon = w.capitalize()
        emit(f'caps.family.{w}',
             f"(?i:\\b(?:{FAMILY_VERBS})\\s+)(?P<target>(?-i:{w})){FAMILY_FOLLOW}",
             canon, 'Capitalization', 0.85,
             'A family word used as a name takes a capital letter.',
             f'I called {w} yesterday to say thanks.',
             f'I called {canon} yesterday to say thanks. I told my {w} about it, and we told {w} jokes at dinner.', fam)


def build_misc():
    fam = 'Units, abbreviations and devices'
    for lower, canon in [('celsius', 'Celsius'), ('fahrenheit', 'Fahrenheit')]:
        emit(f'caps.unit.{lower}', f"{LEFT}(?P<target>(?-i:{lower}|{canon.upper()}))" + RIGHT, canon, 'Capitalization', 0.92,
             f'{canon} is named after a person and takes a capital letter.',
             f'It was thirty degrees {lower} at noon.', f'It was thirty degrees {canon} at noon. ' + neg_noise(lower), fam)
    for lower, canon in [('q&a', 'Q&A'), ('r&d', 'R&D')]:
        alts = [lower, lower.capitalize(), lower[0] + lower[1] + lower[2:].upper() if False else lower[0].lower() + '&' + lower[2].upper()]
        alts = list(dict.fromkeys(alts))
        body = '|'.join(esc(a) for a in alts if a != canon)
        emit(f'caps.unit.{slug(lower)}', f"{LEFT}(?P<target>(?-i:{body})){RIGHT_T}", canon, 'Capitalization', 0.9,
             'This abbreviation is written in capitals.', f'We held a {lower} session after the talk.',
             f'We held a {canon} session after the talk. ' + neg_noise(lower), fam)
    model = r"(?:iPhone|iphone)\s+\d{1,2}[a-z]?\s+"
    phrase_rule('caps.device.iphone_pro_max', 'Pro Max', model, RIGHT, 0.88, 'Apple spells its model names with capitals.',
                'My iPhone 15 {x} has a great camera.', fam)
    for lower, canon in [('pro', 'Pro'), ('plus', 'Plus')]:
        phrase_rule(f'caps.device.iphone_{lower}', canon, model, RIGHT, 0.88, 'Apple spells its model names with capitals.',
                    'My iPhone 15 {x} has a great camera.', fam)
    emit('caps.device.iphone_se', r"(?:iPhone|iphone)\s+(?P<target>(?-i:se|Se))" + RIGHT_T, 'SE', 'Capitalization', 0.88,
         'Apple spells its model names with capitals.', 'My iPhone se has a great camera.',
         'My iPhone SE has a great camera. The iPhone seemed fine.', fam)
    for lower, canon in [('pro', 'Pro'), ('air', 'Air')]:
        emit(f'caps.device.ipad_{lower}', r"(?:iPad|ipad)\s+(?P<target>(?-i:" + lower + r"))" + RIGHT_T, canon, 'Capitalization', 0.88,
             'Apple spells its model names with capitals.', f'My iPad {lower} has a great screen.',
             f'My iPad {canon} has a great screen. The iPad pro-level pen was fine.', fam)


def build():
    build_family()
    build_misc()
    build_dates()
    build_directions()
    build_subjects()
    build_stray()
    build_world()
