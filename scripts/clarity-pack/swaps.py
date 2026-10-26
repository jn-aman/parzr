"""Fixed wordy phrases and their plain replacements (each swap keeps the sentence grammatical as it stands)."""
from core import *

BOUND = ('(?:\\s*[.,;:!?)"”’\\n]|\\s*$|\\s+(?:and|but|or|so|when|if|once|after|because|to|we|I|you|they|he|she|it|the|this|'
         'that|there|our|my|your)\\b)')


def cs(rid, body, repl, conf, reason, pos, exp, neg):
    """A concession phrase: not after "even" ("even although" is not English)."""
    add(rid, '(?im)(?:(?:^|[.!?,;:]\\s+)|\\b[a-z]*(?:[a-mo-z]|[a-df-z]n|[a-uw-z]en)\\s+)(?P<target>%s)\\b' % body, repl, conf, reason, pos, exp,
        neg + ' He won even %s he was ill.' % body)


def build():
    section('Reasons and concessions')
    construction('"the fact that" after a connective: due to / owing to / on account of / by virtue of / for the reason that -> because')
    sw('reason.due_to_fact', 'due to the fact that', 'because', 0.8, 'Shorter: say “because”.',
       'We left early due to the fact that the road was closed.', 'We left early because the road was closed.',
       'We left early because the road was closed. The fact that it rained did not matter. Due to flooding, the road shut.')
    sw('reason.owing_to_fact', 'owing to the fact that', 'because', 0.8, 'Shorter: say “because”.',
       'The match was off owing to the fact that the pitch was flooded.', 'The match was off because the pitch was flooded.',
       'The match was off because the pitch was flooded. Owing to the rain, the pitch was flooded.')
    sw('reason.on_account_of_fact', 'on account of the fact that', 'because', 0.8, 'Shorter: say “because”.',
       'He stayed home on account of the fact that he was ill.', 'He stayed home because he was ill.',
       'He stayed home because he was ill. He stayed home on account of his cold.')
    sw('reason.by_virtue_of_fact', 'by virtue of the fact that', 'because', 0.75, 'Shorter: say “because”.',
       'She qualifies by virtue of the fact that she lived there.', 'She qualifies because she lived there.',
       'She qualifies because she lived there. She qualifies by virtue of her residence.')
    sw('reason.for_the_reason_that', 'for the reason that', 'because', 0.75, 'Shorter: say “because”.',
       'He declined for the reason that he was busy.', 'He declined because he was busy.',
       'He declined because he was busy. He gave no reason that I could accept.')
    sw('reason.in_view_of_fact', 'in view of the fact that', 'since', 0.75, 'Shorter: say “since”.',
       'We will wait in view of the fact that the budget is tight.', 'We will wait since the budget is tight.',
       'We will wait since the budget is tight. In view of the budget, we will wait.')
    sw('reason.in_light_of_fact', 'in (?:the )?light of the fact that', 'since', 0.75, 'Shorter: say “since”.',
       'We will wait in light of the fact that the budget is tight.', 'We will wait since the budget is tight.',
       'We will wait since the budget is tight. In light of the budget, we will wait.')
    sw('reason.considering_fact', 'considering the fact that', 'considering that', 0.7, 'Drop “the fact”: “considering that” says the same.',
       'He did well considering the fact that he was ill.', 'He did well considering that he was ill.',
       'He did well considering that he was ill. Considering the cost, he did well.')
    sw('reason.given_fact', 'given the fact that', 'given that', 0.7, 'Drop “the fact”: “given that” says the same.',
       'It is cheap given the fact that it is new.', 'It is cheap given that it is new.',
       'It is cheap given that it is new. Given the price, it is cheap.')
    sw('reason.in_case_that', 'in the (?:event|case) that', 'if', 0.8, 'Shorter: say “if”.',
       'Call us in the event that the alarm sounds.', 'Call us if the alarm sounds.',
       'Call us if the alarm sounds. In the event of fire, leave the building. In case of doubt, ask.')
    sw('reason.in_the_case_where', 'in the case where', 'if', 0.7, 'Shorter: say “if”.',
       'Ask for help in the case where the form fails.', 'Ask for help if the form fails.',
       'Ask for help if the form fails. In the case of failure, ask for help.')
    construction('"the fact that" after a concession: despite / in spite of / regardless of / notwithstanding / except for -> although, even though, except that')
    cs('reason.despite_fact', 'despite the fact that', 'although', 0.75, 'Shorter: say “although”.',
       'He came despite the fact that he was tired.', 'He came although he was tired.',
       'He came although he was tired. He came despite the rain, and the fact was plain.')
    cs('reason.in_spite_of_fact', 'in spite of the fact that', 'although', 0.75, 'Shorter: say “although”.',
       'He won in spite of the fact that he was tired.', 'He won although he was tired.',
       'He won although he was tired. He won in spite of his injury.')
    cs('reason.regardless_of_fact', 'regardless of the fact that', 'even though', 0.7, 'Shorter: say “even though”.',
       'We went regardless of the fact that it rained.', 'We went even though it rained.',
       'We went even though it rained. We went regardless of the rain.')
    cs('reason.notwithstanding_fact', 'notwithstanding the fact that', 'although', 0.7, 'Shorter: say “although”.',
       'He stayed notwithstanding the fact that it was late.', 'He stayed although it was late.',
       'He stayed although it was late. He stayed notwithstanding the hour.')
    sw('reason.except_for_fact', 'except for the fact that', 'except that', 0.7, 'Drop “for the fact”: “except that” says the same.',
       'The plan is fine except for the fact that it costs too much.', 'The plan is fine except that it costs too much.',
       'The plan is fine except that it costs too much. The plan is fine except for the cost.')
    construction('"in the event that" / "for the purpose of"')
    sw('reason.for_the_purpose_of', 'for the purpose of', 'for', 0.75, 'Shorter: say “for”.',
       'We use the room for the purpose of testing.', 'We use the room for testing.',
       'We use the room for testing. The purpose of the room is clear. For the purposes of this note, we agree.')
    section('Topic phrases')
    construction('"with regard to" / "in regard to" / "with reference to" / "pertaining to" -> about (mid-sentence) or Regarding (sentence start)')
    add('topic.regard_mid', '(?i)\\b[a-z]+ (?P<target>(?:with|in) regard to|(?:with|in) reference to|pertaining to)\\b', 'about', 0.7,
        'Shorter: say “about”.', 'I am writing with regard to your order.', 'I am writing about your order.',
        'I am writing about your order. Give him my regards. This is for reference.')
    add('topic.regard_start', '(?im)(?:^|[.!?]\\s+)(?P<target>(?:with|in) regard to|(?:with|in) reference to)\\b', 'Regarding', 0.7,
        'Shorter: say “regarding”.', 'With regard to your order, we have a reply.', 'Regarding your order, we have a reply.',
        'Regarding your order, we have a reply. Please give him my regards.')
    construction('"as to whether/how/why/..." -> drop "as to"')
    add('topic.as_to_whether', '(?i)\\b(?:unsure|unclear|uncertain|unknown|unaware|doubt|doubtful|undecided|confused|curious|question|debate|wonder|'
        'wondering|ask|asked|asking|decide|decided|deciding|decision|disagree|inquire|advise|advice|uncertainty|clear|sure|certain|know|knew) '
        '(?P<target>as to )(?:whether|how|why|when|where|who|what|which)\\b', '', 0.72,
        'Drop “as to”: the question word already links the clause.', 'He is unsure as to whether he should go.',
        'He is unsure whether he should go.',
        'He is unsure whether he should go. As to why he left, nobody knows. It is up to the firm as to how it ends. It was made so well as to impress us.')
    construction('"regardless of whether or not" / "whether or not" after know/ask/wonder/decide -> whether')
    add('topic.regardless_whether_or_not', '(?i)\\b(?P<target>(?P<r>regardless|irrespective) of whether or not)\\b', '${r} of whether', 0.8,
        'Drop “or not”: “whether” already covers both cases.', 'We will go regardless of whether or not it rains.',
        'We will go regardless of whether it rains.', 'We will go regardless of whether it rains. We will go regardless of the weather.')
    add('topic.whether_or_not_after_verb', '(?i)\\b(?:wonder|wondered|wondering|know|knew|ask|asked|decide|decided|determine|determined|check|'
        'checked|see|sure|unsure|question) (?P<target>whether or not) [a-z]', 'whether', 0.7,
        'Drop “or not”: “whether” already covers both cases.', 'I wonder whether or not the shop is open.',
        'I wonder whether the shop is open.',
        'I wonder whether the shop is open. We will go whether or not it rains. I do not know whether or not.')
    construction('"the way in which" / "the manner in which" -> how; "the time at which" -> when; "the place at which/in which" -> where')
    sw('topic.way_in_which', 'the (?:way|manner) in which', 'how', 0.7, 'Shorter: say “how”.',
       'We saw the way in which the system failed.', 'We saw how the system failed.',
       'We saw how the system failed. The way he spoke was calm. The room in which we met was cold.')
    sw('topic.time_at_which', 'the time at which', 'when', 0.7, 'Shorter: say “when”.',
       'Check the time at which the shop opens.', 'Check when the shop opens.',
       'Check when the shop opens. The time was late. We met at which point?')
    sw('topic.place_at_which', 'the place (?:at|in) which', 'where', 0.7, 'Shorter: say “where”.',
       'Tell me the place at which we meet.', 'Tell me where we meet.',
       'Tell me where we meet. It is a place which we love. The place was quiet.')
    construction('"in situations/cases where" -> when')
    sw('topic.in_cases_where', 'in (?:situations|cases|instances|circumstances) where', 'when', 0.62, 'Shorter: say “when”.',
       'Call us in situations where the form fails.', 'Call us when the form fails.',
       'Call us when the form fails. In some cases where it fails, call us. In many situations, we help.')
    construction('"and so on and so forth" -> and so on')
    sw('topic.and_so_on_and_so_forth', 'and so on and so forth', 'and so on', 0.75, 'Say it once: “and so on”.',
       'We packed tents, stoves, and so on and so forth.', 'We packed tents, stoves, and so on.',
       'We packed tents, stoves, and so on. We worked on and on.')

    section('Time')
    construction('"at this point in time" and its variants -> now')
    sw('time.at_this_point_in_time', 'at (?:this|the (?:present|current)) (?:point|moment) in time', 'now', 0.78, 'Shorter: say “now”.',
       'We cannot comment at this point in time.', 'We cannot comment now.',
       'We cannot comment now. At this point, we wait. The point in time is unclear.')
    sw('time.at_the_present_time', 'at (?:the|this) (?:present|current) (?:time|moment)', 'now', 0.78, 'Shorter: say “now”.',
       'We cannot comment at the present time.', 'We cannot comment now.',
       'We cannot comment now. At present, nothing is planned. The present is a gift. At this time of year it snows.')
    construction('"in the near future" and variants -> soon')
    sw('time.in_the_near_future', 'in the near future', 'soon', 0.75, 'Shorter: say “soon”.',
       'We will ship the update in the near future.', 'We will ship the update soon.',
       'We will ship the update soon. The near future is unclear. In the future we will ship it.')
    construction('"at a later date" / "at an earlier time" -> later / earlier')
    sw('time.at_a_later_date', 'at (?:a|some) (?:later|future) (?:date|time|stage|point(?: in time)?)', 'later', 0.75, 'Shorter: say “later”.',
       'We will revisit this at a later date.', 'We will revisit this later.',
       'We will revisit this later. At a later stage of the process, we vote. The later date works.', follow=BOUND)
    sw('time.at_an_earlier_date', 'at an earlier (?:date|time|stage|point(?: in time)?)', 'earlier', 0.75, 'Shorter: say “earlier”.',
       'We had met at an earlier date.', 'We had met earlier.',
       'We had met earlier. At an earlier stage of the process, we met. The earlier date works.', follow=BOUND)
    construction('"until such time as" / "by the time that" / "at the time that" / "during the time that"')
    sw('time.until_such_time_as', 'until such time as', 'until', 0.78, 'Shorter: say “until”.',
       'Do not leave until such time as the manager arrives.', 'Do not leave until the manager arrives.',
       'Do not leave until the manager arrives. Such time as we have is short.')
    sw('time.by_the_time_that', 'by the time that', 'by the time', 0.7, 'Drop “that”: “by the time” already links the clause.',
       'We were home by the time that it rained.', 'We were home by the time it rained.',
       'We were home by the time it rained. The time that we spent was fun.')
    sw('time.at_the_time_that', 'at the time (?:that|when)', 'when', 0.72, 'Shorter: say “when”.',
       'I was away at the time that it happened.', 'I was away when it happened.',
       'I was away when it happened. At the time of the crash, I was away.')
    sw('time.during_the_time_that', 'during the time (?:that|when)', 'while', 0.7, 'Shorter: say “while”.',
       'I was away during the time that it happened.', 'I was away while it happened.',
       'I was away while it happened. During the time off, I slept.')
    construction('"during the course of" / "throughout the course of" / "over the course of" / "in the course of" -> during / throughout / over')
    sw('time.during_the_course_of', 'during the course of', 'during', 0.75, 'Shorter: say “during”.',
       'We spoke during the course of the meeting.', 'We spoke during the meeting.',
       'We spoke during the meeting. The course of the river is long. Of course we spoke.')
    sw('time.throughout_the_course_of', 'throughout the course of', 'throughout', 0.75, 'Shorter: say “throughout”.',
       'Sales rose throughout the course of the year.', 'Sales rose throughout the year.',
       'Sales rose throughout the year. The course of the year was steady.')
    sw('time.over_the_course_of', 'over the course of', 'over', 0.75, 'Shorter: say “over”.',
       'Sales rose over the course of the year.', 'Sales rose over the year.',
       'Sales rose over the year. The course of the year was steady.')
    add('time.in_the_course_of', '(?i)\\b(?P<target>in the course of) (?:the|my|our|his|her|their|your|this|that|these|those)\\b', 'during', 0.68,
        'Shorter: say “during”.', 'We spoke in the course of the meeting.', 'We spoke during the meeting.',
        'We spoke during the meeting. In the course of events, we spoke. The course of the meeting was calm.')
    construction('"for the duration of" -> during')
    sw('time.for_the_duration_of', 'for the duration of', 'during', 0.7, 'Shorter: say “during”.',
       'The office is closed for the duration of the repairs.', 'The office is closed during the repairs.',
       'The office is closed during the repairs. The duration of the repairs is long.')
    construction('"for / over / within / after a period of" + a length of time -> for / over / within / after')
    nums = ('(?:\\d[\\d,.]*|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty|thirty|forty|fifty|sixty|ninety|'
            'several|many|few|some|about|approximately|roughly|nearly|almost|over|more|at|up|less|weeks|months|years|days|hours|decades|'
            'centuries|minutes|seconds)')
    for w, pos, exp in [('for', 'The permit is valid for a period of two years.', 'The permit is valid for two years.'),
                        ('over', 'Sales rose over a period of six months.', 'Sales rose over six months.'),
                        ('within', 'Reply within a period of five days.', 'Reply within five days.'),
                        ('after', 'Prices fell after a period of three weeks.', 'Prices fell after three weeks.')]:
        add('time.%s_a_period_of' % w, '(?i)\\b(?P<target>%s a period of) %s\\b' % (w, nums), w, 0.7,
            'Shorter: say “%s” and the length of time.' % w, pos, exp,
            exp + ' A period of rest helped. The permit lasts for a period of time.')
    add('time.period_of_time', '(?i)\\b(?:for|over|in|after|within) a (?P<a>long|short|brief|limited|considerable|certain) (?P<target>period of time)\\b',
        'time', 0.7, 'Shorter: “period of” adds nothing.', 'We waited for a long period of time.', 'We waited for a long time.',
        'We waited for a long time. A period of time passed. Over a long period, sales rose.')
    construction('"on several occasions" and variants -> several times, once, twice')
    for rid, body, rep, pos, exp in [
            ('several', 'on several occasions', 'several times', 'She called him on several occasions.', 'She called him several times.'),
            ('many', 'on many occasions', 'many times', 'She called him on many occasions.', 'She called him many times.'),
            ('numerous', 'on numerous occasions', 'many times', 'She called him on numerous occasions.', 'She called him many times.'),
            ('multiple', 'on multiple occasions', 'multiple times', 'She called him on multiple occasions.', 'She called him multiple times.'),
            ('a_few', 'on a few occasions', 'a few times', 'She called him on a few occasions.', 'She called him a few times.'),
            ('one', 'on one occasion', 'once', 'She called him on one occasion.', 'She called him once.'),
            ('two', 'on two occasions', 'twice', 'She called him on two occasions.', 'She called him twice.'),
            ('three', 'on three occasions', 'three times', 'She called him on three occasions.', 'She called him three times.')]:
        sw('time.on_%s_occasions' % rid, body, rep, 0.7, 'Shorter: say “%s”.' % rep, pos, exp,
           exp + ' The occasion was special. She called him on occasion.')
    construction('"in this day and age" -> today; "in the year 1998" -> "in 1998"')
    sw('time.in_this_day_and_age', 'in (?:this|today[’\']s) (?:modern )?day and age', 'today', 0.65, 'Shorter: say “today”.',
       'Everyone has a phone in this day and age.', 'Everyone has a phone today.',
       'Everyone has a phone today. He lived day by day in this age.')
    add('time.in_the_year_1998', '(?i)\\bin (?P<target>the year (?:of )?)(?:1[0-9]{3}|20[0-9]{2})\\b', '', 0.72,
        'Drop “the year”: “in 1998” is enough.', 'The bridge opened in the year 1998.', 'The bridge opened in 1998.',
        'The bridge opened in 1998. In the year ahead, we plan more. In the year of the flood, we left.')
    construction('"as a general rule" / "in the majority of cases" -> generally, usually, almost always')
    sw('time.as_a_general_rule', 'as a general rule', 'generally', 0.7, 'Shorter: say “generally”.',
       'As a general rule, we reply within a day.', 'Generally, we reply within a day.',
       'Generally, we reply within a day. As a rule, we reply. The general rule is simple.')
    sw('time.in_the_majority_of_cases', 'in the (?:great |large )?majority of (?:cases|instances)', 'usually', 0.7, 'Shorter: say “usually”.',
       'In the majority of cases, the fix works.', 'Usually, the fix works.',
       'Usually, the fix works. In a majority of cases, the fix works. The majority of cases were fine.')
    sw('time.in_the_vast_majority_of_cases', 'in the (?:vast|overwhelming) majority of (?:cases|instances)', 'almost always', 0.7,
       'Shorter: say “almost always”.', 'In the vast majority of cases, the fix works.', 'Almost always, the fix works.',
       'Almost always, the fix works. The vast majority of cases were fine.')

    section('Quantity')
    construction('"a large number of" and variants -> many')
    sw('quantity.a_large_number_of', 'a (?:large|great|good|vast) number of', 'many', 0.75, 'Shorter: say “many”.',
       'A large number of users reported the bug.', 'Many users reported the bug.',
       'Many users reported the bug. The number of users is large. A number of users reported it.')
    construction('"the majority of" + the / these / my / them -> most of; + a plural noun -> most')
    dets = '(?:the|these|those|my|our|his|her|their|your|its|them|us|you)'
    add('quantity.majority_of_det', '(?i)\\b(?P<target>the majority of) %s\\b' % dets, 'most of', 0.75, 'Shorter: say “most of”.',
        'The majority of the staff agreed.', 'Most of the staff agreed.',
        'Most of the staff agreed. A majority of 12 votes won. The majority view won.')
    nouns = ('(?:people|users|customers|clients|students|employees|workers|respondents|participants|patients|members|voters|residents|'
             'citizens|readers|viewers|players|teachers|parents|children|women|men|countries|companies|businesses|schools|doctors|'
             'researchers|developers|experts|scientists|investors|visitors|drivers|owners|nurses|farmers|families|studies|states|'
             'stores|shops|sites|apps|tests|samples|surveys|reviews|reports|requests|errors|bugs|issues|problems|complaints|questions)')
    add('quantity.majority_of_noun', '(?i)\\b(?P<target>the majority of) %s\\b' % nouns, 'most', 0.75, 'Shorter: say “most”.',
        'The majority of people agreed.', 'Most people agreed.', 'Most people agreed. The majority view agreed later. A majority of people agreed later.')
    add('quantity.vast_majority_of_det', '(?i)\\b(?P<target>the (?:vast|overwhelming) majority of) %s\\b' % dets, 'nearly all of', 0.72,
        'Shorter: say “nearly all of”.', 'The vast majority of the staff agreed.', 'Nearly all of the staff agreed.',
        'Nearly all of the staff agreed. The vast majority view won.')
    add('quantity.vast_majority_of_noun', '(?i)\\b(?P<target>the (?:vast|overwhelming) majority of) %s\\b' % nouns, 'nearly all', 0.72,
        'Shorter: say “nearly all”.', 'The vast majority of people agreed.', 'Nearly all people agreed.',
        'Nearly all people agreed. The vast majority view won. A vast majority of people agreed later.')
    construction('"in the amount of" -> of; "in excess of" -> more than; "in the neighborhood of" + number -> about')
    sw('quantity.in_the_amount_of', 'in the amount of', 'of', 0.75, 'Shorter: say “of”.',
       'We received a refund in the amount of 40 dollars.', 'We received a refund of 40 dollars.',
       'We received a refund of 40 dollars. The amount of the refund is clear.')
    sw('quantity.in_excess_of', 'in excess of', 'more than', 0.65, 'Shorter: say “more than”.',
       'The cost was in excess of five thousand dollars.', 'The cost was more than five thousand dollars.',
       'The cost was more than five thousand dollars. Eating in excess is unhealthy.')
    add('quantity.in_the_neighborhood_of', '(?i)\\b(?P<target>in the neighbou?rhood of) (?:[$£€]|\\d)', 'about', 0.7, 'Shorter: say “about”.',
        'The fee is in the neighborhood of 50 dollars.', 'The fee is about 50 dollars.',
        'The fee is about 50 dollars. We live in the neighborhood of the school.')

    section('Place and means')
    construction('"in close proximity to" / "in the vicinity of" -> near')
    sw('place.in_close_proximity_to', 'in close proximity to', 'near', 0.75, 'Shorter: say “near”.',
       'The shop is in close proximity to the station.', 'The shop is near the station.',
       'The shop is near the station. The proximity of the shop is handy.')
    sw('place.in_the_vicinity_of', 'in the vicinity of', 'near', 0.7, 'Shorter: say “near”.',
       'The shop is in the vicinity of the station.', 'The shop is near the station.',
       'The shop is near the station. The vicinity is quiet.')
    construction('"with the exception of" -> except for; "in the absence of" -> without; "in conjunction with" -> with')
    sw('place.in_the_absence_of', 'in the absence of', 'without', 0.7, 'Shorter: say “without”.',
       'We proceeded in the absence of a clear plan.', 'We proceeded without a clear plan.',
       'We proceeded without a clear plan. The absence of a plan was clear.')
    sw('place.in_conjunction_with', 'in conjunction with', 'with', 0.7, 'Shorter: say “with”.',
       'Use the tool in conjunction with the manual.', 'Use the tool with the manual.',
       'Use the tool with the manual. The conjunction “and” joins words.')
    construction('"by means of" + determiner / "through the use of" -> using')
    add('place.by_means_of', '(?i)\\b(?P<target>by means of) (?:the|a|an|this|that|these|those|his|her|our|their|your|my|its)\\b', 'using', 0.7,
        'Shorter: say “using”.', 'We moved the box by means of a trolley.', 'We moved the box using a trolley.',
        'We moved the box using a trolley. Money is a means of exchange. We moved it by means of which tool?')
    sw('place.through_the_use_of', 'through the use of', 'using', 0.72, 'Shorter: say “using”.',
       'We cut costs through the use of cheaper parts.', 'We cut costs using cheaper parts.',
       'We cut costs using cheaper parts. The use of cheaper parts cut costs.')

    section('Verb frames')
    construction('"is in the process of" + -ing -> drop "in the process of"')
    add('frame.in_the_process_of', "(?i)\\b(?:is|are|was|were|am|['’]m|['’]re|['’]s) (?P<target>in the process of )[a-z]+ing\\b", '', 0.7,
        'Drop “in the process of”: the -ing form already says the work is under way.',
        'We are in the process of reviewing the files.', 'We are reviewing the files.',
        'We are reviewing the files. The process of reviewing takes time. He was in the middle of reviewing.')
    construction('"as per" skipped; "at which point"; "it is" frames')
    flush()
