"""Irregular plurals that are also possessives or verbs: flagged only where the plural is certain."""
from core import *

PAIRS = [
    ('wolfs', 'wolfs', 'wolves', 0.93,
     'Two wolfs circled the camp.', 'Two wolves circled the camp, and the wolf\'s den is deep, and he wolfs down lunch.',
     'The wolfs are hunting at night.', 'The wolves are hunting at night, and the wolf\'s den is deep.'),
    ('knifes', 'knifes', 'knives', 0.93,
     'We bought six knifes for the kitchen.', 'We bought six knives for the kitchen, and she knifes the butter onto toast.',
     'The knifes are in the drawer.', 'The knives are in the drawer, and the knife\'s handle is loose.'),
    ('leafs', 'leafs', 'leaves', 0.93,
     'Many leafs fell in October.', 'Many leaves fell in October, and he leafs through the book.',
     'The leafs are turning red.', 'The leaves are turning red, and the leaf\'s edge is torn.'),
    ('wifes', 'wifes', 'wives', 0.94,
     'Both wifes joined the committee.', 'Both wives joined the committee, and his wife\'s car is new.',
     'The wifes are meeting at noon.', 'The wives are meeting at noon, and the wife\'s office is near.'),
    ('lifes', 'lifes', 'lives', 0.94,
     'Many lifes were saved that night.', 'Many lives were saved that night, and life\'s too short to wait.',
     'Our lifes are busy and full.', 'Our lives are busy and full, and life\'s good.'),
    ('halfs', 'halfs', 'halves', 0.93,
     'Cut the loaf into two halfs.', 'Cut the loaf into two halves, and the half\'s price is posted.',
     'The halfs are not equal.', 'The halves are not equal, and the half\'s score was close.'),
    ('shelfs', 'shelfs', 'shelves', 0.93,
     'We built three shelfs for the books.', 'We built three shelves for the books, and the shelf\'s edge is rough.',
     'The shelfs are full of books.', 'The shelves are full of books, and the shelf\'s paint is new.'),
    ('thiefs', 'thiefs', 'thieves', 0.94,
     'Two thiefs broke into the shop.', 'Two thieves broke into the shop, and the thief\'s bag was left behind.',
     'The thiefs are in custody.', 'The thieves are in custody, and the thief\'s name is known.'),
    ('calfs', 'calfs', 'calves', 0.88,
     'The cow had two calfs this spring.', 'The cow had two calves this spring, and the calf\'s mother is near.',
     'The calfs are drinking milk.', 'The calves are drinking milk, and the calf\'s pen is clean.'),
    ('loafs', 'loafs', 'loaves', 0.92,
     'The bakery sells six loafs every morning.', 'The bakery sells six loaves every morning, and he loafs around on Sundays.',
     'The loafs are cooling on the rack.', 'The loaves are cooling on the rack, and the loaf\'s crust is crisp.'),
    ('elfs', 'elfs', 'elves', 0.88,
     'The story has three elfs and a dragon.', 'The story has three elves and a dragon, and the elf\'s bow is gold.',
     'The elfs are wrapping the gifts.', 'The elves are wrapping the gifts, and the elf\'s hat is red.'),
    ('mans', 'mans', 'men', 0.93,
     'Two mans waited at the gate.', 'Two men waited at the gate, and the crew mans the pumps, and my mans is here.',
     'The mans are carrying boxes.', 'The men are carrying boxes, and the man\'s coat is wet.'),
    ('womans', 'womans', 'women', 0.93,
     'Three womans spoke at the meeting.', 'Three women spoke at the meeting, and the woman\'s coat is red.',
     'The womans are leading the project.', 'The women are leading the project, and the woman\'s desk is tidy.'),
    ('childs', 'childs', 'children', 0.94,
     'She has three childs at home.', 'She has three children at home, and the child\'s toy is on the floor.',
     'The childs are playing outside.', 'The children are playing outside, and the child\'s coat is blue.'),
]
for slug, wrong, right, conf, pqp, pqn, tp, tn in PAIRS:
    # "my mans" is slang for "my friend": never flagged.
    dets = r"the|our|their|some|other|more|most|any|no|your|his|her" if slug == 'mans' else r"the|our|their|some|other|more|most|any|no|your|his|her|my"
    plural_pair(slug, wrong, right, conf, pqp, pqn, tp, tn, dets=dets)
cover('Irregular and Latin/Greek plurals', 'an irregular noun given -s that is also a possessive without its apostrophe or a verb (wolfs, knifes, leafs, wifes, lifes, halfs, shelfs, thiefs, calfs, loafs, elfs, mans, womans, childs): flagged after a plural quantifier, or after a determiner when a verb or the clause end follows; "the wolfs den" and "he wolfs down" are left alone',
      [f'irreg.{p[0]}_{k}' for p in PAIRS for k in 'nt'])

# a singular determiner before -s can only be a possessive typed without its apostrophe.
for slug, wrong, right, pos, neg in [
    ('mans_poss', 'mans', "man's", 'It was a mans world.', "It was a man's world, and the crew mans the pumps."),
    ('womans_poss', 'womans', "woman's", 'She heard a womans voice.', "She heard a woman's voice, and the woman is calm."),
    ('childs_poss', 'childs', "child's", 'Every childs smile counts.', "Every child's smile counts, and the children smile."),
]:
    add(f'irreg.{slug}', rf"(?i)\b(?:a|an|every|another|any|no)\s+(?P<target>(?-i:{wrong}))\s+[a-z]", right, 'Possessive', 0.9,
        f'A single person needs the possessive: “{right}”.', pos, neg)
cover('Irregular and Latin/Greek plurals', 'a mans / a womans / every childs + noun: possessive typed without the apostrophe', ['irreg.mans_poss', 'irreg.womans_poss', 'irreg.childs_poss'])

add('irreg.foots', rf"(?i)\b(?:{PQ}|the|these|those|my|your|his|her|our|their|bare|cold|sore|swollen|tired|wet|dirty|big|small)\s+(?P<target>(?-i:foots))\b",
    'feet', 'Grammar', 0.93, '“Foot” has the irregular plural “feet”.',
    'My foots are cold from the snow.', 'My feet are cold from the snow, and she foots the bill.')
add('irreg.gooses', rf"(?i)\b(?:{PQ}|the|these|those|wild|young|all)\s+(?P<target>(?-i:gooses))\b",
    'geese', 'Grammar', 0.93, '“Goose” has the irregular plural “geese”.',
    'The gooses fly south in autumn.', 'The geese fly south in autumn, and the goose is loud.')
add('irreg.dices', rf"(?i)\b(?:{PQ}|the|these|those|some|both|loaded)\s+(?P<target>(?-i:dices))\b",
    'dice', 'Grammar', 0.88, 'The plural of “die” and “dice” is “dice”.',
    'Roll the two dices again.', 'Roll the two dice again, and she dices onions for soup.')
add('irreg.fishes',
    r"(?i)\b(?:many|the|some|these|those|several|few|all|tropical|colorful|colourful|small|big|fresh|dead|live)\s+(?P<target>fishes)(?:\s*[,.;:!?)\"”]|\s*$|\s+(?:are|were|in|on|at|for|from|with|that|which|and|to|as|live|swim)\b)",
    'fish', 'Style', 0.7, '“Fish” is the usual plural for more than one fish; “fishes” is used only for several species.',
    'The tank holds many colorful fishes.', 'The tank holds many colorful fish, and the angler fishes at dawn; the fishes of the Nile include many species.')
cover('Irregular and Latin/Greek plurals', 'foots, gooses, dices (after a determiner or plural quantifier; "he foots the bill", "she dices onions" are verbs), fishes (suggestion: valid for species)',
      ['irreg.foots', 'irreg.gooses', 'irreg.dices', 'irreg.fishes'])

# Possessive plurals of the irregular nouns: the apostrophe goes before the s. The base spelling pass already turns
# "childrens museum" into "children's museum" (and "mens room" via punct.apostrophe.mens), but it also turns the plain
# plural "The childrens are here" into "children's are" and loops, so these rules stand above it (confidence 0.96 beats its 0.95).
for wrong, right, pl_pos, pl_neg in [
    ('childrens', "children's", 'The childrens are playing outside.', "The children are playing outside, and the children's toys are tidy; childrens and adults classes run at noon."),
    ('womens', "women's", 'The womens are leading the project.', "The women are leading the project, and the women's room is open; the club runs mens, womens and youth leagues."),
]:
    base = wrong[:-1]
    add(f'poss.{wrong}_plural', rf"(?i)\b(?P<target>{wrong})\s+(?:are|were|have|had|will|can|could|would|should|must|do|did|who|that|which|is|was|has)\b",
        base, 'Grammar', 0.96, f'“{base.capitalize()}” is already plural: no “s” is needed.', pl_pos, pl_neg)
    add(f'poss.{wrong}_apos', rf"(?i)\b(?P<target>{wrong}['’])(?:\s|$)", right, 'Possessive', 0.96,
        f'The possessive of “{base}” is “{right}”.',
        f"The {wrong}' ward has toys." if wrong == 'childrens' else f"The {wrong}' ward has beds.",
        f"The {right} ward has toys." if wrong == 'childrens' else f"The {right} ward has beds.")
for wrong, right in [('childrens', "children's"), ('womens', "women's"), ('mens', "men's")]:
    add(f'poss.{wrong}_double', rf"(?i)\b(?P<target>{wrong}['’]s)\b", right, 'Possessive', 0.96,
        f'“{wrong.capitalize()}” already has an “s” in it: “{right}”.',
        f"The {wrong}'s ward is on the left.", f"The {right} ward is on the left.")
cover('Possessive plurals', "childrens/womens before a verb -> children/women (not before a conjunction or the clause end: \"mens, womens and youth leagues\" is an elliptical possessive list) (the base spelling pass would loop on these); childrens'/womens' (apostrophe after the s) -> children's/women's; childrens's/womens's/mens's. Base rules already fix childrens/womens/mens + noun and mens'",
      ['poss.childrens_plural', 'poss.womens_plural', 'poss.childrens_apos', 'poss.womens_apos', 'poss.childrens_double', 'poss.womens_double', 'poss.mens_double'])
