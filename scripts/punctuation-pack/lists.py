"""Shared word lists for the punctuation pack: head nouns, left contexts and plural helpers."""
import re

# A noun that follows a compound modifier ("a data-driven team"): written as a singular; the plural is added by plurals().
# A trailing * marks a noun with no plural form here (mass noun or already plural).
GEN = ('approach plan strategy solution model system method process policy option idea concept project program '
       'initiative effort campaign decision change improvement benefit effect impact result outcome trend issue problem '
       'challenge opportunity tool product service feature design team company business organization group culture '
       'environment experience performance content platform application network community client customer employee worker '
       'professional leader manager expert specialist player athlete student teacher family household home house '
       'hotel restaurant shop store market industry sector job role position career task assignment activity event '
       'meeting session course class lesson factor element component aspect element rule requirement standard '
       'framework tactic technique technology software* equipment* training* guidance* support* work*').split()

# Words that may stand right before a bare compound modifier without being a determiner: a verb or a preposition that is
# followed by a noun phrase ("We offer award-winning service", "for hands-on training").
LEFT_EXTRA = 'for with of from using and or offer offers provide provides need needs'.split()


def plural(word):
    if word.endswith('*'):
        return [word[:-1]]
    if re.search(r'[^aeiou]y$', word):
        return [word, word[:-1] + 'ies']
    if re.search(r'(s|x|ch|sh|z)$', word):
        return [word, word + 'es']
    if word.endswith('man'):
        return [word, word[:-3] + 'men']
    return [word, word + 's']


def heads_alt(heads):
    out = []
    for h in heads:
        for form in plural(h):
            if form not in out:
                out.append(form)
    out.sort(key=lambda w: (-len(w), w))
    return '|'.join(out)


def first_head(heads):
    return heads[0].rstrip('*')


LEFT_ALT = r'(?:' + '|'.join(['a', 'an', 'the', 'this', 'that', 'our', 'my', 'your', 'their', 'his', 'her', 'its']  + LEFT_EXTRA) + r')'

LEFT_DET_ALT = r'(?:a|an|the|this|that|our|my|your|their|his|her|its)'

NUMBER_WORDS = ['two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'eleven', 'twelve', 'thirteen',
                'fourteen', 'fifteen', 'sixteen', 'seventeen', 'eighteen', 'nineteen', 'twenty', 'thirty', 'forty',
                'fifty', 'sixty', 'seventy', 'eighty', 'ninety', 'hundred']
NUM_ALT = r'(?:' + '|'.join(NUMBER_WORDS) + r'|\d+)'


def art(word):
    return 'an' if re.match(r'(?i)[aeiou]', word) and not re.match(r'(?i)(uni|use|one|eu)', word) else 'a'
