"""Future in time clauses, conditionals, wish, 'would have' for 'had', modal + of."""
from core import *
from lex import *

CONNECTORS = [
    # (id, text, example sentence with the error, example corrected)
    ('after', 'after', "I will call you after I will finish the work.", "I will call you after I finish the work."),
    ('before', 'before', "I will text you before I will leave.", "I will text you before I leave."),
    ('as_soon_as', 'as soon as', "We will start as soon as they will arrive.", "We will start as soon as they arrive."),
    ('until', 'until', "Please wait until I will return.", "Please wait until I return."),
    ('till', 'till', "Stay here till we will come back.", "Stay here till we come back."),
    ('once', 'once', "We will begin once you will confirm.", "We will begin once you confirm."),
    ('by_the_time', 'by the time', "The show will start by the time we will arrive.", "The show will start by the time we arrive."),
    ('whenever', 'whenever', "Whenever I will visit, we eat together.", "Whenever I visit, we eat together."),
    ('every_time', 'every time', "Every time I will try, it fails.", "Every time I try, it fails."),
    ('next_time', 'the next time', "The next time you will see him, say hello.", "The next time you see him, say hello."),
    ('in_case', 'in case', "Take a coat in case you will need it.", "Take a coat in case you need it."),
]
CONN_ALL = '|'.join(c[1] for c in CONNECTORS)
VERB_ALT = '|'.join(TC_VERBS)


def time_clauses():
    for cid, conn, wrong, right in CONNECTORS:
        reason = ("After “%s” a future event takes the present tense, without “will”." % conn)
        pat = rf"(?i)\b{conn} (?:I|we|you|they) (?P<target>will )(?:{VERB_ALT})\b"
        neg = f"{right} Tell me when you will arrive. I think we will leave {conn} the meeting ends."
        rule(f"tense.time_clause.{cid}", pat, "", reason, wrong, neg, right=right, category='Tense', confidence=0.94)
        # "will be" -> am / are
        for subj, aux in (('I', 'am'), ('we|you|they', 'are')):
            ex_s = 'I' if subj == 'I' else 'we'
            wb = f"Please call me {conn} {ex_s} will be ready." if cid != 'in_case' else f"Take a coat in case {ex_s} will be late."
            rb = wb.replace('will be', aux)
            rule(f"tense.time_clause_be.{cid}.{aux}", rf"(?i)\b{conn} (?:{subj}) (?P<target>will be)\b", aux,
                 reason, wb, f"{rb} Ask whether {ex_s} will be there.", right=rb, category='Tense', confidence=0.94)
    # third person singular: "until he will arrive" -> "until he arrives"
    for b in TC_VERBS:
        t = third(b)
        pat = rf"(?i)\b(?:{CONN_ALL}) (?:he|she|it) (?P<target>will {b})\b"
        rule(f"tense.time_clause_3sg.{b}", pat, t,
             f"After words like “until”, “after” or “once” a future event takes the present tense: “{t}”, not “will {b}”.",
             f"We can start once she will {b}.", f"We can start once she {t}. Ask whether she will {b}.",
             right=f"We can start once she {t}.", category='Tense', confidence=0.94,
             more_pos=[(f"Wait until he will {b}.", f"Wait until he {t}.")])
    rule("tense.time_clause_3sg.be", rf"(?i)\b(?:{CONN_ALL}) (?:he|she|it) (?P<target>will be)\b", "is",
         "After words like “until”, “after” or “once” a future event takes the present tense: “is”, not “will be”.",
         "Wait until it will be ready.", "Wait until it is ready. Ask whether it will be ready.",
         right="Wait until it is ready.", category='Tense', confidence=0.94)
    # initial "When ..., " and "If ..., "
    rule("tense.time_clause.when_initial",
         rf"(?im)(?:^|[.!?] )When (?:I|we|you|they) (?P<target>will )(?:{VERB_ALT})\b[^.!?;\n]{{0,60}},",
         "", "After “when” a future event takes the present tense, without “will”.",
         "When I will reach home, I will call you.",
         "When I reach home, I will call you. When will you reach home? I do not know when I will reach home, but I will call.",
         right="When I reach home, I will call you.", category='Tense', confidence=0.93,
         more_pos=[("When we will arrive, the show will have started.", "When we arrive, the show will have started.")])
    rule("tense.time_clause.if_initial",
         rf"(?im)(?:^|[.!?] )If (?:I|we) (?P<target>will )(?:{VERB_ALT})\b[^.!?;\n]{{0,60}},",
         "", "After “if” a possible future event takes the present tense, without “will”.",
         "If I will go there, I will call you.",
         "If I go there, I will call you. I wonder if I will go there. If you will follow me, I will show you the room.",
         right="If I go there, I will call you.", category='Tense', confidence=0.93,
         more_pos=[("If we will leave now, we will arrive on time.", "If we leave now, we will arrive on time.")])
    for ini, w in (('when_initial', 'When'), ('if_initial', 'If')):
        for sj, aux in (('I', 'am'), ('we|you|they' if w == 'When' else 'we', 'are')):
            ex_s = 'I' if sj == 'I' else 'we'
            wrong = f"{w} {ex_s} will be ready, we will leave."
            right = wrong.replace('will be', aux, 1)
            rule(f"tense.time_clause_be.{ini}.{aux}",
                 rf"(?im)(?:^|[.!?] ){w} (?:{sj}) (?P<target>will be)\b[^.!?;\n]{{0,60}},", aux,
                 f"After “{w.lower()}” a future event takes the present tense: “{aux}”, not “will be”.",
                 wrong, f"{right} {w} will {ex_s} be ready?", right=right, category='Tense', confidence=0.93)


# ---------------------------------------------------------------------------------------------------------------
V3_LIST = ("been gone done seen taken given known written eaten begun broken chosen driven fallen flown forgotten "
           "grown hidden ridden risen run shown spoken stolen thrown worn won lost made told said sold sent bought "
           "brought built caught found got had heard held kept left lent met paid read set sat slept spent stood "
           "taught thought understood come become").split()


def conditionals():
    v3 = '|'.join(V3_LIST)
    ed = r"[a-z]{2,}ed"
    rule("tense.wish.would_have",
         rf"(?i)\b(?:I|we|he|she|they) wish(?:es|ed)? (?:I|we|he|she|it|they|you|(?-i:[A-Z][a-z]+)) (?P<target>would have) (?:{v3}|{ed})\b",
         "had", "A wish about the past takes the past perfect: “I wish I had gone”.",
         "I wish I would have gone to the party.", "I wish I had gone to the party. I wish you would have patience.",
         right="I wish I had gone to the party.", category='Tense', confidence=0.93,
         more_pos=[("She wished he would have called earlier.", "She wished he had called earlier.")])
    for mod, rep, ex, ok in (('can', 'could', "I wish I can fly.", "I wish I could fly."),
                             ('will', 'would', "I wish it will stop raining.", "I wish it would stop raining."),
                             ('may', 'might', "I wish I may see him again.", "I wish I might see him again.")):
        rule(f"tense.wish.{mod}",
             rf"(?i)\bI wish(?:ed)? (?:I|we|he|she|it|they|you) (?P<target>{mod})\b",
             rep, f"After “wish” the verb moves back in time: “{rep}”, not “{mod}”.",
             ex, f"{ok} I wish you well. Make a wish, and I {mod} listen.", right=ok, category='Tense', confidence=0.93)
    rule("tense.wish.am",
         r"(?i)\b(?:I wish(?:ed)? I|we wish(?:ed)? we) (?P<target>am|are) (?:a|an|the|rich|taller|there|here|"
         r"young|younger|better|free|home|at|in|on|with|not|so|very|more|less|stronger|smarter|thinner)\b",
         "were", "After “wish” the verb moves back in time: “I wish I were …”.",
         "I wish I am taller.", "I wish I were taller. I know that I am tall enough.",
         right="I wish I were taller.", category='Tense', confidence=0.92,
         more_pos=[("We wish we are there.", "We wish we were there.")])
    rule("tense.wish.have",
         r"(?i)\b(?:I wish(?:ed)? I|we wish(?:ed)? we) (?P<target>have) (?:a|an|the|more|enough|some|my|time|money|no|two|three)\b",
         "had", "After “wish” the verb moves back in time: “I wish I had …”.",
         "I wish I have more time.", "I wish I had more time. I hope I have more time soon.",
         right="I wish I had more time.", category='Tense', confidence=0.92,
         more_pos=[("I wished I have a car.", "I wished I had a car.")])


def modal_of():
    for mod in ("wouldn", "couldn", "shouldn", "mightn", "mustn"):
        rule(f"tense.modal_of.{mod}t",
             rf"(?i)\b{mod}['’]t (?P<target>of) (?:been|{'|'.join(V3_LIST)}|[a-z]{{2,}}ed)\b", "have",
             f"Write “{mod}’t have”, not “{mod}’t of”: “of” is a misheard “have”.",
             f"She {mod}'t of known.", f"She {mod}'t have known. They spoke of it. You {mod}'t of course take it back.",
             right=f"She {mod}'t have known.", category='Grammar', confidence=0.97,
             more_pos=[(f"He {mod}'t of been there.", f"He {mod}'t have been there.")])
