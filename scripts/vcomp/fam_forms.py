"""Family L: "to" followed by a past or third-person form instead of the base verb ("want to came" -> "want to come").
The governor list is shared; each form is its own rule so a form that is also a noun can be left out."""
import core
from core import add

GOVERNORS = ("want|wants|wanted|need|needs|needed|try|tries|tried|trying|plan|plans|planned|decide|decides|decided|"
             "hope|hopes|hoped|like|liked|love|loved|hate|hated|prefer|preferred|wish|wished|have|has|had|ought|able|"
             "unable|supposed|going|about|begin|began|start|started|continue|continued|forget|forgot|remember|"
             "remembered|refuse|refused|manage|managed|fail|failed|offer|offered|expect|expected|intend|intended|"
             "attempt|attempted|choose|chose|learn|learned|afford|how|what|where|when|whether")
LEAD = r'\b(?:' + GOVERNORS + r')\s+to\s+'
# A form that is also the past participle ("made", "sold") can be a passive with "be" missing ("had to made" is
# "had to be made"), so those only follow verbs that cannot take a passive: wanting, trying, deciding...
ACTIVE = ("want|wants|wanted|try|tries|tried|trying|plan|plans|planned|decide|decides|decided|hope|hopes|hoped|like|liked|"
          "love|loved|hate|hated|prefer|preferred|wish|wished|refuse|refused|manage|managed|fail|failed|offer|offered|"
          "intend|intended|attempt|attempted|choose|chose|learn|learned|afford")
LEAD_ACTIVE = r'\b(?:' + ACTIVE + r')\s+to\s+'
SAME_AS_PARTICIPLE = {'made', 'got', 'said', 'thought', 'told', 'bought', 'brought', 'met', 'paid', 'sent', 'taught',
                      'understood', 'won', 'kept', 'slept', 'built', 'sold', 'heard', 'held', 'stood'}

def form_rule(prefix, form, base, pos_tail='home', note=''):
    pos = f'I want to {form} {pos_tail}.'
    exp = f'I want to {base} {pos_tail}.'
    neg = f'I want to {base} {pos_tail}. She {form} {pos_tail} yesterday. We went to the shop.'
    add(f'{prefix}.{form}', (LEAD_ACTIVE if form in SAME_AS_PARTICIPLE else LEAD) + r'(?P<target>(?-i:' + form + r'))\b', base,
        f'After “to”, use the base verb: “to {base}”, not “to {form}”.', pos, exp, neg,
        [form], conf=0.93, cover=f'to {form} -> to {base}')

PAST = [('came', 'come'), ('did', 'do'), ('made', 'make'), ('got', 'get'), ('said', 'say'), ('ran', 'run'),
        ('wrote', 'write'), ('ate', 'eat'), ('gave', 'give'), ('knew', 'know'), ('thought', 'think'), ('told', 'tell'),
        ('bought', 'buy'), ('brought', 'bring'), ('met', 'meet'), ('paid', 'pay'), ('sent', 'send'), ('spoke', 'speak'),
        ('taught', 'teach'), ('understood', 'understand'), ('won', 'win'), ('began', 'begin'), ('drank', 'drink'),
        ('flew', 'fly'), ('forgot', 'forget'), ('swam', 'swim'), ('rode', 'ride'), ('became', 'become'),
        ('broke', 'break'), ('chose', 'choose'), ('wore', 'wear'), ('stole', 'steal'), ('woke', 'wake'),
        ('grew', 'grow'), ('threw', 'throw'), ('sang', 'sing'), ('stood', 'stand'), ('kept', 'keep'),
        ('slept', 'sleep'), ('built', 'build'), ('sold', 'sell'), ('heard', 'hear'), ('held', 'hold')]
for form, base in PAST:
    form_rule('topast', form, base)
