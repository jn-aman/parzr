"""Adjective or adverb in the wrong slot: good/well, an adjective after a verb of doing, an adverb after a linking
verb, "real" for "really", and an adjective in front of a verb."""
from core import add, cover, tail, pick, IDS

# An adjective that ends the clause (or is followed by a word that can never be a noun) is acting as an adverb.
# The comma is left out on purpose: "plays good, clean football" is two adjectives.
GOOD_TAIL = (r"(?:[.!?;:)\n\"”]|\s*$|\s+(?:too|together|today|tonight|now|for|at|in|on|with|here|there|yesterday|"
             r"from|over|around|against|under|without|until|about|into|through|between|among|across|along|near|off|out|up|down|away|behind|beside|within|upon|again|last|this|anymore|anyway|either|yet|lately|then|when|since|but|so|because|though|while|if|after|before|during)\b)")

# (id, verb forms not already in usage.verb_well, positive, negative)
GOOD_VERBS = [
    ('play', 'play|playing', 'They can play good together.', 'They can play well together. Play good music for us. She plays well.'),
    ('speak', 'speak|speaking', 'He cannot speak good when he is nervous.', 'He cannot speak well when he is nervous. Speak good English with me. She speaks well.'),
    ('write', 'write|writing', 'I want to write good for the school paper.', 'I want to write well for the school paper. Write good code. He writes well.'),
    ('cook', 'cook|cooking', 'My mother can cook good.', 'My mother can cook well. Cook good food every day. He cooks well.'),
    ('dance', 'dance|dancing', 'She learned to dance good at school.', 'She learned to dance well at school. Dance good dances with us.'),
    ('drive', 'drive|driving', 'You need to drive good in the snow.', 'You need to drive well in the snow. He drives well.'),
    ('work', 'work|working', 'The new filter does not work good.', 'The new filter does not work well. Good work is rewarded. I like working with good people.'),
    ('run', 'run|running', 'The old laptop does not run good anymore.', 'The old laptop does not run well anymore. Run good programs on it. She runs well.'),
    ('perform', 'perform|performing', 'The team did not perform good in the final.', 'The team did not perform well in the final. Perform good deeds.'),
    ('sing_ing', 'singing', 'He is singing good tonight.', 'He is singing well tonight. She likes singing good songs.'),
    ('go', 'go|going', 'The meeting is going good so far.', 'The meeting is going well so far. Go good and slow into the turn. We are going to a good restaurant.'),
    ('sleep', 'sleep|sleeps|slept|sleeping', 'I slept good last night.', 'I slept well last night. Sleep is good for you. A good sleep helps.'),
    ('swim', 'swim|swims|swam|swimming', 'My son swims good for his age.', 'My son swims well for his age. He swims in a good pool.'),
    ('read', 'read|reads|reading', 'The sign is too small to read good from here.', 'The sign is too small to read well from here. She reads good books.'),
    ('listen', 'listen|listens|listened|listening', 'Our dog does not listen good.', 'Our dog does not listen well. Listen to good advice.'),
    ('see', 'see|sees|saw|seeing', 'My grandfather cannot see good without his glasses.', 'My grandfather cannot see well without his glasses. We saw a good film. I can see good in everyone.'),
    ('hear', 'hear|hears|heard|hearing', 'I cannot hear good from the back row.', 'I cannot hear well from the back row. I heard good news. We hear good in the quiet.'),
    ('understand', 'understand|understands|understood|understanding', 'I do not understand good when people talk fast.', 'I do not understand well when people talk fast. He understood good manners.'),
    ('learn', 'learn|learns|learned|learnt|learning', 'Children learn good when they are curious.', 'Children learn well when they are curious. Learn good habits early.'),
    ('teach', 'teach|teaches|taught|teaching', 'Her professor teaches good so everyone passes.', 'Her professor teaches well and everyone passes. He taught good manners.'),
    ('fight', 'fight|fights|fought|fighting', 'Our team fought good until the last minute.', 'Our team fought well until the last minute. Fight for good causes.'),
    ('communicate', 'communicate|communicates|communicated|communicating', 'He does not communicate good with the staff.', 'He does not communicate well with the staff. They communicate good news first.'),
    ('handle', 'handle|handles|handled|handling', 'The new phone handles good in the cold.', 'The new phone handles well in the cold. She handled good news calmly.'),
    ('manage', 'manage|manages|managed|managing', 'She managed good under pressure.', 'She managed well under pressure. He manages good teams.'),
    ('behave', 'behave|behaves|behaved|behaving', 'The children behaved good at the museum.', 'The children behaved well at the museum. They are good children.'),
    ('type', 'type|types|typed|typing', 'He types good after a little practice.', 'He types well after a little practice. She types good letters.'),
    ('fit', 'fits|fitted|fitting', 'The new jacket fits good around the shoulders.', 'The new jacket fits well around the shoulders. It is a good fit.'),
    ('function', 'function|functions|functioned|functioning', 'The old pump still functions good.', 'The old pump still functions well. It has a good function.'),
    ('cope', 'cope|copes|coped|coping', 'He copes good with the pressure.', 'He copes well with the pressure. She copes with good humour.'),
    ('sell', 'sells|sold|selling', 'The new flavor sells good in the north.', 'The new flavor sells well in the north. He sold good wine.'),
    ('ride', 'rides|rode|riding', 'The new bike rides good on rough roads.', 'The new bike rides well on rough roads. They rode a good horse.'),
    ('draw', 'draws|drew|drawing', 'My daughter draws good for her age.', 'My daughter draws well for her age. She drew good pictures.'),
    ('paint', 'paint|paints|painted|painting', 'He paints good but slowly.', 'He paints well, but slowly. He paints good, honest pictures.'),
    ('dress', 'dress|dresses|dressed|dressing', 'She always dresses good for work.', 'She always dresses well for work. She wore a good dress.'),
    ('bake', 'bake|bakes|baked|baking', 'My aunt bakes good for the local shop.', 'My aunt bakes well for the local shop. She bakes good bread.'),
    ('shoot', 'shoot|shoots|shooting', 'He does not shoot good from the left.', 'He does not shoot well from the left. They shoot good photos.'),
    ('jump', 'jump|jumps|jumped|jumping', 'The horse jumped good over every fence.', 'The horse jumped well over every fence. It jumped a good height.'),
    ('compete', 'compete|competes|competed|competing', 'Our small team competes good against bigger clubs.', 'Our small team competes well against bigger clubs. They compete in good faith.'),
    ('get_along', 'get along|gets along|got along|getting along|get on|gets on|got on|getting on', 'My brothers get along good now.', 'My brothers get along well now. They get on with good humour.'),
    ('worked_out', 'work out|works out|worked out|working out', 'Our plan worked out good in the end.', 'Our plan worked out well in the end. It worked out good value. A good work out helps.'),
    ('treat_pronoun', '(?:treat|treats|treated|treating) (?:me|him|her|us|them|you|people|everyone|everybody|customers|employees|workers|staff|others|animals|dogs|kids|children)',
     'My manager treats everyone good.', 'My manager treats everyone well. He treats good ideas seriously.'),
]


def build():
    # ---- "good" where "well" is needed: verbs that the base rule usage.verb_well does not list
    ids = []
    for key, forms, pos, neg in GOOD_VERBS:
        t = GOOD_TAIL if key not in ('see', 'hear') else r"(?:[.!?;:)\n\"”]|\s*$|\s+(?:without|from|at|today|now|anymore|lately)\b)"
        ids.append(add(
            f'good_{key}',
            rf"(?i)\b(?:{forms}) (?:(?:really|so|very|pretty|too|not) )?(?P<target>good){t}",
            'well', 'Grammar', 0.9,
            '“Good” describes a noun. To say how something is done, use the adverb “well”.', pos, neg))
    cover('Good and well', 'verb + good where "well" is meant: play, speak, write, cook, dance, drive, work, run, perform, singing, go, sleep, swim, read, listen, see, hear, understand, learn, teach, fight, communicate, handle, manage, behave, type, fit, function, cope, sell, ride, draw, paint, dress, bake, shoot, jump, compete, get along, work out, treat someone (the inflected forms sings/plays/works/runs/writes/cooks/dances/speaks/drives are base usage.verb_well; "did good" is base usage.did_well; "feel badly" and "doing good" are left)', ids)

    ids = []
    for key, verbs, pos, neg in [
        ('taste', 'tastes?|tasted', 'The soup tastes well.', 'The soup tastes good, but it needs salt. The cook tasted it well.'),
        ('sound', 'sounds?|sounded', 'That plan sounds well to me.', 'That plan sounds good to me. It is all well and good.'),
        ('smell', 'smells?|smelled|smelt', 'Something in the kitchen smells well.', 'Something in the kitchen smells good. The dog smells well.'),
    ]:
        # well as a predicate adjective after a sense verb ("tastes well"); "looks well" and "feels well" are health
        # idioms, "sounds well and good" is the idiom "well and good"
        subj = {'taste': '', 'sound': '', 'smell': ''}[key]
        pat = rf"(?i)\b(?:{verbs}) (?:(?:really|so|very|pretty) )?(?P<target>well)(?:[.!?;:)\n\"”]|\s*$|\s+(?:to|for|with|today|now)\b)"
        if key == 'smell':
            pat = rf"(?i)\b(?:it|this|that|something|everything|the food|the room|the kitchen|the house) (?:{verbs}) (?:(?:really|so|very|pretty) )?(?P<target>well)(?:[.!?;:)\n\"”]|\s*$)"
        ids.append(add(
            f'well_{key}', pat, 'good', 'Grammar', 0.9,
            f'After “{key}”, describe the thing with the adjective “good”, not the adverb “well”.', pos, neg))
    ids.append(add(
        'have_a_well_day',
        r"(?i)\b(?:have|had|having|wish(?:ed)? you|hope you (?:have|had)|hope you[’']ll have|and) an? (?P<target>well) (?:day|weekend|time|week|evening|night|holiday|vacation|trip|flight|journey|morning|afternoon|one|year|summer|winter|break|life|sleep)\b",
        'good', 'Grammar', 0.92, 'Before a noun, use the adjective “good”, not the adverb “well”.',
        'I hope you have a well weekend.', 'I hope you have a good weekend. She is well and happy. We all had a well-earned break.'))
    for noun in ['teacher', 'friend', 'student', 'player', 'worker', 'writer', 'speaker', 'cook', 'driver', 'idea', 'job',
                 'choice', 'decision', 'example', 'plan', 'reason', 'story', 'movie', 'film', 'book', 'school', 'doctor',
                 'manager', 'leader', 'father', 'mother', 'husband', 'wife', 'boy', 'girl', 'team', 'result']:
        ids.append(add(
            f'a_well_{noun}', rf"(?i)\b(?:an?|the|my|our|your|his|her|their|this|that|such) (?P<target>well) {noun}\b",
            'good', 'Grammar', 0.9, f'Before “{noun}” use the adjective “good”, not the adverb “well”.',
            f'She is a well {noun}.',
            f'She is a good {noun}. The old well is dry, and he is well.'))
    cover('Good and well', 'well after taste/smell/sound ("tastes well"), "have a well day", "a well teacher/friend/idea/job ..." (health uses "a well baby" and "a well person" are left alone)', ids)
