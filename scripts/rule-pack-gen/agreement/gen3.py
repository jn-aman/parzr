"""Part 3: indefinite pronouns, each/either/neither of, one of, number, heads of phrases, partitives."""
from lib import *
from gen2 import (ADJ_RX, vpat, vrep, spl, A, PLURAL_GROUPS, SINGULAR_GROUPS)
import vocab

F = '(?im)'
DET_P = 'the|these|those|my|our|your|their|his|her'

# --- verb tables for the "wrong singular verb -> plural" and the reverse -------------------------------
# (wrong, right, complement-for-the-example)
TO_SG = [('are', 'is', 'ready'), ('were', 'was', 'late'), ('have', 'has', 'arrived'), ('do', 'does', 'the work'),
         ("aren't", "isn't", 'ready'), ("weren't", "wasn't", 'late'), ("haven't", "hasn't", 'arrived'),
         ("don't", "doesn't", 'agree')]
TO_PL = [('is', 'are', 'ready'), ('was', 'were', 'late'), ('has', 'have', 'arrived'), ('does', 'do', 'the work'),
         ("isn't", "aren't", 'ready'), ("wasn't", "weren't", 'late'), ("hasn't", "haven't", 'arrived'),
         ("doesn't", "don't", 'agree')]
NAMEY = lambda w: w.replace("'", '')

def lc_for(wrong, broad):
    """left context: bare forms and 'were' need a strict clause start"""
    if wrong in ('have', 'do'):
        return CL_N
    if wrong in ('were', "weren't"):
        return WERE_N
    return broad

# --- indefinite pronouns ----------------------------------------------------------------------------
INDEF = 'everyone|everybody|everything|someone|somebody|something|anyone|anybody|anything|no one|nobody|nothing'
for wrong, right, comp in TO_SG:
    pat = F + lc_for(wrong, CLN_SG) + r'(?:' + INDEF + r') (?P<target>' + vpat(wrong) + r')\b'
    pos = {'are': 'I think everyone are ready.', 'were': 'Everyone were late.',
           'have': 'I know everybody have arrived.', 'do': 'I think everybody do the work.',
           "aren't": 'Sadly nobody aren\'t ready.', "weren't": 'Everyone weren\'t late.',
           "haven't": 'I think somebody haven\'t arrived.', "don't": 'I think everyone don\'t agree.'}[wrong]
    pos = {"aren't": 'I think everyone aren\'t ready.', "weren't": 'Everyone weren\'t there.',
           }.get(wrong, pos)
    neg = ('Everyone ' + right + ' ' + comp + '. Let everyone ' + ('have' if wrong == 'have' else 'do' if wrong == 'do' else 'go') +
           ' a turn. If everyone were here, we could start. I wish everybody were home. All of the people ' + wrong + ' ' + comp + '. '
           'Everyone I know ' + wrong + ' fine.')
    add('agree.indef_' + NAMEY(wrong), pat, vrep(right), 'Agreement', 0.96,
        'Words like ' + q('everyone') + ' and ' + q('nobody') + ' take ' + q(right) + '.', pos, neg)

# --- each / either / neither of ---------------------------------------------------------------------------
for who, conf, pronoun_only in (('each', 0.95, False), ('either|neither', 0.82, False)):
    tag = 'each' if who == 'each' else 'eitherneither'
    word = 'Each' if who == 'each' else 'Neither'
    for wrong, right, comp in TO_SG:
        pre = F + lc_for(wrong, CLN_SG)
        # pronoun form: each of them / us / you
        pat = pre + r'(?:' + who + r') of (?:us|them|you) (?P<target>' + vpat(wrong) + r')\b'
        pos = (word + ' of them ' + wrong + ' ' + comp + '.')
        if wrong == 'do':
            pos = 'I think ' + word.lower() + ' of them do the work.'
        elif wrong == 'have':
            pos = word + ' of them have arrived.'
        neg = (word + ' of them ' + right + ' ' + comp + '. Let ' + word.lower() + ' of them ' + ('have' if wrong == 'have' else 'do' if wrong == 'do' else 'go') +
               ' a turn. If ' + word.lower() + ' of them were here, we could start. Both of them ' + wrong + ' ' + comp + '.')
        add('agree.' + tag + '_of_them_' + NAMEY(wrong), pat, vrep(right), 'Agreement', conf,
            q(word) + ' with ' + q('of them') + ' takes ' + q(right) + '.', pos, neg)
        # noun form: each of the students
        pat = pre + r'(?:' + who + r') of (?:' + DET_P + r') (?:' + ADJ_RX + r' )?\w+s (?P<target>' + vpat(wrong) + r')\b'
        pos = (word + ' of the students ' + wrong + ' ' + comp + '.')
        if wrong == 'do':
            pos = 'I think ' + word.lower() + ' of the students do the work.'
        elif wrong == 'have':
            pos = word + ' of the students have arrived.'
        neg = (word + ' of the students ' + right + ' ' + comp + '. Let ' + word.lower() + ' of the students ' + ('have' if wrong == 'have' else 'do' if wrong == 'do' else 'go') +
               ' a turn. ' + word + ' of the students she teaches ' + right + ' ' + comp + '. I told ' + word.lower() + ' of the boys they ' + wrong + ' ' + comp + '. Both of the students ' + wrong + ' ' + comp + '.')
        add('agree.' + tag + '_of_nouns_' + NAMEY(wrong), pat, vrep(right), 'Agreement', conf,
            q(word) + ' is singular, so use ' + q(right) + '.', pos, neg)

# --- "each of it", "all of it are" ---------------------------------------------------------------------
for wrong, right, comp in TO_SG:
    pre = F + lc_for(wrong, CLN_SG)
    pat = pre + r'(?:all|most|some|much|half|none|any|a lot|a little|part|the rest) of it (?P<target>' + vpat(wrong) + r')\b'
    pos = {'are': 'Most of it are wrong.', 'were': 'Some of it were wrong.', 'have': 'I think most of it have changed.',
           'do': 'I think most of it do the job.', "aren't": 'Most of it aren\'t correct.',
           "weren't": 'Most of it weren\'t correct.', "haven't": 'I think most of it haven\'t changed.',
           "don't": 'I think most of it don\'t matter.'}[wrong]
    neg = ('Most of it ' + right + ' ' + comp + '. Most of them ' + wrong + ' ' + comp + '. If some of it were wrong, I would say so.')
    add('agree.partitive_of_it_' + NAMEY(wrong), pat, vrep(right), 'Agreement', 0.95,
        q('Most of it') + ' is singular, so use ' + q(right) + '.', pos, neg)

# --- all / most / many / both of them + singular verb ----------------------------------------------------
for wrong, right, comp in TO_PL:
    pat = F + r'\b(?:all|most|many|several|few|some|both|half|plenty|dozens|hundreds|a few|lots|a lot) of (?:them|us|you) (?P<target>' + vpat(wrong) + r')\b'
    pos = {'is': 'Most of them is ready.', 'was': 'Some of them was late.', 'has': 'Many of them has arrived.',
           'does': 'Most of them does the work.', "isn't": 'Most of them isn\'t ready.', "wasn't": 'Most of them wasn\'t late.',
           "hasn't": 'Many of them hasn\'t arrived.', "doesn't": 'Most of them doesn\'t agree.'}[wrong]
    neg = ('Most of them ' + right + ' ' + comp + '. Most of it ' + wrong + ' ' + comp + '. None of them ' + wrong + ' ' + comp + '. Each of them ' + wrong + ' ' + comp + '.')
    add('agree.partitive_of_them_' + NAMEY(wrong), pat, vrep(right), 'Agreement', 0.95,
        'A plural group takes ' + q(right) + '.', pos, neg)

# --- both + singular verb -----------------------------------------------------------------------------
for wrong, right, comp in TO_PL:
    pat = F + CLN + r'both (?P<target>' + vpat(wrong) + r')\b'
    pos = {'is': 'I think both is correct.', 'was': 'Both was late.', 'has': 'I think both has arrived.',
           'does': 'I think both does the work.', "isn't": 'I think both isn\'t correct.', "wasn't": 'I think both wasn\'t late.',
           "hasn't": 'I think both hasn\'t arrived.', "doesn't": 'I think both doesn\'t agree.'}[wrong]
    neg = ('Both ' + right + ' ' + comp + '. Both of them ' + right + ' ' + comp + '. Each ' + wrong + ' ' + comp + '. Both sides ' + right + ' ' + comp + '.')
    add('agree.both_' + NAMEY(wrong), pat, vrep(right), 'Agreement', 0.96,
        q('Both') + ' is plural, so use ' + q(right) + '.', pos, neg)
    pat = F + CLN + r'both of (?:' + DET_P + r') (?:' + ADJ_RX + r' )?\w+ (?P<target>' + vpat(wrong) + r')\b'
    pos = 'I think both of the students ' + wrong + ' ' + comp + '.'
    neg = ('Both of the students ' + right + ' ' + comp + '. Both of the reasons she ' + wrong + ' ' + comp + '. Each of the students ' + wrong + ' ' + comp + '.')
    add('agree.both_of_nouns_' + NAMEY(wrong), pat, vrep(right), 'Agreement', 0.95,
        q('Both of') + ' takes a plural verb: ' + q(right) + '.', pos, neg)

# --- one of the + plural + plural verb ----------------------------------------------------------------------
ADJ_X = ('(?:(?:most|very|more|least) )?(?:best|worst|biggest|largest|smallest|oldest|newest|greatest|finest|top|'
         'leading|main|major|key|important|popular|famous|common|new|old|first|last|great|good|bad|many|other|'
         'same|big|small|large|little|long|short|young|late|best-known|well-known|recent|useful)')
for wrong, right, comp in TO_SG:
    lc = lc_for(wrong, CLN_SG)
    pat = (F + lc + r'(?:only )?(?:one|each one|every one) of (?:' + DET_P + r') (?:' + ADJ_X + r' )?(?:\w+s|people|children|men|women) (?P<target>'
           + vpat(wrong) + r')\b')
    pos = {'are': 'One of the students are absent.', 'were': 'One of the students were absent.',
           'have': 'One of the students have called.', 'do': 'I think one of the students do the work.',
           "aren't": 'One of the students aren\'t ready.', "weren't": 'One of the students weren\'t ready.',
           "haven't": 'One of the students haven\'t called.', "don't": 'One of the students don\'t agree.'}[wrong]
    neg = ('One of the students ' + right + ' ' + comp + '. One of the reasons users ' + wrong + ' ' + comp + '. '
           'Let one of the students ' + ('have' if wrong == 'have' else 'do' if wrong == 'do' else 'go') + ' first. '
           'He is one of the students who ' + wrong + ' ' + comp + '. One of the issues we ' + wrong + ' ' + comp + '. '
           'Two of the students ' + wrong + ' ' + comp + '.')
    add('agree.one_of_' + NAMEY(wrong), pat, vrep(right), 'Agreement', 0.95,
        q('One of') + ' takes ' + q(right) + ': the subject is ' + q('one') + '.', pos, neg)

# --- the number of / a number of --------------------------------------------------------------------------
for wrong, right, comp in TO_SG:
    lc = lc_for(wrong, CLN_SG)
    pat = (F + lc + r'the number of (?:' + ADJ_X + r' )?(?:\w+s|people|children|men|women) (?P<target>' + vpat(wrong) + r')\b')
    pos = {'are': 'The number of students are growing.', 'were': 'The number of students were small.',
           'have': 'The number of students have grown.', 'do': 'I think the number of students do matter.',
           "aren't": 'The number of students aren\'t growing.', "weren't": 'The number of students weren\'t small.',
           "haven't": 'The number of students haven\'t changed.', "don't": 'The number of students don\'t matter.'}[wrong]
    neg = ('The number of students ' + right + ' ' + comp + '. A number of students ' + wrong + ' ' + comp + '. '
           'The number of students who ' + wrong + ' ' + comp + '. The numbers ' + wrong + ' ' + comp + '.')
    add('agree.the_number_of_' + NAMEY(wrong), pat, vrep(right), 'Agreement', 0.96,
        q('The number of') + ' takes ' + q(right) + '.', pos, neg)
for wrong, right, comp in TO_PL:
    pat = (F + CLN + r'a number of (?:' + ADJ_X + r' )?(?:\w+s|people|children|men|women) (?P<target>' + vpat(wrong) + r')\b')
    pos = {'is': 'A number of students is absent.', 'was': 'A number of students was absent.',
           'has': 'A number of students has called.', 'does': 'A number of students does the work.',
           "isn't": 'A number of students isn\'t ready.', "wasn't": 'A number of students wasn\'t ready.',
           "hasn't": 'A number of students hasn\'t called.', "doesn't": 'A number of students doesn\'t agree.'}[wrong]
    neg = ('A number of students ' + right + ' ' + comp + '. The number of students ' + wrong + ' ' + comp + '. A number of the reasons she ' + wrong + ' ' + comp + '.')
    add('agree.a_number_of_' + NAMEY(wrong), pat, vrep(right), 'Agreement', 0.96,
        q('A number of') + ' means ' + q('several') + ' and takes ' + q(right) + '.', pos, neg)

# --- heads: "the list of items ARE" -> is -------------------------------------------------------------------
HEADS = ('list|set|collection|amount|quality|price|cost|size|name|purpose|use|importance|history|role|meaning|'
         'cause|result|goal|top|bottom|end|beginning|middle|front|back|side|owner|author|creator|director|leader|member|'
         'president|editor|founder|teacher|student|effect|impact|level|presence|absence|lack|loss|growth|increase|'
         'structure|design|layout|version|status|risk|benefit|reason|answer|solution|rate|speed|weight|length|shape|'
         'content|description|summary|value|total|sum|average')
HEADS = '|'.join(sorted(set(h for h in HEADS.split('|') if not h.endswith('_skip'))))
for wrong, right, comp in TO_SG:
    lc = lc_for(wrong, CLN_SG)
    pat = (F + lc + r'(?:the|this|that|my|our|your|his|her|their|a|an) (?:' + ADJ_RX + r' )?(?-i:' + HEADS + r') of (?:(?:' + DET_P + r'|some|many|several|various|all) )?(?:' + ADJ_RX + r' )?(?-i:\w+s|people|children|men|women) (?P<target>' + vpat(wrong) + r')\b')
    pos = {'are': 'The list of items are long.', 'were': 'The owner of the shops were away.',
           'have': 'The owner of the shops have left.', 'do': 'I think the owner of the shops do the books.',
           "aren't": 'The list of items aren\'t complete.', "weren't": 'The owner of the shops weren\'t there.',
           "haven't": 'The owner of the shops haven\'t called.', "don't": 'The owner of the shops don\'t agree.'}[wrong]
    neg = ('The list of items ' + right + ' ' + comp + '. The items on the list ' + wrong + ' ' + comp + '. The list of items you sent ' + wrong + ' ' + comp + '. '
           'At the top of the stairs ' + wrong + ' two doors. The list of items that ' + wrong + ' missing is short.')
    add('agree.head_of_' + NAMEY(wrong), pat, vrep(right), 'Agreement', 0.93,
        'The subject is the singular noun before ' + q('of') + ', so use ' + q(right) + '.', pos, neg)

PL_HEADS_RX = ('results|names|files|reports|members|leaders|owners|authors|parents|friends|students|teachers|managers|directors|'
               'editors|founders|designers|writers|readers|users|customers|clients|patients|employees|players|winners|numbers|'
               'prices|costs|rates|levels|sizes|colors|colours|reasons|causes|effects|impacts|roles|goals|aims|points|rules|'
               'steps|details|questions|answers|changes|updates|items|entries|records|pages|lines|songs|titles|images|photos|'
               'pictures|videos|documents|emails|messages|notes|tasks|tickets|orders|payments|accounts|rooms|doors|windows|'
               'books|cars|houses|shops|schools|friends|neighbors|neighbours|children|people|women|men')
for wrong, right, comp in TO_PL:
    pat = (F + CLN + r'(?:' + DET_P + r') (?:' + ADJ_RX + r' )?(?-i:' + PL_HEADS_RX + r') of (?:the|this|that|my|our|your|his|her|their|a|an) (?:' + ADJ_RX + r' )?(?-i:\w+) (?P<target>' + vpat(wrong) + r')\b')
    pos = {'is': 'The results of the survey is clear.', 'was': 'The results of the survey was clear.',
           'has': 'The results of the survey has arrived.', 'does': 'The results of the survey does matter.',
           "isn't": 'The results of the survey isn\'t clear.', "wasn't": 'The results of the survey wasn\'t clear.',
           "hasn't": 'The results of the survey hasn\'t arrived.', "doesn't": 'The results of the survey doesn\'t matter.'}[wrong]
    neg = ('The results of the survey ' + right + ' ' + comp + '. The result of the survey ' + wrong + ' ' + comp + '. The results of the survey, which ' + wrong + ' ' + comp + ', are in. '
           'The results of the survey you ran ' + wrong + ' ' + comp + '.')
    add('agree.plural_head_of_' + NAMEY(wrong), pat, vrep(right), 'Agreement', 0.92,
        'The subject is the plural noun before ' + q('of') + ', so use ' + q(right) + '.', pos, neg)
