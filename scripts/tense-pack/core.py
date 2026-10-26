"""Rule records, a Python self-check that mirrors how the engine applies a rule, and shared regex pieces.

Pattern style (for the engine's prefilter, see engine/src/rules/literals.rs): fixed words are joined with a single
literal space, and optional pieces carry their own leading space ("(?: already)?"), so the verb a rule is about sits in a
literal run of its own (" went", " go the") and the rule is only compiled when that phrase occurs in the text."""
import re

RULES = []          # every rule, in order
E2E = []            # (rule_id, wrong, right) end-to-end cases for the engine probe
NEG = []            # (rule_id, correct sentence) that the engine must leave alone
PROBLEMS = []

PROV = "parzr original rule"

# --- shared pieces -------------------------------------------------------------------------------------------
END = r'(?:[\s.,;:!?)\]"”]|$)'
# adverbs that may sit between an auxiliary and its verb
ADV_WORDS = ('not|never|ever|already|just|also|still|finally|recently|always|even|really|only|once|often|'
             'previously|actually|probably|quickly|since|yet|then|barely|hardly|almost|nearly|twice|again|'
             'first|later|suddenly|simply')
SP_ADV1 = rf'(?: (?:{ADV_WORDS}))?'
SP_ADV2 = rf'(?: (?:{ADV_WORDS})){{0,2}}'
PRON = r'(?:you|he|she|it|we|they|I)'
SP_SUBJ = rf'(?: {PRON})?'
# a noun-phrase or name subject of an inverted question: "Has the team went?", "Did Anna came?"
NP = (r"(?:(?:the|my|your|his|her|our|their|this|that|these|those) [A-Za-z]+|(?-i:[A-Z][a-z]+)|"
      r"anyone|someone|everyone|anybody|somebody|everybody|nobody|no one)")
PERFECT = r"(?:have|has|had|haven['’]t|hasn['’]t|hadn['’]t|['’]ve|['’]d|having)"
# "'d" is "would" as often as "had" ("I'd never go"), so rules that read a bare verb after the auxiliary leave it out
PERFECT_NOD = r"(?:have|has|had|haven['’]t|hasn['’]t|hadn['’]t|['’]ve|having)"
BE_AUX = r"(?:was|were|is|are|am|be|been|being|wasn['’]t|weren['’]t|isn['’]t|aren['’]t)"
DET = (r"(?:the|a|an|my|your|his|her|our|their|its|this|that|these|those|it|them|him|me|us|you|some|any|all|"
       r"every|each|no|more|many|enough|both|another|one|two|three|four|five|six|ten)")
DETOBJ = (r"(?:the|a|an|my|your|his|her|our|their|its|this|that|these|those|it|them|him|me|us|some|all|any|every|"
          r"more|no|two|three|four|five|ten)")
PARTS = (r"(?:to|from|for|with|into|on|at|about|over|through|across|by|around|after|up|down|off|back|home|away|"
         r"there|here|again|twice|once|before|already|last|in|out)")
STARTS = (r"(?:^|[.!?;:] |, |\b(?:and|but|so|then|because|when|while|after|before|once|until|yesterday|today|"
          r"tonight|later|finally|suddenly) )")
MODAL = r"(?-i:can|could|may|might|must|shall|should|will|would)"
MODAL_NEG = r"(?i:won['’]t|can['’]t|couldn['’]t|wouldn['’]t|shouldn['’]t|mustn['’]t|cannot)"


def Q(w):
    return f'“{w}”'


def rule(id, pattern, replacement, reason, positive, negative, right=None, category='Verb form',
         confidence=0.95, more_pos=(), more_neg=()):
    """Register a rule.  right = the corrected form of `positive` (checked by the self-check and the engine probe)."""
    r = dict(id=id, pattern=pattern, replacement=replacement, category=category, confidence=confidence,
             reason=reason, provenance=PROV, positive=positive, negative=negative)
    RULES.append(r)
    check(r, right, more_pos, more_neg)
    if right is not None:
        E2E.append((id, positive, right))
    for w, rt in more_pos:
        E2E.append((id, w, rt))
    for n in negative_sentences(negative) + list(more_neg):
        NEG.append((id, n))
    return r


def negative_sentences(neg):
    return [s.strip() for s in re.split(r'(?<=[.!?])\s+', neg) if s.strip()]


def apply(r, text, rx=None):
    """What the engine does for one rule: every non-overlapping match, target group replaced."""
    rx = rx or re.compile(r['pattern'])
    out, last = [], 0
    for m in rx.finditer(text):
        t = m.start('target') if 'target' in rx.groupindex else m.start()
        e = m.end('target') if 'target' in rx.groupindex else m.end()
        rep = re.sub(r'\$\{(\w+)\}', lambda g: m.group(g.group(1)) or '', r['replacement'])
        out.append(text[last:t]); out.append(rep); last = e
    out.append(text[last:])
    return ''.join(out)


def same_text(a, b):
    """Compare ignoring a capital the engine would add at a sentence start."""
    return a == b or (a[:1].lower() + a[1:] == b[:1].lower() + b[1:])


def check(r, right, more_pos, more_neg):
    try:
        rx = re.compile(r['pattern'])
    except re.error as e:
        PROBLEMS.append(f"{r['id']}: bad pattern {e}"); return
    if re.search(r'\(\?[=!<]|\\[1-9]', r['pattern']):
        PROBLEMS.append(f"{r['id']}: lookaround/backreference")
    if '(?P<target>' not in r['pattern']:
        PROBLEMS.append(f"{r['id']}: no target group")
    if not rx.search(r['positive']):
        PROBLEMS.append(f"{r['id']}: positive does not match: {r['positive']}")
    elif right is not None and not same_text(apply(r, r['positive'], rx), right):
        PROBLEMS.append(f"{r['id']}: positive gives {apply(r, r['positive'], rx)!r}, wanted {right!r}")
    for w, rt in more_pos:
        if not rx.search(w):
            PROBLEMS.append(f"{r['id']}: extra positive does not match: {w}")
        elif not same_text(apply(r, w, rx), rt):
            PROBLEMS.append(f"{r['id']}: extra positive {w!r} gives {apply(r, w, rx)!r}, wanted {rt!r}")
    if rx.search(r['negative']):
        PROBLEMS.append(f"{r['id']}: negative matches: {rx.search(r['negative']).group(0)!r} in {r['negative']!r}")
    for n in more_neg:
        if rx.search(n):
            PROBLEMS.append(f"{r['id']}: extra negative matches: {n}")


def pick(pattern, makers):
    """First (wrong, right) pair from makers whose wrong sentence the pattern matches."""
    rx = re.compile(pattern)
    for w, rt in makers:
        if rx.search(w):
            return w, rt
    return None
