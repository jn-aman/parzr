"""Phrases whose plain form differs by the adverb, the verb form or the person: basis, manner, be-frames, ability,
first-person opinion frames, openers that can be dropped, stacked intensifiers and hedges."""
from core import *


def an(word):
    return 'an' if word[0] in 'aeiou' else 'a'


def build_basis():
    section('Adverbs')
    construction('"on a ___ basis" -> the adverb (daily, weekly, regularly, permanently ...)')
    rows = [
        ('daily', 'on a daily basis', 'Staff check the logs {}.'),
        ('weekly', 'on a weekly basis', 'Staff check the logs {}.'),
        ('monthly', 'on a monthly basis', 'Staff check the logs {}.'),
        ('yearly', 'on a yearly basis', 'Staff check the logs {}.'),
        ('annually', 'on an annual basis', 'Staff check the logs {}.'),
        ('quarterly', 'on a quarterly basis', 'Staff check the logs {}.'),
        ('hourly', 'on an hourly basis', 'Staff check the logs {}.'),
        ('daily', 'on a day-to-day basis', 'Staff check the logs {}.'),
        ('regularly', 'on a regular basis', 'Staff check the logs {}.'),
        ('continuously', 'on a continuous basis', 'The system records the logs {}.'),
        ('continually', 'on a continual basis', 'The system records the logs {}.'),
        ('consistently', 'on a consistent basis', 'The team meets the targets {}.'),
        ('frequently', 'on a frequent basis', 'Staff check the logs {}.'),
        ('routinely', 'on a routine basis', 'Staff check the logs {}.'),
        ('permanently', 'on a permanent basis', 'The firm hired her {}.'),
        ('temporarily', 'on a temporary basis', 'The firm hired her {}.'),
        ('voluntarily', 'on a voluntary basis', 'She serves on the board {}.'),
        ('part-time', 'on a part-time basis', 'She works {}.'),
        ('full-time', 'on a full-time basis', 'She works {}.'),
        ('once', 'on a one-time basis', 'The fee is charged {}.'),
    ]
    for adv, ph, frame in rows:
        rid = 'basis.' + ph.replace('on ', '', 1).replace(' basis', '').replace('-', '_').replace(' ', '_').replace('a_', '', 1).replace('an_', '', 1)
        sw(rid, ph.replace('-', '[ -]'), adv, 0.75, 'Shorter: say “%s”.' % adv,
           frame.format(ph), frame.format(adv),
           frame.format(adv) + ' The basis of the plan is sound.')


def build_manner():
    construction('"in a ___ manner/fashion" -> the adverb (promptly, efficiently, differently ...)')
    pairs = [('prompt', 'promptly'), ('quick', 'quickly'), ('rapid', 'rapidly'), ('careful', 'carefully'),
             ('safe', 'safely'), ('secure', 'securely'), ('efficient', 'efficiently'), ('effective', 'effectively'),
             ('appropriate', 'appropriately'), ('professional', 'professionally'), ('responsible', 'responsibly'),
             ('consistent', 'consistently'), ('clear', 'clearly'), ('transparent', 'transparently'), ('respectful', 'respectfully'),
             ('polite', 'politely'), ('serious', 'seriously'), ('satisfactory', 'satisfactorily'), ('honest', 'honestly'),
             ('proper', 'properly'), ('correct', 'correctly'), ('accurate', 'accurately'), ('thorough', 'thoroughly'),
             ('smooth', 'smoothly'), ('gradual', 'gradually'), ('regular', 'regularly'), ('random', 'randomly'),
             ('different', 'differently'), ('similar', 'similarly'), ('cost-effective', 'cost-effectively'),
             ('sustainable', 'sustainably'), ('systematic', 'systematically'), ('unexpected', 'unexpectedly'),
             ('dramatic', 'dramatically'), ('significant', 'significantly'), ('positive', 'positively'),
             ('negative', 'negatively'), ('open', 'openly'), ('calm', 'calmly'), ('quiet', 'quietly')]
    for adj, adv in pairs:
        conf = 0.75 if adj in ('timely', 'prompt', 'efficient', 'effective', 'different', 'similar') else 0.72
        ph = 'in %s %s manner' % (an(adj), adj)
        frame = 'The team handled the request {}.'
        rid = 'manner.' + adj.replace('-', '_')
        sw(rid, 'in an? %s (?:manner|fashion)' % adj.replace('-', '[ -]'), adv, conf, 'Shorter: say “%s”.' % adv,
           frame.format(ph), frame.format(adv),
           frame.format(adv) + ' The manner of the reply was polite. She spoke in a hurry.')


BE = [
    # id, tail regex, tail text, (present-plural/am, 3rd singular, past), subject pair, rest
    ('agreement', 'in agreement with', ('agree with', 'agrees with', 'agreed with'), 'the new plan.', 0.7),
    ('need', 'in need of', ('need', 'needs', 'needed'), 'new tools.', 0.7),
    ('possession', 'in possession of', ('have', 'has', 'had'), 'the keys.', 0.68),
    ('violation', 'in violation of', ('violate', 'violates', 'violated'), 'the rules.', 0.7),
    ('compliance', 'in compliance with', ('comply with', 'complies with', 'complied with'), 'the rules.', 0.7),
    ('conflict', 'in conflict with', ('conflict with', 'conflicts with', 'conflicted with'), 'the rules.', 0.7),
    ('receipt', 'in receipt of', ('have received', 'has received', 'had received'), 'your letter.', 0.68),
    ('attendance', 'in attendance at', ('attend', 'attends', 'attended'), 'the meeting.', 0.68),
    ('opinion', 'of the opinion that', ('think that', 'thinks that', 'thought that'), 'the plan is sound.', 0.7),
    ('belief', 'of the belief that', ('believe that', 'believes that', 'believed that'), 'the plan is sound.', 0.7),
    ('indicative', 'indicative of', ('indicate', 'indicates', 'indicated'), 'a wider problem.', 0.68),
    ('suggestive', 'suggestive of', ('suggest', 'suggests', 'suggested'), 'a wider problem.', 0.68),
    ('reflective', 'reflective of', ('reflect', 'reflects', 'reflected'), 'a wider problem.', 0.68),
    ('illustrative', 'illustrative of', ('illustrate', 'illustrates', 'illustrated'), 'a wider problem.', 0.68),
    ('applicable', 'applicable to', ('apply to', 'applies to', 'applied to'), 'all staff.', 0.68),
]


def build_be():
    section('Verb frames')
    construction('"is in agreement with", "are in need of", "was in violation of", "is indicative of" ... -> the plain verb')
    for fid, tail, (b, s, p), rest, conf in BE:
        negs = {
            'agreement': 'The members agree with the plan. They reached agreement quickly.',
            'need': 'The children need new tools. Children in need of tools get them.',
            'possession': 'The guards have the keys. Anyone in possession of keys must say so.',
            'violation': 'The firms violate the rules. Any act in violation of the rules is void.',
            'compliance': 'The firms comply with the rules. Anything in compliance with the rules is fine.',
            'conflict': 'The firms conflict with the rules. A plan in conflict with the rules is void.',
            'receipt': 'The firm has received your letter. Anyone in receipt of a letter should reply.',
            'attendance': 'The members attend the meeting. The list shows who was in attendance.',
            'opinion': 'The members think that the plan is sound. A person of the opinion that it fails can speak.',
            'belief': 'The members believe that the plan is sound. A person of the belief that it fails can speak.',
            'indicative': 'The numbers indicate a wider problem. An indicative price is given.',
            'suggestive': 'The numbers suggest a wider problem. A suggestive pattern is shown.',
            'reflective': 'The numbers reflect a wider problem. A reflective surface is shown.',
            'illustrative': 'The numbers illustrate a wider problem. An illustrative case is shown.',
            'applicable': 'The rules apply to all staff. Any applicable rules are listed.',
        }[fid]
        for form, be, subj, verb in (('plural', '(?:am|are)', 'The firms', b), ('singular', 'is', 'The firm', s), ('past', '(?:was|were)', 'The firm', p)):
            be_text = {'plural': 'are', 'singular': 'is', 'past': 'was'}[form]
            add('be.%s.%s' % (fid, form), '(?i)\\b(?P<target>%s %s)\\b' % (be, tail), verb, conf,
                'Shorter: say “%s” instead of “%s %s”.' % (verb, be_text, tail),
                '%s %s %s %s' % (subj, be_text, tail, rest), '%s %s %s' % (subj, verb, rest), negs)
    # "in a position to" and the ability frames -> can / could / be able to
    construction('"has the ability to", "had the capability to" -> can / could / be able to')
    add('ability.has', '(?i)\\b(?P<target>has the (?:ability|capability) to)\\b', 'can', 0.68, 'Shorter: say “can”.',
        'The new tool has the ability to export files.', 'The new tool can export files.',
        'The new tool can export files. She has the ability, and the tool has no capacity limit.')
    add('ability.have', '(?i)\\b(?:I|we|you|they|who|that|which) (?P<target>have the (?:ability|capability) to)\\b', 'can', 0.68,
        'Shorter: say “can”.', 'We have the ability to export files.', 'We can export files.',
        'We can export files. Anyone who has had the ability to export files signed in.')
    add('ability.had', '(?i)\\b(?:I|we|you|he|she|it|they|who|that|which) (?P<target>had the (?:ability|capability) to)\\b', 'could',
        0.68, 'Shorter: say “could”.', 'She had the ability to export files.', 'She could export files.',
        'She could export files. She has had the ability to export files.')
    add('ability.will_have', "(?i)(?:\\b(?:to|will|would|should|shall|may|might|must)|['’](?:ll|d)) (?P<target>have the (?:ability|capability) to)\\b",
        'be able to', 0.68, 'Shorter: say “be able to”.', 'You will have the ability to export files.',
        'You will be able to export files.', 'You will be able to export files. The ability to export files is new.')


def build_my():
    section('First-person frames')
    construction('"it is my opinion that" and its kin -> "I think", "I believe", "I recommend that" ...')
    rows = [
        ('opinion', '(?:opinion|view)', 'think', 'the plan will fail.', 'think'),
        ('belief', 'belief', 'believe', 'the plan will fail.', 'believe'),
        ('hope', 'hope', 'hope', 'the plan will work.', 'hope'),
        ('feeling', 'feeling', 'feel', 'the plan will fail.', 'feel'),
        ('contention', 'contention', 'contend that', 'the plan will fail.', 'contend that'),
        ('recommendation', 'recommendation', 'recommend that', 'we wait.', 'recommend that'),
        ('suggestion', 'suggestion', 'suggest that', 'we wait.', 'suggest that'),
    ]
    for fid, nounre, verb, rest, _ in rows:
        word = {'opinion': 'opinion', 'belief': 'belief', 'hope': 'hope', 'feeling': 'feeling', 'understanding': 'understanding',
                'contention': 'contention', 'recommendation': 'recommendation', 'suggestion': 'suggestion'}[fid]
        for p, subj in (('my', 'I'), ('our', 'we')):
            if fid == 'opinion':
                word_text = 'view' if p == 'our' else 'opinion'
            else:
                word_text = word
            lead = 'It is %s %s that' % (p, word_text)
            rep = '%s %s' % (subj, verb)
            pos = '%s %s' % (lead, rest)
            exp = '%s %s' % (rep[0].upper() + rep[1:], rest)
            # "that" is part of the phrase, so the verb's own "that" (understand that) stays
            add('my.%s.%s' % (fid, p), "(?i)\\b(?P<target>it(?: is|['’]s) %s %s that)\\b" % (p, nounre), rep, 0.7,
                'Shorter: say “%s”.' % rep, pos, exp,
                '%s %s %s Their %s was clear.' % (rep[0].upper() + rep[1:], rest[:-1] + '.', 'It is my right.', word_text))
    add('my.intention.my', "(?i)\\b(?P<target>it(?: is|['’]s) my intention to)\\b", 'I intend to', 0.7, 'Shorter: say “I intend to”.',
        'It is my intention to resign.', 'I intend to resign.', 'I intend to resign. His intention was clear.')
    add('my.intention.our', "(?i)\\b(?P<target>it(?: is|['’]s) our intention to)\\b", 'we intend to', 0.7, 'Shorter: say “we intend to”.',
        'It is our intention to resign.', 'We intend to resign.', 'We intend to resign. Our intention was clear.')
    construction('"in my personal opinion", "I personally think" -> "in my opinion", "I think"')
    add('personal.in_my_personal_opinion', '(?i)\\bin (?P<target>(?P<p>my|our) (?:own )?personal) (?:opinion|view)\\b', '${p}', 0.62,
        'Drop “personal”: “in my opinion” already says it is yours.', 'In my personal opinion, the plan is sound.',
        'In my opinion, the plan is sound.',
        'In my opinion, the plan is sound. These are my personal views and not my employer’s. Keep it personal.')
    add('personal.i_personally_think', "(?i)\\b(?:I|we) (?P<target>personally )(?:(?:do not|don't|would|wouldn't|could|will|can|cannot|can't) )?"
        "(?:think|believe|feel|consider|doubt|prefer|suppose|guess|reckon|recommend|suggest)\\b", '', 0.62,
        'Drop “personally”: “I think” already says it is your view.', 'I personally think the plan is sound.',
        'I think the plan is sound.', 'I think the plan is sound. I personally delivered the parcel. He personally thinks it fails.')
    construction('"in my own opinion" -> "in my opinion"')
    add('personal.in_my_own_opinion', '(?i)\\bin (?P<target>(?P<p>my|our) own) (?:opinion|view)\\b', '${p}', 0.65,
        'Drop “own”: “in my opinion” already says it is yours.', 'In my own opinion, the plan is sound.',
        'In my opinion, the plan is sound.', 'In my opinion, the plan is sound. The plan is my own.')


def drops(rid, label, body, ex_pos_tail, tail_text='the plan is sound.', conf=0.65, why=None):
    """Two rules for an opener that can simply go: at the start of a sentence (the next word takes the capital) and
    in the middle of one (after a comma or a conjunction)."""
    why = why or 'Drop the opener: the sentence works without it.'
    add('drop.%s.start' % rid, '(?im)(?:^|[.!?]\\s+)(?P<target>%s )(?P<action>[a-z])?' % body, '', conf, why,
        '%s the plan is sound.' % ex_pos_tail, 'The plan is sound.',
        'The plan is sound. We know the plan is sound.')
    add('drop.%s.mid' % rid, '(?i)(?:[,;:]|\\b(?:and|but|so|yet|because|since|although|though|while|whereas|if|when|that|as)) '
        '(?P<target>%s )' % body, '', conf, why,
        'The test passed, and %s the plan is sound.' % (ex_pos_tail[0].lower() + ex_pos_tail[1:]),
        'The test passed, and the plan is sound.', 'The test passed, and the plan is sound. The plan is sound.')


def build_drops():
    section('Openers that can be dropped')
    construction('"It is important to note that" and its kin (start of sentence, then mid-sentence) -> drop')
    drops('important_to_note', 'it is important to note that', '(?:it is (?:also )?important to note that)', 'It is important to note that')
    drops('worth_noting', 'it is worth noting that', '(?:it is (?:also )?worth noting that)', 'It is worth noting that')
    drops('should_be_noted', 'it should be noted that', '(?:it (?:should|must|needs to) be noted that)', 'It should be noted that')
    drops('worth_mentioning', 'it is worth mentioning that', '(?:it (?:is worth mentioning|should be mentioned|bears mentioning) that)',
          'It is worth mentioning that')
    drops('worth_pointing_out', 'it is worth pointing out that', '(?:it (?:is worth pointing out|should be pointed out|is important to point out) that)',
          'It should be pointed out that')
    drops('goes_without_saying', 'it goes without saying that', '(?:it (?:should )?goes? without saying that)', 'It goes without saying that')
    drops('needless_to_say', 'needless to say', 'needless to say,', 'Needless to say,', conf=0.68,
          why='Drop “needless to say”: if it needs no saying, leave it out.')
    drops('fact_of_the_matter', 'the fact of the matter is that', 'the (?:fact|truth|reality) of the matter is that', 'The fact of the matter is that')


def build_stacks():
    section('Stacked intensifiers and hedges')
    construction('"very very", "really really", "so so" + adjective -> one intensifier')
    add('stack.very_very', '(?i)\\b(?P<target>very(?: very)+)\\b', 'very', 0.6, 'Say it once: one “very” is enough.',
        'The soup was very very hot.', 'The soup was very hot.', 'The soup was very hot. The soup was very, very hot. Very well.')
    add('stack.really_really', '(?i)\\b(?P<target>really(?: really)+)\\b', 'really', 0.6, 'Say it once: one “really” is enough.',
        'The soup was really really hot.', 'The soup was really hot.', 'The soup was really hot. The soup was really, really hot.')
    adj = ('(?:happy|sorry|proud|good|glad|excited|tired|sad|grateful|thankful|angry|cold|hot|bad|big|small|nice|sweet|cute|funny|hard|easy|'
           'long|late|early|fast|slow|old|young|beautiful|amazing|great|lucky|scared|bored|hungry|sleepy|worried|helpful|useful|tall|loud)')
    add('stack.so_so', '(?i)\\b(?P<target>so so) %s\\b' % adj, 'so', 0.6, 'Say it once: one “so” is enough.',
        'The soup was so so hot.', 'The soup was so hot.', 'The soup was so hot. The film was so so. The film was so-so good.')
    add('stack.extremely_extremely', '(?i)\\b(?P<target>extremely(?: extremely)+)\\b', 'extremely', 0.6, 'Say it once.',
        'The soup was extremely extremely hot.', 'The soup was extremely hot.', 'The soup was extremely hot.')
    construction('"absolutely essential" and kin -> drop "absolutely"')
    add('stack.absolutely_essential', '(?i)\\b(?P<target>absolutely )(?:essential|indispensable|imperative|vital|mandatory)\\b', '', 0.62,
        'Drop “absolutely”: “essential” already means it cannot be left out.',
        'A backup is absolutely essential.', 'A backup is essential.',
        'A backup is essential. Delete it only if absolutely necessary. It is absolutely right.')
    construction('"kind of" / "sort of" + adjective after a formal subject -> somewhat')
    subj = ('(?:report|reports|results?|findings?|analysis|approach|process|method|design|proposal|policy|system|model|data|evidence|plan|'
            'argument|study|experiment|procedure|framework|strategy|solution|outcome|performance|implementation|document|draft|paper|'
            'article|algorithm|argument|conclusion|estimate|forecast|budget|schedule|timeline)')
    adjs = ('(?:important|difficult|hard|complicated|confusing|unclear|expensive|slow|vague|limited|weak|small|large|big|high|low|poor|messy|'
            'rough|slight|similar|different|useful|helpful|disappointing|surprising|unusual|inconsistent|incomplete|outdated|long|short|'
            'simple|obvious|tricky|risky|cheap|fast|early|late)')
    add('hedge.kind_of', '(?i)\\b%s (?:is|are|was|were|seems|seem|appears|appear|looks|look|remains|remain) (?P<target>(?:kind|sort) of) %s\\b' % (subj, adjs),
        'somewhat', 0.62, 'In formal writing, “somewhat” is the plain form of “kind of” or “sort of”.',
        'The report is kind of long.', 'The report is somewhat long.',
        'The report is somewhat long. This kind of report is long. What sort of report is it? The report is a kind of long list.')
    construction('"I would actually like to" -> "I would like to"')
    add('filler.would_actually_like', "(?i)\\b(?:I|we) would (?P<target>(?:actually|basically) )like to\\b",
        '', 0.6, 'Drop the filler: “I would like to” already says it.', 'I would actually like to ask a question.',
        'I would like to ask a question.', 'I would like to ask a question. I actually like to cook.')
    add('filler.id_actually_like', "(?i)\\b(?:I|we)['’]d (?P<target>(?:actually|basically) )like to\\b", '', 0.6,
        'Drop the filler: “I’d like to” already says it.', 'I’d actually like to ask a question.', 'I’d like to ask a question.',
        'I’d like to ask a question. I actually like to cook.')
    construction('"in actual fact" / "in point of fact" -> in fact')
    sw('filler.in_actual_fact', 'in (?:actual|point of) fact', 'in fact', 0.78, 'Shorter: say “in fact”.',
       'In actual fact, the plan is sound.', 'In fact, the plan is sound.',
       'In fact, the plan is sound. The actual fact is clear. A point of fact was raised.')
    construction('"it would be appreciated" skipped; "very unique" is covered by mod.very_unique_abs')
    flush()
