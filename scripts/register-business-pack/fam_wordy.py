"""Wordy stock phrases with a plain replacement: purpose, time, cause, reference, quantity."""
from core import rule, note

S = "Style"
def build():
    # ---- purpose -------------------------------------------------------------------------------
    rule("wordy.so_as_to", r"(?i)\b(?P<target>so as to)\b", "to", S, 0.7,
         "“So as to” can usually be just “to”.",
         "We left early so as to avoid the traffic.",
         "He tiptoed so as not to wake her. We left early to avoid the traffic.",
         "We left early to avoid the traffic.", "purpose")
    rule("wordy.in_order_for", r"(?i)\b(?P<target>in order for)\s+(?:[\w'’-]+\s+){1,4}to\b", "for", S, 0.7,
         "“For” does the job of “in order for”.",
         "In order for this to work, the team must agree.",
         "For this to work, the team must agree. Put the forms in order. For the audit, keep them in order.",
         "For this to work, the team must agree.", "purpose")
    rule("wordy.in_order_that", r"(?i)\b(?P<target>in order that)\b", "so that", S, 0.7,
         "“So that” is plainer than “in order that”.",
         "Please send the file in order that we can review it.",
         "Please send the file so that we can review it.",
         "Please send the file so that we can review it.", "purpose")
    # ---- time ----------------------------------------------------------------------------------
    rule("wordy.now_phrases",
         r"(?i)\b(?P<target>at this point in time|at this point of time|at the present point in time|at the present time|at the current time|at this moment in time|at the present moment in time|at the present moment|at the current moment|at this juncture)\b",
         "now", S, 0.75,
         "“Now” says the same thing in one word.",
         "We are not accepting orders at this moment in time.",
         "At this point, the road bends left. The idea came at that time. We are not accepting orders now.",
         "We are not accepting orders now.", "time")
    rule("wordy.at_this_time_start", r"(?im)(?:^|[.!?]\s+)(?P<target>at this time)\s*,", "now", S, 0.7,
         "\u201cNow\u201d is shorter than \u201cat this time\u201d.",
         "At this time, we cannot offer refunds.",
         "At this time of year the lake freezes. Each year at this time, I send a card. Now, we cannot offer refunds.",
         "Now, we cannot offer refunds.", "time")
    rule("wordy.at_this_time_end",
         r"(?i)\b(?:comment|respond|answer|share|provide|disclose|confirm|discuss|say|offer|accept|release|announce|decide|determine|available|unavailable|closed|open|appropriate|inappropriate|necessary|unnecessary|possible|impossible|needed|required|planned|scheduled|interest|class|content|teaching|working)\b[^.!?;,\n]{0,30}\s(?P<target>at this time)\s*(?:[.,;!?]|$)",
         "now", S, 0.7,
         "\u201cNow\u201d is shorter than \u201cat this time\u201d.",
         "We cannot comment at this time.",
         "Each year at this time, I send a card. We spoke at this time yesterday. We cannot comment now.",
         "We cannot comment now.", "time")
    rule("wordy.at_that_time", r"(?i)\b(?P<target>at that point in time|at that moment in time)\b", "then", S, 0.75,
         "“Then” is shorter than “at that point in time”.",
         "He was unaware of the problem at that point in time.",
         "At that point the road ends. He was unaware of the problem then.",
         "He was unaware of the problem then.", "time")
    rule("wordy.later_date", r"(?i)\b(?P<target>at (?:a later|some later|a future|some future) (?:date|time))\b\s*(?:[.,;!?]|$)", "later", S, 0.75,
         "“Later” replaces “at a later date”.",
         "We can revisit the budget at some future date.",
         "We left at a later hour. Revisit it on a later date. We can revisit the budget later.",
         "We can revisit the budget later.", "time")
    rule("wordy.until_such_time", r"(?i)\b(?P<target>until such time as)\b", "until", S, 0.75,
         "“Until” does the work of “until such time as”.",
         "Hold the funds until such time as the audit ends.",
         "Until then, hold the funds. Hold the funds until the audit ends.",
         "Hold the funds until the audit ends.", "time")
    rule("wordy.at_such_time", r"(?i)\b(?P<target>at such time as)\b", "when", S, 0.75,
         "“When” is plainer than “at such time as”.",
         "We will reopen at such time as the repairs are finished.",
         "We will reopen when the repairs are finished. He arrived at such a time as to see it.",
         "We will reopen when the repairs are finished.", "time")
    rule("wordy.during_the_time_that", r"(?i)\b(?P<target>during the time (?:that|when))\b", "while", S, 0.72,
         "“While” is shorter than “during the time that”.",
         "We lost data during the time that the server was down.",
         "During the time we had, we finished. We lost data while the server was down.",
         "We lost data while the server was down.", "time")
    rule("wordy.at_the_time_that", r"(?i)\b(?P<target>at the time (?:that|when))\b", "when", S, 0.72,
         "“When” is shorter than “at the time that”.",
         "At the time that the report was filed, nobody objected.",
         "At the time, nobody objected. The time when we met was good. When the report was filed, nobody objected.",
         "When the report was filed, nobody objected.", "time")
    # ---- "on a ... basis" ----------------------------------------------------------------------
    rule("wordy.basis_period", r"(?i)\b(?P<target>on an? (?P<w>daily|weekly|monthly|yearly|hourly|nightly|quarterly) basis)\b", "${w}", S, 0.72,
         "The adverb says it in one word: “monthly”, not “on a monthly basis”.",
         "We review the budget on a monthly basis.",
         "The monthly basis for the fee is stated. She works on a daily schedule. We review the budget monthly.",
         "We review the budget monthly.", "basis")
    rule("wordy.basis_adjective",
         r"(?i)\b(?P<target>on an? (?P<w>regular|consistent|continuous|individual|permanent|frequent|occasional|immediate|urgent|separate|random) basis)\b",
         "${w}ly", S, 0.72,
         "Use the adverb instead of “on a … basis”.",
         "Files are backed up on a regular basis.",
         "A regular basis of comparison is needed. They sell it on a first-come basis. Files are backed up regularly.",
         "Files are backed up regularly.", "basis")
    rule("wordy.basis_annual", r"(?i)\b(?P<target>on an annual basis)\b", "annually", S, 0.72,
         "“Annually” is shorter than “on an annual basis”.",
         "The fee is reviewed on an annual basis.",
         "The annual basis of the fee is public. The fee is reviewed annually.",
         "The fee is reviewed annually.", "basis")
    rule("wordy.basis_temporary", r"(?i)\b(?P<target>on a temporary basis)\b", "temporarily", S, 0.72,
         "“Temporarily” is shorter than “on a temporary basis”.",
         "She is covering the desk on a temporary basis.",
         "A temporary basis was agreed. She is covering the desk temporarily.",
         "She is covering the desk temporarily.", "basis")
    rule("wordy.basis_voluntary", r"(?i)\b(?P<target>on a voluntary basis)\b", "voluntarily", S, 0.72,
         "“Voluntarily” is shorter than “on a voluntary basis”.",
         "Staff attend the sessions on a voluntary basis.",
         "A voluntary basis was proposed. Staff attend the sessions voluntarily.",
         "Staff attend the sessions voluntarily.", "basis")
    rule("wordy.basis_as_needed", r"(?i)\b(?P<target>on an as[- ](?P<w>needed|required) basis)\b", "as ${w}", S, 0.72,
         "“As needed” is shorter than “on an as-needed basis”.",
         "Contractors are hired on an as needed basis.",
         "An as-needed basis is fine. Contractors are hired as needed.",
         "Contractors are hired as needed.", "basis")
    rule("wordy.basis_case_by_case", r"(?i)\b(?P<target>on an? case[- ]by[- ]case basis)\b", "case by case", S, 0.72,
         "“Case by case” is shorter than “on a case-by-case basis”.",
         "Refunds are decided on a case-by-case basis.",
         "A case-by-case basis was agreed. Refunds are decided case by case.",
         "Refunds are decided case by case.", "basis")
    rule("wordy.timely_manner", r"(?i)\b(?P<target>in a timely (?:manner|fashion))\b", "promptly", S, 0.72,
         "“Promptly” is shorter than “in a timely manner”.",
         "Please respond in a timely manner.",
         "A timely response matters. Please respond promptly.",
         "Please respond promptly.", "manner")
    rule("wordy.manner_adverb",
         r"(?i)\b(?P<target>in an? (?P<w>efficient|effective|professional|appropriate|careful|consistent|transparent|accurate|thorough|prompt|courteous|respectful|constructive|collaborative|proactive|diligent|secure|safe|proper|logical|polite|cautious) (?:manner|fashion))\b",
         "${w}ly", S, 0.7,
         "An adverb is shorter than “in a … manner”.",
         "The team handled the claim in an efficient manner.",
         "She spoke in a manner of speaking. He answered in a friendly manner. The team handled the claim efficiently.",
         "The team handled the claim efficiently.", "manner")
    # ---- cause and condition -------------------------------------------------------------------
    rule("wordy.because_phrases",
         r"(?i)\b(?P<target>due to the fact that|owing to the fact that|on account of the fact that|by virtue of the fact that|for the reason that)\b",
         "because", S, 0.78,
         "“Because” replaces this long phrase.",
         "We moved the launch owing to the fact that the vendor was late.",
         "The fact that she resigned surprised us. We moved it due to the delay. We moved the launch because the vendor was late.",
         "We moved the launch because the vendor was late.", "cause")
    rule("wordy.given_that_phrases",
         r"(?i)\b(?P<target>in view of the fact that|in light of the fact that|considering the fact that|given the fact that|taking into account the fact that)\b",
         "given that", S, 0.75,
         "“Given that” is shorter than this phrase.",
         "In view of the fact that costs rose, we paused hiring.",
         "Given that costs rose, we paused hiring. In view of the costs, we paused hiring.",
         "Given that costs rose, we paused hiring.", "cause")
    rule("wordy.though_phrases",
         r"(?i)\b(?P<target>despite the fact that|in spite of the fact that|regardless of the fact that|notwithstanding the fact that)\b",
         "though", S, 0.76,
         "\u201cThough\u201d replaces this long phrase.",
         "We shipped on time despite the fact that the weather was bad.",
         "Despite the delay, we shipped. They ignored the fact that she was ill. We shipped on time though the weather was bad.",
         "We shipped on time though the weather was bad.", "cause")
    rule("wordy.if_event_phrases",
         r"(?i)\b(?P<target>in the event that|in the case that|in the instance that|in the eventuality that)\b",
         "if", S, 0.75,
         "“If” is plainer than “in the event that”.",
         "Call us in the case that the system fails.",
         "In the event of rain, the picnic moves indoors. The event that I attended was long. Call us if the system fails.",
         "Call us if the system fails.", "cause")
    # ---- reference and relation ----------------------------------------------------------------
    rule("wordy.regarding", r"(?i)\b(?P<target>(?:with|in) regards? to)\b", "regarding", S, 0.72,
         "“Regarding” is shorter than “with regard to”.",
         "I am writing in regard to your invoice.",
         "She has high regard for him. Please give my regards to your team. I am writing regarding your invoice.",
         "I am writing regarding your invoice.", "reference")
    rule("wordy.with_reference_to",
         r"(?i)\b(?P<target>(?:with|in) reference to)\s+(?:your|our|my|the|this|that|these|those|his|her|their|its)\b",
         "regarding", S, 0.68,
         "“Regarding” is shorter than “with reference to”.",
         "With reference to your letter of 5 May, we confirm the order.",
         "He made reference to the report. Regarding your letter of 5 May, we confirm the order.",
         "Regarding your letter of 5 May, we confirm the order.", "reference")
    rule("wordy.pertaining_to", r"(?i)\b(?P<target>pertaining to)\b", "about", S, 0.68,
         "“About” is plainer than “pertaining to”.",
         "Questions pertaining to billing go to finance.",
         "This is a question about billing. Pertinent facts were shared.",
         "Questions about billing go to finance.", "reference")
    rule("wordy.as_to_whether", r"(?i)\b(?P<target>as to whether)\b", "whether", "Redundancy", 0.75,
         "“As to” adds nothing before “whether”.",
         "There was doubt as to whether the test would pass.",
         "As to the schedule, we agree. Decide whether to go. There was doubt whether the test would pass.",
         "There was doubt whether the test would pass.", "reference")
    rule("wordy.in_lieu_of", r"(?i)\b(?P<target>in lieu of)\b", "instead of", S, 0.72,
         "“Instead of” is plainer than “in lieu of”.",
         "We offered a voucher in lieu of a refund.",
         "We offered a voucher instead of a refund.",
         "We offered a voucher instead of a refund.", "reference")
    rule("wordy.in_conjunction_with", r"(?i)\b(?P<target>in conjunction with)\b", "with", S, 0.7,
         "“With” does the job of “in conjunction with”.",
         "Use this form in conjunction with the manual.",
         "It was a conjunction of events. Use this form with the manual.",
         "Use this form with the manual.", "reference")
    rule("wordy.with_the_exception_of", r"(?i)\b(?P<target>with the exception of)\b", "except for", S, 0.72,
         "“Except for” is shorter than “with the exception of”.",
         "With the exception of Tom, everyone attended.",
         "Tom was the exception. Everyone except Tom attended.",
         "Except for Tom, everyone attended.", "reference")
    rule("wordy.in_excess_of",
         r"(?i)\b(?P<target>in excess of)\s+(?:[$£€¥]\s?)?\d",
         "more than", S, 0.72,
         "“More than” is plainer than “in excess of”.",
         "Costs in excess of $5,000 need approval.",
         "He spent in excess of his budget. Costs above $5,000 need approval. Costs more than $5,000 need approval.",
         "Costs more than $5,000 need approval.", "reference")
    rule("wordy.in_the_vicinity_of", r"(?i)\b(?P<target>in the vicinity of)\b", "near", S, 0.72,
         "“Near” is shorter than “in the vicinity of”.",
         "The warehouse is in the vicinity of the station.",
         "Vicinity maps are posted. The warehouse is near the station.",
         "The warehouse is near the station.", "reference")
    rule("wordy.in_proximity_to", r"(?i)\b(?P<target>in (?:close )?proximity to)\b", "near", S, 0.72,
         "“Near” is shorter than “in close proximity to”.",
         "The hotel is in close proximity to the airport.",
         "A proximity sensor detects hands. The hotel is near the airport.",
         "The hotel is near the airport.", "reference")
    # ---- quantity ------------------------------------------------------------------------------
    rule("wordy.sufficient_number", r"(?i)\b(?P<target>an? (?:sufficient|adequate) (?:number|amount|quantity) of)\b", "enough", S, 0.72,
         "“Enough” replaces “a sufficient number of”.",
         "We need a sufficient number of volunteers.",
         "A sufficient reason was given. We need enough volunteers.",
         "We need enough volunteers.", "quantity")
    rule("wordy.large_number_of",
         r"(?i)\b(?P<target>a (?:large|great|considerable) number of)\s+(?:(?:people|children|men|women|staff|data)\b|[a-z]{3,}s\b)",
         "many", S, 0.72,
         "\u201cMany\u201d is shorter than \u201ca large number of\u201d.",
         "A great number of users reported the bug.",
         "A large number was printed. The number of users grew. Many users reported the bug.",
         "Many users reported the bug.", "quantity")
    rule("wordy.large_number_of_the",
         r"(?i)\b(?P<target>a (?:large|great|considerable) number of)\s+(?:the|my|our|your|his|her|their|its|these|those)\b",
         "many of", S, 0.72,
         "\u201cMany of\u201d is shorter than \u201ca large number of\u201d.",
         "A great number of the users reported the bug.",
         "A large number was expected. Many of the users reported the bug.",
         "Many of the users reported the bug.", "quantity")
    rule("wordy.majority_of_the",
         r"(?i)\b(?P<target>the majority of)\s+(?:the|my|our|your|his|her|their|its|these|those|this|that)\b",
         "most of", S, 0.72,
         "“Most of” is shorter than “the majority of”.",
         "The majority of the staff agreed.",
         "The majority opinion won. A majority of 40 votes carried it. Most of the staff agreed.",
         "Most of the staff agreed.", "quantity")
    rule("wordy.majority_of_noun",
         r"(?i)\b(?P<target>the majority of)\s+(?:people|users|customers|clients|employees|members|respondents|participants|students|patients|teachers|parents|companies|businesses|countries|states|developers|voters|residents|workers|owners|players|readers|buyers|guests|visitors|families|children|women|men)\b",
         "most", S, 0.72,
         "“Most” is shorter than “the majority of”.",
         "The majority of customers renewed.",
         "The majority opinion won. Most customers renewed.",
         "Most customers renewed.", "quantity")
    rule("wordy.majority_of_cases", r"(?i)\b(?P<target>in (?:the|a) majority of cases)\b", "in most cases", S, 0.72,
         "“In most cases” is shorter than “in the majority of cases”.",
         "In the majority of cases, the fix works.",
         "In most cases, the fix works. In a majority of 12 votes, it passed.",
         "In most cases, the fix works.", "quantity")
    # ---- prepositions of time and place --------------------------------------------------------
    rule("wordy.previous_to", r"(?i)\b(?P<target>previous to)\b", "before", S, 0.78,
         "“Before” is the usual word; “previous to” is nonstandard.",
         "Check the lock previous to departure.",
         "The previous owner left. Check the lock before departure.",
         "Check the lock before departure.", "preposition")
    rule("wordy.during_the_course_of", r"(?i)\b(?P<target>during the course of)\b", "during", S, 0.75,
         "“During” is shorter than “during the course of”.",
         "Questions arose during the course of the audit.",
         "During the course, we practiced. The course of events was clear. Questions arose during the audit.",
         "Questions arose during the audit.", "preposition")
    rule("wordy.throughout_the_course_of", r"(?i)\b(?P<target>throughout the course of)\b", "throughout", S, 0.75,
         "“Throughout” is shorter than “throughout the course of”.",
         "She improved throughout the course of the year.",
         "The course of the year was kind. She improved throughout the year.",
         "She improved throughout the year.", "preposition")
    rule("wordy.for_a_period_of",
         r"(?i)\b(?P<target>(?P<w>for|over|within|after) a period of)\s+(?:\d|(?:one|two|three|four|five|six|seven|eight|nine|ten|twelve|twenty|several|many|about|approximately|at least|up to|roughly|around|nearly)\b)",
         "${w}", S, 0.72,
         "Drop “a period of”: “for 30 days” says it directly.",
         "The offer runs for a period of 30 days.",
         "He rested for a period of time. It improved over a period of years. The offer runs for 30 days.",
         "The offer runs for 30 days.", "preposition")
    note("Wordy phrases", "in order to / so as to / in order for / in order that", "4 rules (`wordy.in_order_*`, `wordy.so_as_to`)")
