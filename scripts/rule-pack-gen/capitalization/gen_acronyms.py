"""Acronyms and initialisms typed in lowercase (nasa, api, ceo...), with context for the ones that are also words.

Tokens that mix letters and digits (html5, b2b, ps5, m1) are protected from every edit by the engine, so they are not
covered here.
"""
from lib import *

FAM = 'Acronyms and initialisms'
FAM_CTX = 'Acronyms that are also words (context rules)'

# Canonical spelling -> fixed. "Nasa" (capitalized only) is also wrong, unless the capitalized form is a real name.
SIMPLE = """NASA FBI NATO UNESCO UNICEF OPEC IMF WTO OECD ASEAN UAE USA NHS BBC CNN NBA NFL MLB NHL FIFA UEFA IPL BCCI WWE
UNHCR DMV FDA CDC EPA FEMA DARPA NOAA ISRO DRDO RBI SEBI SBI HDFC ICICI TCS HCL BJP IIT IIM AIIMS UPSC CBSE ICSE UGC
UCLA NYU NYC NYSE GDP GST KYC FAQ CEO CFO CTO CMO CIO CPO PTO MBA GPA GRE GMAT IELTS TOEFL JEE NEET CV USD EUR GBP INR
JPY AUD API URL URI HTML CSS JSON XML SQL PDF SDK UI UX GCP NLP LLM GPT VPN DNS CPU GPU SSD HDD HDMI OLED LCD USB
GPS VR XR IoT SaaS PaaS IaaS KPI OKR ROI CRM ERP CDN YAML CSV JPG JPEG PNG SVG SUV VIP DIY RSVP TBD TBA QA SMS OTP UPI
IFSC NEFT RTGS IRCTC SSL TLS TCP UDP JWT MVC GUI ASCII XSS CSRF OCR DNA RNA MRI ICU ECG EKG BMI ADHD OCD PTSD HIV
COVID UV LGBTQ AGI TTS ASR ISP SMTP IMAP RSS WYSIWYG CAPTCHA TV DVD KFC HBO MTV DDoS DevOps MLOps NoSQL GraphQL OAuth
UK""".split()
# Names that read as ordinary capitalized words (a surname, a name): only the all-lowercase spelling is fixed.
LOWER_ONLY = {'SEO', 'CIA', 'KFC', 'MRI', 'HIV', 'CAD', 'EUR', 'NYU', 'COVID', 'IRS', 'ICICI', 'RSS', 'DNA', 'RNA', 'PC', 'TV',
              'DVD', 'NSA', 'CV', 'UV', 'ISP', 'ECG', 'OCR', 'GUI', 'UK', 'EU', 'IoT', 'SaaS', 'PaaS', 'IaaS', 'DDoS',
              'DevOps', 'MLOps', 'NoSQL', 'GraphQL', 'OAuth', 'GPA', 'GST', 'AUD', 'JPY', 'GBP', 'INR', 'USD', 'TBA',
              'TBD', 'QA', 'SMS', 'OTP', 'UPI', 'GRE', 'CPO', 'CIO', 'PTO', 'NDA', 'WWE', 'CMS', 'CDN', 'DMV', 'FDA',
              'CDC', 'EPA'}
# Forms with a lowercase letter inside (SaaS): the wrong spelling is all lowercase, or capitalized.
# Acronyms whose capitalized-first spelling ("Api", "Nasa") is never a name or a word, so a sentence-start "Api" that the
# engine just capitalized is fixed on the next pass. Others (Saas, Cia, Seo, Eu, Nda...) are names somewhere.
SAFE_CAP = set("""API URL HTML CSS JSON XML SQL PDF FAQ CEO CFO CTO SDK GPS USB DVD VPN DNS CPU GPU SSD HDMI KPI""".split())
PLURALS = {'API': 'APIs', 'URL': 'URLs', 'FAQ': 'FAQs', 'CEO': 'CEOs', 'CTO': 'CTOs', 'CFO': 'CFOs', 'SDK': 'SDKs',
           'LLM': 'LLMs', 'GPU': 'GPUs', 'CPU': 'CPUs', 'SSD': 'SSDs', 'PDF': 'PDFs', 'NGO': 'NGOs', 'DVD': 'DVDs',
           'VPN': 'VPNs', 'KPI': 'KPIs', 'SUV': 'SUVs', 'TV': 'TVs', 'PNG': 'PNGs', 'CSV': 'CSVs', 'JPG': 'JPGs',
           'OKR': 'OKRs', 'MBA': 'MBAs', 'VIP': 'VIPs', 'CMO': 'CMOs', 'URI': 'URIs', 'GPT': 'GPTs'}
# "NGO" is also an ordinary three-letter combination only in names, so the rule is safe; add it to SIMPLE
SIMPLE.append('NGO')


# Python modules and CLI words that are also acronyms: framed like the developer tools in gen_brands, so that
# "import json" and "from csv import reader" stay as typed.
ACR_FRAMED = {'JSON', 'CSV', 'XML', 'HTML', 'SSL', 'SQL', 'YAML'}


def simple_acronym(canon):
    lower = canon.lower()
    if lower in GAZ:
        return
    alts = [lower]
    cap = canon[:1] + canon[1:].lower()
    if canon in SAFE_CAP and cap != lower and cap != canon:
        alts.append(cap)
    if canon == 'IoT':
        alts = ['iot', 'Iot', 'IOT']
    if canon in ('SaaS', 'PaaS', 'IaaS'):
        alts = [lower, canon.upper()]
    if canon == 'DDoS':
        alts = ['ddos', 'Ddos', 'DDOS']
    if canon == 'DevOps':
        alts = ['devops', 'Devops']
    if canon == 'MLOps':
        alts = ['mlops', 'Mlops', 'MLOPS']
    if canon == 'NoSQL':
        alts = ['nosql', 'Nosql', 'NOSQL', 'noSQL']
    if canon == 'GraphQL':
        return  # in brands
    if canon == 'OAuth':
        alts = ['oauth', 'Oauth', 'OAUTH']
    left = LEFT_MID if canon[:1].islower() else LEFT
    alts = [a for a in alts if a != canon]
    body = '|'.join(esc(a) for a in alts)
    pat = f'{left}(?P<target>(?-i:{body})){RIGHT_T}'
    sentence = 'Please send the {x} to the whole team.'
    pos = sentence.format(x=alts[0])
    neg = sentence.format(x=canon) + ' ' + neg_noise(lower)
    if canon in ACR_FRAMED:
        pat = f'{FRAME_DEV}(?P<target>(?-i:{body})){RIGHT_DEV}'
        pos = f'Please convert the file to {alts[0]} before lunch.'
        neg = (f'Please convert the file to {canon} before lunch. ' + neg_noise(lower) +
               f' Run import {lower}, then from {lower} import loads, and call {lower}.dumps(x).')
    emit(f'caps.acr.{slug(canon)}', pat, canon, 'Capitalization', 0.92,
         'This abbreviation is written in capitals.', pos, neg, FAM)


def build_simple():
    for c in dict.fromkeys(SIMPLE):
        simple_acronym(c)
    for sing, plural in PLURALS.items():
        lower = plural.lower()
        alts = [a for a in dict.fromkeys([lower]) if a != plural]
        body = '|'.join(esc(a) for a in alts)
        pat = f'{LEFT}(?P<target>(?-i:{body})){RIGHT_T}'
        sentence = 'We shipped three {x} before the deadline.'
        emit(f'caps.acr.{slug(plural)}', pat, plural, 'Capitalization', 0.92,
             'This abbreviation is written in capitals; the plural takes a small s.',
             sentence.format(x=alts[0]), sentence.format(x=plural) + ' ' + neg_noise(lower), FAM)


def build_ctx():
    def rule(rid, pat, repl, conf, pos, neg, reason='This abbreviation is written in capitals.'):
        emit(rid, pat, repl, 'Capitalization', conf, reason, pos, neg, FAM_CTX)

    END = RIGHT_T
    NOUN_AI = (r"tools?|models?|assistants?|agents?|systems?|chatbots?|startups?|companies|company|engineers?|researchers?|"
               r"safety|ethics|regulation|act|apps?|features?|products?|market|industry|hype|bubble|boom|revolution|labs?|"
               r"research|era|age|stack|infrastructure|chips?|adoption|strategy|team|teams|workflows?|automation|literacy|"
               r"policy|governance|risks?|alignment|training|inference|prompts?|content|images?|art|music|video|code|coding|"
               r"detection|detectors|writing|writer|skills?|courses?|degree|generated|powered|driven|based|enabled|"
               r"assisted|first|native|ready|summit|conference|community|laws?|bill|race|winter|expert|experts|"
               r"scientist|scientists|developer|developers|lab|platform|platforms|solutions?|services?|projects?")
    rule('caps.acr.ai_noun',
         f"{LEFT}(?P<target>(?-i:ai|Ai))(?:\\s+|-)(?i:{NOUN_AI})\\b",
         'AI', 0.9, 'Our ai tools write the first draft.',
         'Our AI tools write the first draft. Ai Weiwei is an artist, and she said ai in Japanese means love.')
    rule('caps.acr.ai_frame',
         r"(?i:\b(?:generative|artificial|the|an|of|with|using|use|uses|used|by|about|via|through|powered by|no|any|all|new|our|your|their|its|applied|responsible|ethical|conversational|enterprise|explainable|embedded|edge|agentic|general|advanced|modern|cutting-edge)\s+)(?P<target>(?-i:ai|Ai))(?:\s*[,.;:!?)\]\"”’]|\s*$|\s+(?:and|or|but|to|for|in|on|is|are|was|will|can|has|have|that|which)\b)",
         'AI', 0.88, 'We build products with ai and robots.',
         'We build products with AI and robots. Ai Weiwei joined the show.')
    rule('caps.acr.ml_noun',
         r"(?:^|[\s(\[\"“‘])(?P<target>(?-i:ml|Ml))\s+(?:model|models|engineer|engineers|team|pipeline|pipelines|ops|platform|training|infrastructure|algorithm|algorithms|research|scientist|scientists|libraries|library|framework|frameworks|workflow|workflows|project|projects|system|systems|experiments?|jobs?|engineering|developer|developers)\b",
         'ML', 0.9, 'The ml team retrained the model.',
         'The ML team retrained the model. Add 5 ml of water to the mix.')
    rule('caps.acr.eu_frame',
         r"(?i:\b(?:the|non|pro|anti|in the|of the|from the|to the|across the|within the|outside the|an|our|any)\s+)(?P<target>(?-i:eu))" + RIGHT_T,
         'EU', 0.9, 'The rules of the eu apply to every member state.',
         'The rules of the EU apply to every member state. Eu te amo, he wrote in his letter.')
    rule('caps.acr.eu_noun',
         r"(?:^|[\s(])(?P<target>(?-i:eu))\s+(?:member|members|law|laws|countries|country|regulation|regulations|citizens|citizen|commission|parliament|leaders|rules|tariffs|states|budget|directive|directives|court|council|summit|ban|sanctions|funding|data|trade)\b",
         'EU', 0.9, 'Every eu member agreed on the budget.', 'Every EU member agreed on the budget.')
    rule('caps.acr.nda_frame',
         r"(?i:\b(?:a|an|the|sign|signed|signing|under|our|your|my|this|that|mutual|standard|an?\s+signed|without|with)\s+)(?P<target>(?-i:nda))(?:\s*[,.;:!?)\]\"”’]|\s*$|\s+(?:and|or|but|for|with|to|from|on|at|in|is|are|was|were|before|after|agreement|template|form|clause|terms)\b)",
         'NDA', 0.88, 'Please sign the nda before the call.', 'Please sign the NDA before the call. Udah lama nda ketemu.')
    rule('caps.acr.pc_frame',
         r"(?i:\b(?:a|an|the|my|your|our|their|his|her|gaming|new|old|desktop|home|work|personal|windows|on|for|to|any|every|each|this|that|your own|mac or|mac and|pc and|laptop or|laptop and)\s+)(?P<target>(?-i:pc))" + RIGHT_T,
         'PC', 0.88, 'I built a gaming pc for my brother last winter.',
         'I built a gaming PC for my brother last winter. The cloud sits 0.5 pc from the core, about 3 pc across.')
    rule('caps.acr.aws_frame',
         r"(?i:\b(?:on|in|the|with|from|using|our|your|my|an|use|via|for|to|and|or|of|at|by|into)\s+)(?P<target>(?-i:aws|Aws))" + RIGHT_T,
         'AWS', 0.9, 'We host the service on aws and test it locally.',
         'We host the service on AWS and test it locally. Run aws configure, then aws s3 ls to list buckets.')
    rule('caps.acr.id_prefix',
         r"(?i:\b(?:user|student|employee|order|customer|photo|government|national|device|session|ticket|account|transaction|product|invoice|valid|unique|voter|picture|passport|job|request|row|record|post|file|team|project|issue|bug|tracking|reference|merchant|seller|buyer|patient|member|payment|booking|flight|case|claim|policy|license|licence|apple|google|login|badge|staff|company|school|college|university)\s+)(?P<target>(?-i:id))" + RIGHT_T,
         'ID', 0.9, 'Please enter your user id before you log in.',
         'Please enter your user ID before you log in. Freud wrote about the id and the ego.')
    rule('caps.acr.id_noun',
         r"(?:^|[\s(\[\"“‘])(?P<target>(?-i:id))\s+(?:card|cards|number|numbers|proof|badge|badges|document|documents|verification|check|checks|photo|scan|theft|requirements?)\b",
         'ID', 0.9, 'Bring a valid id card to the desk.',
         'Bring a valid ID card to the desk. The id and ego clashed in his theory.')
    rule('caps.acr.hr_noun',
         r"(?:^|[\s(\[\"“‘])(?P<target>(?-i:hr|Hr))\s+(?:department|team|manager|managers|policy|policies|portal|person|rep|representative|executive|head|director|business partner|generalist|round|interview|onboarding|software|system|tech|analytics|admin|assistant|office|staff|professional|professionals|complaint|complaints|issue|issues|investigation|email|emails|lead|leads|ops|operations)\b",
         'HR', 0.9, 'The hr department sent the form.', 'The HR department sent the form. It took 2 hr to finish, about 3 hr in all.')
    rule('caps.acr.hr_verb',
         r"(?i:\b(?:call|contact|email|ask|tell|inform|notify|report to|talk to|speak to|speak with|reach out to|escalate to|message|ping|loop in|check with|go to|went to|complain to|complained to|reported to|send to|forward to|cc)\s+(?:the\s+)?)(?P<target>(?-i:hr|Hr))" + END,
         'HR', 0.88, 'Please contact hr about your leave.', 'Please contact HR about your leave. The run took 2 hr, then 3 hr more.')
    rule('caps.acr.ide_noun',
         r"(?i:\b(?:an|the|your|my|our|their|his|her|any|which|each|every|preferred|favorite|favourite|modern|popular|new|good|best|same|another|different|this|that|these|those|in|inside|from|with|using|use|open|opens)\s+)(?P<target>(?-i:ide))(?:\s*[,.;:!?)\]\"”’]|\s*$|\s+(?:and|or|but|for|to|with|on|in|is|are|was|has|plugin|plugins|extension|extensions|settings|support|integration|terminal|debugger|console|setup|window|project|projects|vendor|vendors|features?|users?)\b)",
         'IDE', 0.86, 'Open the project in your ide and run the tests.',
         'Open the project in your IDE and run the tests. Beware the ides of March.')
    rule('caps.acr.atm_noun',
         r"(?:^|[\s(\[\"“‘])(?P<target>(?-i:atm))\s+(?:machine|machines|card|cards|pin|withdrawal|withdrawals|fee|fees|network|booth|kiosk|location|locations|cash|receipt|skimmer|skimmers)\b",
         'ATM', 0.9, 'The atm machine ate my card.',
         'The ATM machine ate my card. Busy atm, call you later? I am free atm.')
    rule('caps.acr.atm_frame',
         r"(?i:\b(?:an|the|nearest|any|my|a|at the|at an|find an|find the)\s+)(?P<target>(?-i:atm))(?:\s*[,.;:!?)\]\"”’]|\s*$|\s+(?:near|nearby|nearest|and|or|but|to|for|in|on|is|was|has|ran|before|after|first|again|now|today|later)\b)",
         'ATM', 0.86, 'I need to find an atm before the trip.',
         'I need to find an ATM before the trip. Are you free atm? I am busy atm.')
    rule('caps.acr.sim_card',
         r"(?:^|[\s(\[\"“‘])(?P<target>(?-i:sim))\s+(?:card|cards|slot|slots|tray|lock|unlocked|swap|swapping|number|pin|puk|activation)\b",
         'SIM', 0.9, 'Insert the sim card into the tray.', 'Insert the SIM card into the tray. The sims game is a classic.')
    rule('caps.acr.esim',
         r"(?:[A-Za-z0-9,;] )(?P<target>(?-i:esim|Esim))" + END,
         'eSIM', 0.9, 'My phone supports an esim.', 'My phone supports an eSIM.')
    rule('caps.acr.vat_noun',
         r"(?:^|[\s(\[\"“‘])(?P<target>(?-i:vat))\s+(?:number|rate|rates|registration|invoice|invoices|return|returns|refund|refunds|id|exemption|included|inclusive|exclusive|charge|charges|free|compliance|tax)\b",
         'VAT', 0.9, 'The price includes the vat rate.', 'The price includes the VAT rate. The brewer stirred the vat of wine.')
    rule('caps.acr.vat_prefix',
         r"(?i:\b(?:incl|excl|plus|inc|ex|including|excluding|inclusive of|exclusive of|before|after|with|without|pay|paid|charge|charged)\s+)(?P<target>(?-i:vat))" + END,
         'VAT', 0.88, 'The total is 40 plus vat.', 'The total is 40 plus VAT. A vat of boiling oil sat there.')
    rule('caps.acr.ip_noun',
         r"(?:^|[\s(\[\"“‘])(?P<target>(?-i:ip))\s+(?:address|addresses|range|ranges|whitelist|allowlist|block|blocks|ban|camera|cameras|rating|adapter|geolocation|lookup|tracking|spoofing|forwarding|protocol)\b",
         'IP', 0.9, 'Add the server ip address to the list.', 'Add the server IP address to the list.')
    rule('caps.acr.mac_address',
         r"(?:^|[\s(\[\"“‘])(?P<target>(?-i:mac))\s+address(?:es)?\b",
         'MAC', 0.9, 'Find the mac address of the printer.', 'Find the MAC address of the printer. Open the Mac app.')
    rule('caps.acr.qr_code',
         r"(?:^|[\s(\[\"“‘])(?P<target>(?-i:qr|Qr))\s+code(?:s)?\b",
         'QR', 0.9, 'Scan the qr code at the door.', 'Scan the QR code at the door.')
    rule('caps.acr.four_k',
         r"(?:^|[\s(\[\"“‘])(?P<target>(?-i:4k))\s+(?:video|videos|tv|tvs|monitor|monitors|display|displays|resolution|screen|screens|uhd|footage|camera|cameras|movie|movies|stream|streaming|gaming|projector|hdr)\b",
         '4K', 0.9, 'The 4k monitor arrived today.', 'The 4K monitor arrived today. I ran 4k steps this morning.')
    rule('caps.acr.covid_19',
         r"(?:^|[\s(\[\"“‘])(?P<target>(?-i:covid|Covid))-19\b",
         'COVID', 0.9, 'The covid-19 rules changed again.', 'The COVID-19 rules changed again.')
    rule('caps.acr.washington_dc',
         r"(?:Washington|washington),?\s+(?P<target>(?-i:dc|Dc|d\.c\.))(?:\s*[,.;:!?)\]\"”’]|\s*$|\s)",
         'DC', 0.9, 'The office in Washington dc opens in May.', 'The office in Washington DC opens in May.')
    rule('caps.acr.phd_degree',
         f"{LEFT}(?P<target>(?-i:phd|Phd|PHD))(?:['’]s)?(?:\\s*[,.;:!?)\\]\"”’]|\\s*$|\\s)",
         'PhD', 0.9, 'She has a phd in physics.', 'She has a PhD in physics.')
    for lower, canon in [('bsc', 'BSc'), ('msc', 'MSc'), ('mphil', 'MPhil'), ('bcom', 'BCom'), ('mcom', 'MCom')]:
        rule(f'caps.acr.{lower}',
             f"{LEFT}(?P<target>(?-i:{lower}|{lower.capitalize()}|{lower.upper()}))(?:['’]s)?(?:\\s*[,.;:!?)\\]\"”’]|\\s*$|\\s)",
             canon, 0.88, f'He finished his {lower} in 2019.', f'He finished his {canon} in 2019.')
    # Time zones after a time: "5 pm est" (the Latin "est" and the German "ist" never follow a clock time).
    for lower, canon in [('est', 'EST'), ('edt', 'EDT'), ('cst', 'CST'), ('cdt', 'CDT'), ('mst', 'MST'), ('mdt', 'MDT'),
                         ('pst', 'PST'), ('pdt', 'PDT'), ('ist', 'IST'), ('gmt', 'GMT'), ('utc', 'UTC'), ('bst', 'BST'),
                         ('cet', 'CET'), ('cest', 'CEST'), ('aest', 'AEST'), ('aedt', 'AEDT'), ('jst', 'JST'),
                         ('hkt', 'HKT'), ('sgt', 'SGT'), ('akst', 'AKST'), ('hst', 'HST')]:
        rule(f'caps.acr.tz_{lower}',
             f"\\d(?::\\d\\d)?\\s?(?i:am|pm|a\\.m\\.|p\\.m\\.)?\\s+(?P<target>(?-i:{lower}|{lower.capitalize()}))" + r"(?:\s*[,.;:!?)\]\"”’]|\s*$|\s)",
             canon, 0.9, f'The call starts at 9:30 am {lower} tomorrow.', f'The call starts at 9:30 am {canon} tomorrow.',
             'Time zones are written in capitals.')


def build():
    build_simple()
    build_ctx()
