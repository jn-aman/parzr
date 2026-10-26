"""Indian-English and other L1 vocabulary that is plain in one community and unclear elsewhere: Register suggestions
at 0.75 or below (README policy), each with the standard form beside it."""
from lib import R


def build():
    needful()
    prepone()
    revert()
    introductions()
    places_and_people()
    doubts()
    things()
    appliances_exams_leave()
    set_phrases()


# ---------------------------------------------------------------- do the needful
def needful():
    why = 'In English, “do the needful” is mainly Indian usage and sounds vague. Say what is needed.'
    neg = 'Only the needful items are in the box. Do the dishes before you leave. She did the work well.'
    for rid, pat, rep, pos, exp in [
        ('needful.do', r'\b(?P<target>(?P<v>do|does) (?:the )?needful)\b', '${v} what is needed',
         'Please do the needful by Friday.', 'Please do what is needed by Friday.'),
        ('needful.did', r'\b(?P<target>did (?:the )?needful)\b', 'did what was needed',
         'I did the needful yesterday.', 'I did what was needed yesterday.'),
        ('needful.doing', r'\b(?P<target>doing (?:the )?needful)\b', 'doing what is needed',
         'We are doing the needful at our end.', 'We are doing what is needed at our end.'),
        ('needful.done', r'\b(?P<target>done (?:the )?needful)\b', 'done what was needed',
         'I have done the needful.', 'I have done what was needed.'),
    ]:
        R(rid, '(?i)' + pat, rep, 'Register', 0.72, why, pos, exp, neg)
    R('needful.adjective',
      r'(?i)\b(?:the |all |any |every )?(?P<target>needful) (?:action|steps?|measures?|help|assistance|support|documents?|information|details|changes|approvals?)\b',
      'necessary', 'Register', 0.72, '“Needful” as an adjective is old-fashioned or Indian usage; “necessary” is the common word.',
      'Please take the needful action today.', 'Please take the necessary action today.',
      'The necessary action is already taken. We need full details soon.')


# ---------------------------------------------------------------- prepone
def prepone():
    why = '“Prepone” is understood mainly in India. “Move up” or “bring forward” is clear everywhere.'
    forms = [('prepone', 'move', 'move up', 'We should prepone the meeting to 3 pm.', 'We should move up the meeting to 3 pm.',
              'We should prepone it to 3 pm.', 'We should move it up to 3 pm.'),
             ('preponed', 'moved', 'moved up', 'The meeting was preponed to Monday.', 'The meeting was moved up to Monday.',
              'They preponed it to Monday.', 'They moved it up to Monday.'),
             ('preponing', 'moving', 'moving up', 'Preponing the launch helps us.', 'Moving up the launch helps us.',
              'Preponing it helps us.', 'Moving it up helps us.'),
             ('prepones', 'moves', 'moves up', 'She prepones the call every week.', 'She moves up the call every week.',
              'She prepones it every week.', 'She moves it up every week.')]
    neg = 'We will postpone the meeting to Friday. Can we bring the launch forward? She moves up the schedule.'
    for word, stem, rep, p1, e1, p2, e2 in forms:
        wrx = word.replace('prepone', 'pre-?pone').replace('prepon', 'pre-?pon')
        R(f'prepone.obj.{word}', rf'(?i)\b(?P<target>{wrx} (?P<o>it|them|this|that))\b', stem + ' ${o} up', 'Register', 0.74, why, p2, e2, neg)
        R(f'prepone.{word}', rf'(?i)\b(?P<target>{wrx})\b', rep, 'Register', 0.72, why, p1, e1, neg)


# ---------------------------------------------------------------- revert
REPLY_NOUN = (r'(?:the |my |our |a |an |your |more |further |some |any |an updated |the updated |the final |a final |the revised |a revised )?'
              r'(?:update|details|numbers|comments|feedback|answer|response|reply|inputs?|findings|status|suggestions?|proposal|quote|'
              r'estimate|confirmation|options|clarification|timeline|plan)')
REVERT_TAIL = (r'(?: (?:by|asap|soon|shortly|at the earliest|tomorrow|today|latest|once|after|before|within)\b'
               r'| with ' + REPLY_NOUN + r'\b'
               r'| on (?:this|that|it|these|those|the same|the above|your (?:mail|email|query|request|question|message))'
               r'(?:[.,;!?]|$| (?:by|tomorrow|today|soon|asap|shortly|once|after|before|and|within|at)\b))')


def revert():
    why = 'In English, “revert” means go back to an earlier state. To answer someone, say “reply” or “get back to you”.'
    neg = ('We will revert the change if the build fails. You can revert to the old version with git. The server reverted to defaults. '
           'I am reverting the commit now. Please revert the last commit.')
    lead_base = r'(?:\b(?:I|we)(?:[\'’](?:ll|d))?(?: (?:will|shall|would|can|could|also|then|soon|just|kindly|please))* |\b(?:please|kindly|pls|plz) (?:do )?|\b(?:can|could|would|will) you (?:please |kindly )?)'
    lead_past = r'\b(?:I|we|he|she|they|you|who|and|then|but)(?: (?:also|then|just|already|promptly|finally|quickly|has|have|had))* '
    lead_ing = r'\b(?:I|we|he|she|they|you) (?:am|is|are|was|were) '
    for rid, word, lead, rep, pos, exp in [
        ('revert.reply', 'revert', lead_base, 'reply', 'I will revert by Friday with the numbers.', 'I will reply by Friday with the numbers.'),
        ('revert.reply_past', 'reverted', lead_past, 'replied', 'He reverted with the final quote.', 'He replied with the final quote.'),
        ('revert.reply_ing', 'reverting', lead_ing, 'replying', 'We are reverting with the updated plan.', 'We are replying with the updated plan.'),
    ]:
        R(rid, rf'(?i){lead}(?P<target>{word}(?: back)?){REVERT_TAIL}', rep, 'Register', 0.74, why, pos, exp, neg)
    R('revert.noun',
      r'(?i)\b(?:(?:awaiting|await|waiting for|pending|expecting|expect) (?:your|an early|a quick|a prompt|your early|your quick|your prompt)|(?:thanks for|thank you for|appreciate|sorry for|apologies for|apologize for|apologise for) (?:your|an|a|the) (?:early|quick|prompt|speedy|fast|timely|detailed|late|delayed)) (?P<target>revert)(?:[.,;!?]|$| (?:on|at|by|regarding|soon|asap|and|so|before|from))',
      'reply', 'Register', 0.72, 'A “revert” is a return to an earlier state; for an answer to a message, say “reply”.',
      'Awaiting your revert on this.', 'Awaiting your reply on this.',
      'Thanks for your revert of the faulty commit. The release is pending your review. Thank you for your quick reply. Use this for a revert. Sorry for the revert.')
    R('revert.back_state',
      r'(?i)\b(?P<target>(?P<v>revert(?:ed|ing|s)?) back) to (?:the |its |their |a |an |our |my |your )?(?:previous|original|old|default|earlier|last|prior|former|initial|normal|base|stable|working|known|main|master|v?\d|version|state|setting|settings|config|commit|branch|snapshot|backup|checkpoint|baseline)\b',
      '${v}', 'Redundancy', 0.8, '“Revert” already means go back, so “back” is not needed.',
      'You can revert back to the previous version.', 'You can revert to the previous version.',
      'You can revert to the previous version. Please reply back to the team when you are ready.')


# ---------------------------------------------------------------- self-introductions and polite forms
def introductions():
    name = r'(?-i:[A-Z][a-z]{2,}(?: [A-Z][a-z]{2,})?)'
    # No bare comma: "Myself Rahul, I am new" would become "I am Rahul, I am new", which the run-on pass then splits; the
    # everyday set accepts that sentence as typed, so the rule waits for a word that the fix cannot turn into a run-on.
    foll = r'(?:,? (?:from|and|here|working|is|a|an|the|currently|as|in|at|calling|writing|speaking|of|new)\b)'
    why = 'Introduce yourself with “I am …” or “My name is …”; “myself” cannot be the subject.'
    R('myself.name_start', rf'(?im)(?:^|[.!?]\s+)(?P<target>myself) {name}{foll}', 'I am', 'Grammar', 0.9, why,
      'Myself Aman, working as an engineer.', 'I am Aman, working as an engineer.',
      'Myself, I prefer tea. I did it myself. Myself and Ravi are in the team. Please introduce yourself. I will do it by myself.')
    R('myself.name_comma',
      rf'(?im)\b(?:hello|hi|hey|dear \w+|good (?:morning|afternoon|evening)|sir|madam|team|all|everyone),\s+(?P<target>myself) {name}{foll}',
      'I am', 'Grammar', 0.9, why,
      'Hello sir, myself Ravi from the sales team.', 'Hello sir, I am Ravi from the sales team.',
      'Hello sir, I am Ravi from the sales team. Hi team, I did it myself.')
    ask = (r"(?:what(?: is|['’]s)|(?:may|can|could|would) I (?:please |kindly )?(?:know|have|get|ask)|tell (?:me|us)|share|give (?:me|us)"
           r"|enter|mention|write|type)")
    R('goodname.ask', rf"(?i)\b{ask} your (?P<target>good )name\b", '', 'Register', 0.72,
      'Asking for “your good name” is mainly Indian usage; “your name” is the plain question.',
      'May I know your good name?', 'May I know your name?',
      'Protect your good name at work. He built a good name for the firm. What is your name?')
    R('goodname.please', r"(?i)\byour (?P<target>good )name,? (?:please|sir|madam|ma['’]am)\b", '', 'Register', 0.72,
      'Asking for “your good name” is mainly Indian usage; “your name” is the plain question.',
      'Your good name please?', 'Your name please?', 'Your good name matters to us. Your name please?')
    R('goodself', r'(?i)\b(?P<target>your good ?self)\b', 'you', 'Register', 0.7,
      '“Your good self” is an old formal way of saying “you”; plain “you” is clearer.',
      'We request your goodself to approve it.', 'We request you to approve it.',
      'Take care of your good name. Look after yourself. We thank you for your help.')
    R('respected',
      r'(?m)^(?P<target>Respected)\s+(?:Sir|Sirs|Madam|Mam|Ma[\'’]am|Team|All|Professor|Prof\.?|Principal|Teacher|Mr\.?|Mrs\.?|Ms\.?|Dr\.?|Miss|Manager)\b',
      'Dear', 'Register', 0.72, 'Open an email with “Dear …”; “Respected Sir” is mainly Indian usage.',
      'Respected Sir, I am writing about the leave.', 'Dear Sir, I am writing about the leave.',
      'Dear Sir, I am writing about the leave. He is a respected doctor. Respected members of the board will attend.')
    R('mailid',
      r'(?i)\b(?:your|my|his|her|their|our|the|official|personal|correct|new|old|same|another|this|that|a|an|valid|work|office|company) (?P<target>e?-?mail ?id)\b',
      'email address', 'Register', 0.72, '“Mail id” is mainly Indian usage; “email address” is the standard term.',
      'Please send it to my mail id.', 'Please send it to my email address.',
      'Please send it to my email address. Show your ID at the desk. Did you mail it?')
    R('mailids',
      r'(?i)\b(?:your|my|his|her|their|our|the|official|personal|correct|new|old|valid|work|office|company|these|those|both|all|two|three|\d+) (?P<target>e?-?mail ids)\b',
      'email addresses', 'Register', 0.72, '“Mail ids” is mainly Indian usage; “email addresses” is the standard term.',
      'Please share their mail ids.', 'Please share their email addresses.',
      'Please share their email addresses. Bring your ids tomorrow.')


# ---------------------------------------------------------------- places, people, family
def places_and_people():
    be = r"(?:am|is|are|was|were|be|been|['’]m|['’]s|['’]re|being|currently|presently|now|will be|shall be|gone|went|go|going|travelling|traveling|stay|stayed|staying)"
    R('outofstation', rf'(?i)\b{be} out of (?P<target>station)\b', 'town', 'Register', 0.72,
      '“Out of station” is mainly Indian usage; “out of town” is the usual phrase.',
      'He is out of station till Monday.', 'He is out of town till Monday.',
      'The train is out of the station. He is out of town till Monday. We stood out of station limits.')
    R('outstation.state', r"(?i)\b(?:am|is|are|was|were|be|been|['’]m|['’]s|['’]re|currently|presently|now|will be|still) (?P<target>outstation)\b",
      'out of town', 'Register', 0.72, '“Outstation” as a state is mainly Indian usage; say “out of town”.',
      'I am outstation this week.', 'I am out of town this week.',
      'I am out of town this week. The outstation bus leaves at nine.')
    R('outstation.trip',
      r'(?i)\b(?:an?|the|my|our|his|her|their|one|next|this|last|any) (?P<target>outstation) (?:trip|tour|travel|visit|journey|cab|taxi|meeting|client|work|assignment|duty|posting|project|conference|holiday|ticket)s?\b',
      'out-of-town', 'Register', 0.7, '“Outstation” is mainly Indian usage; “out-of-town” is the usual adjective.',
      'We planned an outstation trip for the weekend.', 'We planned an out-of-town trip for the weekend.',
      'We planned an out-of-town trip for the weekend. The station is closed today.')
    inst = (r'(?:college|university|school|IIT|IIM|NIT|IIIT|BITS|institute|academy|polytechnic|IISc|AIIMS|XLRI|ISB|'
            r'(?:engineering|medical|law|arts|degree|business|nursing|pharmacy) (?:college|school))')
    why = '“Passed out” means fainted in most English; “graduated” says what you did.'
    R('passedout.institution', rf'(?i)\b(?P<target>passed out) (?:from|of) (?:the |my |a |his |her |their |our )?{inst}\b', 'graduated',
      'Register', 0.74, why, 'I passed out from IIT in 2015.', 'I graduated from IIT in 2015.',
      'He passed out from the heat at the match. She passed out after the shot. I graduated from IIT in 2015.')
    R('passedout.year', r'(?i)\b(?:I|we|he|she|they)(?: all)? (?P<target>passed out) in (?:19|20)\d\d\b', 'graduated', 'Register', 0.72, why,
      'She passed out in 2018 with honours.', 'She graduated in 2018 with honours.',
      'She passed out at the concert. We graduated in 2018.')
    R('passedout.batch', r'(?i)\b(?P<target>passed out) (?:batch|students?|candidates?|graduates?|engineers?)\b', 'graduating', 'Register', 0.7,
      '“Passed out” means fainted in most English; “graduating” or “graduated” says what you did.',
      'The passed out students get a certificate.', 'The graduating students get a certificate.',
      'The graduating students get a certificate. The runner passed out near the line.')
    R('batchmate', r'(?i)\b(?P<target>batch ?mate)s?\b', 'classmate', 'Register', 0.62,
      '“Batchmate” is mainly Indian usage; “classmate” is the usual word for someone in your year.',
      'He is my batchmate from college.', 'He is my classmate from college.',
      'He is my classmate from college. Our batch finished early.')
    R('cousin_brother', r'(?i)\b(?P<target>cousin[ -](?:brother|sister))s?\b', 'cousin', 'Register', 0.78,
      'A “cousin” can be male or female, so “cousin brother” or “cousin sister” is not needed.',
      'My cousin brother lives in Pune.', 'My cousin lives in Pune.',
      'My cousin lives in Pune. My cousin and her brother came. He is my brother.')
    R('co_brother', r'(?i)\b(?P<target>co-brother)s?\b', 'brother-in-law', 'Register', 0.62,
      '“Co-brother” is mainly Indian usage; “brother-in-law” is the standard word.',
      'My co-brother lives in Pune.', 'My brother-in-law lives in Pune.',
      'My brother-in-law lives in Pune. She works with a brother of mine.')
    R('co_sister', r'(?i)\b(?P<target>co-sister)s?\b', 'sister-in-law', 'Register', 0.62,
      '“Co-sister” is mainly Indian usage; “sister-in-law” is the standard word.',
      'My co-sister is visiting us.', 'My sister-in-law is visiting us.',
      'My sister-in-law is visiting us. Her sister works with us.')
    R('native_place', r'(?i)\b(?:my|your|his|her|their|our) (?P<target>native place)\b', 'hometown', 'Register', 0.72,
      '“Native place” is mainly Indian usage; “hometown” is the usual word.',
      'My native place is Kanpur.', 'My hometown is Kanpur.',
      'My hometown is Kanpur. Her native language is Marathi.')
    R('native_is', r'(?i)\b(?:my|your|his|her|their|our) (?P<target>native)(?: is| was| are| in)\b', 'hometown', 'Register', 0.7,
      '“Native” alone for a hometown is mainly Indian usage; “hometown” is the usual word.',
      'My native is Kerala.', 'My hometown is Kerala.',
      'Her native language is Tamil. He is a native of Kerala. Your native tongue is Hindi.')
    R('where_stay', r'(?i)\bwhere (?:do|does|did) (?:you|they|he|she|we|I) (?P<target>stay)(?: now| currently|[?.!]|$)', 'live', 'Register', 0.6,
      '“Where do you stay?” is mainly Indian usage for “where do you live?”; in most English “stay” means a short visit.',
      'Where do you stay now?', 'Where do you live now?',
      'Where do you live now? Where do you stay when you visit London? He said where we should stay.')
    R('marriage.event_noun',
      r'(?i)\b(?P<target>marriage) (?:function|invitation|card|hall|reception|party|dress|venue|season|photographer|shopping|gift|gifts|preparations|planner|planning|album|video)s?\b',
      'wedding', 'Register', 0.72, 'For the event, English says “wedding”; “marriage” is the state of being married.',
      'We booked the marriage hall for June.', 'We booked the wedding hall for June.',
      'We booked the wedding hall for June. Their marriage certificate is ready. Marriage counselling helps.')
    R('marriage.attend',
      r"(?i)\b(?:attend(?:ed|ing|s)?|going to|go to|went to|invited to|invitation to|invitation for|missed|miss|skip|skipped) (?:a |the |my |his |her |their |our |your |any |one )(?:(?:cousin|friend|sister|brother|colleague|neighbou?r)['’]s )?(?P<target>marriage)(?: of|[.,;!?]|$| (?:on|in|at|next|last|this|and|with|tomorrow|today|yesterday))",
      'wedding', 'Register', 0.72, 'For the event, English says “wedding”; “marriage” is the state of being married.',
      'I am going to a marriage on Sunday.', 'I am going to a wedding on Sunday.',
      'I am going to a wedding on Sunday. We discussed the marriage between the firms. She attended the marriage counselling.')


# ---------------------------------------------------------------- doubt, expired, intimate
def doubts():
    R('doubt.question_prep',
      r'(?i)\b(?:I|we) (?:have|had|got) (?:a |one |another )?(?P<target>doubt)(?: regarding| related to| with respect to| (?:in|on) (?:this|that|these|those|the|it)\b)',
      'question', 'Style', 0.7, 'In English a “doubt” is a feeling of not being sure; for something you want answered, say “question”.',
      'I have a doubt regarding the invoice.', 'I have a question regarding the invoice.',
      'I have a question regarding the invoice. I have doubts about the plan. I have a doubt about his story. I have a doubt in my mind.')
    R('doubt.question_adj',
      r'(?i)\b(?:I|we) (?:have|had|got) (?:a |one |another )(?:small|quick|little|silly|basic|simple|minor|minute|short|tiny) (?P<target>doubt)\b',
      'question', 'Style', 0.7, 'In English a “doubt” is a feeling of not being sure; for something you want answered, say “question”.',
      'I have a quick doubt on this.', 'I have a quick question on this.',
      'I have a quick question on this. I have a small suspicion about it. There is no doubt about it.')
    R('doubt.question_comma', r'(?i)\b(?:I|we) (?:have|had|got) (?:a |one |another )(?P<target>doubt)(?:,|:| -)\s', 'question', 'Style', 0.7,
      'In English a “doubt” is a feeling of not being sure; for something you want answered, say “question”.',
      'I have a doubt, can you help?', 'I have a question, can you help?',
      'I have a question, can you help? I have no doubt, you are right.')
    R('doubt.having_no_article',
      r"(?i)\b(?P<target>(?P<s>I|we) (?:am|are|['’]m|['’]re) having doubt)(?: regarding| related to| with respect to| (?:in|on) (?:this|that|these|those|the|it)\b)",
      '${s} have a question', 'Style', 0.74, 'Say “I have a question” for something you want answered; “having doubt” reads as being unsure.',
      'I am having doubt in this module.', 'I have a question in this module.',
      'I am having doubts about the plan. I have a question in this module.')
    R('doubt.clear',
      r"(?i)\b(?P<target>(?:clear|solve|resolve) (?P<p>my|our) doubt)(?:[.,;!?]|$| (?:on|in|regarding|about|and|please|today|tomorrow))",
      'answer ${p} question', 'Style', 0.7, '“Clear my doubt” is mainly Indian usage; say “answer my question”.',
      'Can you clear my doubt on this?', 'Can you answer my question on this?',
      'Can you answer my question on this? Nothing can clear my doubts about him. That cleared the doubt.')
    relatives = (r'father|mother|grandfather|grandmother|uncle|aunt|dad|mom|mum|brother|sister|husband|wife|son|daughter|friend|neighbou?r|'
                 r'colleague|boss|cousin|grandpa|grandma|mother-in-law|father-in-law|nephew|niece|dog|cat')
    R('expired.relative', rf'(?i)\b(?:my|his|her|their|our|your) (?:late )?(?:{relatives}) (?P<target>expired)\b',
      'passed away', 'Register', 0.72, '“Expired” is for things like passports and milk; for a person say “passed away”.',
      'My grandfather expired last year.', 'My grandfather passed away last year.',
      'My passport expired last year. My grandfather passed away last year. Your card expired today.')
    R('expired.pronoun', r'(?i)\b(?:he|she)(?: also| suddenly| unfortunately| recently| peacefully)? (?P<target>expired)(?: last| in| on| yesterday| today| at| after| due| a )',
      'passed away', 'Register', 0.72, '“Expired” is for things like passports and milk; for a person say “passed away”.',
      'She expired last month after a long illness.', 'She passed away last month after a long illness.',
      'The licence expired last month. He passed away last month.')
    leads = {'intimate': r"(?:please|kindly|pls|plz|to|will|shall|would|should|can|could|must|may|I|we|you|they|did|do|does|don['’]t|not|and|then)",
             'intimated': r'(?:was|were|been|be|have|has|had|I|we|he|she|they|you|already|also|not|and)',
             'intimating': r'(?:am|is|are|was|were|by|for|after|before|while|kindly|and)'}
    for rid, word, rep, pos, exp in [
        ('intimate.base', 'intimate', 'inform', 'Please intimate me about the change.', 'Please inform me about the change.'),
        ('intimate.past', 'intimated', 'informed', 'I have already intimated the team.', 'I have already informed the team.'),
        ('intimate.ing', 'intimating', 'informing', 'We are intimating all clients today.', 'We are informing all clients today.'),
    ]:
        R(rid, rf"(?i)\b{leads[word]} (?P<target>{word}) (?:me|us|him|her|them|you|the|all|everyone|everybody|our|your|their|his|my|clients?|customers?|about|that|to)\b",
          rep, 'Register', 0.7, '“Intimate” as a verb meaning “tell” is mainly Indian usage; “inform” is the usual word.', pos, exp,
          'They had an intimate dinner. It was an intimate setting. We inform the team daily.')


# ---------------------------------------------------------------- things
def things():
    R('softcopy', r'(?i)\b(?P<target>soft ?copy)\b', 'digital copy', 'Register', 0.66,
      '“Soft copy” is mainly Indian usage; “digital copy” (or “electronic copy”) is clearer.',
      'Please send me the soft copy.', 'Please send me the digital copy.', 'Please send me the digital copy. Keep a hard copy too.')
    R('softcopies', r'(?i)\b(?P<target>soft copies)\b', 'digital copies', 'Register', 0.66,
      '“Soft copies” is mainly Indian usage; “digital copies” (or “electronic copies”) is clearer.',
      'Please send the soft copies.', 'Please send the digital copies.', 'Please send the digital copies. Keep hard copies too.')
    R('centpercent', r'(?i)\b(?P<target>cent ?per ?cent|cent ?percent)\b', '100 percent', 'Register', 0.72,
      '“Cent percent” is mainly Indian usage; say “100 percent”.',
      'I am cent percent sure about it.', 'I am 100 percent sure about it.', 'I am 100 percent sure about it. A cent is a coin.')
    R('pendrive', r'(?i)\b(?P<target>pen ?drive)s?\b', 'USB drive', 'Register', 0.6,
      '“Pen drive” is mainly used in South Asia; “USB drive” is understood everywhere.',
      'Copy the files to a pen drive.', 'Copy the files to a USB drive.', 'Copy the files to a USB drive. Use a pen to sign.')
    R('godown', r'(?i)\b(?P<target>godown)s?\b', 'warehouse', 'Register', 0.62,
      '“Godown” is mainly used in South Asia; “warehouse” is understood everywhere.',
      'The stock is in the godown near the port.', 'The stock is in the warehouse near the port.',
      'The stock is in the warehouse near the port. The price will go down soon.')
    R('timepass.for', r'(?i)\b(?P<target>for time ?pass)\b', 'to pass the time', 'Register', 0.7,
      '“Time pass” is mainly Indian usage; say “to pass the time”.',
      'I watch videos for time pass.', 'I watch videos to pass the time.', 'I watch videos to pass the time. It will pass in time.')
    R('timepass.is', r"(?i)\b(?:is|was|its|it['’]s|just|only|all|purely|mere) (?P<target>time ?pass)\b", 'a pastime', 'Register', 0.7,
      '“Time pass” is mainly Indian usage; say “a pastime”.',
      'It is just time pass for him.', 'It is just a pastime for him.', 'It is just a pastime for him. The time will pass quickly.')
    R('current.cut', r'(?i)\b(?:a|the|every|another|frequent|long|no|our) (?P<target>current cut)s?(?:[.,;!?]|$| (?:in|for|since|and|today|yesterday|last|due|again|all|this|each|every|at|during|when|after|before))',
      'power cut', 'Register', 0.7, 'In most English the electricity is “power”; “current cut” is mainly Indian usage.',
      'We had a current cut all morning.', 'We had a power cut all morning.',
      'We had a power cut all morning. The current cut-off point is ten amps.')
    R('current.off', r'(?i)\b(?:the|our|my) (?P<target>current) (?:went off|has gone off|had gone off|goes off|went out|got cut|came back|comes back)\b',
      'power', 'Register', 0.7, 'In most English the electricity is “power”; “current went” is mainly Indian usage.',
      'The current went off at night.', 'The power went off at night.', 'The power went off at night. The current in the river was strong.')
    R('updation', r'(?i)\b(?P<target>updation)s?\b', 'update', 'Register', 0.72,
      '“Updation” is mainly Indian usage; the English noun is “update” (or “updating”).',
      'The updation of the records is pending.', 'The update of the records is pending.',
      'The update of the records is pending. We are updating the records.')
    R('upgradation', r'(?i)\b(?P<target>upgradation)s?\b', 'upgrade', 'Register', 0.72,
      '“Upgradation” is mainly Indian usage; the English noun is “upgrade”.',
      'The upgradation of the servers is planned.', 'The upgrade of the servers is planned.',
      'The upgrade of the servers is planned. We upgrade servers yearly.')
    R('timings.hours', r'(?i)\b(?P<w>office|working|work|business|shop|store|bank|lunch|visiting|opening|closing|clinic|library|canteen|gym|reception|duty) (?P<target>timings)\b',
      'hours', 'Register', 0.66, 'English says “office hours” or “opening hours”; “timings” for this is mainly Indian usage.',
      'The office timings are nine to five.', 'The office hours are nine to five.',
      'The office hours are nine to five. The timings of the runners were recorded.')
    R('timings.times', r'(?i)\b(?P<w>school|college|class|shift|bus|train|flight|meeting|exam|matinee|ferry|metro) (?P<target>timings)\b',
      'times', 'Register', 0.66, 'English says “bus times” or “class times”; “timings” for a schedule is mainly Indian usage.',
      'Please check the bus timings first.', 'Please check the bus times first.',
      'Please check the bus times first. The timings of the swimmers were recorded.')
    R('yearsback.past',
      r'(?i)\b(?:was|were|had|did|met|saw|joined|started|left|happened|came|got|bought|ordered|sent|told|said|asked|wrote|completed|finished|resigned|released|launched|checked|noticed|received|read|heard|spoke|talked|called|visited|reached|arrived|returned|found|lost|learned|began|ended|worked|lived|stayed|married|passed|graduated|submitted|filed|reported|fixed|booked|paid|cancelled|canceled)\b(?: [\w\'’]+){0,5}? (?:\d+|an?|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|few|several|many|some|couple of) (?P<target>(?P<u>years|months|weeks|days|hours|minutes) back)\b',
      '${u} ago', 'Register', 0.66, '“Years back” for “years ago” is informal and mainly South Asian usage; “ago” is the standard word.',
      'I joined the company two years back.', 'I joined the company two years ago.',
      'I joined the company two years ago. Please move the meeting two days back. We scrolled three pages back.')
    R('yearsback.lead',
      r'(?i)(?:^|[.!?]\s+)(?:a few|few|several|many|some|two|three|four|five|six|seven|eight|nine|ten|\d+) (?P<target>(?P<u>years|months|weeks) back)\b',
      '${u} ago', 'Register', 0.62, '“Years back” for “years ago” is informal and mainly South Asian usage; “ago” is the standard word.',
      'A few years back, we moved to Pune.', 'A few years ago, we moved to Pune.',
      'A few years ago, we moved to Pune. Please push the date two weeks back.')


# ---------------------------------------------------------------- appliances, exams, leave
def appliances_exams_leave():
    obj = r'(?:light|lights|lamp|lamps|fan|fans|AC|A/C|air conditioner|air conditioning|TV|television|radio|geyser|heater|tubelight|tube light)'
    det = r'(?:the|my|our|his|her|their|that|this|your|a|an)'
    neg_app = 'Please turn on the light. Open the window and close the door. He opened the file and closed the tab.'
    for rid, word, rep, pos, exp in [
        ('open.on', 'open', 'turn on', 'Please open the light.', 'Please turn on the light.'),
        ('opened.on', 'opened', 'turned on', 'He opened the fan at night.', 'He turned on the fan at night.'),
        ('opening.on', 'opening', 'turning on', 'She is opening the AC now.', 'She is turning on the AC now.'),
        ('close.off', 'close', 'turn off', 'Please close the lights.', 'Please turn off the lights.'),
        ('closed.off', 'closed', 'turned off', 'He closed the TV early.', 'He turned off the TV early.'),
        ('closing.off', 'closing', 'turning off', 'She is closing the fan now.', 'She is turning off the fan now.'),
    ]:
        R(rid, rf'(?i)\b(?P<target>{word}) {det} {obj}\b', rep, 'Word choice', 0.8,
          'You turn lights and appliances on and off; you do not open or close them.', pos, exp, neg_app)
    exams = r'(?:IELTS|TOEFL|GRE|GMAT|SAT|GATE|NEET|JEE|UPSC|CLAT|PTE)'
    why = 'You take an exam; you give an exam only when you are the examiner.'
    for rid, word, rep, pos, exp in [
        ('exam.give', 'give', 'take', 'I will give GRE next month.', 'I will take GRE next month.'),
        ('exam.gave', 'gave', 'took', 'I gave IELTS last year.', 'I took IELTS last year.'),
        ('exam.giving', 'giving', 'taking', 'She is giving IELTS next week.', 'She is taking IELTS next week.'),
        ('exam.given', 'given', 'taken', 'I have given GATE twice.', 'I have taken GATE twice.'),
    ]:
        R(rid, rf'\b(?P<target>(?i:{word})) (?:my |the |an? |our )?{exams}\b', rep, 'Register', 0.75, why, pos, exp,
          'I will take GRE next month. I gave my cat a bath. She gave the speech at the Gate. I sat in the park.')
    for rid, word, rep, pos, exp in [
        ('exam.my_give', 'give', 'take', 'I will give my exams in May.', 'I will take my exams in May.'),
        ('exam.my_gave', 'gave', 'took', 'I gave my exam yesterday.', 'I took my exam yesterday.'),
        ('exam.my_giving', 'giving', 'taking', 'I am giving my exam tomorrow.', 'I am taking my exam tomorrow.'),
    ]:
        R(rid, rf'(?i)\b(?:I|we)(?:[\'’](?:ll|m|d|ve))?(?: (?:will|am|was|have|had|shall|would|can|could|also|just|already|finally|soon))* (?P<target>{word}) (?:my|our) (?:exams?|finals?|board exams?|semester exams?|entrance exams?|midterms?)\b',
          rep, 'Register', 0.75, why, pos, exp, 'I will take my exams in May. I gave my paper to the teacher. I gave my friend a book.')
    for rid, word, rep, pos, exp in [
        ('avail.base', 'avail', 'take', 'You can avail leave next month.', 'You can take leave next month.'),
        ('avail.past', 'availed', 'took', 'He availed leave last week.', 'He took leave last week.'),
        ('avail.ing', 'availing', 'taking', 'She is availing a holiday now.', 'She is taking a holiday now.'),
    ]:
        R(rid, rf'(?i)\b(?P<target>{word}) (?:a |the |my |his |her |some |two |three |\d+ |their |casual |sick |annual |earned |paid |medical )?(?:leaves?|holidays?|days? off|vacations?)\b',
          rep, 'Register', 0.72, '“Avail leave” is mainly Indian usage; “take leave” is the usual phrase.', pos, exp,
          'You can take leave next month. Avail the offer before Friday. He availed himself of the chance.')


# ---------------------------------------------------------------- set phrases
def set_phrases():
    for rid, word, rep, pos, exp in [
        ('cametoknow.came', 'came', 'learned', 'I came to know that he had left.', 'I learned that he had left.'),
        ('cametoknow.come', 'come', 'learn', 'We will come to know about it soon.', 'We will learn about it soon.'),
        ('cametoknow.coming', 'coming', 'learning', 'I am coming to know about it now.', 'I am learning about it now.'),
    ]:
        R(rid, rf'(?i)\b(?P<target>{word} to know) (?:that|about|of)\b', rep, 'Register', 0.72,
          '“Come to know” in the sense of “find out” is mainly Indian usage; “learn” or “find out” is plainer.', pos, exp,
          'I came to know him well in college. We will get to know each other. I learned that he had left.')
    R('wepeople', r'(?i)\b(?P<target>we people)\b', 'we', 'Register', 0.62, 'Say simply “we”; “we people” is mainly Indian usage.',
      'We people are going out tonight.', 'We are going out tonight.', 'We are going out tonight. Ask the people we met.')
    R('asperme', r'(?i)\b(?P<target>as per me)\b', 'in my view', 'Register', 0.7,
      '“As per me” is mainly Indian usage; “in my view” is the usual phrase.',
      'As per me, this is wrong.', 'In my view, this is wrong.', 'As per the plan, this is wrong. In my view, this is wrong.')
    R('lastbutnot', r'(?i)\b(?P<target>last but not the least)\b', 'last but not least', 'Word choice', 0.88,
      'The phrase is “last but not least”.', 'Last but not the least, thanks to the team.', 'Last but not least, thanks to the team.',
      'Last but not least, thanks to the team. The least of these is small.')
    R('meanwhile', r'(?i)\bin (?:the )?(?P<target>meanwhile)\b', 'meantime', 'Register', 0.75,
      'The phrase is “in the meantime”; “meanwhile” stands alone.', 'In the meanwhile, I will check the logs.', 'In the meantime, I will check the logs.',
      'In the meantime, I will check the logs. Meanwhile, I will check the logs.')
