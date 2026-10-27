"""More transfer errors found by probing the engine with writer-style sentences: wrong words around a fixed
phrase, body-part and device verbs, transport prepositions, comparatives, and the closings of Indian-English email."""
from lib import R


def build():
    comparatives()
    body_and_devices()
    transport_and_places()
    agree_forms()
    email_forms()
    numbers()


def comparatives():
    R('younger.to', r'(?i)\byounger (?P<target>to) (?:me|him|her|us|them|you|my|his|her|their|your|our)\b', 'than', 'Grammar', 0.9,
      'Use “than” after a comparative: “younger than me”.',
      'He is younger to me by two years.', 'He is younger than me by two years.',
      'He is younger than me by two years. He is kind to me.')
    R('lesser.than', r'(?i)\b(?P<target>lesser) than\b', 'less', 'Grammar', 0.88,
      '“Lesser” is not used before “than”; say “less than”.',
      'Lesser than ten people came.', 'Less than ten people came.',
      'Less than ten people came. He is a lesser man than his father.')


def body_and_devices():
    parts = (r'head|stomach|leg|legs|back|hand|hands|eyes?|throat|chest|knees?|neck|tooth|teeth|body|ears?|arms?|shoulders?|foot|feet|belly|waist|joints?|fingers?')
    R('paining.is', rf'(?i)\b(?:my|his|her|their|our|your) (?:\w+ )?(?:{parts}) (?P<target>is paining)\b', 'hurts', 'Word choice', 0.9,
      'Say that a part of the body “hurts”; “paining” is not used this way.',
      'My head is paining since morning.', 'My head hurts since morning.',
      'My head hurts since morning. The pain is strong.')
    R('paining.are', rf'(?i)\b(?:my|his|her|their|our|your) (?:\w+ )?(?:{parts}) (?P<target>are paining)\b', 'hurt', 'Word choice', 0.9,
      'Say that parts of the body “hurt”; “paining” is not used this way.',
      'My legs are paining a lot.', 'My legs hurt a lot.',
      'My legs hurt a lot. The pain is strong.')
    R('hanged.device',
      r'(?i)\b(?:phone|mobile|laptop|computer|system|app|application|screen|PC|server|website|page|browser|tablet|TV|software) (?:is|got|has|was|gets|keeps) (?:been |again |always |just |suddenly |getting |not |also |now )?(?P<target>hanged)\b',
      'hung', 'Word choice', 0.9, 'A frozen device has “hung”; “hanged” is only for executions.',
      'My laptop got hanged again.', 'My laptop got hung again.',
      'My laptop got hung again. The picture was hung on the wall.')


def transport_and_places():
    R('in.meeting', r"(?i)\b(?:am|is|are|was|were|be|been|['’]m|['’]s|['’]re) in (?P<target>meeting)(?:[.,;!?]|$| (?:now|right now|till|until|from|with|for|today|tomorrow|at|and|so|since))",
      'a meeting', 'Grammar', 0.9, 'A meeting needs “a”: “I am in a meeting”.',
      'I am in meeting till noon.', 'I am in a meeting till noon.',
      'I am in a meeting till noon. He is in meeting rooms all day.')
    R('in.bus', r"(?i)\b(?:am|is|are|was|were|['’]m|['’]s|['’]re) (?P<target>in (?P<v>bus|train|metro))(?:[.,;!?]|$| (?:now|right now|till|until|from|to|and|so|since|today|tomorrow))",
      'on the ${v}', 'Grammar', 0.9, 'You are “on the bus” or “on the train”.',
      'I am in bus now.', 'I am on the bus now.', 'I am on the bus now. We sat in bus seats.')
    R('in.cab', r"(?i)\b(?:am|is|are|was|were|['’]m|['’]s|['’]re) (?P<target>in (?P<v>cab|taxi))(?:[.,;!?]|$| (?:now|right now|till|until|from|to|and|so|since|today|tomorrow))",
      'in a ${v}', 'Grammar', 0.9, 'A cab needs “a”: “in a cab”.',
      'I am in cab now.', 'I am in a cab now.', 'I am in a cab now. We sat in cab seats.')
    R('by.walk', r'(?i)\b(?P<target>by walk)\b', 'on foot', 'Word choice', 0.88, 'The phrase is “on foot”.',
      'I came by walk today.', 'I came on foot today.', 'I came on foot today. We took a walk.')
    for rid, word, rep, pos, exp in [
        ('belong.base', 'belong', 'come', 'I belong from Delhi.', 'I come from Delhi.'),
        ('belong.s', 'belongs', 'comes', 'She belongs from Pune.', 'She comes from Pune.'),
        ('belong.past', 'belonged', 'came', 'He belonged from Patna.', 'He came from Patna.'),
    ]:
        R(rid, rf'(?i)\b(?P<target>{word}) from\b', rep, 'Word choice', 0.85, 'To say where you are from, use “come from”; “belong” takes “to”.', pos, exp,
          'I come from Delhi. He belongs to the club. The book belongs to me.')
    R('goodname.is', r'(?i)\bmy (?P<target>good )name is (?-i:[A-Z][a-z]+)', '', 'Register', 0.72,
      'Say “My name is …”; “good name” for your own name is mainly Indian usage.',
      'My good name is Ravi.', 'My name is Ravi.', 'My good name is being protected. My name is Ravi.')


def agree_forms():
    adv = r'(?P<adv>totally|completely|fully|absolutely|entirely|strongly|also|quite|really|100%)'
    R('agree.adv_plural', rf"(?i)\b(?P<target>(?P<s>I|we|you|they)(?: am|['’]m| are|['’]re) {adv} agree)\b", '${s} ${adv} agree', 'Verb form', 0.93,
      '“Agree” is a verb, so it does not follow “am” or “are”: “I totally agree”.',
      'I am totally agree with you.', 'I totally agree with you.',
      'I totally agree with you. We are quite sure about this.')
    R('agree.adv_third', rf"(?i)\b(?P<target>(?P<s>he|she)(?: is|['’]s) {adv} agree)\b", '${s} ${adv} agrees', 'Verb form', 0.93,
      '“Agree” is a verb, so it does not follow “is”: “she totally agrees”.',
      'She is also agree with us.', 'She also agrees with us.',
      'She also agrees with us. She is quite sure about this.')


def email_forms():
    R('informed.please', r'(?im)(?:^|[.!?]\s+)(?P<target>(?:please|kindly) be informed that)\b', 'please note that', 'Register', 0.7,
      '“Please note that” is shorter and plainer than “please be informed that”.',
      'Please be informed that the office is closed.', 'Please note that the office is closed.',
      'Please note that the office is closed. We informed them that it is closed.')
    R('thanking.you', r'(?im)(?:^|[.!?]\s+)(?P<target>thanking you)\b', 'thank you', 'Register', 0.7,
      '“Thank you” is the usual closing; “thanking you” is a fragment.',
      'Thanking you in advance.', 'Thank you in advance.',
      'Thank you in advance. We are thanking you for your time.')


def numbers():
    R('two.three', r'(?i)\b(?P<target>(?P<a>one|two|three|four|five|six|seven)-(?P<b>two|three|four|five|six|seven|eight|nine|ten)) (?:days|weeks|months|years|hours|minutes|times|people|persons|members|items|pages|points|steps|attempts|options|books|tickets|rooms|cups|glasses|pieces)\b',
      '${a} or ${b}', 'Style', 0.82, 'Say “two or three days”; “two-three days” is mainly Indian usage.',
      'Please send me two-three days of leave.', 'Please send me two or three days of leave.',
      'Please send me two or three days of leave. It takes 2-3 days. He threw a one-two punch.')
