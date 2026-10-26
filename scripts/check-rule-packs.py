#!/usr/bin/env python3
"""Checks every engine/rules/packs/*.json before the Rust tests run: valid JSON array, required fields, unique ids
across all rule files, pattern/positive/negative sanity (the positive must contain a target match, the negative
must not), no lookaround/backreference syntax (the engine's regex crate has none), and a prefilter literal.
usage: check-rule-packs.py [FILE...]   (default: every pack)"""
import json, pathlib, re, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
RULES = ROOT / 'engine/rules'
REQUIRED = {'id', 'pattern', 'replacement', 'category', 'confidence', 'reason', 'provenance', 'positive', 'negative'}
CATEGORIES = {'Grammar', 'Agreement', 'Tense', 'Verb form', 'Possessive', 'Word choice', 'Spelling', 'Punctuation',
              'Capitalization', 'Style', 'Clarity', 'Redundancy', 'Register', 'Tone'}
def rust_regex(pattern):
    # Python's re is a superset for the subset the packs use; translate (?P<name>) is shared syntax.
    if re.search(r'\(\?[=!<]|\\[1-9]|\(\?<[=!]', pattern):
        raise ValueError('lookaround or backreference (unsupported by the engine)')
    return re.compile(pattern)
def main(paths):
    ids = {}
    for base in ('grammar.json', 'tone.json', 'usage.json'):
        for r in json.loads((RULES / base).read_text()):
            ids[r['id']] = base
    files = [pathlib.Path(p) for p in paths] or sorted((RULES / 'packs').glob('*.json'))
    problems = 0
    def bad(f, rid, msg):
        nonlocal problems; problems += 1; print(f'{f.name}: {rid}: {msg}')
    for f in files:
        try:
            rules = json.loads(f.read_text())
        except Exception as e:
            print(f'{f.name}: invalid JSON: {e}'); problems += 1; continue
        if not isinstance(rules, list):
            print(f'{f.name}: must be a JSON array'); problems += 1; continue
        for r in rules:
            rid = r.get('id', '?')
            missing = REQUIRED - set(r)
            if missing: bad(f, rid, f'missing {sorted(missing)}'); continue
            if rid in ids: bad(f, rid, f'duplicate id (also in {ids[rid]})')
            ids[rid] = f.name
            if r['category'] not in CATEGORIES: bad(f, rid, f'category {r["category"]!r} not in {sorted(CATEGORIES)}')
            if not (0 < r['confidence'] <= 1): bad(f, rid, 'confidence must be in (0, 1]')
            if not r['reason'].strip() or not r['provenance'].strip(): bad(f, rid, 'empty reason/provenance')
            try:
                rx = rust_regex(r['pattern'])
            except Exception as e:
                bad(f, rid, f'pattern: {e}'); continue
            if '(?P<target>' not in r['pattern'] and '(?P<moved>' not in r['pattern']:
                bad(f, rid, 'pattern needs a (?P<target>...) group')
            if not rx.search(r['positive']): bad(f, rid, 'positive example does not match')
            if rx.search(r['negative']): bad(f, rid, 'negative example matches')
            m = rx.search(r['positive'])
            if m and 'target' in rx.groupindex:
                t = m.group('target')
                rep = re.sub(r'\$\{(\w+)\}', lambda g: m.group(g.group(1)) or '', r['replacement'])
                if t is not None and t == rep: bad(f, rid, 'replacement equals the target on the positive')
            # a crude literal check: at least one run of 3+ letters outside a character class and not optional
            if not re.search(r'[A-Za-z\']{3,}', re.sub(r'\[[^\]]*\]|\\[bBwWsSdD]', '', r['pattern'])):
                bad(f, rid, 'no literal word for the prefilter (the Rust test is the authority)')
        print(f'{f.name}: {len(rules)} rules')
    print(f'{problems} problem(s)' if problems else 'rule packs OK')
    sys.exit(1 if problems else 0)
if __name__ == '__main__':
    main(sys.argv[1:])
