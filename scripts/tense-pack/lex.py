"""Small shared lexicons for the construction rules."""
import re


def third(b):
    irr = {'be': 'is', 'have': 'has', 'do': 'does', 'go': 'goes'}
    if b in irr:
        return irr[b]
    if re.search(r'(s|sh|ch|x|z|o)$', b):
        return b + 'es'
    if re.search(r'[^aeiou]y$', b):
        return b[:-1] + 'ies'
    return b + 's'


def ing(b):
    special = {'be': 'being', 'die': 'dying', 'lie': 'lying', 'tie': 'tying', 'see': 'seeing', 'run': 'running',
               'sit': 'sitting', 'stop': 'stopping', 'plan': 'planning', 'get': 'getting', 'put': 'putting',
               'swim': 'swimming', 'begin': 'beginning', 'shop': 'shopping', 'chat': 'chatting', 'cut': 'cutting',
               'win': 'winning', 'hit': 'hitting', 'set': 'setting', 'let': 'letting', 'meet': 'meeting',
               'travel': 'travelling', 'drop': 'dropping', 'skip': 'skipping', 'submit': 'submitting',
               'admit': 'admitting', 'commit': 'committing', 'refer': 'referring', 'prefer': 'preferring'}
    if b in special:
        return special[b]
    if b.endswith('ie'):
        return b[:-2] + 'ying'
    if b.endswith('e') and not b.endswith('ee') and not b.endswith('oe') and not b.endswith('ye'):
        return b[:-1] + 'ing'
    return b + 'ing'


# verbs that follow a future-time connector: "after I will finish"
TC_VERBS = ("arrive come go reach finish get start leave receive see hear call send check return land begin end open "
            "close complete pay buy find take make meet join wake eat sit stay wait ask tell say know need want win "
            "lose graduate retire move change learn try decide expire run work notice read write speak show turn "
            "fall rise pass happen appear apply submit upload download deliver ship rain snow confirm approve sign "
            "respond reply update leave finish get visit think hope feel look give bring cook clean drive fly "
            "relax recover ring log hand print publish release set settle sort stop talk travel use walk watch "
            "explain solve fix install reboot restart refresh load save sell show sleep sit stand teach tell throw "
            "wear arrange book cancel collect contact create design discuss enter forward invite order plan "
            "prepare process remove repair review schedule share study switch transfer type understand").split()
TC_VERBS = sorted(set(TC_VERBS))

# common base verbs after "to", "would rather", "had better"
BASE_VERBS = ("go be do have get stay wait see take make leave say eat work sleep spend use try ask tell play walk "
              "live buy stick keep let call meet read watch pay die lose start finish avoid move travel drive ride "
              "sit talk think give help join skip wear cook order pick wash drink speak hear hide come run "
              "stop check hurry listen remember forget know leave find bring send write learn teach visit "
              "answer ignore begin turn open close clean fix save book cancel call fight win rest relax "
              "swim sing dance fall sink "
              "sleep return arrive attend stand look move").split()
BASE_VERBS = sorted(set(BASE_VERBS))
