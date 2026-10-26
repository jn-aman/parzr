"""Prefixes and fixed forms that take a hyphen: self-, ex-, co-, non-, mid-, pre-, post-, anti-, pro-, all-, re-,
-in-law, -elect, -to-be, great-grand..., and the split words "e mail" and "re send"."""
import re
import core
import lists

# --- self- ---------------------------------------------------------------------------------------------------------
# stem and a sentence frame: n = noun ("It is about self-esteem."), a = adjective ("She is very self-employed.")
SELF = """
esteem n
employed a
aware a
awareness n
confidence n
confident a
control n
care n
service n
taught a
made a
defense n
defence n
driving a
help n
conscious a
centered a
centred a
sufficient a
sufficiency n
explanatory a
evident a
respect n
worth n
discipline n
improvement n
assessment n
reflection n
paced a
storage n
absorbed a
critical a
destructive a
indulgent a
motivated a
righteous a
serving a
deprecating a
important a
contained a
determination n
portrait n
harm n
image n
interest n
love n
promotion n
published a
reliant a
selected a
sabotage n
expression n
management n
directed a
regulation n
preservation n
actualization n
doubt n
isolation n
quarantine n
assured a
assurance n
employment n
starter n
cleaning a
healing n
hypnosis n
checkout n
test n
hosted a
signed a
learning n
awareness n
driven a
discovery n
critique n
education n
compassion n
acceptance n
sustaining a
supporting a
funded a
financed a
insured a
regulated a
governing a
governance n
administered a
""".strip().splitlines()

EX_NOUNS = ('mayor governor senator minister soldier convict champion player captain manager lover classmate teammate '
            'client customer landlord landlady teacher coach marine cop officer').split()
EX_PLURALS = ('wives husbands boyfriends girlfriends partners colleagues coworkers employees bosses members spouses '
              'presidents').split()

CO = ('worker author founder owner pilot host star chair creator sponsor presenter producer parent parenting working '
      'signer defendant conspirator editor lead led branded branding').split()

NON_PROPER = ('English Hispanic Muslim Jewish Christian Catholic White Black European American Asian African Western '
              'Native Indian Canadian German French Spanish Chinese Japanese Russian Arab Windows Latino Hindu '
              'Buddhist').split()
NON_ACRONYMS = ['US', 'EU', 'UK', 'UN', 'NATO', 'OECD', 'GDPR', 'HIPAA', 'IT', 'STEM', 'NHS']

MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November',
          'December']
MID_NOUNS = 'air morning afternoon century sentence conversation flight season'.split()

PRE = """
existing :: a :: The tool keeps its pre existing settings.
owned :: a :: She bought a pre owned car.
industrial :: a :: It was a pre industrial society.
pandemic :: a :: Prices were lower in the pre pandemic years.
war :: a :: The pre war houses were small.
Christmas :: a :: The pre Christmas rush starts early.
COVID :: a :: Sales were higher in the pre COVID period.
Brexit :: a :: Trade was easier in the pre Brexit era.
order :: n :: You can pre order the book today.
season :: n :: The team starts its pre season in July.
launch :: a :: The pre launch survey closes Friday.
""".strip().splitlines()

POST = """
COVID :: The post COVID world looks different.
pandemic :: Hiring recovered in the post pandemic period.
Brexit :: Rules changed in the post Brexit era.
war :: The post war economy grew quickly.
industrial :: It was a post industrial town.
traumatic :: He lives with post traumatic stress.
operative :: The post operative care lasted a week.
""".strip().splitlines()

ANTI = """
inflammatory :: She took an anti inflammatory pill.
aging :: He bought an anti aging cream.
American :: The speech was called anti American.
Semitic :: The remark was anti Semitic.
spam :: The anti spam filter blocked it.
inflation :: The anti inflation measures worked.
bullying :: The school runs an anti bullying campaign.
corruption :: The anti corruption office opened.
establishment :: It was an anti establishment protest.
discrimination :: The anti discrimination law passed.
harassment :: The anti harassment policy is clear.
""".strip().splitlines()

PRO = """
life :: She is pro life.
choice :: He is pro choice.
American :: It was a pro American speech.
Russian :: The pro Russian group met.
business :: It is a pro business policy.
democracy :: A pro democracy march began.
EU :: She joined the pro EU rally.
gun :: He is a pro gun lobbyist.
""".strip().splitlines()

ALL = """
inclusive :: We booked an all inclusive package.
purpose :: I bought an all purpose cleaner.
""".strip().splitlines()

IN_LAW_ROLES = ['mother', 'father', 'brother', 'sister', 'son', 'daughter']
# words that can follow "mother in law" (a sentence end, a conjunction, a verb or a preposition) but not "enforcement"
IN_LAW_AFTER = (r'(?:[,.;:!?)]|$|\s+(?:and|but|or|is|are|was|were|who|has|have|had|will|would|can|could|lives|works|said|'
                r'says|told|came|called|visited|arrived|always|never|also|too|to|for|from|about|at|on|with|of|that|which|'
                r'as|so|when|if|because|does|did|even|then|just|really|still|only|often|asked|gave|moved|got|made|took|'
                r'wants|likes|loves)\b)')

SPLIT_RE_JOIN = 'send submit schedule launch install run design write think build load name order create apply connect test try upload'.split()
RE_VOWEL = 'enter elect examine evaluate establish engage emerge emphasize energize enable entry election'.split()
