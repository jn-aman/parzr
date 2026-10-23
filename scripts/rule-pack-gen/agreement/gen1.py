"""Part 1: pronouns with be / have / do, and lexical verbs after pronouns."""
from lib import *
import vocab, verbobj

F = '(?im)'
APO = "['’]"

# ---------------------------------------------------------------------------------------------
# be: wrong form after a pronoun
# ---------------------------------------------------------------------------------------------
add('agree.i_is_are_clause',
    F + CL + CAP_I + r' (?P<target>is|are)\b', 'am', 'Agreement', 0.97,
    'Use ' + q('am') + ' after ' + q('I') + '.',
    'I think I are ready for the exam.',
    'I am ready. Part I is about grammar. Type I diabetes is common. World War I was long. Is I the right word? '
    'Chapter I are not needed? Whoever I am, I am here.')
# "Chapter I are" above has no clause context before I, so it stays quiet; kept as the near miss on purpose.

add('agree.you_is_am_clause',
    F + CL_PL + r'you (?P<target>is|am)\b', 'are', 'Agreement', 0.97,
    'Use ' + q('are') + ' after ' + q('you') + '.',
    'When you is tired, take a break.',
    'You are tired. If you are late, call me. I will give you is nothing? The gift to you is large. '
    'Between you and me is a secret.')
add('agree.we_is_am',
    F + r'\bwe (?P<target>is|am)\b', 'are', 'Agreement', 0.97,
    'Use ' + q('are') + ' after ' + q('we') + '.',
    'Tell them what we is planning.',
    'We are planning it. Are we there yet? Tell them where we are. Let us know if we are late.')
add('agree.they_is_am',
    F + r'\bthey (?P<target>is|am)\b', 'are', 'Agreement', 0.97,
    'Use ' + q('are') + ' after ' + q('they') + '.',
    'I hope they is happy with the result.',
    'They are happy. Are they ready? When they arrive, the cake is ready. Tell them it is done. '
    'Wherever they are, they are fine.')
add('agree.he_she_it_am',
    F + SGP_F + r' (?P<target>am)\b', 'is', 'Agreement', 0.97,
    'Use ' + q('is') + ' after ' + q('he') + ', ' + q('she') + ' or ' + q('it') + '.',
    'I think she am the new manager.',
    'I am the new manager. He is the new manager. It is done. Am I late? If I am late, start without me.')
add('agree.he_she_it_are',
    F + SGP_F + r' (?P<target>are)\b', 'is', 'Agreement', 0.96,
    'Use ' + q('is') + ' after ' + q('he') + ', ' + q('she') + ' or ' + q('it') + '.',
    'I know that he are the owner.',
    'They are the owners. We are here. Where are you? Are they in? The IT staff are away. '
    'He said it is late. I told her they are fine.')

add('agree.you_was_clause',
    F + CL_PL + r'you (?P<target>was)\b', 'were', 'Agreement', 0.96,
    'Use ' + q('were') + ' after ' + q('you') + ', in the past as well.',
    'I know you was in Paris last week.',
    'You were in Paris. The money I gave you was stolen. What I told you was true. Everything I showed you was '
    'real. Thank you was never said.')
add('agree.we_were',
    F + r'\bwe (?P<target>was)\b', 'were', 'Agreement', 0.96,
    'Use ' + q('were') + ' after ' + q('we') + '.',
    'Last year we was in Madrid.',
    'We were in Madrid. The day we were there was sunny. I was in Madrid. If I was there, I would say so.')
add('agree.they_were',
    F + r'\bthey (?P<target>was)\b', 'were', 'Agreement', 0.96,
    'Use ' + q('were') + ' after ' + q('they') + ', also for one person.',
    'The guests said they was tired.',
    'They were tired. The guests were tired. The dog was tired. When they were here, it was quiet.')
add('agree.you_wasnt_clause',
    F + CL_PL + r'you (?P<target>wasn(?P<a>' + APO + r')t)\b', 'weren${a}t', 'Agreement', 0.96,
    'Use ' + q('weren’t') + ' after ' + q('you') + '.',
    'I know you wasn\'t there.',
    'You weren\'t there. The ticket I sent you wasn\'t valid. What I told you wasn\'t a secret. It wasn\'t you.')
add('agree.we_they_wasnt',
    F + r'\b(?:we|they) (?P<target>wasn(?P<a>' + APO + r')t)\b', 'weren${a}t', 'Agreement', 0.96,
    'Use ' + q('weren’t') + ' after ' + q('we') + ' or ' + q('they') + '.',
    'We said we wasn\'t ready.',
    'We weren\'t ready. They weren\'t ready. She wasn\'t ready. I wasn\'t there. It wasn\'t them.')

# the subjunctive and "as it were" are fine, so "was/were" for singular pronouns is only judged where the
# clause is plainly indicative: sentence start, or after "because", "when", "since".
WERE_L = r'(?:^|' + END + r'\s+|\b(?:because|when|since)\s+)'
add('agree.i_were_clause',
    F + WERE_L + CAP_I + r' (?P<target>were)\b', 'was', 'Agreement', 0.93,
    'Use ' + q('was') + ' after ' + q('I') + ' in a plain statement about the past.',
    'When I were a child, we lived by the sea.',
    'When I was a child, we lived by the sea. If I were you, I would go. I wish I were taller. '
    'As if I were asleep. Were I to leave, you would stay. Part I were? Whether I were right or not, it was fine.')
add('agree.he_she_it_were_clause',
    F + WERE_L + r'(?:he|she|' + IT + r') (?P<target>were)\b', 'was', 'Agreement', 0.93,
    'Use ' + q('was') + ' after ' + q('he') + ', ' + q('she') + ' or ' + q('it') + ' in a plain statement about the past.',
    'Because she were late, we started without her.',
    'She was late. If she were late, we would start. I wish he were here. As it were, nothing changed. '
    'It looked as though it were new. Even if it were true, it would not matter.')
add('agree.i_werent_clause',
    F + WERE_L + CAP_I + r' (?P<target>weren(?P<a>' + APO + r')t)\b', 'wasn${a}t', 'Agreement', 0.93,
    'Use ' + q('wasn’t') + ' after ' + q('I') + ' in a plain statement about the past.',
    'When I weren\'t looking, the cat jumped up.',
    'I wasn\'t looking. If I weren\'t so tired, I would stay. Weren\'t I there? I wish I weren\'t late.')
add('agree.he_she_it_werent_clause',
    F + WERE_L + r'(?:he|she|' + IT + r') (?P<target>weren(?P<a>' + APO + r')t)\b', 'wasn${a}t', 'Agreement', 0.93,
    'Use ' + q('wasn’t') + ' after ' + q('he') + ', ' + q('she') + ' or ' + q('it') + ' in a plain statement about the past.',
    'Because it weren\'t finished, we waited.',
    'It wasn\'t finished. If it weren\'t for you, I would fail. I wish she weren\'t away. As if he weren\'t there.')

# ---------------------------------------------------------------------------------------------
# have
# ---------------------------------------------------------------------------------------------
add('agree.he_she_it_have_clause',
    F + SGP + r' (?P<target>have)\b', 'has', 'Agreement', 0.96,
    'Use ' + q('has') + ' after ' + q('he') + ', ' + q('she') + ' or ' + q('it') + '.',
    'I think she have a spare key.',
    'She has a spare key. Let her have a turn. Make it have a name. Does he have a key? Should she have called? '
    'I suggest that he have a rest. They have a key. Help it have a chance. Can it have been lost?')
add('agree.i_you_has_clause',
    F + CL_PL + r'(?:' + CAP_I + r'|you) (?P<target>has)\b', 'have', 'Agreement', 0.96,
    'Use ' + q('have') + ' after ' + q('I') + ' or ' + q('you') + '.',
    'When you has time, call me.',
    'You have time. I have time. She has time. Chapter I has ten pages. Part I has a map. '
    'Thank you has never been said.')
add('agree.we_they_has',
    F + r'\b(?:we|they) (?P<target>has)\b', 'have', 'Agreement', 0.96,
    'Use ' + q('have') + ' after ' + q('we') + ' or ' + q('they') + '.',
    'The guests say they has already left.',
    'They have left. We have left. He has left. The team has left. Everyone has left. Where it has gone, nobody knows.')
add('agree.he_she_it_havent',
    F + SGP_F + r' (?P<target>haven(?P<a>' + APO + r')t)\b', 'hasn${a}t', 'Agreement', 0.96,
    'Use ' + q('hasn’t') + ' after ' + q('he') + ', ' + q('she') + ' or ' + q('it') + '.',
    'I think he haven\'t finished.',
    'He hasn\'t finished. They haven\'t finished. I haven\'t finished. Why haven\'t we? It hasn\'t started.')
add('agree.i_you_we_they_hasnt',
    F + r'(?:\b(?:we|they)|' + CL_PL + r'(?:' + CAP_I + r'|you)) (?P<target>hasn(?P<a>' + APO + r')t)\b', 'haven${a}t',
    'Agreement', 0.96,
    'Use ' + q('haven’t') + ' after ' + q('I') + ', ' + q('you') + ', ' + q('we') + ' or ' + q('they') + '.',
    'I hope they hasn\'t forgotten us.',
    'They haven\'t forgotten. He hasn\'t forgotten. Part I hasn\'t changed. The team hasn\'t changed.')

# ---------------------------------------------------------------------------------------------
# do
# ---------------------------------------------------------------------------------------------
add('agree.he_she_it_dont_clause',
    F + SGP_F + r' (?P<target>don(?P<a>' + APO + r')t)\b', 'doesn${a}t', 'Agreement', 0.97,
    'Use ' + q('doesn’t') + ' after ' + q('he') + ', ' + q('she') + ' or ' + q('it') + '.',
    'I think he don\'t like onions.',
    'He doesn\'t like onions. They don\'t like onions. I don\'t like onions. Why don\'t we go? '
    'Do it. Don\'t do it. Whether or not it matters, don\'t worry.')
add('agree.i_you_we_they_doesnt',
    F + r'(?:\b(?:we|they)|' + CL_PL + r'(?:' + CAP_I + r'|you)) (?P<target>doesn(?P<a>' + APO + r')t)\b', 'don${a}t',
    'Agreement', 0.97,
    'Use ' + q('don’t') + ' after ' + q('I') + ', ' + q('you') + ', ' + q('we') + ' or ' + q('they') + '.',
    'I think they doesn\'t care.',
    'They don\'t care. He doesn\'t care. Part I doesn\'t apply. The team doesn\'t care. It doesn\'t matter.')
add('agree.he_she_it_do_clause',
    F + SGP + r' (?P<target>do)\b', 'does', 'Agreement', 0.95,
    'Use ' + q('does') + ' after ' + q('he') + ', ' + q('she') + ' or ' + q('it') + '.',
    'I think she do the filing on Fridays.',
    'She does the filing. They do the filing. Did he do the filing? Let him do the filing. Make it do the work. '
    'Can it do that? What do they do? I suggest that he do the filing.')
add('agree.i_you_we_they_does',
    F + r'(?:\b(?:we|they)|' + CL_PL + r'(?:' + CAP_I + r'|you)) (?P<target>does)\b', 'do', 'Agreement', 0.95,
    'Use ' + q('do') + ' after ' + q('I') + ', ' + q('you') + ', ' + q('we') + ' or ' + q('they') + '.',
    'I think they does the filing on Fridays.',
    'They do the filing. She does the filing. The team does the filing. What he does is fine.')

# ---------------------------------------------------------------------------------------------
# lexical verbs after he / she / it, and after I / you / we / they
# ---------------------------------------------------------------------------------------------
SKIP = {'fit', 'lie', 'rule', 'ring', 'owe'}
# "it design", "it order", "it post" ... are often a typo for "its": there is no safe fix, so only he / she
EXCLUDE_IT = set("""answer call charge claim control copy count cover design head lock mix order pack plan point post
press print record report rest roll sign supply test train type offer promise reply search study talk visit vote
wash waste demand deal fight gain jump push pull rush share stand surprise touch walk guess hurry shout smile
treat laugh cry clean clear close open own fix kill""".split())
NOUNISH_IT = EXCLUDE_IT

def verbs():
    base = [v for v in vocab.VERBS if v not in SKIP]
    return base

for v in verbs():
    t = vocab.third(v)
    obj = verbobj.OBJ[v]
    pron = SGP_HS if v in NOUNISH_IT else SGP
    names = 'he, she' if v in NOUNISH_IT else 'he, she, it'
    shown = 'he or she' if v in NOUNISH_IT else 'he, she or it'
    add('agree.sg_' + v,
        F + pron + r' (?P<target>' + v + r")(?:[^\w'’-]|$)", t, 'Agreement', 0.88,
        'Use ' + q(t) + ' after ' + q('he') + ', ' + q('she') + (' or ' + q('it') if v not in NOUNISH_IT else '') + '.',
        'I think she ' + v + ' ' + obj + '.',
        'Let her ' + v + ' ' + obj + '. They ' + v + ' ' + obj + '. Did he ' + v + ' ' + obj + '? She ' + t + ' ' + obj + '. '
        'I suggest that he ' + v + ' ' + obj + '. Can she ' + v + ' ' + obj + '? Make him ' + v + ' ' + obj + '.')
    add('agree.pl_' + v,
        F + r'(?:\b(?:we|they)|' + CL_PL + r'(?:' + CAP_I + r'|you)) (?P<target>' + t + r")(?:[^\w'’-]|$)", v, 'Agreement', 0.96,
        'Use ' + q(v) + ' after ' + q('I') + ', ' + q('you') + ', ' + q('we') + ' or ' + q('they') + '.',
        'I know they ' + t + ' ' + obj + '.',
        'He ' + t + ' ' + obj + '. We ' + v + ' ' + obj + '. Chapter I ' + t + ' ' + obj + '. I will show you ' + t + ' now. '
        'Anna ' + t + ' ' + obj + '.')
