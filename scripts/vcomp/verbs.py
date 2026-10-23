"""Verb lists. Every entry is a base form that is a verb a learner might put after "to"; names that are also verbs
(mark, bill, will, rob, pat, grant, hope, rose, dean, jack, drew, miles) are left out on purpose, and the lists are
matched in lower case only, so a capitalized name never matches."""
import core

def words(s):
    return sorted(set(s.split()))

# Broad list: used after governors that never take "to" plus a verb.
ACT = words("""
go do see be have get make take come give buy sell pay bring send tell say think know feel find look wait stay
listen ask call check visit join attend learn study try work talk speak help read write watch play eat drink sleep
walk cook clean fix build teach pass meet hear spend share follow create open close start finish continue drive
ride leave live move use change save lose win run put sit stand wear wash pick turn show keep hold set cut hit pull
push carry catch throw sing dance swim fly climb jump
add apply answer arrange believe borrow break breathe burn care celebrate choose collect compare complete contact
contribute cover cross deal decide deliver describe design develop discuss earn enter explain explore express face
fill fight forget forgive gain gather grow guess handle hurt imagine improve include increase invite kill kiss knock
laugh lead lift love manage mean measure mention miss notice obtain offer order organize own pack paint park perform
plan plant post practice prepare prevent produce protect prove provide publish raise reach realize receive recognize
record reduce relax remember remove repair replace reply report request require rest return review rise roll sail
search select serve settle shake shoot shop sign solve spread steal stick stop strike succeed suffer supply support
surprise survive switch taste test thank touch train translate trust understand update upload vote wake warn waste
welcome wish wonder worry
""")

# Narrow list for contexts where "to" followed by a noun is also normal ("keep to the plan", "object to payment").
SAFE = words("""
go do see be have get make take come give buy sell bring send tell say think know feel find look wait stay listen
ask call check visit join attend learn study try work talk speak read write watch play eat drink sleep walk cook
clean fix build teach meet hear spend share follow create open close start finish continue drive leave live move
use change save lose win run put sit stand wear wash pick turn show keep hold set cut hit pull push carry catch
throw sing dance swim fly climb jump add apply answer believe break choose collect compare complete contribute
decide deliver describe develop discuss earn enter explain explore forget gain gather grow guess handle improve
include increase invite kill laugh lead lift love manage mention notice obtain offer organize prepare prevent
produce protect prove provide publish raise reach realize receive recognize record reduce relax remember remove
repair replace reply report request require return review search select serve solve spread support survive
switch understand update upload vote warn welcome wonder worry
""")

# Verbs that are almost never a noun directly after "want/need/ought..." (no "help", "work", "support", "change",
# "access", "update", "fix", "visit", "call", "test", "plan" and the like), for the "missing to" rules.
KV = words("""
go do see be have get make take come give buy sell pay bring send tell say think know feel find wait stay listen ask
join attend learn study try talk speak read write eat sleep meet hear spend share follow create open close start
finish continue leave live move lose win put sit stand wear wash pick fly borrow understand remember forget explain
apply answer arrange believe break choose collect compare complete contact contribute decide deliver describe design
develop discuss earn enter explore express fight fill gain gather grow guess handle hurt imagine improve include
invite kill laugh lead lift mention notice obtain organize own pack perform prepare prevent produce protect prove
provide publish raise reach realize receive recognize reduce relax remove repair replace require return select serve
settle solve spread steal succeed suffer supply survive switch translate trust warn waste welcome wonder look know
buy cook clean drive ride walk watch play sing dance swim jump climb throw catch carry push pull turn
""")

# Safe gerunds after "going to" (so "going to meeting" is left alone): no noun-like -ing words.
SAFEG = words("be have get do make take give tell see say go come find ask try use need look know let put stay buy "
              "send call bring leave start pay talk speak read write")

# KV without verbs that are also bare nouns or adjectives ("need sleep", "got her start", "want leave", "need close to"):
# these are the only ones safe after an object pronoun or "want/need", where a noun reading is a real possibility.
_NOUNISH = set("""lift trust return cover rest play look turn cook walk dance swim jump climb throw catch carry push pull watch
ride drive fly wash fight fill gain lead raise reach settle spread supply switch waste welcome wonder handle guess notice
pack perform start close finish stop break mention design study contact complete invite laugh produce repair select
answer express hurt share stand sleep pay feel leave live pick talk update help work change support access order plan
post test own""".split())
KV2 = [v for v in KV if v not in _NOUNISH]
# After "devoted to", "prior to", "look forward to" and the like: a verb here is an error, but a bare noun ("devoted to
# work", "prior to use", "opposed to change") is normal, so those nouns stay out.
PREPV = sorted(set(KV2) | set('teach ensure keep protect'.split()))

if __name__ == '__main__':
    for name, lst in (('ACT', ACT), ('SAFE', SAFE)):
        print(name, len(lst))
        for v in lst:
            try:
                core.gerund(v)
            except Exception as e:
                print('BAD', v, e)
        print(' '.join(core.gerund(v) for v in lst))
