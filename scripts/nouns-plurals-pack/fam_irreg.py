"""Wrong plurals of irregular nouns, Latin and Greek plurals, the -ys / -s for -ies / -es slips."""
from core import *

# Always wrong wherever they stand.
SIMPLE = [
    ('tooths', 'tooths|teeths', 'teeth', 0.95, 'Grammar', 'Brush your teeths twice a day.', 'Brush your teeth twice a day; the tooth is loose.'),
    ('feets', 'feets', 'feet', 0.86, 'Grammar', 'My feets are sore after the hike.', 'My feet are sore after the hike, and one foot is bruised.'),
    ('mices', 'mices', 'mice', 0.95, 'Grammar', 'The cat chased three mices.', 'The cat chased three mice, and one mouse got away.'),
    ('oxes', 'oxes', 'oxen', 0.86, 'Grammar', 'The farmer owns two oxes.', 'The farmer owns two oxen, and the ox is gentle.'),
    ('sheeps', 'sheeps', 'sheep', 0.93, 'Grammar', 'The sheeps grazed on the hill.', 'The sheep grazed on the hill, and the shepherd watched.'),
    ('deers', 'deers', 'deer', 0.88, 'Grammar', 'We saw four deers near the lake.', 'We saw four deer near the lake, and a deer stood still.'),
    ('fishs', 'fishs', 'fish', 0.9, 'Grammar', 'They caught six fishs this morning.', 'They caught six fish this morning, and the fishing was good.'),
    ('phenomenas', 'phenomenas', 'phenomena', 0.95, 'Grammar', 'We studied two phenomenas in class.', 'We studied two phenomena in class, and each phenomenon has a cause.'),
    ('bacterias', 'bacterias', 'bacteria', 0.94, 'Grammar', 'Some bacterias cause infections.', 'Some bacteria cause infections, and a bacterium is one cell.'),
    ('analysises', 'analysises', 'analyses', 0.95, 'Grammar', 'Both analysises agree.', 'Both analyses agree, and the analysis took a week.'),
    ('thesises', 'thesises', 'theses', 0.94, 'Grammar', 'Her students wrote strong thesises.', 'Her students wrote strong theses, and each thesis was bound.'),
    ('crisises', 'crisises', 'crises', 0.95, 'Grammar', 'The firm survived two crisises.', 'The firm survived two crises, and the crisis team met daily.'),
    ('basises', 'basises', 'bases', 0.92, 'Grammar', 'The theory has several basises.', 'The theory has several bases, and each basis is tested.'),
    ('diagnosises', 'diagnosises', 'diagnoses', 0.95, 'Grammar', 'The doctor reviewed both diagnosises.', 'The doctor reviewed both diagnoses, and the diagnosis stayed the same.'),
    ('oasises', 'oasises', 'oases', 0.95, 'Grammar', 'The desert has a few oasises.', 'The desert has a few oases, and the oasis is green.'),
    ('parenthesises', 'parenthesises', 'parentheses', 0.95, 'Grammar', 'Close the parenthesises in the formula.', 'Close the parentheses in the formula, and check each parenthesis.'),
    ('axises', 'axises', 'axes', 0.93, 'Grammar', 'Label both axises on the chart.', 'Label both axes on the chart, and the axis scale starts at zero.'),
    ('stimuluses', 'stimuluses', 'stimuli', 0.84, 'Grammar', 'The test used visual stimuluses.', 'The test used visual stimuli, and each stimulus lasted a second.'),
    ('fungis', 'fungis', 'fungi', 0.93, 'Grammar', 'Many fungis grow in the dark.', 'Many fungi grow in the dark, and a fungus is not a plant.'),
    ('larvas', 'larvas', 'larvae', 0.84, 'Grammar', 'The pond is full of larvas.', 'The pond is full of larvae, and a larva grows fast.'),
    ('memorandas', 'memorandas', 'memoranda', 0.9, 'Grammar', 'File the memorandas by date.', 'File the memoranda by date, and sign the memorandum.'),
    ('curriculas', 'curriculas', 'curricula', 0.84, 'Grammar', 'The school revised both curriculas.', 'The school revised both curricula, and the curriculum is new.'),
    ('erratas', 'erratas', 'errata', 0.9, 'Grammar', 'The book lists its erratas at the back.', 'The book lists its errata at the back, and an erratum slip came.'),
    ('addendas', 'addendas', 'addenda', 0.9, 'Grammar', 'Sign the addendas to the contract.', 'Sign the addenda to the contract, and read the addendum first.'),
    ('aircrafts', 'aircrafts', 'aircraft', 0.8, 'Word choice', 'Six aircrafts landed before the storm.', 'Six aircraft landed before the storm, and the craft shop opened.'),
    ('offsprings', 'offsprings', 'offspring', 0.76, 'Word choice', 'Both offsprings survived the winter.', 'Both offspring survived the winter, and the offspring of the pair thrived.'),
    ('heros', 'heros', 'heroes', 0.9, 'Spelling', 'The town honored its heros.', 'The town honored its heroes, and the hero smiled.'),
    ('radioes', 'radioes', 'radios', 0.95, 'Spelling', 'The radioes were in the garage.', 'The radios were in the garage, and one radio still worked.'),
    ('indexs', 'indexs', 'indexes', 0.93, 'Spelling', 'The book has two indexs.', 'The book has two indexes, and the index is long.'),
    ('matrixs', 'matrixs', 'matrices', 0.92, 'Spelling', 'Multiply the two matrixs.', 'Multiply the two matrices, and invert the matrix.'),
    ('quizs', 'quizs', 'quizzes', 0.93, 'Spelling', 'We had two quizs this week.', 'We had two quizzes this week, and the quiz was easy.'),
    ('vertexs', 'vertexs', 'vertices', 0.9, 'Spelling', 'The cube has eight vertexs.', 'The cube has eight vertices, and each vertex joins three edges.'),
    ('classs', 'classs', 'classes', 0.95, 'Spelling', 'She teaches three classs a day.', 'She teaches three classes a day, and the class is large.'),
    ('watchs', 'watchs', 'watches', 0.95, 'Spelling', 'The shop repairs old watchs.', 'The shop repairs old watches, and she watches the door.'),
    ('wishs', 'wishs', 'wishes', 0.95, 'Spelling', 'Make two wishs before you blow.', 'Make two wishes before you blow, and she wishes you well.'),
    ('lunchs', 'lunchs', 'lunches', 0.95, 'Spelling', 'We pack our lunchs at night.', 'We pack our lunches at night, and lunch starts at noon.'),
    ('brushs', 'brushs', 'brushes', 0.95, 'Spelling', 'The artist cleaned her brushs.', 'The artist cleaned her brushes, and the brush dried fast.'),
    ('taxs', 'taxs', 'taxes', 0.95, 'Spelling', 'We pay several taxs each year.', 'We pay several taxes each year, and the tax is due.'),
    ('foxs', 'foxs', 'foxes', 0.95, 'Spelling', 'Two foxs live near the farm.', 'Two foxes live near the farm, and the fox is shy.'),
    ('faxs', 'faxs', 'faxes', 0.95, 'Spelling', 'The office still sends faxs.', 'The office still sends faxes, and the fax is old.'),
    ('mixs', 'mixs', 'mixes', 0.95, 'Spelling', 'The DJ mixs old songs.', 'The DJ mixes old songs, and the mix is smooth.'),
    ('fixs', 'fixs', 'fixes', 0.95, 'Spelling', 'She fixs bikes on weekends.', 'She fixes bikes on weekends, and the fix is simple.'),
    ('witchs', 'witchs', 'witches', 0.95, 'Spelling', 'The play has three witchs.', 'The play has three witches, and the witch laughs.'),
    ('benchs', 'benchs', 'benches', 0.95, 'Spelling', 'The park has new benchs.', 'The park has new benches, and the bench is wet.'),
    ('beachs', 'beachs', 'beaches', 0.95, 'Spelling', 'The coast has quiet beachs.', 'The coast has quiet beaches, and the beach is empty.'),
    ('speechs', 'speechs', 'speeches', 0.95, 'Spelling', 'The mayor gave two speechs.', 'The mayor gave two speeches, and the speech was short.'),
    ('sandwichs', 'sandwichs', 'sandwiches', 0.95, 'Spelling', 'We ate sandwichs at noon.', 'We ate sandwiches at noon, and the sandwich was fresh.'),
    ('patchs', 'patchs', 'patches', 0.95, 'Spelling', 'The team shipped two patchs.', 'The team shipped two patches, and the patch fixed the bug.'),
]
for slug, wrong, right, conf, cat, pos, neg in SIMPLE:
    shown = wrong.split('|')[0]
    word_rule(f'irreg.{slug}', wrong, right, conf, cat,
              f'“{shown.capitalize()}” is not the plural of this noun: say “{right}”.', pos, neg)
cover('Irregular and Latin/Greek plurals', 'non-word plurals: tooths, teeths, feets, mices, oxes, sheeps, deers, fishs, phenomenas, bacterias, analysises, thesises, crisises, basises, diagnosises, oasises, parenthesises, axises, stimuluses, fungis, larvas, memorandas, curriculas, erratas, addendas, aircrafts, offsprings, heros, radioes, indexs, matrixs, quizs, vertexs',
      [f'irreg.{s[0]}' for s in SIMPLE if s[4] != 'Spelling' or s[0] in ('heros', 'radioes', 'indexs', 'matrixs', 'quizs', 'vertexs')])
cover('Spelling of regular plurals', 'a sibilant or -ch/-sh noun given only -s (boxs, classs, watchs, wishs, lunchs, brushs, taxs, foxs, faxs, mixs, fixs, witchs, benchs, beachs, speechs, sandwichs, patchs); also correct as a verb form (she fixs)',
      [f'irreg.{s[0]}' for s in SIMPLE if s[4] == 'Spelling' and s[0] not in ('heros', 'radioes', 'indexs', 'matrixs', 'quizs', 'vertexs')])

# in-laws and similar compounds: the plural goes on the first noun.
for slug, wrong, right, pos, neg in [
    ('mother_in_laws', r'mother[- ]in[- ]laws', 'mothers-in-law', 'Both mother-in-laws came to dinner.', 'Both mothers-in-law came to dinner, and my mother-in-law cooked.'),
    ('father_in_laws', r'father[- ]in[- ]laws', 'fathers-in-law', 'The two father-in-laws met at the wedding.', 'The two fathers-in-law met at the wedding, and a father-in-law spoke.'),
    ('sister_in_laws', r'sister[- ]in[- ]laws', 'sisters-in-law', 'My sister-in-laws live abroad.', 'My sisters-in-law live abroad, and my sister-in-law visits.'),
    ('brother_in_laws', r'brother[- ]in[- ]laws', 'brothers-in-law', 'His brother-in-laws run the shop.', 'His brothers-in-law run the shop, and his brother-in-law keeps books.'),
    ('son_in_laws', r'son[- ]in[- ]laws', 'sons-in-law', 'Her son-in-laws help on the farm.', 'Her sons-in-law help on the farm, and a son-in-law drives.'),
    ('daughter_in_laws', r'daughter[- ]in[- ]laws', 'daughters-in-law', 'The daughter-in-laws joined the trip.', 'The daughters-in-law joined the trip, and her daughter-in-law drove.'),
    ('passer_bys', r'passer[- ]bys', 'passers-by', 'Several passer-bys stopped to help.', 'Several passers-by stopped to help, and one passer-by called.'),
    ('runner_ups', r'runner[- ]ups', 'runners-up', 'Both runner-ups got medals.', 'Both runners-up got medals, and the runner-up smiled.'),
]:
    add(f'irreg.compound.{slug}', rf"(?i)\b(?P<target>{wrong})\b", right, 'Grammar', 0.9,
        f'In this compound the plural “s” goes on the first noun: “{right}”.', pos, neg)
cover('Irregular and Latin/Greek plurals', 'compounds that pluralise the first noun: mother/father/sister/brother/son/daughter-in-law, passer-by, runner-up',
      [f'irreg.compound.{s}' for s in ['mother_in_laws', 'father_in_laws', 'sister_in_laws', 'brother_in_laws', 'son_in_laws', 'daughter_in_laws', 'passer_bys', 'runner_ups']])
