"""Where "not" and "no" go: "I not like it", "He not came", "I no have", "No do that"."""
from lib import *
from questions import VERBS

GROUPS = {
    'feel': ['like', 'love', 'want', 'need', 'hate', 'prefer', 'enjoy', 'mind', 'care'],
    'mind': ['know', 'understand', 'believe', 'remember', 'think', 'trust', 'agree', 'mean', 'forget'],
    'daily': ['speak', 'eat', 'drink', 'sleep', 'work', 'live', 'play', 'drive', 'smoke'],
    'move': ['go', 'come', 'see', 'hear', 'feel', 'use', 'read', 'write', 'watch'],
    'give': ['help', 'call', 'ask', 'tell', 'say', 'give', 'take', 'make', 'get', 'find'],
    'life': ['study', 'teach', 'buy', 'sell', 'pay', 'wait', 'stay', 'learn'],
}
EX = {'feel': 'like coffee', 'mind': 'know the answer', 'daily': 'work here', 'move': 'go there',
      'give': 'help us', 'life': 'study law'}
EX_BASE = {'feel': 'like', 'mind': 'know', 'daily': 'work', 'move': 'go', 'give': 'help', 'life': 'study'}
EX_3 = {'feel': 'likes', 'mind': 'knows', 'daily': 'works', 'move': 'goes', 'give': 'helps', 'life': 'studies'}
EX_TAIL = {'feel': ' coffee', 'mind': ' the answer', 'daily': ' here', 'move': ' there', 'give': ' us', 'life': ' law'}


def build_present():
    for g, verbs in GROUPS.items():
        alt = '|'.join(verbs)
        v, v3, tail = EX_BASE[g], EX_3[g], EX_TAIL[g]
        for word, how in (('not', 'do not'), ('no', 'do not')):
            pat = subst(r'(?i)<<CS>>(?:I|we|you|they) (?P<target>' + word + r') (?:' + alt + r')\b', CS=CS)
            R(f'{word}_do.{g}', pat, 'do not', 'Grammar', 0.9,
              f'To make a verb negative, use “do not” before it: “I do not {v}”.',
              f'I {word} {v}{tail}.', f'I do not {v}{tail}.',
              f'I do not {v}{tail}. Do you not {v}{tail}? No, I {v}{tail}. They said no. I said not now. '
              f'Whether or not you {v}{tail}, stay.')
            pat = subst(r'(?i)<<CS>>(?:he|she|it) (?P<target>' + word + r') (?:' + alt + r')\b', CS=CS)
            R(f'{word}_does.{g}', pat, 'does not', 'Grammar', 0.9,
              f'To make a verb negative, use “does not” before it: “He does not {v}”.',
              f'He {word} {v}{tail}.', f'He does not {v}{tail}.',
              f'He does not {v}{tail}. Does he not {v}{tail}? No, he {v3}{tail}. She said no. It said not now.')
    # "I not have time" / "He not has a car"
    follow = r'(?:a|an|the|any|much|many|time|money|enough|my|your|his|her|their|our|no|some|one|two|three|children|kids)'
    for word in ('not', 'no'):
        pat = subst(r'(?i)<<CS>>(?:I|we|you|they) (?P<target>' + word + r') have\s+' + follow + r'\b', CS=CS)
        R(f'{word}_have', pat, 'do not', 'Grammar', 0.9,
          'To make “have” negative, use “do not” before it: “I do not have time”.',
          f'I {word} have time.', 'I do not have time.',
          'I do not have time. Do you not have time? No, I have time. I have no time.')
        pat = subst(r'(?i)<<CS>>(?:he|she|it) (?P<target>' + word + r') have\s+' + follow + r'\b', CS=CS)
        R(f'{word}_has', pat, 'does not', 'Grammar', 0.9,
          'To make “have” negative, use “does not” before it: “He does not have a car”.',
          f'He {word} have a car.', 'He does not have a car.',
          'He does not have a car. He has a car. He said no. She has no car.')
    pat = subst(r'(?i)<<CS>>(?:he|she|it) (?P<target>not has)\s+' + follow + r'\b', CS=CS)
    R('not_has_main', pat, 'does not have', 'Grammar', 0.9,
      'To make “have” negative, use “does not have”.',
      'She not has any money.', 'She does not have any money.',
      'She does not have any money. She has no money. She has not any money, she says.')
    pat = subst(r'(?i)<<CS>>(?:he|she|it) (?P<target>no has)\s+' + follow + r'\b', CS=CS)
    R('no_has_main', pat, 'does not have', 'Grammar', 0.9,
      'To make “have” negative, use “does not have”.',
      'He no has a car.', 'He does not have a car.',
      'He does not have a car. He has no car. He said no, has a car.')
    # have + participle
    pp = r'(?:been|done|seen|gone|received|finished|read|heard|met|tried|visited|taken|had|got|given|made|used|started|decided)'
    pat = subst(r'(?i)<<CS>>(?:I|we|you|they|he|she|it) (?P<target>not (?P<h>have|has)) <<P>>\b', CS=CS, P=pp)
    R('not_have_participle', pat, '${h} not', 'Grammar', 0.9,
      '“Not” goes after “have” or “has” when a past participle follows.',
      'I not have received the file.', 'I have not received the file.',
      'I have not received the file. He has not been here. Whether or not have been there is unclear.')
    pat = subst(r'(?i)<<CS>>(?:I|we|you|they|he|she|it) (?P<target>no (?P<h>have|has)) <<P>>\b', CS=CS, P=pp)
    R('no_have_participle', pat, '${h} not', 'Grammar', 0.9,
      '“Not” goes after “have” or “has” when a past participle follows.',
      'We no have finished yet.', 'We have not finished yet.',
      'We have not finished yet. We have no finished products. He said no, has done it.')
    # not + be
    pat = subst(r'(?i)<<CS>>(?:I|we|you|they|he|she|it) (?P<target>not (?P<b>is|are|am|was|were))\b', CS=CS)
    R('not_be', pat, '${b} not', 'Grammar', 0.9,
      '“Not” goes after the verb “be”: “He is not here”.',
      'He not is here today.', 'He is not here today.',
      'He is not here today. Is he not here? No, he is here.')


def build_past():
    # Only verbs whose simple past cannot be read as a passive participle after a dropped "was" ("it not required",
    # "he not invited"): irregular pasts that differ from the participle, and a few intransitives.
    keep = {'come', 'go', 'see', 'take', 'give', 'eat', 'drink', 'write', 'speak', 'know', 'begin', 'drive', 'run', 'fall',
            'sleep', 'sit', 'stand', 'leave', 'stay', 'work', 'live', 'play', 'wait', 'arrive', 'say', 'think', 'do',
            'have', 'get', 'grow', 'fly', 'break'}
    for base, third, past, wh, tail, s3, sp in VERBS:
        if not past or base not in keep:
            continue
        if base == 'have':
            fol = r'\s+(?:a|an|the|to|some|any|no|more|my|your|his|her|our|their|time|money|lunch|dinner|fun)\b'
            tail_ = ' time'
        elif base == 'do':
            fol = r'\s+(?:it|that|this|the|my|your|his|her|our|their|any|anything|nothing|so|well|more)\b'
            tail_ = ' it'
        else:
            fol = r'\b'
            tail_ = tail
        pat = subst(r'(?i)<<CS>>(?:I|we|you|they|he|she) (?P<target>not ' + past + r')' + fol, CS=CS)
        subj = sp
        pos_tail = tail_ if base not in ('have', 'do') else tail_
        R(f'not_past.{base}', pat, 'did not ' + base, 'Grammar', 0.9,
          f'To make a past verb negative, use “did not” and the plain verb: “did not {base}”.',
          f'{cap(subj)} not {past}{pos_tail}.', f'{cap(subj)} did not {base}{pos_tail}.',
          f'{cap(subj)} did not {base}{pos_tail}. Did {subj} not {base}{pos_tail}? Not {past}, but {base}.')
    # modals
    for word in ('not', 'no'):
        pat = subst(r'(?i)<<CS>>(?:I|we|you|they|he|she|it) (?P<target>' + word + r' can)\b', CS=CS)
        R(f'{word}_can', pat, 'cannot', 'Grammar', 0.9,
          'The negative of “can” is “cannot”.',
          f'I {word} can swim.', 'I cannot swim.',
          'I cannot swim. I can not only swim but dive. You can, no? No can do.')
        pat = subst(r'(?i)<<CS>>(?:I|we|you|they|he|she|it) (?P<target>' + word + r' (?P<m>could|should|would|will|must|may|might))\b', CS=CS)
        R(f'{word}_modal', pat, '${m} not', 'Grammar', 0.9,
          '“Not” goes after the modal verb: “I should not go”.',
          f'You {word} should go.', 'You should not go.',
          'You should not go. Should you not go? No, you should go.')


def build_imperative():
    verbs = [('do', 'that'), ('touch', 'it'), ('say', 'that'), ('tell', 'anyone'), ('open', 'the door'),
             ('close', 'the window'), ('give', 'them money'), ('take', 'my bag'), ('put', 'it there'),
             ('push', 'the button'), ('pull', 'the rope'), ('eat', 'this food'), ('drink', 'the water'),
             ('waste', 'time'), ('forget', 'your ticket'), ('park', 'here'), ('throw', 'the ball'),
             ('bring', 'your phone'), ('enter', 'the room'), ('leave', 'the door open')]
    for v, obj in verbs:
        follow = r'(?:that|this|it|the|a|an|my|your|his|her|their|our|me|him|them|us|any|anything|anyone|more|time)'
        if v in ('park', 'enter', 'leave'):
            follow = r'(?:here|there|the|this|that|it|your|my)'
        if v == 'enter':
            follow = r'(?:the|this|that|it|your|my)'
        pat = subst(r'(?im)<<SS>>(?P<target>No) ' + v + r'\s+' + follow + r'\b', SS=SS)
        sample = f'No {v} {obj}.'
        # keep the sample aligned with the follow-word list
        R(f'no_imperative.{v}', pat, 'Do not', 'Grammar', 0.9,
          f'A negative command uses “do not”: “Do not {v} {obj}”.',
          sample, f'Do not {v} {obj}.',
          f'Do not {v} {obj}. No, {v} {obj}. No one can {v} {obj}. No {v}ing here.')


def build():
    build_present()
    build_past()
    build_imperative()
