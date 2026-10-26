"""Places, languages, nationalities and peoples that the gazetteer (proper-nouns.txt) does not hold."""
from lib import *

# --- words that are never ordinary lowercase words: one rule each, no context needed -----------------------------

COUNTRIES = """Poland|Togo|Nauru|Tonga|Samoa|Kiribati|Palau|Vanuatu|Tuvalu|Burma|Greenland|Vatican|Britain|Korea|America|
Trinidad|Tobago|Bermuda|Gibraltar|Ivory Coast|Cape Verde|Burkina Faso|Central African Republic|Timor-Leste|East Timor|
Solomon Islands|Marshall Islands|Micronesia|Saint Lucia|San Marino|Faroe Islands|Isle of Man|Macedonia|Yugoslavia|
Czechoslovakia|Soviet Union|Western Sahara|Northern Ireland|Equatorial Guinea|Guinea-Bissau|Sao Tome|Comoros|Macau|
Slovakia|Vatican City|South Ossetia|Abkhazia|Transnistria|Nagorno-Karabakh|Tibet|Catalonia|Brittany|Normandy|Bavaria|
Tuscany|Sicily|Sardinia|Crete|Cyprus|Malta|Corsica|Andalusia|Galicia|Flanders|Wallonia|Lombardy|Provence|Transylvania""".replace('\n', '').split('|')

REGIONS = """Oceania|Australasia|Eurasia|Pacific Ocean|Atlantic Ocean|Indian Ocean|Arctic Ocean|Southern Ocean|Arctic Circle|
Antarctic Circle|Baltic Sea|North Sea|Red Sea|Black Sea|Dead Sea|Caspian Sea|Aegean Sea|Adriatic Sea|Irish Sea|Arabian Sea|
Bay of Bengal|South China Sea|Sea of Japan|Persian Gulf|Gulf of Mexico|Strait of Hormuz|English Channel|Nile|Himalaya|
Alps|Andes|Rocky Mountains|Appalachian Mountains|Mount Everest|Great Lakes|Lake Superior|Lake Victoria|Lake Michigan|
Mississippi River|Ganges|Yangtze|Grand Canyon|Niagara Falls|Great Barrier Reef|Panama Canal|Suez Canal|Midwest|
New England|Pacific Northwest|Bay Area|Deep South|Wild West|Far East|East Asia|South Asia|Central Asia|Western Asia|
Eastern Europe|Western Europe|Central Europe|Northern Europe|Southern Europe|North Africa|West Africa|East Africa|
Southern Africa|Central Africa|Sub-Saharan Africa|Middle America|Indian Subcontinent|Horn of Africa|Gulf States|Baltics|Nordics|Benelux|
Iberia|Levant|Maghreb|Punjab|Kashmir|Rajasthan|Gujarat|Kerala|Maharashtra|Karnataka|Tamil Nadu|Uttar Pradesh|
West Bengal|Andhra Pradesh|Telangana|Bihar|Odisha|Assam|Haryana|Himachal Pradesh|Madhya Pradesh|Jharkhand|
Chhattisgarh|Uttarakhand|Goa|Sikkim|Meghalaya|Nagaland|Manipur|Mizoram|Tripura|Arunachal Pradesh|Ladakh|Silicon Valley|Wall Street|Downing Street|Capitol Hill|Buckingham Palace|Red Square|
Times Square|Central Park|Hyde Park|Big Ben|Eiffel Tower|Statue of Liberty|Golden Gate Bridge|Taj Mahal|Red Fort|
Great Wall of China|Machu Picchu|Mount Fuji|Kilimanjaro|Amazon River|
Rhine|Danube|Thames|Seine|Yosemite|Yellowstone|Hollywood|Broadway|Manhattan|Brooklyn|Queens|Bronx|Harlem|Soho|
Chinatown|Greenwich Village|Beverly Hills|Napa Valley|Death Valley|Cape Cod|Long Island|Staten Island|Rhode Island|
Hawaiian Islands|Canary Islands|Balearic Islands|Falkland Islands|Galapagos Islands|Channel Islands|British Isles|
Scottish Highlands|Lake District|Cotswolds|Yorkshire|Cornwall|Devon|Kent|Essex|Sussex|Lancashire|Derbyshire|
Northumberland|Hampshire|Surrey|Norfolk|Suffolk|Cumbria|Somerset|Dorset|Wiltshire|Oxfordshire|Cambridgeshire|
Hertfordshire|Berkshire|Buckinghamshire|East Anglia|West Midlands|East Midlands|Home Counties""".replace('\n', '').split('|')
# Entries above that are also ordinary words are written lowercase here only with their companion word, never alone.
REGIONS_ORDINARY_SINGLE = {'Queens', 'Surrey', 'Somerset'}

CITIES = """Birmingham|Bristol|Cambridge|Cardiff|Newcastle|Sheffield|Nottingham|Leicester|Brighton|Southampton|Aberdeen|
Inverness|Galway|Stuttgart|Dusseldorf|Leipzig|Dresden|Lyon|Marseille|Toulouse|Bordeaux|Naples|Turin|Genoa|Seville|
Valencia|Granada|Bilbao|Porto|Antwerp|Ghent|Bruges|Krakow|Gdansk|Vilnius|Riga|Tallinn|Minsk|Kiev|Odessa|Belgrade|Zagreb|
Sofia|Thessaloniki|Ankara|Izmir|Doha|Riyadh|Jeddah|Baghdad|Damascus|Amman|Manama|Sharjah|Casablanca|Marrakech|Tunis|
Algiers|Tripoli|Khartoum|Kampala|Kigali|Lusaka|Harare|Maputo|Luanda|Dakar|Abidjan|Durban|Pretoria|Kinshasa|Mogadishu|
Chengdu|Hangzhou|Wuhan|Nanjing|Tianjin|Chongqing|Osaka|Kyoto|Yokohama|Nagoya|Sapporo|Busan|Incheon|Pyongyang|
Ulaanbaatar|Cebu|Saigon|Phnom Penh|Vientiane|Yangon|Colombo|Thimphu|Kabul|Islamabad|Rawalpindi|Peshawar|Quetta|Multan|
Faisalabad|Ahmedabad|Jaipur|Lucknow|Kanpur|Nagpur|Indore|Bhopal|Patna|Surat|Chandigarh|Kochi|Cochin|Trivandrum|
Coimbatore|Visakhapatnam|Mysore|Gurgaon|Gurugram|Noida|Ghaziabad|Varanasi|Amritsar|Agra|Ludhiana|Madurai|Vadodara|
Nashik|Ranchi|Guwahati|Bhubaneswar|Albuquerque|Indianapolis|Jacksonville|Louisville|Memphis|Milwaukee|Oakland|
Omaha|Orlando|Raleigh|Sacramento|Tampa|Tucson|Tulsa|Winnipeg|Edmonton|Halifax|Havana|Guadalajara|Monterrey|Cancun|
Tijuana|Medellin|Caracas|Quito|Guayaquil|Montevideo|Brasilia|Recife|Curitiba|Valparaiso|Salt Lake City|Kansas City|
Oklahoma City|St Louis|Quebec City|Ho Chi Minh City|Dar es Salaam|The Hague|Baton Rouge|Santa Barbara|Santa Monica|
Palo Alto|Mountain View|Menlo Park|Sunnyvale|Cupertino|Redmond|Boulder|Tallahassee|Savannah|Charleston|
Edinburgh|Aachen|Heidelberg|Nuremberg|Hanover|Bonn|Salzburg|Innsbruck|Lausanne|Basel|Bern|Lugano|Palermo|Verona|
Siena|Pisa|Padua|Trieste|Malaga|Zaragoza|Marbella|Ibiza|Mallorca|Lagos|Mombasa|Zanzibar|Luxor|Alexandria|Aswan|
Petra|Jaffa|Haifa|Ramallah|Gaza|Beirut|Basra|Mosul|Erbil|Tabriz|Isfahan|Shiraz|Mashhad|Samarkand|Bukhara|Tashkent|Almaty|
Astana|Baku|Tbilisi|Yerevan|Novosibirsk|Vladivostok|Yekaterinburg|Kazan|Sochi|Hokkaido|Okinawa|Hiroshima|Nagasaki|
Kobe|Fukuoka|Shenyang|Harbin|Xiamen|Suzhou|Qingdao|Dalian|Kunming|Lhasa|Urumqi|Lanzhou|Hohhot|Macao|Penang|Johor Bahru|
Malacca|Phuket|Chiang Mai|Pattaya|Da Nang|Hue|Siem Reap|Luang Prabang|Mandalay|Kandy|Galle|Chittagong|Sylhet|Pokhara|
Darjeeling|Shimla|Manali|Rishikesh|Haridwar|Dehradun|Jodhpur|Udaipur|Jaisalmer|Pushkar|Ajmer|Gwalior|Jabalpur|Raipur|
Jamshedpur|Dhanbad|Asansol|Siliguri|Cuttack|Puri|Vijayawada|Guntur|Tirupati|Warangal|Mangalore|Hubli|Belgaum|Kolhapur|
Aurangabad|Solapur|Pondicherry|Puducherry|Tiruchirappalli|Salem|Thanjavur|Kozhikode|Calicut|Thrissur|Srinagar|Jammu|
Leh|Lakshadweep|Imphal|Shillong|Kohima|Aizawl|Agartala|Itanagar|Gangtok|Panaji|Silvassa|Daman""".replace('\n', '').split('|')
# City names that are also ordinary words or common first names stay out of the plain list (Nice, Reading, Salem,
# Jackson, Charlotte, Phoenix...); a few that are only a rare word elsewhere go in with a context below.
CITIES = [c for c in CITIES if c not in {'Hue', 'Puri', 'Daman', 'Charleston', 'Savannah', 'Leh', 'Boulder', 'Bordeaux', 'Genoa', 'Seville',
                                         'Damascus', 'Havana', 'Mysore', 'Calicut', 'Naples', 'Inverness', 'Valencia'}]

# --- languages and demonyms --------------------------------------------------------------------------------------

LANGS = """Lithuanian|Latvian|Estonian|Bulgarian|Serbian|Croatian|Bosnian|Slovak|Slovenian|Albanian|Armenian|Georgian|
Azerbaijani|Kazakh|Uzbek|Mongolian|Burmese|Khmer|Sinhala|Pashto|Kurdish|Amharic|Yoruba|Igbo|Hausa|Zulu|Xhosa|Afrikaans|
Somali|Maltese|Catalan|Galician|Esperanto|Sanskrit|Hakka|Hokkien|Odia|Assamese|Maithili|Konkani|Sindhi|Kashmiri|Yiddish|
Gaelic|Icelandic|Tibetan|Uyghur|Tajik|Turkmen|Kyrgyz|Belarusian|Macedonian|Montenegrin|Moldovan|Luxembourgish|Faroese|
Hawaiian|Maori|Quechua|Guarani|Nahuatl|Haitian Creole|Pashtun|Dari|Tigrinya|Oromo|Wolof|Shona|Sesotho|Setswana|Kinyarwanda|
Lingala|Malagasy|Cebuano|Ilocano|Javanese|Sundanese|Balinese|Bhojpuri|Rajasthani|Tulu|Awadhi|Magahi|Dogri|Santali|
Bodo|Manipuri|Nepalese|Laotian""".replace('\n', '').split('|')

PEOPLES = """Algerian|Angolan|Bolivian|Cambodian|Cameroonian|Dominican|Ecuadorian|Fijian|Guatemalan|Honduran|Jordanian|Libyan|
Namibian|Panamanian|Paraguayan|Qatari|Rwandan|Senegalese|Sudanese|Tanzanian|Tunisian|Ugandan|Uruguayan|Venezuelan|Yemeni|
Zimbabwean|Emirati|Kuwaiti|Omani|Bahraini|Palestinian|Nicaraguan|Salvadoran|Scandinavian|Nordic|Baltic|Slavic|Celtic|
Germanic|Caucasian|Inuit|Zambian|Botswanan|Congolese|Ivorian|Malian|Mauritian|Cypriot|Eritrean|Liberian|Gambian|
Togolese|Beninese|Burkinabe|Gabonese|Chadian|Somali|Slovene|Macedonian|Montenegrin|Moldovan|Belarusian|Uzbek|Tajik|
Turkmen|Kyrgyz|Azeri|Pashtun|Tibetan|Hongkonger|Bhutanese|Maldivian|Hawaiian|Samoan|Tongan|Polynesian|Melanesian|
Micronesian|Andean|Himalayan|Londoner|Parisian|New Yorker|Berliner|Muscovite|Mancunian|Liverpudlian|Glaswegian|
Geordie|Bostonian|Chicagoan|Angeleno|Seattleite|Hoosier|Floridian|Georgian|Virginian|Carolinian|Nevadan|Oregonian|
Coloradan|Hawaiian|Alaskan|Ohioan|Marylander|Kentuckian|Tennessean|Arizonan|Iowan|Utahn|Vermonter|Hindi-speaking|
Bengalis|Punjabis|Gujaratis|Tamils|Telugus|Malayalis|Kannadigas|Marathis|Sindhis|Kashmiris|Rajputs|Pashtuns|Kurds|
Berbers|Tuareg|Zulus|Maasai|Yoruba|Igbo|Hausa|Ashanti|Sikhs|Parsis|Parsi|Anglo-Indian|Gujarati-speaking""".replace('\n', '').split('|')
# These demonym spellings clash with the stems already in the gazetteer or with ordinary words.
PEOPLES = [p for p in PEOPLES if p not in {'Macedonian', 'Montenegrin', 'Moldovan', 'Belarusian', 'Uzbek', 'Tajik', 'Turkmen',
                                           'Kyrgyz', 'Pashtun', 'Tibetan', 'Hindi-speaking', 'Gujarati-speaking', 'Somali', 'Hawaiian', 'Georgian',
                                           'Yoruba', 'Igbo', 'Hausa', 'Sikhs', 'Anglo-Indian'}]
LANGS = [l for l in LANGS if l not in {'Maori', 'Dari'}]
LANGS += ['Maori']  # language and people both


def place_rule(canon, kind, family, conf=0.93):
    if canon.lower() in GAZ:
        return
    multi = ' ' in canon or '-' in canon
    # a region or landmark is an error only when typed all lowercase ("amazon river" is half-right, "Amazon river" ok)
    strict = kind in ('region', 'landmark')
    if multi and not strict:
        alts = variants(canon)
    else:
        alts = [canon.lower()]
    if not alts or alts == [canon]:
        return
    body = '|'.join(esc(a) for a in alts)
    pat = f'{LEFT}(?P<target>(?-i:{body})){RIGHT_H}'
    lower = canon.lower()
    pos_sentence = {
        'country': 'We flew to {x} for the conference.',
        'region': 'They traveled across {x} last summer.',
        'city': 'Our team moved to {x} in the spring.',
        'lang': 'She learned {x} before she moved abroad.',
        'people': 'The {x} delegation arrived late on Tuesday.',
        'landmark': 'We walked around {x} for an hour.',
    }[kind]
    wrong = lower if strict or not multi else shown_form(canon)
    if wrong not in alts:
        wrong = alts[0]
    pos = pos_sentence.format(x=wrong)
    neg = pos_sentence.format(x=canon) + ' ' + neg_noise(lower)
    rid = f'caps.{kind}.{slug(canon)}'
    reason = {
        'country': 'Names of countries take a capital letter.',
        'region': 'Names of regions and geographic features take a capital letter.',
        'city': 'Names of cities take a capital letter.',
        'lang': 'Names of languages and nationalities take a capital letter.',
        'people': 'Names of nationalities and peoples take a capital letter.',
        'landmark': 'Names of places take a capital letter.',
    }[kind]
    emit(rid, pat, canon, 'Capitalization', conf, reason, pos, neg, family)


def build():
    for c in COUNTRIES:
        place_rule(c, 'country', 'Countries and territories')
    for r in REGIONS:
        if r in REGIONS_ORDINARY_SINGLE:
            continue
        place_rule(r, 'region', 'Regions, seas, mountains, landmarks')
    for c in CITIES:
        place_rule(c, 'city', 'Cities')
    for l in dict.fromkeys(LANGS):
        place_rule(l, 'lang', 'Languages')
    for p in dict.fromkeys(PEOPLES):
        place_rule(p, 'people', 'Nationalities and peoples')
