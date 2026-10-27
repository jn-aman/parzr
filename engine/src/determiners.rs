//! Determiners and the number they carry: "a" or "an" by sound, one noun after "a", "this" and
//! "these", "much" and "many", "there is" and "there are", and a helping verb that agrees with a
//! determiner phrase or pronoun subject.
use crate::{
    Edit, Request,
    clause_repairs::{SUBJECTS, clause_start, push, span, word},
    morphology, spelling,
    structure::plural,
    tokenizer::Token,
};

/// Whether "an" (rather than "a") goes before this word, from its spelling; None when unclear.
pub fn an_fits(word: &str) -> Option<bool> {
    let w: String = word
        .chars()
        .take_while(|c| c.is_alphanumeric() || *c == '-')
        .collect();
    let first = w.chars().next()?;
    if !first.is_alphabetic() {
        return None;
    }
    let letters: Vec<char> = w.chars().take_while(|c| c.is_alphabetic()).collect();
    let l = w.to_lowercase();
    // An abbreviation or a letter said by its name ("an MBA", "a URL", "an A"); a long ordinary
    // word in capitals ("A FANTASTIC FUTURE") is just shouted and follows its sound.
    if letters.iter().all(|c| c.is_uppercase())
        && (letters.len() >= 2 || w.len() == 1)
        && !(letters.len() >= 5 && spelling::ordinary(&l))
    {
        return acronym_an(&letters);
    }
    let starts = |list: &[&str]| list.iter().any(|p| l.starts_with(p));
    match first.to_ascii_lowercase() {
        'a' | 'i' => Some(true),
        'e' => Some(!starts(&["eu", "ewe"])),
        'o' => Some(!starts(&["one", "once"])),
        // "an unintentional", "an unidentified" are "un-" words; "a union", "a unit" say "yoo".
        'u' => Some(
            l.len() > 1
                && !starts(&[
                    "unif", "unio", "uniq", "unit", "univ", "unic", "unil", "unip", "unis", "unix",
                    "use", "usu", "uti", "ura", "ure", "uri", "uro", "ubiq", "uku", "unanim", "uk",
                    "ute",
                ]),
        ),
        // American English says "an herb".
        'h' => Some(starts(&[
            "hour", "honest", "honor", "honour", "heir", "herb",
        ])),
        'x' | 'y' => None,
        _ => Some(false),
    }
}
/// Acronyms said as one word whose first letter is named with a vowel ("en", "ef", "el", "em",
/// "ar", "ess", "eks"): "a RAM upgrade", not "an RAM". The longer ones are found by shape
/// (`said_as_word`); the three-letter ones are too short for a shape, so they are listed.
const SPOKEN_SHORT: [&str; 8] = ["RAM", "ROM", "LAN", "SIM", "MAC", "SAN", "NAS", "FAT"];
/// Acronyms people say both ways ("a FAQ" as "fack", "an FAQ" as "eff-ay-cue"; "sequel" or "ess-cue-el"): either
/// article is right, so neither is corrected.
const EITHER_SOUND: [&str; 6] = ["FAQ", "SQL", "SAT", "SAP", "SOC", "NOC"];
/// Letters that start a consonant cluster of an English word ("SC-uba", "SM-art", "ST-em").
const ONSETS: [&str; 24] = [
    "BL", "BR", "CH", "CL", "CR", "DR", "FL", "FR", "GL", "GR", "PL", "PR", "SC", "SH", "SK", "SL",
    "SM", "SN", "SP", "ST", "SW", "TH", "TR", "TW",
];
/// Two consonants an English word can end in ("SMA-RT", "LA-MP", "FAA-NG").
const CODAS: [&str; 24] = [
    "ST", "SK", "SP", "LT", "LD", "ND", "NT", "NK", "RT", "RD", "RK", "RM", "RN", "LF", "LK", "LM",
    "LP", "MP", "FT", "PT", "CT", "NS", "RS", "NG",
];
/// Whether an all-capital acronym of four to eight letters reads as a word ("NASA", "NATO",
/// "FIFA", "SCUBA") rather than letter by letter ("NCAA", "HTML", "MSNBC", "NAACP"): a vowel
/// opens it or follows its first consonant (or an English cluster), and it ends in a vowel, one
/// consonant or a pair English words end in.
fn said_as_word(letters: &[char]) -> bool {
    if !(4..=8).contains(&letters.len()) || !letters.iter().all(char::is_ascii_uppercase) {
        return false;
    }
    let vowel = |c: char| "AEIOU".contains(c);
    let at = |i: usize| letters[i];
    let cluster: String = [at(0), at(1)].iter().collect();
    let onset = vowel(at(0)) || vowel(at(1)) || ONSETS.contains(&cluster.as_str()) && vowel(at(2));
    // "Y" ends a word as a vowel does ("NIMBY").
    let open = |c: char| vowel(c) || c == 'Y';
    let end = letters.len() - 1;
    let coda: String = [letters[end - 1], letters[end]].iter().collect();
    let ends = open(letters[end]) || open(letters[end - 1]) || CODAS.contains(&coda.as_str());
    onset && ends && letters.iter().any(|c| vowel(*c))
}
/// "an" or "a" before an acronym or a letter said by its name: None where people say it both ways.
fn acronym_an(letters: &[char]) -> Option<bool> {
    let word: String = letters.iter().collect();
    if EITHER_SOUND.contains(&word.as_str()) {
        return None;
    }
    let first = *letters.first()?;
    // The letters of "NBA", "FBI" and "HR" begin with a vowel sound if their first letter is named so.
    let named = "AEFHILMNORSX".contains(first);
    if !named {
        return Some(false);
    }
    // "A NASA mission", "a Europol unit": said as a word, the first sound is the word's, a
    // consonant for the names of F, H, L, M, N, R, S and X and for "EU" said "yoo".
    if SPOKEN_SHORT.contains(&word.as_str())
        || said_as_word(letters) && (!"AEIO".contains(first) || word.starts_with("EU"))
    {
        return Some(false);
    }
    Some(true)
}
/// "a engineer", "an huge": the article's form follows the sound of the next word. Only an ordinary
/// word that can follow an article counts, never a letter or code ("the letter a is").
fn article_sound(req: &Request, s: &[Token<'_>], edits: &mut Vec<Edit>) {
    for i in 0..s.len().saturating_sub(1) {
        let t = &s[i];
        let lower = t.surface.chars().all(char::is_lowercase);
        if !["a", "an"].contains(&t.normalized.as_str()) || !(lower || i == 0) {
            continue;
        }
        let next = &s[i + 1];
        let w = next.normalized.as_str();
        // Glued to a hyphen, digit or quote ("a-b", "a 'x'"), or a single letter: leave it.
        if !next.is_word
            || req.text[t.end_byte..next.start_byte] != *" "
            || w.chars().count() < 2
                && !(next.surface.len() == 1
                    && next.surface != "I"
                    && next.surface.chars().all(char::is_uppercase))
            || spelling::flags(w) & (2 | 8) == 0 && !next.surface.chars().all(|c| c.is_uppercase())
            // Function words never follow an article: "an then" is a slip for "and then", not "a then".
            || [
                "and", "or", "is", "of", "in", "then", "than", "the", "that", "to", "at", "on", "as",
                "it", "its", "if", "so", "but", "by", "for", "from", "with",
            ]
            .contains(&w)
            // "I an going": after a subject pronoun "an" is a slip for "am", not an article.
            || i > 0 && SUBJECTS.contains(&word(s, i - 1))
            // "a A$1.5 billion": the letter belongs to a currency or code.
            || req.text[next.end_byte..].starts_with(|c: char| c.is_alphanumeric() || "$€£¥#/_-".contains(c))
        {
            continue;
        }
        let Some(an) = an_fits(next.surface) else {
            continue;
        };
        if an == (t.normalized == "an") {
            continue;
        }
        let form = if an { "an" } else { "a" };
        push(
            req,
            edits,
            span(s, i, i),
            crate::match_case(form, t.surface),
            "grammar.article_sound",
            if an {
                "Use “an” before a vowel sound."
            } else {
                "Use “a” before a consonant sound."
            },
            0.96,
        );
    }
}
/// The singular of a regular plural noun the lexicon knows ("experts" to "expert").
fn singular(w: &str) -> Option<String> {
    let noun = |x: &str| spelling::flags(x) & 2 != 0 && spelling::ordinary(x);
    if let Some(stem) = w.strip_suffix("ies") {
        let y = format!("{stem}y");
        return noun(&y).then_some(y);
    }
    if let Some(stem) = w.strip_suffix("es")
        && ["s", "sh", "ch", "x", "z"]
            .iter()
            .any(|e| stem.ends_with(e))
        && noun(stem)
    {
        return Some(stem.to_owned());
    }
    let stem = w.strip_suffix('s')?;
    (!stem.ends_with('s') && noun(stem)).then(|| stem.to_owned())
}
/// "an experts in": one article, one noun. A plural that names one thing ("a savings account",
/// "a means") or that modifies a following noun ("a sports car") is left alone.
fn article_number(req: &Request, s: &[Token<'_>], edits: &mut Vec<Edit>) {
    for i in 0..s.len().saturating_sub(2) {
        if !["a", "an"].contains(&s[i].normalized.as_str()) || !s[i + 1].is_word {
            continue;
        }
        // "Q&A Facts", "R&A teams": an "A" glued to the mark before it is no article.
        if i > 0 && s[i - 1].end_byte == s[i].start_byte {
            continue;
        }
        // "influenza A viruses": a capital A in mid-sentence is a label, not the article.
        if s[i].surface == "A" && i > 0 {
            continue;
        }
        let w = s[i + 1].normalized.as_str();
        let after = &s[i + 2];
        // "a boys' football team", "a waiters' strike": the plural is a possessive.
        let possessive =
            ["'", "’"].contains(&after.surface) && after.start_byte == s[i + 1].end_byte;
        // "a Worlds Ahead student": a capitalized plural in mid-sentence is a title or a name.
        let title = s[i + 1].surface.starts_with(char::is_uppercase) && i > 0;
        // "a hands-on experience", "a sales-driven team", "a needs-based grant": a plural that is
        // the first part of a hyphenated modifier is part of the compound, not a noun of its own.
        let compound = ["-", "‐"].contains(&after.surface)
            && after.start_byte == s[i + 1].end_byte
            && s.get(i + 3)
                .is_some_and(|n| n.is_word && n.start_byte == after.end_byte);
        if compound
            || possessive
            || title
            || s[i + 1].proper_name
            || w.len() < 4
            || [
                "news",
                "series",
                "species",
                "means",
                "sales",
                "savings",
                "arms",
                "goods",
                "odds",
                "glasses",
                "jeans",
                "pants",
                "scissors",
                "clothes",
                "headquarters",
                "physics",
                "politics",
                "economics",
                "athletics",
                "thanks",
                "sports",
                "series",
                "lots",
                "masters",
                "bachelors",
                "mens",
                "womens",
            ]
            .contains(&w)
            || after.is_word
                && spelling::flags(&after.normalized) & (2 | 8) != 0
                && ![
                    "in", "on", "at", "of", "for", "to", "with", "from", "by", "about", "and",
                    "or", "but", "who", "that", "which", "is", "are", "was", "were", "will", "can",
                ]
                .contains(&after.normalized.as_str())
            || after.normalized == "'s"
        {
            continue;
        }
        let Some(one) = singular(w) else { continue };
        // The article must still fit the singular's sound ("an experts" to "an expert").
        if an_fits(&one).is_some_and(|an| an != (s[i].normalized == "an")) {
            continue;
        }
        push(
            req,
            edits,
            span(s, i + 1, i + 1),
            one,
            "grammar.article_number",
            "“A” or “an” goes with one thing: use the singular noun.",
            0.93,
        );
    }
}
/// "The age don't matter", "they interests me": a noun or pronoun subject and its verb disagree.
fn subject_agreement(req: &Request, s: &[Token<'_>], edits: &mut Vec<Edit>) {
    const DET: [&str; 10] = [
        "the", "this", "that", "my", "your", "his", "her", "our", "their", "each",
    ];
    for i in 0..s.len().saturating_sub(2) {
        // A determiner, its noun and a negated do at the start of the clause.
        if DET.contains(&word(s, i)) && clause_start(s, i) {
            let aux = word(s, i + 2);
            let fix = match (plural(&s[i + 1]), aux) {
                (Some(false), "don't")
                    if word(s, i) != "the" || spelling::flags(word(s, i + 1)) & 2 != 0 =>
                {
                    "doesn't"
                }
                (Some(true), "doesn't") => "don't",
                _ => continue,
            };
            push(
                req,
                edits,
                span(s, i + 2, i + 2),
                crate::match_case(fix, s[i + 2].surface),
                "grammar.subject_do_agreement",
                "Match the helping verb to its subject.",
                0.95,
            );
            continue;
        }
        // A plural pronoun with a verb in the "-s" form.
        let p = word(s, i);
        if !["i", "you", "we", "they"].contains(&p) || !clause_start(s, i) {
            continue;
        }
        let w = word(s, i + 1);
        let Some(v) = morphology::verb(w) else {
            continue;
        };
        let next = &s[i + 2];
        if w != v.third
            || v.third == v.base
            || ["be", "have", "do"].contains(&v.base.as_str())
            || spelling::flags(&v.base) & 4 == 0
            || crate::punctuation::finite(next)
            || morphology::verb(&next.normalized).is_some_and(|n| n.base == next.normalized)
        {
            continue;
        }
        push(
            req,
            edits,
            span(s, i + 1, i + 1),
            v.base.clone(),
            "grammar.subject_base",
            "Use the base present-tense verb with this plural subject.",
            0.94,
        );
    }
}
/// A noun that is plural in form and never a verb ("stories", "puppies"; not "issues" or "costs",
/// which also follow the pronoun "this" as verbs).
fn plural_noun(t: &Token<'_>) -> bool {
    let w = t.normalized.as_str();
    t.is_word
        && !t.proper_name
        && plural(t) == Some(true)
        && w.ends_with('s')
        && spelling::flags(w) & 4 == 0
        && singular_known(w)
}
fn singular_known(w: &str) -> bool {
    singular(w).is_some()
}
/// One noun that has no plural reading ("guy", "furniture", "weather").
fn singular_noun(t: &Token<'_>) -> bool {
    let w = t.normalized.as_str();
    t.is_word
        && !t.proper_name
        && plural(t) == Some(false)
        && spelling::flags(w) & 2 != 0
        && !w.ends_with('s')
        && !crate::punctuation::finite(t)
        && !["kind", "sort", "type", "one", "lot", "day", "time", "way"].contains(&w)
}
/// A regular plural noun, whether or not the same spelling is also a verb ("files", "cooks").
fn plural_form(t: &Token<'_>) -> bool {
    let w = t.normalized.as_str();
    t.is_word
        && !t.proper_name
        && plural(t) == Some(true)
        && w.ends_with('s')
        && singular_known(w)
        // "does" is a verb before it is the plural of "doe".
        && !morphology::verb(w).is_some_and(|v| ["be", "have", "do", "go"].contains(&v.base.as_str()))
}
/// Words before "this" or "that" that make it a determiner: a preposition, or a verb taking an
/// object ("print this pages"). Verbs of saying and thinking take a clause ("I think this works").
fn object_position(s: &[Token<'_>], i: usize) -> bool {
    if i == 0 {
        return false;
    }
    let p = word(s, i - 1);
    if [
        "of", "at", "for", "on", "in", "with", "from", "to", "about", "into", "by", "all", "are",
        "were",
    ]
    .contains(&p)
    {
        return true;
    }
    morphology::verb(p).is_some_and(|v| {
        spelling::flags(p) & 4 != 0
            && ![
                "be", "have", "do", "think", "know", "say", "believe", "hope", "guess", "feel",
                "bet", "mean", "suppose", "find", "tell", "show", "realize", "wish", "make", "let",
            ]
            .contains(&v.base.as_str())
    })
}
/// "this pages", "these furniture": a demonstrative takes the number of its noun.
fn demonstratives(req: &Request, s: &[Token<'_>], edits: &mut Vec<Edit>) {
    for i in 0..s.len().saturating_sub(1) {
        let d = word(s, i);
        // "check that that directories": the doubled word is the slip, not the number.
        if i > 0 && word(s, i - 1) == d {
            continue;
        }
        // One adjective may come first ("this cute puppies").
        let n = if spelling::flags(word(s, i + 1)) & 8 != 0
            && spelling::flags(word(s, i + 2)) & 2 != 0
        {
            i + 2
        } else {
            i + 1
        };
        let noun = &s[n];
        // "These Q&A Facts", "this API": a title-case or acronym noun names something; its
        // number is the name's.
        if s[i + 1..=n]
            .iter()
            .any(|t| t.surface.chars().any(char::is_uppercase))
        {
            continue;
        }
        // "this weeks pool", "this years budget": a time word before another noun lost its
        // possessive apostrophe.
        if [
            "weeks", "months", "years", "days", "quarters", "seasons", "mornings", "nights",
        ]
        .contains(&noun.normalized.as_str())
            && s.get(n + 1)
                .is_some_and(|a| a.is_word && spelling::flags(&a.normalized) & 2 != 0)
            && ["this", "that"].contains(&d)
        {
            continue;
        }
        // A noun that goes on into a compound ("this sports car") is a modifier.
        let ends = s.get(n + 1).is_none_or(|a| {
            let f = spelling::flags(&a.normalized);
            !a.is_word
                || f & 2 == 0
                || f & 4 != 0
                || [
                    "today",
                    "tomorrow",
                    "tonight",
                    "yesterday",
                    "again",
                    "now",
                    "first",
                ]
                .contains(&a.normalized.as_str())
        });
        let object = object_position(s, i);
        // As a subject "this" or "that" may take an "-s" verb ("this costs", "that works"), so
        // there the noun must have no verb reading.
        // After "see" or "hear" a clause can follow too ("I see this works"): a noun that is also a
        // common verb stays.
        let perceived = i > 0
            && morphology::verb(word(s, i - 1))
                .is_some_and(|v| ["see", "hear"].contains(&v.base.as_str()))
            && singular(&noun.normalized).is_some_and(|one| morphology::predicate(&one));
        let plural_here = if object || i == 0 && ["are", "were"].contains(&word(s, n + 1)) {
            plural_form(noun) && !perceived
        } else {
            plural_noun(noun)
        };
        let prep = i > 0
            && [
                "of", "at", "for", "on", "in", "with", "from", "to", "about", "into", "by", "all",
                "are", "were",
            ]
            .contains(&word(s, i - 1));
        let that_ok = prep
            || object && plural_noun(noun)
            || i == 0 && (plural_noun(noun) || ["are", "were"].contains(&word(s, n + 1)));
        // "that returns a 429": a verb reading with its own object.
        let verb_object = spelling::flags(&noun.normalized) & 4 != 0
            && [
                "a", "an", "the", "my", "your", "it", "them", "me", "us", "him", "this", "that",
            ]
            .contains(&word(s, n + 1));
        if verb_object && !prep {
            continue;
        }
        // "similar to those that you put together": a pronoun before a relative clause.
        if ["that", "who", "which", "whom", "whose", "where", "when"]
            .contains(&noun.normalized.as_str())
        {
            continue;
        }
        // "see that final agreements are forwarded": a "that" with a clause after it is the
        // conjunction.
        if d == "that"
            && i > 0
            && !prep
            && [
                "are", "were", "have", "is", "was", "will", "can", "could", "should", "would",
                "must", "may", "might", "do", "don't", "get", "go",
            ]
            .contains(&word(s, n + 1))
        {
            continue;
        }
        let fix = match d {
            "this" if plural_here && ends => "these",
            // "that" also opens a clause ("I know that kids love it"): only as a determiner.
            "that" if plural_here && ends && that_ok => "those",
            "these" if singular_noun(noun) && ends => "this",
            "those" if singular_noun(noun) && ends && word(s, n + 1) != "who" => "that",
            _ => continue,
        };
        push(
            req,
            edits,
            span(s, i, i),
            crate::match_case(fix, s[i].surface),
            "grammar.demonstrative_number",
            "Match “this” or “these” to the number of the noun.",
            0.95,
        );
    }
}
/// "less complaints", "too much cooks", "an another": the quantifier follows the noun's number.
fn quantifiers(req: &Request, s: &[Token<'_>], edits: &mut Vec<Edit>) {
    for i in 0..s.len().saturating_sub(1) {
        let q = word(s, i);
        let next = &s[i + 1];
        if q == "an" && next.normalized == "another" {
            push(
                req,
                edits,
                (s[i].start_utf16, next.start_utf16),
                String::new(),
                "grammar.another_article",
                "“Another” already includes the article.",
                0.97,
            );
            continue;
        }
        let fix = match q {
            "less" if plural_form(next) => "fewer",
            "much" if plural_form(next) && !["thanks"].contains(&next.normalized.as_str()) => {
                "many"
            }
            _ => continue,
        };
        // "much more", "less than": only a quantifier straight before its noun.
        push(
            req,
            edits,
            span(s, i, i),
            crate::match_case(fix, s[i].surface),
            "grammar.quantifier_number",
            "Use “fewer” and “many” with countable plural nouns.",
            0.95,
        );
    }
}
/// "There's three emails", "Is there any snacks", "There are a problem": the verb of "there is"
/// agrees with the noun after it.
fn there_be(req: &Request, s: &[Token<'_>], edits: &mut Vec<Edit>) {
    const NUMBERS: [&str; 15] = [
        "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "many", "several",
        "few", "both", "dozens", "hundreds",
    ];
    // Whether the noun phrase starting at `k` is plural (Some(true)), one thing (Some(false)) or unclear.
    let number = |mut k: usize| -> Option<bool> {
        while [
            "still", "also", "just", "only", "really", "so", "now", "too",
        ]
        .contains(&word(s, k))
        {
            k += 1;
        }
        let w = word(s, k);
        if NUMBERS.contains(&w)
            || w.chars().all(|c| c.is_ascii_digit()) && !w.is_empty() && w != "1"
        {
            return Some(true);
        }
        if [
            "some", "any", "the", "these", "those", "no", "my", "your", "our", "their",
        ]
        .contains(&w)
        {
            let mut n = k + 1;
            if s.get(n).is_some_and(|t| spelling::adjective(t)) {
                n += 1;
            }
            return s.get(n).filter(|t| plural_form(t)).map(|_| true);
        }
        if ["a", "an", "one"].contains(&w)
            && ![
                "lot", "few", "couple", "number", "bunch", "variety", "total", "lots", "pair",
                "dozen",
            ]
            .contains(&word(s, k + 1))
        {
            return Some(false);
        }
        None
    };
    for i in 0..s.len().saturating_sub(1) {
        let w = word(s, i);
        // "there's" / "here's", or "there is" / "there was" / "here is".
        let (be_at, after, many) = match w {
            "there's" | "here's" => (i, i + 1, false),
            "there" | "here" if ["is", "are", "was", "were"].contains(&word(s, i + 1)) => {
                (i + 1, i + 2, ["are", "were"].contains(&word(s, i + 1)))
            }
            // "Is there any snacks left?"
            "is" | "are" | "was" | "were" if word(s, i + 1) == "there" && i == 0 => {
                (i, i + 2, ["are", "were"].contains(&w))
            }
            _ => continue,
        };
        let Some(plural_np) = number(after) else {
            continue;
        };
        if plural_np == many {
            continue;
        }
        let be = word(s, be_at);
        let past = ["was", "were"].contains(&be);
        let fixed_be = match (plural_np, past) {
            (true, false) => "are",
            (true, true) => "were",
            (false, false) => "is",
            (false, true) => "was",
        };
        let replacement = if be.ends_with("'s") {
            let stem = &s[be_at].surface
                [..s[be_at].surface.len() - 2 - usize::from(s[be_at].surface.ends_with("’s")) * 2];
            format!("{stem} {fixed_be}")
        } else {
            crate::match_case(fixed_be, s[be_at].surface)
        };
        push(
            req,
            edits,
            span(s, be_at, be_at),
            replacement,
            "grammar.there_agreement",
            "After “there”, the verb agrees with the noun that follows.",
            0.95,
        );
    }
}
/// "Does they have", "Has they confirmed", "Was you there": a question's opening auxiliary agrees
/// with the pronoun after it.
fn opening_auxiliary(req: &Request, s: &[Token<'_>], edits: &mut Vec<Edit>, question: bool) {
    if !question || s.len() < 3 {
        return;
    }
    let (aux, subject) = (word(s, 0), word(s, 1));
    if !SUBJECTS.contains(&subject) {
        return;
    }
    let one = ["he", "she", "it"].contains(&subject);
    let fix = match (aux, subject) {
        ("does", _) if !one => "do",
        ("do", _) if one => "does",
        ("has", _) if !one => "have",
        ("have", _) if one => "has",
        ("was", "you" | "we" | "they") => "were",
        ("were", "i" | "he" | "she" | "it") => "was",
        ("is", "you" | "we" | "they") => "are",
        ("is", "i") | ("are", "i") => "am",
        ("are", _) if one => "is",
        ("doesn't", _) if !one => "don't",
        ("don't", _) if one => "doesn't",
        _ => return,
    };
    push(
        req,
        edits,
        span(s, 0, 0),
        crate::match_case(fix, s[0].surface),
        "grammar.inverted_subject_agreement",
        "Match the inverted auxiliary to its subject.",
        0.95,
    );
}
pub fn check(req: &Request, s: &[Token<'_>], edits: &mut Vec<Edit>, question: bool) {
    article_sound(req, s, edits);
    article_number(req, s, edits);
    subject_agreement(req, s, edits);
    demonstratives(req, s, edits);
    quantifiers(req, s, edits);
    there_be(req, s, edits);
    opening_auxiliary(req, s, edits, question);
}
#[cfg(test)]
mod tests {
    use crate::Request;
    fn fix(text: &str) -> String {
        crate::pipeline::rewrite(&Request {
            text: text.into(),
            ..Request::default()
        })
        .unwrap()
        .text
    }
    #[test]
    fn acronyms_said_as_words_take_a_and_letters_take_an() {
        // Said as a word, the first sound is the word's: "a NASA", "a RAM", "a LAN", "a SIM".
        for noun in [
            "NASA", "NATO", "FIFA", "NAFTA", "UNICEF", "UNESCO", "SCUBA", "SWAT", "NASDAQ",
            "FAANG", "HIPAA", "LIDAR", "RAM", "ROM", "LAN", "SIM", "JSON", "PIN",
        ] {
            let right = format!("It was a {noun} decision.");
            assert_eq!(fix(&right), right, "{right}");
            let wrong = format!("It was an {noun} decision.");
            assert_eq!(fix(&wrong), right, "{wrong}");
        }
        // Said letter by letter, a first letter named with a vowel sound takes "an".
        for noun in [
            "NBA", "NFL", "FBI", "MBA", "HR", "SMS", "MRI", "LLM", "HTML", "NCAA", "NHS", "SUV",
            "RSVP", "NAACP", "MSNBC", "SMTP", "OPEC", "ASAP", "EU", "FDA", "XML",
        ] {
            let right = format!("It was an {noun} decision.");
            assert_eq!(fix(&right), right, "{right}");
            let wrong = format!("It was a {noun} decision.");
            assert_eq!(fix(&wrong), right, "{wrong}");
        }
        // A letter or a word that begins with a "yoo" sound takes "a"; "URL" and "UFO" are such.
        for (wrong, right) in [
            ("Open an URL in a tab.", "Open a URL in a tab."),
            ("We saw an UFO last night.", "We saw a UFO last night."),
            ("He is an UN envoy.", "He is a UN envoy."),
        ] {
            assert_eq!(fix(wrong), right, "{wrong}");
        }
        // Said both ways ("fack" and "eff-ay-cue", "sequel" and "ess-cue-el"): neither is wrong.
        for text in [
            "Read a FAQ page first.",
            "Read an FAQ page first.",
            "Write a SQL query.",
            "Write an SQL query.",
            "Take a SAT prep class.",
            "Take an SAT prep class.",
        ] {
            assert_eq!(fix(text), text, "{text}");
        }
        // A long word in capitals is a shouted word, not an acronym.
        assert_eq!(fix("A FANTASTIC FUTURE"), "A FANTASTIC FUTURE");
        assert_eq!(fix("A EXCELLENT PLAN"), "An EXCELLENT PLAN");
        // Ordinary words keep following the sound of the word.
        assert_eq!(fix("She is a engineer."), "She is an engineer.");
        assert_eq!(fix("It was an huge win."), "It was a huge win.");
        assert_eq!(fix("He took an X-ray."), "He took an X-ray.");
    }
    #[test]
    fn words_that_begin_with_un_take_an_and_those_that_begin_with_yoo_take_a() {
        for text in [
            "It was an unintentional slip.",
            "That is an unanswerable question.",
            "We work in an unincorporated area.",
            "She wore an unidentified badge.",
            "He gave an uninformed answer.",
            "We joined a union.",
            "It is a unique case.",
            "Use a unit test.",
            "Visit a university.",
            "It was a unanimous vote.",
        ] {
            assert_eq!(fix(text), text, "{text}");
        }
        assert_eq!(
            fix("It was a unintentional slip."),
            "It was an unintentional slip."
        );
        assert_eq!(fix("We joined an union."), "We joined a union.");
    }
    #[test]
    fn a_possessive_plural_a_label_or_a_title_after_a_is_no_plural_noun() {
        for text in [
            "Every school has a boys' football team.",
            "I heard about a waiters' strike.",
            "It is a Worlds Ahead student programme.",
            "Specimens of influenza A viruses were tested.",
        ] {
            assert_eq!(fix(text), text, "{text}");
        }
    }
    #[test]
    fn a_plural_that_starts_a_hyphenated_modifier_is_not_a_noun_of_its_own() {
        for text in [
            "It was a hands-on experience for the whole class.",
            "We want a sales-driven culture.",
            "She needs a systems-level view of the project.",
            "It is a needs-based grant.",
            "They kept it at an arms-length distance.",
            "He wrote a thank-you note and a rules-based filter.",
        ] {
            assert_eq!(fix(text), text, "{text}");
        }
        // One article, one noun: a plural noun after it is still made singular.
        assert_eq!(
            fix("We asked an experts in the field."),
            "We asked an expert in the field."
        );
    }
}
