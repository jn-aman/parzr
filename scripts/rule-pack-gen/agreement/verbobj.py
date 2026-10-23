"""verb -> a short natural complement used in the examples ("she accepts the offer")."""
RAW = """
accept|the offer
add|some salt
afford|the rent
agree|with us
allow|late entries
announce|the winners
answer|the phone
appear|tired
apply|for the job
argue|about money
arrive|before noon
ask|a lot of questions
attend|every meeting
avoid|the traffic
bake|bread on Sundays
bark|at night
bloom|in spring
shine|in the morning
believe|the story
belong|to the club
borrow|my charger
bother|the neighbors
break|the rules
bring|snacks
build|small models
burn|the toast
buy|fresh bread
call|every morning
care|about the result
carry|the boxes
catch|the early train
cause|delays
change|the settings
charge|a small fee
chat|with the team
check|the logs
choose|the cheaper plan
claim|the prize
clean|the kitchen
clear|the cache
click|the button
close|at nine
collect|old coins
compare|the prices
complain|about the noise
complete|the form
contain|extra sugar
continue|after lunch
control|the volume
cook|dinner
copy|the notes
count|every vote
cover|the costs
create|new accounts
cry|at sad movies
deal|with complaints
decide|quickly
deliver|on time
demand|a refund
depend|on the weather
describe|the problem
design|the posters
destroy|old files
develop|new tools
die|young
disagree|with the plan
discuss|the budget
drink|green tea
drive|to work
drop|by on Fridays
earn|a good salary
eat|lunch at noon
enjoy|long walks
enter|the room
escape|every time
exist|only on paper
expect|a reply
explain|the rules
fail|more often
fall|asleep early
fight|with his brother
fill|the form
find|good deals
finish|before dinner
fix|old bikes
fly|to Berlin
follow|the recipe
forget|my name
forgive|easily
gain|weight
gather|the data
get|home late
give|good advice
go|to school
grow|tomatoes
guess|the answer
handle|the calls
happen|every year
hate|the cold
head|the committee
hear|the bell
help|with the dishes
hide|the keys
hold|the door
hope|for good news
hurry|to class
identify|the problem
imagine|a better way
improve|every week
include|a short note
increase|the price
intend|to stay
invite|everyone
join|us for lunch
jump|the queue
keep|a journal
kill|the process
knock|before entering
know|the answer
last|a long time
laugh|at every joke
lead|the team
learn|quickly
leave|at five
lend|me books
listen|to the radio
live|in Leeds
lock|the door
look|tired
lose|the thread
love|the garden
maintain|the server
make|good coffee
manage|the shop
matter|a lot
mean|well
meet|clients on Mondays
mention|the deadline
mind|the noise
miss|the bus
mix|the colors
move|to Madrid
notice|small details
offer|free shipping
open|at eight
order|a pizza
own|a small shop
pack|the bags
pay|on time
perform|well
pick|the best seat
plan|the trip
play|the guitar
point|to the map
post|every day
prefer|tea
prepare|the slides
press|the key
pretend|to sleep
prevent|mistakes
print|the tickets
promise|nothing
protect|the data
prove|the point
provide|free meals
pull|the lever
push|the cart
reach|the office by nine
realize|the risk
receive|the files
recommend|the blue one
record|the calls
reduce|the noise
refuse|to help
relate|to the story
remain|calm
remember|the date
remove|the label
repeat|the question
reply|within an hour
report|to the manager
represent|the school
require|a password
respond|quickly
rest|after lunch
return|on Friday
reveal|the plan
ride|to work
ring|twice
rise|early
roll|the dice
save|money
say|nothing
search|the archive
see|the problem
seem|happy
sell|used books
send|the invoice
serve|dinner at six
share|the files
shout|from the hall
show|the results
sign|the form
sing|in the choir
sit|by the window
sleep|late
smile|a lot
solve|the puzzle
sound|tired
speak|three languages
spend|too much
stand|by the door
start|at nine
stay|home
steal|the show
stop|at the corner
study|at night
succeed|every time
suffer|from allergies
suggest|a break
supply|the shop
support|the plan
suppose|so
surprise|everyone
survive|the winter
take|the bus
talk|too fast
teach|history
tell|the truth
test|the app
thank|everyone
think|about it
throw|the ball
touch|the screen
train|every day
travel|by train
treat|us well
trust|the team
try|again
turn|left
type|quickly
understand|the question
use|a laptop
visit|on Sundays
vote|every year
wait|outside
wake|up early
walk|to work
want|a new phone
warn|the others
wash|the dishes
waste|time
watch|the news
wear|a coat
win|every game
wish|for sunshine
wonder|why
work|late
worry|about nothing
write|every day
"""
OBJ = dict(line.split('|') for line in RAW.strip().splitlines())
