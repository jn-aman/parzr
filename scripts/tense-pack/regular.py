"""Regular verbs for the perfect-with-base family: base, participle, N when the base is also a common noun."""
REG = """
accept accepted
add added
agree agreed
announce announced
answer answered N
apologize apologized
appear appeared
apply applied
approve approved
arrange arranged
arrive arrived
ask asked
assign assigned
attach attached
attend attended
avoid avoided
believe believed
book booked N
call called N
change changed N
check checked N
clarify clarified
clean cleaned N
close closed N
collect collected
complete completed N
confirm confirmed
consider considered
contact contacted N
continue continued
copy copied N
create created
decide decided
deliver delivered
describe described
develop developed
discuss discussed
download downloaded N
email emailed N
enjoy enjoyed
ensure ensured
expect expected
explain explained
fail failed
finish finished
fix fixed N
follow followed
forward forwarded N
handle handled N
happen happened
help helped N
hope hoped N
improve improved
include included
inform informed
install installed
invite invited N
join joined
like liked N
listen listened
live lived
look looked N
love loved N
manage managed
mention mentioned
miss missed N
move moved N
need needed N
notice noticed N
offer offered N
open opened N
order ordered N
organize organized
pass passed
plan planned N
play played N
post posted N
prepare prepared
print printed N
promise promised N
provide provided
publish published
push pushed N
reach reached
realize realized
receive received
record recorded N
reduce reduced
reject rejected
remember remembered
remind reminded
remove removed
repeat repeated
reply replied N
report reported N
request requested N
require required
reserve reserved
resolve resolved
respond responded
return returned N
review reviewed N
save saved
schedule scheduled N
search searched N
share shared
sign signed N
solve solved
start started N
stay stayed N
stop stopped N
submit submitted
suggest suggested
support supported N
switch switched N
talk talked N
thank thanked
test tested N
try tried N
turn turned N
type typed N
update updated N
upload uploaded N
use used N
visit visited N
wait waited N
walk walked N
want wanted N
watch watched N
work worked N
worry worried N
"""
REG_ROWS = []
for line in REG.strip().splitlines():
    p = line.split()
    REG_ROWS.append(dict(base=p[0], part=p[1], noun=len(p) > 2))
