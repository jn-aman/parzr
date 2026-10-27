"""Phrasing that Hindi and other L1 writers carry into work English: polite-form pile-ups, "the same" as a pronoun,
extra words after a verb, and fixed phrases."""
from lib import R

KV = ('send|share|confirm|let|find|check|review|update|advise|inform|provide|forward|arrange|approve|acknowledge|note|look|have|take|ensure|'
      'do|help|bear|give|reply|respond|attend|join|come|cooperate|co-operate|consider|clarify|get|make|see|visit|ignore|excuse|accept|go|put|'
      'keep|use|process|release|issue|complete|submit|fill|sign|return|pay|clear|read|mark|add|include|attach|elaborate|explain|resend|schedule|book|'
      'revert|call|contact|mail|email|tell|show|bring|hold|wait|proceed|verify|validate|refer|extend|grant|permit|allow|suggest|guide|support')
KV_SHORT = ('send|share|confirm|let|find|check|review|update|advise|inform|provide|forward|arrange|approve|note|look|take|ensure|do|help|bear|give|'
            'reply|respond|attend|join|come|consider|clarify|get|make|see')


def build():
    polite()
    wrong_extras()
    fixed_phrases()


def polite():
    R('kindly.imperative', rf'(?im)(?:^|[.!?,]\s+|\band\s+)(?P<target>kindly)\s+(?:{KV})\b', 'please', 'Register', 0.66,
      '“Kindly” sounds formal or old-fashioned in most English; “please” is the usual way to ask.',
      'Kindly send me the signed copy.', 'Please send me the signed copy.',
      'Would you kindly send me the signed copy? She kindly sent me the copy. Please send me the signed copy.')
    R('kindly.please_kindly', rf'(?i)\b(?P<target>please kindly) (?:{KV_SHORT})\b', 'please', 'Redundancy', 0.8,
      '“Please” and “kindly” both ask politely. One is enough.',
      'Please kindly share the report.', 'Please share the report.', 'Please share the report. She was kind to share the report.')
    R('kindly.kindly_please', rf'(?i)\b(?P<target>kindly please) (?:{KV_SHORT})\b', 'please', 'Redundancy', 0.8,
      '“Kindly” and “please” both ask politely. One is enough.',
      'Kindly please confirm the date.', 'Please confirm the date.', 'Please confirm the date. She is kind to confirm it.')
    obj = r'(?:you|all|everyone|everybody|him|her|them|the team|team)'
    R('request.please', rf'(?i)\brequest(?:s|ed|ing)? {obj} (?P<target>to please) \w', 'to', 'Redundancy', 0.8,
      '“Request” already asks politely. “Please” is not needed after it.',
      'I request you to please send the file.', 'I request you to send the file.',
      'I request you to send the file. Please send the file. They asked me to please wait.')
    R('request.kindly', rf'(?i)\brequest(?:s|ed|ing)? {obj} (?P<target>to kindly) \w', 'to', 'Redundancy', 0.68,
      '“Request” already asks politely. “Kindly” is not needed after it.',
      'I request you to kindly share the file.', 'I request you to share the file.',
      'I kindly request you to share the file. I request you to share the file.')
    R('request.start', r'(?im)(?:^|[.!?]\s+)(?P<target>request you to)\b', 'I request you to', 'Style', 0.7,
      'A sentence needs a subject: “I request you to …” (or simply “Please …”).',
      'Request you to share the report.', 'I request you to share the report.',
      'I request you to share the report. We request you to share the report.')
    R('request.kindly_start', r'(?im)(?:^|[.!?]\s+)(?P<target>kindly request you to)\b', 'I kindly request you to', 'Style', 0.7,
      'A sentence needs a subject: “I kindly request you to …” (or simply “Please …”).',
      'Kindly request you to share the report.', 'I kindly request you to share the report.',
      'I kindly request you to share the report. Please share the report.')
    R('same.pronoun',
      r'(?i)\b(?:find|check|checked|checking|verify|verified|review|reviewed|reviewing|confirm|confirmed|confirming|share|shared|sharing|send|sent|sending|forward|forwarded|forwarding|attach|attached|attaching|resend|approve|approved|submit|submitted|sign|signed|process|processed|arrange|arranged|provide|provided|providing|update|updated|updating|acknowledge|acknowledged) (?P<target>the same)(?:[.,;!?)]|$| (?:attached|enclosed|herewith|below|again|and|please|asap|by|before|after|once|today|tomorrow)\b)',
      'it', 'Style', 0.68, '“The same” is not a pronoun in everyday English. Say “it” (or “them” for more than one thing).',
      'Please find the same attached.', 'Please find it attached.',
      'Please send the same message again. Please do the same. I use the same laptop. Check the same boxes. We will confirm the same price.')
    R('herewith.attached', r'(?i)\b(?P<target>herewith )attached\b', '', 'Redundancy', 0.75,
      '“Herewith” and “attached” say the same thing. “Please find attached” is enough.',
      'Please find herewith attached the report.', 'Please find attached the report.',
      'Please find the report attached herewith. Please find attached the report.')


def wrong_extras():
    R('discuss.about_all',
      r'(?i)\bdiscuss(?:ed|es|ing)? (?P<target>about )(?:everything|anything|something|nothing|next|further|some|us|you|me)\b',
      '', 'Grammar', 0.93, '“Discuss” takes its object directly: “discuss everything”, not “discuss about everything”.',
      'We discussed about everything yesterday.', 'We discussed everything yesterday.',
      'We discussed everything yesterday. We talked about everything yesterday. They argued about what to do.')
    R('discuss.about_noun',
      r'(?i)\bdiscuss(?:ed|es|ing)? (?P<target>about )(?:(?-i:[A-Z][A-Za-z0-9]*)|(?:budget|project|projects|timeline|targets?|roadmap|requirements?|features?|bugs?|tasks?|deadlines?|pricing|salary|hiring|strategy|priorities|goals?|results?|progress|changes|updates?|concerns|questions|problems?|topics?|matters?|proposals?|plans?|ideas?|details|terms|rates|costs?|policy|policies|process|processes|schedule|release|launch|marketing|sales|finances|payments?|training|leave|performance|promotion|expectations)\b)',
      '', 'Grammar', 0.93, '“Discuss” takes its object directly: “discuss Q3 targets”, not “discuss about Q3 targets”.',
      'Let us discuss about Q3 targets.', 'Let us discuss Q3 targets.',
      'Let us discuss Q3 targets. We talked about the budget. They disagreed about 20 items in the list.')
    R('discuss.on',
      r'(?i)\bdiscuss(?:ed|es|ing)? (?P<target>on )(?:it|them|everything|all|those|these|which|what|how|why|whether|(?:the |this |that |these |those |our |your |my |their |his |her |a |an |some |all |each |every )?(?:matter|issue|topic|subject|proposal|plan|idea|agenda|point|points|problem|problems|requirements?|details?|findings|results|options|strategy|progress|status|changes|budget|timeline|schedule))\b',
      '', 'Grammar', 0.9, '“Discuss” takes its object directly: “discuss the issue”, not “discuss on the issue”.',
      'We discussed on this issue yesterday.', 'We discussed this issue yesterday.',
      'We discussed this issue yesterday. Let us discuss on Monday. We can discuss on a call.')
    R('inform.to', r'(?i)\binform(?:ed|ing|s)? (?P<target>to )(?:me|him|her|us|them|you|everyone|all|the|your|our|his|their|my)\b',
      '', 'Grammar', 0.9, '“Inform” takes the person directly: “inform the team”, not “inform to the team”.',
      'Please inform to the team about it.', 'Please inform the team about it.',
      'Please inform the team about it. We reported it to the team. She sent the details to me.')
    R('ask.that_wh', r'(?i)\b(?:ask|asks|asked|asking|wonder|wonders|wondered|wondering|enquire|enquired|inquire|inquired)(?: (?:me|him|her|them|us|you))? (?P<target>that )(?:where|why|how|when|who|whom|whether|if)\b',
      '', 'Grammar', 0.9, 'After “ask”, the question word follows directly: “asked me why”, not “asked me that why”.',
      'She asked me that where I live.', 'She asked me where I live.',
      'She asked me where I live. He asked that we leave early. I asked him that morning why he left.')
    R('order.for_item',
      r"(?i)\b(?:I|we|let['’]s|to|will|shall|can|could|would|should|please|just|also|already|then|want to|wanted to|need to|needs to) (?:also |just |already |then |will |would )?order(?:ed|ing)? (?P<target>for )(?:a|an|the|some|two|three|\d+)(?: [a-z]+)? (?:pizzas?|burgers?|biryanis?|sandwich(?:es)?|laptops?|phones?|books?|cakes?|coffees?|dosas?|noodles|fries|tickets?|chairs?|desks?|monitors?|keyboards?|cabs?|cars?)\b",
      '', 'Grammar', 0.88, 'You order a thing directly: “order a pizza”. “Order for” means ordering on someone’s behalf.',
      'I will order for a pizza tonight.', 'I will order a pizza tonight.',
      'I will order a pizza tonight. I ordered for a friend yesterday. Is there an order for a pizza?')
    R('able.didnt', r'(?i)\b(?P<target>did not able to)\b', 'could not', 'Grammar', 0.93, 'After “did not”, use the plain verb: “could not attend”.',
      'I did not able to attend.', 'I could not attend.', 'I could not attend. I was not able to attend.')
    R('able.didnt_contr', r"(?i)\b(?P<target>didn(?P<a>['’])t able to)\b", 'couldn${a}t', 'Grammar', 0.93,
      'After “didn’t”, use the plain verb: “couldn’t attend”.',
      "I didn't able to attend.", "I couldn't attend.", "I couldn't attend. I wasn't able to attend.")
    R('able.dont', r"(?i)\b(?P<target>(?:do not|does not) able to)\b", 'cannot', 'Grammar', 0.93, 'Use “cannot” or “is not able to”: “I cannot attend”.',
      'He does not able to come.', 'He cannot come.', 'He cannot come. He is not able to come.')
    R('able.dont_contr', r"(?i)\b(?P<target>(?:don|doesn)(?P<a>['’])t able to)\b", 'can${a}t', 'Grammar', 0.93, 'Use “can’t” or “isn’t able to”: “I can’t attend”.',
      "He doesn't able to come.", "He can't come.", "He can't come. He isn't able to come.")
    R('very.less_count',
      r'(?i)\b(?P<target>very less) (?:people|users|students|employees|customers|clients|members|items|files|options|choices|cases|days|hours|minutes|tickets|issues|bugs|errors|mistakes|times|friends|marks|candidates|seats|openings|jobs|resources)\b',
      'very few', 'Grammar', 0.9, 'With things you can count, say “few”: “very few people”.',
      'There are very less people here.', 'There are very few people here.',
      'There are very few people here. There are far fewer people here. We have less time.')
    R('very.less_mass',
      r'(?i)\bvery (?P<target>less) (?:time|money|information|data|work|space|memory|budget|effort|experience|knowledge|chance|scope|difference|use|value|importance|sleep|food|water|traffic)\b',
      'little', 'Grammar', 0.9, 'With things you cannot count, say “little”: “very little time”.',
      'I have very less time today.', 'I have very little time today.',
      'I have very little time today. I have less time today. We spent much less money.')
    R('very.much_adj',
      r'(?i)\bvery (?P<target>much )(?:happy|glad|sorry|tired|busy|angry|hungry|sad|sure|scared|nervous|proud|thankful|grateful|keen|good|bad|big|small|late|early|fast|slow|easy|hard|difficult|important|useful|helpful|clear)\b',
      '', 'Grammar', 0.88, 'Use “very” alone before an adjective: “very tired”. “Very much” goes with verbs.',
      'I am very much tired today.', 'I am very tired today.',
      'I am very tired today. I like it very much. Thank you very much.')


def fixed_phrases():
    R('mostofthetimes', r'(?i)\bmost of the (?P<target>times)(?:[.,;!?]|$| (?:and|but)\b)', 'time', 'Grammar', 0.88,
      '“Most of the time” is singular: “most of the time”, not “most of the times”.',
      'Most of the times, the build passes.', 'Most of the time, the build passes.',
      'Most of the time, the build passes. At most of the times we met, he was late.')
    R('nexttonext', r'(?i)\b(?P<target>next to next (?P<u>week|month|year))\b', 'the ${u} after next', 'Register', 0.75,
      '“Next to next week” is mainly Indian usage; say “the week after next”.',
      'We will meet next to next week.', 'We will meet the week after next.',
      'We will meet the week after next. We will meet next week.')
