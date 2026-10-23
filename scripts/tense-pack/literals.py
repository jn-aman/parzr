"""A Python port of engine/src/rules/literals.rs (required literals of a pattern) to judge prefilter quality."""
LIMIT = 256


class Exact:
    def __init__(s, v): s.v = v


class Need:
    def __init__(s, v): s.v = v


class Any_:
    pass


ANY = Any_()


def usable(s):
    return bool(s) and all(x for x in s)


def score(s):
    shortest = min(len(x) for x in s) if s else 0
    return (shortest, -len(s))


def keep(best, s):
    if usable(s) and (best[0] is None or score(s) > score(best[0])):
        best[0] = s


def union(a, b):
    out = list(a)
    for x in b:
        if x not in out:
            out.append(x)
    return out


def concat(parts):
    cur = ['']
    best = [None]
    exact = True
    for part in parts:
        if isinstance(part, Exact) and len(cur) * len(part.v) <= LIMIT:
            cur = [a + b for a in cur for b in part.v]
        else:
            exact = False
            keep(best, cur)
            cur = ['']
            if isinstance(part, Exact):
                cur = part.v
            elif isinstance(part, Need):
                keep(best, part.v)
    if exact:
        return Exact(cur)
    keep(best, cur)
    return Need(best[0]) if best[0] else ANY


def alternate(branches):
    all_exact = True
    s = []
    for b in branches:
        if isinstance(b, Exact):
            s = union(s, b.v)
        elif isinstance(b, Need):
            all_exact = False
            s = union(s, b.v)
        else:
            return ANY
    if all_exact and len(s) <= LIMIT:
        return Exact(s)
    if usable(s):
        return Need(s)
    return ANY


def repeated(n):
    if isinstance(n, (Exact, Need)) and usable(n.v):
        return Need(n.v)
    return ANY


def optional(n):
    if isinstance(n, Exact):
        return Exact(union(n.v, ['']))
    return ANY


def literal(c):
    if ord(c) < 128 or c == '’':
        return Exact([c.lower()])
    return ANY


class P:
    def __init__(s, c): s.c = c; s.i = 0
    def peek(s): return s.c[s.i] if s.i < len(s.c) else None
    def eat(s, ch):
        if s.peek() == ch:
            s.i += 1; return True
        return False

    def alt(s):
        br = [s.concat()]
        while s.eat('|'):
            br.append(s.concat())
        return br[0] if len(br) == 1 else alternate(br)

    def concat(s):
        parts = []
        while s.peek() not in (None, '|', ')'):
            parts.append(s.quantified())
        return concat(parts)

    def quantified(s):
        atom = s.atom()
        p = s.peek()
        if p == '?':
            s.i += 1; node = optional(atom)
        elif p == '*':
            s.i += 1; node = ANY
        elif p == '+':
            s.i += 1; node = repeated(atom)
        elif p == '{':
            close = s.c.index('}', s.i)
            body = s.c[s.i + 1:close]
            s.i = close + 1
            mn, _, mx = body.partition(',')
            mx = mx or mn
            mn = int(mn)
            if mn == 0: node = ANY
            elif mn == 1 and mx == '1': node = atom
            else: node = repeated(atom)
        else:
            return atom
        s.eat('?')
        return node

    def atom(s):
        c = s.peek(); s.i += 1
        if c == '(': return s.group()
        if c == '[': return s.cls()
        if c == '\\': return s.escape()
        if c in '^$': return Exact([''])
        if c == '.': return ANY
        if c in '*+?{}])|': raise ValueError('bad atom ' + c)
        return literal(c)

    def group(s):
        if s.eat('?'):
            if s.eat('P'):
                while s.peek() != '>': s.i += 1
                s.i += 1
            else:
                flags = 0
                while s.peek() not in (')', ':'):
                    if s.peek() not in 'ims-': raise ValueError('flag')
                    s.i += 1; flags += 1
                if s.eat(')'):
                    return Exact(['']) if flags > 0 else ANY
                s.i += 1
        inner = s.alt()
        if not s.eat(')'): raise ValueError('unclosed')
        return inner

    def cls(s):
        st = []
        plain = not s.eat('^')
        first = True
        while True:
            c = s.peek(); s.i += 1
            if c == ']' and not first: break
            if c == '[': raise ValueError('nested')
            if c == '\\':
                e = s.escape()
                if isinstance(e, Exact) and len(e.v) == 1 and e.v[0]: st.extend(e.v)
                else: plain = False
            elif c in '-&~': plain = False
            else:
                l = literal(c)
                if isinstance(l, Exact): st.extend(l.v)
                else: plain = False
            first = False
        return Exact(st) if plain and usable(st) and len(st) <= 8 else ANY

    def escape(s):
        c = s.peek(); s.i += 1
        if c in 'bBAz': return Exact([''])
        if c in 'dDwWsS': return ANY
        if c in 'pP':
            if s.eat('{'):
                while s.peek() != '}': s.i += 1
            s.i += 1
            return ANY
        if c == 'x':
            h = s.c[s.i:s.i + 2]; s.i += 2
            return literal(chr(int(h, 16)))
        if c == 'n': return literal('\n')
        if c == 't': return literal('\t')
        if c.isascii() and not c.isalnum() and not c.isspace(): return literal(c)
        raise ValueError('escape ' + c)


def required(pattern):
    p = P(pattern)
    try:
        node = p.alt()
    except (ValueError, IndexError):
        return None
    if p.i != len(pattern):
        return None
    if isinstance(node, (Exact, Need)) and usable(node.v):
        return node.v
    return None


if __name__ == '__main__':
    print(sorted(required(r"(?i)\b(?P<target>an) (?:report|file)\b")))
    print(sorted(required(r"(?im)^(can|could) you ")))
    print(sorted(required(r"(?i)\bI['’]m\b")))
    print(sorted(required(r"(?i)\bgoes? home\b")))
    print(sorted(required(r"(?i)\b[\p{L}']+ (?P<target>goes)\b")))
