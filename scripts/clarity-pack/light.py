"""Light-verb phrases ("make a decision", "conduct a review of", "have a tendency to") and their plain verbs, one rule
per verb form so the replacement keeps tense, person and number ("made a decision" -> "decided")."""
from core import *
from core import DETF as core_DETF

# base, 3rd person, past, past participle, -ing   (None: no rule for that form)
VERBS = {
    'make': ('make', 'makes', 'made', 'made', 'making'),
    'have': ('have', 'has', 'had', 'had', 'having'),
    'give': ('give', 'gives', 'gave', 'given', 'giving'),
    'take': ('take', 'takes', 'took', 'taken', 'taking'),
    'provide': ('provide', 'provides', 'provided', 'provided', 'providing'),
    'conduct': ('conduct', 'conducts', 'conducted', 'conducted', 'conducting'),
    'perform': ('perform', 'performs', 'performed', 'performed', 'performing'),
    'carry': ('carry out', 'carries out', 'carried out', 'carried out', 'carrying out'),
    'reach': ('reach', 'reaches', 'reached', 'reached', 'reaching'),
    'arrive': ('arrive', 'arrives', 'arrived', 'arrived', 'arriving'),
    'find': ('find', 'finds', 'found', 'found', 'finding'),
    'place': ('place', 'places', 'placed', 'placed', 'placing'),
    'hold': ('hold', 'holds', 'held', 'held', 'holding'),
    'raise': ('raise', 'raises', 'raised', 'raised', 'raising'),
    'lend': ('lend', 'lends', 'lent', 'lent', 'lending'),
    'file': ('file', 'files', 'filed', 'filed', 'filing'),
    'lodge': ('lodge', 'lodges', 'lodged', 'lodged', 'lodging'),
    'come': ('come', 'comes', 'came', 'come', 'coming'),
    'put': ('put', 'puts', None, None, 'putting'),
}
FORMS = ['base', 's', 'past', 'pp', 'ing']
BASE_CTX = "(?:\\b(?:to|will|would|can|could|should|must|may|might|shall|did|do|does|not|let us|let[’']s)|n[’']t)"
PP_CTX = '\\b(?:has|have|had|having|been)'
CTX = {'come': {'base': BASE_CTX, 'pp': PP_CTX}, 'put': {'base': BASE_CTX}}
PREFIX = {'base': 'We will ', 's': 'She ', 'past': 'We ', 'pp': 'She has ', 'ing': 'They are '}
# FOLLOW (core.py) for a phrase that ends the clause; THAT_TO for a report verb that takes a clause
THAT = '\\s+that\\b'
THAT_TO = '\\s+(?:that|to)\\b'
DETF = core_DETF


def light(label, verbs, tail, tail_text, tv, rest, conf, follow='', neg='', pre=None):
    """tv: (base, 3rd person, past, -ing[, past participle]) of the plain verb."""
    tv = tuple(tv) + (tv[2],) if len(tv) == 4 else tuple(tv)
    plain = dict(zip(FORMS, (tv[0], tv[1], tv[2], tv[4], tv[3])))
    for vk in verbs:
        vf = dict(zip(FORMS, VERBS[vk]))
        for form in FORMS:
            surface = vf[form]
            if surface is None:
                continue
            ctx = CTX.get(vk, {}).get(form)
            if form == 'pp' and vf['pp'] == vf['past'] and not ctx:
                continue          # "made" is covered by the past-tense rule
            if form == 'base' and vk in CTX and not ctx:
                continue
            rep = plain[form]
            body = '%s %s' % (surface, tail)
            prefix = ('(?i)%s ' % ctx) if ctx else '(?i)\\b'
            pattern = '%s(?P<target>%s)\\b%s' % (prefix, body, follow)
            lead = (pre or PREFIX)[form]
            pos = join('%s%s %s' % (lead, surface, tail_text), rest)
            exp = join('%s%s' % (lead, rep), rest)
            add('light.%s.%s.%s' % (label, vk, form), pattern, rep, conf,
                'Shorter: say “%s” instead of “%s %s”.' % (rep, surface, tail_text), pos, exp, neg)


def build():
    section('Light verb + noun')
    construction('make / reach / come to / arrive at a decision -> decide')
    dn = ('She made the right decision. The decision tree helps us decide, and no decisions were rushed. '
          'We make a decision tree for each case. Making a decision-making plan took time.')
    light('decision', ['make'], 'a decision', 'a decision', ('decide', 'decides', 'decided', 'deciding'),
          'about the budget on Friday.', 0.65, FOLLOW, dn)
    light('reach_decision', ['reach'], 'a decision', 'a decision', ('decide', 'decides', 'decided', 'deciding'),
          'about the budget on Friday.', 0.65, FOLLOW, dn)
    light('come_decision', ['come'], 'to a decision', 'to a decision', ('decide', 'decides', 'decided', 'deciding'),
          'about the budget on Friday.', 0.65, FOLLOW, dn)
    light('arrive_decision', ['arrive'], 'at a decision', 'at a decision', ('decide', 'decides', 'decided', 'deciding'),
          'about the budget on Friday.', 0.65, FOLLOW, dn)
    construction('make a recommendation / suggestion / assumption / announcement / determination that -> recommend / suggest / assume / announce / determine')
    light('recommendation', ['make'], 'a recommendation', 'a recommendation', ('recommend', 'recommends', 'recommended', 'recommending'),
          'that we wait.', 0.62, THAT_TO, 'She recommended it. Her recommendation that we wait was clear. We make a recommendation list.')
    light('suggestion', ['make'], 'a suggestion', 'a suggestion', ('suggest', 'suggests', 'suggested', 'suggesting'),
          'that we wait.', 0.62, THAT, 'She suggested it. Her suggestion that we wait was clear. We make a suggestion box.')
    light('assumption', ['make'], 'an assumption', 'an assumption', ('assume', 'assumes', 'assumed', 'assuming'),
          'that the data is clean.', 0.62, THAT, 'She assumed it. Her assumption that the data is clean was wrong.')
    light('announcement', ['make'], 'an announcement that', 'an announcement that', ('announce that', 'announces that', 'announced that', 'announcing that'),
          'the shop will close.', 0.65, '', 'She announced that the shop will close. An announcement was made.')
    light('determination', ['make'], 'a determination that', 'a determination that', ('determine that', 'determines that', 'determined that', 'determining that'),
          'the claim is valid.', 0.65, '', 'She determined that the claim is valid. A determination was made.')
    construction('make an attempt / an effort to -> try to')
    light('attempt', ['make'], 'an attempt to', 'an attempt to', ('try to', 'tries to', 'tried to', 'trying to'),
          'fix the bug twice.', 0.7, '', 'She tried to fix it. The attempt to fix it failed. We make attempts daily.')
    light('effort', ['make'], 'an effort to', 'an effort to', ('try to', 'tries to', 'tried to', 'trying to'),
          'fix the bug twice.', 0.68, '', 'She tried to fix it. Her effort to fix it paid off. They make every effort to help.')
    construction('make (a) mention of / reference to / use of -> mention / refer to / use')
    light('mention', ['make'], '(?:a )?mention of', 'a mention of', ('mention', 'mentions', 'mentioned', 'mentioning'),
          'the delay in the report.', 0.7, '', 'The report mentions the delay. A mention of the delay appeared. They make mentions in passing.')
    light('reference', ['make'], '(?:a )?reference to', 'a reference to', ('refer to', 'refers to', 'referred to', 'referring to'),
          'the earlier report.', 0.7, '', 'The memo refers to the earlier report. Her reference to the report was brief.')
    light('use', ['make'], 'use of', 'use of', ('use', 'uses', 'used', 'using'), 'the old tools.', 0.75, '',
          'The team used the old tools. The use of old tools is common. Make sure of it.')
    construction('make a contribution to / complaint about / commitment to / comparison of -> contribute to / complain about / commit to / compare')
    light('contribution', ['make'], 'a contribution to', 'a contribution to', ('contribute to', 'contributes to', 'contributed to', 'contributing to'),
          'the project.', 0.68, '', 'She contributed to the project. Her contribution to the project was large.')
    light('complaint', ['make'], 'a complaint about', 'a complaint about', ('complain about', 'complains about', 'complained about', 'complaining about'),
          'the noise.', 0.7, '', 'She complained about the noise. A complaint about the noise was filed.')
    light('commitment', ['make'], 'a commitment to', 'a commitment to', ('commit to', 'commits to', 'committed to', 'committing to'),
          'the plan.', 0.62, '', 'She committed to the plan. Her commitment to the plan was firm.')
    light('comparison', ['make'], 'a comparison (?:of|between)', 'a comparison between', ('compare', 'compares', 'compared', 'comparing'),
          'the two offers.', 0.62, '', 'She compared the two offers. A comparison between the two offers was made.')
    construction('make a purchase of / from -> buy / buy from')
    light('purchase_of', ['make'], 'a purchase of', 'a purchase of', ('buy', 'buys', 'bought', 'buying'), 'two tickets.', 0.65, '',
          'She bought two tickets. A purchase of two tickets was recorded.')
    light('purchase_from', ['make'], 'a purchase from', 'a purchase from', ('buy from', 'buys from', 'bought from', 'buying from'),
          'the shop.', 0.65, '', 'She bought from the shop. A purchase from the shop was recorded.')
    construction('make a note of / take note of -> note')
    light('note_of', ['make'], 'a note of', 'a note of', ('note', 'notes', 'noted', 'noting'), 'the date.', 0.7, '',
          'She noted the date. She made a note on the card. A note of the date was kept.')
    light('take_note', ['take'], 'note of', 'note of', ('note', 'notes', 'noted', 'noting'), 'the changes.', 0.72, '',
          'She noted the changes. We take notes in class. She took a note of nothing.'.replace(' She took a note of nothing.', ''))
    construction('make a change / adjustment / revision / amendment / correction / update / modification / improvement / addition to -> change / adjust / revise / amend / correct / update / modify / improve / add to')
    for lab, tail, text, tv, rest in [
            ('adjustment', '(?:an adjustment|adjustments) to', 'an adjustment to', ('adjust', 'adjusts', 'adjusted', 'adjusting'), 'the plan.'),
            ('revision', '(?:a revision|revisions) to', 'a revision to', ('revise', 'revises', 'revised', 'revising'), 'the draft.'),
            ('amendment', '(?:an amendment|amendments) to', 'an amendment to', ('amend', 'amends', 'amended', 'amending'), 'the draft.'),
            ('correction', '(?:a correction|corrections) to', 'a correction to', ('correct', 'corrects', 'corrected', 'correcting'), 'the draft.'),
            ('update', '(?:an update|updates) to', 'an update to', ('update', 'updates', 'updated', 'updating'), 'the page.'),
            ('modification', '(?:a modification|modifications) to', 'a modification to', ('modify', 'modifies', 'modified', 'modifying'), 'the plan.'),
            ('improvement', '(?:an improvement|improvements) to', 'an improvement to', ('improve', 'improves', 'improved', 'improving'), 'the process.'),
            ('addition', '(?:an addition|additions) to', 'an addition to', ('add to', 'adds to', 'added to', 'adding to'), 'the list.')]:
        light(lab, ['make'], tail, text, tv, rest, 0.65, DETF,
              'She %s %s She made a big %s to it. The %s to the plan is clear.' % (tv[2], rest, lab, lab))
    flush()
    section('Light verb + noun (consider, cause, end, stress)')
    construction('give consideration to / take into consideration -> consider')
    light('consideration', ['give'], 'consideration to', 'consideration to', ('consider', 'considers', 'considered', 'considering'),
          'the cost.', 0.7, '', 'She considered the cost. The cost was given careful consideration.')
    light('take_consideration', ['take'], 'into consideration', 'into consideration', ('consider', 'considers', 'considered', 'considering'),
          'the cost.', 0.7, '', 'She considered the cost. The cost was a consideration. She took the cost into account.')
    construction('put an end to -> end')
    light('end', ['put'], 'an end to', 'an end to', ('end', 'ends', 'ended', 'ending'), 'the practice.', 0.7, '',
          'It ended the practice. An end to the practice is near. They put the end of the rope down.')
    construction('place / put emphasis on -> stress')
    light('emphasis', ['place', 'put'], '(?:an |the )?emphasis on', 'emphasis on', ('stress', 'stresses', 'stressed', 'stressing'),
          'safety.', 0.62, '', 'The report stresses safety. Emphasis on safety is rising. Nobody put more emphasis on it.')
    flush()
    section('Provide / give + noun')
    construction('provide / give assistance to / with -> help / help with')
    for vs in (['provide', 'give'],):
        light('assistance_to', vs, 'assistance to', 'assistance to', ('help', 'helps', 'helped', 'helping'), 'the new staff.', 0.7, '',
              'She helped the new staff. Assistance to the new staff was free. Financial assistance is available.')
        light('assistance_with', vs, 'assistance (?=with)'.replace('(?=with)', 'with'), 'assistance with', ('help with', 'helps with', 'helped with', 'helping with'),
              'the forms.', 0.7, DETF, 'She helped with the forms. Assistance with the forms was free.')
    construction('provide / give an explanation of / a description of / a definition of / an estimate of / an indication of / a demonstration of / an illustration of -> explain / describe / define / estimate / indicate / demonstrate / illustrate')
    for lab, tail, text, tv, rest, conf in [
            ('explanation', '(?:an )?explanation (?:of|for)', 'an explanation of', ('explain', 'explains', 'explained', 'explaining'), 'the delay.', 0.7),
            ('description', 'a description of', 'a description of', ('describe', 'describes', 'described', 'describing'), 'the fault.', 0.7),
            ('definition', 'a definition of', 'a definition of', ('define', 'defines', 'defined', 'defining'), 'the term.', 0.65),
            ('estimate', 'an estimate of', 'an estimate of', ('estimate', 'estimates', 'estimated', 'estimating'), 'the cost.', 0.65),
            ('indication', 'an indication of', 'an indication of', ('indicate', 'indicates', 'indicated', 'indicating'), 'a wider problem.', 0.68),
            ('demonstration', 'a demonstration of', 'a demonstration of', ('demonstrate', 'demonstrates', 'demonstrated', 'demonstrating'), 'the new tool.', 0.65),
            ('illustration', 'an illustration of', 'an illustration of', ('illustrate', 'illustrates', 'illustrated', 'illustrating'), 'the problem.', 0.62),
            ('justification', 'a justification for', 'a justification for', ('justify', 'justifies', 'justified', 'justifying'), 'the cost.', 0.65)]:
        light(lab, ['provide', 'give'], tail, text, tv, rest, conf, '',
              'She %s %s The %s was brief.' % (tv[2], rest, text.split(' ', 1)[1].split(' ')[0] if text.split(' ')[0] in ('a', 'an') else text.split(' ')[0]))
    construction('provide / give a response / an answer to; provide / find a solution to -> respond to / answer / solve')
    light('response', ['provide', 'give'], 'a response to', 'a response to', ('respond to', 'responds to', 'responded to', 'responding to'),
          'the complaint.', 0.68, DETF, 'She responded to the complaint. Her response to the complaint was brief.')
    light('answer', ['provide', 'give'], 'an answer to', 'an answer to', ('answer', 'answers', 'answered', 'answering'),
          'the question.', 0.68, DETF, 'She answered the question. Her answer to the question was brief.')
    light('solution', ['provide', 'find'], 'a solution to', 'a solution to', ('solve', 'solves', 'solved', 'solving'),
          'the problem.', 0.62, DETF, 'She solved the problem. The solution to the problem was brief.')
    construction('provide confirmation / clarification / verification of -> confirm / clarify / verify')
    light('confirmation', ['provide'], 'confirmation of', 'confirmation of', ('confirm', 'confirms', 'confirmed', 'confirming'),
          'the order.', 0.65, '', 'She confirmed the order. Confirmation of the order arrived.')
    light('clarification', ['provide'], 'clarification (?:of|on|about|regarding)', 'clarification on', ('clarify', 'clarifies', 'clarified', 'clarifying'),
          'the terms.', 0.65, '', 'She clarified the terms. Clarification on the terms arrived.')
    light('verification', ['provide'], 'verification of', 'verification of', ('verify', 'verifies', 'verified', 'verifying'),
          'the claim.', 0.62, '', 'She verified the claim. Verification of the claim arrived.')
    flush()
    section('Conduct / perform / carry out + noun')
    construction('conduct / carry out / perform an investigation, review, assessment, evaluation, audit, inspection, examination, test, search -> investigate, review, assess, evaluate, audit, inspect, examine, test, search for')
    for lab, tail, text, tv, rest, vs in [
            ('investigation', 'an investigation (?:into|of|on)', 'an investigation into', ('investigate', 'investigates', 'investigated', 'investigating'), 'the fire.', ['conduct', 'carry', 'perform']),
            ('review', 'a review of', 'a review of', ('review', 'reviews', 'reviewed', 'reviewing'), 'the files.', ['conduct', 'carry', 'perform']),
            ('assessment', 'an assessment of', 'an assessment of', ('assess', 'assesses', 'assessed', 'assessing'), 'the risks.', ['conduct', 'carry', 'perform']),
            ('evaluation', 'an evaluation of', 'an evaluation of', ('evaluate', 'evaluates', 'evaluated', 'evaluating'), 'the options.', ['conduct', 'carry', 'perform']),
            ('audit', 'an audit of', 'an audit of', ('audit', 'audits', 'audited', 'auditing'), 'the accounts.', ['conduct', 'carry', 'perform']),
            ('inspection', 'an inspection of', 'an inspection of', ('inspect', 'inspects', 'inspected', 'inspecting'), 'the site.', ['conduct', 'carry', 'perform']),
            ('examination', 'an examination of', 'an examination of', ('examine', 'examines', 'examined', 'examining'), 'the data.', ['conduct', 'carry', 'perform']),
            ('test', 'a test (?:of|on)', 'a test of', ('test', 'tests', 'tested', 'testing'), 'the system.', ['conduct', 'carry', 'perform']),
            ('search', 'a search for', 'a search for', ('search for', 'searches for', 'searched for', 'searching for'), 'the file.', ['conduct', 'carry', 'perform']),
            ('survey', 'a survey of', 'a survey of', ('survey', 'surveys', 'surveyed', 'surveying'), 'the staff.', ['conduct', 'carry']),
            ('poll', 'a poll of', 'a poll of', ('poll', 'polls', 'polled', 'polling'), 'the voters.', ['conduct']),
            ('study', 'a study (?:of|on|into)', 'a study of', ('study', 'studies', 'studied', 'studying'), 'the effects.', ['conduct', 'carry']),
            ('research', 'research (?:on|into)', 'research into', ('research', 'researches', 'researched', 'researching'), 'the effects.', ['conduct', 'carry']),
            ('interview', 'an interview with', 'an interview with', ('interview', 'interviews', 'interviewed', 'interviewing'), 'the manager.', ['conduct'])]:
        noun = text.split(' ')[1] if text.split(' ')[0] in ('a', 'an') else text.split(' ')[0]
        light(lab, vs, tail, text, tv, rest, 0.68 if lab in ('investigation', 'review', 'assessment', 'evaluation', 'audit', 'inspection') else 0.64, '',
              'She %s %s The %s was long. They run %s often.' % (tv[2], rest, noun, noun) if False else
              'She %s %s The %s was long.' % (tv[2], rest, noun))
    flush()
    section('Have + noun')
    construction('have a tendency / preference / understanding / desire / need / belief -> tend to / prefer / understand / want to / need to / believe')
    for lab, tail, text, tv, rest, conf, neg in [
            ('tendency', 'a tendency to', 'a tendency to', ('tend to', 'tends to', 'tended to', 'tending to'), 'run late.', 0.68, 'She tends to run late. A tendency to run late is common.'),
            ('preference', 'a preference for', 'a preference for', ('prefer', 'prefers', 'preferred', 'preferring'), 'tea.', 0.65, 'She prefers tea. A preference for tea is common.'),
            ('understanding', 'an understanding of', 'an understanding of', ('understand', 'understands', 'understood', 'understanding'), 'the rules.', 0.62, 'She understands the rules. An understanding of the rules is useful.'),
            ('desire', 'a desire to', 'a desire to', ('want to', 'wants to', 'wanted to', 'wanting to'), 'leave.', 0.65, 'She wants to leave. A desire to leave is common.'),
            ('need', 'a need to', 'a need to', ('need to', 'needs to', 'needed to', 'needing to'), 'leave.', 0.65, 'She needs to leave. A need to leave is common.'),
            ('belief', '(?:a|the) belief that', 'a belief that', ('believe that', 'believes that', 'believed that', 'believing that'), 'the plan works.', 0.62, 'She believes that the plan works. A belief that it works is common.'),
            ('effect', '(?:an|the) effect on', 'an effect on', ('affect', 'affects', 'affected', 'affecting'), 'sales.', 0.68, 'The rain affects sales. It has no effect on sales. A strong effect on sales is clear.'),
            ('impact', '(?:an|the) impact on', 'an impact on', ('affect', 'affects', 'affected', 'affecting'), 'sales.', 0.65, 'The rain affects sales. It has no impact on sales. A strong impact on sales is clear.'),
            ('influence', '(?:an|the) influence on', 'an influence on', ('influence', 'influences', 'influenced', 'influencing'), 'sales.', 0.65, 'The rain influences sales. It has no influence on sales. A strong influence on sales is clear.'),
            ('discussion', 'a discussion (?:about|of|on|regarding|concerning)', 'a discussion about', ('discuss', 'discusses', 'discussed', 'discussing'), 'the budget.', 0.65, 'She discussed the budget. A discussion about the budget followed. A long discussion about it began.')]:
        light(lab, ['have'], tail, text, tv, rest, conf, '', neg, pre=dict(PREFIX, ing='Not ') if lab in ('preference', 'understanding', 'desire', 'need', 'belief') else None)
    flush()
    construction('hold a discussion about; raise an objection to; make contact with; file / lodge a complaint about; provide / lend support')
    light('discussion_hold', ['hold'], 'a discussion (?:about|of|on|regarding|concerning)', 'a discussion about', ('discuss', 'discusses', 'discussed', 'discussing'),
          'the budget.', 0.65, '', 'She discussed the budget. A discussion about the budget followed. She held a discussion group.')
    light('objection', ['raise'], 'an objection to', 'an objection to', ('object to', 'objects to', 'objected to', 'objecting to'),
          'the plan.', 0.65, '', 'She objected to the plan. An objection to the plan was heard.')
    light('contact', ['make'], 'contact with', 'contact with', ('contact', 'contacts', 'contacted', 'contacting'),
          'the manager.', 0.65, '', 'She contacted the manager. Contact with the manager is easy. We keep in contact with the manager.')
    light('complaint_file', ['file', 'lodge'], 'a complaint about', 'a complaint about', ('complain about', 'complains about', 'complained about', 'complaining about'),
          'the noise.', 0.68, '', 'She complained about the noise. A complaint about the noise was filed late.')
    light('support', ['provide', 'lend', 'give'], 'support (?:to|for)', 'support for', ('support', 'supports', 'supported', 'supporting'),
          'the new plan.', 0.62, DETF, 'She supported the new plan. Support for the new plan is strong. Software support for it is rare.')
    flush()
