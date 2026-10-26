"""Brands, products and platforms: the gazetteer holds the common ones (iPhone, GitHub, YouTube, ...)."""
from lib import *

FAM_SIMPLE = 'Brands and products (never ordinary words)'
FAM_CTX = 'Brands that are also ordinary words (context rules)'

# Canonical spelling. A name that is never an ordinary word needs no context.
SIMPLE = """Xbox|PlayStation|Nintendo Switch|Nintendo|Linux|Debian|CentOS|Unix|Firefox|OneDrive|SharePoint|OneNote|
Siri|Alexa|Midjourney|Quora|Tumblr|Skype|WeChat|Hulu|Bluetooth|Ethernet|Kotlin|PHP|Django|FastAPI|Laravel|Symfony|
TensorFlow|PyTorch|NumPy|SciPy|Matplotlib|MATLAB|Elasticsearch|RabbitMQ|Hadoop|Kafka|Redis|MariaDB|DynamoDB|
Firebase|Supabase|Vercel|Netlify|Heroku|Cloudflare|DigitalOcean|Jenkins|GraphQL|SQLite|
InDesign|Lightroom|FaceTime|CarPlay|MagSafe|HomePod|AirTag|AirTags|Chromecast|Chromebook|ThinkPad|
GoPro|Fitbit|Garmin|Roku|Raspberry Pi|Arduino|Etsy|AliExpress|Alibaba|Temu|Shein|Kroger|Meesho|BigBasket|Zepto|
Dunzo|BookMyShow|MakeMyTrip|Goibibo|Cleartrip|Tripadvisor|Expedia|Skyscanner|Hyundai|Suzuki|Nissan|Mazda|Subaru|Volvo|
Porsche|Ferrari|Lamborghini|Chevrolet|Lexus|Mahindra|Maruti|Volkswagen|Mercedes|Audi|Nespresso|Pepsi|Coca-Cola|Reebok|
Nike|Lego|Nutella|Gatorade|Kleenex|Tupperware|Pixar|Disney|ESPN|SoundCloud|Evernote|Airtable|Zapier|HubSpot|Mailchimp|
Zendesk|Squarespace|GoDaddy|Wix|Coursera|Udemy|Kaggle|LeetCode|HackerRank|Substack|Patreon|Kickstarter|Zelle|Coinbase|
Binance|DeepSeek|Hugging Face|Stable Diffusion|DALL-E|Grindr|OkCupid|WhatsApp Business|Google Chrome|Google Drive|
Google Docs|Google Sheets|Google Slides|Google Forms|Google Maps|Google Meet|Google Calendar|Google Photos|Google Translate|
Google Classroom|Google Analytics|Google Ads|Google Cloud|Google Play|Google Pay|Google Pixel|Google Workspace|
Google Scholar|Google Assistant|Google Earth|Google Lens|Google Keep|Google Search|Google Home|Google Nest|Google Fonts|
Google Trends|Google News|Google Colab|Google Sites|Google Groups|Google Duo|Google Wallet|Google Voice|Google Gemini|
Google Search Console|Google Tag Manager|Google My Business|Apple Watch|
Apple Music|Apple Pay|Apple TV|Apple Store|Apple ID|Apple Maps|Apple Pencil|Apple Arcade|Apple Silicon|
Apple Intelligence|Apple Vision Pro|Apple Books|Apple News|Apple Fitness|Apple Wallet|Microsoft Word|
Microsoft Teams|Microsoft Office|Microsoft Outlook|Microsoft Edge|Microsoft Azure|Microsoft Access|Microsoft Visio|
Microsoft Project|Microsoft Copilot|Windows Defender|Windows Server|Windows Update|
Amazon Prime|Amazon Web Services|Amazon Alexa|Amazon Echo|Amazon Kindle|Amazon Fire|Amazon Music|Amazon Pay|
Adobe Photoshop|Adobe Illustrator|Adobe InDesign|Adobe Premiere|Adobe Acrobat|Adobe Lightroom|Adobe After Effects|
Adobe Creative Cloud|Adobe Firefly|Adobe Express|Adobe Reader|Adobe XD|Stack Overflow|Visual Studio Code|VS Code|
Android Studio|Spring Boot|Ruby on Rails|React Native|Node.js|Vue.js|Next.js|AngularJS|Express.js|GitHub Copilot|
Samsung Galaxy|Surface Pro|Mac mini|Mac Pro|Mac Studio|MacBook Air|MacBook Pro|Disney Plus|Red Bull|
Rolls-Royce|Mercedes-Benz|Johnson & Johnson|Procter & Gamble|Goldman Sachs|JPMorgan|Morgan Stanley|Wells Fargo|
Bank of America|Barclays|HSBC|Deutsche Bank|Credit Suisse|Standard Chartered|Berkshire Hathaway|Warner Bros|
Universal Studios|Sony|Panasonic|Huawei|Xiaomi|Lenovo|OnePlus|Motorola|Nokia|Qualcomm|Nvidia|Cisco""".replace('\n', '').split('|')

SIMPLE = [x for x in SIMPLE if x not in {'Google Search Console', 'Land Rover', 'Photoshop', 'Acrobat'}]

# Names whose canonical form starts with a lowercase letter: never at the start of a sentence (the engine would turn
# the capital back into "EBay"), so they need a word or comma before them.
LOWER_FIRST = ['eBay', 'iPadOS', 'watchOS', 'tvOS', 'visionOS', 'iMessage', 'iMovie', 'iPhoto', 'iWork', 'eBooks',
               'macOS', 'iOS', 'jQuery']
# (macOS, iOS, jQuery... are in the gazetteer or handled at sentence start; the mid-sentence form still needs a rule
# only for the ones missing there.)

MULTI_OK = {'Nintendo Switch', 'Raspberry Pi', 'Hugging Face', 'Stable Diffusion', 'Mac mini', 'Mac Pro', 'Mac Studio',
            'MacBook Air', 'MacBook Pro', 'Disney Plus', 'Red Bull', 'Land Rover', 'Spring Boot', 'Ruby on Rails',
            'React Native', 'Samsung Galaxy', 'Surface Pro', 'Visual Studio Code', 'Android Studio'}

# Words that exist in the gazetteer as a first word ("Samsung galaxy" stays half-fixed): the engine fixes the first word
# and the next pass fixes the rest.


EXTRA = {  # other wrong spellings that go to the same canonical form
    'Node.js': ['nodejs', 'Nodejs', 'node js', 'Node js'],
    'Vue.js': ['vuejs', 'Vuejs', 'vue js', 'Vue js'],
    'Next.js': ['nextjs', 'Nextjs', 'next js', 'Next js'],
    'Express.js': ['expressjs', 'Expressjs'],
    'VS Code': ['vscode', 'Vscode', 'vs code', 'Vs Code', 'VSCode'],
    'Visual Studio Code': [],
    'DALL-E': ['dall-e', 'Dall-e', 'dalle', 'Dalle', 'dall e', 'Dall-E', 'DALLE'],
    'TensorFlow': ['Tensorflow'],
    'GitHub Copilot': ['github copilot', 'Github copilot', 'GitHub copilot', 'Github Copilot'],
    'WhatsApp Business': ['whatsapp business', 'Whatsapp business', 'WhatsApp business', 'Whatsapp Business'],
}


# Developer tools that are also commands or modules: capitalized only after a prose word ("use django") and before
# punctuation, a function word or a plain noun ("redis server"), so "heroku login", "import numpy as np" and
# "redis-cli" stay as typed.
DEV_FRAMED = {'Django', 'FastAPI', 'Laravel', 'Symfony', 'TensorFlow', 'PyTorch', 'NumPy', 'SciPy', 'Matplotlib',
              'Elasticsearch', 'RabbitMQ', 'Hadoop', 'Kafka', 'Redis', 'MariaDB', 'DynamoDB', 'Firebase', 'Supabase',
              'Vercel', 'Netlify', 'Heroku', 'Cloudflare', 'DigitalOcean', 'Jenkins', 'SQLite', 'MATLAB', 'Kotlin',
              'PHP', 'GraphQL', 'Jupyter'}
DEV_FOLLOW = {'Firefox', 'Linux', 'Debian', 'CentOS', 'Unix'}


def simple_name(canon):
    lower = canon.lower()
    if lower in GAZ:
        return
    left, right = LEFT, RIGHT_T
    if canon in DEV_FRAMED:
        left, right = FRAME_DEV, RIGHT_DEV
    elif canon in DEV_FOLLOW:
        right = RIGHT_DEV
    if canon[:1].islower():
        left = LEFT_MID
    if ' ' in canon:
        alts = variants(canon)
    else:
        alts = [lower]
        cap = canon[:1].upper() + canon[1:].lower()
        if cap != canon and cap != lower and cap not in alts:
            alts.append(cap)
    alts = list(dict.fromkeys(alts + EXTRA.get(canon, [])))
    alts = [a for a in alts if a != canon]
    body = '|'.join(esc(a) for a in alts)
    pat = f'{left}(?P<target>(?-i:{body})){right}'
    wrong = shown_form(canon) if ' ' in canon else lower
    if wrong not in alts:
        wrong = alts[0]
    if canon.endswith('.js'):
        alts = [x for x in alts if not x.endswith('.js')]
        if not alts:
            return
        wrong = alts[0]
        body = '|'.join(esc(a_) for a_ in alts)
        pat = f'{left}(?P<target>(?-i:{body})){right}'
    pos = f'I saw it on {wrong} yesterday.'
    neg = f'I saw it on {canon} yesterday. ' + neg_noise(lower)
    if canon in DEV_FRAMED:
        pos = f'We built the site with {wrong} yesterday.'
        neg = (f'We built the site with {canon} yesterday. ' + neg_noise(lower) +
               f' Run {lower} login, then import {lower} as x, and open {lower}-cli.')
    emit(f'caps.brand.{slug(canon)}', pat, canon, 'Capitalization', 0.9,
         'Brand and product names keep their own capitalization.', pos, neg, FAM_SIMPLE)


def build_simple():
    for c in dict.fromkeys(SIMPLE):
        simple_name(c)
    for c in dict.fromkeys(LOWER_FIRST):
        simple_name(c)


def build_ctx():
    FN = ('and|or|but|for|with|to|from|on|at|in|inside|into|is|are|was|were|has|have|had|will|would|can|could|may|might|'
          'if|when|while|then|once|since|because|so|as|by|about|instead|again|first|too|also|now|today|tomorrow|tonight|'
          'later|please|anyway|before|after|until|that|which|who|last|next|this|yesterday|soon|earlier|just|only|every|'
          'each|over|than|via|per|all|both|still|already|always|never|really')

    def rule(rid, pat, repl, conf, pos, neg, reason='Brand and product names keep their own capitalization.'):
        # a frame that makes the word unambiguous may be followed by any function word
        pat = pat.replace(r"|\s*$|\s+(?:", r"|\s*$|\s+(?:" + FN + "|")
        emit(rid, pat, repl, 'Capitalization', conf, reason, pos, neg, FAM_CTX)

    END = RIGHT_T

    # --- Google ---------------------------------------------------------------------------------------------
    rule('caps.brand.google_frame',
         r"(?i:\b(?:on|via|from|at|in|by|through|with|ask|check|open|search|searched|searching|use|using|used)\s+)(?P<target>(?-i:google))" + END,
         'Google', 0.88, 'We searched on google for the answer.',
         'We searched on Google for the answer. Please google it before asking, and I googled the term.')
    rule('caps.brand.google_possessive',
         r"(?:^|[\s(\[\"“‘])(?P<target>(?-i:google))['’]s\s+(?:search|ceo|engineers|engineer|servers|cloud|ads|algorithm|assistant|pixel|chrome|android|maps|gemini|new|latest|data|office|offices|headquarters|stock|shares|ai|team|policy|products|product)\b",
         'Google', 0.88, "We read that google's new search feature is live.",
         "We read that Google's new search feature is live. I google things daily and googled it twice.")
    # --- Apple ----------------------------------------------------------------------------------------------
    rule('caps.brand.apple_employer',
         r"(?i:\b(?:works|work|worked|working|joined|joins|joining|hired by|employed by|engineer at|engineers at|intern at|interned at|internship at|interview at|interviewed at|job at|jobs at|career at|careers at|leave|left|leaving|quit|quitting|fired from|laid off from)\s+(?:at\s+)?)(?P<target>(?-i:apple))" + END,
         'Apple', 0.88, 'She works at apple in Cupertino.',
         'She works at Apple in Cupertino. We picked an apple at the orchard, and the apple fell.')
    rule('caps.brand.apple_possessive',
         r"(?:^|[\s(\[\"“‘])(?P<target>(?-i:apple))['’]s\s+(?:iphone|ipad|macbook|mac|app store|ios|macos|watch|siri|airpods|vision pro|latest|new|ceo|stock|shares|event|keynote|silicon|chip|chips|store|stores|services|ecosystem|devices)\b",
         'Apple', 0.88, "Reviewers say apple's new iphone has a better camera.",
         "Reviewers say Apple's new iPhone has a better camera. The apple's skin was bright red and the apple's core was brown.")

    # --- Microsoft products (the gazetteer fixes "microsoft") ------------------------------------------------
    # --- Amazon ---------------------------------------------------------------------------------------------
    rule('caps.brand.amazon_frame',
         r"(?i:\b(?:on|from|at|via|through|buy|bought|buying|order|ordered|ordering|shop|shopping|shopped|sell|selling|sold|ship|shipped|shipping|returned|return|returns|returning|search|searched|check|checked|sells|sold by|shipped by|delivered by|fulfilled by)\s+)(?P<target>(?-i:amazon))" + END,
         'Amazon', 0.86, 'I bought the charger on amazon last week.',
         'I bought the charger on Amazon last week. We sailed up the Amazon, and the amazon warriors of myth fought.')
    rule('caps.brand.amazon_product',
         r"(?:^|[\s(\[\"“‘])(?P<target>(?-i:amazon))\s+(?:prime|alexa|echo|kindle|fire|music|pay|web services|aws|seller|sellers|fba|marketplace|warehouse|warehouses|delivery|driver|drivers|account|gift card|review|reviews|listing|listings|basics|studios|video|photos|rekognition|bedrock|sagemaker)\b",
         'Amazon', 0.88, 'Her amazon seller account renews in May.',
         'Her Amazon seller account renews in May. The Amazon river basin floods.')

    # --- Windows / Android / Chrome / Safari / Excel / Outlook / Teams / Slack / Zoom / Notion ----------------
    rule('caps.brand.windows_version',
         r"(?:^|[\s(\[\"“‘])(?P<target>(?-i:windows))\s+(?:7|8|8\.1|10|11|xp|vista|explorer|registry|terminal|subsystem|store|phone|insider|hello|11 home|10 home|pro|enterprise)(?:\s*[,.;:!?)\]\"”’]|\s*$|\s+(?:and|or|but|is|was|has|users?|laptop|pc|machine|computer|update|installation|install|iso|home|pro|version|release|setup|license|key|support|supports|only|on|for|with|in|to)\b)",
         'Windows', 0.9, 'The app runs on windows 11 and macOS.',
         'The app runs on Windows 11 and macOS. We cleaned the windows 10 times this month, so clean the windows twice.')
    rule('caps.brand.windows_pair',
         r"(?i:\b(?:mac|macos|linux|android|ios|ubuntu|chromeos)(?:\s*,\s*|\s+and\s+|\s+or\s+|\s*/\s*)|\b(?:on|for|in|under)\s+)(?P<target>(?-i:windows))(?:\s*[,.;:!?)\]\"”’/]|\s*$|\s+(?:and|or)\s+(?i:mac|macos|linux|android|ios|ubuntu)\b)",
         'Windows', 0.88, 'The tool works on mac and windows.',
         'The tool works on Mac and Windows. The light came in through the windows. She wiped the windows and closed the windows.')
    rule('caps.brand.android_frame',
         r"(?i:\b(?:on|for|to|from|between|under|with|and|or)\s+)(?P<target>(?-i:android))(?:\s*[,.;:!?)\]\"”’]|\s*$|\s+(?:and|or|phones?|devices?|apps?|users?|tablets?|versions?|only|os|first|too|as well|is|has|does|support|supports|studio|sdk|auto|tv|wear|emulator)\b)",
         'Android', 0.88, 'The app is available for ios and android.',
         'The app is available for iOS and Android. In the film, an android that looks like a man could not feel pain.',
         )
    rule('caps.brand.chrome_use',
         r"(?i:\b(?:open|opened|opening|launch|launched|launching|restart|restarted|restarting|quit|quitting|reopen|reopened|update|updated|updating|install|installed|installing|uninstall|uninstalled|use|used|using|try|tried|trying|switch to|switched to|switching to|clear|cleared|clearing)\s+(?:the\s+)?)(?P<target>(?-i:chrome))(?:\s*[,.;:!?)\]\"”’]|\s*$|\s+(?:and|or|but|browser|extension|extensions|tab|tabs|devtools|canary|os|again|first|instead|to|for|with|on)\b)",
         'Chrome', 0.88, 'Please reopen chrome and sign in again.',
         'Please reopen Chrome and sign in again. The car had a bumper of bright chrome and chrome wheels.')
    rule('caps.brand.chrome_nouns',
         r"(?:^|[\s(\[\"“‘])(?P<target>(?-i:chrome))\s+(?:browser|extension|extensions|devtools|dev tools|canary|web store|bookmarks|profile|cache|history|tab|tabs|update|settings|flags|os)\b",
         'Chrome', 0.9, 'Open the chrome extension page.',
         'Open the Chrome extension page. The bumper had chrome trim.')
    rule('caps.brand.safari_use',
         r"(?i:\b(?:open|opened|opening|launch|launched|quit|restart|restarted|reopen|reopened|close|closed|use|using|used|switch to|switched to|try|tried|trying)\s+(?:the\s+)?)(?P<target>(?-i:safari))(?:\s*[,.;:!?)\]\"”’]|\s*$|\s+(?:and|or|but|browser|extension|extensions|tab|tabs|again|first|instead|to|for|with|on)\b)",
         'Safari', 0.88, 'Try opening safari in private mode.',
         'Try opening Safari in private mode. They went on safari in Kenya and booked a safari lodge.')
    rule('caps.brand.safari_nouns',
         r"(?:^|[\s(\[\"“‘])(?P<target>(?-i:safari))\s+(?:browser|extension|extensions|reader|bookmarks|settings|history|private|tab|tabs|update|preferences|web inspector|technology preview)\b",
         'Safari', 0.9, 'The safari browser blocked the cookie.', 'The Safari browser blocked the cookie. The safari park was full.')
    rule('caps.brand.excel_frame',
         r"(?i:\b(?:in|on|from|into|using|use|uses|used|open|opened|opening|export|exported|exporting|import|imported|importing|convert|converted|converting|save|saved|saving|an|the|my|your|our|this|that|a|microsoft)\s+)(?P<target>(?-i:excel))(?:\s*[,.;:!?)\]\"”’]|\s*$|\s+(?:and|or|but|sheet|sheets|file|files|spreadsheet|spreadsheets|document|formula|formulas|macro|macros|table|tables|chart|charts|workbook|workbooks|template|templates|add-in|add-ins|pivot|expert|skills|training|course|tutorial|version|report|reports|users?|to|for|with)\b)",
         'Excel', 0.88, 'I keep the budget in an excel sheet.',
         'I keep the budget in an Excel sheet. Students excel at math, and you can excel in any field.')
    rule('caps.brand.outlook_use',
         r"(?i:\b(?:open|opened|opening|launch|launched|restart|restarted|reopen|reopened|close|closed|quit|check|checked|checking|sync|syncs|synced|syncing|install|installed|update|updated|use|using)\s+(?:the\s+)?)(?P<target>(?-i:outlook))(?:\s*[,.;:!?)\]\"”’]|\s*$|\s+(?:and|or|but|again|first|instead|to|for|with|on)\b)",
         'Outlook', 0.86, 'Please restart outlook and try again.',
         'Please restart Outlook and try again. The outlook for sales is positive, and her outlook on life is bright.')
    rule('caps.brand.outlook_nouns',
         r"(?:^|[\s(\[\"“‘])(?P<target>(?-i:outlook))\s+(?:email|emails|calendar|inbox|app|account|invite|invites|rule|rules|signature|web|desktop|mail|add-in|add-ins|profile|folder|folders|contacts|meeting|meetings)\b",
         'Outlook', 0.88, 'Add the outlook calendar invite to the folder.',
         'Add the Outlook calendar invite to the folder. The outlook for sales is positive.')
    rule('caps.brand.teams_me',
         r"(?i:\b(?:ping|message|messaged|text|dm|call|called|reach|find|add|invite|catch|meet|contact)\s+(?:me|us|you|him|her|them)\s+(?:on|via|over|through)\s+)(?P<target>(?-i:teams))" + END,
         'Teams', 0.86, 'Ping me on teams if you need anything.',
         'Ping me on Teams if you need anything. The two teams played well, and she works across teams.')
    rule('caps.brand.slack_frame',
         r"(?i:\b(?:on|via|over|through)\s+)(?P<target>(?-i:slack))" + END,
         'Slack', 0.86, 'Send me the file on slack.',
         'Send me the file on Slack. Cut me some slack, and leave some slack in the rope.')
    rule('caps.brand.slack_pronoun',
         r"(?i:\b(?:ping|message|messaged|text|dm|reach|find|add|invite|catch|contact)\s+(?:me|us|you|him|her|them)\s+(?:in)\s+)(?P<target>(?-i:slack))" + END,
         'Slack', 0.86, 'Ping me in slack if it fails.',
         'Ping me in Slack if it fails. There is too much slack in the rope.')
    rule('caps.brand.slack_nouns',
         r"(?:^|[\s(\[\"“‘])(?P<target>(?-i:slack))\s+(?:channel|channels|message|messages|thread|threads|workspace|app|bot|huddle|dm|dms|notification|notifications|integration|status|emoji|invite)\b",
         'Slack', 0.88, 'Post it in the slack channel.',
         'Post it in the Slack channel. There was too much slack in the line.')
    rule('caps.brand.zoom_frame',
         r"(?i:\b(?:on|via|over|through|using|use|join|joined|joining|open|opened|start|started|starting|host|hosted|hosting)\s+(?:a\s+|the\s+|our\s+|my\s+|your\s+)?)(?P<target>(?-i:zoom))(?:\s*[,.;:!?)\]\"”’]|\s*$|\s+(?:call|calls|meeting|meetings|link|links|room|rooms|webinar|webinars|invite|invites|id|account|session|sessions|background|recording|recordings|chat|bombing|fatigue|and|or|but|today|tomorrow|tonight|later|instead|tomorrow|at)\b)",
         'Zoom', 0.86, 'Let us talk on zoom tomorrow.',
         'Let us talk on Zoom tomorrow. Use the zoom lens, then zoom in on the map.')
    rule('caps.brand.zoom_nouns',
         r"(?:^|[\s(\[\"“‘])(?P<target>(?-i:zoom))\s+(?:call|calls|meeting|meetings|link|links|room|webinar|webinars|invite|invites|id|account|session|sessions|background|recording|recordings|bombing|fatigue)\b",
         'Zoom', 0.88, 'Send me the zoom link.', 'Send me the Zoom link. The zoom lens and the zoom level are fine.')
    rule('caps.brand.notion_nouns',
         r"(?:^|[\s(\[\"“‘])(?P<target>(?-i:notion))\s+(?:page|pages|doc|docs|database|databases|workspace|template|templates|board|boards|app|ai|calendar|account|link|links|block|blocks|integration)\b",
         'Notion', 0.88, 'I keep my plans in a notion page.',
         'I keep my plans in a Notion page. The notion that plans fail is wrong.')
    rule('caps.brand.notion_frame',
         r"(?i:\b(?:in|into|to|from|on)\s+)(?P<target>(?-i:notion))(?:\s*[,.;:!?)\]\"”’]|\s*$|\s+(?:and|or|but|too|instead|as well|for|with)\b)",
         'Notion', 0.84, 'I keep my notes in notion.',
         'I keep my notes in Notion. She holds a firm notion of right and wrong.')
    rule('caps.brand.python_use',
         r"(?i:\b(?:learn|learns|learning|learned|use|uses|using|used|know|knows|knew|write|writes|writing|wrote|written|code|codes|coding|coded|program|programs|programming|teach|teaches|teaching|taught|study|studies|studying|studied|in|with|via|from|port|ported|porting|rewrite|rewrote|rewriting|rewritten|migrate|migrated|migrating|switch to|switched to|switching to|install|installed|installing|upgrade|upgraded|upgrading|run|runs|running|ran)\s+(?:in\s+|with\s+|the\s+)?)(?P<target>(?-i:python))(?:\s*[,.;:!?)\]\"”’]|\s*$|\s+(?:and|or|but|code|script|scripts|package|packages|library|libraries|module|modules|program|programs|developer|developers|programmer|programmers|dev|file|files|function|functions|class|classes|version|interpreter|environment|notebook|api|3|2|3\.\d+|for|to|on|with|instead|first|too|as well)\b)",
         'Python', 0.88, 'She wrote the script in python last week.',
         'She wrote the script in Python last week. The python swallowed a rabbit, and a python is a large snake.')
    rule('caps.brand.python_nouns',
         r"(?:^|[\s(\[\"“‘])(?P<target>(?-i:python))\s+(?:script|scripts|package|packages|library|libraries|module|modules|developer|developers|programmer|programmers|code|file|files|function|functions|class|classes|interpreter|virtualenv|environment|notebook|3|2|3\.\d+|programming|program|tutorial|course|api|sdk|bindings|wheel|pip)\b",
         'Python', 0.9, 'The python script crashed on startup.',
         'The Python script crashed on startup. The python swallowed a rabbit and the pet python hid.')
    rule('caps.brand.java_use',
         r"(?i:\b(?:learn|learns|learning|learned|know|knows|knew|write|writes|writing|wrote|written|code|coding|program|programming|teach|taught|study|studying|studied|rewrite|rewrote|port|ported|migrate|migrated|switch to|switched to|in|with)\s+(?:in\s+|with\s+)?)(?P<target>(?-i:java))(?:\s*[,.;:!?)\]\"”’]|\s*$|\s+(?:and|or|but|code|class|classes|developer|developers|programmer|programmers|file|files|library|libraries|application|applications|app|apps|project|projects|package|packages|method|methods|interface|streams?|8|11|17|21|for|to|on|instead|first|too|as well)\b)",
         'Java', 0.86, 'He writes the backend in java and python.',
         'He writes the backend in Java and Python. She sipped java at the cafe, and flew to the island of java.')
    rule('caps.brand.java_nouns',
         r"(?:^|[\s(\[\"“‘])(?P<target>(?-i:java))\s+(?:code|class|classes|developer|developers|programmer|programmers|file|files|library|libraries|virtual machine|jvm|jdk|jre|runtime|spring|8|11|17|21|bytecode|application|applications|project|projects|package|packages|stream|streams|interface|interfaces|programming|backend|compiler|garbage collector)\b",
         'Java', 0.88, 'The java developer fixed the bug.', 'The Java developer fixed the bug. A cup of java steamed on the desk.')
    rule('caps.brand.rust_nouns',
         r"(?:^|[\s(\[\"“‘])(?P<target>(?-i:rust))\s+(?:code|crate|crates|compiler|programming|programmer|developer|developers|borrow checker|cargo|library|libraries|backend|project|projects|toolchain|std|trait|traits|macro|macros|ownership)\b",
         'Rust', 0.88, 'The rust compiler caught the bug.', 'The Rust compiler caught the bug. Rust had eaten the hinge, and rust on the bike was bad.')
    rule('caps.brand.swift_nouns',
         r"(?:^|[\s(\[\"“‘])(?P<target>(?-i:swift))\s+(?:code|package|packages|developer|developers|programmer|compiler|concurrency|playgrounds?|ui|data|charts|testing|macros|programming|project|projects|library|libraries|language|6|5|5\.\d+)\b",
         'Swift', 0.88, 'The swift compiler warned about the unused variable.',
         'The Swift compiler warned about the unused variable. She gave a swift reply and a swift kick.')
    rule('caps.brand.ruby_nouns',
         r"(?:^|[\s(\[\"“‘])(?P<target>(?-i:ruby))\s+(?:gem|gems|developer|developers|programmer|programmers|script|scripts|code|on rails|version|interpreter|bundler|file|files|project|projects|library|libraries|3|3\.\d+)\b",
         'Ruby', 0.88, 'We deploy the ruby gem each Friday.',
         'We deploy the Ruby gem each Friday. She wore a ruby ring and a ruby necklace.')
    rule('caps.brand.twitter_frame',
         r"(?i:\b(?:on|via|from)\s+)(?P<target>(?-i:twitter))(?:\s*[,.;:!?)\]\"”’]|\s*$|\s+(?:and|or|but|for|account|handle|thread|feed|post|posts|user|users|bio|follower|followers|api|link|bot|ads|blue|today|yesterday|too|as well|is|was|has)\b)",
         'Twitter', 0.88, 'The news broke on twitter first.',
         'The news broke on Twitter first. The birds began to twitter at dawn.')
    rule('caps.brand.discord_nouns',
         r"(?:^|[\s(\[\"“‘])(?P<target>(?-i:discord))\s+(?:server|servers|channel|channels|bot|bots|link|invite|community|message|messages|dm|dms|call|calls|group|chat|role|roles|mod|mods|moderator|moderators|nitro|username)\b",
         'Discord', 0.9, 'Join the discord server tonight.', 'Join the Discord server tonight. The remark sowed discord in the ranks.')
    rule('caps.brand.discord_on',
         r"(?i:\b(?:on|via|over)\s+)(?P<target>(?-i:discord))" + END,
         'Discord', 0.86, 'Message me on discord later.', 'Message me on Discord later. Their quarrel sowed discord among the staff.')
    rule('caps.brand.twitch_frame',
         r"(?i:\b(?:on|via|from)\s+)(?P<target>(?-i:twitch))(?:\s*[,.;:!?)\]\"”’]|\s*$|\s+(?:and|or|but|stream|streams|streamer|streamers|chat|channel|prime|emote|emotes|clip|clips|drops|account|too|as well)\b)",
         'Twitch', 0.88, 'She streams games on twitch every night.',
         'She streams games on Twitch every night. A twitch of his eye gave him away.')
    rule('caps.brand.telegram_nouns',
         r"(?:^|[\s(\[\"“‘])(?P<target>(?-i:telegram))\s+(?:group|groups|channel|channels|bot|bots|app|link|chat|username|handle|admin|account|number|desktop|web)\b",
         'Telegram', 0.88, 'Join our telegram group for updates.',
         'Join our Telegram group for updates. The telegram arrived by horse in 1890.')
    rule('caps.brand.telegram_me',
         r"(?i:\b(?:ping|message|messaged|text|dm|reach|find|add|catch|contact|join|follow)\s+(?:me|us|you|him|her|them)\s+(?:on|via)\s+)(?P<target>(?-i:telegram))" + END,
         'Telegram', 0.86, 'Message me on telegram.', 'Message me on Telegram. They sent a telegram to the king.')
    rule('caps.brand.dropbox_frame',
         r"(?i:\b(?:in|on|to|from|via|through|using|use|upload to|uploaded to|shared via|saved to|save to|stored in|store in|put it in|put them in|share via|share on)\s+)(?P<target>(?-i:dropbox))(?:\s*[,.;:!?)\]\"”’]|\s*$|\s+(?:and|or|but|link|folder|account|file|files|paper|business|app|sync|storage|too|as well)\b)",
         'Dropbox', 0.86, 'I saved the draft to dropbox.',
         'I saved the draft to Dropbox. Drop it in the library dropbox before closing.')
    rule('caps.brand.photoshop_frame',
         r"(?i:\b(?:in|using|use|uses|used|open|opened|opening|launch|learn|learning|learned|know|knows|with|expert in|skilled in|proficient in|good at|trained in|fluent in|edited in|made in|designed in|created in|done in|drawn in)\s+)(?P<target>(?-i:photoshop))(?:\s*[,.;:!?)\]\"”’]|\s*$|\s+(?:and|or|but|cc|cs6|file|files|layer|layers|tutorial|skills|template|action|actions|brush|brushes|psd|for|to|too|as well|2\d\d\d)\b)",
         'Photoshop', 0.88, 'She made the poster in photoshop.',
         'She made the poster in Photoshop. They like to photoshop their vacation photos.')
    rule('caps.brand.airdrop_frame',
         r"(?i:\b(?:via|using|use|with|over|through)\s+)(?P<target>(?-i:airdrop))(?:\s*[,.;:!?)\]\"”’]|\s*$|\s+(?:and|or|but|to|from|instead|too|as well)\b)",
         'AirDrop', 0.86, 'Send the photos via airdrop.',
         'Send the photos via AirDrop. The crypto project plans an airdrop of tokens next week.')
    rule('caps.brand.airdrop_me',
         r"(?:^|[\s(\[\"“‘])(?P<target>(?-i:airdrop))\s+(?:me|us|him|her|them)\b",
         'AirDrop', 0.86, 'Please airdrop me the file.', 'Please AirDrop me the file.')
    rule('caps.brand.kindle_frame',
         r"(?i:\b(?:my|your|his|her|our|their|new|a|an|the|on|to|from)\s+(?:amazon\s+)?)(?P<target>(?-i:kindle))(?:\s*[,.;:!?)\]\"”’]|\s*$|\s+(?:and|or|but|app|book|books|device|reader|paperwhite|unlimited|store|edition|fire|library|is|was|has|too|as well)\b)",
         'Kindle', 0.86, 'I read the book on my kindle.',
         'I read the book on my Kindle. Candles kindle hope, and dry twigs kindle fast.')
    rule('caps.brand.tinder_frame',
         r"(?i:\b(?:on|via|from)\s+)(?P<target>(?-i:tinder))(?:\s*[,.;:!?)\]\"”’]|\s*$|\s+(?:and|or|but|profile|match|matches|date|dates|swipe|swipes|too|as well)\b)",
         'Tinder', 0.88, 'They met on tinder last year.',
         'They met on Tinder last year. The dry tinder caught fire at once.')
    rule('caps.brand.azure_frame',
         r"(?i:\b(?:on|in|to|from|via|using|use|deploy to|deployed to|host on|hosted on|run on|running on)\s+)(?P<target>(?-i:azure))(?:\s*[,.;:!?)\]\"”’]|\s*$|\s+(?:and|or|but|devops|portal|ad|functions|vm|vms|blob|sql|cloud|active directory|app service|kubernetes|openai|storage|key vault|data factory|too|as well)\b)",
         'Azure', 0.88, 'We deploy the service on azure.', 'We deploy the service on Azure. The azure sky stretched above the hills.')
    rule('caps.brand.oracle_nouns',
         r"(?:^|[\s(\[\"“‘])(?P<target>(?-i:oracle))\s+(?:cloud|database|corporation|netsuite|linux|java|erp|fusion|apex|developer|dba|jdk)\b",
         'Oracle', 0.88, 'The oracle database holds the billing data.',
         'The Oracle database holds the billing data. The oracle at Delphi spoke in riddles.')
    rule('caps.brand.docker_nouns',
         r"(?:^|[\s(\[\"“‘])(?P<target>(?-i:docker))\s+(?:desktop|hub|swarm|engine|container|containers|image|images|compose file|registry)\b",
         'Docker', 0.86, 'Pull the docker image before the deploy.',
         'Pull the Docker image before the deploy. Run docker compose up to start, then docker ps to check.')
    rule('caps.brand.intel_nouns',
         r"(?:^|[\s(\[\"“‘])(?P<target>(?-i:intel))\s+(?:core|xeon|chip|chips|cpu|cpus|processor|processors|mac|macs|i[3579]|arc|graphics|gpu|motherboard|laptop|laptops)\b",
         'Intel', 0.88, 'The laptop has an intel core processor.',
         'The laptop has an Intel core processor. The agency gathered intel on the plan.')
    rule('caps.brand.dell_nouns',
         r"(?:^|[\s(\[\"“‘])(?P<target>(?-i:dell))\s+(?:laptop|laptops|xps|inspiron|latitude|monitor|monitors|server|servers|pc|computer|computers|technologies|alienware)\b",
         'Dell', 0.88, 'My dell laptop needs a new battery.',
         'My Dell laptop needs a new battery. We walked down the dell to the stream.')
    rule('caps.brand.facebook_page',
         r"(?i:\b(?:on|via|from|through)\s+)(?P<target>(?-i:meta))(?:\s*[,.;:!?)\]\"”’]|\s*$|\s+(?:ads|platforms|ai|quest|verified|business suite|and|or)\b)",
         'Meta', 0.84, 'We ran the campaign on meta ads.',
         'We ran the campaign on Meta ads. The study is a meta analysis of meta data.')
    rule('caps.brand.edge_browser',
         r"(?i:\b(?:open|opened|launch|launched|use|using|used|try|tried|switch to|switched to|in|on)\s+(?:microsoft\s+)?)(?P<target>(?-i:edge))\s+(?:browser|extension|extensions|tab|tabs|devtools|canary|dev|beta|stable)\b",
         'Edge', 0.86, 'The page broke in edge browser only.',
         'The page broke in Edge browser only. We stood on the edge of the cliff.')
    rule('caps.brand.stripe_frame',
         r"(?i:\b(?:via|using|through|with|on|to|from)\s+)(?P<target>(?-i:stripe))(?:\s+(?:payments?|checkout|account|dashboard|api|webhook|webhooks|connect|fees?|invoice|invoices|integration|customer|customers|sdk|keys?))\b",
         'Stripe', 0.88, 'Customers pay via stripe checkout.',
         'Customers pay via Stripe checkout. The zebra has a black stripe.')


def build():
    build_simple()
    build_ctx()
    # Wi-Fi: a spelling preference, not an error, so a lower-confidence Style suggestion
    alts = ['wifi', 'Wifi', 'wi-fi', 'Wi-fi', 'WiFi', 'WIFI', 'wi-Fi']
    emit('caps.brand.wi_fi', f"{LEFT}(?P<target>(?-i:wifi|Wifi|wi-fi|Wi-fi|WiFi))" + RIGHT_T, 'Wi-Fi', 'Style', 0.8,
         'The usual spelling of the wireless standard is “Wi-Fi”.', 'The hotel has free wifi in every room.',
         'The hotel has free Wi-Fi in every room. ' + neg_noise('wifi'), FAM_SIMPLE)
