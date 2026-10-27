//! Details of a sentence that a tone rewrite keeps as the writer wrote them: a statement stays
//! a statement, a time keeps its am or pm (or lacks it), a date keeps its order, the words that
//! set a condition stay, and the people in it (we, our, my, your) and what it promises stay. Part
//! of the meaning check (`meaning::keeps_meaning`); each finding names the first change.
use regex::Regex;
use std::sync::OnceLock;

/// The words of `text`, lowercase, an apostrophe inside a word kept ("don't"), a curly one made straight.
fn words(text: &str) -> Vec<String> {
    text.replace('\u{2019}', "'")
        .split(|c: char| !c.is_alphanumeric() && c != '\'')
        .map(|w| w.trim_matches('\''))
        .filter(|w| !w.is_empty())
        .map(str::to_lowercase)
        .collect()
}

/// Ok when `output` keeps the details of `source` that a change of tone never touches.
pub(crate) fn kept_details(source: &str, output: &str) -> Result<(), String> {
    let (src, out) = (words(source), words(output));
    statement_stays(source, output, &src)?;
    times(source, output)?;
    dates(source, output)?;
    conditions(&src, &out)?;
    people(&src, &out)?;
    promises(&src, &out)?;
    Ok(())
}

/// Who or what a negative opener asks about ("can't you", "isn't it").
const ASKED_ABOUT: &[&str] = &[
    "you",
    "u",
    "we",
    "i",
    "he",
    "she",
    "they",
    "it",
    "this",
    "that",
    "there",
    "someone",
    "anyone",
    "somebody",
    "anybody",
    "everyone",
    "everybody",
    "these",
    "those",
    "the",
    "my",
    "your",
    "our",
    "his",
    "her",
    "their",
];
/// Words that open a question when they start a clause.
const QUESTION_OPENERS: &[&str] = &[
    "can", "could", "would", "will", "do", "does", "did", "is", "are", "am", "was", "were", "have",
    "has", "had", "should", "shall", "may", "might", "must", "what", "why", "how", "when", "where",
    "who", "whom", "which", "whose", "any", "anyone", "anybody", "anything", "whats", "wheres",
    "whos", "hows", "whens", "whys",
];
/// Words that may stand before a question's opener ("hey, can you").
const LEAD_INS: &[&str] = &[
    "hey", "hi", "hello", "so", "also", "and", "but", "ok", "okay", "btw", "um", "well", "then",
    "oh", "please", "pls",
];
fn ends_question(text: &str) -> bool {
    text.trim_end_matches(|c: char| c.is_whitespace() || !c.is_ascii() && !c.is_alphanumeric())
        .ends_with('?')
}
/// Words a statement starts with. An instruction starts with a verb and may become a polite
/// question ("Fix it today." is "Could you please fix it today?"); a statement does not.
const STATEMENT_STARTS: &[&str] = &[
    "i",
    "we",
    "they",
    "he",
    "she",
    "it",
    "this",
    "that",
    "these",
    "those",
    "there",
    "the",
    "a",
    "an",
    "my",
    "our",
    "your",
    "his",
    "her",
    "their",
    "its",
    "everyone",
    "everybody",
    "nobody",
    "nothing",
    "cant",
    "cannot",
    "dont",
    "wont",
    "couldnt",
    "wouldnt",
    "shouldnt",
    "isnt",
    "arent",
    "didnt",
    "doesnt",
    "wasnt",
    "werent",
    "havent",
    "hasnt",
];
/// A statement stays one: "cant open the file, it says its corrupted" does not end in "?".
fn statement_stays(source: &str, output: &str, src: &[String]) -> Result<(), String> {
    if !ends_question(output) || source.contains('?') {
        return Ok(());
    }
    // The output ends in a question; what matters is the sentence of the source that it ends.
    let last_sentence = source
        .split(['.', '!', '\n'])
        .rfind(|s| s.chars().any(char::is_alphanumeric))
        .unwrap_or(source);
    let clauses: Vec<Vec<String>> = last_sentence
        .split([',', ';', ':'])
        .map(words)
        .map(|c| {
            let lead = c
                .iter()
                .take_while(|w| LEAD_INS.contains(&w.as_str()))
                .count();
            c[lead..].to_vec()
        })
        .filter(|c| !c.is_empty())
        .collect();
    // A chat message that asks without its mark ("can u send it", "the build is down, is anyone on it").
    let asks = clauses.iter().any(|clause| {
        let first = clause[0].as_str();
        QUESTION_OPENERS.contains(&first)
            || first.ends_with("n't")
                && clause
                    .get(1)
                    .is_some_and(|w| ASKED_ABOUT.contains(&w.as_str()))
    });
    // "I was wondering if you could send it" and "do you know" ask someone, with or without a mark.
    let addresses = src.iter().any(|w| {
        matches!(
            w.as_str(),
            "you"
                | "u"
                | "ya"
                | "wondering"
                | "wonder"
                | "curious"
                | "anyone"
                | "someone"
                | "anybody"
                | "somebody"
                | "whether"
        )
    });
    // The first clause is a statement when it opens like one (a subject, or a negated verb: "can't
    // open the file").
    let statement = clauses.first().is_some_and(|c| {
        let first = c[0].as_str();
        STATEMENT_STARTS.contains(&first)
            || first.ends_with("n't")
                && !c.get(1).is_some_and(|w| ASKED_ABOUT.contains(&w.as_str()))
    });
    if statement && !asks && !addresses {
        Err("turns a statement into a question".into())
    } else {
        Ok(())
    }
}

/// A clock time as written: hour, minute and the am or pm it carries, if any.
type Clock = (u32, u32, Option<char>);
fn clocks(text: &str) -> Vec<Clock> {
    static TIME: OnceLock<Regex> = OnceLock::new();
    let time = TIME.get_or_init(|| {
        Regex::new(r"(?i)\b(\d{1,2})(?::(\d{2}))?\s?([ap])\.?m\b|\b(\d{1,2}):(\d{2})\b")
            .expect("constant time pattern")
    });
    time.captures_iter(text)
        .filter_map(|c| {
            if let Some(hour) = c.get(1) {
                let suffix = c.get(3)?.as_str().to_ascii_lowercase().chars().next();
                Some((
                    hour.as_str().parse().ok()?,
                    c.get(2).map_or(Some(0), |m| m.as_str().parse().ok())?,
                    suffix,
                ))
            } else {
                Some((
                    c.get(4)?.as_str().parse().ok()?,
                    c.get(5)?.as_str().parse().ok()?,
                    None,
                ))
            }
        })
        .collect()
}
/// A time comes through as written: "5:30" is not "5:30 am", and "7:50 am" keeps its "am".
fn times(source: &str, output: &str) -> Result<(), String> {
    let (src, out) = (clocks(source), clocks(output));
    for &(hour, minute, suffix) in &out {
        let same_time = |c: &&Clock| c.0 == hour && c.1 == minute;
        if src.iter().any(|c| same_time(&c) && c.2 == suffix) {
            continue;
        }
        if let Some(&(_, _, was)) = src.iter().find(same_time) {
            return Err(match (was, suffix) {
                (None, Some(_)) => format!("gives {hour}:{minute:02} an am or pm it did not have"),
                (Some(_), None) => format!("drops the am or pm of {hour}:{minute:02}"),
                _ => format!("changes the am or pm of {hour}:{minute:02}"),
            });
        }
    }
    Ok(())
}

/// A date as written: month, day, whether the day comes first and whether it is an ordinal.
type Calendar = (String, u32, bool, bool);
fn calendar(text: &str) -> Vec<Calendar> {
    static DATE: OnceLock<Regex> = OnceLock::new();
    const MONTH: &str = "(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|June?|July?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)";
    let date = DATE.get_or_init(|| {
        Regex::new(&format!(
            r"\b(\d{{1,2}})(st|nd|rd|th)?(?:\s+of)?\s+{MONTH}\b|\b{MONTH}\.?\s+(\d{{1,2}})(st|nd|rd|th)?\b"
        ))
        .expect("constant date pattern")
    });
    date.captures_iter(text)
        .filter_map(|c| {
            if let Some(day) = c.get(1) {
                Some((
                    c.get(3)?.as_str()[..3].to_owned(),
                    day.as_str().parse().ok()?,
                    true,
                    c.get(2).is_some(),
                ))
            } else {
                Some((
                    c.get(4)?.as_str()[..3].to_owned(),
                    c.get(5)?.as_str().parse().ok()?,
                    false,
                    c.get(6).is_some(),
                ))
            }
        })
        .collect()
}
/// A date keeps its order and its form: "4 March" is not "March 4th".
fn dates(source: &str, output: &str) -> Result<(), String> {
    let (src, out) = (calendar(source), calendar(output));
    for d in &src {
        let same_day = |o: &&Calendar| o.0 == d.0 && o.1 == d.1;
        if out.iter().any(|o| o == d) {
            continue;
        }
        if out.iter().any(|o| same_day(&o)) {
            return Err(format!("writes the date {} {} another way", d.1, d.0));
        }
    }
    Ok(())
}

fn negations(words: &[String]) -> usize {
    words
        .iter()
        .filter(|w| {
            matches!(
                w.as_str(),
                "not" | "never" | "no" | "cannot" | "none" | "nobody" | "nothing" | "without"
            ) || w.ends_with("n't")
        })
        .count()
}
/// Whether the "if" at `i` sets a condition. "Let me know if", "I wonder if", "even if" and the
/// "if you could" of a polite request do not.
fn conditional_if(w: &[String], i: usize) -> bool {
    const NOT_BEFORE: &[&str] = &[
        "as",
        "even",
        "what",
        "know",
        "wondering",
        "wonder",
        "see",
        "check",
        "ask",
        "asking",
        "tell",
        "sure",
        "confirm",
        "verify",
        "determine",
        "say",
        "mind",
        "okay",
        "ok",
        "fine",
        "alright",
        "possible",
        "appreciate",
        "grateful",
        "thankful",
        "hope",
        "whether",
        "curious",
        "unsure",
        "wondered",
        "asked",
        "checking",
        "seeing",
        "knowing",
        "decide",
        "decides",
    ];
    let before = i.checked_sub(1).map(|k| w[k].as_str());
    // "if possible", "if convenient": a courtesy, which a plain request does without.
    let courtesy = w.get(i + 1).is_some_and(|n| {
        [
            "possible",
            "convenient",
            "needed",
            "necessary",
            "applicable",
            "feasible",
            "appropriate",
        ]
        .contains(&n.as_str())
    });
    let request = courtesy
        || w.get(i + 1).is_some_and(|n| n == "you" || n == "u")
            && w.get(i + 2)
                .is_some_and(|m| ["could", "would", "can", "might", "may"].contains(&m.as_str()));
    !before.is_some_and(|b| NOT_BEFORE.contains(&b)) && !request
}
fn has_any(w: &[String], set: &[&str]) -> bool {
    w.iter().any(|x| set.contains(&x.as_str()))
}
fn phrase(w: &[String], first: &str, second: &str) -> bool {
    w.windows(2).any(|p| p[0] == first && p[1] == second)
}
/// The words that set a condition stay: "if" is not "until", "only call" is not "call", and
/// "provided that" is not "must".
fn conditions(src: &[String], out: &[String]) -> Result<(), String> {
    let kept_if = |w: &[String]| {
        has_any(w, &["if", "provided", "providing", "assuming", "whenever"])
            || phrase(w, "as", "long")
            || phrase(w, "in", "case")
            || phrase(w, "in", "event")
    };
    if (0..src.len()).any(|i| src[i] == "if" && conditional_if(src, i))
        || has_any(src, &["provided", "providing", "assuming"])
    {
        // "if" -> "when" says something else, and so does "until".
        if !kept_if(out) && !has_any(out, &["unless"]) {
            return Err("drops the condition “if”".into());
        }
    }
    if src.iter().any(|w| w == "unless")
        && !has_any(out, &["unless", "except", "otherwise"])
        && !(out.iter().any(|w| w == "if") && negations(out) > negations(src))
    {
        return Err("drops “unless”".into());
    }
    if has_any(src, &["until", "till"]) && !has_any(out, &["until", "till", "before"]) {
        return Err("drops “until”".into());
    }
    // "the only option" is no limit; "only call if" and "we only need" are.
    let limits = src.iter().enumerate().any(|(i, w)| {
        w == "only"
            && !(i > 0
                && [
                    "the", "a", "an", "our", "my", "your", "his", "her", "their", "one", "its",
                ]
                .contains(&src[i - 1].as_str()))
    });
    if limits
        && !has_any(
            out,
            &["only", "just", "solely", "merely", "exclusively", "alone"],
        )
    {
        return Err("drops “only”".into());
    }
    Ok(())
}

fn head(word: &str) -> &str {
    word.split('\'').next().unwrap_or(word)
}
fn us(w: &[String]) -> bool {
    w.iter()
        .any(|x| matches!(head(x), "we" | "us" | "our" | "ours" | "ourselves") || x == "let's")
}
fn me(w: &[String]) -> bool {
    w.iter().any(|x| {
        matches!(
            head(x),
            "i" | "me" | "my" | "mine" | "myself" | "im" | "ive"
        )
    })
}
/// The people in the sentence stay: a rewrite does not add "we" or "our" to a writer who did
/// not say it, swap "my" and "your", or turn "we" into "I".
fn people(src: &[String], out: &[String]) -> Result<(), String> {
    // "As discussed" may become "As we discussed": the idiom has its "we" in either form.
    let added: Vec<String> = out
        .iter()
        .enumerate()
        .filter(|&(i, x)| (i == 0 || out[i - 1] != "as") || !matches!(head(x), "we" | "us"))
        .map(|(_, x)| x.clone())
        .collect();
    if us(&added) && !us(src) {
        return Err("adds “we” or “our”, which the writer did not say".into());
    }
    if us(src) && !us(out) && me(out) && !me(src) {
        return Err("turns “we” into “I”".into());
    }
    let mine = |w: &[String]| has_any(w, &["my", "mine", "myself"]);
    let yours = |w: &[String]| has_any(w, &["your", "yours", "yourself", "yourselves", "ur"]);
    if mine(src) && !yours(src) && yours(out) && !mine(out) {
        return Err("swaps “my” for “your”".into());
    }
    if yours(src) && !mine(src) && mine(out) && !yours(out) {
        return Err("swaps “your” for “my”".into());
    }
    Ok(())
}

/// A suggestion or a duty ("we should buy") is not turned into a promise ("we'll grab").
fn promises(src: &[String], out: &[String]) -> Result<(), String> {
    let future = |w: &[String]| {
        w.iter().any(|x| {
            x == "will"
                || x == "won't"
                || x == "shall"
                || x == "gonna"
                || x == "promise"
                || x == "guarantee"
                || x.ends_with("'ll")
        }) || phrase(w, "going", "to")
    };
    let advises = has_any(
        src,
        &[
            "should", "ought", "could", "might", "may", "need", "needs", "must", "maybe", "perhaps",
        ],
    ) || phrase(src, "have", "to")
        || phrase(src, "had", "better");
    if advises && !future(src) && future(out) {
        return Err("turns a suggestion into a promise".into());
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::kept_details;

    #[test]
    fn a_rewrite_keeps_what_the_writer_set_down() {
        for (source, output, why) in [
            (
                "cant open the file, it says its corrupted",
                "Can't open the file, it says it's corrupted?",
                "statement",
            ),
            (
                "Our flight leaves at 7:50 am. The taxi comes at 5:30.",
                "Flight leaves at 7:50 am. The taxi comes at 5:30 am.",
                "am or pm",
            ),
            (
                "We meet at 6:30 pm.",
                "We meet at 6:30.",
                "drops the am or pm",
            ),
            (
                "Thank you for your letter of 4 March.",
                "Thank you for your letter of March 4th.",
                "date",
            ),
            (
                "Provided that the permits arrive, construction starts in April.",
                "Permits must arrive for construction to begin in April.",
                "condition",
            ),
            (
                "We will not ship the order if payment is still pending on the 15th.",
                "We will not ship the order until payment is confirmed on the 15th.",
                "condition",
            ),
            (
                "Only call the emergency line if the main system is completely down.",
                "Call the emergency line if the main system is down.",
                "only",
            ),
            (
                "Don't open the attachment unless you know the sender.",
                "Do not open the attachment if you know the sender.",
                "unless",
            ),
            (
                "Wait until the build is green.",
                "Wait for the build to be green.",
                "until",
            ),
            (
                "I would like to ask about the final project.",
                "I'd love to ask about our final project.",
                "we",
            ),
            (
                "Heading out now, back at 2:30.",
                "Heading out now, and we will be back at 2:30.",
                "we",
            ),
            (
                "Can you bring my charger?",
                "Can you bring your charger?",
                "my",
            ),
            (
                "We should buy the cake on Saturday.",
                "We will buy the cake on Saturday.",
                "promise",
            ),
        ] {
            assert!(kept_details(source, output).is_err(), "{why}: {output}");
        }
    }

    #[test]
    fn good_rewrites_pass_the_details() {
        for (source, output) in [
            // A chat question without its mark may get one.
            ("can u send it", "Could you send it?"),
            ("Fix it today.", "Could you please fix it today?"),
            (
                "Send me the slides by noon.",
                "Could you send me the slides by noon? Thanks!",
            ),
            (
                "As discused, I attached the file.",
                "As we discussed, I have attached the file.",
            ),
            ("hey, can you look at this", "Could you look at this?"),
            (
                "the build is down, is anyone on it",
                "The build is down. Is anyone on it?",
            ),
            (
                "Our flight leaves at 7:50 am. The taxi comes at 5:30.",
                "Our flight leaves at 7:50 am. The taxi comes at 5:30.",
            ),
            ("The call is at 9am.", "The call is at 9:00 a.m."),
            (
                "Thank you for your letter of 4 March.",
                "Thank you for your letter of 4 March.",
            ),
            ("The meeting is on March 4.", "The meeting is on March 4."),
            (
                "If the test fails, do not deploy.",
                "If the test fails, do not deploy.",
            ),
            (
                "Let me know if the room is free.",
                "Please tell me whether the room is free.",
            ),
            (
                "I was wondering if you could send the file.",
                "Could you send the file?",
            ),
            (
                "Would it be okay if I borrowed your notes?",
                "Can I borrow your notes?",
            ),
            (
                "Do not open it unless you know the sender.",
                "Do not open it unless you know the sender.",
            ),
            ("Wait until Monday.", "Wait until Monday."),
            ("It is the only option.", "It is the option."),
            ("We only need two.", "We just need two."),
            ("We should buy the cake.", "We should buy the cake."),
            ("We will buy the cake.", "We'll buy the cake."),
            ("I'll send it.", "I will send it."),
            ("Let's meet at noon.", "Let's meet at noon."),
            (
                "We'll send it, thanks for your help.",
                "We will send it, thank you for your help.",
            ),
        ] {
            assert_eq!(kept_details(source, output), Ok(()), "{source} -> {output}");
        }
    }
}
