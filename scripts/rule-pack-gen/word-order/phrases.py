"""Fixed word orders: "two years ago", "all my friends", "the first two days", "my friend and I", "Me too"."""
from lib import *

VERBS_AFTER_SUBJ = (r'(?:are|were|was|have|had|will|would|can|could|should|went|go|got|did|do|decided|came|met|saw|'
                    r'visited|work|live|play|study|like|love|want|need|plan|planned|agreed|left|arrived|started|enjoyed)')


def build_ago():
    nums = (r'(?:a couple of|a few|several|many|an?|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|'
            r'twenty|thirty|fifty|\d+)')
    for unit, plural in (('second', 'seconds'), ('minute', 'minutes'), ('hour', 'hours'), ('day', 'days'),
                         ('week', 'weeks'), ('month', 'months'), ('year', 'years'), ('decade', 'decades')):
        pat = subst(r'(?i)\b(?P<target>ago (?P<n><<N>>) (?P<u>' + unit + r's?))\b', N=nums)
        n = 'a' if unit not in ('hour',) else 'an'
        sample_n = 'two'
        R(f'ago_first.{unit}', pat, '${n} ${u} ago', 'Grammar', 0.93,
          '“Ago” goes after the time: “two years ago”.',
          f'I moved here ago {sample_n} {plural}.', f'I moved here {sample_n} {plural} ago.',
          f'I moved here {sample_n} {plural} ago. Long ago, {sample_n} men came. Ago is a short word.')


def build_dialect_times():
    for bad, good in (('today morning', 'this morning'), ('today afternoon', 'this afternoon'),
                      ('today evening', 'this evening'), ('today night', 'tonight'), ('yesterday night', 'last night')):
        key = bad.replace(' ', '_')
        pat = r'(?i)\b(?P<target>' + bad + r')\b'
        R(f'time_phrase.{key}', pat, good, 'Register', 0.72,
          f'Most writers say “{good}” rather than “{bad}”.',
          f'I will call you {bad} after work.', f'I will call you {good} after work.',
          f'I will call you {good} after work. Today, morning traffic is heavy. Yesterday, night fell early.')


def build_also_me():
    pat = subst(r'(?im)<<SS>>(?P<target>Also me|Me also)\s*(?:[.!]|$)', SS=SS)
    R('also_me', pat, 'Me too', 'Style', 0.78,
      '“Me too” is the usual way to say you agree or do the same.',
      'I like pizza. Also me.', 'I like pizza. Me too.',
      'I like pizza. Me too. Also, me and my friend like it. Me also wanted pizza.')


def build_i_and():
    names = (r'(?-i:[A-Z])[a-z]+')
    pat = subst(r'(?im)<<SS>>(?P<target>I and )(?P<moved>(?-i:[A-Z])[a-z]+)\s+<<V>>\b', SS=SS, V=VERBS_AFTER_SUBJ)
    R('i_and_name', pat, ' and I', 'Style', 0.8,
      'It is polite to name the other person first: “Sarah and I”.',
      'I and Sarah went home together.', 'Sarah and I went home together.',
      'Sarah and I went home together. Sarah and I were there. I and I alone know.', moved=True)
    pat = subst(r'(?i)\b[a-z]+ (?P<target>I and )(?P<moved>(?:my|your|his|her|our|their|the) [a-z]+)\s+<<V>>\b', V=VERBS_AFTER_SUBJ)
    R('i_and_np', pat, ' and I', 'Style', 0.8,
      'It is polite to name the other person first: “my friend and I”.',
      'Yesterday I and my friend went to the market.', 'Yesterday my friend and I went to the market.',
      'Yesterday my friend and I went to the market. I and my friend. Between I and my friend there was silence.', moved=True)
    pat = subst(r'(?i)\b[a-z]+ (?P<target>I and )(?P<moved>he|she|they|you)\s+<<V>>\b', V=VERBS_AFTER_SUBJ)
    R('i_and_pronoun', pat, ' and I', 'Style', 0.8,
      'It is polite to name the other person first: “he and I”.',
      'Then I and he went home.', 'Then he and I went home.',
      'Then he and I went home. I and he. Then you and I decided.', moved=True)


def build_predeterminers():
    nouns = (r'(?:friends|family|people|children|kids|students|colleagues|teachers|employees|members|team|staff|life|'
             r'money|data|files|things|work|classmates|relatives|neighbou?rs|customers|clients|plans|dreams|points|answers|'
             r'questions|ideas|problems|photos|documents|emails|tasks|books|belongings|savings|efforts|energy|attention)')
    for d in ('my', 'your', 'his', 'her', 'our', 'their'):
        pat = subst(r'(?i)<<SS>>(?P<target>' + d + r' all)\s+<<N>>\b', SS=SS, N=nouns)
        R(f'all_after.{d}_start', pat, f'All {d}', 'Grammar', 0.93,
          f'“All” goes before the possessive: “all {d} friends”.',
          f'{cap(d)} all friends came to the party.', f'All {d} friends came to the party.',
          f'All {d} friends came to the party. {cap(d)} all is on the line.')
        pat = subst(r'(?i)\b[a-z]+,? (?P<target>' + d + r' all) <<N>>\b', N=nouns)
        R(f'all_after.{d}', pat, f'all {d}', 'Grammar', 0.93,
          f'“All” goes before the possessive: “all {d} friends”.',
          f'We invited {d} all friends.', f'We invited all {d} friends.',
          f'We invited all {d} friends. Give it {d} all. Give {d} all, then.')
    nums = 'two|three|four|five|six|seven|eight|nine|ten'
    for o in ('first', 'last', 'next'):
        pat = subst(r'(?i)\b(?:the|my|your|his|her|our|their) (?P<target>(?P<n>' + nums + r') ' + o +
                    r')\s+(?:days|weeks|months|years|steps|items|pages|things|people|times|rows|lines|chapters|paragraphs|'
                    r'points|questions|options|results|parts|episodes|slides|letters|words|sentences|minutes|hours|miles|'
                    r'games|rounds|weekends|nights)\b')
        R(f'ordinal_after_number.{o}', pat, o + ' ${n}', 'Style', 0.78,
          f'The ordinal comes before the number: “the {o} two days”.',
          f'I was sick for the two {o} days.', f'I was sick for the {o} two days.',
          f'I was sick for the {o} two days. The two of us {o} met. The two next to me left.')


def build():
    build_ago()
    build_dialect_times()
    build_also_me()
    build_i_and()
    build_predeterminers()
