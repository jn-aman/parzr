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
    "approximately",
    "roughly",
    "approx",
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
    "it would be great if",
    "it would be nice if",
    "it would be helpful if",
    "would be great if",
    "would be nice if",
    "would be helpful if",
    "would be much appreciated",
    "would be appreciated",
    "i'd appreciate it if",
    "i would appreciate it if",
    "a good idea to",
    "if it's not too much trouble",
    "if it is not too much trouble",
    "if it's no trouble",
    "if you don't mind",
    "if you do not mind",
    "in my opinion",
    "sorry to bother you",
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
    "check if",
    "check whether",
    "see if",
    "see whether",
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
    "not",
    "no",
    "never",
    "nothing",
    "nobody",
    "none",
    "nowhere",
    "neither",
    "nor",
    "cannot",
    "without",
    "unable",
    "nope",
    "nah",
    "unsure",
    "uncertain",
    "unclear",
    "unaware",
    "unavailable",
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
    "pleasure",
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
    "january",
    "february",
    "march",
    "april",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
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
    "hope wish",
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
    "postpone delay reschedule move push wait",
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
    // "stated" is "state", "sharing" is "share", whatever the paradigm lookup found.
    for suffix in ["ed", "ing"] {
        if let Some(stem) = bare.strip_suffix(suffix)
            && stem.chars().count() >= 3
        {
            push(format!("{stem}e"));
        }
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
/// Which tokens belong to padding phrases, and the one word a phrasal verb at a token means
/// ("take care of" is "handle"; the rest of the phrase counts as padding).
fn phrases(all_keys: &[Vec<String>]) -> (Vec<bool>, Vec<Option<&'static str>>) {
    let n = all_keys.len();
    // A phrase matches when each of its words is a form of the token at its place ("heard back").
    let found = |phrase: &str| -> Vec<usize> {
        let parts: Vec<&str> = phrase.split(' ').collect();
        (0..n.saturating_sub(parts.len() - 1))
            .filter(|&i| {
                parts
                    .iter()
                    .enumerate()
                    .all(|(j, p)| all_keys[i + j].iter().any(|k| k == p))
            })
            .collect()
    };
    let mut padding = vec![false; n];
    for phrase in PADDING {
        let len = phrase.split(' ').count();
        for i in found(phrase) {
            padding[i..i + len].iter_mut().for_each(|p| *p = true);
        }
    }
    let mut meaning: Vec<Option<&'static str>> = vec![None; n];
    for (phrase, word) in PHRASAL {
        let len = phrase.split(' ').count();
        for i in found(phrase) {
            if padding[i..i + len].iter().all(|p| !p) {
                meaning[i] = Some(word);
                padding[i + 1..i + len].iter_mut().for_each(|p| *p = true);
            }
        }
    }
    (padding, meaning)
}
/// The tokens the meaning check reads: words, numbers and sentence ends.
fn content_tokens<'a>(text: &'a str, hints: &[TokenHint]) -> Vec<tokenizer::Token<'a>> {
    tokenizer::tokenize(text, hints)
        .into_iter()
        .filter(|t| {
            t.is_word
                || t.surface.chars().any(|c| c.is_ascii_digit())
                || [".", "!", "?"].contains(&t.surface)
        })
        .collect()
}
fn words(text: &str, hints: &[TokenHint]) -> Vec<Word> {
    let tokens = content_tokens(text, hints);
    let all_keys: Vec<Vec<String>> = tokens
        .iter()
        .map(|t| keys(&t.normalized, &t.lemma))
        .collect();
    let (padding, meaning) = phrases(&all_keys);
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
        } else if TIMES.contains(&w)
            || ["end", "beginning", "start", "middle", "early", "late"].contains(&w)
                && tokens.get(i + 1).is_some_and(|t| t.normalized == "of")
                && tokens
                    .get(i + 2)
                    .is_some_and(|t| TIMES.contains(&t.normalized.as_str()))
        {
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

/// Who does what a clause says: the writer ("I", "we", a chat message's dropped "I"), the reader
/// ("you", an instruction) or someone else.
#[derive(Clone, Copy, Debug, PartialEq)]
enum Person {
    Speaker,
    Addressee,
    /// "someone", "anyone": not the reader ("can someone review" is not "could you review").
    Anyone,
    Other,
}
/// When it happens. A perfect ("has shipped") fits both a past and a present rewrite; a future,
/// a modal and an instruction count as present.
#[derive(Clone, Copy, Debug, PartialEq)]
enum Tense {
    Past,
    Perfect,
    Present,
}
/// The finite verb of one clause: what it means (its forms), its tense and its subject.
#[derive(Debug)]
struct Clause {
    keys: Vec<String>,
    tense: Option<Tense>,
    person: Option<Person>,
}
/// Auxiliaries and modals: a clause's tense comes from the first of them.
const AUXILIARY: &[&str] = &[
    "am", "is", "are", "was", "were", "be", "been", "do", "does", "did", "have", "has", "had",
    "will", "would", "shall", "should", "can", "could", "may", "might", "must",
];
/// Words that open a new clause.
const CLAUSE_BREAK: &[&str] = &[
    "and", "but", "so", "or", "if", "when", "before", "after", "because", "while", "unless",
    "until", "although", "though", "since", "whether", "once", "cuz", "bc", "who", "which",
    "where",
];
/// Verbs whose subject a chat message drops when it is the writer ("need it by noon", "hope
/// you're well"); any other bare verb at the start of a clause is an instruction.
const STATIVE: &[&str] = &[
    "need",
    "want",
    "hope",
    "wish",
    "think",
    "guess",
    "love",
    "like",
    "hate",
    "know",
    "agree",
    "mean",
    "miss",
    "appreciate",
    "believe",
    "feel",
    "suppose",
    "prefer",
    "understand",
    "wonder",
    "apologize",
    "apologise",
    "owe",
    "doubt",
];
/// Words a clause may start with before its subject: they say nothing about who acts.
const OPENERS: &[&str] = &[
    "thank",
    "thanks",
    "thx",
    "please",
    "pls",
    "plz",
    "kindly",
    "sorry",
    "just",
    "also",
    "then",
    "now",
    "honestly",
    "unfortunately",
    "fortunately",
    "lol",
    "oh",
    "hey",
    "hi",
    "hello",
    "ok",
    "okay",
    "yes",
    "yeah",
    "no",
    "not",
];
fn person_of(word: &str) -> Option<Person> {
    let head = word.split(['\'', '’']).next().unwrap_or(word);
    match head {
        "i" | "we" | "me" | "us" | "im" | "ive" | "myself" | "ourselves" => Some(Person::Speaker),
        _ if word == "let's" || word == "lets" => Some(Person::Speaker),
        "you" | "u" | "ya" | "youre" | "yourself" | "yourselves" => Some(Person::Addressee),
        "someone" | "anyone" | "somebody" | "anybody" | "everyone" | "everybody" => {
            Some(Person::Anyone)
        }
        _ => None,
    }
}
/// The tense a contraction's verb gives ("I'm", "we've", "it's"), when the word is one.
fn contracted(word: &str) -> Option<Tense> {
    let (head, tail) = word.split_once('\'')?;
    if head.is_empty() || tail.contains('\'') {
        return None;
    }
    match tail {
        "m" | "re" | "s" | "ll" | "d" => Some(Tense::Present),
        "ve" => Some(Tense::Perfect),
        "t" => Some(match head {
            "didn" | "wasn" | "weren" | "hadn" => Tense::Past,
            "haven" | "hasn" => Tense::Perfect,
            _ => Tense::Present,
        }),
        _ => None,
    }
    .filter(|_| {
        tail != "s"
            || [
                "it", "that", "there", "here", "what", "who", "he", "she", "let",
            ]
            .contains(&head)
    })
}
/// An auxiliary, a modal, or a contraction or negation of one ("I'm", "didn't", "dont").
fn auxiliary(word: &str) -> bool {
    const BARE: [&str; 16] = [
        "dont", "cant", "wont", "isnt", "didnt", "doesnt", "wasnt", "arent", "werent", "couldnt",
        "wouldnt", "shouldnt", "havent", "hasnt", "aint", "cannot",
    ];
    AUXILIARY.contains(&word) || contracted(word).is_some() || BARE.contains(&word)
}
/// The tense a lone verb form gives: "pushed" and "sent" are past, "gone" a perfect; None for
/// a form that is both base and past ("cut", "put").
fn form_tense(word: &str) -> Option<Tense> {
    match word {
        "was" | "were" | "did" | "had" | "didnt" | "wasnt" | "werent" | "hadnt" => {
            return Some(Tense::Past);
        }
        "been" | "havent" | "hasnt" => return Some(Tense::Perfect),
        _ => {}
    }
    match crate::morphology::verb(word) {
        Some(v) if word == v.base && (v.past == v.base || v.participle == v.base) => None,
        Some(v) if word == v.past && word != v.third => Some(Tense::Past),
        Some(v) if word == v.participle => Some(Tense::Perfect),
        _ => Some(Tense::Present),
    }
}
/// The finite verb of each clause of `text`, with its tense and subject. Padding ("I wanted
/// to", "I think") is skipped, so its verb never counts as the clause's.
fn clauses(text: &str, hints: &[TokenHint]) -> Vec<Clause> {
    let tokens: Vec<_> = content_tokens(text, hints);
    let all_keys: Vec<Vec<String>> = tokens
        .iter()
        .map(|t| keys(&t.normalized, &t.lemma))
        .collect();
    let (padding, meaning) = phrases(&all_keys);
    let tagged = tokens.iter().any(|t| !t.pos.is_empty());
    // Where each clause starts: sentence ends, commas and the words that open a clause.
    let mut starts = vec![0];
    for (i, t) in tokens.iter().enumerate() {
        let after = &text[t.end_byte..];
        if [".", "!", "?"].contains(&t.surface)
            || after
                .trim_start_matches(' ')
                .starts_with([',', ';', ':', '—', '–'])
        {
            starts.push(i + 1);
        } else if CLAUSE_BREAK.contains(&t.normalized.as_str()) {
            starts.push(i);
        }
    }
    starts.push(tokens.len());
    starts.dedup();
    let is_verb = |i: usize| {
        let t = &tokens[i];
        let w = t.normalized.as_str();
        if auxiliary(w) {
            return true;
        }
        // The tagger calls "please" a verb; courtesy words never carry the clause.
        if OPENERS.contains(&w) {
            return false;
        }
        if tagged {
            return t.pos == "Verb";
        }
        // Untagged text (tests): a known verb form that does not follow a determiner.
        let before = if i == 0 {
            ""
        } else {
            tokens[i - 1].normalized.as_str()
        };
        !FUNCTION.contains(&w)
            && (!FILLER.contains(&w) || STATIVE.contains(&w))
            && crate::morphology::verb(w).is_some()
            && (!FUNCTION.contains(&before)
                || auxiliary(before)
                || person_of(before).is_some()
                || ["it", "they", "he", "she", "this", "that", "to"].contains(&before))
    };
    let mut out = vec![];
    let mut previous: Option<Person> = None;
    for pair in starts.windows(2) {
        let (a, b) = (pair[0], pair[1]);
        // "I'm running late and will start without you": the second clause's subject is the
        // first one's.
        let joined = a < b && ["and", "but", "or"].contains(&tokens[a].normalized.as_str());
        let opens = a == 0 || [".", "!", "?"].contains(&tokens[a - 1].surface);
        if a > 0 && [".", "!", "?"].contains(&tokens[a - 1].surface) {
            previous = None;
        }
        let mut i = a;
        // Skip what opens the clause without acting: clause words, courtesy and padding.
        while i < b {
            let w = tokens[i].normalized.as_str();
            if [".", "!", "?"].contains(&w)
                || CLAUSE_BREAK.contains(&w)
                || OPENERS.contains(&w)
                || padding[i]
                || tokens[i].pos == "Interjection"
            {
                i += 1;
            } else {
                break;
            }
        }
        let first = i;
        // "would you mind taking", "feel free to start": a wrapper says who acts, not the verb.
        let wrapped = (a..first).any(|k| padding[k]);
        // The finite verb: the first verb that is neither padding nor an infinitive.
        // The tagger often calls a clause-opening instruction a noun ("Ship 3 features",
        // "cache the results"): a verb's base form before an object counts as a verb there.
        let instruction = |k: usize| {
            let w = tokens[k].normalized.as_str();
            k == first
                && k + 1 < b
                && crate::morphology::verb(w).is_some_and(|v| v.base == w)
                && crate::spelling::known(w)
                && (["Determiner", "Number"].contains(&tokens[k + 1].pos.as_str())
                    || tokens[k + 1].pos == "Noun"
                        && (k == 0 || [".", "!", "?"].contains(&tokens[k - 1].surface))
                        && tokens[k].surface.starts_with(char::is_uppercase)
                    || [
                        "the", "a", "an", "this", "that", "these", "those", "it", "them", "me",
                        "us", "your", "my", "our", "his", "her", "their", "all", "some", "any",
                    ]
                    .contains(&tokens[k + 1].normalized.as_str())
                    || tokens[k + 1]
                        .surface
                        .starts_with(|c: char| c.is_ascii_digit()))
        };
        let Some(v) = (first..b).find(|&k| {
            (is_verb(k) || instruction(k))
                && !padding[k]
                && !(k > 0 && tokens[k - 1].normalized == "to")
        }) else {
            continue;
        };
        let w = tokens[v].normalized.as_str();
        // The verb chain: auxiliaries, adverbs, a negation and (in a question) the subject,
        // up to the main verb.
        let mut main = v;
        let mut k = v + 1;
        let mut inverted = None;
        let leads = auxiliary(w);
        while leads && k < b {
            let t = &tokens[k];
            let x = t.normalized.as_str();
            if is_verb(k) && !padding[k] {
                main = k;
                if !AUXILIARY.contains(&x) {
                    break;
                }
            } else if v == first
                && inverted.is_none()
                && (t.pos == "Pronoun"
                    || person_of(x).is_some()
                    || [
                        "it", "they", "he", "she", "someone", "anyone", "this", "that",
                    ]
                    .contains(&x))
            {
                inverted = Some(k);
            } else if !(t.pos == "Adverb" || FILLER.contains(&x) || negative(x) || padding[k]) {
                break;
            }
            k += 1;
        }
        // Tense: from the first verb, unless a perfect follows ("has shipped", "'ve sent").
        let mut tense = contracted(w).or_else(|| form_tense(w));
        // A participle after "have": any verb form but the base, "-s" and "-ing" forms (the
        // paradigms do not list every irregular one, such as "arisen").
        let m = tokens[main].normalized.as_str();
        let participle = main != v
            && crate::morphology::verb(m).is_none_or(|f| {
                m == f.participle || ![&f.base, &f.third, &f.gerund].contains(&&m.to_owned())
            });
        let perfect = [
            "have", "has", "having", "haven't", "hasn't", "havent", "hasnt",
        ]
        .contains(&w)
            || w.ends_with("'ve");
        if perfect {
            tense = Some(if participle {
                Tense::Perfect
            } else {
                Tense::Present
            });
        }
        if w.ends_with("'s") && tokens[main].normalized == "been" {
            tense = Some(Tense::Perfect);
        }
        if (w == "had" || w.ends_with("'d")) && participle {
            tense = Some(Tense::Past);
        }
        // Subject: the words before the verb, the pronoun after an opening auxiliary, the
        // pronoun inside a contraction; none means a dropped subject.
        let subject: Vec<&str> = match inverted {
            Some(s) => vec![tokens[s].normalized.as_str()],
            None => (first..v)
                .filter(|&k| {
                    !padding[k]
                        && tokens[k].pos != "Adverb"
                        && !FILLER.contains(&tokens[k].normalized.as_str())
                })
                .map(|k| tokens[k].normalized.as_str())
                .collect(),
        };
        let own = w
            .contains('\'')
            .then(|| person_of(w))
            .flatten()
            .or_else(|| {
                (w.contains('\'') && contracted(w).is_some() && !negative(w))
                    .then_some(Person::Other)
            });
        // "We should move it", "can we move it?" and "let's move it" propose what the reader
        // may do as well: an instruction ("Move it") keeps that.
        const PROPOSE: &[&str] = &[
            "should", "could", "can", "must", "might", "need", "let's", "lets", "we'd", "shall",
        ];
        let inclusive = (subject.iter().any(|s| ["we", "us"].contains(s))
            || w == "let's"
            || w == "lets"
            || w == "we'd")
            && PROPOSE.contains(&w);
        // "Find attached the slides" is the writer attaching them, whatever its grammar says.
        let formula = meaning[main] == Some("attach");
        let person = if inclusive || formula || (wrapped && subject.is_empty() && own.is_none()) {
            None
        } else if let Some(p) = own {
            Some(p)
        } else if !subject.is_empty() {
            Some(
                subject
                    .iter()
                    .rev()
                    .find_map(|s| person_of(s))
                    .unwrap_or(Person::Other),
            )
        } else {
            // A dropped subject: "pushed the fix" and "running late" are the writer's, "start
            // without me" and "don't forget" the reader's, "looks good" someone else's.
            let base = tokens[main].lemma.to_lowercase();
            let lemma = if base.is_empty() {
                crate::morphology::verb(&tokens[main].normalized)
                    .map(|v| v.base)
                    .unwrap_or_default()
            } else {
                base
            };
            let m = tokens[main].normalized.as_str();
            match crate::morphology::verb(m) {
                _ if ["do", "don't", "dont"].contains(&w) && main != v => Some(Person::Addressee),
                _ if leads && joined => previous,
                _ if leads => None,
                _ if STATIVE.contains(&lemma.as_str()) => Some(Person::Speaker),
                Some(f) if m == f.base => Some(Person::Addressee),
                Some(f) if m == f.third => Some(Person::Other),
                // "Running late" opens a message; "before starting" says nothing of who.
                Some(_) if opens && first == a => Some(Person::Speaker),
                Some(_) => None,
                None => None,
            }
        };
        // "I am disappointed": the describing word after "be" is what the clause says, so its
        // tense and subject are compared ("We were disappointed" is another statement).
        let copula = all_keys[main].iter().any(|k| k == "be");
        let described = (main + 1..b.min(main + 4))
            .take_while(|&k| !is_verb(k) || tokens[k].pos == "Adjective")
            .find(|&k| tokens[k].pos == "Adjective");
        let keys = match (meaning[main], described) {
            (Some(word), _) => keys(word, ""),
            (None, Some(k)) if copula => all_keys[k].clone(),
            _ => all_keys[main].clone(),
        };
        if person.is_some() {
            previous = person;
        }
        out.push(Clause {
            keys,
            tense,
            person,
        });
    }
    out
}
/// Ok when every clause verb the output keeps keeps its tense and its subject: "Just pushed the
/// fix" is not "Just push the fix", and "start without me" is not "I'm starting without me".
fn same_frames(source: &[Clause], output: &[Clause]) -> Result<(), String> {
    // "have" stays: "You have Clickhouse" is not "I have Clickhouse".
    const LIGHT: &[&str] = &["be", "do", "get", "go", "make", "let"];
    for s in source {
        if s.keys.iter().any(|k| {
            LIGHT.contains(&k.as_str())
                || AUXILIARY.contains(&k.as_str()) && !["have", "has", "had"].contains(&k.as_str())
        }) {
            continue;
        }
        let exact = |a: &Clause, b: &Clause| a.keys.iter().any(|k| b.keys.contains(k));
        // A synonym only stands in for a verb that no other clause of the source has as is
        // ("send" is not the "share" of "so I can share it").
        let same: Vec<&Clause> = output
            .iter()
            .filter(|o| {
                exact(s, o)
                    || synonyms(&s.keys, &o.keys)
                        && !source.iter().any(|t| !std::ptr::eq(t, s) && exact(t, o))
            })
            .collect();
        if same.is_empty() {
            continue;
        }
        let tense = |o: &&Clause| {
            !matches!(
                (s.tense, o.tense),
                (Some(Tense::Past), Some(Tense::Present))
                    | (Some(Tense::Present), Some(Tense::Past))
            )
        };
        let person = |o: &&Clause| {
            !matches!(
                (s.person, o.person),
                (Some(Person::Speaker), Some(Person::Addressee))
                    | (Some(Person::Addressee), Some(Person::Speaker))
                    | (
                        Some(Person::Anyone),
                        Some(Person::Addressee | Person::Speaker)
                    )
            )
        };
        if !same.iter().any(tense) {
            return Err(format!("changes the tense of “{}”", s.keys[0]));
        }
        if !same.iter().any(|o| tense(o) && person(o)) {
            return Err(format!("changes who does “{}”", s.keys[0]));
        }
    }
    Ok(())
}
/// Words that state a hope or wish rather than a fact.
const WISH: &[&str] = &[
    "hope",
    "hoping",
    "hoped",
    "hopes",
    "hopefully",
    "wish",
    "wishing",
    "wished",
];
/// Words a rewrite of a hope may use instead.
const WANT: &[&str] = &[
    "hope",
    "hoping",
    "hopefully",
    "wish",
    "want",
    "wants",
    "like",
    "love",
    "forward",
    "eager",
    "excited",
    "keen",
    "wanted",
    "wondering",
    "wonder",
];
/// Words that say the writer is not sure of what follows.
const UNSURE: &[&str] = &["unsure", "uncertain", "doubt", "doubtful", "unclear"];
/// Ok when a hope stays a hope: "I hope we can work together again" is not "We can work
/// together again", and a plain statement does not become a hope.
fn same_mood(source: &str, output: &str) -> Result<(), String> {
    let wishes = |text: &str| -> (bool, bool) {
        let tokens = content_tokens(text, &[]);
        let all_keys: Vec<Vec<String>> = tokens.iter().map(|t| keys(&t.normalized, "")).collect();
        let (padding, _) = phrases(&all_keys);
        let wish = tokens
            .iter()
            .zip(&padding)
            .any(|(t, p)| !p && WISH.contains(&t.normalized.as_str()));
        // "I was wondering if" and "I was hoping" are padding, but a wish all the same.
        let want = tokens.iter().any(|t| WANT.contains(&t.normalized.as_str()));
        (wish, want)
    };
    let ((source_wish, source_want), (output_wish, output_want)) = (wishes(source), wishes(output));
    if source_wish && !output_want {
        return Err("turns a hope into a statement".into());
    }
    if output_wish && !source_want {
        return Err("turns a statement into a hope".into());
    }
    // "I'm not sure the design works" is not "The design doesn't work".
    let unsure = |text: &str| {
        let tokens = content_tokens(text, &[]);
        tokens.iter().enumerate().any(|(i, t)| {
            let w = t.normalized.as_str();
            UNSURE.contains(&w)
                || (["sure", "certain"].contains(&w)
                    && tokens[i.saturating_sub(2)..i]
                        .iter()
                        .any(|p| negative(&p.normalized)))
        })
    };
    if unsure(source) != unsure(output) {
        return Err(if unsure(source) {
            "turns a doubt into a statement".into()
        } else {
            "turns a statement into a doubt".into()
        });
    }
    Ok(())
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

/// Verbs that take something away and verbs that add or keep it: a rewrite never turns one into
/// the other ("drops support for iOS 15" is not "brings support for iOS 15").
const REMOVES: &[&str] = &[
    "drop",
    "remove",
    "delete",
    "cut",
    "discontinue",
    "deprecate",
    "lose",
    "disable",
    "stop",
    "end",
    "cancel",
    "withdraw",
    "reduce",
    "decrease",
    "lower",
];
const ADDS: &[&str] = &[
    "add",
    "bring",
    "include",
    "introduce",
    "gain",
    "enable",
    "start",
    "keep",
    "extend",
    "launch",
    "increase",
    "raise",
    "restore",
    "offer",
];
fn direction(w: &Word) -> i8 {
    if w.keys.iter().any(|k| REMOVES.contains(&k.as_str())) {
        -1
    } else if w.keys.iter().any(|k| ADDS.contains(&k.as_str())) {
        1
    } else {
        0
    }
}
/// Words that make a statement less certain.
const HEDGED: &[&str] = &[
    "appears",
    "appear",
    "appeared",
    "seems",
    "seem",
    "seemed",
    "might",
    "likely",
    "apparently",
    "presumably",
    "supposedly",
];
/// The kinds of approximation before each number of `text`, sorted: "about 2,000" is not
/// "2,000", and "at least 5" is not "about 5".
fn approximations(text: &str) -> Vec<u8> {
    const KINDS: &[(&str, u8)] = &[
        ("about", 1),
        ("around", 1),
        ("approximately", 1),
        ("roughly", 1),
        ("nearly", 1),
        ("almost", 1),
        ("approx", 1),
        ("least", 2),
        ("over", 2),
        ("most", 3),
        ("under", 3),
    ];
    let tokens = tokenizer::tokenize(text, &[]);
    let mut out: Vec<u8> = tokens
        .windows(2)
        .filter(|w| number(&w[1].normalized).is_some() || w[1].normalized == "one")
        .filter_map(|w| KINDS.iter().find(|(k, _)| *k == w[0].normalized))
        .map(|(_, kind)| *kind)
        .collect();
    out.sort_unstable();
    out
}
/// The sentences of `text`.
fn sentences(text: &str) -> Vec<&str> {
    let tokens = tokenizer::tokenize(text, &[]);
    let mut out = vec![];
    let mut start = 0;
    for (i, t) in tokens.iter().enumerate() {
        if tokens.get(i + 1).is_none_or(|n| n.sentence != t.sentence) {
            out.push(&text[start..t.end_byte]);
            start = t.end_byte;
        }
    }
    out
}
/// The currency signs of `text`, sorted: "$1,200" keeps its "$".
fn currencies(text: &str) -> Vec<char> {
    let mut signs: Vec<char> = text.chars().filter(|c| "$€£¥₹".contains(*c)).collect();
    signs.sort_unstable();
    signs
}
/// A first line or phrase that announces the answer ("Here is the edited text:", "Rewritten:")
/// rather than belonging to it.
pub(crate) fn preamble(text: &str) -> Option<&str> {
    let text = text.trim_start();
    let head = text.split_once(':')?.0;
    let words = head.split_whitespace().count();
    let lower = head.to_lowercase();
    let announces = [
        "here",
        "edited",
        "rewritten",
        "revised",
        "rewrite",
        "version",
        "text",
    ]
    .iter()
    .any(|w| lower.split(|c: char| !c.is_alphanumeric()).any(|x| x == *w));
    (words <= 8 && !head.contains('\n') && announces).then_some(head)
}
/// The words of a tone's worked example that a rewrite of other text has no reason to use: the
/// example's content words absent from `source`. A small model sometimes copies the example
/// ("Who approved it?") into an unrelated rewrite.
pub(crate) fn borrows(example: &str, source: &str, output: &str) -> Result<(), String> {
    let (ex, src, out) = (words(example, &[]), words(source, &[]), words(output, &[]));
    match ex.iter().find(|e| {
        e.kind == Kind::Content
            && e.surface.chars().count() >= 4
            && !src.iter().any(|s| matches(s, e))
            && out
                .iter()
                .any(|o| o.keys.iter().any(|k| e.keys.contains(k)))
    }) {
        Some(e) => Err(format!("copies “{}” from the worked example", e.surface)),
        None => Ok(()),
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
    // An emoji after the question mark ("Free for lunch? ☕") still ends a question.
    let ends = |t: &str| {
        t.trim_end_matches(|c: char| c.is_whitespace() || !c.is_ascii() && !c.is_alphanumeric())
            .ends_with('?')
    };
    if mode != Mode::Direct && ends(source) && !ends(output) {
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
    // Negations are counted: "start without me" is not "will not start without help".
    let negations = |w: &[Word]| w.iter().filter(|w| w.kind == Kind::Negation).count();
    let (src_negations, out_negations) = (negations(&src), negations(&out));
    // A softened sentence may gain a "not" ("a dumb idea" to "not a good idea"), never lose one.
    if out_negations < src_negations {
        return Err("drops a negation".into());
    }
    if out_negations > src_negations && !(softened && out_negations == src_negations + 1) {
        return Err("adds a negation".into());
    }
    // A plain statement does not gain a hedge ("It is blocking" is not "It appears to be").
    let hedged = |w: &[Word]| {
        w.iter().any(|w| {
            w.kind != Kind::Filler && HEDGED.contains(&w.surface.as_str())
                || ["perhaps", "possibly", "probably", "potentially"].contains(&w.surface.as_str())
        })
    };
    // Any hedge in the source ("I guess we could maybe") lets the rewrite hedge its own way.
    let unsure = |w: &[Word]| {
        hedged(w)
            || w.iter().any(|w| {
                ["maybe", "kinda", "sorta"].contains(&w.surface.as_str())
                    || w.keys.iter().any(|k| HEDGES.contains(&k.as_str()))
            })
    };
    if hedged(&out) && !unsure(&src) {
        return Err("adds a hedge".into());
    }
    if approximations(source) != approximations(output) {
        return Err("changes how exact a number is".into());
    }
    // Every sentence of the rewrite comes from the original: one whose content words all are
    // new ("I was hoping to discuss this matter.") was made up.
    // A softened insult may be said anew ("This is garbage" as "This needs more work").
    for sentence in sentences(output).into_iter().filter(|_| !softened) {
        let content: Vec<Word> = words(sentence, &[])
            .into_iter()
            .filter(|w| w.kind == Kind::Content)
            .collect();
        let kept = content
            .iter()
            .filter(|o| src.iter().any(|s| matches(s, o)))
            .count();
        if content.len() >= 2 && kept == 0 || content.len() >= 4 && kept <= 1 {
            return Err(format!("adds “{}”", sentence.trim()));
        }
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
    // A name stays what it was: "You have Clickhouse" is not "You have the Clickhouse token".
    for (i, o) in out.iter().enumerate() {
        let Some(next) = out.get(i + 1) else { break };
        if o.name
            && next.kind == Kind::Content
            && !next.name
            && src.iter().any(|s| s.surface == o.surface)
            && !src.iter().any(|s| matches(s, next))
        {
            return Err(format!(
                "turns “{}” into “{} {}”",
                o.surface, o.surface, next.surface
            ));
        }
    }
    if currencies(source) != currencies(output) {
        return Err("changes a currency".into());
    }
    if let Some(head) = preamble(output)
        && preamble(source).is_none()
    {
        return Err(format!("adds “{head}:” before the text"));
    }
    let times =
        |w: &[Word]| -> Vec<Word> { w.iter().filter(|w| w.kind == Kind::Time).cloned().collect() };
    let (src_times, out_times) = (times(&src), times(&out));
    // Days and times match by their own forms only ("end of June" is not "completed").
    let same_time = |a: &Word, b: &Word| {
        a.keys.iter().any(|k| b.keys.contains(k))
            || (a.kind != Kind::Function
                && b.kind != Kind::Function
                && same_word(&a.surface, &b.surface))
            || (synonyms(&a.keys, &b.keys) && a.kind == b.kind)
    };
    if src_times
        .iter()
        .any(|s| !out.iter().any(|o| same_time(s, o)))
        || out_times
            .iter()
            .any(|o| !src.iter().any(|s| same_time(s, o)))
    {
        return Err("changes a day or time".into());
    }
    let content = |w: &[Word]| -> Vec<Word> {
        w.iter()
            .filter(|w| w.kind == Kind::Content)
            .cloned()
            .collect()
    };
    same_mood(source, output)?;
    same_frames(
        &clauses(source, source_hints),
        &clauses(output, output_hints),
    )?;
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
    // A feeling word may give way to another of the same feeling ("a pleasure" to "a
    // wonderful experience"), never vanish.
    if let Some(w) = lost.iter().find(|w| {
        let p = polarity(w);
        p != 0
            && !out
                .iter()
                .any(|o| polarity(o) == p && !src.iter().any(|s| matches(s, o)))
    }) {
        return Err(format!(
            "drops “{}”, which carries the sentiment",
            w.surface
        ));
    }
    let moves: Vec<i8> = src.iter().map(direction).filter(|d| *d != 0).collect();
    if let Some(w) = out.iter().find(|o| {
        let d = direction(o);
        d != 0 && moves.contains(&-d) && !moves.contains(&d) && !src.iter().any(|s| matches(s, o))
    }) {
        return Err(format!("adds “{}”, which reverses what happens", w.surface));
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
    fn the_main_verb_keeps_its_tense_and_its_subject() {
        for mode in TONES {
            // Past is not an instruction, an instruction is not the writer's own plan.
            assert!(!ok(mode, "Just pushed the fix.", "Just push the fix."));
            assert!(!ok(
                mode,
                "I sent the invoice.",
                "I am sending the invoice."
            ));
            assert!(!ok(mode, "Start without me.", "I'm starting without me."));
            assert!(!ok(
                mode,
                "Please send me the report.",
                "I will send you the report."
            ));
            assert!(ok(mode, "Just pushed the fix.", "I just pushed the fix."));
            assert!(ok(
                mode,
                "I have reviewed the contract.",
                "I reviewed the contract."
            ));
            assert!(ok(mode, "Start without me.", "Please start without me."));
            assert!(ok(
                mode,
                "We should move the meeting to Friday.",
                "Let's move the meeting to Friday."
            ));
        }
        assert!(ok(Mode::Direct, "Could you review this?", "Review this."));
        assert!(ok(
            Mode::Direct,
            "Could you review this?",
            "Please review this."
        ));
        assert!(ok(
            Mode::Direct,
            "We should move the meeting to Friday.",
            "Move the meeting to Friday."
        ));
    }

    #[test]
    fn what_happens_to_a_thing_and_who_has_it_stay() {
        for mode in TONES {
            assert!(!ok(
                mode,
                "Version 2.4.1 drops support for iOS 15.",
                "Version 2.4.1 brings support for iOS 15."
            ));
            assert!(ok(
                mode,
                "Version 2.4.1 drops support for iOS 15.",
                "Version 2.4.1 removes support for iOS 15."
            ));
            assert!(!ok(
                mode,
                "You have Clickhouse available now!",
                "You have the Clickhouse token available now!"
            ));
            assert!(!ok(
                mode,
                "You have Clickhouse available now!",
                "I have Clickhouse available now!"
            ));
            assert!(!ok(
                mode,
                "The payment of $1,200 was refunded.",
                "The payment of 1,200 was refunded."
            ));
            assert!(!ok(
                mode,
                "The report is ready.",
                "Here is the edited text: The report is ready."
            ));
            assert!(ok(
                mode,
                "I'm not sure the design works.",
                "I'm unsure the design works."
            ));
        }
        for mode in TONES {
            for (a, b) in [
                (
                    "I'm running late, start without me.",
                    "I am running late and will not start without my assistance.",
                ),
                (
                    "It is blocking the deploy.",
                    "It appears to be blocking the deployment.",
                ),
                (
                    "That meeting was so long, I almost fell asleep.",
                    "I was hoping to discuss this matter. It was a long meeting, and I almost fell asleep.",
                ),
                (
                    "Can someone review my changes?",
                    "Could you review my changes?",
                ),
                (
                    "The system handles about 2,000 requests.",
                    "The system handles 2,000 requests.",
                ),
                (
                    "We will deliver by the end of June.",
                    "We will deliver by June.",
                ),
                (
                    "I appreciate your feedback and will share it with the team.",
                    "Appreciate your feedback and share it with the team.",
                ),
            ] {
                assert!(!ok(mode, a, b), "{mode:?}: {b}");
            }
            assert!(ok(
                mode,
                "Can someone review my changes?",
                "Can someone please review my changes?"
            ));
            assert!(ok(
                mode,
                "The system handles about 2,000 requests.",
                "The system handles approximately 2,000 requests."
            ));
        }
        let example = "this plan is dumb, who even approved it??";
        assert!(borrows(example, "This is garbage.", "This plan needs work.").is_err());
        assert!(borrows(example, "This plan is late.", "This plan is delayed.").is_ok());
        assert_eq!(preamble("Edited text: Hi."), Some("Edited text"));
        assert_eq!(preamble("Note: the build is red."), None);
    }

    #[test]
    fn a_hope_stays_a_hope() {
        for mode in TONES {
            assert!(!ok(
                mode,
                "I hope we can work together again.",
                "We can work together again."
            ));
            assert!(!ok(
                mode,
                "We will deliver by Friday.",
                "We hope to deliver by Friday."
            ));
            assert!(ok(
                mode,
                "I hope we can work together again.",
                "I really hope we can work together again."
            ));
            assert!(ok(
                mode,
                "Hope you're doing well! The report is ready.",
                "The report is ready."
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
