//! Word-boundary errors between closed compounds and the phrases they come from: a compound
//! split in two ("data base", "my self", "no where") is joined, and a noun compound used as a
//! verb ("to setup the room", "I'll backup my files") or a adverb ("log in everyday") is split.
//! Only the frames where one reading is impossible are changed: "any way to help", "any one of
//! them", "a short cut" and "the login page" are valid English and stay.
use crate::tokenizer::Token;
use crate::{Edit, Request, contractions, make_edit, morphology, names, spelling, starts_sentence};

/// Compounds whose split spelling is not English, with the words after that keep it (`except`).
struct Split {
    parts: &'static [&'static str],
    joined: &'static str,
    /// Only after one of these words (empty: anywhere).
    after: &'static [&'static str],
    /// Never before one of these words.
    except: &'static [&'static str],
}
const DETERMINERS: &[&str] = &[
    "a", "an", "the", "my", "your", "his", "her", "our", "their", "this", "that", "new", "old",
    "every", "each", "one",
];
const MEALS: &[&str] = &[
    "a", "the", "my", "our", "your", "their", "his", "her", "for", "at", "after", "before",
    "during", "grab", "have", "had", "having", "eat", "ate", "make", "made", "cook", "skip",
    "skipped", "serve", "served", "quick", "big", "late", "early", "free", "hotel",
];
const SPLITS: &[Split] = &[
    Split {
        parts: &["no", "where"],
        joined: "nowhere",
        after: &[],
        except: &["clause", "clauses"],
    },
    Split {
        parts: &["some", "where"],
        joined: "somewhere",
        after: &[],
        except: &["clause", "clauses"],
    },
    Split {
        parts: &["any", "where"],
        joined: "anywhere",
        after: &[],
        except: &["clause", "clauses"],
    },
    Split {
        parts: &["every", "where"],
        joined: "everywhere",
        after: &[],
        except: &[],
    },
    Split {
        parts: &["with", "out"],
        joined: "without",
        after: &[],
        except: &["of"],
    },
    Split {
        parts: &["to", "morrow"],
        joined: "tomorrow",
        after: &[],
        except: &[],
    },
    Split {
        parts: &["never", "the", "less"],
        joined: "nevertheless",
        after: &[],
        except: &[],
    },
    Split {
        parts: &["none", "the", "less"],
        joined: "nonetheless",
        after: &[],
        except: &[],
    },
    Split {
        parts: &["sand", "wich"],
        joined: "sandwich",
        after: &[],
        except: &[],
    },
    Split {
        parts: &["sand", "wiches"],
        joined: "sandwiches",
        after: &[],
        except: &[],
    },
    Split {
        parts: &["week", "end"],
        joined: "weekend",
        after: &[],
        except: &[],
    },
    Split {
        parts: &["week", "ends"],
        joined: "weekends",
        after: &[],
        except: &[],
    },
    Split {
        parts: &["week", "day"],
        joined: "weekday",
        after: &[],
        except: &[],
    },
    Split {
        parts: &["week", "days"],
        joined: "weekdays",
        after: &[],
        except: &[],
    },
    Split {
        parts: &["fire", "place"],
        joined: "fireplace",
        after: &[],
        except: &[],
    },
    Split {
        parts: &["pass", "word"],
        joined: "password",
        after: &[],
        except: &[],
    },
    Split {
        parts: &["pass", "words"],
        joined: "passwords",
        after: &[],
        except: &[],
    },
    Split {
        parts: &["data", "base"],
        joined: "database",
        after: &[],
        except: &[],
    },
    Split {
        parts: &["data", "bases"],
        joined: "databases",
        after: &[],
        except: &[],
    },
    Split {
        parts: &["note", "book"],
        joined: "notebook",
        after: DETERMINERS,
        except: &[],
    },
    Split {
        parts: &["note", "books"],
        joined: "notebooks",
        after: DETERMINERS,
        except: &[],
    },
    Split {
        parts: &["class", "room"],
        joined: "classroom",
        after: &[],
        except: &[],
    },
    Split {
        parts: &["class", "rooms"],
        joined: "classrooms",
        after: &[],
        except: &[],
    },
    Split {
        parts: &["book", "store"],
        joined: "bookstore",
        after: DETERMINERS,
        except: &[],
    },
    Split {
        parts: &["break", "fast"],
        joined: "breakfast",
        after: MEALS,
        except: &[],
    },
    Split {
        parts: &["news", "paper"],
        joined: "newspaper",
        after: &[],
        except: &[],
    },
    Split {
        parts: &["news", "papers"],
        joined: "newspapers",
        after: &[],
        except: &[],
    },
    Split {
        parts: &["my", "self"],
        joined: "myself",
        after: &[],
        except: &[],
    },
    Split {
        parts: &["your", "self"],
        joined: "yourself",
        after: &[],
        except: &[],
    },
    Split {
        parts: &["him", "self"],
        joined: "himself",
        after: &[],
        except: &[],
    },
    Split {
        parts: &["her", "self"],
        joined: "herself",
        after: &[],
        except: &[],
    },
    Split {
        parts: &["it", "self"],
        joined: "itself",
        after: &[],
        except: &[],
    },
    Split {
        parts: &["our", "selves"],
        joined: "ourselves",
        after: &[],
        except: &[],
    },
    Split {
        parts: &["your", "selves"],
        joined: "yourselves",
        after: &[],
        except: &[],
    },
    Split {
        parts: &["them", "selves"],
        joined: "themselves",
        after: &[],
        except: &[],
    },
    Split {
        parts: &["any", "body"],
        joined: "anybody",
        after: &[],
        except: &["of"],
    },
    Split {
        parts: &["some", "body"],
        joined: "somebody",
        after: &[],
        except: &["of"],
    },
    Split {
        parts: &["some", "thing"],
        joined: "something",
        after: &[],
        except: &[],
    },
    Split {
        parts: &["any", "thing"],
        joined: "anything",
        after: &[],
        except: &[],
    },
    Split {
        parts: &["some", "how"],
        joined: "somehow",
        after: &[],
        except: &[],
    },
    Split {
        parts: &["birth", "day"],
        joined: "birthday",
        after: &[],
        except: &[],
    },
    Split {
        parts: &["head", "phones"],
        joined: "headphones",
        after: &[],
        except: &[],
    },
    Split {
        parts: &["lap", "top"],
        joined: "laptop",
        after: &[],
        except: &[],
    },
    Split {
        parts: &["class", "mate"],
        joined: "classmate",
        after: &[],
        except: &[],
    },
    Split {
        parts: &["class", "mates"],
        joined: "classmates",
        after: &[],
        except: &[],
    },
    Split {
        parts: &["room", "mate"],
        joined: "roommate",
        after: &[],
        except: &[],
    },
    Split {
        parts: &["room", "mates"],
        joined: "roommates",
        after: &[],
        except: &[],
    },
    Split {
        parts: &["team", "mate"],
        joined: "teammate",
        after: &[],
        except: &[],
    },
    Split {
        parts: &["team", "mates"],
        joined: "teammates",
        after: &[],
        except: &[],
    },
    Split {
        parts: &["there", "fore"],
        joined: "therefore",
        after: &[],
        except: &[],
    },
    Split {
        parts: &["before", "hand"],
        joined: "beforehand",
        after: &[],
        except: &[],
    },
    Split {
        parts: &["short", "cut"],
        joined: "shortcut",
        after: &["the", "keyboard"],
        except: &[],
    },
    Split {
        parts: &["short", "cuts"],
        joined: "shortcuts",
        after: &["the", "keyboard"],
        except: &[],
    },
];
/// Auxiliaries that open a question whose subject is "anyone" ("Did any one see it?").
const QUESTION_AUX: [&str; 12] = [
    "did", "does", "do", "has", "have", "had", "can", "could", "will", "would", "is", "was",
];
/// Words before "any way" that make it a noun phrase ("in any way", "no way").
const WAY_DETERMINERS: [&str; 12] = [
    "in", "no", "some", "the", "every", "one", "that", "this", "either", "any", "which", "what",
];
/// "How ever," and "any way," before a comma are the adverbs "however" and "anyway"; "any one"
/// between an auxiliary and a verb is the pronoun "anyone".
fn adverb_join(text: &str, tokens: &[Token<'_>], i: usize) -> Option<(usize, &'static str)> {
    let token = &tokens[i];
    let paragraph = token.paragraph;
    let second = tokens.get(i + 1)?;
    let comma_after = tokens.get(i + 2).is_some_and(|t| t.surface == ",");
    let prev = word(tokens, i.checked_sub(1), paragraph);
    let next = word(tokens, Some(i + 2), paragraph);
    if !plain(text, &tokens[i..=i + 1]) {
        return None;
    }
    match (token.normalized.as_str(), second.normalized.as_str()) {
        ("how", "ever") if comma_after => Some((i + 1, "however")),
        // "Is there any way, though, ..." asks about a way; "I'll be there any way," is "anyway".
        ("any", "way")
            if comma_after
                && !WAY_DETERMINERS.contains(&prev)
                && !(prev == "there"
                    && ["is", "was", "isn't", "wasn't", "are", "were"].contains(&word(
                        tokens,
                        i.checked_sub(2),
                        paragraph,
                    ))) =>
        {
            Some((i + 1, "anyway"))
        }
        ("any", "one")
            if QUESTION_AUX.contains(&prev)
                && next != "of"
                && morphology::verb(next).is_some_and(|v| {
                    [&v.base, &v.participle, &v.gerund].contains(&&next.to_string())
                })
                // "any one person" is a determiner phrase: the verb must not also be a noun.
                && (spelling::flags(next) & 2 == 0
                    || [
                        "see", "know", "have", "want", "need", "call", "hear", "find", "help",
                        "notice", "try", "use", "like", "take", "get", "check", "mind", "care",
                    ]
                    .contains(&next)) =>
        {
            Some((i + 1, "anyone"))
        }
        _ => None,
    }
}
/// Noun compounds and the phrasal verbs they come from ("a backup", "back up your files").
const PHRASAL: [(&str, &str); 22] = [
    ("backup", "back up"),
    ("checkout", "check out"),
    ("cleanup", "clean up"),
    ("followup", "follow up"),
    ("login", "log in"),
    ("logout", "log out"),
    ("lookup", "look up"),
    ("pickup", "pick up"),
    ("setup", "set up"),
    ("shutdown", "shut down"),
    ("signup", "sign up"),
    ("wakeup", "wake up"),
    ("workout", "work out"),
    ("breakup", "break up"),
    ("kickoff", "kick off"),
    ("rollout", "roll out"),
    ("warmup", "warm up"),
    ("writeup", "write up"),
    ("dropoff", "drop off"),
    ("handover", "hand over"),
    ("takeover", "take over"),
    ("sendoff", "send off"),
];
/// Words after which a bare verb follows: modals, "to", "please", a subject pronoun, a negation.
const VERB_LEADS: [&str; 30] = [
    "will", "would", "can", "could", "should", "must", "might", "please", "let's", "i", "we",
    "you", "they", "i'll", "we'll", "you'll", "they'll", "he'll", "she'll", "don't", "didn't",
    "doesn't", "won't", "can't", "cannot", "never", "i'd", "we'd", "just", "to",
];
/// Words that may follow the verb but not the noun after "to" ("to setup the room").
const OBJECT_START: [&str; 30] = [
    "the",
    "a",
    "an",
    "my",
    "your",
    "his",
    "her",
    "our",
    "their",
    "its",
    "this",
    "that",
    "these",
    "those",
    "it",
    "them",
    "him",
    "me",
    "us",
    "everything",
    "everyone",
    "all",
    "some",
    "of",
    "with",
    "on",
    "at",
    "for",
    "and",
    "before",
];
fn word<'t>(tokens: &'t [Token<'_>], at: Option<usize>, paragraph: usize) -> &'t str {
    at.and_then(|i| tokens.get(i))
        .filter(|t| t.is_word && t.paragraph == paragraph)
        .map_or("", |t| t.normalized.as_str())
}
fn case_like(replacement: &str, original: &str) -> String {
    if original.starts_with(char::is_uppercase) {
        let mut chars = replacement.chars();
        chars
            .next()
            .map(|c| c.to_uppercase().collect::<String>() + chars.as_str())
            .unwrap_or_default()
    } else {
        replacement.to_string()
    }
}
fn push(req: &Request, edits: &mut Vec<Edit>, first: &Token<'_>, last: &Token<'_>, joined: &str) {
    let original = &req.text[first.start_byte..last.end_byte];
    let (reason, id) = if joined.contains(' ') {
        ("Use the two-word verb here.", "spelling.split_compound")
    } else {
        (
            "This compound is written as one word.",
            "spelling.join_compound",
        )
    };
    if let Some(e) = make_edit(
        &req.text,
        first.start_utf16,
        last.end_utf16,
        case_like(joined, original),
        "Spelling",
        id,
        reason,
        0.93,
    ) {
        edits.push(e);
    }
}
/// A piece that stands as a word on its own: an ordinary word of two or more letters, "a", "I",
/// or chat shorthand ("u", "ur").
fn whole(piece: &str) -> bool {
    piece == "a"
        || piece == "i"
        || piece.len() >= 2 && spelling::ordinary(piece)
        || names::is_shorthand(piece)
}
/// The second pieces that end a contraction typed with a space for its apostrophe ("don t").
const CONTRACTION_TAILS: [&str; 8] = ["t", "nt", "s", "m", "re", "ll", "ve", "d"];
/// A space typed inside a word ("no t", "Wh at", "thi s", "do nt"): two neighbouring pieces, at
/// least one of them no word on its own, that make one frequent word (or a contraction) together.
/// Two real words ("a part", "some one") have a reading as typed and are left to the phrase rules.
fn split_word(req: &Request, tokens: &[Token<'_>], i: usize) -> Option<String> {
    let text = req.text.as_str();
    let (a, b) = (&tokens[i], tokens.get(i + 1)?);
    if !b.is_word || a.paragraph != b.paragraph || !plain(text, &tokens[i..=i + 1]) {
        return None;
    }
    // A capital inside a sentence starts a name ("Le Pen", "Ho Chi Minh").
    let capital = |t: &Token<'_>| t.surface.starts_with(char::is_uppercase);
    if capital(b) || capital(a) && a.surface != "I" && !starts_sentence(text, a.start_byte, req) {
        return None;
    }
    // Chat shorthand beside a letter ("thank u s much") is chat, not a broken word.
    let shorthand = |t: &Token<'_>| names::is_shorthand(&t.normalized);
    if whole(&a.normalized) && whole(&b.normalized) || shorthand(a) || shorthand(b) {
        return None;
    }
    let joined = format!("{}{}", a.normalized, b.normalized);
    // A damaged word beside a whole one ("the beac on Sunday", "a lt") is a typo of its own, not
    // half of "beacon" or "alt": a piece of three letters or more that is one slip from a frequent
    // word, or two letters that are a slip of a word more frequent than the joined one.
    let typo_piece = |piece: &Token<'_>, other: &Token<'_>| {
        whole(&other.normalized)
            && piece.normalized.len() >= 2
            && spelling::cheap_fix(&piece.normalized).is_some_and(|fix| {
                piece.normalized.len() >= 3
                    || spelling::frequency(&fix) > spelling::frequency(&joined)
            })
    };
    let contraction_tail = CONTRACTION_TAILS.contains(&b.normalized.as_str());
    if !contraction_tail && (typo_piece(a, b) || typo_piece(b, a)) {
        return None;
    }
    if CONTRACTION_TAILS.contains(&b.normalized.as_str())
        && let Some(contraction) = contractions::contraction(&joined)
    {
        return Some(contraction.to_string());
    }
    (spelling::ordinary(&joined) && spelling::frequency(&joined) >= 300).then_some(joined)
}
/// Plain lowercase prose words separated by single spaces, not glued to code or a path.
fn plain(text: &str, span: &[Token<'_>]) -> bool {
    let first = &span[0];
    let last = &span[span.len() - 1];
    let before = text[..first.start_byte].chars().next_back();
    let after = text[last.end_byte..].chars().next();
    span.iter().all(|t| {
        t.is_word
            && t.surface.chars().skip(1).all(|c| c.is_ascii_lowercase())
            && t.surface.is_ascii()
    }) && span
        .windows(2)
        .all(|w| text[w[0].end_byte..w[1].start_byte] == *" ")
        && !before.is_some_and(|c| "._/@#\\-".contains(c) || c.is_alphanumeric())
        && !after.is_some_and(|c| "_/@\\-".contains(c) || c.is_alphanumeric())
        && !(after == Some('.')
            && text[last.end_byte + 1..].starts_with(|c: char| c.is_alphanumeric()))
}
pub fn check(req: &Request, tokens: &[Token<'_>], edits: &mut Vec<Edit>) {
    let text = req.text.as_str();
    for (i, token) in tokens.iter().enumerate() {
        if !token.is_word {
            continue;
        }
        let paragraph = token.paragraph;
        if let Some(joined) = split_word(req, tokens, i) {
            let last = &tokens[i + 1];
            let original = &req.text[token.start_byte..last.end_byte];
            let replacement = if joined.starts_with("i'") {
                format!("I{}", &joined[1..])
            } else {
                case_like(&joined, original)
            };
            if let Some(e) = make_edit(
                &req.text,
                token.start_utf16,
                last.end_utf16,
                replacement,
                "Spelling",
                "spelling.split_word",
                "A space was typed inside this word.",
                0.93,
            ) {
                edits.push(e);
            }
            continue;
        }
        let prev = word(tokens, i.checked_sub(1), paragraph);
        let lower = token.normalized.as_str();
        // "data base" to "database".
        for split in SPLITS.iter().filter(|s| s.parts[0] == lower) {
            let n = split.parts.len();
            let Some(span) = tokens.get(i..i + n) else {
                continue;
            };
            let next = word(tokens, Some(i + n), paragraph);
            if span
                .iter()
                .zip(split.parts)
                .all(|(t, p)| t.normalized == *p)
                && plain(text, span)
                && (split.after.is_empty() || split.after.contains(&prev))
                && !split.except.contains(&next)
                // "before hand surgery" is a time phrase; "beforehand" ends its clause.
                && !(split.joined == "beforehand" && spelling::flags(next) & 2 != 0)
            {
                push(req, edits, &span[0], &span[n - 1], split.joined);
            }
        }
        if let Some((last, joined)) = adverb_join(text, tokens, i) {
            push(req, edits, token, &tokens[last], joined);
            continue;
        }
        if !plain(text, &tokens[i..=i]) {
            continue;
        }
        let next_token = tokens.get(i + 1);
        let next = word(tokens, Some(i + 1), paragraph);
        let ends = next_token.is_none_or(|n| !n.is_word || n.paragraph != paragraph);
        // "I'll backup the files", "to setup the room": the verb, not the noun.
        if let Some((_, phrase)) = PHRASAL.iter().find(|(noun, _)| *noun == lower) {
            // After "to" the noun is as likely ("go to checkout"), so an object must follow.
            let verb_slot =
                VERB_LEADS.contains(&prev) && (prev != "to" || OBJECT_START.contains(&next));
            let noun_after = !next.is_empty()
                && spelling::flags(next) & 2 != 0
                && !OBJECT_START.contains(&next)
                && ![
                    "now", "later", "today", "tonight", "tomorrow", "first", "again", "once",
                    "twice", "two", "three", "four", "five", "daily", "every", "hard", "together",
                ]
                .contains(&next);
            if verb_slot && !noun_after {
                push(req, edits, token, token, phrase);
            }
            continue;
        }
        match lower {
            // "log in everyday to check": the adverbial phrase, not the adjective ("everyday life").
            "everyday"
                if !DETERMINERS.contains(&prev)
                    && (ends
                        || [
                            "to", "at", "in", "on", "for", "and", "but", "so", "because", "if",
                            "until", "after", "before", "with", "this", "that", "of", "or",
                        ]
                        .contains(&next)) =>
            {
                push(req, edits, token, token, "every day");
            }
            // "need anymore help": "any more" before a noun; "anymore" ends a negative clause.
            "anymore"
                if !next.is_empty()
                    && spelling::flags(next) & 2 != 0
                    && ![
                        "today", "tonight", "now", "though", "either", "anyway", "yet", "lol",
                        "honestly", "thanks", "man", "dude", "bro", "guys", "these", "lately",
                    ]
                    .contains(&next) =>
            {
                push(req, edits, token, token, "any more");
            }
            _ => {}
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn fixed(text: &str) -> String {
        let req = Request {
            text: text.into(),
            ..Request::default()
        };
        let tokens = crate::tokenizer::tokenize(text, &[]);
        let mut edits = vec![];
        check(&req, &tokens, &mut edits);
        crate::apply_edits(text, &edits).unwrap().0
    }
    #[test]
    fn split_compounds_are_joined() {
        for (input, output) in [
            (
                "Back up the data base nightly.",
                "Back up the database nightly.",
            ),
            ("She did it her self.", "She did it herself."),
            (
                "The keys are some where here.",
                "The keys are somewhere here.",
            ),
            (
                "I left my note book at home.",
                "I left my notebook at home.",
            ),
            ("Never the less, it worked.", "Nevertheless, it worked."),
            (
                "It rained. How ever, we went.",
                "It rained. However, we went.",
            ),
            ("We left any way, sadly.", "We left anyway, sadly."),
            ("Has any one called back?", "Has anyone called back?"),
            ("Press the short cut twice.", "Press the shortcut twice."),
            ("We had a quick break fast.", "We had a quick breakfast."),
        ] {
            assert_eq!(fixed(input), output, "{input}");
        }
        for text in [
            "Please note book prices rose.",
            "They break fast at sunset.",
            "Is any body of water safe?",
            "How ever did you do it?",
            "Is there any way, though, to fix it?",
            "Help in any way, please.",
            "Can any one of you help?",
            "Did any one person win?",
            "She got a short cut at the salon.",
            "Use the WHERE clause, or no where clause at all.",
            "Run my_self.py first.",
        ] {
            assert_eq!(fixed(text), text, "{text}");
        }
    }
    #[test]
    fn noun_compounds_used_as_verbs_are_split() {
        for (input, output) in [
            ("I'll setup the call.", "I'll set up the call."),
            (
                "You should backup your phone.",
                "You should back up your phone.",
            ),
            (
                "We need to cleanup the repo.",
                "We need to clean up the repo.",
            ),
            ("Please login.", "Please log in."),
            ("I workout every morning.", "I work out every morning."),
            ("I check email everyday.", "I check email every day."),
            (
                "Do you need anymore chairs?",
                "Do you need any more chairs?",
            ),
        ] {
            assert_eq!(fixed(input), output, "{input}");
        }
        for text in [
            "The setup took an hour.",
            "Go to checkout.",
            "Click the login button.",
            "My workout was hard.",
            "I need a backup plan.",
            "It is an everyday thing.",
            "I don't drink coffee anymore.",
            "You can login page by page.",
        ] {
            assert_eq!(fixed(text), text, "{text}");
        }
    }
}
