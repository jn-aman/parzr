"""Formal or jargon verb phrases with a plain verb: utilize, commence, leverage, touch base, tendency, ability..."""
from core import rule

S = "Style"
Q = lambda s: s.replace("'", "’")
def forms(base_id, items, cat, conf, reason, family):
    """items: (suffix id, pattern, replacement, positive, negative, expect)"""
    for sid, pat, rep, pos, neg, exp in items:
        rule(f"{base_id}.{sid}", pat, rep, cat, conf, reason, pos, neg, exp, family)

def build():
    # ---- utilize -------------------------------------------------------------------------------
    r = "“Use” is plainer than “utilize”."
    forms("verb.utilize", [
        ("base", r"(?i)\b(?P<target>utilise)\b", "use", "We utilise cookies to remember your choices.",
         "The utilization rate is 80 percent. We use cookies to remember your choices.", "We use cookies to remember your choices."),
        ("s", r"(?i)\b(?P<target>utili[sz]es)\b", "uses", "The app utilizes your location.",
         "The app uses your location.", "The app uses your location."),
        ("ed", r"(?i)\b(?P<target>utilised)\b", "used", "The team utilised a spreadsheet.",
         "The team used a spreadsheet.", "The team used a spreadsheet."),
        ("ing", r"(?i)\b(?P<target>utili[sz]ing)\b", "using", "We saved time by utilizing templates.",
         "We saved time by using templates.", "We saved time by using templates."),
    ], S, 0.72, r, "verb")
    # ---- commence ------------------------------------------------------------------------------
    r = "“Start” or “begin” is plainer than “commence”."
    forms("verb.commence", [
        ("base", r"(?i)\b(?P<target>commence)\b", "start", "The meeting will commence at noon.",
         "The commencement speech was short. The meeting will start at noon.", "The meeting will start at noon."),
        ("s", r"(?i)\b(?P<target>commences)\b", "starts", "The course commences on Monday.",
         "The course starts on Monday.", "The course starts on Monday."),
        ("ed", r"(?i)\b(?P<target>commenced)\b", "started", "Work commenced in May.",
         "Work started in May.", "Work started in May."),
        ("ing", r"(?i)\b(?P<target>commencing)\b", "starting", "Commencing next week, the shop opens at nine.",
         "Starting next week, the shop opens at nine.", "Starting next week, the shop opens at nine."),
    ], S, 0.68, r, "verb")
    # ---- endeavor ------------------------------------------------------------------------------
    r = "“Try” is plainer than “endeavor”."
    ctx = r"(?:we|I|you|they|will|shall|would|can|could|must|should|always|to)"
    forms("verb.endeavor", [
        ("base", rf"(?i)\b{ctx}\s+(?P<target>endeavou?r) to\b", "try", "We endeavor to reply within a day.",
         "His endeavor to win failed. We try to reply within a day.", "We try to reply within a day."),
        ("s", r"(?i)\b(?:he|she|it|who|which|that|team|company|firm)\s+(?P<target>endeavou?rs) to\b", "tries", "The firm endeavours to reply within a day.",
         "The firm tries to reply within a day.", "The firm tries to reply within a day."),
        ("ed", r"(?i)\b(?:we|I|you|they|he|she|it|who|that)\s+(?P<target>endeavou?red) to\b", "tried", "We endeavored to reply within a day.",
         "We tried to reply within a day.", "We tried to reply within a day."),
    ], S, 0.7, r, "verb")
    # ---- ascertain -----------------------------------------------------------------------------
    r = "“Find out” is plainer than “ascertain”."
    forms("verb.ascertain", [
        ("base", r"(?i)\b(?:to|will|shall|would|can|could|must|should|we|I|you|they)\s+(?P<target>ascertain)\b", "find out", "We need to ascertain whether the file is safe.",
         "The ascertained facts agree. We need to find out whether the file is safe.", "We need to find out whether the file is safe."),
        ("ed", r"(?i)\b(?:we|I|you|they|he|she|it|has|have|had|was|were|been)\s+(?P<target>ascertained)\b", "found out", "We ascertained that the file was safe.",
         "The ascertained facts agree. We found out that the file was safe.", "We found out that the file was safe."),
        ("ing", r"(?i)\b(?P<target>ascertaining)\b", "finding out", "She is ascertaining whether the file is safe.",
         "She is finding out whether the file is safe.", "She is finding out whether the file is safe."),
    ], S, 0.7, r, "verb")
    # ---- leverage as a verb --------------------------------------------------------------------
    obj = r"(?:our|your|the|their|my|his|her|its|these|those|this|that|a|an|existing|new|all|data|AI|cloud|technology|expertise|experience|insights|strengths)"
    r = "“Leverage” as a verb is jargon; “use” is plainer."
    forms("verb.leverage", [
        ("base", rf"(?i)\b(?:to|will|would|can|could|should|must|may|might|shall|we|you|they|I|let['’]s|please)\s+(?P<target>leverage)\s+{obj}\b", "use",
         "We can leverage our existing data.", "She has leverage over the vendor. We can use our existing data.", "We can use our existing data."),
        ("s", rf"(?i)\b(?P<target>leverages)\s+{obj}\b", "uses",
         "The tool leverages your calendar.", "The tool uses your calendar.", "The tool uses your calendar."),
        ("ed", rf"(?i)\b(?:we|they|I|you|he|she|it|who|that|has|have|had|was|were)\s+(?P<target>leveraged)\s+{obj}\b", "used",
         "We leveraged our network to find staff.", "It is a highly leveraged firm. We used our network to find staff.", "We used our network to find staff."),
        ("ing", rf"(?i)\b(?P<target>leveraging)\s+{obj}\b", "using",
         "We cut costs by leveraging the cloud.", "We cut costs by using the cloud.", "We cut costs by using the cloud."),
    ], S, 0.62, r, "verb")
    # ---- touch base / circle back --------------------------------------------------------------
    tail = r"(?:\s+(?:with|on|about|again|soon|later|briefly|offline|regularly|tomorrow|today|next|this|after|every|each|quickly|once|when|and)\b|\s*[.,;!?]|\s*$)"
    r = "“Check in” is plainer than “touch base”."
    forms("verb.touch_base", [
        ("base", rf"(?i)\b(?P<target>touch base){tail}", "check in", "Let us touch base with the vendor tomorrow.",
         "The runner must touch the base. A touch-base meeting is set. Let us check in with the vendor tomorrow.", "Let us check in with the vendor tomorrow."),
        ("ed", rf"(?i)\b(?P<target>touched base){tail}", "checked in", "I touched base with the vendor yesterday.",
         "I checked in with the vendor yesterday.", "I checked in with the vendor yesterday."),
        ("ing", rf"(?i)\b(?P<target>touching base){tail}", "checking in", "I am touching base with the vendor today.",
         "I am checking in with the vendor today.", "I am checking in with the vendor today."),
    ], S, 0.62, r, "verb")
    to_obj = r"(?:you|this|that|it|them|your|our|my|these|those|the (?:topic|issue|question|proposal|discussion|plan|agenda|budget|contract))\b"
    other = r"(?:with (?:you|him|her|them|the team|everyone|everybody)|on (?:this|that|these|those|your|our|my|the (?:topic|issue|question|proposal|discussion|plan|agenda|budget|contract|invoice|thread))|later|tomorrow|next (?:week|month|quarter|year|time)|soon|shortly)\b"
    r = "“Circle back” is jargon; say what you will do."
    forms("verb.circle_back", [
        ("to", rf"(?i)\b(?P<target>circle back) to {to_obj}", "return",
         "I will circle back to this after lunch.", "The plane will circle back to the airport. I will return to this after lunch.", "I will return to this after lunch."),
        ("on", rf"(?i)\b(?P<target>circle back) {other}", "follow up",
         "I will circle back with you tomorrow.", "The plane will circle back toward the airport. I will follow up with you tomorrow.", "I will follow up with you tomorrow."),
        ("ed_to", rf"(?i)\b(?P<target>circled back) to {to_obj}", "returned",
         "We circled back to this after lunch.", "The plane circled back to the airport. We returned to this after lunch.", "We returned to this after lunch."),
        ("ed", rf"(?i)\b(?P<target>circled back) {other}", "followed up",
         "She circled back with the team on Friday.", "The drone circled back toward us. She followed up with the team on Friday.", "She followed up with the team on Friday."),
        ("ing_to", rf"(?i)\b(?P<target>circling back) to {to_obj}", "returning",
         "I am circling back to this thread.", "The plane is circling back to the airport. I am returning to this thread.", "I am returning to this thread."),
        ("ing", rf"(?i)\b(?P<target>circling back) {other}", "following up",
         "I am circling back on the invoice.", "The plane is circling back toward the field. I am following up on the invoice.", "I am following up on the invoice."),
    ], S, 0.62, r, "verb")
    # ---- make use of ---------------------------------------------------------------------------
    r = "One verb says it: “use”, not “make use of”."
    forms("verb.make_use_of", [
        ("make", r"(?i)\b(?P<target>make use of)\b", "use", "You can make use of the free trial.",
         "You can make good use of the trial. You can use the free trial.", "You can use the free trial."),
        ("makes", r"(?i)\b(?P<target>makes use of)\b", "uses", "She makes use of the free trial.",
         "She uses the free trial.", "She uses the free trial."),
        ("made", r"(?i)\b(?P<target>made use of)\b", "used", "They made use of the free trial.",
         "They used the free trial.", "They used the free trial."),
        ("making", r"(?i)\b(?P<target>making use of)\b", "using", "By making use of the free trial, you save money.",
         "By using the free trial, you save money.", "By using the free trial, you save money."),
    ], S, 0.7, r, "verb")
    # ---- take into consideration ---------------------------------------------------------------
    r = "“Consider” is shorter than “take into consideration”."
    forms("verb.take_into_consideration", [
        ("take", r"(?i)\b(?P<target>take into consideration)\b", "consider", "Please take into consideration the risks.",
         "Please take the risks into consideration. Please consider the risks.", "Please consider the risks."),
        ("takes", r"(?i)\b(?P<target>takes into consideration)\b", "considers", "The model takes into consideration your age.",
         "The model considers your age.", "The model considers your age."),
        ("took_taken", r"(?i)\b(?P<target>took into consideration|taken into consideration)\b", "considered", "All factors were taken into consideration.",
         "All factors were considered.", "All factors were considered."),
        ("taking", r"(?i)\b(?P<target>taking into consideration)\b", "considering", "Taking into consideration the cost, we agreed.",
         "Considering the cost, we agreed.", "Considering the cost, we agreed."),
    ], S, 0.7, r, "verb")
    # ---- has a tendency to ---------------------------------------------------------------------
    r = "“Tend to” is shorter than “have a tendency to”."
    forms("verb.tendency", [
        ("have", r"(?i)\b(?P<target>have (?:a|the) tendency to)\b", "tend to", "Large teams have a tendency to split into groups.",
         "A tendency to overspend is common. Large teams tend to split into groups.", "Large teams tend to split into groups."),
        ("has", r"(?i)\b(?P<target>has (?:a|the) tendency to)\b", "tends to", "The system has a tendency to stall.",
         "The system tends to stall.", "The system tends to stall."),
        ("had", r"(?i)\b(?P<target>had (?:a|the) tendency to)\b", "tended to", "He had a tendency to interrupt.",
         "He tended to interrupt.", "He tended to interrupt."),
        ("having", r"(?i)\b(?P<target>having (?:a|the) tendency to)\b", "tending to", "Having a tendency to stall, the system needs care.",
         "Tending to stall, the system needs care.", "Tending to stall, the system needs care."),
    ], S, 0.72, r, "verb")
    # ---- has the ability to --------------------------------------------------------------------
    r = "“Can” is shorter than “has the ability to”."
    forms("verb.ability", [
        ("has", r"(?i)\b(?P<target>has the (?:ability|capability|capacity) to)\b", "can", "The app has the capability to sync files.",
         "Gaining the ability to sync files matters. The app can sync files.", "The app can sync files."),
        ("have", r"(?i)(?:^|[.!?,;:]\s+|\b(?:and|but|that|if|because|as|when|since|so|then|while|although|though|whereas)\s+)(?:I|we|you|they)\s+(?P<target>have the (?:ability|capability|capacity) to)\b", "can",
         "We have the ability to sync files.", "Do you have the ability to sync files? We can sync files.", "We can sync files."),
        ("had", r"(?i)(?:^|[.!?,;:]\s+|\b(?:and|but|that|if|because|as|when|since|so|then|while|although|though|whereas|wish)\s+)(?:I|we|you|they|he|she)\s+(?P<target>had the (?:ability|capability|capacity) to)\b", "could",
         "If we had the ability to sync files, we would.", "Did you have the ability to sync? If we could sync files, we would.", "If we could sync files, we would."),
    ], S, 0.7, r, "verb")
    # ---- in a position to ----------------------------------------------------------------------
    pv = r"(?:help|offer|provide|give|assist|support|confirm|share|advise|accept|take|make|meet|deliver|ship|send|commit|answer|respond|supply|approve|process|handle|discuss|comment|say|promise|guarantee|pay|fund|cover|release|announce|finalize|finalise|proceed|start|begin|speak|reply|issue|grant|extend)\b"
    r = "“Can” is shorter than “is in a position to”."
    forms("verb.position", [
        ("present", rf"(?i)\b(?P<target>(?:am|are|is) in a position to)\s+{pv}", "can", "We are in a position to offer a discount.",
         "The chair is in a position to the left of the desk. We can offer a discount.", "We can offer a discount."),
        ("past", rf"(?i)\b(?P<target>(?:was|were) in a position to)\s+{pv}", "could", "She was in a position to help.",
         "She could help.", "She could help."),
    ], S, 0.7, r, "verb")
    # ---- receipt -------------------------------------------------------------------------------
    forms("verb.receipt", [
        ("in_receipt", r"(?i)\b(?P<target>(?P<s>I|we) (?:am|are) in receipt of)\b", "${s} have received", "We are in receipt of your letter.",
         "Anyone in receipt of the letter should reply. We have received your letter.", "We have received your letter."),
        ("acknowledge", r"(?i)\b(?:I|we)\s+(?P<target>acknowledge receipt of)\b", "have received", "We acknowledge receipt of your payment.",
         "Please acknowledge receipt of this form. We have received your payment.", "We have received your payment."),
    ], S, 0.72, "“I have received” is plainer than “I am in receipt of”.", "verb")
    # ---- is of the opinion that ----------------------------------------------------------------
    r = "“Think” is shorter than “be of the opinion”."
    forms("verb.opinion", [
        ("are", r"(?i)\b(?P<target>(?:am|are) of the (?:opinion|view) that)\b", "think that", "We are of the opinion that the plan is sound.",
         "Are you of the opinion that it works? We think that the plan is sound.", "We think that the plan is sound."),
        ("is", r"(?i)\b(?P<target>is of the (?:opinion|view) that)\b", "thinks that", "The board is of the opinion that the plan is sound.",
         "The board thinks that the plan is sound.", "The board thinks that the plan is sound."),
        ("was", r"(?i)\b(?P<target>(?:was|were) of the (?:opinion|view) that)\b", "thought that", "She was of the opinion that the plan was sound.",
         "She thought that the plan was sound.", "She thought that the plan was sound."),
    ], S, 0.72, r, "verb")
    # ---- it is my understanding / belief / hope / intention ------------------------------------
    for who, subj in (("my", "I"), ("our", "we")):
        for noun, verb, conj, ex in (("understanding", "understand", "that", "the order shipped"),
                                      ("belief", "believe", "that", "the order shipped"),
                                      ("hope", "hope", "that", "the order ships soon")):
            Cap = subj
            rule(f"verb.it_is_{who}_{noun}", rf"(?i)\b(?P<target>it is {who} {noun} that)\b", f"{subj} {verb} that", S, 0.72,
                 f"“{subj} {verb} that” is shorter than “it is {who} {noun} that”.",
                 f"It is {who} {noun} that {ex}.",
                 f"The {noun} is that {ex}. {subj} {verb} that {ex}.",
                 f"{subj[0].upper() + subj[1:]} {verb} that {ex}.", "verb")
        rule(f"verb.it_is_{who}_intention", rf"(?i)\b(?P<target>it is {who} intention to)\b", f"{subj} intend to", S, 0.72,
             f"“{subj} intend to” is shorter than “it is {who} intention to”.",
             f"It is {who} intention to reply by Friday.",
             f"{subj} intend to reply by Friday. His intention to leave was clear.",
             f"{subj[0].upper() + subj[1:]} intend to reply by Friday.", "verb")
    # ---- it would be appreciated ---------------------------------------------------------------
    rule("verb.would_be_appreciated",
         r"(?i)\b(?P<target>it would be (?P<adv>greatly |really |truly |highly |deeply |very much )?appreciated if)\b", "I would ${adv}appreciate it if", S, 0.72,
         "“I would appreciate it if” is direct and personal.",
         "It would be greatly appreciated if you could reply today.",
         "I would greatly appreciate it if you could reply today. Your help is appreciated.",
         "I would greatly appreciate it if you could reply today.", "verb")
    # ---- in agreement / in need of / in possession of ------------------------------------------
    r = "“Agree” is shorter than “be in agreement”."
    forms("verb.agreement", [
        ("are", r"(?i)\b(?P<target>(?:am|are) in agreement with)\b", "agree with", "We are in agreement with the proposal.",
         "Are you in agreement with the proposal? We agree with the proposal.", "We agree with the proposal."),
        ("is", r"(?i)\b(?P<target>is in agreement with)\b", "agrees with", "The board is in agreement with the proposal.",
         "The board agrees with the proposal.", "The board agrees with the proposal."),
        ("was", r"(?i)\b(?P<target>(?:was|were) in agreement with)\b", "agreed with", "They were in agreement with the proposal.",
         "They agreed with the proposal.", "They agreed with the proposal."),
    ], S, 0.72, r, "verb")
    r = "“Need” is shorter than “be in need of”."
    forms("verb.need_of", [
        ("are", r"(?i)\b(?P<target>(?:am|are) in need of)\b", "need", "We are in need of a new printer.",
         "Teams in need of help should call. We need a new printer.", "We need a new printer."),
        ("is", r"(?i)\b(?P<target>is in need of)\b", "needs", "The office is in need of a new printer.",
         "The office needs a new printer.", "The office needs a new printer."),
        ("was", r"(?i)\b(?P<target>(?:was|were) in need of)\b", "needed", "The office was in need of a new printer.",
         "The office needed a new printer.", "The office needed a new printer."),
    ], S, 0.7, r, "verb")
    r = "“Have” is shorter than “be in possession of”."
    forms("verb.possession", [
        ("are", r"(?i)\b(?P<target>(?:am|are) in possession of)\b", "have", "We are in possession of the signed contract.",
         "The man in possession of the key left. We have the signed contract.", "We have the signed contract."),
        ("is", r"(?i)\b(?P<target>is in possession of)\b", "has", "The bank is in possession of the signed contract.",
         "The bank has the signed contract.", "The bank has the signed contract."),
    ], S, 0.7, r, "verb")
    # ---- make an attempt / come to the conclusion ----------------------------------------------
    r = "“Try” is shorter than “make an attempt”."
    forms("verb.attempt", [
        ("make", r"(?i)\b(?P<target>make an attempt to)\b", "try to", "Please make an attempt to reply today.",
         "An attempt to reply failed. Please try to reply today.", "Please try to reply today."),
        ("makes", r"(?i)\b(?P<target>makes an attempt to)\b", "tries to", "She makes an attempt to reply daily.",
         "She tries to reply daily.", "She tries to reply daily."),
        ("made", r"(?i)\b(?P<target>made an attempt to)\b", "tried to", "He made an attempt to reply.",
         "He tried to reply.", "He tried to reply."),
        ("making", r"(?i)\b(?P<target>making an attempt to)\b", "trying to", "She is making an attempt to reply.",
         "She is trying to reply.", "She is trying to reply."),
    ], S, 0.7, r, "verb")
    r = "“Conclude” is shorter than “come to the conclusion”."
    forms("verb.conclusion", [
        ("come", r"(?i)\b(?P<target>come to the conclusion that)\b", "conclude that", "We may come to the conclusion that the plan failed.",
         "We may conclude that the plan failed.", "We may conclude that the plan failed."),
        ("came", r"(?i)\b(?P<target>came to the conclusion that)\b", "concluded that", "The panel came to the conclusion that the plan failed.",
         "The panel concluded that the plan failed.", "The panel concluded that the plan failed."),
        ("comes", r"(?i)\b(?P<target>comes to the conclusion that)\b", "concludes that", "The panel comes to the conclusion that the plan failed.",
         "The panel concludes that the plan failed.", "The panel concludes that the plan failed."),
    ], S, 0.7, r, "verb")
