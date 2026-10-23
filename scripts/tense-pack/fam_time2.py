"""More conditional slips: 'If I would have the money', 'If I would be you', 'If you will have any questions'."""
from core import *


def if_clauses():
    rule("tense.conditional.if_would_have_noun",
         r"(?im)(?:^|[.!?] )If (?:I|we|he|she|it|they) (?P<target>would have) (?:the|a|an|enough|more|any|some|my|your|his|her|our|their|no|two|three|time|money)\b[^.!?;\n]{0,60},",
         "had", "An unreal “if” clause about the present takes the past: “If I had the money, …”.",
         "If I would have the money, I would buy it.",
         "If I had the money, I would buy it. If you would have a seat, the doctor will see you. I wonder if I would have the time.",
         right="If I had the money, I would buy it.", category='Tense', confidence=0.92,
         more_pos=[("If they would have a bigger budget, they would hire more people.",
                    "If they had a bigger budget, they would hire more people.")])
    rule("tense.conditional.if_would_be_you",
         r"(?i)\bif (?:I|we) (?P<target>would be) (?:you|in your (?:place|position|shoes|situation))\b",
         "were", "An unreal “if” clause takes the past: “If I were you, …”.",
         "If I would be you, I would call him.", "If I were you, I would call him. He asked if I would be there.",
         right="If I were you, I would call him.", category='Tense', confidence=0.93,
         more_pos=[("I would apologize if I would be in your position.", "I would apologize if I were in your position.")])
    verbs = "have|need|require|receive|encounter|face|experience|get|find|notice"
    rule("tense.time_clause.if_initial_state",
         rf"(?im)(?:^|[.!?] )If (?:you|they) (?P<target>will )(?:{verbs})\b[^.!?;\n]{{0,60}},",
         "", "After “if” a possible future event takes the present tense, without “will”: “If you have any questions, …”.",
         "If you will have any questions, please call me.",
         "If you have any questions, please call me. If you will follow me, I will show you the room. Let me know if you will need anything.",
         right="If you have any questions, please call me.", category='Tense', confidence=0.93,
         more_pos=[("If they will need more time, we can extend the deadline.",
                    "If they need more time, we can extend the deadline.")])
