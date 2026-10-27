"""Redundant acronym syndrome: the last word of the acronym is said again ("ATM machine", "PIN number", "HIV virus")."""
from core import add, S, E

SEC = 'Acronym followed by the word it ends in'


def acro(rid, ac, word, pos, neg, conf=0.76, spelled=None, plural=True):
    sp = spelled or f'{ac} stands for a phrase that ends in “{word}”'
    # The acronym is kept as typed (any case), a plural "s" moves onto it.
    pat = rf'(?im){S}(?P<target>(?P<k>(?-i:{ac})) {word}(?P<s>s)?){E}' if plural else rf'(?im){S}(?P<target>(?P<k>(?-i:{ac})) {word}){E}'
    rep = '${k}${s}' if plural else '${k}'
    reason = f'“{ac}” already ends in “{word}” ({sp}): “{ac}” alone is enough.'
    return add(f'acro.{rid}', pat, rep, 'Style', conf, reason, pos, neg)


def build():
    ids = []
    a = lambda *x, **k: ids.append(acro(*x, **k))
    a('atm_machine', 'ATM', 'machine', 'I found an ATM machine near the station.',
      'I found an ATM near the station, and a coffee machine next to it.',
      spelled='automated teller machine')
    a('pin_number', 'PIN', 'number', 'Never share your PIN number with anyone.',
      'Never share your PIN with anyone, and write the phone number somewhere else.',
      spelled='personal identification number')
    a('hiv_virus', 'HIV', 'virus', 'The clinic tests for the HIV virus.',
      'The clinic tests for HIV, and a flu virus sample was sent out.',
      spelled='human immunodeficiency virus', plural=False)
    a('aids_syndrome', 'AIDS', 'syndrome', 'The AIDS syndrome was first described in 1981.',
      'AIDS was first described in 1981, and Down syndrome in the 1860s.',
      spelled='acquired immune deficiency syndrome', plural=False)
    a('lcd_display', 'LCD', 'display', 'The LCD display is easy to read.',
      'The LCD is easy to read, and the OLED display is brighter.',
      spelled='liquid crystal display')
    a('led_diode', 'LED', 'diode', 'Each LED diode draws very little power.',
      'Each LED draws very little power, and the Zener diode stays cool.',
      spelled='light-emitting diode')
    a('isbn_number', 'ISBN', 'number', 'The ISBN number is printed on the back cover.',
      'The ISBN is printed on the back cover, next to the price.',
      spelled='International Standard Book Number')
    a('vin_number', 'VIN', 'number', 'Check the VIN number before you buy the car.',
      'Check the VIN before you buy the car, and note the phone number of the seller.',
      spelled='vehicle identification number')
    # "GPS system" and "SMS messages" are the everyday names of the things (a car's GPS system, sending
    # SMS messages): both fired on correct sentences in the 30k-sentence false-alarm corpus, so neither
    # is a rule.
    a('ram_memory', 'RAM', 'memory', 'The laptop has eight gigabytes of RAM memory.',
      'The laptop has eight gigabytes of RAM, and good memory management.',
      spelled='random access memory', plural=False)
    a('rom_memory', 'ROM', 'memory', 'The console keeps the boot code in ROM memory.',
      'The console keeps the boot code in ROM, and the old memory card is full.',
      spelled='read-only memory', plural=False)
    a('lan_network', 'LAN', 'network', 'The office LAN network went down at noon.',
      'The office LAN went down at noon, and the guest network stayed up.',
      spelled='local area network')
    a('wan_network', 'WAN', 'network', 'The company runs a private WAN network between its sites.',
      'The company runs a private WAN between its sites, and a guest network at each one.',
      spelled='wide area network')
    a('vpn_network', 'VPN', 'network', 'Connect through the VPN network before you open the file.',
      'Connect through the VPN before you open the file, and then join the office network.',
      spelled='virtual private network')
    a('dns_system', 'DNS', 'system', 'The DNS system returned the wrong address.',
      'The DNS returned the wrong address, and the billing system was fine.',
      spelled='Domain Name System')
    a('upc_code', 'UPC', 'code', 'Scan the UPC code at the till.',
      'Scan the UPC at the till, and then type the discount code.',
      spelled='Universal Product Code')
    a('isp_provider', 'ISP', 'provider', 'Call your ISP provider if the line is down.',
      'Call your ISP if the line is down, and the cloud provider if the site is.',
      spelled='Internet service provider')
    ids.append(add('acro.faq_questions', rf'(?im){S}(?P<target>(?P<k>(?-i:FAQ)) question(?P<s>s)){E}', '${k}${s}', 'Style', 0.76,
                   '“FAQ” already stands for “frequently asked questions”: say “FAQs”, not “FAQ questions”.',
                   'The FAQ questions are listed on the help page.',
                   'The FAQs are listed on the help page. Add this FAQ question to the list, and email other questions.'))
    a('gui_interface', 'GUI', 'interface', 'The GUI interface is easy to learn.',
      'The GUI is easy to learn, and the command line interface is faster.',
      spelled='graphical user interface', conf=0.74)
    a('cli_interface', 'CLI', 'interface', 'The CLI interface takes a path as its argument.',
      'The CLI takes a path as its argument, and the web interface takes a name.',
      spelled='command-line interface')
    a('api_interface', 'API', 'interface', 'The API interface is documented online.',
      'The API is documented online, and the web interface is in beta.',
      spelled='application programming interface', conf=0.72)
    a('rip_in_peace', 'R\\.?I\\.?P\\.?', 'in peace', 'RIP in peace, old friend.',
      'RIP, old friend. Rest in peace.', conf=0.78, spelled='rest in peace', plural=False)
    a('cpu_processor', 'CPU', 'processor', 'The CPU processor runs at 3 GHz.',
      'The CPU runs at 3 GHz, and the graphics processor is idle.',
      spelled='central processing unit', conf=0.74)
    a('ocr_recognition', 'OCR', 'recognition', 'The OCR recognition step failed on the scan.',
      'The OCR step failed on the scan, and speech recognition was fine.',
      spelled='optical character recognition', plural=False)
    return ids
