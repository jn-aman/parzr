"""Family G: verb or adjective plus a preposition or fixed phrase that takes -ing ("worth to try" -> "worth trying",
"look forward to see" -> "look forward to seeing", "prevent us to leave" -> "prevent us from leaving")."""
import core
from core import add, b2g, alt, ADV, BE, AFTER, P1
from verbs import ACT, PREPV

INTERESTED = ('join apply participate attend buy purchase rent invest enroll enrol register volunteer contribute '
              'collaborate study pursue become develop build create open move sell work').split()
PREVENT_V = sorted(set(ACT) | {'happen', 'occur', 'fall', 'fail'})
OBJECTS = r'(?:me|him|her|us|them|you|it|this|that|these|those|people|everyone|anyone|users|customers|students|children|others)'

def drop_to(rid, lead, forms, verbs, reason, pos, exp, neg, prefix='', conf=0.93, cover=''):
    """lead + "to V" -> lead + prefix + "Ving" (the whole "to V" is replaced)."""
    alt_v, repl = b2g(verbs)
    add(rid, lead + r'(?P<target>to\s+(?-i:' + alt_v + r'))' + AFTER, prefix + repl, reason, pos, exp, neg, forms,
        conf=conf, cover=cover or rid)

def after_to(rid, lead, forms, verbs, reason, pos, exp, neg, conf=0.93, cover=''):
    """lead + "to" + V: only the verb is replaced, by its -ing form."""
    alt_v, repl = b2g(verbs)
    add(rid, lead + r'(?P<target>(?-i:' + alt_v + r'))' + AFTER, repl, reason, pos, exp, neg, forms, conf=conf,
        cover=cover or rid)

drop_to('idiom.worth', BE + r'worth\s+', ['worth'], ACT,
        '“Worth” is followed by an -ing form: “worth trying”, not “worth to try”.',
        'It is worth to try again.', 'It is worth trying again.',
        'It is worth trying again. He estimated his net worth to be high. What is it worth to them? The painting is worth to the museum a fortune.',
        cover='worth to V -> worth Ving')
drop_to('idiom.busy', BE + r'busy\s+', ['busy'], ACT,
        '“Busy” is followed by an -ing form: “busy preparing”, not “busy to prepare”.',
        'I am busy to prepare the report.', 'I am busy preparing the report.',
        'I am busy preparing the report. I am too busy to prepare it. He was never too busy to help.',
        cover='busy to V -> busy Ving')
drop_to('idiom.capable', r'\bcapable\s+', ['capable'], ACT,
        '“Capable” is followed by “of” and an -ing form: “capable of handling”.',
        'She is capable to handle the pressure.', 'She is capable of handling the pressure.',
        'She is capable of handling the pressure. A capable leader to the end.', prefix='of ',
        cover='capable to V -> capable of Ving')
drop_to('idiom.interested', r'\binterested\s+', ['interested'], INTERESTED,
        '“Interested” is followed by “in” and an -ing form: “interested in joining”.',
        'I am interested to join your team.', 'I am interested in joining your team.',
        'I am interested in joining your team. I was interested to see the results. We were interested to learn that.',
        prefix='in ', conf=0.9, cover='interested to V -> interested in Ving (see/hear/learn/know are fine)')
drop_to('idiom.insist', r'\binsist(?:s|ed|ing)?\s+', ['insist', 'insists', 'insisted', 'insisting'], ACT,
        '“Insist” is followed by “on” and an -ing form: “insisted on paying”.',
        'He insisted to pay the bill.', 'He insisted on paying the bill.',
        'He insisted on paying the bill. I insist to him that we leave.', prefix='on ',
        cover='insist to V -> insist on Ving')
drop_to('idiom.succeed', r'\bsucceed(?:s|ed|ing)?\s+', ['succeed', 'succeeds', 'succeeded', 'succeeding'], ACT,
        '“Succeed” is followed by “in” and an -ing form: “succeeded in getting”.',
        'We succeeded to get the funding.', 'We succeeded in getting the funding.',
        'We succeeded in getting the funding. He will succeed to the throne. She succeeded to the post after him.',
        prefix='in ', cover='succeed to V -> succeed in Ving')
for gov, forms, pos, exp, neg in [
        ('prevent', ['prevent', 'prevents', 'prevented', 'preventing'],
         'Heavy rain prevented us to leave the city.', 'Heavy rain prevented us from leaving the city.',
         'Heavy rain prevented us from leaving the city. It prevents this from happening. The lock prevents access to the data.'),
        ('prohibit', ['prohibit', 'prohibits', 'prohibited', 'prohibiting'],
         'The rules prohibit them to enter the building.', 'The rules prohibit them from entering the building.',
         'The rules prohibit them from entering the building. The law prohibits sales to minors.'),
        ('discourage', ['discourage', 'discourages', 'discouraged', 'discouraging'],
         'High prices discourage people to buy the product.', 'High prices discourage people from buying the product.',
         'High prices discourage people from buying the product. It was a discouraging result.'),
        ('deter', ['deter', 'deters', 'deterred', 'deterring'],
         'The fee deters customers to apply.', 'The fee deters customers from applying.',
         'The fee deters customers from applying. The alarm deters theft.')]:
    drop_to(f'idiom.{gov}', r'\b(?:' + alt(forms) + r')\s+' + OBJECTS + r'\s+', forms, PREVENT_V,
            f'“{gov.capitalize()}” takes “from” and an -ing form: “{gov} us from leaving”, not “{gov} us to leave”.',
            pos, exp, neg, prefix='from ', cover=f'{gov} X to V -> {gov} X from Ving')
after_to('idiom.look_forward', r'\blook(?:s|ed|ing)?\s+forward\s+to\s+', ['forward'], PREPV,
         'After “look forward to”, use an -ing form: “look forward to seeing”.',
         'I look forward to see you soon.', 'I look forward to seeing you soon.',
         'I look forward to seeing you soon. We look forward to the meeting. I look forward to hearing from you.',
         conf=0.95, cover='look forward to V -> look forward to Ving')
