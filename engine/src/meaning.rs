//! Whether a tone rewrite keeps the meaning of the sentence it rewrote. A small model sometimes
//! answers a tone request with a different sentence ("I hat it." became "It is."); every
//! rewritten sentence is compared with the corrected original word by word, and one that drops
//! or changes what it says is not offered.
use crate::{Edit, Mode, TokenHint, apply_edits, byte_at, tokenizer};

/// Words with no content of their own: pronouns, determiners, auxiliaries, prepositions and
/// conjunctions. A rewrite may add, drop or swap these freely.
const FUNCTION: &[&str] = &[
    "a",
    "an",
    "the",
    "this",
    "that",
    "these",
    "those",
    "some",
    "any",
    "each",
    "every",
    "all",
    "both",
    "either",
    "much",
    "many",
    "more",
    "most",
    "few",
    "less",
    "least",
    "other",
    "another",
    "such",
    "what",
    "which",
    "whose",
    "whatever",
    "i",
    "me",
    "my",
    "mine",
    "myself",
    "you",
    "your",
    "yours",
    "yourself",
    "yourselves",
    "he",
    "him",
    "his",
    "himself",
    "she",
    "her",
    "hers",
    "herself",
    "it",
    "its",
    "itself",
    "we",
    "us",
    "our",
    "ours",
    "ourselves",
    "they",
    "them",
    "their",
    "theirs",
    "themselves",
    "one",
    "ones",
    "someone",
    "somebody",
    "something",
    "anyone",
    "anybody",
    "anything",
    "everyone",
    "everybody",
    "everything",
    "u",
    "ur",
    "ya",
    "be",
    "am",
    "is",
    "are",
    "was",
    "were",
    "been",
    "being",
    "have",
    "has",
    "had",
    "having",
    "do",
    "does",
    "did",
    "doing",
    "will",
    "would",
    "shall",
    "should",
    "can",
    "could",
    "may",
    "might",
    "must",
    "ought",
    "gonna",
    "wanna",
    "gotta",
    "i'm",
    "i've",
    "i'd",
    "i'll",
    "you're",
    "you've",
    "you'd",
    "you'll",
    "he's",
    "she's",
    "it's",
    "we're",
    "we've",
    "we'd",
    "we'll",
    "they're",
    "they've",
    "they'd",
    "they'll",
    "that's",
    "there's",
    "here's",
    "what's",
    "who's",
    "let's",
    "how's",
    "where's",
    "im",
    "ive",
    "id",
    "ill",
    "youre",
    "dont",
    "of",
    "to",
    "in",
    "on",
    "at",
    "by",
    "for",
    "with",
    "from",
    "about",
    "into",
    "onto",
    "over",
    "under",
    "up",
    "down",
    "out",
    "off",
    "through",
    "during",
    "before",
    "after",
    "above",
    "below",
    "between",
    "among",
    "against",
    "within",
    "per",
    "via",
    "upon",
    "around",
    "across",
    "along",
    "toward",
    "towards",
    "behind",
    "beyond",
    "near",
    "since",
    "until",
    "till",
    "than",
    "like",
    "as",
    "and",
    "or",
    "but",
    "so",
    "because",
    "cause",
    "cuz",
    "bc",
    "if",
    "then",
    "though",
    "although",
    "while",
    "whereas",
    "unless",
    "whether",
    "yet",
    "also",
    "too",
    "there",
    "here",
    "who",
    "whom",
    "when",
    "where",
    "why",
    "how",
    "let",
    "get",
    "got",
    "getting",
    "gets",
    "make",
    "makes",
    "made",
    "going",
    "go",
    "goes",
    "st",
    "nd",
    "rd",
    "th",
    "pm",
    "s",
    "d",
    "m",
    "t",
    "ll",
    "ve",
    "re",
    "able",
];
/// Words that soften, stress or pad without adding content: dropping them never changes what a
/// sentence says. Greetings, thanks and courtesy words belong here too, as a tone may add or
/// drop them.
const FILLER: &[&str] = &[
    "really",
    "very",
    "just",
    "actually",
    "basically",
    "literally",
    "quite",
    "pretty",
    "totally",
    "honestly",
    "definitely",
    "simply",
    "truly",
    "extremely",
    "super",
    "kinda",
    "sorta",
    "maybe",
    "perhaps",
    "probably",
    "possibly",
    "somewhat",
    "rather",
    "fairly",
    "highly",
    "absolutely",
    "completely",
    "entirely",
    "certainly",
    "surely",
    "seriously",
    "obviously",
    "clearly",
    "lot",
    "lots",
    "bit",
    "well",
    "anyway",
    "anyways",
    "still",
    "even",
    "already",
    "hi",
    "hey",
    "hello",
    "hiya",
    "yo",
    "dear",
    "thanks",
    "thank",
    "thx",
    "ty",
    "please",
    "pls",
    "plz",
    "cheers",
    "regards",
    "ok",
    "okay",
    "yes",
    "yeah",
    "yep",
    "sure",
    "oh",
    "ah",
    "um",
    "uh",
    "lol",
    "haha",
    "btw",
    "fyi",
    "guys",
    "folks",
    "everyone",
    "team",
    "kindly",
    "appreciate",
    "appreciated",
    "again",
    "quick",
    "quickly",
];
/// Rude or crude words ("stupid", "hell"): softening them is what a tone rewrite is for, so every tone may drop
/// them, and a softened sentence may say "not" ("a dumb idea" is "not the best idea").
const RUDE: &[&str] = &[
    "stupid",
    "dumb",
    "idiot",
    "idiotic",
    "idiots",
    "moron",
    "moronic",
    "hell",
    "damn",
    "damned",
    "dammit",
    "goddamn",
    "crap",
    "crappy",
    "shit",
    "shitty",
    "bullshit",
    "fuck",
    "fucking",
    "fucked",
    "wtf",
    "bloody",
    "freaking",
    "frigging",
    "sucks",
    "suck",
    "sucky",
    "lame",
    "pathetic",
    "useless",
    "ridiculous",
    "garbage",
    "trash",
    "ass",
    "asshole",
    "jerk",
    "screw",
    "screwed",
    "nonsense",
    "shut",
];
/// How a reply begins: a rewrite that starts like this answers the message instead of rewriting it.
const REPLY_OPENERS: &[&str] = &[
    "sure",
    "of course",
    "absolutely",
    "no problem",
    "certainly",
    "yes,",
    "yes!",
    "no,",
    "thanks for asking",
    "i'd love to",
    "i would love to",
    "i'd be happy to",
    "i would be happy to",
    "happy to help",
    "great question",
];
/// "have" as the main verb ("You have Clickhouse available", "We have a meeting"), not the auxiliary of a
/// perfect ("have sent", "has already been"): the sentence says someone has something, and a rewrite that drops it
/// ("You and Clickhouse are now available") says something else.
fn possessive_have(text: &str) -> bool {
    const PARTICIPLES: &[&str] = &[
        "been",
        "done",
        "gone",
        "made",
        "seen",
        "got",
        "gotten",
        "taken",
        "given",
        "written",
        "known",
        "sent",
        "built",
        "put",
        "set",
        "had",
        "left",
        "found",
        "told",
        "said",
        "heard",
        "kept",
        "brought",
        "bought",
        "thought",
        "met",
        "run",
        "come",
        "become",
        "begun",
        "read",
        "paid",
        "lost",
        "won",
        "sold",
        "held",
        "felt",
        "to",
        "spent",
        "let",
        "shut",
        "cut",
        "hit",
        "hurt",
        "understood",
        "taught",
        "caught",
        "fought",
        "sought",
    ];
    const BETWEEN: &[&str] = &[
        "already", "just", "never", "not", "also", "recently", "ever", "still", "all", "both",
        "finally", "now",
    ];
    let words: Vec<String> = text
        .split(|c: char| !(c.is_alphanumeric() || c == '\'' || c == '’'))
        .filter(|w| !w.is_empty())
        .map(|w| w.to_lowercase().replace('’', "'"))
        .collect();
    words.iter().enumerate().any(|(i, w)| {
        let have = ["have", "has", "had", "having"].contains(&w.as_str()) || w.ends_with("'ve");
        if !have {
            return false;
        }
        let next = words[i + 1..]
            .iter()
            .find(|n| !BETWEEN.contains(&n.as_str()));
        next.is_some_and(|n| {
            !(PARTICIPLES.contains(&n.as_str()) || n.ends_with("ed") && n.len() > 3)
        })
    })
}
/// Hedging verbs ("I think", "I guess"): Direct and Concise may drop them.
const HEDGES: &[&str] = &[
    "think", "guess", "believe", "suppose", "feel", "reckon", "seem",
];
/// Phrases that are padding as a whole ("at this point in time" is "now"); their words count as
/// filler in the source.
const PADDING: &[&str] = &[
    "in order to",
    "due to the fact that",
    "in spite of the fact that",
    "for the purpose of",
    "in the event that",
    "at the end of the day",
    "each and every",
    "first and foremost",
    "as a matter of fact",
    "with regard to",
    "with respect to",
    "in terms of",
    "in the near future",
    "on a daily basis",
    "for all intents and purposes",
    "it is important to note that",
    "please note that",
    "i was wondering if",
    "i was wondering whether",
    "i was hoping",
    "would you mind",
    "a lot of",
    "the fact that",
    "take a look",
    "have a look",
    "let me know",
    "let you know",
    "feel free to",
    "touch base",
    "reach out",
    "i think",
    "i guess",
    "i believe",
    "i feel like",
    "i suppose",
    "i mean",
    "you know",
    "just wanted to",
    "wanted to",
    "want to",
    "hope you're well",
    "hope you are well",
    "hope you're doing well",
    "hope you are doing well",
    "hope this helps",
    "hope all is well",
    "checking in",
    "check in",
    "kind of",
    "sort of",
    "a little",
    "make sure",
    "it seems",
    "seems like",
    "had a chance to",
    "have a chance to",
    "get a chance to",
    "a chance to",
    "when you get a chance",
    "when you have a moment",
    "when you can",
    "if possible",
    "oh no",
    "sounds good",
    "no worries",
    "no problem",
    "i am writing to",
    "i'm writing to",
    "just writing to",
    "writing to let you know",
    "in the middle of",
];
/// Words that turn a statement into its opposite. A rewrite must keep the same polarity.
const NEGATION: &[&str] = &[
    "not", "no", "never", "nothing", "nobody", "none", "nowhere", "neither", "nor", "cannot",
    "without", "unable", "nope", "nah",
];
const NUMBERS: &[(&str, &str)] = &[
    ("zero", "0"),
    ("two", "2"),
    ("three", "3"),
    ("four", "4"),
    ("five", "5"),
    ("six", "6"),
    ("seven", "7"),
    ("eight", "8"),
    ("nine", "9"),
    ("ten", "10"),
    ("eleven", "11"),
    ("twelve", "12"),
    ("fifteen", "15"),
    ("twenty", "20"),
    ("thirty", "30"),
    ("forty", "40"),
    ("fifty", "50"),
    ("hundred", "100"),
    ("thousand", "1000"),
    ("half", "1/2"),
];
/// Evaluative words: a rewrite keeps each one (or a synonym) and never brings in the opposite.
const POSITIVE: &[&str] = &[
    "good",
    "great",
    "excellent",
    "wonderful",
    "fantastic",
    "amazing",
    "awesome",
    "brilliant",
    "nice",
    "love",
    "like",
    "enjoy",
    "happy",
    "glad",
    "pleased",
    "delighted",
    "perfect",
    "best",
    "better",
    "cool",
    "beautiful",
    "lovely",
    "thrilled",
    "excited",
    "impressive",
    "fine",
];
const NEGATIVE: &[&str] = &[
    "bad",
    "poor",
    "terrible",
    "awful",
    "horrible",
    "hate",
    "dislike",
    "sad",
    "unhappy",
    "upset",
    "angry",
    "mad",
    "annoyed",
    "frustrated",
    "worse",
    "worst",
    "ugly",
    "disappointing",
    "disappointed",
    "boring",
    "wrong",
    "broken",
    "useless",
    "annoying",
    "painful",
    "slow",
];
/// Days and times a rewrite must keep ("tomorrow" never becomes "today").
const TIMES: &[&str] = &[
    "today",
    "tomorrow",
    "tonight",
    "yesterday",
    "morning",
    "afternoon",
    "evening",
    "weekend",
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
    "tmrw",
    "tmr",
    "eod",
    "eow",
];
const ORDINALS: &[(&str, &str)] = &[
    ("first", "1"),
    ("second", "2"),
    ("third", "3"),
    ("fourth", "4"),
    ("fifth", "5"),
];
/// Phrasal verbs and fixed phrases that mean one word; the rest of the phrase is filler.
const PHRASAL: &[(&str, &str)] = &[
    ("take care of", "handle"),
    ("please find attached", "attach"),
    ("find attached", "attach"),
    ("at any time", "anytime"),
    ("at this point in time", "now"),
    ("at the present time", "now"),
    ("at the moment", "now"),
    ("right now", "now"),
    ("hear back", "reply"),
    ("get back to", "reply"),
    ("write back", "reply"),
    ("look into", "investigate"),
    ("figure out", "solve"),
    ("find out", "learn"),
    ("set up", "configure"),
    ("sign up", "register"),
    ("check out", "review"),
    ("go over", "review"),
    ("look at", "review"),
    ("look over", "review"),
    ("make it", "attend"),
    ("put off", "postpone"),
    ("call off", "cancel"),
    ("fill out", "complete"),
    ("fill in", "complete"),
    ("hand in", "submit"),
    ("send over", "send"),
    ("point out", "note"),
    ("carry out", "perform"),
    ("as soon as possible", "asap"),
    ("right away", "asap"),
    ("free up", "release"),
    ("run into", "encounter"),
    ("come up", "arise"),
    ("give up", "quit"),
    ("in charge of", "responsible"),
];
/// Words a tone change may swap for one another. Each row is one group; inflected forms match
/// through their lemma.
const SYNONYMS: &[&str] = &[
    "get receive obtain gotten",
    "send forward share email",
    "help assist support aid assistance",
    "need require necessary needed",
    "want like prefer wish",
    "buy purchase",
    "start begin commence kick launch",
    "end finish complete wrap conclude done",
    "show demonstrate present",
    "tell inform let notify update",
    "ask request inquire",
    "fix resolve solve repair address sort",
    "check review verify look examine confirm",
    "use utilize employ",
    "try attempt",
    "big large huge major significant",
    "small little minor tiny",
    "kid kids child children",
    "job position role work",
    "doc document file",
    "info information details detail",
    "asap soon promptly quickly urgently immediately",
    "sorry apologize apologise apology apologies regret",
    "fine okay ok good alright acceptable",
    "great excellent wonderful fantastic amazing awesome brilliant",
    "bad poor terrible awful horrible",
    "hate dislike detest loathe",
    "love adore enjoy",
    "happy glad pleased delighted",
    "sad unhappy upset",
    "angry mad annoyed frustrated",
    "tired exhausted",
    "meeting call sync meet",
    "talk speak chat discuss discussion conversation",
    "think believe feel",
    "say mention state note",
    "late delayed overdue behind",
    "issue problem trouble bug",
    "idea suggestion proposal",
    "plan schedule",
    "change update modify revise adjust edit",
    "make create build produce",
    "give provide offer",
    "keep maintain retain",
    "allow let permit enable",
    "answer reply respond response",
    "stop halt pause cease",
    "boss manager lead supervisor",
    "guy person man",
    "folk people",
    "hard difficult tough challenging",
    "easy simple straightforward",
    "fast quick rapid",
    "important key critical crucial essential",
    "right correct accurate",
    "wrong incorrect mistaken",
    "buddy friend pal mate",
    "awesome cool",
    "pic picture photo image",
    "pls please",
    "thx thanks",
    "u you",
    "yeah yes",
    "maybe perhaps possibly",
    "come attend join",
    "go leave head",
    "wait hold",
    "finished completed done",
    "deadline due",
    "ready prepared set",
    "around approximately about roughly",
    "today tonight",
    "tomorrow tmrw tmr",
    "week weekly",
    "month monthly",
    "currently now presently",
    "later afterwards subsequently",
    "agree concur",
    "approve approval sign",
    "remind reminder",
    "attach attached attachment enclose",
    "happen occur",
    "mess chaos",
    "boring dull tedious",
    "thing item matter",
    "lot many numerous",
    "whole entire",
    "cost price",
    "pay payment",
    "goal aim objective target",
    "result outcome",
    "team group",
    "customer client",
    "company business firm organization",
    "error mistake",
    "main primary principal chief",
    "store keep save hold",
    "information data info",
    "hear receive",
    "remain stay",
    "handle manage deal",
    "reply response respond answer",
    "review evaluate assess",
    "investigate examine",
    "leave off away",
    "free available",
    "ping message contact text",
    "break fail crash",
    "complicated complex",
    "sleep asleep doze",
    "long lengthy",
    "pending outstanding",
    "attend come join",
    "cancel drop",
    "postpone delay reschedule move push",
    "concern worry issue",
    "deliver ship release",
    "finish complete",
    "reason cause",
    "reduce cut lower decrease",
    "increase rise growth grow",
    "prefer like favor",
    "employee staff worker",
    "user customer",
    "device phone",
    "crash fail",
    "large big",
    "automatically auto",
    "responsible charge",
    "restart reboot",
    "recommend suggest advise",
    "share circulate distribute",
    "participant attendee",
    "keep retain maintain",
    "price rate pricing",
    "renew extend",
    "expire end lapse",
    "avoid prevent",
    "interruption disruption",
    "refund return reimburse",
    "close shut",
    "holiday vacation break",
    "request ask",
    "event occasion",
    "attach include",
    "revise update",
    "proposal offer",
    "pleasure delight",
    "confirm verify",
    "attendance presence",
    "process handle",
    "request call query",
    "drop lose",
    "export download",
    "available offered",
    "plan tier",
    "flow process",
    "ticket request",
    "budget funds",
    "schedule timeline",
    "complete finish",
    "slow sluggish",
    "accurate precise",
    "method approach way",
    "approach method way",
    "committee panel board",
    "announce share publish",
    "survey poll study",
    "apply cover",
    "staff employee team",
    "quarter period",
    "show indicate reveal",
    "clear significant notable",
    "season period",
    "sign join register",
    "current existing",
    "work suit suitable fit",
    "anytime always",
    "attach here",
];

#[derive(Debug, Clone, PartialEq)]
enum Kind {
    Content,
    Filler,
    Function,
    Negation,
    Number(String),
    /// "second" may stand for "2nd" but needs no number on the other side.
    Ordinal(String),
    Time,
}
#[derive(Debug, Clone)]
struct Word {
    surface: String,
    keys: Vec<String>,
    kind: Kind,
    name: bool,
    /// The tagger calls it an adjective ("old", "free"): a describing word a tone keeps.
    adjective: bool,
}

fn number(word: &str) -> Option<String> {
    if word.chars().any(|c| c.is_ascii_digit()) {
        return Some(word.replace(',', ""));
    }
    NUMBERS
        .iter()
        .find(|(w, _)| *w == word)
        .map(|(_, d)| (*d).to_owned())
}
fn negative(word: &str) -> bool {
    // "dont", "cant" and "wont" are often typed without the apostrophe.
    const BARE: [&str; 15] = [
        "dont", "cant", "wont", "isnt", "didnt", "doesnt", "wasnt", "arent", "werent", "couldnt",
        "wouldnt", "shouldnt", "havent", "hasnt", "aint",
    ];
    NEGATION.contains(&word)
        || word.ends_with("n't")
        || word.ends_with("n’t")
        || BARE.contains(&word)
}
/// +1 for a positive evaluative word, -1 for a negative one.
fn polarity(w: &Word) -> i8 {
    if w.keys.iter().any(|k| POSITIVE.contains(&k.as_str())) {
        1
    } else if w.keys.iter().any(|k| NEGATIVE.contains(&k.as_str())) {
        -1
    } else {
        0
    }
}
/// The forms a word may match by: itself, the tagger's lemma, a verb's base and a noun's
/// singular, an adverb's adjective.
fn keys(word: &str, lemma: &str) -> Vec<String> {
    let mut out = vec![word.to_owned()];
    let mut push = |k: String| {
        if !k.is_empty() && !out.contains(&k) {
            out.push(k);
        }
    };
    let bare = word
        .strip_suffix("'s")
        .or_else(|| word.strip_suffix('\''))
        .unwrap_or(word);
    push(bare.to_owned());
    push(lemma.to_lowercase());
    if let Some(v) = crate::morphology::verb(bare) {
        push(v.base);
    }
    if let Some(stem) = bare.strip_suffix("ies") {
        push(format!("{stem}y"));
    }
    if let Some(stem) = bare.strip_suffix("es") {
        push(stem.to_owned());
    }
    if let Some(stem) = bare.strip_suffix('s')
        && !stem.ends_with('s')
        && stem.chars().count() >= 3
    {
        push(stem.to_owned());
    }
    if let Some(stem) = bare.strip_suffix("ily") {
        push(format!("{stem}y"));
    }
    if let Some(stem) = bare.strip_suffix("ly")
        && stem.chars().count() >= 3
    {
        push(stem.to_owned());
    }
    out
}
fn words(text: &str, hints: &[TokenHint]) -> Vec<Word> {
    let tokens: Vec<_> = tokenizer::tokenize(text, hints)
        .into_iter()
        .filter(|t| {
            t.is_word
                || t.surface.chars().any(|c| c.is_ascii_digit())
                || [".", "!", "?"].contains(&t.surface)
        })
        .collect();
    let all_keys: Vec<Vec<String>> = tokens
        .iter()
        .map(|t| keys(&t.normalized, &t.lemma))
        .collect();
    // A phrase matches when each of its words is a form of the token at its place ("heard back").
    let found = |phrase: &str| -> Vec<usize> {
        let parts: Vec<&str> = phrase.split(' ').collect();
        (0..tokens.len().saturating_sub(parts.len() - 1))
            .filter(|&i| {
                parts
                    .iter()
                    .enumerate()
                    .all(|(j, p)| all_keys[i + j].iter().any(|k| k == p))
            })
            .collect()
    };
    let mut padding = vec![false; tokens.len()];
    for phrase in PADDING {
        let n = phrase.split(' ').count();
        for i in found(phrase) {
            padding[i..i + n].iter_mut().for_each(|p| *p = true);
        }
    }
    // A phrasal verb counts as the one word it means ("take care of" is "handle").
    let mut meaning: Vec<Option<&str>> = vec![None; tokens.len()];
    for (phrase, word) in PHRASAL {
        let n = phrase.split(' ').count();
        for i in found(phrase) {
            if padding[i..i + n].iter().all(|p| !p) {
                meaning[i] = Some(word);
                padding[i + 1..i + n].iter_mut().for_each(|p| *p = true);
            }
        }
    }
    let mut out = vec![];
    let mut first = true;
    for (i, t) in tokens.iter().enumerate() {
        if [".", "!", "?"].contains(&t.surface) {
            first = true;
            continue;
        }
        let w = t.normalized.as_str();
        let kind = if let Some(n) = number(w) {
            Kind::Number(n)
        } else if let Some(n) = ORDINALS.iter().find(|(o, _)| *o == w) {
            Kind::Ordinal(n.1.to_owned())
        } else if padding[i] {
            Kind::Filler
        } else if meaning[i].is_some() {
            Kind::Content
        } else if TIMES.contains(&w) {
            Kind::Time
        } else if negative(w) {
            Kind::Negation
        } else if FILLER.contains(&w) {
            Kind::Filler
        } else if FUNCTION.contains(&w)
            || [
                "Pronoun",
                "Determiner",
                "Particle",
                "Preposition",
                "Conjunction",
                "Interjection",
            ]
            .contains(&t.pos.as_str())
        {
            Kind::Function
        } else {
            Kind::Content
        };
        let capital = t.surface.chars().next().is_some_and(char::is_uppercase)
            && t.surface != "I"
            && !t.surface.starts_with("I'")
            && !t.surface.starts_with("I’");
        let name = kind == Kind::Content
            && (t.proper_name || (capital && !first && !crate::spelling::ordinary(w)));
        first = false;
        let keys = match meaning[i] {
            Some(word) => keys(word, ""),
            None => all_keys[i].clone(),
        };
        out.push(Word {
            surface: w.to_owned(),
            keys,
            kind,
            name,
            adjective: t.pos == "Adjective",
        });
    }
    out
}

fn synonyms(a: &[String], b: &[String]) -> bool {
    SYNONYMS.iter().any(|row| {
        let group: Vec<&str> = row.split(' ').collect();
        a.iter().any(|k| group.contains(&k.as_str()))
            && b.iter().any(|k| group.contains(&k.as_str()))
    })
}
/// A spelling of the same word: a slip the rewrite corrected ("hat" to "hate", "recieve" to
/// "receive"), an abbreviation ("doc" to "document") or a derived form ("approve", "approval").
fn same_word(source: &str, output: &str) -> bool {
    let (a, b): (Vec<char>, Vec<char>) = (source.chars().collect(), output.chars().collect());
    let shortest = a.len().min(b.len());
    if shortest < 3 {
        return false;
    }
    let d = crate::model::distance(source, output);
    if !crate::spelling::known(source) && d <= 3 {
        return true;
    }
    // Between two real words, one letter more or less ("hat", "hate") or two swapped ("form",
    // "from") is a slip; a different letter ("bad", "sad") is a different word.
    if d == 1
        && (a.len() != b.len() || {
            let mut x = a.clone();
            let mut y = b.clone();
            x.sort_unstable();
            y.sort_unstable();
            x == y
        })
    {
        return true;
    }
    if shortest >= 6 && d <= 2 {
        return true;
    }
    let prefix = a.iter().zip(&b).take_while(|(x, y)| x == y).count();
    prefix == shortest || (prefix >= 5 && prefix * 4 >= shortest * 3)
}
/// The same word, a form or a synonym of it, or a slip for it. A function word only matches
/// itself (the tagger may call "sorry" an interjection in one text and an adjective in another),
/// never a near spelling ("hat" is not "that").
fn matches(a: &Word, b: &Word) -> bool {
    a.keys.iter().any(|k| b.keys.contains(k))
        || (a.kind != Kind::Function
            && b.kind != Kind::Function
            && (synonyms(&a.keys, &b.keys) || same_word(&a.surface, &b.surface)))
}

/// How many content words a mode may drop, and add, in a sentence with `n` content words.
fn budget(mode: Mode, n: usize) -> (usize, usize) {
    match mode {
        Mode::Concise => (n / 3, n / 4),
        _ => (n / 4, n.div_ceil(3)),
    }
}

/// Ok when `output` says what `source` says, as far as `mode` allows: the same negation, numbers
/// and names in every mode; Concise may drop filler and redundant words but keeps the content
/// words (only a third may go, in a sentence with three or more); Professional, Friendly and
/// Direct may also swap words for known synonyms, keeping most content words. `elsewhere` is
/// the rest of the passage: a sentence may not take words from it (a model sometimes repeats
/// the next sentence inside this one). Err names the first problem found.
pub(crate) fn keeps_meaning(
    mode: Mode,
    source: &str,
    output: &str,
    elsewhere: &str,
    source_hints: &[TokenHint],
    output_hints: &[TokenHint],
) -> Result<(), String> {
    let (src, out) = (words(source, source_hints), words(output, output_hints));
    let around = words(elsewhere, &[]);
    let rude = |w: &Word| mode != Mode::Fix && w.keys.iter().any(|k| RUDE.contains(&k.as_str()));
    let softened = src
        .iter()
        .any(|s| rude(s) && !out.iter().any(|o| matches(s, o)));
    if let Some(w) = out
        .iter()
        .find(|o| rude(o) && !src.iter().any(|s| matches(s, o)))
    {
        return Err(format!("adds “{}”, which is rude", w.surface));
    }
    // A rewrite keeps what kind of sentence it is: a question stays a question (Direct may turn a request into
    // an instruction), and it never answers the message ("Sure, I'd love to take a look!").
    if mode != Mode::Direct && source.trim_end().ends_with('?') && !output.trim_end().ends_with('?')
    {
        return Err("turns a question into a statement".into());
    }
    let opener = |t: &str| {
        let t = t.trim_start().to_lowercase();
        REPLY_OPENERS.iter().any(|o| t.starts_with(o))
    };
    if opener(output) && !opener(source) {
        return Err("answers the message instead of rewriting it".into());
    }
    // Professional and Friendly keep the sentence's shape; Concise and Direct may recast it ("if you had a chance to
    // look" is "did you check").
    if matches!(mode, Mode::Professional | Mode::Friendly)
        && possessive_have(source)
        && !possessive_have(output)
        && !["got", "own", "owns", "possess", "with"].iter().any(|w| {
            output
                .split(|c: char| !c.is_alphanumeric())
                .any(|o| o.eq_ignore_ascii_case(w))
        })
    {
        return Err("drops “have”, so the sentence says something else".into());
    }
    let negated = |w: &[Word]| w.iter().any(|w| w.kind == Kind::Negation);
    // A softened sentence may gain a "not" ("a dumb idea" to "not a good idea"), never lose one.
    if negated(&src) != negated(&out) && (negated(&src) || !softened) {
        return Err(if negated(&src) {
            "drops a negation".into()
        } else {
            "adds a negation".into()
        });
    }
    let numbers = |w: &[Word]| {
        let mut n: Vec<String> = w
            .iter()
            .filter_map(|w| match &w.kind {
                Kind::Number(n) => Some(n.clone()),
                _ => None,
            })
            .collect();
        n.sort();
        n
    };
    let ordinals = |w: &[Word]| -> Vec<String> {
        w.iter()
            .filter_map(|w| match &w.kind {
                Kind::Ordinal(n) => Some(n.clone()),
                _ => None,
            })
            .collect()
    };
    let (src_numbers, out_numbers) = (numbers(&src), numbers(&out));
    if src_numbers
        .iter()
        .any(|n| !out_numbers.contains(n) && !ordinals(&out).contains(n))
        || out_numbers
            .iter()
            .any(|n| !src_numbers.contains(n) && !ordinals(&src).contains(n))
    {
        return Err("changes a number".into());
    }
    if let Some(name) = src
        .iter()
        .find(|s| s.name && !out.iter().any(|o| o.surface == s.surface))
    {
        return Err(format!("drops the name “{}”", name.surface));
    }
    let times =
        |w: &[Word]| -> Vec<Word> { w.iter().filter(|w| w.kind == Kind::Time).cloned().collect() };
    let (src_times, out_times) = (times(&src), times(&out));
    if src_times.iter().any(|s| !out.iter().any(|o| matches(s, o)))
        || out_times.iter().any(|o| !src.iter().any(|s| matches(s, o)))
    {
        return Err("changes a day or time".into());
    }
    let content = |w: &[Word]| -> Vec<Word> {
        w.iter()
            .filter(|w| w.kind == Kind::Content)
            .cloned()
            .collect()
    };
    let (src_content, out_content) = (content(&src), content(&out));
    let hedge = |w: &Word| {
        matches!(mode, Mode::Direct | Mode::Concise)
            && w.keys.iter().any(|k| HEDGES.contains(&k.as_str()))
    };
    let lost: Vec<&Word> = src_content
        .iter()
        .filter(|s| !hedge(s) && !rude(s) && !out.iter().any(|o| matches(s, o)))
        .collect();
    let added: Vec<&str> = out_content
        .iter()
        .filter(|o| !src.iter().any(|s| matches(s, o)))
        .map(|o| o.surface.as_str())
        .collect();
    if let Some(w) = lost.iter().find(|w| polarity(w) != 0) {
        return Err(format!(
            "drops “{}”, which carries the sentiment",
            w.surface
        ));
    }
    let feeling: Vec<i8> = src.iter().map(polarity).filter(|p| *p != 0).collect();
    if let Some(w) = out_content.iter().find(|o| {
        let p = polarity(o);
        p != 0 && feeling.contains(&-p) && !src.iter().any(|s| matches(s, o))
    }) {
        return Err(format!(
            "adds “{}”, which reverses the sentiment",
            w.surface
        ));
    }
    if let Some(w) = out_content.iter().find(|o| {
        !src.iter().any(|s| matches(s, o))
            && around
                .iter()
                .any(|a| a.kind == Kind::Content && matches(a, o))
    }) {
        return Err(format!("brings in “{}” from another sentence", w.surface));
    }
    // Professional and Friendly keep every describing word or a synonym of it ("the old
    // method" never becomes "the current method"); Concise and Direct may leave one out.
    if matches!(mode, Mode::Professional | Mode::Friendly)
        && let Some(w) = lost
            .iter()
            .find(|w| w.adjective && crate::spelling::known(&w.surface))
    {
        return Err(format!("drops or changes “{}”", w.surface));
    }
    let n = src_content.len();
    let (drop, add) = budget(mode, n);
    if n > 0 && lost.len() == n {
        return Err(format!(
            "keeps none of the content words (lost “{}”)",
            lost[0].surface
        ));
    }
    if lost.len() > drop {
        let list: Vec<&str> = lost.iter().map(|w| w.surface.as_str()).collect();
        return Err(format!("drops “{}”", list.join("”, “")));
    }
    if added.len() > add {
        return Err(format!("adds “{}”", added.join("”, “")));
    }
    Ok(())
}

/// A run of whole sentences (UTF-16 range in the source) and the edits inside it.
#[derive(Debug, PartialEq)]
pub(crate) struct Segment {
    pub start: usize,
    pub end: usize,
    pub edits: Vec<usize>,
}
/// Groups `edits` by the sentences of `text` they touch. An edit that spans two sentences joins
/// them into one segment; an edit between sentences belongs to the one before it.
pub(crate) fn segments(text: &str, edits: &[Edit]) -> Vec<Segment> {
    let tokens = tokenizer::tokenize(text, &[]);
    let mut sentences: Vec<(usize, usize)> = vec![];
    let mut last = usize::MAX;
    for t in &tokens {
        if t.sentence != last || sentences.is_empty() {
            sentences.push((t.start_utf16, t.end_utf16));
            last = t.sentence;
        } else if let Some(s) = sentences.last_mut() {
            s.1 = t.end_utf16;
        }
    }
    if sentences.is_empty() {
        sentences.push((0, text.encode_utf16().count()));
    }
    // (first sentence, last sentence, edits)
    let mut spans: Vec<(usize, usize, Vec<usize>)> = vec![];
    for (i, e) in edits.iter().enumerate() {
        let touched: Vec<usize> = (0..sentences.len())
            .filter(|&k| {
                let (a, b) = sentences[k];
                if e.start_utf16 == e.end_utf16 {
                    false
                } else {
                    e.start_utf16 < b && e.end_utf16 > a
                }
            })
            .collect();
        let (a, b) = match (touched.first(), touched.last()) {
            (Some(&a), Some(&b)) => (a, b),
            _ => {
                let k = sentences
                    .iter()
                    .rposition(|&(a, _)| a <= e.start_utf16)
                    .unwrap_or(0);
                (k, k)
            }
        };
        match spans.last_mut() {
            Some(s) if a <= s.1 => {
                s.1 = s.1.max(b);
                s.2.push(i);
            }
            _ => spans.push((a, b, vec![i])),
        }
    }
    spans
        .into_iter()
        .map(|(a, b, members)| {
            let start = members
                .iter()
                .map(|&i| edits[i].start_utf16)
                .min()
                .unwrap_or(0)
                .min(sentences[a].0);
            let end = members
                .iter()
                .map(|&i| edits[i].end_utf16)
                .max()
                .unwrap_or(0)
                .max(sentences[b].1);
            Segment {
                start,
                end,
                edits: members,
            }
        })
        .collect()
}
/// The source text of a segment and what its edits make of it.
pub(crate) fn texts(text: &str, segment: &Segment, edits: &[Edit]) -> Option<(String, String)> {
    let (a, b) = (byte_at(text, segment.start)?, byte_at(text, segment.end)?);
    let source = text.get(a..b)?.to_owned();
    let shifted: Vec<Edit> = segment
        .edits
        .iter()
        .map(|&i| {
            let mut e = edits[i].clone();
            e.start_utf16 -= segment.start;
            e.end_utf16 -= segment.start;
            e
        })
        .collect();
    let output = apply_edits(&source, &shifted).ok()?.0;
    Some((source, output))
}

#[cfg(test)]
mod tests {
    use super::*;
    fn ok(mode: Mode, a: &str, b: &str) -> bool {
        keeps_meaning(mode, a, b, "", &[], &[]).is_ok()
    }
    const TONES: [Mode; 4] = [
        Mode::Professional,
        Mode::Friendly,
        Mode::Concise,
        Mode::Direct,
    ];

    #[test]
    fn the_owners_sentence() {
        for mode in TONES {
            assert!(!ok(mode, "I hat it.", "It is."), "{mode:?}");
            assert!(ok(mode, "I hat it.", "I hate it."), "{mode:?}");
            assert!(ok(mode, "This is so bad.", "This is bad."), "{mode:?}");
            assert!(!ok(mode, "This is so bad.", "This is great."), "{mode:?}");
        }
    }

    #[test]
    fn negation_numbers_and_names_never_change() {
        for mode in TONES {
            assert!(!ok(mode, "I can't make it today.", "I can make it today."));
            assert!(!ok(mode, "Send it.", "Don't send it."));
            assert!(!ok(mode, "We need 3 more days.", "We need more days."));
            assert!(!ok(mode, "We need 3 more days.", "We need 4 more days."));
            assert!(ok(mode, "We need three more days.", "We need 3 more days."));
            assert!(!ok(
                mode,
                "Ask Priya about the invoice.",
                "Ask about the invoice."
            ));
            assert!(ok(
                mode,
                "I dont think it works.",
                "I don't think it works."
            ));
        }
    }

    #[test]
    fn concise_drops_filler_but_keeps_the_content() {
        let c = Mode::Concise;
        assert!(ok(
            c,
            "I just wanted to quickly check if you had a chance to look at the report.",
            "Did you check the report?"
        ));
        assert!(ok(
            c,
            "At this point in time we are really not able to ship the release.",
            "We can't ship the release now."
        ));
        assert!(!ok(
            c,
            "The client approved the budget for the new office.",
            "The client approved it."
        ));
        assert!(!ok(c, "Please send me the slides.", "Please send me."));
    }

    #[test]
    fn a_rewrite_keeps_who_has_what() {
        let src = "Hey, You have Clickhouse available now!";
        assert!(!ok(
            Mode::Professional,
            src,
            "Hello, You and Clickhouse are now available!"
        ));
        assert!(ok(
            Mode::Professional,
            src,
            "Hello, you now have Clickhouse available!"
        ));
        assert!(ok(
            Mode::Friendly,
            src,
            "Hey, you've got Clickhouse available now!"
        ));
        // The auxiliary of a perfect is no possession: "I have sent it" may become "I sent it".
        assert!(ok(
            Mode::Concise,
            "I have already sent the report.",
            "I sent the report."
        ));
    }
    #[test]
    fn tones_soften_rudeness_but_never_answer_or_turn_a_question_around() {
        assert!(ok(
            Mode::Professional,
            "Why the hell is this broken again?",
            "Why is this broken again?"
        ));
        assert!(ok(
            Mode::Professional,
            "This is a dumb idea.",
            "This is not a good idea."
        ));
        assert!(!ok(
            Mode::Direct,
            "This is a dumb idea.",
            "This is a stupid idea."
        ));
        assert!(!ok(
            Mode::Friendly,
            "Could you review this?",
            "Sure, I'd love to review this!"
        ));
        assert!(!ok(
            Mode::Professional,
            "Can we meet tomorrow?",
            "We would be happy to meet tomorrow."
        ));
        assert!(ok(
            Mode::Direct,
            "Could you review this?",
            "Please review this."
        ));
        assert!(!ok(Mode::Fix, "This is a dumb idea.", "This is an idea."));
    }
    #[test]
    fn tones_may_swap_synonyms_but_not_the_point() {
        for mode in [Mode::Professional, Mode::Friendly, Mode::Direct] {
            assert!(ok(
                mode,
                "hey can u send me the doc asap",
                "Could you please send me the document as soon as possible?"
            ));
            assert!(ok(
                mode,
                "We need to fix this bug before the launch.",
                "We must resolve this issue before the launch."
            ));
            assert!(!ok(
                mode,
                "We need to fix this bug before the launch.",
                "We should celebrate the launch together."
            ));
            assert!(!ok(
                mode,
                "I love the new design.",
                "I dislike the new design."
            ));
        }
    }

    #[test]
    fn a_sentence_may_not_take_words_from_the_next_one() {
        let verdict = keeps_meaning(
            Mode::Friendly,
            "This is so bad.",
            "Hey, I hate it. This is so bad.",
            " . I hat it.",
            &[],
            &[],
        );
        assert!(verdict.is_err());
        assert!(ok(
            Mode::Friendly,
            "This is so bad.",
            "Oh no, this is so bad."
        ));
    }

    #[test]
    fn edits_are_grouped_by_sentence() {
        let text = "This is so bad. I hat it. Fine.";
        let edit = |a: usize, b: usize, r: &str| Edit {
            start_utf16: a,
            end_utf16: b,
            original: text[a..b].into(),
            replacement: r.into(),
            category: "Style".into(),
            rule_id: "local-model".into(),
            explanation: String::new(),
            confidence: 1.0,
            group_id: None,
        };
        // "so " removed, "I hat it" rewritten, and a joined edit across the last two sentences.
        let edits = [edit(8, 11, ""), edit(16, 24, "It is"), edit(24, 27, "! f")];
        let segs = segments(text, &edits);
        assert_eq!(segs.len(), 2);
        assert_eq!(
            (segs[0].start, segs[0].end, segs[0].edits.clone()),
            (0, 15, vec![0])
        );
        assert_eq!(segs[1].edits, vec![1, 2]);
        let (source, output) = texts(text, &segs[1], &edits).unwrap();
        assert_eq!(source, "I hat it. Fine.");
        assert_eq!(output, "It is! fine.");
        // An insertion after the last sentence belongs to it.
        let tail = [edit(31, 31, " 🙂")];
        assert_eq!(segments(text, &tail)[0].edits, vec![0]);
        assert_eq!(segments(text, &tail)[0].start, 26);
    }
}
