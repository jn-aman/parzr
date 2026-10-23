"""since / for, how long, perfect with a past-time marker."""
import json, os
from core import *
from lex import *
from verbs import ALL_ROWS

MONTHS = "january|february|march|april|may|june|july|august|september|october|november|december"
DAYS = "monday|tuesday|wednesday|thursday|friday|saturday|sunday"
POINT = (rf"(?:(?:19|20)\d\d|\d{{1,2}}(?::\d\d)?\s*(?:am|pm|a\.m\.|p\.m\.)|yesterday|last (?:night|week|weekend|month|year|"
         rf"summer|winter|spring|autumn|{DAYS}|{MONTHS})|this morning|morning|noon|midnight|childhood|birth|"
         rf"{DAYS}|(?:{MONTHS})(?: (?:19|20)\d\d)?)")
POINT_END = r"(?:\s*[.,;:!?)]|\s*$| (?:and|but|so|now|also)\b)"
# what may stand between a present-tense verb and "since": an object, an adverb or a short phrase, never a clause
SWIN = (r"(?:(?:him|her|them|me|us|you|it|this|each other|one another|here|there|together|abroad|alone|nearby|"
        r"(?:in|at|on|for|with|as|from) (?:(?:a|an|the|my|our|his|her|their) )?[A-Za-z]+(?: [A-Z][a-z]+)?|"
        r"(?:a|an|the|my|our|his|her|their|this|that) [A-Za-z]+) )?")
SINCE_VERBS = [  # base, 3sg, participle, example tail
    ('know', 'knows', 'known', 'him'), ('live', 'lives', 'lived', 'here'), ('work', 'works', 'worked', 'here'),
    ('study', 'studies', 'studied', 'here'), ('stay', 'stays', 'stayed', 'here'), ('own', 'owns', 'owned', 'this house'),
    ('use', 'uses', 'used', 'this phone'), ('teach', 'teaches', 'taught', 'here'), ('play', 'plays', 'played', 'cricket'),
    ('love', 'loves', 'loved', 'her'), ('want', 'wants', 'wanted', 'this job'), ('need', 'needs', 'needed', 'help'),
    ('like', 'likes', 'liked', 'him'), ('hold', 'holds', 'held', 'this post'),
    ('serve', 'serves', 'served', 'here'), ('belong', 'belongs', 'belonged', 'here'), ('hate', 'hates', 'hated', 'him'),
    ('miss', 'misses', 'missed', 'her'), ('trust', 'trusts', 'trusted', 'him'), ('support', 'supports', 'supported', 'them'),
    ('manage', 'manages', 'managed', 'this team'), ('maintain', 'maintains', 'maintained', 'this site'),
    ('write', 'writes', 'written', 'this blog'), ('read', 'reads', 'read', 'this blog'), ('keep', 'keeps', 'kept', 'this diary'),
    ('wear', 'wears', 'worn', 'glasses'), ('drive', 'drives', 'driven', 'this car'), ('sell', 'sells', 'sold', 'shoes'),
    ('speak', 'speaks', 'spoken', 'Hindi'), ('train', 'trains', 'trained', 'here'), ('run', 'runs', 'run', 'this shop'),
    ('lead', 'leads', 'led', 'this team'), ('host', 'hosts', 'hosted', 'this show'), ('collect', 'collects', 'collected', 'stamps'),
    ('follow', 'follows', 'followed', 'her'), ('practice', 'practices', 'practiced', 'yoga'), ('coach', 'coaches', 'coached', 'them'),
    ('volunteer', 'volunteers', 'volunteered', 'here'), ('wait', 'waits', 'waited', 'here'), ('sit', 'sits', 'sat', 'here'),
    ('stand', 'stands', 'stood', 'here'), ('smoke', 'smokes', 'smoked', 'here'), ('drink', 'drinks', 'drunk', 'tea'),
    ('suffer', 'suffers', 'suffered', 'here'),
]


def since_present():
    """I know him since 2010 -> I have known him since 2010."""
    for b, t, p, tail in SINCE_VERBS:
        for sj, aux, vb, ex_s in (('I|we|you|they', 'have', b, 'I'), ('he|she', 'has', t, 'She')):
            rep = f'{aux} {p}'
            pat = rf"(?i)\b(?:{sj}) (?P<target>{vb}) {SWIN}since\s+{POINT}{POINT_END}"
            tail_ok = tail
            pos = f"{ex_s} {vb} {tail_ok} since 2010."
            if not re.search(pat, pos):
                pos = f"{ex_s} {vb} since 2010."
                tail_ok = ''
            right = pos.replace(f" {vb}", f" {rep}", 1)
            if tail_ok:
                neg = f"{right} I think that since 2010 we {b} {tail_ok}. {ex_s} {rep} {tail_ok}."
            else:
                neg = f"{right} I think that since 2010 we {b}."
            rule(f"tense.since_present.{b}.{'plural' if aux == 'have' else '3sg'}", pat, rep,
                 f"A situation that began in the past and continues takes the present perfect with “since”: “{rep}”.",
                 pos, neg, right=right, category='Tense', confidence=0.92)
    state = (r"(?:not )?(?:here|there|sick|ill|absent|busy|unwell|ready|free|married|closed|offline|online|down|"
             r"in [A-Z][a-z]+|at [A-Z][a-z]+|on leave)")
    rule("tense.since_present.be.plural",
         rf"(?i)\b(?:I|we|you|they) (?P<target>am|are) {state} since {POINT}{POINT_END}",
         "have been", "A state that began in the past and continues takes the present perfect with “since”: “have been”.",
         "I am here since morning.", "I have been here since morning. I am here now.",
         right="I have been here since morning.", category='Tense', confidence=0.92,
         more_pos=[("We are in Pune since 2019.", "We have been in Pune since 2019.")])
    rule("tense.since_present.be.3sg",
         rf"(?i)\b(?:he|she|it) (?P<target>is) {state} since {POINT}{POINT_END}",
         "has been", "A state that began in the past and continues takes the present perfect with “since”: “has been”.",
         "She is sick since yesterday.", "She has been sick since yesterday. She is sick today.",
         right="She has been sick since yesterday.", category='Tense', confidence=0.92,
         more_pos=[("He is absent since Monday.", "He has been absent since Monday.")])
    rule("tense.since_present.be.contracted_I",
         rf"(?i)\b(?P<target>I['’]m) {state} since {POINT}{POINT_END}",
         "I've been", "A state that began in the past and continues takes the present perfect with “since”: “I’ve been”.",
         "I'm here since morning.", "I've been here since morning. I'm here now.",
         right="I've been here since morning.", category='Tense', confidence=0.92)
    rule("tense.since_present.be.contracted_plural",
         rf"(?i)\b(?P<target>(?P<s>we|you|they)['’]re) {state} since {POINT}{POINT_END}",
         "${s}'ve been", "A state that began in the past and continues takes the present perfect with “since”: “we’ve been”.",
         "We're in Pune since 2019.", "We've been in Pune since 2019. We're in Pune now.",
         right="We've been in Pune since 2019.", category='Tense', confidence=0.92)
    rule("tense.since_present.be.contracted_3sg",
         rf"(?i)\b(?P<target>(?P<s>he|she|it)['’]s) {state} since {POINT}{POINT_END}",
         "${s}'s been", "A state that began in the past and continues takes the present perfect with “since”: “she’s been”.",
         "She's sick since yesterday.", "She's been sick since yesterday. She's sick today.",
         right="She's been sick since yesterday.", category='Tense', confidence=0.92)


def for_since():
    rule("tense.for_year.for",
         r"(?i)\b(?:have|has|had|['’]ve)\s+(?:been|lived|stayed|known|waited) (?:(?:here|there|together|alone) |(?:in|at) [A-Z][a-z]+ )?(?P<target>for) (?:19|20)\d\d(?:\s*[.,;:!?)]|\s*$)",
         "since", "A starting point in time (a year) takes “since”, not “for”: “since 2010”.",
         "I have lived here for 2010.", "I have lived here since 2010. I have lived here for ten years. A second season has been planned for 2007.",
         right="I have lived here since 2010.", category='Tense', confidence=0.93,
         more_pos=[("She has been in Pune for 2018.", "She has been in Pune since 2018.")])
    rule("tense.since_for.vague",
         r"(?i)\b(?P<target>since) (?:a long time|a while|many years|a few years|a couple of years|some time|quite some time|"
         r"ages|years|decades|centuries|so long|a very long time)(?:[.!?,;:]|$| (?:and|but|so|now|already|I|we|he|she|they|it)\b)",
         "for", "A length of time takes “for”, not “since”: “for a long time”.",
         "I have not seen him since a long time.", "I have not seen him for a long time. I have not seen him since 2010.",
         right="I have not seen him for a long time.", category='Word choice', confidence=0.94,
         more_pos=[("We have been friends since ages.", "We have been friends for ages.")])
    rule("tense.since_for.long",
         r"(?i)\b(?P<target>since long)(?:[.!?,;:]|$| (?:and|but|so|now|already)\b)",
         "for a long time", "A length of time takes “for”: “for a long time”.",
         "I have known him since long.", "I have known him for a long time. I have known him since long before that.",
         right="I have known him for a long time.", category='Word choice', confidence=0.93)
    rule("tense.since_for.article_unit",
         r"(?i)\b(?P<target>since) (?:an|a|half an|half a) (?:hour|day|week|month|year|minute|decade)(?:[.!?,;:]|$| (?:now|already|and|but|so|in|at|on|with|for|to|here|there|because|when|until)\b)",
         "for", "A length of time takes “for”, not “since”: “for an hour”.",
         "I have been waiting since an hour.", "I have been waiting for an hour. I have been waiting since an hour ago.",
         right="I have been waiting for an hour.", category='Word choice', confidence=0.94,
         more_pos=[("She has lived here since a year.", "She has lived here for a year.")])
    rule("tense.since_for.last_n",
         r"(?i)\b(?P<target>since last) (?:\d+|two|three|four|five|six|seven|eight|nine|ten|twelve|few|several) (?:hours|days|weeks|months|years|decades)\b",
         "for the last", "A length of time takes “for the last”, not “since last”: “for the last three years”.",
         "I have lived here since last three years.", "I have lived here for the last three years. I have lived here since last year.",
         right="I have lived here for the last three years.", category='Word choice', confidence=0.94)


def how_long():
    for g in ("living", "waiting", "studying", "learning", "teaching"):
        for s in ("you", "they", "we"):
            rule(f"tense.how_long.progressive.{g}.{s}",
                 rf"(?i)\bhow long (?P<target>are {s} {g})\b",
                 f"have {s} been {g}", "A situation that began earlier and continues takes the present perfect continuous: “How long have you been living here?”.",
                 f"How long are {s} {g} here?", f"How long have {s} been {g} here? How long are {s} staying here?",
                 right=f"How long have {s} been {g} here?", category='Tense', confidence=0.9)
    for s, h in (("you", "have"), ("they", "have"), ("we", "have"), ("he", "has"), ("she", "has")):
        rule(f"tense.how_long.know.{s}",
             rf"(?i)\bhow long (?P<target>(?:do|does) {s} know)\b",
             f"{h} {s} known", "“Know” names a state that continues up to now: “How long have you known him?”.",
             f"How long {'does' if h == 'has' else 'do'} {s} know him?", f"How long {h} {s} known him? How long do we need to wait?",
             right=f"How long {h} {s} known him?", category='Tense', confidence=0.93)


# ---------------------------------------------------------------------------------------------------------------
MARK = (rf"(?:yesterday|the other day|last (?:night|week|weekend|month|year|summer|winter|spring|autumn|{DAYS}|{MONTHS})|"
        r"(?:\d+|a|an|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|a few|a couple of|"
        r"several|many|some|half an|half a) (?:seconds?|minutes?|hours?|days?|weeks?|months?|years?|decades?|centuries)"
        r" ago|(?:a long time|a while|long|ages) ago)")
# the markers the engine's own check lacks
MARK_GAP = rf"(?:the other day|last (?:{MONTHS}|decade|century|semester|quarter|christmas|easter|diwali))"
WIN = (r"(?:(?:him|her|them|me|us|you|it|that|this|everything|nothing|something|anything|everyone|anyone|someone|"
       r"there|here|home|back|out|away|early|late|again|twice|once)|(?:the|a|an|my|your|his|her|our|their|this|that|"
       r"these|those|some|any|each|every|no|one|two|three|four|five|six|several|many|few|more|most|all) [A-Za-z]+|"
       r"(?-i:[A-Z][a-z]+)|(?:to|at|in|on|with|from) (?:(?:the|a|an|my|your|his|her|our|their) )?[A-Za-z]+)")


def perfect_marker():
    """I have seen him yesterday -> I saw him yesterday."""
    cov = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'coverage_yt.json')))
    for v in ALL_ROWS:
        b, v2, v3 = v['base'], v['past'], v['part']
        if b in ('come', 'run', 'become', 'overcome', 'lie', 'hide', 'show', 'sew',
                 'ring', 'slay', 'bind', 'grind', 'sit', 'wind', 'retake'):
            # (the last six: the engine's own check rewrites their correct past again, e.g. "rang" to "ranged")
            continue
        # verbs the engine already fixes get only the markers it lacks
        full = b not in cov
        marker = MARK if full else MARK_GAP
        mtext = 'yesterday' if full else 'the other day'
        pat = (rf"(?i)\b(?:(?:I|we|you|they) |(?:he|she|it) )(?P<target>(?:have|has) {v3})"
               rf"(?: {WIN})? {marker}{END}")
        for pos in [f"I have {v3} {t} {mtext}." for t in ("it", "him", "there", "the work", "the story")]:
            if re.search(pat, pos):
                break
        else:
            PROBLEMS.append(f"perfect_marker.{b}: no example"); continue
        right = pos.replace(f"have {v3}", v2)
        other = 'two days ago' if full else 'last June'
        neg = f"{right} I have {v3} it since {mtext}. I have {v3} it, and the report sent yesterday is ready."
        neg = neg.replace(f"I have {v3} it since {mtext}. ", "")
        rule(f"tense.perfect_marker{'' if full else '_gap'}.{b}", pat, v2,
             f"A finished past time (“yesterday”, “ago”, “last week”) takes the simple past: “{v2}”, not “have {v3}”.",
             pos, neg, right=right, category='Tense', confidence=0.94,
             more_pos=[(pos.replace(mtext, other), right.replace(mtext, other))])
    # regular verbs: "have visited ... last June"
    rule("tense.perfect_marker_gap.regular",
         rf"(?i)\b(?:(?:I|we|you|they) |(?:he|she|it) )(?P<target>(?:have|has) (?P<v>[a-z]{{3,}}ed))"
         rf"(?: {WIN})? {MARK_GAP}{END}",
         "${v}", "A finished past time (“last June”, “the other day”) takes the simple past: “visited”, not “have visited”.",
         "We have visited Paris last June.", "We visited Paris last June. We have visited Paris twice since last June.".replace(" We have visited Paris twice since last June.", ""),
         right="We visited Paris last June.", category='Tense', confidence=0.93,
         more_pos=[("She has called me the other day.", "She called me the other day.")])
