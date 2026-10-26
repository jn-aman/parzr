"""More -s for -es / -ies slips. Each word was screened against the engine without this pack in five different sentences
(see the coverage map): only the ones the engine's own spelling pass leaves unfixed or fixes wrongly (trashs -> trash,
gass -> gas) are kept; about 110 other candidates (cherrys, querys, entrys, propertys ...) it already fixes."""
from core import *

# wrong, right, singular, true when the wrong form is also a plausible verb form (he touchs)
SLIPS = [
    ('trashs', 'trashes', 'trash', True), ('mashs', 'mashes', 'mash', True), ('hunchs', 'hunches', 'hunch', False),
    ('annexs', 'annexes', 'annex', False), ('apexs', 'apexes', 'apex', False), ('gass', 'gases', 'gas', False),
    ('appendixs', 'appendixes', 'appendix', False), ('synopsises', 'synopses', 'synopsis', False),
    ('ellipsises', 'ellipses', 'ellipsis', False), ('prognosises', 'prognoses', 'prognosis', False),
    ('paralysises', 'paralyses', 'paralysis', False), ('stratas', 'strata', 'stratum', False),
    ('genuses', 'genera', 'genus', False), ('vetos', 'vetoes', 'veto', False), ('bashs', 'bashes', 'bash', True),
    ('crosss', 'crosses', 'cross', True), ('flashs', 'flashes', 'flash', True), ('pushs', 'pushes', 'push', True),
    ('rushs', 'rushes', 'rush', True), ('stretchs', 'stretches', 'stretch', True), ('catchs', 'catches', 'catch', True),
    ('pitchs', 'pitches', 'pitch', True), ('touchs', 'touches', 'touch', True), ('porchs', 'porches', 'porch', False),
    ('ranchs', 'ranches', 'ranch', False), ('punchs', 'punches', 'punch', True), ('bosss', 'bosses', 'boss', False),
    ('kisss', 'kisses', 'kiss', True), ('guesss', 'guesses', 'guess', True), ('passs', 'passes', 'pass', True),
    ('prefixs', 'prefixes', 'prefix', False), ('crashs', 'crashes', 'crash', True),
    ('ashs', 'ashes', 'ash', False), ('splashs', 'splashes', 'splash', True), ('scratchs', 'scratches', 'scratch', True),
    ('torchs', 'torches', 'torch', False), ('archs', 'arches', 'arch', False), ('sketchs', 'sketches', 'sketch', True),
    ('latchs', 'latches', 'latch', False), ('hatchs', 'hatches', 'hatch', False), ('ditchs', 'ditches', 'ditch', False),
    ('bunchs', 'bunches', 'bunch', False), ('dresss', 'dresses', 'dress', True), ('suffixs', 'suffixes', 'suffix', False),
    ('bushs', 'bushes', 'bush', False), ('teachs', 'teaches', 'teach', True),
]
for wrong, right, single, verbal in SLIPS:
    if verbal:
        pos = f'She {wrong} the class every night.'
        neg = f'She {right} the class every night, and the word “{single}” stays as typed.'
    else:
        pos = f'We counted six {wrong} on the way home.'
        neg = f'We counted six {right} on the way home, and the word “{single}” stays as typed.'
    word_rule(f'irreg.slip.{wrong}', wrong, right, 0.94, 'Spelling',
              f'“{wrong.capitalize()}” is not the plural or verb form: say “{right}”.', pos, neg)
cover('Spelling of regular plurals', 'more sibilant and -ch/-sh nouns and verbs given only -s, and a few Latin/Greek plurals, that the engine\'s spelling pass leaves unfixed or turns into the wrong word (trashs, mashs, hunchs, annexs, apexs, gass, appendixs, synopsises, ellipsises, prognosises, paralysises, stratas, genuses, vetos, bashs, crosss, flashs, pushs, rushs, stretchs, catchs, pitchs, touchs, porchs, ranchs, punchs, bosss, kisss, guesss, passs, prefixs, crashs, ashs, splashs, scratchs, torchs, archs, sketchs, latchs, hatchs, ditchs, bunchs, dresss, suffixs, bushs, teachs). 112 other -ys/-s slips (cherrys, querys, entrys, propertys, crushs, branchs, reachs ...) were screened and are already fixed by the engine, so they have no rule',
      [f'irreg.slip.{s[0]}' for s in SLIPS])
