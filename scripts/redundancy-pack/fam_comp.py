"""Doubled comparatives and superlatives ("more cleaner", "most coolest") for the adjectives the base rules and the
modifiers pack do not list. One rule per group of adjectives: the replacement is the same ("cleaner")."""
import re
from core import add, cover, ERRORS, S, E

SEC = 'Doubled comparatives and superlatives'
# A comparative that is also a common noun ("more cleaner" can be "more cleaner spray") is judged only at the end of a
# clause or before a word that cannot be a noun.
TAIL = (r"(?:[.!?,;:)\n\"”]|\s*$|\s+(?:than|and|or|but|now|today|too|still|at|in|on|for|with|to|by|as|when|if|so|this|that|"
        r"these|those|here|there|every|each|after|before|then|though|until|since)\b)")


def comp(a):
    if a.endswith('e'):
        return a + 'r'
    if a.endswith('y') and len(a) > 2 and a[-2] not in 'aeiou':
        return a[:-1] + 'ier'
    if len(a) <= 5 and a[-1] not in 'aeiouwyx' and a[-2] in 'aeiou' and a[-3] not in 'aeiou':
        return a + a[-1] + 'er'
    return a + 'er'


def sup(a):
    if a.endswith('e'):
        return a + 'st'
    if a.endswith('y') and len(a) > 2 and a[-2] not in 'aeiou':
        return a[:-1] + 'iest'
    if len(a) <= 5 and a[-1] not in 'aeiouwyx' and a[-2] in 'aeiou' and a[-3] not in 'aeiou':
        return a + a[-1] + 'est'
    return a + 'est'


# Adjectives whose -er comparative is common and unambiguous.
Y = ('bumpy chilly classy clumsy costly cosy cranky creepy cuddly curly dizzy dreary dusty empty fancy filthy fluffy foggy '
     'frosty fuzzy ghastly gloomy greasy greedy grumpy guilty gusty hairy hasty hilly holy icy jolly juicy likely lovely '
     'mighty moody muddy nasty naughty needy portly queasy ready rusty salty scary shabby shady shaky skinny slimy '
     'slippery smelly snappy sneaky spicy spooky steady sticky stingy stormy stuffy sturdy sweaty trendy tricky wary '
     'weary witty worthy bossy bulky crazy crispy deadly handy').split()
B = ('blunt bland blank bleak blind bold brief brisk broad brown coarse cruel crude dead dear dense dumb evil faint false '
     'fierce frail frank free full grand grave gray grim gross harsh hollow honest huge humble keen lame lean little mean '
     'mellow moist naive noble odd plump prim quaint raw real ripe sane scarce shy sick sleek slick slender smug snug sore '
     'sour spare stable stale stern stiff stupid subtle supple sure swift tart tender tense true vague vast weird wild').split()
Y += ('brainy breezy bubbly burly bushy chubby chunky clingy cocky comfy corny crafty creamy crunchy cushy dainty dotty doughy '
      'drafty dreamy droopy earthy edgy faulty feisty fishy flabby flaky flashy fleshy flimsy floppy frilly frizzy frothy '
      'funky gaudy gawky giddy glassy goofy grainy grassy gritty groovy grubby gummy hardy hazy heady hefty husky itchy '
      'jazzy jerky jumpy kooky leafy leaky lofty loopy lumpy lusty mangy meaty milky minty mossy mushy musty nerdy nippy '
      'nutty oily pasty patchy peppy perky pesky petty picky pithy plucky pushy quirky racy rangy rocky roomy rosy rowdy '
      'runny sandy sappy sassy savvy scaly scanty scrappy scruffy seedy shaggy sketchy sleazy slushy smoggy smoky snazzy '
      'snowy soapy soggy sooty soupy spiky splashy spotty spunky squeaky squishy stocky stony streaky stubby sudsy sulky '
      'sultry surly swampy tacky tangy tardy teary testy thorny thrifty toasty touchy trashy tubby wacky watery waxy weedy '
      'weepy wheezy whiny wiry wispy woody woolly wordy wrinkly zany zesty').split()
B += 'bare blue black white pink meek square hip'.split()
# Comparatives that are also nouns (a cleaner, a cooler, a thinner, a dimmer, a damper, a tamer, a rounder ...).
C = 'clean cool dry fresh light thin warm firm damp tame dim idle round common strange straight sound trim green furry glossy'.split()
EXTRA_COMP = {}  # base -> comparative when the regular spelling is wrong
ODD = {'dry': ('drier', 'driest'), 'shy': ('shier', 'shiest'), 'gray': ('grayer', 'grayest'), 'little': ('littler', 'littlest')}


def forms(a):
    if a in ODD:
        return ODD[a]
    return comp(a), sup(a)


def group(rid, bases, guard, kind, size=45):
    ids = []
    words = [forms(b)[0 if kind == 'more' else 1] for b in bases]
    for i in range(0, len(words), size):
        chunk = words[i:i + size]
        alt = '|'.join(sorted(chunk, key=lambda w: (-len(w), w)))
        pat = rf'(?im){S}(?P<target>{kind} (?P<c>{alt})){guard}'
        rx = re.compile(pat)
        for w in chunk:
            for ctx in (f'This is {kind} {w} than that one.' if kind == 'more' else f'This is the {kind} {w} one.',):
                m = rx.search(ctx + (' ' if guard == E else ''))
                if guard == TAIL:
                    ctx = f'This is {kind} {w} than that one.'
                    m = rx.search(ctx)
                if not m or m.group('c') != w:
                    ERRORS.append(f'{rid}: {w!r} does not match in {ctx!r}')
        first = chunk[0]
        if kind == 'more':
            pos = f'This chair is {kind} {first} than the old one.'
            neg = f'This chair is {first} than the old one, and the shop sells more of them.'
            reason = ('An “-er” comparative already means “more”: say “cleaner”, not “more cleaner”.')
        else:
            pos = f'This chair is the {kind} {first} one in the shop.'
            neg = f'This chair is the {first} one in the shop, and the shop sells most of them.'
            reason = ('An “-est” superlative already means “most”: say “coolest”, not “most coolest”.')
        n = i // size + 1
        ids.append(add(f'{rid}{n}', pat, '${c}', 'Grammar', 0.95, reason, pos, neg))
    return ids


def build():
    ids = []
    ids += group('comp.more_ier', Y, E, 'more')
    ids += group('comp.more_er', B, E, 'more')
    ids += group('comp.more_noun', C, TAIL, 'more')
    ids += group('comp.most_est_y', Y, E, 'most')
    ids += group('comp.most_est', B + C, E, 'most')
    return ids
