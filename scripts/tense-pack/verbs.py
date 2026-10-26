"""Verb data for the tense/aspect pack generator. One row per verb:
base third past participle gerund | tail | kind | flags
kind: T transitive, I intransitive, B both.  tail: a natural complement that follows the verb.
flags: a past form is also a noun/base verb/name (amb), participle variant accepted (var), rare verb (rare)."""

STRONG = """
arise arises arose arisen arising | from the delay | I | rare
bite bites bit bitten biting | the apple | T | amb
blow blows blew blown blowing | the whistle | T
break breaks broke broken breaking | the window | T | amb
choose chooses chose chosen choosing | the red one | T
come comes came come coming | home early | I
do does did done doing | the work | T
draw draws drew drawn drawing | a picture | T | amb
drink drinks drank drunk drinking | the water | T
drive drives drove driven driving | the truck | T
eat eats ate eaten eating | the cake | T
fall falls fell fallen falling | off the ladder | I | amb
fly flies flew flown flying | to Paris | I
forbid forbids forbade forbidden forbidding | the sale | T | rare
forget forgets forgot forgotten forgetting | the password | T
forgive forgives forgave forgiven forgiving | the mistake | T
freeze freezes froze frozen freezing | the pipes | T
give gives gave given giving | the money | T
go goes went gone going | to the market | I
grow grows grew grown growing | tomatoes | T
hide hides hid hidden hiding | the keys | T | var
know knows knew known knowing | the answer | T
lie lies lay lain lying | in bed | I | amb
mistake mistakes mistook mistaken mistaking | the signal | T
overcome overcomes overcame overcome overcoming | the fear | T
override overrides overrode overridden overriding | the setting | T
ride rides rode ridden riding | the bus | T
ring rings rang rung ringing | the bell | T
rise rises rose risen rising | to the top | I | amb
run runs ran run running | the test | T
see sees saw seen seeing | the movie | T | amb
shake shakes shook shaken shaking | the box | T
shrink shrinks shrank shrunk shrinking | the shirt | T
sing sings sang sung singing | the song | T
sink sinks sank sunk sinking | the boat | T
speak speaks spoke spoken speaking | to him | I
spring springs sprang sprung springing | into action | I
steal steals stole stolen stealing | the wallet | T
strive strives strove striven striving | for success | I | rare
swear swears swore sworn swearing | an oath | T
swim swims swam swum swimming | across the lake | I
take takes took taken taking | the bus | T
tear tears tore torn tearing | the paper | T
throw throws threw thrown throwing | the ball | T
undergo undergoes underwent undergone undergoing | surgery | T
undertake undertakes undertook undertaken undertaking | the task | T
undo undoes undid undone undoing | the change | T
wake wakes woke woken waking | the baby | T
wear wears wore worn wearing | a coat | T
weave weaves wove woven weaving | a basket | T
withdraw withdraws withdrew withdrawn withdrawing | the offer | T
write writes wrote written writing | a letter | T
overtake overtakes overtook overtaken overtaking | the truck | T
rewrite rewrites rewrote rewritten rewriting | the section | T
redo redoes redid redone redoing | the report | T
outgrow outgrows outgrew outgrown outgrowing | the shoes | T
foresee foresees foresaw foreseen foreseeing | the problem | T
oversee oversees oversaw overseen overseeing | the project | T
retake retakes retook retaken retaking | the exam | T
partake partakes partook partaken partaking | in the feast | I | rare
forsake forsakes forsook forsaken forsaking | his friends | T | rare
slay slays slew slain slaying | the dragon | T | rare
tread treads trod trodden treading | on the grass | I | rare
overdo overdoes overdid overdone overdoing | it | T
overeat overeats overate overeaten overeating | at dinner | I
overthrow overthrows overthrew overthrown overthrowing | the government | T
begin begins began begun beginning | the lesson | B
become becomes became become becoming | a doctor | I
"""

# V2 == V3 irregulars (the confusion is with the base form or a regularized "-ed")
SAME = """
bend bends bent bent bending | the wire | T
bind binds bound bound binding | the books | T | amb
bleed bleeds bled bled bleeding | for hours | I
breed breeds bred bred breeding | horses | T
bring brings brought brought bringing | the documents | T
build builds built built building | a house | T
buy buys bought bought buying | a car | T
catch catches caught caught catching | the train | T
cling clings clung clung clinging | to the rope | I
creep creeps crept crept creeping | inside | I
deal deals dealt dealt dealing | with the issue | I
dig digs dug dug digging | a hole | T
feed feeds fed fed feeding | the cat | T
feel feels felt felt feeling | the pain | T | amb
fight fights fought fought fighting | the fire | T
find finds found found finding | the key | T | amb
flee flees fled fled fleeing | the city | B
fling flings flung flung flinging | the door open | T
grind grinds ground ground grinding | the coffee | T | amb
hang hangs hung hung hanging | the picture | T
hear hears heard heard hearing | the news | T
hold holds held held holding | the meeting | T
keep keeps kept kept keeping | the receipt | T
kneel kneels knelt knelt kneeling | on the floor | I
lay lays laid laid laying | the foundation | T
lead leads led led leading | the team | T
leave leaves left left leaving | the office | T | amb
lend lends lent lent lending | me money | T
lose loses lost lost losing | the game | T
make makes made made making | a cake | T
mean means meant meant meaning | no harm | T
meet meets met met meeting | the client | T
pay pays paid paid paying | the bill | T
say says said said saying | hello | T
seek seeks sought sought seeking | advice | T
sell sells sold sold selling | the house | T
send sends sent sent sending | the email | T
shine shines shone shone shining | brightly | I
shoot shoots shot shot shooting | the film | T
sit sits sat sat sitting | in the chair | I
sleep sleeps slept slept sleeping | well | I
slide slides slid slid sliding | down the hill | I
spend spends spent spent spending | the money | T
spin spins spun spun spinning | the wheel | T
stand stands stood stood standing | in line | I
stick sticks stuck stuck sticking | to the plan | I
sting stings stung stung stinging | the skin | T
strike strikes struck struck striking | the target | T
sweep sweeps swept swept sweeping | the floor | T
swing swings swung swung swinging | the bat | T
teach teaches taught taught teaching | the class | T
tell tells told told telling | the story | T
think thinks thought thought thinking | about it | I
understand understands understood understood understanding | the rules | T
weep weeps wept wept weeping | for hours | I
win wins won won winning | the prize | T
wind winds wound wound winding | the clock | T | amb
wring wrings wrung wrung wringing | the cloth | T | rare
withhold withholds withheld withheld withholding | payment | T
uphold upholds upheld upheld upholding | the decision | T
overhear overhears overheard overheard overhearing | the talk | T
mislead misleads misled misled misleading | customers | T
misunderstand misunderstands misunderstood misunderstood misunderstanding | the question | T
rebuild rebuilds rebuilt rebuilt rebuilding | the bridge | T
repay repays repaid repaid repaying | the loan | T
retell retells retold retold retelling | the story | T
rethink rethinks rethought rethought rethinking | the plan | T
foretell foretells foretold foretold foretelling | the future | T | rare
"""


def parse(block):
    rows = []
    for line in block.strip().splitlines():
        left, tail, kind, *flags = [x.strip() for x in line.split('|')] + ['']
        forms = left.split()
        base, third, past, part, ing = forms
        rows.append(dict(base=base, third=third, past=past, part=part, ing=ing, tail=tail, kind=kind,
                         flags=set((flags[0] if flags else '').split())))
    return rows


STRONG_ROWS = parse(STRONG)
SAME_ROWS = parse(SAME)
ALL_ROWS = STRONG_ROWS + SAME_ROWS
