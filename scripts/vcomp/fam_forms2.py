"""Family L (continued): "to" followed by a third-person -s form ("want to goes" -> "want to go")."""
from fam_forms import form_rule

THIRD = [('goes', 'go'), ('comes', 'come'), ('gets', 'get'), ('sees', 'see'), ('knows', 'know'), ('thinks', 'think'),
         ('says', 'say'), ('has', 'have'), ('begins', 'begin'), ('becomes', 'become'), ('forgets', 'forget'),
         ('understands', 'understand'), ('remembers', 'remember'), ('writes', 'write'), ('sends', 'send'),
         ('tells', 'tell'), ('brings', 'bring'), ('speaks', 'speak'), ('sleeps', 'sleep'), ('believes', 'believe'),
         ('chooses', 'choose'), ('decides', 'decide'), ('happens', 'happen')]
for form, base in THIRD:
    form_rule('to3sg', form, base)
