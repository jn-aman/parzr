"""Every negative must be matched by no rule of the pack (not only its own), and every positive by its own rule."""
import re, sys


def run(rules):
    compiled = [(r['id'], re.compile(r['pattern']), r) for r in rules]
    bad = 0
    for rid, rx, r in compiled:
        for other, rx2, r2 in compiled:
            if rx2.search(r['negative']):
                print('NEGATIVE of %s is matched by %s: %r' % (rid, other, r['negative'])); bad += 1
        if not rx.search(r['positive']):
            print('POSITIVE of %s does not match' % rid); bad += 1
    if bad:
        sys.exit('%d problem(s)' % bad)
