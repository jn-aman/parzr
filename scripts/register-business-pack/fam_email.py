"""Email and letter stock phrases: advisories, enclosures, per/as per, going forward, kindly, thanking you."""
from core import rule

S = "Style"
def build():
    # ---- be advised / informed -----------------------------------------------------------------
    r = "Skip the wrapper and start with the news itself."
    rule("email.be_advised_start",
         r"(?im)(?:^|[.!?:]\s+|\n\s*)(?P<target>(?:(?:please|kindly)\s+)?be (?:advised|informed) that\s+(?P<w>[A-Za-z][\w'’-]*))",
         "${w}", S, 0.68, r,
         "Please be advised that the office will close early on Friday.",
         "You should be advised that fees apply. She was advised that the office closes early. The office will close early on Friday.",
         "The office will close early on Friday.", "advisory")
    rule("email.be_advised_mid",
         r"(?i)[,;]\s+(?:(?:and|but)\s+)?(?P<target>(?:please|kindly)\s+be (?:advised|informed) that\s+(?P<w>[A-Za-z][\w'’-]*))",
         "${w}", S, 0.68, r,
         "Thanks for the update, but please be advised that the office closes early.",
         "You should be advised that fees apply. Thanks for the update, but the office closes early.",
         "Thanks for the update, but the office closes early.", "advisory")
    rule("email.this_is_to_inform",
         r"(?im)(?:^|[.!?:]\s+|\n\s*)(?P<target>(?:this is to inform you that|(?:I|we) (?:am|are) writing to inform you that|(?:I|we) (?:would like|wish|want|need) to inform you that)\s+(?P<w>[A-Za-z][\w'’-]*))",
         "${w}", S, 0.62,
         "Start with the news itself; the reader knows it is a message to them.",
         "I am writing to inform you that your order has shipped.",
         "We regret to inform you that the post is filled. I am pleased to inform you that you passed. Your order has shipped.",
         "Your order has shipped.", "advisory")
    rule("email.bring_to_attention",
         r"(?i)\bto\s+(?P<target>bring to your (?:kind )?(?:notice|attention) that)\b", "tell you that", S, 0.65,
         "“Tell you that” is plainer than “bring to your attention that”.",
         "I would like to bring to your attention that the invoice is overdue.",
         "Thank you for bringing this to my attention. I would like to tell you that the invoice is overdue.",
         "I would like to tell you that the invoice is overdue.", "advisory")
    rule("email.it_should_be_noted",
         r"(?im)(?:^|[.!?:]\s+|\n\s*)(?P<target>it (?:should be noted|is important to note) that\s+(?P<w>[A-Za-z][\w'’-]*))",
         "${w}", S, 0.6,
         "Say the point directly; “it should be noted that” adds nothing.",
         "It should be noted that the fee is not refundable.",
         "Please note that the fee is not refundable. The fee is not refundable.",
         "The fee is not refundable.", "advisory")
    rule("email.take_this_opportunity",
         r"(?i)\b(?:to|will|would|can|could|shall|must|should|may|let me|let us|let['’]s|also|just|and)\s+(?P<target>take (?:this|the) opportunity to\s+)(?:thank|express|welcome|congratulate|introduce|wish|remind|apologi[sz]e|inform|extend|say|reiterate|acknowledge|appreciate|invite|update|share|announce|highlight|mention|clarify|recognize|recognise|reaffirm|confirm|offer|let)\b",
         "", S, 0.65,
         "Just say it: “I would like to thank you”.",
         "I would like to take this opportunity to thank the whole team.",
         "Take this opportunity to learn Spanish. I would like to thank the whole team.",
         "I would like to thank the whole team.", "advisory")
    # ---- per / as per --------------------------------------------------------------------------
    rule("email.as_per",
         r"(?i)\b(?P<target>as per)\s+(?:your|our|my|the|their|his|her|its|attached|company|standard|previous|prior|above|below|last|this|that|these|those|\d)",
         "per", S, 0.72,
         "“Per” or “according to” does the job of “as per”.",
         "The invoice was prepared as per your request.",
         "Everything went as per usual. The invoice was prepared per your request.",
         "The invoice was prepared per your request.", "per")
    rule("email.per_our_conversation",
         r"(?i)\b(?P<target>(?:as )?per our (?:conversation|discussion|talk|chat))(?:\s*[,.;:!?)]|\s*$|\s+(?:yesterday|today|earlier|last|this|on|in|at|just)\b)",
         "as we discussed", S, 0.72,
         "“As we discussed” is friendlier than “per our conversation”.",
         "I have updated the file per our conversation on Monday.",
         "Our conversation went well. I have updated the file as we discussed on Monday.",
         "I have updated the file as we discussed on Monday.", "per")
    # ---- enclosures ----------------------------------------------------------------------------
    for w in ("attached", "enclosed"):
        rule(f"email.{w}_please_find",
             rf"(?i)\b(?P<target>{w} please find)\s+(?:the|a|an|my|our|your|this|these|\d)",
             f"I have {w}", S, 0.65,
             f"\u201cI have {w}\u201d is plainer than \u201c{w} please find\u201d.",
             f"{w.capitalize()} please find the signed contract.",
             f"Please find the {w} contract. I have {w} the signed contract.",
             f"I have {w} the signed contract.", "enclosure")
    rule("email.attached_herewith", r"(?i)\b(?P<target>(?P<w>attached|enclosed)\s+herewith)\b", "${w}", "Redundancy", 0.78,
         "“Herewith” adds nothing after “attached”.",
         "The signed contract is attached herewith.",
         "The signed contract is attached. The herewith clause is void.",
         "The signed contract is attached.", "enclosure")
    rule("email.herewith_attached", r"(?i)\b(?P<target>herewith\s+(?P<w>attached|enclosed))\b", "${w}", "Redundancy", 0.78,
         "“Herewith” adds nothing before “attached”.",
         "Please see the contract herewith attached.",
         "Please see the contract attached.",
         "Please see the contract attached.", "enclosure")
    rule("email.verb_herewith", r"(?i)\b(?P<target>(?P<w>find|sending|sent|attaching|enclosing|forwarding|submitting)\s+herewith)\b", "${w}", "Redundancy", 0.72,
         "“Herewith” adds nothing here.",
         "I am sending herewith the signed contract.",
         "I am sending the signed contract.",
         "I am sending the signed contract.", "enclosure")
    # ---- archaic adverbs -----------------------------------------------------------------------
    rule("email.aforementioned", r"(?i)\b(?P<target>aforementioned|aforesaid|above[- ]mentioned)\b", "previously mentioned", S, 0.62,
         "“Previously mentioned” is plainer than “aforementioned”.",
         "The aforementioned report is attached.",
         "The report mentioned above is attached. The previously mentioned report is attached.",
         "The previously mentioned report is attached.", "archaic")
    rule("email.heretofore", r"(?i)\b(?P<target>heretofore)\b", "until now", S, 0.7,
         "“Until now” is plainer than “heretofore”.",
         "The policy was heretofore unwritten.",
         "The policy was until now unwritten.",
         "The policy was until now unwritten.", "archaic")
    rule("email.henceforth", r"(?i)\b(?P<target>henceforth)\b", "from now on", S, 0.7,
         "“From now on” is plainer than “henceforth”.",
         "Henceforth, all invoices go to finance.",
         "From now on, all invoices go to finance.",
         "From now on, all invoices go to finance.", "archaic")
    rule("email.forthwith", r"(?i)\b(?P<target>forthwith)\b", "immediately", S, 0.7,
         "“Immediately” is plainer than “forthwith”.",
         "Return the badge forthwith.",
         "Return the badge immediately.",
         "Return the badge immediately.", "archaic")
    # ---- going forward / moving forward --------------------------------------------------------
    for w, a in (("going", "Going"), ("moving", "Moving")):
        rule(f"email.{w}_forward",
             rf"(?im)(?:^|[.!?]\s+|,\s*)(?P<target>{w} forward)\s*(?:,|[.;!?]|$)", "from now on", S, 0.62,
             f"“{a} forward” is business filler; “from now on” says it plainly.",
             f"{a} forward, all invoices go to finance.",
             f"We are {w} forward with the plan. The car is {w} forward slowly. From now on, all invoices go to finance.",
             "From now on, all invoices go to finance.", "forward")
    # ---- kindly ----------------------------------------------------------------------------------
    kv = r"(?:send|share|confirm|provide|let|find|review|check|forward|note|reply|respond|update|ensure|make|do|see|refer|treat|consider|acknowledge|approve|arrange|attend|inform|give|submit|return|call|contact|get|help|take|read|look|add|include|accept|allow|excuse|accommodate|clarify|resend|advise|tell|bring|keep|join|visit|complete|fill|sign|process|proceed|remit|pay|cooperate|co-operate|oblige|adjust|bear|extend|grant|issue|mail|email|schedule|book|set|attach|wait|hold|be)\b"
    rule("email.kindly_imperative",
         rf"(?i)(?:^|[.!?]\s+|\n\s*|,\s+(?:and\s+|but\s+|then\s+)?|\b(?:and|then|also|but)\s+)(?P<target>kindly)\s+{kv}",
         "please", S, 0.66,
         "“Please” is the usual way to ask; “kindly” reads as stiff or curt.",
         "Kindly send me the signed contract.",
         "She spoke kindly to everyone. Kindly old Mr Lee waved. He kindly offered us a seat. Could you kindly help? Please send me the signed contract.",
         "Please send me the signed contract.", "kindly")
    rule("email.please_kindly", r"(?i)\b(?P<target>please kindly)\b", "please", "Redundancy", 0.88,
         "“Please” and “kindly” say the same thing; use one.",
         "Please kindly send me the signed contract.",
         "Please send me the signed contract. He spoke kindly, please note.",
         "Please send me the signed contract.", "kindly")
    rule("email.kindly_please", r"(?i)\b(?P<target>kindly please)\b", "please", "Redundancy", 0.88,
         "“Please” and “kindly” say the same thing; use one.",
         "Kindly please send me the signed contract.",
         "Please send me the signed contract. He spoke kindly. Please wait.",
         "Please send me the signed contract.", "kindly")
    # ---- thanking you ----------------------------------------------------------------------------
    rule("email.thanking_you", r"(?im)(?:^|[.!?]\s+)(?P<target>thanking you)\b", "Thank you", "Register", 0.76,
         "“Thank you” is the standard closing; “thanking you” is an old-fashioned form.",
         "Thanking you in advance for your help.",
         "I am thanking you for the gift. Thank you in advance for your help.",
         "Thank you in advance for your help.", "thanks")
    rule("email.thanks_in_advanced", r"(?i)\b(?:thanks|thank you) in (?P<target>advanced)\b", "advance", "Word choice", 0.95,
         "The fixed phrase is “in advance”.",
         "Thanks in advanced for your help.",
         "Thanks in advance for your help. She chose the advanced course.",
         "Thanks in advance for your help.", "thanks")
    # ---- politeness boilerplate ------------------------------------------------------------------
    rule("email.should_you",
         r"(?i)\b(?P<target>should you)\s+(?:need|require|wish|want|encounter|experience|prefer|have\s+(?:any|a|an|some|more|further|other|additional|questions?|problems?|issues?|concerns?|queries|trouble|difficult(?:y|ies)|doubts?))\b[^?.!;\n]{0,70},",
         "if you", S, 0.7,
         "“If you” is plainer than the inverted “should you”.",
         "Should you have any questions, call me.",
         "Should you need a visa? If you have any questions, call me.",
         "If you have any questions, call me.", "boilerplate")
    rule("email.do_not_hesitate",
         r"(?i)\bplease\s+(?P<target>(?:do not|don['’]t) hesitate to\s+)(?:contact|call|email|write|ask|reach|get|let|message|text|phone|visit|speak|talk)\b",
         "", S, 0.66,
         "“Please contact me” is more direct than “please do not hesitate to contact me”.",
         "Please do not hesitate to contact me with questions.",
         "Please contact me with questions. Do not hesitate to ask. They did not hesitate to act.",
         "Please contact me with questions.", "boilerplate")
    rule("email.earliest_convenience", r"(?i)\b(?P<target>at your earliest (?:possible )?convenience)\s*(?:[.!?]|$)", "when you can", S, 0.6,
         "“When you can” is friendlier than “at your earliest convenience”.",
         "Please reply at your earliest convenience.",
         "Please reply at your convenience, whether today or later. Please reply when you can.",
         "Please reply when you can.", "boilerplate")
    rule("email.under_separate_cover", r"(?i)\b(?P<target>under separate cover)\b", "separately", S, 0.75,
         "“Separately” is plainer than “under separate cover”.",
         "The invoice was sent under separate cover.",
         "The invoice was sent separately. The cover was separate.",
         "The invoice was sent separately.", "boilerplate")
    rule("email.you_are_requested_to", r"(?i)\b(?P<target>you are (?:kindly |hereby )?requested to)\b", "please", S, 0.65,
         "“Please” is plainer than “you are requested to”.",
         "You are requested to confirm your attendance.",
         "Please confirm your attendance. Who requested you to confirm?",
         "Please confirm your attendance.", "boilerplate")
    rule("email.writing_this_email",
         r"(?i)\bwriting\s+(?P<target>this (?:e-?mail|mail|letter|message)\s+)to\b", "", "Redundancy", 0.75,
         "“I am writing to” already says it is this message.",
         "I am writing this email to ask about the invoice.",
         "I am writing to ask about the invoice. I wrote this email yesterday.",
         "I am writing to ask about the invoice.", "boilerplate")
    rule("email.as_and_when", r"(?i)\b(?P<target>as and when)\b", "when", "Redundancy", 0.7,
         "“When” does the work of “as and when”.",
         "We will update the page as and when new data arrives.",
         "We will update the page when new data arrives. As soon as data arrives, we update.",
         "We will update the page when new data arrives.", "boilerplate")
    rule("email.as_of_yet",
         r"(?i)\b(?:n['’]t|not|no|never|nothing|none|nobody)\b[^.!?;\n]{0,50}\s(?P<target>as of yet)\b", "yet", "Redundancy", 0.75,
         "“Yet” does the work of “as of yet”.",
         "We have not heard back as of yet.",
         "As of yet, we are waiting. We have not heard back yet.",
         "We have not heard back yet.", "boilerplate")
    rule("email.day_and_age", r"(?i)\b(?P<target>in (?:this|today['’]s) day and age)\b", "today", S, 0.72,
         "“Today” is shorter than “in this day and age”.",
         "In this day and age, email is everywhere.",
         "Today, email is everywhere. This age and day differ.",
         "Today, email is everywhere.", "boilerplate")
    rule("email.month_of", r"(?i)\b(?P<target>the month of (?P<m>January|February|March|April|May|June|July|August|September|October|November|December))\b", "${m}", "Redundancy", 0.75,
         "The month name already says it is a month.",
         "We launch in the month of March.",
         "The month of Ramadan begins soon. We launch in March.",
         "We launch in March.", "boilerplate")
    rule("email.am_in_the_morning", r"(?i)\b\d{1,2}(?::\d{2})?\s?(?:a\.m\.|am)(?P<target>\s+in the morning)\b", "", "Redundancy", 0.85,
         "“AM” already means morning.",
         "The call starts at 9 AM in the morning.",
         "The call starts at 9 AM in Chicago. The call starts at 9 in the morning. The call starts at 9 AM.",
         "The call starts at 9 AM.", "boilerplate")
    rule("email.pm_in_the_evening", r"(?i)\b\d{1,2}(?::\d{2})?\s?(?:p\.m\.|pm)(?P<target>\s+in the (?:afternoon|evening)|\s+at night)\b", "", "Redundancy", 0.85,
         "“PM” already means afternoon or evening.",
         "The call starts at 6 PM in the evening.",
         "The call starts at 6 PM in Chicago. The call starts at 6 in the evening. The call starts at 6 PM.",
         "The call starts at 6 PM.", "boilerplate")
