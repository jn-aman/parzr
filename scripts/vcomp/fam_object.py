"""Family M: a strictly transitive verb left without its object after a modal or negative
("I cannot install, but ..." -> "I cannot install it"). Same shape as grammar.missing_object_after_modal in
owner-reports.json; this list extends it with verbs that name an action on a thing and cannot stand alone."""
import core
from core import add, alt, CLAUSE

AUX = (r"(?:can(?:no|[’'])t|can not|could(?:n[’']t| not)|won[’']t|will not|wouldn[’']t|would not|"
       r"(?:am|[’']m|was|were|is|are) (?:not able|unable) to)")
TAIL = (r"(?:\s*[(,.;:!?)\n]|\s+(?:but|because|as|since|so|until|unless|though|either|now|yet|anymore|any more|myself|"
        r"ourselves)\b|\s*$)")

GROUPS = [
    ('software', 'install uninstall reinstall', 'I cannot install (the license is missing), but I can read the guide.',
     'I cannot install it (the license is missing), but I can read the guide.',
     'I cannot install the update. We can install or remove it. I cannot install and test it. The tool I cannot install is old.'),
    ('locks', 'unlock decrypt encrypt', "We can't unlock, because the key is missing.", "We can't unlock it, because the key is missing.",
     "We can't unlock the door. We can't unlock or lock it. You can't decrypt the file."),
    ('workflow', 'approve cancel reschedule resubmit reapply redo', 'I cannot approve, since I am not the owner.',
     'I cannot approve it, since I am not the owner.',
     'I cannot approve the request. I cannot cancel or reschedule it. You cannot cancel the order.'),
    ('locate', 'locate retrieve recover replace duplicate merge clone relocate', "They couldn't locate, so they asked for help.",
     "They couldn't locate it, so they asked for help.",
     "They couldn't locate the file. We cannot replace or repair it. I couldn't recover the data."),
]
for rid, verbs, pos, exp, neg in GROUPS:
    pattern = (CLAUSE + r"(?:I|we|you|they|he|she)\s+" + AUX + r"(?: also| still| even| just| really| yet)? (?P<target>" +
               alt(verbs.split()) + r")" + TAIL)
    add(f'missingobj.{rid}', pattern, '${target} it',
        'Say what cannot be done: this verb needs an object.', pos, exp, neg, verbs.split(), conf=0.86,
        cover=f'{verbs} with no object after a modal or negative')
