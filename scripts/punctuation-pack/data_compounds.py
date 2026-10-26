"""Compound modifiers that take a hyphen before the noun they describe ("a data-driven team") and stay open after it or
in the predicate ("the team is data driven"). One line per compound: the open form, then " :: ", then the head nouns
that follow it (singular; a trailing * marks a noun with no plural; +G adds the general list in lists.GEN).
Compounds the engine already hyphenates (long term, short term, full time, part time, last minute, real time, open
source, third party, high quality, low cost, high level, low level, high end, first class, world class, long distance,
high speed, up to date, out of date, state of the art, once in a lifetime, face to face, day to day, end to end, one on
one, well thought out, so called, old fashioned, long lasting, large scale, small scale, full scale, top notch, step
by step, user friendly, cutting edge, follow up, decision making, in person, on call, same day, next day, year end,
"well" plus a participle, "ex-", "X based") and the noun forms the confusions pack hyphenates (check in, sign in, opt in,
warm up, drop off ...) are left to them."""

# --- people, work and results ---------------------------------------------------------------------------------------
PEOPLE_WORK = """
hard working :: team employee worker staff person man woman people family professional student parent farmer mother father
high paying :: job career position role industry field profession occupation
low paying :: job career position role industry field profession occupation
award winning :: author film movie series show team service product designer chef restaurant writer director novel book
record breaking :: performance season year profit sale revenue temperature heat attendance run win
best selling :: author book novel product item album title series single
top selling :: product item album single model brand game title car
top performing :: employee team fund stock salesperson student school
high performing :: team employee organization company athlete system fund student school
low performing :: school student employee team fund stock
game changing :: idea innovation technology product feature move play decision change discovery
life changing :: experience event decision moment injury surgery diagnosis opportunity
mind blowing :: experience result performance fact idea view show
mind boggling :: number amount scale complexity fact
eye catching :: design headline color colour logo display feature graphic outfit poster
eye opening :: experience trip lesson report book moment
heart warming :: story moment gesture tale
heart breaking :: story news loss moment scene
thought provoking :: question film book article idea discussion essay
mouth watering :: aroma dish smell menu recipe
hard hitting :: report article story journalism documentary
fast acting :: formula relief medicine treatment
fast moving :: market industry world situation story car
fast paced :: environment world game industry workplace life story action
fast growing :: company market industry business sector city economy
slow moving :: traffic process line project
free flowing :: conversation discussion style
free standing :: structure bathtub tub sign unit
high flying :: career executive lawyer banker
far reaching :: consequence implication effect change impact reform decision
wide ranging :: discussion survey review reform study
far fetched :: idea story claim theory plot
long standing :: tradition relationship policy member customer partner rule tension rivalry
long running :: series show feud dispute program programme joke
long awaited :: return release update decision report
short lived :: success trend career peace joy
time consuming :: process task job project activity part step work effort procedure
time saving :: tool tip feature device shortcut
money saving :: tip tool deal feature hack
cost saving :: measure measures* tip initiative feature opportunity
labor saving :: device machine
life saving :: treatment surgery drug equipment device measure technology
life threatening :: illness injury condition disease situation allergy emergency
ever changing :: world landscape environment market need requirement
ever growing :: list demand number population market team
ever increasing :: demand cost number pressure
ever present :: threat danger risk reminder
ever evolving :: landscape field world threat industry
ever expanding :: universe list market network
never ending :: story battle cycle list stream search
open ended :: question discussion contract task
open minded :: person attitude approach friend
narrow minded :: person view attitude
strong willed :: child person woman man leader
big hearted :: man woman person
kind hearted :: man woman person soul
warm hearted :: man woman person
light hearted :: comedy moment tone approach banter film
good natured :: person fun man woman rivalry teasing
ill advised :: move decision plan attempt
ill conceived :: plan idea project scheme
ill fitting :: shoe shoes* suit clothes* dress
like minded :: person people individual friend professional
full blown :: crisis war panic campaign investigation attack version
full length :: film movie album mirror dress book novel feature
full body :: workout massage scan mirror
full service :: restaurant agency bank provider firm marketing
middle aged :: man woman person couple adult
left handed :: man woman player pitcher person batter
right handed :: man woman player pitcher person batter
two faced :: person liar friend
hand held :: device camera computer unit vacuum
hand picked :: team selection group
hand written :: note letter card sign
sun dried :: tomato
oven baked :: chicken potato fries dish
pan fried :: chicken fish steak
deep fried :: chicken fish food snack
slow cooked :: beef pork stew meal meat
wood fired :: pizza oven stove
wood burning :: stove fireplace
gas powered :: engine car generator tool
battery powered :: device toy tool light camera
solar powered :: light device charger car home
voice activated :: assistant device system
touch sensitive :: screen panel button
heat resistant :: glass material coating
water resistant :: watch jacket coating material
stain resistant :: fabric coating carpet
scratch resistant :: glass coating screen
fire resistant :: material coating door
heat sensitive :: material
weight bearing :: exercise wall
load bearing :: wall beam
""".strip().splitlines()

# --- orientation, criticality, efficiency, friendliness -------------------------------------------------------------
ORIENT = """
data driven :: approach team decision culture strategy company organization insight
customer facing :: team role staff application website employee position
customer centric :: approach strategy company culture design
customer focused :: approach team strategy company
results oriented :: manager team professional approach
goal oriented :: person team approach
detail oriented :: person professional worker
task oriented :: approach person
solution oriented :: approach person team
service oriented :: architecture company approach
family oriented :: person company community
user centered :: design approach
user centric :: design approach
human centered :: design approach
people centric :: approach culture
mission critical :: system application data service
safety critical :: system application
business critical :: system application data service
time critical :: task information system
time sensitive :: information task matter material
cost effective :: solution way option approach alternative treatment
cost efficient :: solution way option
energy efficient :: appliance home building bulb light
fuel efficient :: car vehicle engine
space saving :: design solution
family friendly :: hotel restaurant resort event movie place workplace neighborhood neighbourhood
kid friendly :: restaurant recipe hotel meal
child friendly :: environment hotel space
pet friendly :: hotel apartment rental home
dog friendly :: hotel beach park
beginner friendly :: guide course tutorial tool
mobile friendly :: website site design layout page
budget friendly :: option hotel meal choice
wallet friendly :: option
vegan friendly :: restaurant menu option
developer friendly :: platform tool
customer friendly :: policy service approach
reader friendly :: format layout
""".strip().splitlines()

# --- "-free" --------------------------------------------------------------------------------------------------------
FREE = """
tax free :: allowance shopping savings account status income purchase threshold
duty free :: shop store allowance goods shopping
interest free :: loan credit period payment
risk free :: trial investment guarantee return
stress free :: experience life travel way
hassle free :: experience process way return
sugar free :: drink gum candy diet version soda
gluten free :: bread diet option menu pasta product
dairy free :: milk option recipe
lactose free :: milk option
fat free :: yogurt milk dressing
caffeine free :: coffee soda tea
fragrance free :: product soap lotion
ad free :: experience version browsing
cruelty free :: product brand cosmetic
pain free :: life movement
trouble free :: operation journey
worry free :: retirement experience
lead free :: gasoline paint solder
nut free :: snack option product
alcohol free :: beer drink wine
smoke free :: environment workplace zone
drug free :: workplace zone school
rent free :: period accommodation
""".strip().splitlines()

# --- grades and levels, income and class ----------------------------------------------------------------------------
GRADES = """
food grade :: silicone plastic material oil
military grade :: encryption weapon equipment hardware
medical grade :: device silicone equipment
enterprise grade :: security software solution platform
production grade :: system code database
commercial grade :: equipment appliance
professional grade :: equipment camera tool
entry level :: job position role salary employee developer engineer
mid level :: manager position role developer engineer
senior level :: position role manager executive
top level :: domain manager management executive
executive level :: position role job
board level :: support position
expert level :: knowledge skill
low income :: family household housing country area student worker neighborhood community resident group
high income :: family household country earner group
middle income :: family household country earner
middle class :: family neighborhood neighbourhood household suburb value voter
working class :: family neighborhood neighbourhood hero community
lower class :: family
fixed rate :: mortgage loan plan contract
flat rate :: fee shipping pricing charge tax payment
fixed term :: contract deposit
fixed price :: contract quote project
variable rate :: mortgage loan
""".strip().splitlines()

# --- "-sized" and related -------------------------------------------------------------------------------------------
SIZED = """
medium sized :: company business city organization firm enterprise
mid sized :: company business city organization firm
small sized :: company business city organization
large sized :: company business city organization
full sized :: car bed truck keyboard
king sized :: bed mattress
queen sized :: bed mattress
bite sized :: piece snack portion chunk
life sized :: statue model doll
pocket sized :: camera guide
travel sized :: bottle toiletry
family sized :: pack car
pint sized :: hero
fun sized :: candy bar
good sized :: house room garden
decent sized :: house room garden
mid size :: sedan car company business city
full size :: bed car truck keyboard
life size :: statue model doll
""".strip().splitlines()

# --- stakes, risk, performance, tech --------------------------------------------------------------------------------
LEVELS = """
double digit :: growth inflation increase decline gain rate return margin
single digit :: temperature growth inflation number percentage
triple digit :: temperature growth number
high stakes :: game decision test poker environment situation negotiation gamble election exam
high risk :: patient group investment area activity behavior behaviour pregnancy environment strategy user category customer client factor situation job sport loan
low risk :: investment patient option strategy approach
high impact :: work project change initiative activity exercise workout event area
low impact :: exercise workout activity option
high profile :: case client position job event customer project target figure visit role launch
low profile :: position job approach
high performance :: computing car team engine culture cluster system storage graphics network processor athlete vehicle
high volume :: business customer order sale
low volume :: business order
high traffic :: area website site road page
high availability :: cluster system setup
high density :: housing development storage
low density :: housing development area
high resolution :: image photo display screen camera scan
low resolution :: image photo display screen
high definition :: video image television camera
high frequency :: trading signal word
low frequency :: sound noise signal
high pressure :: system situation sale environment hose
low pressure :: system area hose
high temperature :: environment application setting
low temperature :: environment application setting
high tech :: company industry gadget equipment product solution world firm field job startup hub sector device gear
low tech :: solution option approach
high protein :: diet snack food meal breakfast shake bar
low carb :: diet snack food meal breakfast recipe
low calorie :: diet snack food meal option drink
low fat :: diet snack food meal option milk
low sodium :: diet option soup
high calorie :: diet snack food meal
high fat :: diet food meal
high carb :: diet food meal
high fiber :: diet cereal food snack
high maintenance :: client customer person plant
low maintenance :: plant garden lawn car design solution option
high pitched :: voice noise sound squeal
low pitched :: voice noise sound hum
high priced :: product item hotel
low priced :: product item hotel option
mid priced :: product item hotel option
high rise :: building apartment tower condo office hotel block
low rise :: building apartment tower condo office hotel block
mid rise :: building apartment tower condo office hotel block
high strength :: steel alloy material
high security :: prison area facility
low light :: condition photography environment
high contrast :: image display mode theme
high gloss :: finish paint magazine
high energy :: drink music team workout dance atmosphere performance
low energy :: bulb light lamp
high yield :: savings bond account crop investment
low yield :: bond account crop investment
high ticket :: item sale product
low code :: platform development tool solution application app
no code :: platform tool solution app builder development
""".strip().splitlines()

# --- open/closed, long/short, other adjective pairs -----------------------------------------------------------------
OPEN = """
open plan :: office kitchen layout living space
open air :: market theater theatre museum concert restaurant cinema festival gym event
open door :: policy event
open book :: exam test policy management
open access :: journal article publishing repository policy paper
open top :: bus car truck tour
open toe :: shoe shoes* sandal heel
closed door :: meeting session policy negotiation hearing discussion
closed loop :: system control recycling process feedback economy
open loop :: system control
closed circuit :: television camera system video
full fat :: milk cheese yogurt yoghurt version cream
long haul :: flight truck route trip driver travel carrier destination
short haul :: flight route trip
long range :: plan forecast goal missile radar target shot
short range :: plan forecast goal missile radar target
mid range :: phone laptop camera model option speaker car price
long life :: battery milk bulb
long form :: content journalism video article essay story writing post
short form :: video content story writing
full page :: ad spread photo image view advert screenshot layout
half page :: ad spread photo image
double page :: spread
single page :: application app site website layout document summary report
brand new :: car phone design home model product look book laptop building approach feature version idea
down to earth :: approach person guy attitude style advice manner
good looking :: man guy woman boy girl couple actor family kid
great looking :: car design website phone photo
nice looking :: car house design website
best looking :: man woman car
late night :: show talk host comedy snack shift bus shopping meeting session craving pizza
early morning :: flight run shift meeting workout call commute coffee fog hour
late stage :: cancer capitalism company startup investor funding development trial disease project
early stage :: company startup investor investment cancer funding development venture research project idea disease product
end stage :: renal kidney disease liver cancer failure care
full stack :: developer engineer application web solution development framework team
real world :: example application experience scenario situation data problem use test performance result condition testing impact environment skill project
real life :: example situation story scenario experience application event people problem case character couple
next generation :: technology product system network console sequencing leader platform model vehicle software battery
next gen :: technology product system network console platform model vehicle software battery
next level :: performance gaming experience technology
new age :: music spirituality religion medicine
old school :: style approach method hip-hop rap cool charm way technique
new school :: style approach method
old world :: charm style wine elegance craftsmanship flavor
old time :: radio music charm religion
last ditch :: effort attempt bid appeal hope
last gasp :: equalizer winner effort
last second :: shot decision change goal save
""".strip().splitlines()

# --- in-/on-/off- and other prepositional modifiers -----------------------------------------------------------------
PREP = """
built in :: camera microphone speaker feature function support storage battery protection security help tool mechanism flash memory browser
hands on :: experience training approach learning workshop lab session demonstration management role involvement support knowledge practice class activity exercise guide tutorial work course
hands off :: approach policy management style leadership parenting
hands free :: calling mode device kit operation driving system phone headset option technology tool steering faucet
on site :: support training visit inspection service staff storage parking daycare childcare facility team installation consultation
off site :: storage meeting backup location training event parking
in house :: team expert counsel developer solution training production staff lawyer designer
in app :: purchase message notification ad chat feedback survey support currency billing product subscription
in store :: pickup shopping purchase event experience promotion sale credit service
in depth :: analysis review look knowledge study guide report interview understanding discussion research article coverage
in flight :: entertainment meal service wifi magazine
in game :: purchase currency item chat event
in home :: care service visit
on demand :: video service delivery access streaming economy content training webinar printing
on screen :: display keyboard text instruction prompt message button
on campus :: housing job event interview parking student resident
off campus :: housing job apartment student
on board :: computer camera storage diagnostics entertainment
one off :: event cost payment fee purchase project expense charge sale deal occurrence exception job order custom special fix
one time :: fee payment offer purchase charge password code use cost setup event deal donation investment license fix
one way :: ticket street trip mirror door flight fare road traffic
two way :: street communication conversation radio mirror ticket traffic door flow dialogue relationship sync valve switch
three way :: tie split call conversation race merger deal street
round trip :: ticket flight fare distance journey time airfare transfer commute drive hike
back to back :: game meeting win title season day year loss class call championship appointment
side by side :: comparison view layout display test analysis seating refrigerator fridge installation trial testing panel
year over year :: growth increase decline change comparison revenue sale performance improvement gain drop trend rate
month over month :: growth increase decline change comparison revenue sale performance improvement gain drop trend rate
quarter over quarter :: growth increase decline change comparison revenue sale performance improvement gain drop trend rate
week over week :: growth increase decline change comparison revenue sale performance improvement gain drop trend rate
day over day :: growth increase decline change comparison revenue sale performance improvement gain drop trend rate
year to date :: revenue sale total figure performance spending earnings data balance number result return gain growth profit
month to date :: revenue sale total figure performance spending earnings data balance number result profit
quarter to date :: revenue sale total figure performance spending earnings data balance number result profit
cross functional :: team collaboration project initiative communication alignment stakeholder meeting work group leadership
cross platform :: app application development framework tool support compatibility game
cross border :: trade payment transaction shipping travel merger investment collaboration
cross cultural :: communication training understanding exchange team
cross country :: skiing trip flight move race road journey drive travel trek team championship
cross team :: collaboration communication meeting project
cross browser :: compatibility testing support
cross device :: tracking experience sync support
cross sectional :: study survey analysis design
cross disciplinary :: team research approach collaboration study
cross channel :: marketing campaign experience
cross department :: collaboration communication project team
cross industry :: collaboration partnership
off grid :: living cabin solar home power system solution lifestyle
off road :: vehicle driving trail tire racing bike adventure capability truck park course
off peak :: hour season rate time travel fare pricing electricity period ticket demand
off season :: training sale rate price discount travel camp workout work period
off white :: color colour paint wall dress shade finish cabinet background
off brand :: version product knockoff
off label :: use prescription drug treatment medication marketing
off topic :: question comment post discussion conversation thread remark
off the cuff :: remark comment speech joke response
off the record :: conversation comment remark briefing meeting interview statement discussion session
off the wall :: idea humor humour comedy question suggestion
off the shelf :: solution software product option item tool component
out of the box :: solution experience functionality thinking feature
over the counter :: medication drug medicine product remedy
over the top :: reaction performance response design decor claim behavior behaviour party display drama costume
over the air :: update programming download firmware television broadcast signal upgrade software
over the shoulder :: bag shot strap holster
under the table :: payment deal cash work money arrangement
on the job :: training experience learning injury safety
behind the scenes :: look view footage glimpse tour work story
round the clock :: monitoring care service support coverage access
around the clock :: monitoring care service support coverage access
in your face :: attitude style approach advertising marketing music comedy politics
tongue in cheek :: humor humour tone comment remark reference response style article approach manner title
tried and true :: method formula approach technique recipe strategy way solution
tried and tested :: method formula approach technique recipe strategy way solution
bread and butter :: issue business product income work customer service dish
hit and miss :: approach affair proposition basis result performance attempt method
hit or miss :: approach affair proposition result performance attempt method
touch and go :: situation moment
rough and tumble :: world politics play environment business life
up and coming :: artist star talent musician actor band designer neighborhood brand company
up front :: cost payment fee investment deposit
take home :: pay message salary exam
go to market :: strategy plan model team
go to :: person guy place source resource
no go :: zone area
trial and error :: approach method process basis testing
wait and see :: approach attitude mode
all or nothing :: approach proposition attitude game mentality situation thinking bet gamble
life or death :: situation decision struggle matter choice moment emergency
make or break :: moment decision point time game season year
do or die :: situation moment game match battle attitude
yes or no :: question answer vote decision response proposition format
true or false :: question test statement quiz
multiple choice :: question test exam quiz format answer section option
fill in the blank :: question exercise test worksheet format activity quiz
work from home :: policy job employee arrangement option
pay per click :: advertising campaign model
pay as you go :: plan phone service model option contract
all in one :: solution device printer tool package platform
do it yourself :: project kit guide approach
plug and play :: solution device system module design interface setup
plug in :: hybrid vehicle car module device adapter charger
drag and drop :: interface builder editor feature functionality upload tool
point and click :: interface game adventure
copy and paste :: job method approach
cut and paste :: job method approach
question and answer :: session format period forum section segment
give and take :: relationship process
black and white :: photo photograph film movie image picture television print thinking world
heart to heart :: conversation talk chat discussion
one to one :: meeting session ratio relationship mapping correspondence coaching support conversation chat tutoring training call consultation lesson attention interview
peer to peer :: network lending payment support review learning file sharing marketplace transfer platform communication
door to door :: sale salesman service delivery campaign canvassing shipping transportation travel
hand to hand :: combat fighting
hand to mouth :: existence living
word for word :: translation copy transcript quote account
case by case :: basis analysis review decision approach evaluation assessment
stand up :: comedy comedian meeting desk routine show special comic paddle
sit down :: dinner meal restaurant interview strike protest lunch comedy
drive through :: window restaurant lane service pharmacy bank coffee car wash line
pop up :: shop store window menu restaurant ad blocker event book tent market kitchen notification message banner camper cafe bar
drop down :: menu list box arrow option field selector button
pull down :: menu bar list screen window
run through :: rehearsal
back office :: operation staff function system support work process automation task software
front office :: staff operation
front line :: worker staff employee manager troop service defense defence supervisor leader
front facing :: camera lens seat
rear facing :: seat camera
forward facing :: camera seat
easy to use :: interface design guide tool app instruction layout product format language process solution platform system
easy to read :: format font layout guide text
easy to follow :: guide instruction tutorial step recipe format
easy to understand :: guide explanation format language instruction summary
easy to clean :: surface material design finish
easy to install :: kit software design plugin
easy to navigate :: menu layout site website interface
easy to remember :: password name phrase
easy to learn :: language tool interface
easy to implement :: solution change process
easy to maintain :: code design garden
easy to carry :: bag case design
easy to digest :: format meal food
easy to manage :: system tool
hard to find :: item book part product information ingredient
hard to reach :: place area community group population spot
hard to read :: font text
hard to replace :: item part
ready to use :: solution product template kit mix formula
ready to eat :: meal food cereal snack product breakfast
ready to wear :: collection fashion clothing line dress
ready to go :: solution template kit meal package
ready to assemble :: furniture kit
ready to drink :: cocktail beverage
""".strip().splitlines()

# --- speakers of a language -----------------------------------------------------------------------------------------
LANGS = ['English', 'French', 'Spanish', 'German', 'Chinese', 'Portuguese', 'Arabic', 'Hindi', 'Italian', 'Russian',
         'Japanese', 'Korean', 'Dutch', 'Swedish', 'Polish', 'Turkish', 'Urdu', 'Bengali', 'Mandarin', 'Tamil']

# --- always-hyphenated nouns and adjectives (no following noun needed) -----------------------------------------------
# (open form, hyphen form, left-context regex, example sentence with the open form, same with the hyphen, negative)
ALWAYS = [
    ('half life', 'half-life', r'(?:the|a|its|their|short|long)', 'The drug has a long half life.', 'The drug has a long half-life.', 'Half of the life of the drug is spent waiting.'),
    ('half brother', 'half-brother', r'(?:my|your|his|her|our|their|a|the)', 'She lives with her half brother.', 'She lives with her half-brother.', 'Half of her brothers live abroad.'),
    ('half sister', 'half-sister', r'(?:my|your|his|her|our|their|a|the)', 'He lives with his half sister.', 'He lives with his half-sister.', 'Half of his sisters live abroad.'),
    ('half hearted', 'half-hearted', r'(?:a|an|the|his|her|their|my)', 'It was a half hearted attempt.', 'It was a half-hearted attempt.', 'Half of the hearts were hearted in the game.'),
    ('half baked', 'half-baked', r'(?:a|an|the|this|that|another)', 'That is a half baked idea.', 'That is a half-baked idea.', 'Half of the cakes were baked early.'),
    ('half truth', 'half-truth', r'(?:a|the|only|mere|these|those)', 'It was only a half truth.', 'It was only a half-truth.', 'Half of the truth came out.'),
    ('no brainer', 'no-brainer', r'(?:a|an|the|total|complete|real|absolute)', 'Taking the offer was a no brainer.', 'Taking the offer was a no-brainer.', 'There is no brain in that jar.'),
    ('x ray', 'X-ray', r'(?:an?|the|my|her|his|chest|dental|take|took|got|get)', 'She had an x ray taken.', 'She had an X-ray taken.', 'The X-ray came back clear.'),
    ('t shirt', 'T-shirt', r'(?:an?|the|my|her|his|your|their|this|that|new|old|white|black|blue|red)', 'He wore a white t shirt.', 'He wore a white T-shirt.', 'The T-shirt was too big.'),
    ('u turn', 'U-turn', r'(?:an?|the|make|made|making|do|did|doing|take|took|taking|illegal)', 'He made a U turn at the corner.', 'He made a U-turn at the corner.', 'The U-turn sign was bent.'),
    ('wi fi', 'Wi-Fi', r'(?:the|a|free|public|home|office|hotel|guest|fast|slow|no|our|your)', 'The hotel has free wi fi.', 'The hotel has free Wi-Fi.', 'The Wi-Fi is down.'),
    ('sci fi', 'sci-fi', r'(?:a|the|my|his|her|their|favorite|favourite|classic|old|new)', 'It is a classic sci fi movie.', 'It is a classic sci-fi movie.', 'The sci-fi movie was long.'),
    ('hi fi', 'hi-fi', r'(?:a|the|my|his|her|their|old|new)', 'He bought a new hi fi system.', 'He bought a new hi-fi system.', 'The hi-fi system was loud.'),
    ('lo fi', 'lo-fi', r'(?:a|the|my|his|her|their|old|new)', 'She plays a lo fi playlist while she works.', 'She plays a lo-fi playlist while she works.', 'The lo-fi beats were calm.'),
    ('e commerce', 'e-commerce', r'(?:an?|the|our|your|their|my|its|his|her)', 'We run an e commerce store.', 'We run an e-commerce store.', 'The e-commerce store is busy.'),
    ('e learning', 'e-learning', r'(?:an?|the|our|your|their|my|its|his|her)', 'Our e learning platform is free.', 'Our e-learning platform is free.', 'The e-learning platform is free.'),
    ('e book', 'e-book', r'(?:an?|the|our|your|their|my|its|his|her|free|new)', 'Download the e book from our site.', 'Download the e-book from our site.', 'The e-book is free.'),
    ('e reader', 'e-reader', r'(?:an?|the|our|your|their|my|its|his|her|new)', 'She bought a new e reader.', 'She bought a new e-reader.', 'The e-reader is light.'),
    ('c suite', 'C-suite', r'(?:the|our|your|their|my|its)', 'The plan went to the c suite.', 'The plan went to the C-suite.', 'The C-suite approved it.'),
]
