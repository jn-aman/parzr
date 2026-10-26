"""Verbs and adjectives with the wrong preposition, an object that must follow directly, "have" as an action verb,
and state verbs in the progressive: transfer errors that the base and preposition packs leave open."""
from lib import R

SUBJ_LEAD = (r"(?:\b(?:I|we|you|they|he|she|who|please|must|should|will|would|can|could|always|also|strongly|again|and|just)\b"
             r"(?: (?:also|again|strongly|always|really|just|must|should|will|would|can|could))* )")


def build():
    prepositions()
    doing_and_making()
    having()
    states()
    tension()


def prepositions():
    R('stress.on', rf'(?i){SUBJ_LEAD}(?P<target>(?P<v>stress(?:ed|es|ing)?) on)\b', '${v}', 'Grammar', 0.9,
      '“Stress” takes its object directly: “stress testing”, not “stress on testing”.',
      'We should stress on testing.', 'We should stress testing.',
      'The stress on the beam is high. He put stress on timing. We should stress testing.')
    lead_call = (r"(?:please|kindly|pls|plz|I will|I['’]ll|we will|we['’]ll|I shall|will you|can you|could you|would you|shall I|should I|"
                 r"can I|could I|may I|let me|let us|let['’]s|do not|don['’]t|I can|I could|I would|I['’]d|to)")
    R('call.to', rf"(?i)\b{lead_call} (?:also |just |again |then )?(?P<target>(?P<v>call|called|calling) to) (?:me|him|her|us|them|you)\b", '${v}',
      'Grammar', 0.9, 'You call a person directly: “call me”, not “call to me”.',
      'Please call to me tomorrow.', 'Please call me tomorrow.',
      'Please call me tomorrow. He called to her across the yard. A call to action went out.')
    R('married.with', r'(?i)\b(?:get|gets|got|getting|gotten) (?P<target>married with) (?:him|her|them|me|us|you|each other|someone|anyone|somebody)\b',
      'married to', 'Grammar', 0.9, 'You are “married to” someone, not “married with” them.',
      'She got married with him in May.', 'She got married to him in May.',
      'She got married to him in May. They got married with all their friends there.')
    R('keen.in', r"(?i)\b(?:am|is|are|was|were|be|been|['’]m|['’]s|['’]re|very|quite|really|so|too|not|extremely|particularly|highly|equally|also) keen (?P<target>in)\b",
      'on', 'Grammar', 0.88, '“Keen” goes with “on”: “keen on cricket”.',
      'He is keen in cricket.', 'He is keen on cricket.',
      'He is keen on cricket. She takes a keen interest in cricket.')
    R('surprised.on', r'(?i)\b(?:surprised|shocked|astonished|amazed|stunned|startled|alarmed|appalled|horrified) (?P<target>on) (?:the|this|that|these|those|my|your|his|her|their|our)\b',
      'at', 'Grammar', 0.88, 'These feelings go with “at” (or “by”): “surprised at the news”.',
      'I was surprised on the news.', 'I was surprised at the news.',
      'I was surprised at the news. She was shocked on hearing the result. He arrived on the day.')
    R('participate.on',
      r'(?i)\bparticipat(?:e|ed|es|ing) (?P<target>on) (?:the |a |an |our |my |their )?(?:quiz|contest|competition|marathon|hackathon|survey|tournament|race|game|match|drive|program|programme|training|workshop|seminar|course|exam|campaign)\b',
      'in', 'Grammar', 0.88, 'You “participate in” an event: “participate in the quiz”.',
      'I participated on the quiz last week.', 'I participated in the quiz last week.',
      'I participated in the quiz last week. She will participate on the panel. They participate on the conference call.')
    R('knowledge.on', r'(?i)\b(?:have|has|had|having|with|no|any|good|little|much|some|more|limited|basic|deep|detailed|enough|great|sufficient|working|expert|full) knowledge (?P<target>on)\b',
      'of', 'Grammar', 0.88, 'Use “knowledge of” (or “knowledge about”): “knowledge of this topic”.',
      'I have no knowledge on this.', 'I have no knowledge of this.',
      'I have no knowledge of this. The knowledge base on the wiki is useful.')
    R('access.of', r'(?i)\b(?:have|has|had|having|get|got|gets|getting|gain|gained|give|gave|giving|provide|provided|grant|granted|need|needs|needed|deny|denied|no|full|read|write|admin|remote|direct|easy|quick|free|public|restricted|limited) access (?P<target>of) (?:the|this|that|these|those|my|your|our|his|her|their|a|an|all|any)\b',
      'to', 'Grammar', 0.9, 'You have “access to” something, not “access of” it.',
      'You have access of the server.', 'You have access to the server.',
      'You have access to the server. He had an access of anger.')
    R('apply.for',
      r'(?i)\bappl(?:y|ied|ies|ying) (?P<target>on) (?:the |a |an |this |that |these |those |my |our |any |every )?(?:jobs?|positions?|posts?|vacanc(?:y|ies)|roles?|openings?|scholarships?|visas?|loans?|leaves?|passports?|internships?|admissions?|memberships?)\b',
      'for', 'Grammar', 0.9, 'You “apply for” a job or a visa: “apply for the vacancy”.',
      'I applied on the vacancy last week.', 'I applied for the vacancy last week.',
      'I applied for the vacancy last week. Apply on the skin twice a day. Apply on Monday.')
    R('apply.to', r'(?i)\bappl(?:y|ied|ies|ying) (?P<target>on) (?:the |a |an |this |that |my |our |any |every |two |three |four |five |\d+ )?(?:colleges?|universit(?:y|ies)|schools?|programs?|programmes?|courses?)\b',
      'to', 'Grammar', 0.9, 'You “apply to” a college or a programme: “apply to the university”.',
      'She applied on three universities.', 'She applied to three universities.',
      'She applied to three universities. Apply on the skin twice a day.')
    R('disagree.to', r'(?i)\bdisagree(?:d|s)? (?P<target>to) (?:this|that|your|his|her|their|our|my|the|these|those|it|him|them|you|me|us)\b',
      'with', 'Grammar', 0.88, 'You “disagree with” someone or something: “disagree with this”.',
      'I disagree to your point.', 'I disagree with your point.',
      'I disagree with your point. I disagree to some extent. We agree to disagree.')
    R('key.of', r'(?i)\bthe key (?P<target>of) (?:success|happiness|growth|winning|victory|prosperity|health|longevity|learning|life|good|great|better|effective|healthy)\b',
      'to', 'Grammar', 0.88, 'You use “the key to” something: “the key to success”.',
      'The key of success is practice.', 'The key to success is practice.',
      'The key to success is practice. The key of C major is bright.')
    R('attend.to', r'(?i)\battend(?:ed|ing|s)? (?P<target>to )(?:the |a |an |my |our |this |that |your |his |her |their )?(?:meeting|conference|webinar|training|seminar|workshop|wedding|class|classes|session|party|event|function|interview|lecture|exam|ceremony|funeral|concert)\b',
      '', 'Grammar', 0.88, 'You “attend” an event directly: “attend the meeting”. “Attend to” means to take care of something.',
      'I will attend to the meeting tomorrow.', 'I will attend the meeting tomorrow.',
      'I will attend the meeting tomorrow. I will attend to the customer first. He attends to the patients.')
    R('go.for_activity',
      r'(?i)\b(?P<target>(?P<v>go|goes|going|went|gone) for) (?:shopping|swimming|dancing|fishing|hiking|camping|skiing|sailing|sightseeing|trekking|cycling|jogging|running|biking|boating|clubbing)(?:[.,;!?]|$| (?:on|in|at|with|this|next|tomorrow|today|tonight|every|after|before|and|to|during|last|yesterday|from|now|then|later|soon))',
      '${v}', 'Grammar', 0.88, 'Say “go shopping” or “go swimming”; “for” is not needed before an “-ing” activity.',
      'Let us go for shopping this evening.', 'Let us go shopping this evening.',
      'Let us go shopping this evening. We went for a swim. I will go for running shoes.')


def doing_and_making():
    det = (r"(?:a |an |some |many |any |no |few |a few |several |such |same |the same |so many |too many |more |"
           r"(?:silly|small|big|bad|serious|stupid|careless|costly|common|simple|basic|grave|terrible|same) )")
    why = 'You “make” a mistake; you do not “do” one.'
    neg = ('Please do not make the same mistake again. What did they do about the mistake? We do our best. Why do these mistakes occur? '
           'Why did these mistakes happen? Did you do the mistakes on purpose?')
    leads = [
        ('mistake.do', 'do', 'make', r"(?:\b(?:to|will|would|can|could|should|must|may|might|not|never|please|just|always|often|keep|stop|avoid|try|want|need|let's|and|or|I|we|they|you)|n['’]t) (?:not |never |also |again |ever |really )?",
         'Please do not do the same mistake again.', 'Please do not make the same mistake again.'),
        ('mistake.does', 'does', 'makes', r'\b(?:he|she|it|who|someone|somebody|everyone|everybody|nobody|one) (?:also |often |always |never |just |really )?',
         'He does a mistake every day.', 'He makes a mistake every day.'),
        ('mistake.did', 'did', 'made', r'\b(?:I|he|she|we|they|you|who|someone|somebody) (?:also |often |always |never |just |really |once |again )?',
         'I did a mistake in the report.', 'I made a mistake in the report.'),
        ('mistake.doing', 'doing', 'making', r'\b(?:am|is|are|was|were|be|been|keep|kept|stop|avoid|without|by|of|for) (?:also |often |always |just |really )?',
         'She is doing many mistakes.', 'She is making many mistakes.'),
        ('mistake.done', 'done', 'made', r"\b(?:have|has|had|having|I['’]ve|we['’]ve|you['’]ve|they['’]ve) (?:also |often |always |never |just |really |already )?",
         'I have done a mistake.', 'I have made a mistake.'),
    ]
    for rid, word, rep, lead, pos, exp in leads:
        R(rid, rf'(?i){lead}(?P<target>{word}) {det}mistakes?\b', rep, 'Word choice', 0.9, why, pos, exp, neg)
    for rid, word, rep, pos, exp in [
        ('photo.make', 'make', 'take', 'Can I make a photo of the invoice?', 'Can I take a photo of the invoice?'),
        ('photo.made', 'made', 'took', 'She made some selfies there.', 'She took some selfies there.'),
        ('photo.making', 'making', 'taking', 'He is making photos of the stage.', 'He is taking photos of the stage.'),
        ('photo.makes', 'makes', 'takes', 'He makes a selfie here.', 'He takes a selfie here.'),
    ]:
        R(rid, rf'(?i)\b(?P<target>{word}) (?:a |some |my |your |our |his |her |two |many |a few |three )?(?:photos?|selfies?)(?:[.,;!?]|$| (?:of|with|at|in|and|on|for|there|here|now|today|together|again)\b)', rep, 'Word choice', 0.85,
          'You “take” a photo or a selfie; you do not “make” one.', pos, exp,
          'Can I take a photo of the invoice? They make photo frames. She made a video.')


HAVE_NOUNS = (r'car|cars|house|brothers?|sisters?|sons?|daughters?|kids|children|dogs?|cats?|laptops?|bikes?|scooters?|motorcycles?|bungalows?|villas?|farms?|shops?|'
              r'business|degrees?|diplomas?|licen[cs]es?|passports?|accounts?|desktops?|phones?|mobiles?|tablets?|cameras?|watch|plots?|gardens?|offices?|wife|'
              r'husband|girlfriend|boyfriend|managers?|partners?|PC|TV|fridge|apartments?')
HAVE_FOLLOW = r'(?:[.,;!?]|$| (?:in|at|with|from|since|for|and|but|which|that|so|because|these days|now|also|too|of)\b)'


def having():
    adj = r'(?: (?:[a-z]+))?'
    R('having.possession_plural',
      rf"(?im)(?:^|[.!?,;]\s+|\b(?:and|but|so) )(?P<target>(?P<s>I|we|they|you) (?:am|are|['’]m|['’]re) having) (?:a|an|one|two|three|four|five|no|many|some){adj} (?:{HAVE_NOUNS}){HAVE_FOLLOW}",
      '${s} have', 'Word choice', 0.88, 'For owning something, use “have”, not “am having”: “I have a car”.',
      'I am having a red bike at home.', 'I have a red bike at home.',
      'I am having a red bike delivered. I have a red bike at home. We are having a car show.')
    R('having.possession_third',
      rf"(?im)(?:^|[.!?,;]\s+|\b(?:and|but|so) )(?P<target>(?P<s>he|she) (?:is|['’]s) having) (?:a|an|one|two|three|four|five|no|many|some){adj} (?:{HAVE_NOUNS}){HAVE_FOLLOW}",
      '${s} has', 'Word choice', 0.88, 'For owning something, use “has”, not “is having”: “She has a car”.',
      'She is having a nice car.', 'She has a nice car.',
      'She is having a new car delivered. She has a nice car.')
    R('having.experience',
      r"(?i)\b(?P<target>(?P<s>I|we|they|you) (?:am|are|['’]m|['’]re) having) (?:over |more than |around |nearly |about |almost )?(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty)\+? years? (?:of )?(?:experience|exp)\b",
      '${s} have', 'Word choice', 0.9, 'Experience is something you “have”, not “am having”: “I have five years of experience”.',
      'I am having five years of experience in sales.', 'I have five years of experience in sales.',
      'I have five years of experience in sales. We are having a meeting about experience.')
    R('having.experience_third',
      r"(?i)\b(?P<target>(?P<s>he|she) (?:is|['’]s) having) (?:over |more than |around |nearly |about |almost )?(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty)\+? years? (?:of )?(?:experience|exp)\b",
      '${s} has', 'Word choice', 0.9, 'Experience is something you “have”, not “is having”: “She has five years of experience”.',
      'She is having five years of experience in sales.', 'She has five years of experience in sales.',
      'She has five years of experience in sales. He is having a call about experience.')
    sick = r'(?:fever|headache|cold|cough|toothache|backache|stomachache|stomach ache|migraine|sore throat|rash|temperature)'
    mass = r'(?:back pain|body pain|chest pain|stomach pain|leg pain|joint pain|diarrh(?:o)?ea|nausea|asthma)'
    R('having.illness_plural', rf"(?i)\b(?P<target>(?P<s>I|we|they|you) (?:am|are|['’]m|['’]re) having) {sick}\b", '${s} have a', 'Verb form', 0.9,
      'For an illness, use “have a”: “I have a fever”.', 'I am having fever today.', 'I have a fever today.',
      'I have a fever today. I am having a fever now.')
    R('having.illness_third', rf"(?i)\b(?P<target>(?P<s>he|she) (?:is|['’]s) having) {sick}\b", '${s} has a', 'Verb form', 0.9,
      'For an illness, use “has a”: “She has a fever”.', 'She is having headache today.', 'She has a headache today.',
      'She has a headache today. She is having a headache now.')
    R('having.pain_plural', rf"(?i)\b(?P<target>(?P<s>I|we|they|you) (?:am|are|['’]m|['’]re) having) {mass}\b", '${s} have', 'Verb form', 0.9,
      'For an illness or pain, use “have”: “I have back pain”.', 'I am having back pain.', 'I have back pain.',
      'I have back pain. I am having a good day.')
    R('having.pain_third', rf"(?i)\b(?P<target>(?P<s>he|she) (?:is|['’]s) having) {mass}\b", '${s} has', 'Verb form', 0.9,
      'For an illness or pain, use “has”: “She has back pain”.', 'She is having chest pain.', 'She has chest pain.',
      'She has chest pain. She is having a good day.')
    R('having.not_object',
      r"(?i)\b(?P<target>(?P<s>I|we|they|you) (?:am|are|['’]m|['’]re) not having) (?:any )?(?:time|idea|clue|access|permission|network|signal|internet|data|bandwidth|budget|knowledge|information|authority|option|choice|money|cash|laptop|car|bike|phone)\b",
      '${s} do not have', 'Verb form', 0.9, 'For possession, use “do not have”, not “am not having”: “I do not have time”.',
      'I am not having time today.', 'I do not have time today.',
      'I do not have time today. I am not having it. We are not having a meeting today.')
    R('having.not_object_third',
      r"(?i)\b(?P<target>(?P<s>he|she) (?:is|['’]s) not having) (?:any )?(?:time|idea|clue|access|permission|network|signal|internet|data|bandwidth|budget|knowledge|information|authority|option|choice|money|cash|laptop|car|bike|phone)\b",
      '${s} does not have', 'Verb form', 0.9, 'For possession, use “does not have”, not “is not having”: “She does not have time”.',
      'She is not having time today.', 'She does not have time today.',
      'She does not have time today. She is not having it. He is not having a meeting today.')


def states():
    why = 'Verbs of knowing and liking do not take the progressive: say “I do not understand”, not “I am not understanding”.'
    plain = r'understand|know|want|need|prefer'
    edrop = r'believ|lik|hat'
    plural_aux = r"(?: am not| are not| aren['’]t|['’]m not|['’]re not)"
    third_aux = r"(?: is not| isn['’]t|['’]s not)"
    R('stative.not_plain', rf"(?i)\b(?P<target>(?P<s>I|we|you|they){plural_aux} (?P<v>{plain})ing)\b", '${s} do not ${v}', 'Verb form', 0.88, why,
      'I am not understanding this.', 'I do not understand this.', 'I do not understand this. We are not at home.')
    R('stative.not_plain_third', rf"(?i)\b(?P<target>(?P<s>he|she|it){third_aux} (?P<v>{plain})ing)\b", '${s} does not ${v}', 'Verb form', 0.88, why,
      'She is not knowing the answer.', 'She does not know the answer.', 'She does not know the answer. She is not at home.')
    R('stative.not_edrop', rf"(?i)\b(?P<target>(?P<s>I|we|you|they){plural_aux} (?P<v>{edrop})ing)\b", '${s} do not ${v}e', 'Verb form', 0.88, why,
      'I am not liking this place.', 'I do not like this place.', 'I do not like this place. We are not at the place.')
    R('stative.not_edrop_third', rf"(?i)\b(?P<target>(?P<s>he|she|it){third_aux} (?P<v>{edrop})ing)\b", '${s} does not ${v}e', 'Verb form', 0.88, why,
      'He is not believing the story.', 'He does not believe the story.', 'He does not believe the story. He is not at home.')


def tension():
    why = '“Tension” is not the usual word for stress or worry in English; say “stress” or “worry”.'
    lead = (r"(?:\b(?:I|you|we|they|he|she|who|please|don['’]t|do not|never|why|stop|just|also|always|no need to|need not|not to|without)\b"
            r"(?: (?:also|just|always|really|ever|even|do|did|does|are|is|am|will|would|should|can|could))* )")
    tail = r"(?:[.,;!?]|$| (?:about|for|on|over|of|regarding|from|yaar|na|dude|bro|man|because|if|when|so)\b)"
    for rid, word, rep, pos, exp in [
        ('tension.take', 'take', 'worry', "Don't take tension about the exam.", "Don't worry about the exam."),
        ('tension.taking', 'taking', 'worrying', 'Why are you taking tension?', 'Why are you worrying?'),
        ('tension.took', 'took', 'worried', 'She took so much tension about it.', 'She worried about it.'),
        ('tension.takes', 'takes', 'worries', 'He takes too much tension about work.', 'He worries about work.'),
    ]:
        R(rid, rf"(?i){lead}(?P<target>{word} (?:so much |any |too much |much |more |a lot of |lots of |unnecessary )?tension){tail}", rep, 'Register', 0.72, why, pos, exp,
          'The cable takes tension. Please take the tension out of the rope. We took the call about it.')
    R('tension.in', r"(?i)\b(?:I am|I['’]m|we are|we['’]re|you are|you['’]re|he is|he['’]s|she is|she['’]s|they are|they['’]re) (?P<target>in (?:so much |too much |a lot of |lots of |very much )?tension)(?:[.,;!?]|$| (?:about|for|on|over|of|because|since|as|due|right now|today|these days|before|after))",
      'stressed', 'Register', 0.72, why, 'I am in tension about the exam.', 'I am stressed about the exam.',
      'The two countries are in tension. I am stressed about the exam. The rope is in tension.')
    R('tension.give', r"(?i)\b(?:give|gives|gave|giving|given) (?:me|us|him|her|them|you) (?:so much |a lot of |lots of |too much |more |extra |unnecessary )?(?P<target>tension)\b",
      'stress', 'Register', 0.72, why, 'He is giving me so much tension.', 'He is giving me so much stress.',
      'He is giving me so much stress. The rope gives it tension. They gave us tickets.')
    R('tension.no', r"(?im)(?:^|[.!?]\s+)(?P<target>no tension)(?:[.!,]|$)", 'no worries', 'Register', 0.7, why,
      'No tension, I will handle it.', 'No worries, I will handle it.',
      'No worries, I will handle it. There was no tension in the room.')
