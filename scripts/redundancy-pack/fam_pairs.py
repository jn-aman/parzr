"""Adjective or noun modifiers that repeat what the noun already says: "end result", "free gift", "past history"."""
from core import pair, keep_first, style, cover, note, AFTER, S, E

SEC = 'Modifier plus noun that repeats it'


def build():
    ids = []
    P = lambda *a, **k: ids.extend(pair(*a, **k))
    P('pair.past_history', 'past', 'history',
      'Her past history of knee injuries is in the file.',
      'The history of the club is long, and in the past it won every title.', plural=False)
    P('pair.future_plans', 'future', 'plans',
      'What are your future plans for the house?',
      'Our plans for the future are modest, and the future tense is easy to learn.', plural=False)
    P('pair.end_result', 'end', 'result',
      'The end result looked better than the first draft.',
      'The result looked better than the first draft, and the end of the road was in sight.',
      art_pos='We got an end result that nobody expected.')
    P('pair.final_outcome', 'final', 'outcome',
      'The final outcome is still unknown.',
      'The outcome is still unknown, and the final whistle has not blown.',
      art_pos='She will accept a final outcome that is fair.', post=AFTER)
    P('pair.advance_warning', 'advance', 'warning',
      'They gave us no advance warning of the storm.',
      'They gave us no warning of the storm, and the advance party reached camp early.',
      art_pos='He sent an advance warning to the whole staff.')
    P('pair.advance_preview', 'advance', 'preview',
      'Members see the advance preview on Friday.',
      'Members see the preview on Friday, and the advance tickets sold out.',
      art_pos='Members get an advance preview of the show.')
    P('pair.close_proximity', 'close', 'proximity',
      'The cafe is in close proximity to the station.',
      'The cafe is in proximity to the station, and the tables are close together.', plural=False)
    P('pair.basic_fundamentals', 'basic', 'fundamentals',
      'Start with the basic fundamentals of budgeting.',
      'Start with the fundamentals of budgeting; the basic plan costs less.', plural=False)
    P('pair.basic_essentials', 'basic', 'essentials',
      'The kit holds only the basic essentials.',
      'The kit holds only the essentials, plus a basic first aid manual.', plural=False, mass=True, post=AFTER)
    P('pair.core_fundamentals', 'core', 'fundamentals',
      'Practise the core fundamentals.',
      'Practise the fundamentals every day; the core muscles need rest too.', plural=False, post=AFTER)
    P('pair.free_gift', 'free', 'gift',
      'Every order over fifty dollars includes a free gift.',
      'Every order includes a gift, and shipping is free of charge. A free gift card also works for the contest.',
      post=AFTER)
    P('pair.free_giveaway', 'free', 'giveaway',
      'Enter the free giveaway before midnight.',
      'Enter the giveaway before midnight; the contest is free to join.', post=AFTER)
    P('pair.unexpected_surprise', 'unexpected', 'surprise',
      'The party was the unexpected surprise of the week.',
      'The party was the surprise of the week, and nothing else unexpected happened.',
      art_pos='The party was an unexpected surprise for everyone.')
    P('pair.new_innovation', 'new', 'innovation',
      'Each new innovation is costly to test.',
      'Each innovation costs money to test, and a new model arrives in May.',
      art_pos='The lab announced a new innovation in batteries.', post=AFTER)
    P('pair.new_invention', 'new', 'invention',
      'Each new invention was tested in the shop.',
      'Each invention was tested in the shop, and the new shop opened in May.',
      art_pos='She patented a new invention.', post=AFTER)
    P('pair.true_fact', 'true', 'fact',
      'It is a true fact that the shop closed in June.',
      'It is a fact that the shop closed in June, and the rumour is true.')
    P('pair.general_consensus', 'general', 'consensus',
      'There is a general consensus on the plan.',
      'There is a consensus on the plan, and the general manager agreed.', plural=False)
    P('pair.final_conclusion', 'final', 'conclusion',
      'The final conclusion of the report is clear.',
      'The conclusion of the report is clear, and the final chapter is short.')
    P('pair.past_precedent', 'past', 'precedent',
      'Past precedent suggests the court will agree.',
      'Precedent suggests the court will agree, and the past ruling was narrow.')
    P('pair.past_memories', 'past', 'memories',
      'Old photographs bring back past memories.',
      'Old photographs bring back memories of a past summer.', plural=False)
    P('pair.armed_gunman', 'armed', 'gunm[ae]n',
      'Police said the armed gunman fled on foot.',
      'Police said the gunman fled on foot, and the armed forces were called in.',
      art_pos='A witness described an armed gunman at the door.', plural=False, kshow='gunman')
    P('pair.usual_custom', 'usual', 'custom',
      'It was his usual custom to rise at five.',
      'It was his custom to rise at five, and the usual crowd came.')
    P('pair.joint_collaboration', 'joint', 'collaboration',
      'The joint collaboration produced a new vaccine.',
      'The collaboration produced a new vaccine, and the joint account is empty.')
    P('pair.temporary_reprieve', 'temporary', 'reprieve',
      'The ruling gave the tenants a temporary reprieve.',
      'The ruling gave the tenants a reprieve, and the rental was temporary.')
    P('pair.temporary_stopgap', 'temporary', 'stopgap',
      'This patch is only a temporary stopgap.',
      'This patch is only a stopgap, and the temporary office closes soon.')
    P('pair.necessary_prerequisite', 'necessary|required|mandatory', 'prerequisite',
      'A degree is a necessary prerequisite for the job.',
      'A degree is a prerequisite for the job, and the necessary forms are online.',
      phrase='necessary prerequisite', kshow='prerequisite')
    P('pair.essential_prerequisite', 'essential', 'prerequisite',
      'Trust is the essential prerequisite for teamwork.',
      'Trust is the prerequisite for teamwork, and sleep is essential.',
      art_pos='Trust is an essential prerequisite for teamwork.')
    P('pair.dead_corpse', 'dead', 'corpse',
      'They found the dead corpse near the river.',
      'They found the corpse near the river, and the dead leaves piled up.')
    P('pair.empty_void', 'empty', 'void',
      'She stared into the empty void.',
      'She stared into the void, and the empty glass sat on the sill.',
      art_pos='The loss left an empty void in the house.', plural=False)
    P('pair.frozen_ice', 'frozen', 'ice',
      'Do not walk on the frozen ice.',
      'Do not walk on the ice; the frozen lake is thin.', plural=False, mass=True)
    P('pair.sworn_affidavit', 'sworn', 'affidavit',
      'The sworn affidavit was filed on Monday.',
      'The affidavit was filed on Monday, and the sworn witness spoke.',
      art_pos='She filed a sworn affidavit with the court.')
    P('pair.female_actress', 'female', 'actress(?:es)?',
      'The female actress thanked the crew.',
      'The actress thanked the crew, and the female lead was kind.',
      art_pos='She is a female actress with two awards.', plural=False, kshow='actress')
    P('pair.female_waitress', 'female', 'waitress(?:es)?',
      'The female waitress took our order.',
      'The waitress took our order, and a female guest sat nearby.', plural=False, kshow='waitress')
    P('pair.female_heroine', 'female', 'heroines?',
      'The female heroine of the book is a doctor.',
      'The heroine of the book is a doctor, and the female lead is a pilot.', plural=False, kshow='heroine')
    P('pair.female_princess', 'female', 'princess(?:es)?',
      'The female princess waved from the balcony.',
      'The princess waved from the balcony, and a female guard stood beside her.', plural=False, kshow='princess')
    P('pair.female_widow', 'female', 'widows?',
      'The female widow runs the farm alone.',
      'The widow runs the farm alone, and a female vet visits weekly.', plural=False, kshow='widow')
    P('pair.empty_vacuum', 'empty', 'vacuum',
      'The probe crossed the empty vacuum.',
      'The probe crossed the vacuum between the planets, and the empty tank was refilled.', plural=False, mass=True, post=AFTER)
    P('pair.universal_panacea', 'universal', 'panacea',
      'No diet is a universal panacea.',
      'No diet is a panacea, and the rule is universal.', plural=False)
    P('pair.essential_necessities', 'essential', 'necessities',
      'The shelter supplied the essential necessities of life.',
      'The shelter supplied the necessities of life, and food is essential.', plural=False, mass=True)
    P('pair.previous_history', 'previous', 'history',
      'The previous history of the house is unclear.',
      'The history of the house is unclear, and the previous owner left no notes.', plural=False)
    P('pair.brief_synopsis', 'brief', 'synopsis',
      'Write a brief synopsis of the plot.',
      'Write a synopsis of the plot, and keep the cover letter brief.', plural=False)
    return ids


cover(SEC, 'a modifier that repeats its noun (end result, final outcome, past history, future plans, advance warning, '
      'close proximity, basic fundamentals, free gift, true fact, sum total, general consensus, dead corpse, '
      'female actress, exact duplicate ...); a/an follows the word that is left', [])
