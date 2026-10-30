//! Insults said without the insult (Professional and Friendly), before the model sees the text:
//! the small model keeps most put-downs or answers them. A sentence that only evaluates the
//! reader or their work and carries no fact ("Nice work, genius.", "Your code is garbage.", "Are
//! you deaf?") is cut when another sentence remains, and the insult inside a sentence that
//! carries a fact is replaced ("this nonsense" is "this", "you people" is "you all", "What the
//! hell is wrong" is "What is wrong"). Names, numbers, times and protected text are never touched,
//! and no rule adds a negation or a question word the writer did not use.
use crate::tone_format::{REQUEST_VERBS, edit, protected_at, sentence_spans};
use crate::{Edit, Request, TextRange, tokenizer};
use regex::{Captures, Regex};
use std::sync::OnceLock;

/// A sentence that is an insult or a sarcastic remark and nothing else.
fn insult_only_regexes() -> &'static Vec<Regex> {
    static RES: OnceLock<Vec<Regex>> = OnceLock::new();
    RES.get_or_init(|| {
        let praise = r"(?:nice|great|good|fine|excellent|brilliant|wonderful|amazing|fantastic|perfect|bravo)";
        let sarcasm = r"(?:genius|einstein|sherlock|smartypants|as\s+usual)";
        [
            // "Nice work, genius.", "Wow, great job, Einstein!", "Great job again."
            format!(
                r"^(?:wow|oh|well|ah|gee)?[,!.\s]*{praise}\s+(?:work|job|going|one|move|call|effort)\s*[,!.]*\s*(?:{sarcasm}\b[,!.]*\s*)+(?:\w+[,!.]*\s*)?$"
            ),
            // "Nice of you to finally show up."
            r"^(?:wow|oh|well)?[,!.\s]*(?:nice|good|kind)\s+of\s+you\s+to\s+(?:finally\s+|actually\s+|even\s+)*(?:show\s+up|join\s+us|grace\s+us|turn\s+up|reply|respond|answer|check\s+in|bother)\b[^.!?]*[.!?]+$".into(),
            // "Thanks for nothing."
            r"^(?:thanks|thank\s+you)\s+for\s+nothing\b[^.!?]*[.!?]+$".into(),
            // "Are you deaf?", "Are you stupid?"
            r"^(?:are|were)\s+(?:you|u)\s+(?:even\s+)?(?:deaf|blind|dense|daft|stupid|dumb|thick|an\s+idiot|listening|paying\s+attention)\s*\?+$".into(),
            // "Can you read?", "Can you even listen?"
            r"^(?:can|do)\s+(?:you|u)\s+(?:even\s+)?(?:read|listen|count|think|understand|hear)\s*\?+$".into(),
            // "I told you already."
            r"^i\s+(?:told|said|mentioned|explained|wrote)\s+(?:this\s+|that\s+|it\s+)?(?:to\s+)?you\s+(?:already|before|twice|(?:two|three|four|five|several)\s+times)(?:\s+(?:already|before|now))?\s*[.!]+$".into(),
            // "Whatever.", "Typical.", "Hello?", "Unbelievable."
            r"^(?:(?:whatever|typical|ugh|unbelievable|sigh|figures)\s*[?!.…]+|(?:hello|seriously)\s*\?+)$".into(),
            // "Anyone there?", "Anybody home?"
            r"^(?:is\s+)?(?:anyone|anybody|someone)\s+(?:there|home|alive|awake|listening|out\s+there)\s*\?+$".into(),
            // "You call this a summary?"
            r"^you\s+call\s+(?:this|that|it)\s+(?:an?|the)\s+[a-z -]{1,25}\?+$".into(),
            // "Is this a joke?", "Is it really that difficult?"
            r"^is\s+(?:this|that|it)\s+(?:a\s+joke|some\s+(?:kind\s+of\s+)?(?:joke|game)|really\s+(?:that\s+|so\s+)?(?:difficult|hard|complicated|much\s+to\s+ask)|too\s+much\s+to\s+ask)\s*\?+$".into(),
            // "Your code is garbage.", "Your work was a joke."
            r"^your\s+[a-z -]{1,25}\s+(?:is|are|was|were|looks?|sounds?)\s+(?:complete\s+|total\s+|utter\s+|absolute\s+)?(?:garbage|trash|rubbish|junk|crap|a\s+joke|a\s+mess|a\s+disaster|useless|worthless|terrible|awful|pathetic|embarrassing)\s*[.!]+$".into(),
            // "You're an idiot.", "You are useless."
            r"^you(?:'re|’re|\s+are)\s+(?:such\s+)?(?:an?\s+)?(?:idiot|moron|fool|joke|disgrace|embarrassment|useless|hopeless|incompetent|clueless|pathetic)\b[^.!?]*[.!]+$".into(),
            // "What is wrong with you?"
            r"^what(?:'s|’s|\s+is)\s+wrong\s+with\s+you\s*\?+$".into(),
        ]
        .into_iter()
        .map(|p| Regex::new(&format!("(?i){p}")).expect("constant insult-only pattern"))
        .collect()
    })
}

/// Whether `sentence` is an insult and nothing else: no number, link or time, and one of the
/// shapes above.
fn insult_only(sentence: &str) -> bool {
    let s = sentence.trim();
    !s.chars().any(|c| c.is_ascii_digit())
        && !s.contains(['@', '/', '#', '`'])
        && insult_only_regexes().iter().any(|re| re.is_match(s))
}

/// Verbs of spoiling: "great job breaking the build" is sarcasm, "great job finishing the report"
/// is praise and stays.
const SPOILING: &[&str] = &[
    "break",
    "ruin",
    "mess",
    "delete",
    "crash",
    "destroy",
    "waste",
    "kill",
    "forget",
    "miss",
    "lose",
    "wreck",
    "blow",
    "botch",
    "burn",
    "trash",
    "drop",
    "skip",
    "ignore",
    "corrupt",
    "overwrite",
    "erase",
    "bury",
    "sink",
    "tank",
    "screw",
    "bungle",
    "fumble",
];

/// One replacement inside a sentence: byte range relative to the sentence, and the new text.
type Piece = (usize, usize, String);

struct Rule {
    re: Regex,
    pieces: fn(&Captures<'_>) -> Vec<Piece>,
}

fn whole(c: &Captures<'_>, name: &str) -> Option<(usize, usize)> {
    c.name(name).map(|m| (m.start(), m.end()))
}

fn rules() -> &'static Vec<Rule> {
    static RULES: OnceLock<Vec<Rule>> = OnceLock::new();
    RULES.get_or_init(|| {
        let rule = |pattern: &str, pieces: fn(&Captures<'_>) -> Vec<Piece>| Rule {
            re: Regex::new(&format!("(?i){pattern}")).expect("constant insult rule"),
            pieces,
        };
        vec![
            // "What the hell is wrong with the forecast?" is "What is wrong with the forecast?"
            rule(
                r"\b(?:what|why|who|how|where|when)(?P<cut>\s+the\s+(?:hell|heck|fuck|devil))\b",
                |c| whole(c, "cut").map(|(a, b)| (a, b, String::new())).into_iter().collect(),
            ),
            // "Who approved this nonsense?" is "Who approved this?"
            rule(
                r"\b(?:this|that|these|those)(?P<cut>\s+(?:nonsense|garbage|crap|trash|rubbish|junk|bullshit|bs))\b",
                |c| whole(c, "cut").map(|(a, b)| (a, b, String::new())).into_iter().collect(),
            ),
            // "You people never answer" is "You all never answer".
            rule(r"\byou(?P<cut>\s+people)\b", |c| {
                whole(c, "cut").map(|(a, b)| (a, b, " all".into())).into_iter().collect()
            }),
            // "Ugh, Priya, why are you…" is "Priya, why are you…"
            rule(r"^(?P<cut>(?:ugh|argh|ffs|pfft)[,.!]*\s+)\w", |c| {
                whole(c, "cut").map(|(a, b)| (a, b, String::new())).into_iter().collect()
            }),
            // "why are you always the one missing the standup" is "why are you missing the standup".
            rule(r"\bwhy\s+are\s+you(?P<cut>\s+always\s+the\s+one)\s+\w+ing\b", |c| {
                whole(c, "cut").map(|(a, b)| (a, b, String::new())).into_iter().collect()
            }),
            // "Did you even read it?" is "Did you read it?"
            rule(
                r"\b(?:did|do|does|can|could|would|will|have|has|are|is)\s+(?:you|u|they|he|she)(?P<cut>\s+even)\s+\w",
                |c| whole(c, "cut").map(|(a, b)| (a, b, String::new())).into_iter().collect(),
            ),
            // "Just do your job and send the report" is "Please send the report".
            rule(
                r"^(?P<cut>(?:just\s+|please\s+)?do\s+your\s+(?:damn\s+|bloody\s+|freaking\s+)?job\s+and\s+)(?P<verb>[a-z]+)\b",
                |c| {
                    let (Some((a, b)), Some(v)) = (whole(c, "cut"), c.name("verb")) else {
                        return vec![];
                    };
                    if !REQUEST_VERBS.contains(&v.as_str().to_lowercase().as_str()) {
                        return vec![];
                    }
                    vec![(a, b, "Please ".into())]
                },
            ),
            // "Any chance you can do your actual job this week?" asks for the work.
            rule(
                r"\bdo\s+your(?P<cut>\s+(?:actual|real|damn|bloody|freaking))\s+job\b",
                |c| whole(c, "cut").map(|(a, b)| (a, b, String::new())).into_iter().collect(),
            ),
            // "Stop wasting everyone's time with these pointless updates." asks to hold off.
            rule(
                r"^(?P<cut>stop\s+wasting\s+(?:everyone['’]s|our|my|their|the\s+team['’]s|people['’]s)\s+time\s+with)\s+(?:(?P<det>these|those|the|your|this|that)\s+)?(?:pointless|useless|stupid|dumb|worthless)\s+",
                |c| {
                    whole(c, "cut")
                        .map(|(a, b)| (a, b, "Please hold off on".into()))
                        .into_iter()
                        .collect()
                },
            ),
            // The adjective of an insult before a noun ("these pointless updates").
            rule(r"\b(?:these|those|this|that|the|your|my|our)\s+(?P<cut>(?:pointless|worthless|useless)\s+)\w", |c| {
                whole(c, "cut").map(|(a, b)| (a, b, String::new())).into_iter().collect()
            }),
            // "…, or is that too much to ask?" and "…, or are we all just pretending?" go.
            rule(
                r"(?P<cut>,?\s+or\s+(?:is\s+that\s+too\s+much\s+to\s+ask|are\s+we\s+all\s+just\s+pretending|am\s+i\s+talking\s+to\s+a\s+wall|is\s+that\s+too\s+difficult))\s*\?",
                |c| whole(c, "cut").map(|(a, b)| (a, b, String::new())).into_iter().collect(),
            ),
            // "don't come crying to me when it breaks" is "don't come to me when it breaks".
            rule(r"\bcome\s+(?P<cut>crying\s+)to\s+me\b", |c| {
                whole(c, "cut").map(|(a, b)| (a, b, String::new())).into_iter().collect()
            }),
            // "I don't have time to hold your hand through this" is "…to go through this in detail".
            rule(
                r"\b(?P<cut>hold\s+your\s+hand\s+through\s+this)\b",
                |c| {
                    whole(c, "cut")
                        .map(|(a, b)| (a, b, "go through this in detail".into()))
                        .into_iter()
                        .collect()
                },
            ),
            // "How hard is it to attach the right file, Tomasz?" is "How can the right file be
            // attached, Tomasz?"
            rule(
                r"^(?P<cut>how\s+hard\s+is\s+it\s+to\s+(?P<verb>[a-z]+)\s+(?P<object>(?:the|a|an|my|your|our|this|that|these|those)\s+[a-z]+(?:\s+[a-z]+)?))\s*[,?]",
                |c| {
                    let (Some((a, b)), Some(v), Some(o)) =
                        (whole(c, "cut"), c.name("verb"), c.name("object"))
                    else {
                        return vec![];
                    };
                    let word = v.as_str().to_lowercase();
                    let Some(verb) = crate::morphology::verb(&word).filter(|m| m.base == word)
                    else {
                        return vec![];
                    };
                    vec![(a, b, format!("How can {} be {}", o.as_str(), verb.participle))]
                },
            ),
            // "I am tired of chasing them" is "I would like to stop chasing them".
            rule(r"\b(?P<cut>i(?:['’]m|\s+am)(?:\s+(?:so|really|getting|very))*\s+tired\s+of)\s+\w+ing\b", |c| {
                whole(c, "cut")
                    .map(|(a, b)| (a, b, "I would like to stop".into()))
                    .into_iter()
                    .collect()
            }),
            // "Per my last three emails" is "As mentioned in my last three emails".
            rule(r"^(?P<cut>per\s+my)\s+(?:last|previous|earlier)\s+", |c| {
                whole(c, "cut")
                    .map(|(a, b)| (a, b, "As mentioned in my".into()))
                    .into_iter()
                    .collect()
            }),
            // "As I said yesterday," is "As mentioned yesterday,".
            rule(r"^(?P<cut>as\s+i\s+(?:said|mentioned|told\s+you|explained))\s+\w+,", |c| {
                whole(c, "cut")
                    .map(|(a, b)| (a, b, "As mentioned".into()))
                    .into_iter()
                    .collect()
            }),
            // "you strolled in at 2:25" is "you arrived at 2:25".
            rule(r"\byou\s+(?P<cut>strolled|wandered|sauntered|dragged\s+yourself)\s+in\b", |c| {
                whole(c, "cut")
                    .map(|(a, b)| (a, b, "arrived".into()))
                    .into_iter()
                    .collect()
            }),
            // "Please try to keep up" is "Please try to catch up".
            rule(r"\b(?:try\s+to|please|just)\s+(?P<cut>keep\s+up)\s*[,.!?]", |c| {
                whole(c, "cut")
                    .map(|(a, b)| (a, b, "catch up".into()))
                    .into_iter()
                    .collect()
            }),
            // "Fix that." is "Please sort that out."
            rule(r"^(?P<cut>fix\s+that)\s*[.!]$", |c| {
                whole(c, "cut")
                    .map(|(a, b)| (a, b, "Please sort that out".into()))
                    .into_iter()
                    .collect()
            }),
            // "Do I have to do everything myself around here?" asks for help.
            rule(
                r"^(?P<cut>do\s+i\s+(?:always\s+)?have\s+to\s+do\s+everything\s+myself(?:\s+around\s+here)?)\s*\?$",
                |c| {
                    whole(c, "cut")
                        .map(|(a, b)| (a, b, "Could I get some help with this".into()))
                        .into_iter()
                        .collect()
                },
            ),
            // "…the dumbest idea I've heard all week." is "I have doubts about this idea."
            rule(
                r"^(?P<cut>(?:that|this|it)(?:['’]s|\s+is)\s+the\s+(?:dumbest|stupidest|worst|silliest|most\s+(?:stupid|ridiculous|idiotic))\s+(?P<noun>idea|plan|decision|approach|proposal|suggestion)\b[^.!?]*)[.!]$",
                |c| {
                    let (Some((a, b)), Some(n)) = (whole(c, "cut"), c.name("noun")) else {
                        return vec![];
                    };
                    vec![(a, b, format!("I have doubts about this {}", n.as_str().to_lowercase()))]
                },
            ),
            // "This is unacceptable." is "This falls short of what I was hoping for."
            rule(
                r"^(?P<cut>(?:this|that|it)(?:['’]s|\s+is)\s+(?:totally\s+|completely\s+|absolutely\s+|just\s+)?(?:unacceptable|inexcusable|a\s+disgrace|pathetic|ridiculous|a\s+joke))[.!]$",
                |c| {
                    whole(c, "cut")
                        .map(|(a, b)| (a, b, "This falls short of what I was hoping for".into()))
                        .into_iter()
                        .collect()
                },
            ),
            // "Whoever wrote this clearly has never used a spreadsheet." is said without the verdict.
            rule(
                r"^(?P<subject>.+?)(?P<cut>\s+(?:clearly\s+|obviously\s+|honestly\s+)?(?P<verb>has|have)\s+(?:no\s+(?:clue|idea)\b[^.!?]*|never\s+(?:used|worked\s+with|read|seen|opened|tried|heard)\b[^.!?]*))[.!]$",
                |c| {
                    let (Some((a, b)), Some(v)) = (whole(c, "cut"), c.name("verb")) else {
                        return vec![];
                    };
                    let does = if v.as_str().eq_ignore_ascii_case("has") { "doesn't" } else { "don't" };
                    vec![(a, b, format!(" {does} seem to have the full picture"))]
                },
            ),
            // "Great job breaking the build again, Kenji." is "The build was broken again, Kenji."
            rule(
                r"^(?P<cut>(?:wow|oh|well)?[,!.\s]*(?:great|nice|good|fine|excellent|brilliant|fantastic|amazing)\s+(?:job|work)\s+(?P<gerund>[a-z]+ing)\s+(?P<object>(?:the|a|an|our|my|your|this|that)\s+[a-z]+(?:\s+[a-z]+)?)(?P<again>\s+again)?)",
                |c| {
                    let (Some((a, b)), Some(g), Some(o)) =
                        (whole(c, "cut"), c.name("gerund"), c.name("object"))
                    else {
                        return vec![];
                    };
                    let gerund = g.as_str().to_lowercase();
                    let Some(verb) = crate::morphology::verb(&gerund)
                        .filter(|v| v.gerund == gerund && SPOILING.contains(&v.base.as_str()))
                    else {
                        return vec![];
                    };
                    // The pattern may take "again" as the object's second word.
                    let (object, kept_again) = match o.as_str().strip_suffix(" again") {
                        Some(rest) => (rest, true),
                        None => (o.as_str(), false),
                    };
                    let mut head = object[..1].to_uppercase();
                    head.push_str(&object[1..]);
                    let again = if kept_again || c.name("again").is_some() {
                        " again"
                    } else {
                        ""
                    };
                    vec![(a, b, format!("{head} was {}{again}", verb.participle))]
                },
            ),
            // "Well done breaking the build" is "The build was broken".
            rule(
                r"^(?P<cut>well\s+done\s+(?P<gerund>[a-z]+ing)\s+(?P<object>(?:the|a|an|our|my|your|this|that)\s+[a-z]+(?:\s+[a-z]+)?)(?P<again>\s+again)?)",
                |c| {
                    let (Some((a, b)), Some(g), Some(o)) =
                        (whole(c, "cut"), c.name("gerund"), c.name("object"))
                    else {
                        return vec![];
                    };
                    let gerund = g.as_str().to_lowercase();
                    let Some(verb) = crate::morphology::verb(&gerund)
                        .filter(|v| v.gerund == gerund && SPOILING.contains(&v.base.as_str()))
                    else {
                        return vec![];
                    };
                    // The pattern may take "again" as the object's second word.
                    let (object, kept_again) = match o.as_str().strip_suffix(" again") {
                        Some(rest) => (rest, true),
                        None => (o.as_str(), false),
                    };
                    let mut head = object[..1].to_uppercase();
                    head.push_str(&object[1..]);
                    let again = if kept_again || c.name("again").is_some() {
                        " again"
                    } else {
                        ""
                    };
                    vec![(a, b, format!("{head} was {}{again}", verb.participle))]
                },
            ),
            // "Shut up and listen for once." is "Please listen."
            rule(r"^(?P<cut>shut\s+up\s+and\s+)(?P<verb>[a-z]+)\b", |c| {
                let (Some((a, b)), Some(v)) = (whole(c, "cut"), c.name("verb")) else {
                    return vec![];
                };
                let word = v.as_str().to_lowercase();
                if crate::morphology::verb(&word).is_none_or(|x| x.base != word) {
                    return vec![];
                }
                vec![(a, b, "Please ".into())]
            }),
            // "for once" after a request.
            rule(r"\b(?P<cut>\s+for\s+once)\b\s*[.!]", |c| {
                whole(c, "cut").map(|(a, b)| (a, b, String::new())).into_iter().collect()
            }),
        ]
    })
}

/// The edits, relative to `sentence`, that say it without its insult; none when no rule applies.
fn pieces(sentence: &str) -> Vec<Piece> {
    let mut out: Vec<Piece> = vec![];
    for rule in rules() {
        for c in rule.re.captures_iter(sentence) {
            for piece in (rule.pieces)(&c) {
                // The first rule to touch a span keeps it.
                if out.iter().all(|&(a, b, _)| piece.1 <= a || piece.0 >= b) {
                    out.push(piece);
                }
            }
        }
    }
    out.sort_by_key(|p| (p.0, p.1));
    out
}

/// Whether an imperative follows a cut insult: "Rewrite the parser before Thursday." is "Please
/// rewrite the parser before Thursday."
fn imperative(sentence: &str) -> bool {
    let first = sentence
        .split(|c: char| !c.is_alphabetic())
        .next()
        .unwrap_or("")
        .to_lowercase();
    !first.is_empty()
        && !sentence.trim_end().ends_with('?')
        && (REQUEST_VERBS.contains(&first.as_str())
            || [
                "rewrite", "redo", "read", "revise", "correct", "try", "stop", "make", "use",
                "stay", "keep", "start", "finish", "show", "tell", "explain", "answer", "reply",
            ]
            .contains(&first.as_str()))
}

/// Insults said without the insult for Professional and Friendly: sentences that only insult are
/// cut when another sentence remains, and the insult inside the others is replaced. Edits are in
/// `req.text` coordinates; protected text is never touched.
pub(crate) fn insult_forms(req: &Request, protected: &[TextRange]) -> Vec<Edit> {
    if !matches!(req.mode, crate::Mode::Professional | crate::Mode::Friendly) {
        return vec![];
    }
    let text = req.text.as_str();
    let tokens = tokenizer::tokenize(text, &req.tokens);
    let utf16 = |b: usize| text[..b].encode_utf16().count();
    let spans = sentence_spans(&tokens);
    let sentence_at = |i: usize| &text[tokens[spans[i].0].start_byte..tokens[spans[i].1].end_byte];
    let only: Vec<bool> = (0..spans.len())
        .map(|i| insult_only(sentence_at(i)))
        .collect();
    // Another sentence with words of its own must remain, and every name in a cut sentence must
    // still be written somewhere else.
    let mut cut = vec![false; spans.len()];
    for i in 0..spans.len() {
        if !only[i] {
            continue;
        }
        let others = (0..spans.len())
            .filter(|&j| j != i && !only[j])
            .map(sentence_at)
            .collect::<Vec<_>>();
        let words = |s: &str| s.split_whitespace().count();
        if others.iter().all(|s| words(s) < 3) {
            continue;
        }
        let elsewhere = others.join(" ");
        let names_kept = sentence_at(i)
            .split(|c: char| !c.is_alphanumeric() && c != '\'' && c != '’')
            .enumerate()
            .filter(|(k, w)| {
                *k > 0 && w.chars().next().is_some_and(char::is_uppercase) && *w != "I"
            })
            .all(|(_, w)| elsewhere.contains(w));
        cut[i] = names_kept
            && !protected_at(
                protected,
                utf16(tokens[spans[i].0].start_byte),
                utf16(tokens[spans[i].1].end_byte),
            );
    }
    if cut.iter().all(|c| !c) && !(0..spans.len()).any(|i| !pieces(sentence_at(i)).is_empty()) {
        return vec![];
    }
    let mut edits = vec![];
    let mut after_cut = false;
    for i in 0..spans.len() {
        let (start, end) = (tokens[spans[i].0].start_byte, tokens[spans[i].1].end_byte);
        if cut[i] {
            // On its own line the sentence goes with the space after it; in a line it goes with
            // the spaces before it, or, with more text behind it, with the one after.
            let before = text[..start].len() - text[..start].trim_end().len();
            let after = text[end..].len() - text[end..].trim_start().len();
            let line_start = text[start - before..start].contains('\n') || start == before;
            let more = spans.get(i + 1).is_some() && (i + 1..spans.len()).any(|j| !cut[j]);
            let (a, b) = if line_start && more {
                (start, end + after)
            } else if line_start || !more || text[end..end + after].contains('\n') {
                let blanks = text[start - before..start]
                    .chars()
                    .rev()
                    .take_while(|c| *c == ' ' || *c == '\t')
                    .count();
                (start - blanks, end)
            } else {
                (start, end + after)
            };
            edits.push(edit(
                utf16(a),
                utf16(b),
                &text[a..b],
                String::new(),
                "tone.insult_cut",
                "Leave out the insult.",
            ));
            after_cut = true;
            continue;
        }
        let sentence = &text[start..end];
        let mut plan = pieces(sentence);
        if after_cut && imperative(sentence) && plan.iter().all(|p| p.0 > 0) {
            let first = sentence.chars().next().map_or(0, char::len_utf8);
            plan.push((
                0,
                first,
                format!("Please {}", sentence[..first].to_lowercase()),
            ));
            plan.sort_by_key(|p| (p.0, p.1));
        }
        after_cut = false;
        if plan
            .iter()
            .any(|&(a, b, _)| protected_at(protected, utf16(start + a), utf16(start + b)))
        {
            continue;
        }
        for (a, b, replacement) in plan {
            let (a, b) = (start + a, start + b);
            if text[a..b] != replacement {
                edits.push(edit(
                    utf16(a),
                    utf16(b),
                    &text[a..b],
                    replacement,
                    "tone.insult_replaced",
                    "Say it without the insult.",
                ));
            }
        }
    }
    edits
}

#[cfg(test)]
mod tests {
    use super::*;

    fn said(mode: crate::Mode, text: &str) -> String {
        let req = Request {
            text: text.into(),
            mode,
            ..Default::default()
        };
        crate::apply_edits(text, &insult_forms(&req, &[]))
            .unwrap()
            .0
    }
    fn both(text: &str) -> String {
        let (p, f) = (
            said(crate::Mode::Professional, text),
            said(crate::Mode::Friendly, text),
        );
        assert_eq!(p, f, "{text}");
        p
    }

    #[test]
    fn a_sentence_that_only_insults_is_cut_when_another_sentence_remains() {
        for (text, expected) in [
            (
                "Nice work, genius. The link goes to a blank page.",
                "The link goes to a blank page.",
            ),
            (
                "Your code is garbage. Rewrite the parser before Thursday.",
                "Please rewrite the parser before Thursday.",
            ),
            (
                "Nice of you to finally show up. The client waited 40 minutes since 9 am.",
                "The client waited 40 minutes since 9 am.",
            ),
            (
                "Are you deaf? I said the invoice number is 48213.",
                "I said the invoice number is 48213.",
            ),
            (
                "I told you already. The meeting is at 10:30, not 11.",
                "The meeting is at 10:30, not 11.",
            ),
            (
                "Can you read? The deadline is 5 pm Friday. It says so right in the brief.",
                "The deadline is 5 pm Friday. It says so right in the brief.",
            ),
            (
                "Is this a joke? The estimate says $4,200 and last time it was $2,800.",
                "The estimate says $4,200 and last time it was $2,800.",
            ),
            (
                "You call this a summary? It's four pages long.",
                "It's four pages long.",
            ),
            (
                "Whatever. Do it your way, then, and don't come crying to me when it breaks.",
                "Do it your way, then, and don't come to me when it breaks.",
            ),
            (
                "You were supposed to call the supplier by noon. Typical.",
                "You were supposed to call the supplier by noon.",
            ),
            (
                "Hello? Anyone there? I have pinged this channel 6 times since 8:15.",
                "I have pinged this channel 6 times since 8:15.",
            ),
            (
                "Mr. Delgado,\n\nI have now asked three times for the corrected quote. Is it really that difficult?\n\nAnnika Roth",
                "Mr. Delgado,\n\nI have now asked three times for the corrected quote.\n\nAnnika Roth",
            ),
        ] {
            assert_eq!(both(text), expected, "{text}");
        }
    }

    #[test]
    fn a_lone_insult_a_name_or_a_fact_keeps_the_sentence() {
        for text in [
            // Nothing else would remain.
            "Your code is garbage.",
            "Nice work, genius.",
            // The name would be lost with the sentence, and praise is no sarcasm.
            "Nice work, genius Kenji. The link is broken.",
            "Nice work on the launch. The numbers look good.",
            "Great job, team! The release went out at 9 am.",
            "Hello. I am writing about my order from 5 May.",
            "Keep up the good work, everyone.",
            // A sentence with a fact is not insult-only.
            "Your report is garbage because the totals are wrong. Please fix them.",
            "Thanks for nothing, Kenji. See you at 5 pm.",
        ] {
            assert_eq!(both(text), text, "{text}");
        }
    }

    #[test]
    fn the_insult_inside_a_sentence_with_a_fact_is_replaced() {
        for (text, expected) in [
            (
                "What the hell is wrong with the Q3 forecast?",
                "What is wrong with the Q3 forecast?",
            ),
            ("Who approved this nonsense?", "Who approved this?"),
            (
                "You people never answer your phones.",
                "You all never answer your phones.",
            ),
            (
                "Just do your job and send the report, Marcus.",
                "Please send the report, Marcus.",
            ),
            (
                "Any chance you can do your actual job this week?",
                "Any chance you can do your job this week?",
            ),
            (
                "Ugh, Priya, why are you always the one missing the standup?",
                "Priya, why are you missing the standup?",
            ),
            (
                "Do you ever listen in meetings, or is that too much to ask?",
                "Do you ever listen in meetings?",
            ),
            (
                "Is anyone actually working on this, or are we all just pretending?",
                "Is anyone actually working on this?",
            ),
            (
                "Stop wasting everyone's time with these pointless updates.",
                "Please hold off on these updates.",
            ),
            (
                "How hard is it to attach the right file, Tomasz?",
                "How can the right file be attached, Tomasz?",
            ),
            (
                "Wow, great job breaking the build again, Kenji.",
                "The build was broken again, Kenji.",
            ),
            (
                "Whoever wrote this paragraph clearly has never used a spreadsheet.",
                "Whoever wrote this paragraph doesn't seem to have the full picture.",
            ),
            (
                "That's the dumbest idea I've heard all week.",
                "I have doubts about this idea.",
            ),
            (
                "This is unacceptable.",
                "This falls short of what I was hoping for.",
            ),
            (
                "I don't have time to hold your hand through this, Beatriz.",
                "I don't have time to go through this in detail, Beatriz.",
            ),
            (
                "Hi team,\n\nOnce again the weekly numbers are late, and I am tired of chasing them.\n\nDaniela",
                "Hi team,\n\nOnce again the weekly numbers are late, and I would like to stop chasing them.\n\nDaniela",
            ),
            (
                "Per my last three emails, the answer is still 1,500 units.",
                "As mentioned in my last three emails, the answer is still 1,500 units.",
            ),
            ("Shut up and listen for once.", "Please listen."),
            (
                "lol did u even test this before pushing it?",
                "lol did u test this before pushing it?",
            ),
        ] {
            assert_eq!(both(text), expected, "{text}");
        }
        // Praise that is meant stays.
        assert_eq!(
            both("Great job finishing the report early, Kenji."),
            "Great job finishing the report early, Kenji."
        );
        // Other modes are left to their own rules.
        assert_eq!(
            said(crate::Mode::Concise, "Who approved this nonsense?"),
            "Who approved this nonsense?"
        );
    }
}
