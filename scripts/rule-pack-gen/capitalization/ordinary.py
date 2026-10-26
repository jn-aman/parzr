"""Lists the single-word names of the plain (no-context) families that are also ordinary lowercase dictionary words.
Each one needs a second look: a rule that capitalizes it everywhere is only safe if the lowercase reading is not
a real use ("terraform" the verb, "photoshop" the verb, "polish" the verb)."""
import json, sys, pathlib
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
import gen_acronyms, gen_brands, gen_holidays, gen_misc, gen_names, gen_places

lex = {w for w, _ in json.load(open(ROOT / 'engine/rules/lexicon.json'))}
low = {w for w in lex if w == w.lower()}
groups = {
    'brands': gen_brands.SIMPLE + gen_brands.LOWER_FIRST,
    'acronyms': gen_acronyms.SIMPLE,
    'holidays': gen_holidays.SIMPLE,
    'faith': gen_names.DEITIES + gen_names.SCRIPTURE,
    'countries': gen_places.COUNTRIES, 'regions': gen_places.REGIONS, 'cities': gen_places.CITIES,
    'langs': gen_places.LANGS, 'peoples': gen_places.PEOPLES,
    'world': gen_misc.PLANETS + gen_misc.ZODIAC + gen_misc.HISTORY + gen_misc.ORGS,
}
for name, items in groups.items():
    amb = [c for c in dict.fromkeys(items) if ' ' not in c and c.lower() in low]
    print(f'{name}: {amb}')
