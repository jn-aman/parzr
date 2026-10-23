"""Other tense and aspect constructions."""
import json
from core import *
from lex import *
from verbs import ALL_ROWS

BV = '|'.join(BASE_VERBS)


def rather_better():
    rule("tense.would_rather.to",
         rf"(?i)\b(?:would|['’]d) rather(?: not)? (?P<target>to )(?:{BV})\b",
         "", "After “would rather” the verb comes without “to”: “I would rather stay”.",
         "I would rather to stay home tonight.", "I would rather stay home tonight. I want to stay home. She walked rather to the left.",
         right="I would rather stay home tonight.", category='Verb form', confidence=0.94,
         more_pos=[("We'd rather not to go.", "We'd rather not go.")])
    rule("tense.had_better.to",
         rf"(?i)\b(?:had|['’]d) better(?: not)? (?P<target>to )(?:{BV})\b",
         "", "After “had better” the verb comes without “to”: “you had better go”.",
         "You had better to hurry.", "You had better hurry. It is better to hurry.",
         right="You had better hurry.", category='Verb form', confidence=0.94,
         more_pos=[("I'd better not to wait.", "I'd better not wait.")])
    hb = 'go|get|leave|hurry|stop|ask|tell|see|be|wait|listen|move|finish|check|call|stay|think|watch|start|do|make|take|let|come|try|keep|know|remember|run'
    rule("tense.had_better.have",
         rf"(?i)\b(?:I|you|we|they|he|she) (?P<target>have|has|would|will|should) better(?: not)? (?:{hb}){END}",
         "had", "The idiom is “had better”: “you had better go”.",
         "You have better go now.", "You had better go now. They have better odds this year. She has better check-in times.",
         right="You had better go now.", category='Verb form', confidence=0.92,
         more_pos=[("We would better leave early.", "We had better leave early.")])


def lets():
    verbs = ("get start try see talk meet do take make have keep check move begin find just not be all continue look "
             "discuss figure hope stop finish wrap work plan focus use review call sync schedule set put give think say "
             "hear send add remember assume agree ensure eat play celebrate grab jump hit run walk head leave wait dive "
             "break build")
    V = '|'.join(verbs.split())
    # sentence start with a marker, or after a comma / and: "lets" + verb without an object is a suggestion
    rule("tense.lets.suggestion",
         rf"(?im)(?:^|[.!?] |, |\b(?:ok|okay|so|well|now|alright|then|hey|oh|yeah|please|and|but|or) )(?P<target>lets) (?:{V})\b",
         "let's", "A suggestion to do something together is “let’s”: “let’s get started”.",
         "Okay, lets get started.", "Okay, let's get started. She lets the dog out. He lets go of the rope.",
         right="Okay, let's get started.", category='Grammar', confidence=0.92,
         more_pos=[("We should hurry, lets start now.", "We should hurry, let's start now."),
                   ("So lets check the list.", "So let's check the list.")])
    rule("tense.lets.go",
         rf"(?im)(?:^|[.!?] |\b(?:ok|okay|so|well|now|alright|hey|oh|yeah|please) )(?P<target>lets) go (?:to|for|out|home|back|there|now|ahead|on|get|see|eat|grab)\b",
         "let's", "A suggestion to do something together is “let’s”: “let’s go”.",
         "Okay lets go to the park.", "Okay let's go to the park. She lets go of the rope.",
         right="Okay let's go to the park.", category='Grammar', confidence=0.92,
         more_pos=[("Lets go home now.", "Let's go home now.")])
    rule("tense.lets.third_person",
         rf"(?i)\b(?:he|she|it|who|which|that|this|nobody|nothing) (?P<target>let['’]s) (?:me|us|you|him|her|them|it|users|people|the|a|an|my|your|our)\b",
         "lets", "With “he”, “she” or “it” the verb is “lets”, without an apostrophe.",
         "She let's me use her car.", "She lets me use her car. Let's use her car.",
         right="She lets me use her car.", category='Grammar', confidence=0.93,
         more_pos=[("That let's us know the answer.", "That lets us know the answer."),
                   ("It let's you see the results.", "It lets you see the results.")])


def supposed_used():
    be = (r"(?:am|is|are|was|were|be|been|being|['’]m|['’]re|isn['’]t|aren['’]t|wasn['’]t|weren['’]t|am not|is not|"
          r"are not|was not|were not|ain['’]t)")
    rule("tense.supposed_to.be",
         rf"(?i)\b{be} (?P<target>suppose) to\b",
         "supposed", "The phrase is “supposed to”, with a “d”.",
         "I'm suppose to call him at nine.", "I'm supposed to call him at nine. I suppose to call him is fine. Do you suppose it will rain?",
         right="I'm supposed to call him at nine.", category='Verb form', confidence=0.95,
         more_pos=[("You are suppose to be there.", "You are supposed to be there."),
                   ("He was not suppose to leave.", "He was not supposed to leave.")])
    rule("tense.supposed_to.question",
         rf"(?i)\b(?:am|is|are|was|were) (?:I|you|he|she|it|we|they) (?P<target>suppose) to\b",
         "supposed", "The phrase is “supposed to”, with a “d”.",
         "What am I suppose to do?", "What am I supposed to do?", right="What am I supposed to do?",
         category='Verb form', confidence=0.95)
    rule("tense.used_to.be_use",
         rf"(?i)\b(?:am|is|are|was|were|be|been|get|gets|got|getting|become|becomes|became|['’]m|['’]re|grow|grew) (?P<target>use) to\b",
         "used", "The phrase is “used to”, with a “d”: “I am used to it”.",
         "I am use to waking up early.", "I am used to waking up early. We use it to wake up early.",
         right="I am used to waking up early.", category='Verb form', confidence=0.95,
         more_pos=[("She got use to the cold.", "She got used to the cold."),
                   ("It takes time to get use to this.", "It takes time to get used to this.")])
    rule("tense.used_to.adverb",
         rf"(?i)\b(?:I|we|you|they|he|she|it|who) (?:always|never|often|really|also|just|all|usually|both|still) (?P<target>use) to (?:be|live|go|work|play|have|think|say|do|get|see|eat|come|take|make|visit|drive|walk|ride|meet|love|hate|like|smoke|drink|sleep|wake|run|swim|sing|dance|talk|speak|read|write|study|teach|own|wear|call|help|ask|know|watch|cook|buy|sell|send|stay|travel|fight|cry|laugh|argue|sit|stand)\b",
         "used", "A past habit is “used to”, with a “d”.",
         "We always use to go there.", "We always used to go there. We always use them to go there.",
         right="We always used to go there.", category='Verb form', confidence=0.94,
         more_pos=[("I really use to love it.", "I really used to love it.")])
    # "get used to wake up" -> "get used to waking up"
    for b in ("wake get work live eat drive sleep study stay deal cook walk wear speak take be see hear do go "
              "travel play read write run swim talk").split():
        g = ing(b)
        pat = (rf"(?i)\b(?:(?:I|we|you|they|he|she) (?:get|gets|got|getting|become|becomes|became|becoming|grew|grow)|"
               rf"I am|I['’]m) used to (?P<target>{b}){END}")
        rule(f"tense.used_to.gerund.{b}", pat, g,
             f"After “get used to” and “be used to” (meaning “accustomed to”) the verb takes “-ing”: “{g}”.",
             f"I got used to {b} early.", f"I got used to {g} early. We used to {b} early. They are used to {b} early.",
             right=f"I got used to {g} early.", category='Verb form', confidence=0.9,
             more_pos=[(f"I am used to {b} early.", f"I am used to {g} early.")])


BE_FOLLOW = (rf"(?:{DETOBJ[3:-1]}|you|to|in|at|on|for|with|from|by|about|up|out|back|home|there|here|now|today|hard|well|"
             r"very|too|so|a lot|more|much|again|together|outside|inside|abroad|online|English|Hindi|football|cricket|"
             r"games?|TV|music|lunch|dinner|breakfast|food|coffee|tea|water|school|college|work|office|class|bed|sleep|"
             r"late|early|fast|slowly|quickly|alone|tomorrow|tonight)")
BE_VERBS = ("go work study play eat watch wait sleep talk walk listen look try live stay send buy learn make take give "
            "ask meet speak pay sing dance prepare finish start think write drink do help teach build call").split()
BE_TAILS = {'go': 'to the market', 'work': 'in a bank', 'study': 'English', 'play': 'football', 'eat': 'lunch',
            'watch': 'TV', 'wait': 'for you', 'sleep': 'now', 'talk': 'to him', 'walk': 'to school',
            'listen': 'to music', 'look': 'for a job', 'try': 'to help', 'live': 'in Delhi', 'stay': 'at home',
            'send': 'you the file', 'buy': 'a new phone', 'learn': 'English', 'make': 'dinner', 'take': 'a break',
            'give': 'him the keys', 'ask': 'him about it', 'meet': 'my friends', 'speak': 'to her',
            'pay': 'the bill', 'sing': 'a song', 'dance': 'with her', 'prepare': 'the report', 'finish': 'my work',
            'start': 'a new job', 'think': 'about it', 'write': 'an email', 'drink': 'tea', 'do': 'my homework',
            'help': 'my brother', 'teach': 'English', 'build': 'a house', 'call': 'you now'}


def be_base():
    # no "you're" forms: "I need you're help" is a slip for "your help", not a missing "-ing"
    subj = (r"(?:(?:I|we|you|they) (?:am|are)|(?:he|she) is|I['’]m|"
            r"(?:I|we|you|they) (?:was|were)|(?:he|she) was)")
    for b in BE_VERBS:
        g = ing(b)
        fol = BE_TAILS[b]
        pat = rf"(?i)\b{subj}(?: not)? (?P<target>{b}) {BE_FOLLOW}{END}"
        pos = f"I am {b} {fol}."
        right = f"I am {g} {fol}."
        if not re.search(pat, pos):
            PROBLEMS.append(f"be_base.{b}: example does not match"); continue
        rule(f"tense.be_base.{b}", pat, g,
             f"After “am”, “is” or “are” an action in progress takes “-ing”: “{g}”.",
             pos, f"{right} The best plan is {b} {fol}.", right=right, category='Verb form', confidence=0.95,
             more_pos=[(f"She is not {b} {fol}.", f"She is not {g} {fol}."),
                       (f"They were {b} {fol}.", f"They were {g} {fol}.")])


AUXADV = "already|just|never|ever|also|still|always|not|only|really"


def been_being():
    rule("tense.been.being_after_have",
         rf"(?i)\b(?:have|has|had|having|['’]ve)(?: (?:{AUXADV}))? (?P<target>being) (?:a|an|the|very|so|too|really|quite|there|here|[a-z]+ing|[a-z]+ed)\b",
         "been", "After “have”, “has” or “had” the form is “been”, not “being”.",
         "The meeting has being cancelled.", "The meeting has been cancelled. A human being has rights. They are being kind.",
         right="The meeting has been cancelled.", category='Verb form', confidence=0.95,
         more_pos=[("I have being working here for years.", "I have been working here for years.")])
    rule("tense.been.am_been",
         rf"(?i)\b(?:I|you|we|they) (?P<target>am|are) been\b", "have",
         "Use “have been”: “I have been here”.",
         "I am been here since morning.", "I have been here since morning. I am here now.",
         right="I have been here since morning.", category='Verb form', confidence=0.94,
         more_pos=[("You are been late again.", "You have been late again.")])
    rule("tense.been.is_been",
         rf"(?i)\b(?:he|she|it) (?P<target>is) been\b", "has",
         "Use “has been”: “she has been here”.",
         "She is been here since morning.", "She has been here since morning. She is here now.",
         right="She has been here since morning.", category='Verb form', confidence=0.94)
    rule("tense.been.was_been",
         rf"(?i)\b(?:I|you|we|they|he|she|it) (?P<target>was|were) been\b", "had",
         "Use “had been”: “I had been waiting”.",
         "I was been waiting for an hour.", "I had been waiting for an hour. I was waiting for an hour.",
         right="I had been waiting for an hour.", category='Verb form', confidence=0.93)
    rule("tense.been.contraction",
         rf"(?i)\b(?:I|you|we|they)(?P<target>['’]m|['’]re) been\b", "'ve",
         "Use “have been”: “I’ve been here”.",
         "I'm been waiting for an hour.", "I've been waiting for an hour. I'm waiting for an hour.",
         right="I've been waiting for an hour.", category='Verb form', confidence=0.94,
         more_pos=[("You're been working hard.", "You've been working hard.")])
    aux = r"(?:have|has|had|['’]ve)"
    rule("tense.been.have_be_progressive",
         rf"(?i)\b(?:{aux} |{aux} (?:{AUXADV}) )(?P<target>be) [a-z]{{3,}}ing\b",
         "been", "After “have”, “has” or “had” the form is “been”: “I have been working”.",
         "I have be working here for years.", "I have been working here for years. I will be working here for years.",
         right="I have been working here for years.", category='Verb form', confidence=0.93,
         more_pos=[("She would have be waiting there.", "She would have been waiting there."),
                   ("They have never be working late.", "They have never been working late.")])
    # have + -ing without "been"
    ing_follow = {
        'working': (r"here|there|since|hard|as|at|in|on|with|together|late|overtime", "I have working here since 2015.", "I have been working here since 2015."),
        'living': (r"here|there|in|at|with|since|alone|abroad|together", "We have living here since 2010.", "We have been living here since 2010."),
        'waiting': (r"for|here|there|since|outside|inside|long", "I have waiting for you since morning.", "I have been waiting for you since morning."),
        'studying': (r"here|there|in|at|since|hard|abroad|together|English", "She has studying here since 2020.", "She has been studying here since 2020."),
        'staying': (r"here|there|in|at|with|since|abroad|together", "They have staying here since June.", "They have been staying here since June."),
        'trying': (r"to|hard|again|since", "I have trying to fix it since morning.", "I have been trying to fix it since morning."),
        'looking': (r"for|at|forward|after|into|since", "We have looking for a solution since Monday.", "We have been looking for a solution since Monday."),
        'teaching': (r"here|there|at|in|since", "He has teaching here since 2012.", "He has been teaching here since 2012."),
        'learning': (r"English|to|since|here|there|about", "I have learning English since 2020.", "I have been learning English since 2020."),
        'playing': (r"here|there|since|with|for|in|at", "They have playing since 2018.", "They have been playing since 2018."),
    }
    for g, (follow, wrong, right) in ing_follow.items():
        pat = rf"(?i)\b(?:I|you|we|they|he|she)(?: (?:{ADV_WORDS}))? (?P<target>(?P<a>have|has|had)) {g} (?:{follow})\b"
        rule(f"tense.been.have_ing.{g}", pat, "${a} been",
             "A situation that began earlier and continues takes “have been …ing”: “I have been waiting”.",
             wrong, right, right=right, category='Verb form', confidence=0.93)


def stative():
    obj = ("question|questions|query|queries|doubt|doubts|opinion|opinions|suggestion|suggestions|pen|pencil|phone|mobile|"
           "laptop|bike|scooter|bag|sister|sisters|brother|brothers|son|daughter|wife|husband|child|children|kid|kids|"
           "dog|cat|pet|house|flat|farm|shop|business|car|cars|degree|license|licence|passport|account|ticket|tickets|"
           "knowledge|experience|interest|information|details")
    rule("tense.stative.having_question",
         rf"(?im)(?:^|[.!?,;] |\b(?:and|but|so) )(?P<target>(?P<s>I|we|they|you) (?:am|are|['’]m|['’]re) having) (?:a|an|one|two|three|four|five|no|many|some) (?:{obj})\b",
         "${s} have", "Having something is a state, so it is not used with “-ing”: “I have a question”.",
         "I am having a question about the invoice.", "I have a question about the invoice. I am having a meeting about the invoice.",
         right="I have a question about the invoice.", category='Verb form', confidence=0.92,
         more_pos=[("We are having two brothers.", "We have two brothers.")])
    rule("tense.stative.having_question_3sg",
         rf"(?im)(?:^|[.!?,;] |\b(?:and|but|so) )(?P<target>(?P<s>he|she) (?:is|['’]s) having) (?:a|an|one|two|three|four|five|no|many|some) (?:{obj})\b",
         "${s} has", "Having something is a state, so it is not used with “-ing”: “she has a question”.",
         "She is having a question about the invoice.", "She has a question about the invoice. She is having a meeting about the invoice.",
         right="She has a question about the invoice.", category='Verb form', confidence=0.92)
    for gerund, base, wrong, right in (("understanding", "understand", "I am understanding your point.", "I understand your point."),
                                       ("liking", "like", "I am liking this song.", "I like this song.")):
        rule(f"tense.stative.{base}",
             rf"(?im)(?:^|[.!?,;] |\b(?:and|but|so) )(?P<target>(?P<s>I|we|they|you) (?:am|are|['’]m|['’]re) {gerund})\b",
             "${s} " + base, f"“{base.capitalize()}” names a state, so most writers use the simple present: “I {base} …”.",
             wrong, right + " She is understanding more each day." if base == 'understand' else right + " She is liking the song more each day.",
             right=right, category='Register', confidence=0.7)


def intransitive_passive():
    verbs = "happened occurred arrived died existed emerged resulted vanished appeared remained came went fell".split()
    perfect_ok = set("happened occurred arrived died existed emerged resulted vanished appeared remained".split())
    # "a decision was arrived at" is a real prepositional passive, so "arrived" is only matched before other words
    follow = {'arrived': r"(?:[.,;:!?)\]\"”]|$| (?:in|on|from|to|late|early|there|here|yesterday|today|last|after|before|safely|home)\b| at (?:[0-9]|noon|midnight|dawn|night|home|the (?:airport|station|hotel|office|venue|gate)\b))"}
    for v in verbs:
        subj = "The accident" if v in perfect_ok else "The news"
        more = [(f"It has been {v}.", f"It has {v}.")] if v in perfect_ok and v != 'arrived' else []
        end = follow.get(v, END)
        rule(f"tense.intransitive_passive.{v}",
             rf"(?i)\b(?P<target>(?:was|were|been) ){v}{end}", "",
             f"{Q(v)} has no passive: say “it {v}” without “was” or “been”.",
             f"{subj} was {v} last night.",
             f"{subj} {v} last night." + (f" Something has {v} again." if v in perfect_ok else ""),
             right=f"{subj} {v} last night.", category='Verb form', confidence=0.93, more_pos=more,
             more_neg=(["A 16-point agreement was arrived at after long talks."] if v == 'arrived' else []))


def modal_to():
    verbs = '|'.join(BASE_VERBS)
    for mod in ("will", "would", "shall", "should", "must", "may", "might"):
        ex = f"He {mod} to go home early."
        rule(f"tense.modal_to.{mod}",
             rf"(?i)\b(?:I|we|you|they|he|she|it)(?: (?:also|never|always|still|just|really|even))? (?-i:{mod}) (?P<target>to )(?:{verbs})\b",
             "", f"“{mod.capitalize()}” is followed by the bare verb, without “to”.",
             ex, f"He {mod} go home early. He wants to go home early.",
             right=f"He {mod} go home early.", category='Verb form', confidence=0.94)
    rule("tense.modal_to.negative",
         rf"(?i)\b(?:can['’]t|cannot|couldn['’]t|won['’]t|wouldn['’]t|shouldn['’]t|mustn['’]t) (?P<target>to )(?:{verbs})\b",
         "", "A modal verb is followed by the bare verb, without “to”.",
         "I can't to find the file.", "I can't find the file. I want to find the file.",
         right="I can't find the file.", category='Verb form', confidence=0.94,
         more_pos=[("She couldn't to come.", "She couldn't come.")])
    for mod in ("will", "shall", "would", "should", "must"):
        rule(f"tense.modal_can.{mod}",
             rf"(?i)\b(?:I|we|you|they|he|she|it) (?-i:{mod}) (?P<target>can) (?:{verbs})\b",
             "be able to", f"“{mod.capitalize()}” cannot be followed by “can”: use “be able to”.",
             f"I {mod} can help you tomorrow.", f"I {mod} be able to help you tomorrow. I can help you tomorrow.",
             right=f"I {mod} be able to help you tomorrow.", category='Verb form', confidence=0.93)
    for aux, rep, ex, ok in (("didn['’]t", "couldn't", "I didn't can find the file.", "I couldn't find the file."),
                             ("did not", "could not", "She did not can open it.", "She could not open it."),
                             ("don['’]t", "can't", "I don't can open it.", "I can't open it."),
                             ("doesn['’]t", "can't", "He doesn't can swim.", "He can't swim."),
                             ("do not", "cannot", "We do not can attend.", "We cannot attend."),
                             ("does not", "cannot", "She does not can attend.", "She cannot attend.")):
        key = re.sub(r"[^a-z]", "", aux.replace("['’]", ""))
        rule(f"tense.negative_can.{key}",
             rf"(?i)\b(?:I|we|you|they|he|she|it) (?P<target>{aux} can) (?:{verbs})\b",
             rep, f"“Can” already carries the tense and the negative: use “{rep}”.",
             ex, f"{ok} They can the tomatoes every year.",
             right=ok, category='Verb form', confidence=0.93)
    rule("tense.am_verb.delete",
         rf"(?i)\b(?:I|we|you|they)(?P<target> am| are|['’]m) (?:want|need|hope|know|believe|understand|prefer|remember|agree|disagree|wish|expect) (?:to|the|a|an|that|you|it|this|my|your|his|her|them|him|us|about|what|how|why|when|where|more|so|very|with|in|on)\b",
         "", "This verb does not take “am” or “are”: say “I want …” on its own.",
         "I am want to go home.", "I want to go home. I am wanting to go home soon.",
         right="I want to go home.", category='Verb form', confidence=0.93,
         more_pos=[("We are need your help.", "We need your help."), ("I am hope you are fine.", "I hope you are fine."),
                   ("I'm agree with you.", "I agree with you.")])
    rule("tense.am_verb.not",
         rf"(?i)\b(?:I|we|you|they) (?P<target>(?:am|are) not) (?:agree|want|need|know|understand|believe|remember)\b",
         "do not", "Use “do not” before this verb, not “am not”: “I do not agree”.",
         "I am not agree with you.", "I do not agree with you. I am not sure.",
         right="I do not agree with you.", category='Verb form', confidence=0.93,
         more_pos=[("They are not want to leave.", "They do not want to leave.")])
    rule("tense.am_verb.not_3sg",
         rf"(?i)\b(?:he|she) (?P<target>is not|isn['’]t) (?:agree|want|need|know|understand|believe|remember)\b",
         "does not", "Use “does not” before this verb, not “is not”: “she does not agree”.",
         "She is not agree with us.", "She does not agree with us. She is not sure.",
         right="She does not agree with us.", category='Verb form', confidence=0.93)
    rule("tense.am_verb.contraction",
         rf"(?i)\b(?P<target>I['’]m not) (?:agree|want|need|know|understand|believe|remember)\b",
         "I do not", "Use “do not” before this verb, not “am not”: “I do not agree”.",
         "I'm not agree with that.", "I do not agree with that. I'm not sure about that.",
         right="I do not agree with that.", category='Verb form', confidence=0.93)
