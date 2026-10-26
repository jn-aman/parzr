"""Word lists for the agreement pack generator. All written by hand for this pack."""

# --- verbs: bare form; the third-person form is computed ---------------------------------------
# Excluded on purpose: verbs whose bare form is also the past ("read", "put", "cut", "set", "let", "hit",
# "hurt", "shut", "quit", "cost", "spread"), "come"/"run"/"become" (bare form is also the participle),
# "need"/"dare" (modals: "he need not"), "like" (chat filler: "and he like left"), "be", modals.
VERBS = """
accept add afford bark bloom shine agree allow announce answer appear apply argue arrive ask attend avoid bake believe belong
borrow bother break bring build burn buy call care carry catch cause change charge chat check choose claim
clean clear click close collect compare complain complete contain continue control cook copy cost_skip count
cover create cry cut_skip deal decide deliver demand depend describe design destroy develop die disagree
discuss do_skip drink drive drop earn eat enjoy enter escape exist expect explain fail fall fight fill find
finish fit fix fly follow forget forgive gain gather get give go grow guess handle happen hate have_skip
head hear help hide hold hope hurry identify imagine improve include increase intend invite join jump keep
kill knock know last laugh lead learn leave lend lie listen live lock look lose love maintain make manage
matter mean meet mention mind miss mix move need_skip notice offer open order owe own pack pay perform pick
plan play point post prefer prepare press pretend prevent print promise protect prove provide pull push
reach realize receive recommend record reduce refuse relate remain remember remove repeat reply report
represent require respond rest return reveal ride ring rise roll rule save say search see seem sell send
serve share shout show shut_skip sign sing sit sleep smile solve sound speak spend stand start stay steal
stop study succeed suffer suggest supply support suppose surprise survive take talk teach tell test thank
think throw touch train travel treat trust try turn type understand use visit vote wait wake walk want warn
wash waste watch wear win wish wonder work worry write
""".split()
VERBS = [v for v in VERBS if not v.endswith('_skip')]

# the thirty verbs the base grammar.json already covers at a sentence start (kept: mine cover mid-clause too)

def third(v):
    irregular = {'go': 'goes', 'do': 'does', 'have': 'has'}
    if v in irregular:
        return irregular[v]
    if v.endswith(('s', 'x', 'z', 'ch', 'sh')):
        return v + 'es'
    if v.endswith('y') and v[-2] not in 'aeiou':
        return v[:-1] + 'ies'
    return v + 's'

# verbs where third-person -s form is also a plural noun/noun phrase head, so "I/you <verb>s" is not a safe flag
# ("I give you works" ...): these are skipped for the I/you direction (still used for they/we)
NOUNISH_S = {'works', 'lives', 'looks', 'needs', 'wants', 'ends', 'costs', 'rules', 'plans', 'turns', 'uses',
             'starts', 'tests', 'reports', 'orders', 'records', 'prints', 'drops', 'ranks', 'signs', 'rings',
             'rests', 'types', 'points', 'posts', 'calls', 'changes', 'charges', 'checks', 'claims', 'clicks',
             'cares', 'cooks', 'copies', 'counts', 'covers', 'dies', 'drinks', 'fits', 'fights', 'finds',
             'falls', 'fills', 'flies', 'gains', 'goes', 'guesses', 'heads', 'helps', 'holds', 'hopes',
             'leads', 'links', 'locks', 'matters', 'meets', 'minds', 'mixes', 'moves', 'offers', 'packs',
             'picks', 'plays', 'promises', 'pulls', 'pushes', 'reaches', 'rides', 'rises', 'rolls', 'saves',
             'searches', 'seems', 'shares', 'shows', 'sits', 'smiles', 'sounds', 'stands', 'stays', 'stops',
             'studies', 'supplies', 'supports', 'talks', 'tests', 'thanks', 'throws', 'touches', 'trains',
             'travels', 'treats', 'trusts', 'tries', 'types', 'votes', 'walks', 'wears', 'wins', 'wishes',
             'worries', 'wraps', 'writes', 'answers', 'laughs', 'visits', 'deals', 'doubts', 'drives'}

# --- nouns ---------------------------------------------------------------------------------------
# Plural nouns that are safely plural everywhere (no singular -s homograph, no measure unit, no collective).
PL_PEOPLE = """people children men women students teachers employees  customers  users members
parents  kids players workers owners visitors guests officers officials doctors nurses patients engineers
developers designers writers readers authors leaders voters residents candidates applicants participants
passengers drivers soldiers tenants buyers sellers vendors suppliers contractors attendees volunteers
 partners investors shareholders stakeholders agents analysts reviewers moderators administrators
citizens politicians lawyers judges artists musicians singers fans supporters neighbors neighbours boys girls
babies  sisters mothers   wives sons  uncles   bosses
 classmates roommates strangers travelers tourists customers beginners experts professionals
researchers scientists reporters journalists editors publishers producers directors actors""".split()

PL_WORK = """files folders documents reports messages emails requests results changes updates tests details items
issues bugs errors mistakes tickets tasks projects plans notes records entries fields columns rows tables pages
links images photos pictures videos slides charts graphs numbers figures reasons options steps ideas questions
answers comments suggestions problems solutions topics goals rules features instructions directions
requirements specifications tools apps applications servers computers devices phones screens cables batteries
logs backups builds releases versions patches commits branches scripts functions variables parameters queries
tags labels templates forms invoices payments orders prices costs fees charges rates taxes accounts passwords
keys tokens codes sessions events meetings calls appointments deadlines schedules reminders attachments
downloads uploads drafts reviews proposals contracts agreements policies procedures guidelines standards
settings""".split()
# "settings", "files", "messages" are also app names: the generator matches these nouns in lower case only.

PL_HOME = """books cars bikes houses rooms doors windows chairs shoes dishes plates cups bags boxes toys games animals
dogs cats birds trees flowers plants vegetables apples oranges eggs cookies cakes meals ingredients streets
roads buildings shops stores schools classes lessons exams grades courses subjects lectures assignments essays
papers pictures songs movies films stories letters cards tickets coins stamps lights lamps clocks watches
shirts dresses hats gloves socks boots bottles cans jars bowls forks spoons knives""".split()

# Plural-only and always-plural nouns ("the scissors is")
PL_ONLY = """scissors jeans pants trousers shorts  leggings pajamas pyjamas clothes goods belongings premises
 surroundings remains outskirts binoculars   shears tongs groceries finances
earnings fireworks stairs glasses  police riches""".split()

# classical plurals
PL_CLASSICAL = """criteria  bacteria alumni analyses crises theses hypotheses oases stimuli  fungi cacti radii
curricula memoranda indices appendices matrices vertices  parentheses syntheses emphases""".split()

# Singular count nouns safely singular (no collective sense, no zero plural).
SG_PEOPLE = """manager friend client colleague coworker brother sister father mother son daughter uncle aunt cousin husband wife student teacher employee  customer  user member parent  player worker owner visitor
guest officer doctor nurse patient engineer developer designer writer reader author leader voter resident
candidate applicant participant passenger driver soldier tenant buyer seller
 partner agent analyst reviewer moderator administrator citizen politician
lawyer judge artist musician singer fan supporter neighbor neighbour boy girl man woman child person baby
 sister mother   wife son  uncle   boss  classmate roommate
stranger traveler tourist beginner expert professional researcher scientist reporter journalist editor
director actor""".split()

SG_WORK = """file folder document report message email request result change update test detail item issue bug error
mistake ticket task project plan note record entry field column row table page link image photo picture video
slide chart graph number figure reason option step idea question answer comment suggestion problem solution
topic goal rule feature instruction requirement specification tool app application server computer device
phone screen cable battery log backup build release version patch commit branch script function variable
parameter query tag label template form invoice payment order price cost fee charge rate tax account
password key token code session event meeting call appointment deadline schedule reminder attachment
download upload draft review proposal contract agreement policy procedure guideline standard setting""".split()

SG_HOME = """book car bike house room door window chair shoe dish plate cup bag box toy game animal dog cat bird tree
flower plant vegetable apple orange egg cookie cake meal ingredient street road building shop store
lesson exam grade course subject lecture assignment essay paper song movie film story letter card
coin stamp light lamp clock watch shirt dress hat glove sock boot bottle  jar bowl fork spoon knife""".split()

# Uncountable / mass nouns that take a singular verb ("the information are")
UNCOUNT = """information advice equipment furniture research feedback progress knowledge homework software luggage
baggage traffic weather music money water food evidence paperwork machinery jewelry jewellery clothing rubbish
garbage scenery news spam bread rice milk coffee tea sugar salt butter cheese meat vegetation wildlife
accommodation assistance training employment damage pollution violence behavior behaviour attention patience
honesty happiness education health safety mathematics physics linguistics genetics robotics measles mumps
diabetes""".split()

ADJ = """new old main first last whole entire other same final current previous latest following attached original
big small large little long short good bad best worst next only main whole major minor key full empty
public private local global total second third""".split()

# Heads whose own number decides the verb ("the list of items IS")
SG_HEADS = """list set collection number amount quality price cost size name title purpose use importance history role
meaning definition origin cause result outcome goal aim objective key secret point top bottom end beginning
middle front back side edge center centre owner author creator  director head leader member
president editor founder teacher  mother  sister son  wife   student
owner winner loser inventor designer maker writer builder driver captain coach chief captain price
cost effect impact role state level presence absence lack loss rise fall growth increase decrease
reduction purpose function structure design layout format version status condition risk benefit
cause reason answer solution price rate speed weight height length width depth color colour shape
look feel smell taste sound""".split()
SG_HEADS = sorted(set(SG_HEADS) - {'number'})   # "number" gets its own rules

PL_HEADS = """results names files reports members leaders owners authors parents  students teachers
 directors editors founders designers writers readers users customers  patients
employees players winners numbers prices costs rates levels sizes colors colours types kinds
reasons causes effects impacts roles goals aims points rules steps details questions answers
changes updates items entries records pages lines tracks songs titles images photos pictures
videos documents emails messages notes tasks tickets orders payments accounts""".split()

# Common given names for "Tom don't" style rules (case-sensitive, capitalised)
NAMES = """Tom Mary John Anna Peter Sarah David Emma James Laura Michael Lisa Daniel Maria Paul Susan Mark Julia
Ben Sophie Jack Kate Alex Nina Chris Amy Ryan Nick Ravi Priya Amit Neha Raj Sunita Ali Fatima Omar Aisha
Carlos Sofia Luis Elena Hans Anke Pierre Claire Wei Mei Yuki Kenji Ahmed Sara George Helen Henry Alice
Robert Linda Karen Steve Jessica Andrew Rachel Simon Hannah Oliver Grace Lucy Harry Charlie Jake Zoe""".split()
