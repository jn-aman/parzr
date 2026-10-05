#!/usr/bin/env python3
"""Import a reviewed literal subset from harper-core 1.7.0. No runtime Harper dependency.
Pass the extracted crate directory as --upstream. Complex DSL, stylistic and
context-dependent phrases are deliberately not promoted to automatic edits.
"""
import argparse, hashlib, json, pathlib, re
ROOT=pathlib.Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser();parser.add_argument('--upstream',type=pathlib.Path,required=True);args=parser.parse_args()
allow=set('AdNauseam AfterAll AsFollows AsLongAs BareInMind BatedBreath BeckAndCall BesideThePoint BestRegards BetterOffWith CanBeSeen EggYolk EverSince ForALongTime HalfAnHour HumanBeings InLieuOf InOneFellSwoop InsteadOf IsKnownFor JawDropping KindRegards ManagerialReins MyHouse NeedHelp OldWivesTale OnTheSpurOfTheMoment OnTopOf PartsOfSpeech PerSe PointsOfView PrayingMantis RulesOfThumb SameAs ScantilyClad SomebodyElses SpecialAttention StatuteOfLimitations ThanksALot ThoughtProcess TrialAndError TurnItOff WhetYourAppetite WillContain'.split())
pack=ROOT/'engine/rules/phrases.json';rules=[r for r in json.loads(pack.read_text()) if not r['id'].startswith('harper.')];sources={r['source'].lower() for r in rules};manifest=[]
for name in sorted(allow):
 p=args.upstream/'src/linting/weir_rules'/f'{name}.weir';raw=p.read_bytes();s=raw.decode();expression=re.search(r'^expr main (.+)',s)[1];replacement=re.search(r'let becomes "([^"]+)"',s)[1];reason=re.search(r'let message "([^"]+)"',s)[1];kind=re.search(r'let kind "([^"]+)"',s)[1]
 if not re.fullmatch(r'[()\[\], a-z\x27-]+',expression):raise ValueError(f'{name}: unsupported DSL; review required')
 literals=re.findall(r'\(([^()]+)\)',expression) or [expression]
 for i,literal in enumerate(literals):
  if literal.lower() in sources:continue
  sources.add(literal.lower());rules.append(dict(id=f'harper.{name}.{i}',source=literal,replacement=replacement,category='Spelling' if kind in ('Spelling','Typo') else 'Grammar',confidence=.96,explanation=reason,provenance=f'Adapted from harper-core 1.7.0 {name}.weir; Apache-2.0; see THIRD_PARTY_NOTICES'))
 manifest.append(dict(file=f'{name}.weir',sha256=hashlib.sha256(raw).hexdigest(),license='Apache-2.0'))
pack.write_text(json.dumps(rules,indent=2,ensure_ascii=False)+'\n')
(ROOT/'engine/rules/import-manifest.json').write_text(json.dumps(dict(upstream='https://github.com/Automattic/harper',version='harper-core 1.7.0',changes='Literal subset translated to parzr phrase VM; automatic-correction allowlist; messages and corrections retained.',files=manifest),indent=2)+'\n')
print(f'{len(rules)} phrase corrections; {len(manifest)} reviewed upstream definitions')
