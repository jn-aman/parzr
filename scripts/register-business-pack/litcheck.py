#!/usr/bin/env python3
"""Runs engine/src/rules/literals.rs (compiled standalone by rustc, see the header of this file) over the pack's
patterns and prints the rules without a required literal and the size of every literal set.
Build the checker once:  python3 scripts/register-business-pack/litcheck.py --build DIR
Use it:                  python3 scripts/register-business-pack/litcheck.py DIR"""
import json, pathlib, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
def main():
    if sys.argv[1] == '--build':
        d = pathlib.Path(sys.argv[2]); d.mkdir(parents=True, exist_ok=True)
        src = (ROOT / 'engine/src/rules/literals.rs').read_text()
        src = src[:src.index('#[cfg(test)]')].replace('//!', '//')
        src += '''
fn main() {
    let text = std::fs::read_to_string(std::env::args().nth(1).unwrap()).unwrap();
    for (i, line) in text.lines().enumerate() {
        match required(line) {
            Some(set) => println!("{}\\t{}\\t{}", i, set.len(), set.join("|")),
            None => println!("{}\\tNONE", i),
        }
    }
}
'''
        (d / 'lit.rs').write_text(src)
        subprocess.run(['rustc', '--edition', '2024', '-O', str(d / 'lit.rs'), '-o', str(d / 'litcheck')], check=True)
        return
    d = pathlib.Path(sys.argv[1])
    rules = json.loads((ROOT / 'engine/rules/packs/register-business.json').read_text())
    (d / 'patterns.txt').write_text('\n'.join(r['pattern'] for r in rules) + '\n')
    out = subprocess.run([str(d / 'litcheck'), str(d / 'patterns.txt')], capture_output=True, text=True, check=True).stdout.splitlines()
    bad = 0
    for line, r in zip(out, rules):
        f = line.split('\t')
        if f[1] == 'NONE':
            bad += 1; print('NO LITERAL', r['id'])
        elif int(f[1]) > 32:
            print('LARGE SET', r['id'], f[1])
    print(f'{len(rules)} rules, {bad} without a literal')
    sys.exit(1 if bad else 0)
main()
