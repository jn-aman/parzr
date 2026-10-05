#!/usr/bin/env python3
"""Import an attributed, pinned SymSpell English word-pair frequency asset."""
import hashlib
import json
import pathlib
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
REVISION = 'c239062ae02961df18ab7da1671d01b4388204e0'
BASE = f'https://raw.githubusercontent.com/wolfgarbe/SymSpell/{REVISION}/'
SOURCE = BASE + 'SymSpell/frequency_bigramdictionary_en_243_342.txt'
data = urllib.request.urlopen(SOURCE, timeout=60).read()
lexicon = dict(json.loads((ROOT/'engine/rules/lexicon.json').read_text()))
entries = []
for line in data.decode().splitlines():
    a, b, count = line.split()
    if a in lexicon and b in lexicon:
        entries.append((f'{a} {b}', int(count)))
entries.sort()
metadata = {
    'source': SOURCE, 'revision': REVISION,
    'source_sha256': hashlib.sha256(data).hexdigest(),
    'attribution': 'Wolf Garbe / SymSpell; Google Books Ngram contributors; SCOWL contributors.',
    'license': 'MIT; underlying Google Books Ngram frequencies CC-BY-3.0',
    'license_url': 'https://creativecommons.org/licenses/by/3.0/',
    'changes': 'Word pairs intersected with the Parzr English lexicon. Counts unchanged. No benchmark references used.',
}
output = ROOT/'engine/rules/bigrams.json'
output.write_text(json.dumps({'metadata': metadata, 'entries': entries}, separators=(',', ':'))+'\n')
third = ROOT/'resources/ThirdParty'
(third/'SymSpell-LICENSE.txt').write_bytes(urllib.request.urlopen(BASE+'LICENSE', timeout=30).read())
(third/'EnglishBigrams-NOTICES.md').write_text(
    '# English word-pair frequency data\n\n'
    + json.dumps(metadata, indent=2) + '\n\n'
    + 'Source dictionary provenance and source licenses: https://github.com/wolfgarbe/SymSpell/blob/'+REVISION+'/README.md#frequency-dictionary\n'
    + 'SCOWL attribution and license: http://wordlist.aspell.net/scowl-readme/\n'
    + 'Google Books Ngrams: https://books.google.com/ngrams/ ; CC BY 3.0: https://creativecommons.org/licenses/by/3.0/\n'
    + 'The MIT license accompanies this adapted asset. The data ships offline in the app and DMG.\n')
print(f'Imported {len(entries)} attributed word pairs; SHA256 {hashlib.sha256(output.read_bytes()).hexdigest()}.')
