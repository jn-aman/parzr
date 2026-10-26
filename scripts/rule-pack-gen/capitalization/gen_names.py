"""Names that are also ordinary words (turkey, china, polish, dutch...), plus people, scriptures and faiths.

A name that doubles as a common noun is capitalized only in a frame that cannot be the common noun: a travel verb and
a preposition before a country, a language verb before a language, a noun like "people" after a nationality.
"""
from lib import *

# What can follow such a name: the end of the clause or a function word, never a noun that would make it the
# common-noun reading ("polish the table", "china cabinet", "turkey sandwich").
FOLLOW = (r"(?:['’]s)?(?:\s*[,.;:!?)\]\"”’]|\s*$|\s+(?:and|or|but|for|with|to|from|on|at|in|is|are|was|were|has|have|"
          r"had|will|would|can|could|may|might|last|next|this|during|when|where|which|that|who|after|before|since|"
          r"until|because|so|as|by|yesterday|today|tomorrow|now|then|too|also|again|instead|only|just|every|each|"
          r"every|again|soon|later|earlier|once|twice|over|about|through|within|without|via|per|than|if|while|"
          r"although|though|these|those|all|both|either|neither|nor|yet|still|already|always|never)\b)")

TRAVEL = (r"(?:flew|fly|flies|flying|flight|flights|trip|trips|travel|travels|traveled|travelled|traveling|"
          r"travelling|move|moves|moved|moving|relocate|relocated|relocating|relocation|vacation|vacationed|holiday|"
          r"holidays|visa|visit|visited|visiting|visits|live|lives|lived|living|born|raised|grew up|grown up|based|"
          r"work|works|worked|working|stay|stayed|staying|studied|study|studying|studies|go|goes|went|gone|going|"
          r"return|returned|returning|moved back|go back|went back|came back|come back|coming back|arrive|arrived|"
          r"arriving|land|landed|landing|tour|toured|touring|trek|trekked|backpacking|backpacked|retire|retired|"
          r"retiring|settle|settled|settling|emigrate|emigrated|immigrate|immigrated|deport|deported|expat|expats|"
          r"conference|summit|meeting|office|offices|branch|branches|team|teams|customers|clients|students|"
          r"shipping|ship|ships|shipped|deliver|delivers|delivered|delivery|order|orders|ordered|exports?|imports?|"
          r"exported|imported|trade|trading|invest|invests|invested|investing|investment|investments|sell|sells|"
          r"sold|selling|launch|launched|launching|expand|expanded|expanding|expansion|open|opened|opening|"
          r"operate|operates|operated|operating|operation|operations)")


def emit_loc(canon, kind, rid_kind, extra_pre='', nouns='', common_negative='', pos_sentence=None, conf=0.9):
    lower = canon.lower()
    alts = [f'(?i:{TRAVEL}\\s+(?:to|in|from|across|throughout|around|within|near)\\s+)']
    if extra_pre:
        alts.append(f'(?i:{extra_pre})')
    pre = '(?:' + '|'.join(alts) + ')'
    pat = f'{pre}(?P<target>(?-i:{lower})){FOLLOW}'
    pos = pos_sentence or f'We moved to {lower} last year.'
    neg = f'We moved to {canon} last year. {common_negative}'.strip()
    emit(f'caps.{rid_kind}.{slug(canon)}', pat, canon, 'Capitalization', conf,
         'Names of countries and cities take a capital letter.', pos, neg, 'Places that are also ordinary words')
    if nouns:
        # possessive + a noun only a country has: "china's economy"
        pat2 = f"{LEFT}(?P<target>(?-i:{lower}))['’]s\\s+(?:{nouns})\\b"
        pos2 = f"Sales rose because {lower}'s economy grew again this year."
        neg2 = f"Sales rose because {canon}'s economy grew again this year. {common_negative}".strip()
        emit(f'caps.{rid_kind}.{slug(canon)}_possessive', pat2, canon, 'Capitalization', conf,
             'Names of countries and cities take a capital letter.', pos2.replace('economy', nouns.split('|')[0]),
             neg2.replace('economy', nouns.split('|')[0]), 'Places that are also ordinary words')


COUNTRY_NOUNS = ('economy|government|president|capital|border|borders|population|army|military|currency|exports|imports|'
                 'foreign policy|parliament|prime minister|central bank|stock market|embassy|foreign minister')


def build_places():
    emit_loc('Turkey', 'country', 'country', nouns=COUNTRY_NOUNS,
             common_negative='We roasted a turkey for dinner. The turkey sandwich sold out, and turkey bacon is on the menu.')
    emit_loc('China', 'country', 'country', extra_pre=r'(?:made|manufactured|produced|assembled|sourced|shipped|imported|exported) (?:in|from|to) ',
             nouns=COUNTRY_NOUNS,
             common_negative='She collects fine china and bone china. Set the table with the good china plates.')
    emit_loc('Wales', 'country', 'country', extra_pre=r'(?:north|south|mid|west|south-west|north-west) ',
             common_negative='Blue whales and sperm whales were seen; the wales of the corduroy were deep.')
    emit_loc('Chile', 'country', 'country', nouns=COUNTRY_NOUNS,
             common_negative='We ordered a green chile stew with chile peppers and a chile relleno.')
    emit_loc('Chad', 'country', 'country', nouns=COUNTRY_NOUNS,
             common_negative='The hanging chad ballots were recounted. Chad Smith runs the lab.')
    emit_loc('Panama', 'country', 'country', nouns=COUNTRY_NOUNS,
             common_negative='He wore a straw panama hat with a ribbon.')
    emit_loc('Guinea', 'country', 'country', nouns=COUNTRY_NOUNS,
             common_negative='The guinea pig hid under the guinea fowl cage; a guinea was once worth 21 shillings.')
    emit_loc('Morocco', 'country', 'country', nouns=COUNTRY_NOUNS,
             common_negative='The old book was bound in morocco leather.')
    emit_loc('Niger', 'country', 'country', nouns=COUNTRY_NOUNS,
             common_negative='The seed oil came from the niger plant.')
    emit_loc('Jordan', 'country', 'country', nouns=COUNTRY_NOUNS,
             common_negative='He laced up his old jordans before the game, and Jordan Lee scored first.')
    # cities
    emit_loc('Shanghai', 'city', 'city', extra_pre=r'(?:in|from|of|near|outside|around) ',
             common_negative='The pirates tried to shanghai him onto the ship.')
    emit_loc('Manila', 'city', 'city', extra_pre=r'(?:in|from|to|of|near|outside|around) ',
             common_negative='Put the form in a manila envelope inside a manila folder.')
    emit_loc('Hamburg', 'city', 'city', common_negative='The hamburg steak and the hamburger were both on the menu.')
    emit_loc('Bologna', 'city', 'city', common_negative='He ate a bologna sandwich on the train.')
    emit_loc('Oxford', 'city', 'city', common_negative='He bought black oxford shoes and a white oxford shirt.')
    emit_loc('Cork', 'city', 'city', common_negative='She pulled the cork from the bottle and set it on a cork mat.')
    emit_loc('Mecca', 'city', 'city', common_negative='The shop is a mecca for collectors, a mecca for hikers.')
    emit_loc('Cologne', 'city', 'city', common_negative='He splashed on some cologne and sprayed the cologne bottle.')
    emit_loc('Phoenix', 'city', 'city', common_negative='A phoenix rose from the ashes in the legend.')
    emit_loc('Buffalo', 'city', 'city', common_negative='A buffalo herd crossed the road, and buffalo wings arrived.')
    emit_loc('Anchorage', 'city', 'city', common_negative='The boat found a safe anchorage in the bay.')
    emit_loc('Muscat', 'city', 'city', common_negative='The muscat grapes made a sweet wine.')

    # two-part forms: "springfield, illinois" style where the second word fixes the reading
    pairs = [
        ('Anchorage, Alaska', r'anchorage(?P<c>,) (?P<t>alaska|ak)'),
    ]


def build_langs_ordinary():
    """Languages and nationalities that are also ordinary words."""
    fam = 'Languages that are also words'
    lang_verbs = (r'(?:speak|speaks|speaking|spoke|spoken|learn|learns|learning|learned|learnt|study|studies|studying|'
                  r'studied|fluent in|fluent|native|bilingual in|translate to|translate into|translated into|'
                  r'translated to|translates into|translating into|translation into|lessons in|classes in|'
                  r'course in|courses in|proficient in|conversational|certified in|'
                  r'(?:written|translated|available|subtitled|dubbed|published|printed|titled|said|reply|replied|'
                  r'answer|answered|write|wrote|writing|talk|talked|talking|chat|chatted|chatting|text|texted|'
                  r'texting|type|typed|typing|sing|sang|singing|pray|prayed|praying|swear|swore|swearing|dream|'
                  r'dreamed|dreaming|think|thinking|count|counting|read|reading|taught|teach|teaching|spoken) in)')
    det = (r'(?:the|a|an|our|my|your|their|his|her|its|many|some|most|all|several|these|those|two|three|four|five|few|'
           r'other|every|each|no|any|of|from|by|between|among|with|for|against|than|like|per|plus|and|or|but)')
    nat_nouns = (r'(?:people|man|men|woman|women|boy|girl|kid|kids|child|children|citizen|citizens|national|nationals|'
                 r'speaker|speakers|government|embassy|passport|passports|border|army|police|president|prime minister|'
                 r'parliament|capital|cuisine|diaspora|immigrants|immigrant|migrants|migrant|football|league|cup|'
                 r'delegation|delegates|ambassador|ambassadors|minister|ministers|nationality|origin|ancestry)')
    for canon, extra_neg in [
        ('Dutch', 'Let us go dutch on the bill, and she needed some dutch courage.'),
        ('Polish', 'Please polish the silver, add a coat of polish and buy nail polish.'),
        ('Danish', 'He had a cheese danish and a danish pastry with coffee.'),
        ('Welsh', 'They welsh on bets sometimes, and we ate welsh rarebit.'),
    ]:
        lower = canon.lower()
        pat = f'(?i:\\b{lang_verbs}\\s+)(?P<target>(?-i:{lower})){FOLLOW}'
        pos = f'She learned to speak {lower} at home.'
        neg = f'She learned to speak {canon} at home. {extra_neg}'
        emit(f'caps.lang.{lower}_verb', pat, canon, 'Capitalization', 0.9,
             'Names of languages and nationalities take a capital letter.', pos, neg, fam)
        pat = f'(?i:\\b{det}\\s+)(?P<target>(?-i:{lower}))\\s+(?i:{nat_nouns})\\b'
        pos = f'The {lower} government sent a delegation to the summit.'
        neg = f'The {canon} government sent a delegation to the summit. {extra_neg}'
        emit(f'caps.people.{lower}_noun', pat, canon, 'Capitalization', 0.9,
             'Names of nationalities take a capital letter.', pos, neg, fam)
    emit('caps.lang.mandarin_verb', f'(?i:\\b{lang_verbs}\\s+)(?P<target>(?-i:mandarin)){FOLLOW}', 'Mandarin',
         'Capitalization', 0.9, 'Names of languages take a capital letter.', 'She speaks mandarin at work.',
         'She speaks Mandarin at work. He peeled a mandarin and wore a mandarin collar.', fam)
    emit('caps.lang.basque_verb', f'(?i:\\b{lang_verbs}\\s+)(?P<target>(?-i:basque)){FOLLOW}', 'Basque',
         'Capitalization', 0.9, 'Names of languages take a capital letter.', 'They speak basque in the village.',
         'They speak Basque in the village. The dress had a lace basque top.', fam)
    emit('caps.people.afghan_noun',
         f'(?i:\\b{det}\\s+)(?P<target>(?-i:afghan))\\s+(?i:{nat_nouns}|refugees|refugee|forces)\\b',
         'Afghan', 'Capitalization', 0.9, 'Names of nationalities take a capital letter.',
         'The afghan government met the delegation.',
         'The Afghan government met the delegation. She knitted an afghan blanket.', fam)
    for lower, canon, nouns, neg in [
        ('catholic', 'Catholic', r'church|churches|school|schools|priest|priests|bishop|bishops|diocese|mass|faith|'
         r'university|college|hospital|charity|charities|cardinal|nun|nuns|tradition|teaching|'
         r'teachings|doctrine|clergy|parish|cathedral|pope', 'Her tastes are catholic and broad.'),
        ('baptist', 'Baptist', r'church|churches|minister|pastor|preacher|school|college|convention|congregation|'
         r'tradition|university', 'John the baptist was a fine saint.'),
        ('episcopal', 'Episcopal', r'church|churches|priest|bishop|diocese|school|congregation|parish|cathedral',
         'The episcopal authority of the bishop was limited.'),
        ('evangelical', 'Evangelical', r'church|churches|christian|christians|pastor|pastors|movement|voters|voter|'
         r'protestant|congregation', 'He spoke with evangelical zeal about the new tool.'),
        ('orthodox', 'Orthodox', r'church|churches|christian|christians|jew|jews|jewish|priest|priests|synagogue|'
         r'christianity|judaism|monastery|patriarch|rabbi', 'He holds some orthodox views on grammar.'),
    ]:
        emit(f'caps.faith.{lower}_noun',
             f'{LEFT}(?P<target>(?-i:{lower}))\\s+(?i:{nouns})\\b', canon, 'Capitalization', 0.88,
             'Names of religions and denominations take a capital letter.',
             f'The {lower} church on the hill was rebuilt.',
             f'The {canon} church on the hill was rebuilt. {neg}', 'Faiths and denominations')


# --- people, deities and scriptures that are never ordinary words ----------------------------------------------

DEITIES = ['Jesus', 'Christ', 'Allah', 'Muhammad', 'Mohammed', 'Krishna', 'Ganesha', 'Vishnu', 'Hanuman',
           'Lakshmi', 'Durga', 'Saraswati', 'Parvati', 'Jehovah', 'Yahweh', 'Buddha', 'Zeus', 'Poseidon', 'Confucius',
           'Satan', 'Lucifer']
SCRIPTURE = """Talmud|Vedas|Bhagavad Gita|Guru Granth Sahib|Old Testament|New Testament|Ramayana|Mahabharata|Upanishads|
Torah|Book of Mormon|Dead Sea Scrolls|Ten Commandments|Sermon on the Mount|Holy Bible|Holy Quran|Holy Spirit|
Holy Trinity|Jehovah's Witnesses|Roman Catholic|Eastern Orthodox|Church of England|Church of Scotland|
Methodism|Calvinism|Lutheranism|Anglicanism|Mormonism|Scientology|Jainism|Zoroastrianism|Taoism|Shintoism|Sufism|
Confucianism|Rastafarianism|Baha'i|Hasidic|Shia|Rabbi|Santa Claus|Father Christmas|Easter Bunny|Tooth Fairy|
Noah's Ark|Garden of Eden""".replace('\n', '').split('|')
SCRIPTURE = [s for s in SCRIPTURE if s.lower() not in GAZ and s not in {'Rabbi', 'Tooth Fairy', 'Sabbath'}]


def build_faith():
    for d in dict.fromkeys(DEITIES):
        phrase_rule(f'caps.faith.{slug(d)}', d, LEFT, RIGHT, 0.92,
                    'Names of deities, prophets and holy figures take a capital letter.',
                    'She read a book about {x} last week.', 'Faiths and holy figures')
    for s in dict.fromkeys(SCRIPTURE):
        phrase_rule(f'caps.faith.{slug(s)}', s, LEFT, RIGHT_H, 0.92,
                    'Names of religions, scriptures and holy texts take a capital letter.',
                    'The class discussed {x} on Tuesday.', 'Faiths and holy figures')
    # the Bible / the Gospel / a rabbi: capital only in a religious frame
    emit('caps.faith.bible_frame',
         r"(?i:\b(?:in the|from the|according to the|quoted the|quotes the|quoting the|read the|reads the|reading the|"
         r"about the|on the|studied the|study the|says the|said the|holy|lines in the|verses in the|written in the)\s+)"
         r"(?P<target>(?-i:bible))" + FOLLOW,
         'Bible', 'Capitalization', 0.88, 'The Bible takes a capital letter when it names the scripture.',
         'He quoted the bible in his speech.',
         'He quoted the Bible in his speech. Her cookbook is the bible of French cooking, said the reviewer, and a '
         'bible study group met; the style guide is the bible.', 'Faiths and holy figures')
    emit('caps.faith.bible_says',
         f'{LEFT}(?i:the)\\s+(?P<target>(?-i:bible))\\s+(?:says|said|teaches|tells|states|verse|verses|passage|passages|translation|translations)\\b',
         'Bible', 'Capitalization', 0.9, 'The Bible takes a capital letter when it names the scripture.',
         'The bible says that we should rest.', 'The Bible says that we should rest.', 'Faiths and holy figures')
    emit('caps.faith.gospel_of',
         f'{LEFT}(?:the\\s+)?(?P<target>(?-i:gospel))\\s+(?:of|according to)\\s+(?-i:[A-Z][a-z]+)',
         'Gospel', 'Capitalization', 0.9, 'Name the book of the Bible with a capital letter.',
         'We read the gospel of Mark aloud.',
         'We read the Gospel of Mark aloud. He preached the gospel of hard work, and sang gospel music.', 'Faiths and holy figures')
    emit('caps.faith.sabbath_frame',
         f'(?i:keep|keeps|kept|keeping|observe|observes|observed|break|breaking|on|the|jewish|christian)\\s+(?P<target>(?-i:sabbath)){RIGHT}',
         'Sabbath', 'Capitalization', 0.88, 'The Sabbath takes a capital letter.',
         'They keep the sabbath every week.',
         'They keep the Sabbath every week. She took a sabbatical and a sabbath-like rest.', 'Faiths and holy figures')


def build():
    build_places()
    build_langs_ordinary()
    build_faith()
