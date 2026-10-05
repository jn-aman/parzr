#!/usr/bin/env python3
"""Export the attributed wordfreq English prior for the native spelling ranker.

Build-time only: run with wordfreq==3.1.1 installed in an isolated environment.
The adapted frequency data remains CC BY-SA 4.0, distinct from the Apache code.
"""
import hashlib
import importlib.metadata
import json
import pathlib
import wordfreq

ROOT = pathlib.Path(__file__).resolve().parent.parent
assert importlib.metadata.version('wordfreq') == '3.1.1'
lexicon = dict(json.loads((ROOT / 'engine/rules/lexicon.json').read_text()))
frequencies = wordfreq.get_frequency_dict('en', wordlist='large')
entries = sorted((word, round(wordfreq.zipf_frequency(word, 'en') * 100)) for word in lexicon if word.isascii() and word.isalpha() and word in frequencies)
package = pathlib.Path(wordfreq.__file__).parent
sources = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (package / 'data').glob('*en*') if p.is_file()}
metadata = {
    'title': 'Parzr English spelling frequency prior',
    'license': 'CC-BY-SA-4.0',
    'license_url': 'https://creativecommons.org/licenses/by-sa/4.0/',
    'source': 'https://github.com/rspeer/wordfreq',
    'version': '3.1.1',
    'attribution': 'Robyn Speer / wordfreq; Marc Brysbaert et al. / freely available SUBTLEX; OpenSubtitles; Google Books Ngrams; Leeds Internet Corpus; Wikipedia; ParaCrawl. Full source credits and citations accompany the app in EnglishFrequency-NOTICES.md.',
    'changes': 'ASCII alphabetic English entries intersected with the Parzr lexicon; Zipf frequencies quantized to hundredths. Used as a prior with lexical, inflection and local context constraints. No benchmark references used.',
    'source_data_sha256': sources,
}
output = ROOT / 'engine/rules/frequency.json'
output.write_text(json.dumps({'metadata': metadata, 'entries': entries}, ensure_ascii=False, separators=(',', ':')) + '\n')
print(f'Exported {len(entries)} attributed frequency entries; SHA256 {hashlib.sha256(output.read_bytes()).hexdigest()}.')
