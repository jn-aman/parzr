# Generates the synthetic name stress corpus. Names authored from common public knowledge
# (popular given/family names per culture); no real private data. Seeded for reproducibility.
import json, random, unicodedata, os

HERE = os.path.dirname(os.path.abspath(__file__))
R = random.Random(1497)

# culture -> (given names, family names)
C = {
 "indian_hindi": ("aarav vivaan sneha komal aman rahul priya anjali rohit neha vikas pooja sanjay sunita ankit kavya arjun ishaan manish deepak ritu sachin gaurav nikhil shweta abhishek".split(),
                  "jain sharma verma gupta agarwal mishra tiwari pandey".split()),
 "indian_tamil": ("tamilselvan kalaivani ilango karthik priyanka senthil lakshmi murugan divya arun meena ramesh gayathri vignesh saravanan selvi anbu kavitha balaji".split(),
                  "subramaniam krishnan venkatesan raman natarajan iyer".split()),
 "indian_telugu": ("sai ravi teja srinivas lavanya venkat sravani naveen bhavani chaitanya keerthi raju sirisha harsha tejaswi praveen mounika".split(),
                   "reddy naidu rao chowdary varma raju".split()),
 "indian_bengali": ("rituparna anirban sourav ananya debashish moumita arnab riya subhash tanmoy sayantani indranil paromita joydeep".split(),
                    "banerjee chatterjee mukherjee ganguly bose das sen ghosh".split()),
 "indian_punjabi": ("rajveer tejinder gurpreet harpreet jaspreet manpreet simran amrit navjot balwinder kuldeep jasleen harjit".split(),
                    "singh kaur gill sandhu dhillon sidhu grewal".split()),
 "indian_marathi": ("shreyas mrunal aditya shruti omkar sayali tejas prajakta mandar ketaki swapnil madhura aniket".split(),
                    "deshpande kulkarni joshi patil gokhale apte".split()),
 "indian_gujarati": ("jignesh khushbu hardik dhruv krupa jigar bhavin hetal nirav foram mitesh parth".split(),
                     "patel shah mehta desai parikh trivedi".split()),
 "indian_malayalam": ("arjun manju anoop sreeja jithin aswathy vineeth resmi biju anjana sreekumar nithya".split(),
                      "nair menon pillai kurup panicker".split()),
 "chinese_pinyin": ("xiaoling jianguo meiling zhen wei fang jing lei xiaoming yan hui qiang xin jun li na ming chen zhiwei xiulan yong haoran yuxuan zihan".split(),
                    "wang zhang liu chen yang huang zhao wu zhou xu".split()),
 "japanese": ("kazuki mei shota ayaka haruto yui sota hina ren aoi yuto riko takeshi yuki kenji akiko hiroshi sakura daiki emi kaito naoko".split(),
              "sato suzuki takahashi tanaka watanabe ito yamamoto nakamura kobayashi".split()),
 "korean": ("seojun haeun minjun seoyeon jiho jiwoo hyun jisoo minseo doyun sungmin eunji jaehyun yerin taeyang hana".split(),
            "kim lee park choi jung kang cho yoon jang".split()),
 "arabic_persian": ("ibrahim hamid soraya amir ahmed fatima omar aisha yusuf layla khalid mariam hassan zainab tariq noor karim samira reza dariush parisa shirin farhad navid mehdi leila".split(),
                    "khan hussain rahman haddad nasser al-farsi tehrani hosseini rahimi".split()),
 "yoruba": ("damilola tunde adebayo olumide folake ayodele temitope oluwaseun kehinde taiwo yetunde babatunde adeola funmilayo".split(),
            "adeyemi ogunleye adebayo oyelaran akinola".split()),
 "igbo": ("nkechi chukwuemeka chidi chiamaka emeka ngozi obinna adaeze ifeanyi uchenna chinwe nnamdi kelechi amaka".split(),
          "okonkwo okafor eze nwosu obi okoye".split()),
 "swahili": ("wanjiku kioko baraka imani juma amani zawadi neema rehema jabari faraji asha bahati".split(),
             "mwangi otieno wanjiru kamau njoroge achieng".split()),
 "slavic": ("mikhail anastasia tomasz dmitri svetlana ivan natasha olga sergei katya pavel milan jelena bogdan zoran agnieszka wojciech radek vlad".split(),
            "ivanov petrova kowalski novak horvat smirnov popescu jovanovic".split()),
 "spanish_portuguese": ("pilar gonzalo alejandro lucia mateo valentina santiago camila diego ximena joao thiago beatriz rodrigo ines guadalupe nuno".split(),
                        "garcia rodriguez martinez fernandez gonzalez silva santos pereira oliveira".split()),
 "german_dutch": ("jurgen wim lukas jonas hannah lena maximilian anke joost sanne pieter femke wouter dirk".split(),
                  ["van der berg", "de vries", "van dijk", "von trapp", "ter horst", "van den bosch", "schmidt", "zu hohenlohe"]),
 "irish": ("declan grainne siobhan niamh aoife ciaran padraig saoirse oisin eoin caoimhe".split(),
           ["o'brien", "o'neill", "mccarthy", "mcdonagh", "o'sullivan", "mcguinness", "o'connor"]),
 "hyphenated": ["jean-luc", "anne-marie", "mary-kate", "jean-paul", "ji-hoon", "seo-yeon", "marie-claire", "jae-won"],
 "diacritics": ("josé zoë françois björn søren łukasz ångström renée chloé maël andrés nuño müller gaël inês joão ştefan dvořák".split(),
                "müller núñez lópez gómez dvořák šimić łopatka jørgensen".split()),
 "english_common_word": ("will mark grace hope joy rose bill dawn sunny rich faith june may april summer chase hunter rowan reed sky".split(),
                         "jain bush rich hill wood king".split()),
 "english_ssa": ("isaac nathan lily nora zoey layla riley camila penelope sebastian jackson aiden owen wyatt grayson leo carter mason logan ella aria scarlett liam olivia noah emma oliver charlotte elijah amelia james ava benjamin sophia lucas isabella henry mia theodore evelyn harper ethan".split(),
                 "smith johnson williams brown jones miller davis wilson".split()),
}
C["hyphenated"] = (C["hyphenated"], ["smith-jones", "garcia-lopez", "lloyd-webber", "bonham-carter", "taylor-wood"])

def cap(s):  # capitalize each word part, keep particles lowercase in family names
    parts = []
    for w in s.split(" "):
        if w in ("van", "der", "de", "von", "ter", "den", "zu", "al"):
            parts.append(w); continue
        w = "-".join(p[:1].upper() + p[1:] for p in w.split("-"))
        if w.startswith("O'"): w = "O'" + w[2:3].upper() + w[3:]
        if w.startswith("Mc"): w = "Mc" + w[2:3].upper() + w[3:]
        if w.startswith("Al-"): w = "al-" + w[3:]
        parts.append(w)
    return " ".join(parts)

def ascii_fold(s):
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().replace("'", "").replace(" ", "")

# Templates: {n} given, {f} family, {n2} {n3} other given. Context label, template.
T = [
 ("greeting", "hi {n}, can you send the report today?"),
 ("greeting", "Hey {n}! Long time no see."),
 ("signoff", "That works for me.\nthanks, {n}"),
 ("signoff", "See you at the standup tomorrow.\n\nRegards,\n{n}"),
 ("vocative", "Could you review this before lunch, {n}?"),
 ("vocative", "{n}, could you review this before lunch?"),
 ("subject", "I think {n} said the meeting moved to Friday."),
 ("subject_line_start", "{n} said the meeting moved to Friday."),
 ("object", "Please ask {n} about the budget."),
 ("object", "We should invite {n} to the planning call."),
 ("copula_prep", "This is {n} from the design team."),
 ("copula_prep", "I had lunch with {n} yesterday."),
 ("possessive", "I borrowed {n}'s laptop for the demo."),
 ("list", "{n}, {n2} and {n3} will join the call."),
 ("list", "The new team includes {n}, {n2} and {n3}."),
 ("fullname", "I met {n} {f} at the conference yesterday."),
 ("fullname", "it is {n} {f} here, just checking in."),
 ("mention", "@{n} can you take a look at this?"),
 ("mention", "Looping in @{n} for visibility."),
 ("email", "Send it to {e} when ready."),
 ("alone_line", "Thanks for the update.\n{n}"),
]

def utf16(s, i): return len(s[:i].encode("utf-16-le")) // 2

def render(tpl, vals):
    # returns text and list of name spans (utf16) for every filled slot
    out, spans, i = "", [], 0
    while i < len(tpl):
        if tpl[i] == "{":
            j = tpl.index("}", i); key = tpl[i+1:j]; v = vals[key]
            s = len(out); out += v
            if key == "n" and i > 0 and tpl[i-1] == "@": s -= 1  # include the @
            spans.append((utf16(out, s), utf16(out, len(out)), v))
            i = j + 1
        else:
            out += tpl[i]; i += 1
    return out, spans

rows, seen = [], set()
all_given = [(c, g) for c, (gs, _) in C.items() for g in gs]
def add(row):
    if row["text"] in seen: return
    seen.add(row["text"]); row["id"] = len(rows); rows.append(row)

for culture, (gs, fs) in C.items():
    others = [g for g in gs]
    for g in gs:
        # every name: 6 random contexts (+ all contexts for common-word names), in lower and Capitalized
        tpls = T if culture == "english_common_word" else R.sample(T, 6)
        for ctx, tpl in tpls:
            f = R.choice(fs)
            n2, n3 = R.sample([o for o in others if o != g], 2)
            for case in ("lower", "cap"):
                tr = (lambda s: s) if case == "lower" else cap
                vals = {"n": tr(g), "f": tr(f), "n2": tr(n2), "n3": tr(n3),
                        "e": f"{ascii_fold(g).lower()}.{ascii_fold(f).lower()}@example.com"}
                text, spans = render(tpl, vals)
                add(dict(set="name", culture=culture, context=ctx, case=case, name=g, text=text, spans=spans))
        # all caps: name in caps inside a normal sentence, plus one shouted sentence
        ctx, tpl = R.choice(T[:13])
        text, spans = render(tpl, {"n": g.upper(), "f": "", "n2": "", "n3": "", "e": ""})
        add(dict(set="name", culture=culture, context=ctx, case="allcaps", name=g, text=text, spans=spans))
        text, spans = render("PLEASE ASK {n} TO CALL ME BACK", {"n": g.upper()})
        add(dict(set="name", culture=culture, context="object", case="allcaps", name=g, text=text, spans=spans))

# Controls: real misspellings (several name-like: short, lowercase, unknown) that must still be fixed.
CTRL = [
 ("recieve", "receive", "did you {w} my message?"), ("teh", "the", "can you send {w} report today?"),
 ("adress", "address", "what is your {w} again?"), ("thier", "their", "they forgot {w} keys at home."),
 ("jion", "join", "can you {w} the call at noon?"), ("definately", "definitely", "i will {w} be there."),
 ("seperate", "separate", "keep the files in a {w} folder."), ("occured", "occurred", "the error {w} twice today."),
 ("untill", "until", "wait {w} friday please."), ("wich", "which", "{w} file did you open?"),
 ("becuase", "because", "i left early {w} of the rain."), ("beleive", "believe", "i {w} we can ship it."),
 ("freind", "friend", "my {w} is visiting this week."), ("goverment", "government", "the {w} released new rules."),
 ("tommorow", "tomorrow", "let's meet {w} morning."), ("accomodate", "accommodate", "we can {w} two more people."),
 ("acheive", "achieve", "we will {w} the goal soon."), ("arguement", "argument", "that was a strong {w}."),
 ("begining", "beginning", "start from the {w} please."), ("calender", "calendar", "check your {w} for monday."),
 ("collegue", "colleague", "my {w} sent the draft."), ("comming", "coming", "are you {w} to the party?"),
 ("existance", "existence", "i did not know of its {w}."), ("finaly", "finally", "we {w} fixed the bug."),
 ("foriegn", "foreign", "she speaks a {w} language."), ("happend", "happened", "what {w} at the meeting?"),
 ("immediatly", "immediately", "please reply {w}."), ("independant", "independent", "he is an {w} consultant."),
 ("knowlege", "knowledge", "she has deep {w} of the system."), ("neccessary", "necessary", "is that really {w}?"),
 ("noticable", "noticeable", "the change is barely {w}."), ("persue", "pursue", "i want to {w} this idea."),
 ("prefered", "preferred", "my {w} option is the second one."), ("realy", "really", "that was {w} helpful."),
 ("recomend", "recommend", "i {w} the blue one."), ("relevent", "relevant", "send me the {w} files."),
 ("rember", "remember", "do you {w} the password?"), ("resturant", "restaurant", "the {w} was full."),
 ("shedule", "schedule", "can you share the {w}?"), ("succesful", "successful", "the launch was {w}."),
 ("suprise", "surprise", "it was a nice {w}."), ("truely", "truly", "i am {w} sorry."),
 ("wierd", "weird", "that sounds {w} to me."), ("writting", "writing", "i am {w} the summary now."),
 ("adn", "and", "bring the charger {w} the cable."), ("hte", "the", "open {w} door please."),
 ("yuor", "your", "send me {w} notes."), ("waht", "what", "{w} time is the call?"),
 ("taht", "that", "i think {w} is fine."), ("wiht", "with", "come {w} me to the store."),
 ("abotu", "about", "tell me {w} the trip."), ("becasue", "because", "i stayed {w} it rained."),
 ("thsi", "this", "is {w} the right file?"), ("jsut", "just", "i {w} sent it."),
 ("agian", "again", "can you try {w}?"), ("ammount", "amount", "check the {w} on the invoice."),
 ("mesage", "message", "i got your {w}."), ("reciept", "receipt", "keep the {w} for taxes."),
 ("sumary", "summary", "please write a short {w}."), ("meating", "meeting", "the {w} starts at ten."),
 ("anwser", "answer", "i need an {w} by noon."), ("sned", "send", "can you {w} it again?"),
 ("plase", "please", "{w} call me back."), ("maek", "make", "let's {w} a plan."),
 ("chnage", "change", "we need to {w} the date."), ("wnat", "want", "do you {w} coffee?"),
 ("knwo", "know", "i don't {w} the answer."), ("thnak", "thank", "{w} you for the help."),
 ("whit", "with", "go {w} her to the office."), ("tiem", "time", "what {w} works for you?"),
 ("woudl", "would", "i {w} like that."), ("coudl", "could", "you {w} ask the team."),
 ("shoudl", "should", "we {w} leave now."), ("peopel", "people", "many {w} came to the event."),
 ("probaly", "probably", "it will {w} rain."), ("tomorow", "tomorrow", "see you {w}."),
 ("yesturday", "yesterday", "i saw it {w}."), ("buisness", "business", "how is the {w} going?"),
 ("enviroment", "environment", "the test {w} is down."), ("experiance", "experience", "she has a lot of {w}."),
 ("intrest", "interest", "thanks for your {w}."), ("libary", "library", "i went to the {w}."),
 ("oppurtunity", "opportunity", "this is a great {w}."), ("propably", "probably", "he is {w} late."),
 ("questoin", "question", "i have one {w}."), ("availble", "available", "is the room {w}?"),
 ("diffrent", "different", "try a {w} approach."), ("emial", "email", "send me an {w}."),
 ("mangaer", "manager", "my {w} approved it."), ("intial", "initial", "the {w} draft is ready."),
 ("documnet", "document", "share the {w} with me."), ("problme", "problem", "there is a {w} with the build."),
 ("teh", "the", "thanks for {w} quick reply."), ("jion", "join", "please {w} us for dinner."),
 ("adress", "address", "update the {w} on file."), ("thier", "their", "ask them for {w} input."),
 ("recieve", "receive", "you will {w} a link."), ("wich", "which", "tell me {w} one you like."),
 ("garantee", "guarantee", "we {w} delivery by monday."), ("hapy", "happy", "i am {w} with it."), ("lenght", "length", "check the {w} of the text."), ("strenght", "strength", "that is our main {w}."),
]
for k, (typo, fix, tpl) in enumerate(CTRL):
    base = tpl.replace("{w}", typo)
    for variant, text in (("plain", base[0].upper() + base[1:] if k % 2 else base),
                          ("greeting_prefix", "hi, " + base),
                          ("signoff_suffix", base + "\nthanks")):
        s = text.index(typo) if typo in text else text.lower().index(typo)
        add(dict(set="control", culture="control", context=variant, case="lower", name=typo, fix=fix, text=text,
                 spans=[(utf16(text, s), utf16(text, s + len(typo)), typo)]))

import sys
names = {r["name"] for r in rows if r["set"] == "name"}
with open(os.path.join(HERE, "corpus.jsonl"), "w") as fh:
    for r in rows: fh.write(json.dumps(r, ensure_ascii=False) + "\n")
fam = {f for _, (_, fs) in C.items() for f in fs}
if __name__ == "__main__": print(len(names | fam), "distinct given+family;", len(rows), "rows;", sum(r["set"] == "name" for r in rows), "name sentences;",
      sum(r["set"] == "control" for r in rows), "controls;", len(names), "distinct given names")
