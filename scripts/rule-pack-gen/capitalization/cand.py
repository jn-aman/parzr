"""Candidate proper nouns, brands and acronyms for the capitalization pack, by category.
Each entry is the canonical spelling; the lowercase form is what the rule looks for."""

COUNTRIES = """Poland Morocco Turkey China Jordan Chad Panama Guinea Togo Niger Nauru Tonga Samoa Kiribati Palau Vanuatu Tuvalu
Ghana Mongolia Myanmar Burma Slovakia Kazakhstan Georgia Namibia Zambia Uganda Rwanda Tanzania Senegal Somalia
Liechtenstein Luxembourg Monaco Vatican Iceland Greenland Lebanon Kuwait Oman Yemen Qatar Syria Iraq Iran Libya
Tunisia Algeria Ethiopia Eritrea Sudan Gabon Cameroon Zimbabwe Botswana Malawi Mozambique Madagascar Mauritius
Argentina Chile Peru Bolivia Paraguay Uruguay Venezuela Ecuador Colombia Guyana Suriname Honduras Guatemala Nicaragua
Panama Haiti Jamaica Cuba Bahamas Barbados Trinidad Tobago Greece Albania Serbia Croatia Bosnia Slovenia Montenegro
Bulgaria Romania Hungary Latvia Lithuania Estonia Belarus Moldova Ukraine Russia Finland Sweden Norway Denmark
Netherlands Belgium Switzerland Austria Germany Ireland Scotland Wales England Britain Portugal Spain Italy
Korea Japan Taiwan Vietnam Laos Cambodia Thailand Malaysia Singapore Indonesia Philippines Brunei Bangladesh Nepal Bhutan
Pakistan Afghanistan Uzbekistan Turkmenistan Tajikistan Kyrgyzstan Azerbaijan Armenia Israel Palestine Egypt Libya
Australia Zealand Fiji Canada Mexico America Iceland Eswatini Seychelles Maldives""".split()

REGIONS = """Oceania|Australasia|Eurasia|Antarctica|Arctic|Atlantic|Pacific|Indian Ocean|Atlantic Ocean|Pacific Ocean|Arctic Ocean|
Baltic Sea|North Sea|Red Sea|Black Sea|Persian Gulf|Gulf of Mexico|Amazon|Nile|Alps|Andes|Rockies|Rocky Mountains|Appalachians|
Mount Everest|Great Lakes|Lake Superior|Mississippi River|Grand Canyon|Niagara Falls|Great Barrier Reef|Panama Canal|Suez Canal|
Midwest|New England|Pacific Northwest|Bay Area|Deep South|Wild West|Far East|East Asia|South Asia|Central Asia|Eastern Europe|
Western Europe|Central Europe|North Africa|West Africa|East Africa|Southern Africa|Sub-Saharan Africa|North Pole|South Pole|
Gulf Coast|East Coast|West Coast|Middle America|Western Hemisphere|Northern Hemisphere|Southern Hemisphere|Indian Subcontinent|
Horn of Africa|Persian Gulf|Gulf States|Balkans|Baltics|Nordics|Benelux|Iberia|Levant|Maghreb|Punjab|Kashmir|Rajasthan|Gujarat|Kerala|
Maharashtra|Karnataka|Tamil Nadu|Uttar Pradesh|West Bengal|Andhra Pradesh|Telangana|Bihar|Odisha|Assam|Haryana|Himachal Pradesh""".replace("\n", "").split("|")

CITIES = """Birmingham Bristol Cambridge Oxford Cardiff Newcastle Sheffield Nottingham Leicester Brighton Southampton Aberdeen Inverness Cork Galway
Hamburg Cologne Stuttgart Dusseldorf Leipzig Dresden Lyon Marseille Toulouse Bordeaux Naples Turin Bologna Genoa Seville Valencia Granada Bilbao
Porto Antwerp Ghent Bruges Krakow Gdansk Vilnius Riga Tallinn Minsk Kiev Odessa Belgrade Zagreb Sofia Thessaloniki Ankara Izmir Doha Riyadh Jeddah Mecca
Medina Baghdad Damascus Amman Muscat Manama Sharjah Casablanca Marrakech Tunis Algiers Tripoli Khartoum Kampala Kigali Lusaka Harare Maputo Luanda
Dakar Abidjan Durban Pretoria Kinshasa Mogadishu Shanghai Chengdu Hangzhou Wuhan Nanjing Tianjin Chongqing Macau Osaka Kyoto Yokohama Nagoya Sapporo
Busan Incheon Pyongyang Ulaanbaatar Manila Cebu Saigon Phnom Penh Vientiane Yangon Colombo Thimphu Kabul Islamabad Rawalpindi Peshawar Quetta Multan
Faisalabad Ahmedabad Jaipur Lucknow Kanpur Nagpur Indore Bhopal Patna Surat Chandigarh Kochi Cochin Trivandrum Coimbatore Visakhapatnam Mysore Gurgaon
Gurugram Noida Ghaziabad Varanasi Amritsar Agra Ludhiana Madurai Vadodara Nashik Ranchi Guwahati Bhubaneswar Albuquerque Anchorage Boise Buffalo
Charlotte Columbus Indianapolis Jacksonville Louisville Memphis Milwaukee Oakland Omaha Orlando Phoenix Raleigh Richmond Sacramento Tampa Tucson Tulsa
Winnipeg Edmonton Halifax Havana Guadalajara Monterrey Cancun Tijuana Medellin Caracas Quito Guayaquil Montevideo Brasilia Recife Curitiba Valparaiso
Salt\ Lake\ City Kansas\ City Oklahoma\ City St\ Louis Washington\ DC Quebec\ City Ho\ Chi\ Minh\ City Dar\ es\ Salaam Kuala\ Lumpur The\ Hague""".replace("\\ ", "~").split()
CITIES = [c.replace("~", " ") for c in CITIES]

LANGS = """Dutch Polish Mandarin Welsh Gaelic Danish Icelandic Lithuanian Latvian Estonian Bulgarian Serbian Croatian Bosnian Slovak Slovenian Albanian
Armenian Georgian Azerbaijani Kazakh Uzbek Mongolian Burmese Khmer Lao Sinhala Pashto Kurdish Amharic Yoruba Igbo Hausa Zulu Xhosa Afrikaans Somali
Maltese Catalan Basque Galician Esperanto Sanskrit Hakka Hokkien Odia Assamese Maithili Konkani Sindhi Kashmiri Yiddish Cantonese Nepali""".split()

NATIONS = """Dutch Polish Danish Welsh Icelandic Afghan Albanian Algerian Angolan Armenian Bolivian Bosnian Bulgarian Cambodian Cameroonian Croatian Dominican
Ecuadorian Estonian Fijian Georgian Guatemalan Honduran Jordanian Kazakh Latvian Libyan Lithuanian Mongolian Namibian Panamanian Paraguayan Qatari
Rwandan Senegalese Serbian Slovak Slovenian Somali Sudanese Tanzanian Tunisian Ugandan Uruguayan Venezuelan Yemeni Zimbabwean Emirati Kuwaiti Omani
Bahraini Palestinian Nicaraguan Salvadoran Nepalese Burmese Laotian Scandinavian Nordic Baltic Slavic Celtic Germanic Caucasian Maori Inuit Aboriginal
Zambian Ugandan Botswanan Congolese Ivorian Malian Malagasy Mauritian Maltese Cypriot Luxembourgish Hungarian Slovene""".split()

HOLIDAYS = """Eid|Eid al-Fitr|Eid al-Adha|Eid Mubarak|Yom Kippur|Rosh Hashanah|Purim|Sukkot|Shavuot|Navratri|Dussehra|Holi|Raksha Bandhan|Janmashtami|
Ganesh Chaturthi|Onam|Pongal|Makar Sankranti|Lohri|Baisakhi|Vaisakhi|Durga Puja|Maha Shivaratri|Karva Chauth|Bhai Dooj|Gurpurab|Lent|Ash Wednesday|
Palm Sunday|Pentecost|Good Friday|Easter Sunday|Easter Monday|Christmas Eve|Christmas Day|Boxing Day|New Year's Day|New Year's Eve|Valentine's Day|
Mother's Day|Father's Day|Independence Day|Labor Day|Memorial Day|Veterans Day|Columbus Day|Black Friday|Cyber Monday|St Patrick's Day|
April Fools' Day|Groundhog Day|Chinese New Year|Lunar New Year|Deepavali|Ramzan|Muharram|Mawlid|Republic Day|Gandhi Jayanti|Juneteenth|
Hogmanay|Bonfire Night|Pancake Day|Mardi Gras|Oktoberfest|Carnival""".replace("\n", "").split("|")

RELIGION = """Jainism|Zoroastrianism|Taoism|Shinto|Sufism|Rastafarian|Bahai|Catholicism|Catholic|Catholics|Evangelical|Orthodox Christian|Buddha|Jesus|Christ|Allah|
Muhammad|Mohammed|Krishna|Shiva|Ganesha|Vishnu|Hanuman|Lakshmi|Durga|Bible|Talmud|Vedas|Bhagavad Gita|Guru Granth Sahib|Old Testament|New Testament|
Gospel|Ramayana|Mahabharata|Upanishads|Sunni|Shia|Hasidic|Rabbi|Mormonism|Scientology|Jehovah's Witnesses|Baptist|Episcopal|Lutheranism""".replace("\n", "").split("|")

BRANDS = """eBay|Xbox|PlayStation|Nintendo|Android|Windows|Linux|Ubuntu|Chrome|Safari|Firefox|OneDrive|SharePoint|Dropbox|Google Drive|Google Docs|Google Sheets|
Google Maps|Google Meet|Google Chrome|Photoshop|Illustrator|AirDrop|FaceTime|iMessage|AirTag|Apple Watch|Apple Music|Apple Pay|Siri|Alexa|Copilot|Midjourney|
Stack Overflow|Quora|Twitter|Tumblr|Discord|Twitch|Telegram|Skype|Zoom|Slack|Notion|Asana|Confluence|Airtable|Miro|Docker|Jenkins|Terraform|Ansible|Redis|
Nginx|TensorFlow|PyTorch|NumPy|Jupyter|MATLAB|Amazon|Hulu|Wi-Fi|Bluetooth|Ethernet|Python|Java|Kotlin|PHP|Golang|Node.js|React|Vue.js|Next.js|jQuery|GraphQL|
SQLite|IBM|Nvidia|AMD|Qualcomm|BMW|Mercedes|Volkswagen|Tripadvisor|Expedia|Mastercard|Amex|Google Pay|UPI|Aadhaar|IRCTC|OYO|Yahoo|Bing|DuckDuckGo|DeepSeek|
Hugging Face|LeetCode|HackerRank|Kaggle|Coursera|Udemy|Substack|Patreon|Kickstarter|Zelle|Coinbase|Binance|iPadOS|watchOS|tvOS|visionOS|ChromeOS|Unix|
VS Code|Xcode|IntelliJ|PyCharm|Homebrew|OneNote|Microsoft Teams|Microsoft Word|Microsoft Excel|MS Word|MS Excel|Google|Excel|Outlook|Teams|Gemini|Claude|
Sony|Nokia|Huawei|Xiaomi|Lenovo|OnePlus|Oppo|Motorola|Nike|Pepsi|Coca-Cola|KFC|Disney|Pixar|Lego|Nutella|Gatorade|Kleenex|Photoshop|Wikipedia""".replace("\n", "").split("|")

ACRONYMS = """NASA FBI CIA NATO UNESCO UNICEF OPEC IMF GDP UAE UK USA EU API URL URI HTML CSS JSON XML SQL PDF FAQ CEO CFO COO CTO CMO TV DVD USB GPS UI UX SEO SDK
AWS GCP NLP LLM GPT VPN DNS CPU GPU SSD HDMI OLED PC VR IoT SaaS B2B B2C KPI ROI CRM ERP CMS CDN YAML CSV JPG PNG GIF SUV VIP DIY RSVP NGO GST IRS NHS BBC CNN NBA
NFL FIFA IPL IIT IIM UPSC MBA PhD GPA GRE GMAT IELTS TOEFL JEE NEET CV PTO NDA GDPR NYC USD EUR GBP INR UTC GMT EST PST IST HIPAA ISRO""".split()
