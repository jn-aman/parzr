//! English inflection shared by structural grammar and spelling candidate ranking.
//! Authored paradigms; regular forms are accepted only when present in the lexicon.
use crate::spelling;
use std::sync::OnceLock;

#[derive(Clone, Debug)]
pub struct Verb {
    pub base: String,
    pub third: String,
    pub past: String,
    pub participle: String,
    pub gerund: String,
}
fn irregular() -> &'static [Verb] {
    static VERBS: OnceLock<Vec<Verb>> = OnceLock::new();
    VERBS.get_or_init(|| {
        // Surface ambiguity (read, put, cut) is retained, never forced into present tense.
        const ROWS: &str = "be is was been being
have has had had having
do does did done doing
go goes went gone going
buy buys bought bought buying
come comes came come coming
tell tells told told telling
know knows knew known knowing
write writes wrote written writing
read reads read read reading
see sees saw seen seeing
send sends sent sent sending
take takes took taken taking
give gives gave given giving
make makes made made making
get gets got got getting
find finds found found finding
think thinks thought thought thinking
bring brings brought brought bringing
leave leaves left left leaving
say says said said saying
run runs ran run running
eat eats ate eaten eating
drink drinks drank drunk drinking
begin begins began begun beginning
break breaks broke broken breaking
choose chooses chose chosen choosing
drive drives drove driven driving
fall falls fell fallen falling
feel feels felt felt feeling
forget forgets forgot forgotten forgetting
grow grows grew grown growing
hear hears heard heard hearing
hold holds held held holding
keep keeps kept kept keeping
lose loses lost lost losing
meet meets met met meeting
pay pays paid paid paying
put puts put put putting
sell sells sold sold selling
sit sits sat sat sitting
sleep sleeps slept slept sleeping
speak speaks spoke spoken speaking
spend spends spent spent spending
stand stands stood stood standing
teach teaches taught taught teaching
understand understands understood understood understanding
wear wears wore worn wearing
win wins won won winning
build builds built built building
catch catches caught caught catching
cut cuts cut cut cutting
draw draws drew drawn drawing
fight fights fought fought fighting
fly flies flew flown flying
hide hides hid hidden hiding
lead leads led led leading
lend lends lent lent lending
let lets let let letting
lie lies lay lain lying
lay lays laid laid laying
ride rides rode ridden riding
rise rises rose risen rising
shake shakes shook shaken shaking
sing sings sang sung singing
swim swims swam swum swimming
throw throws threw thrown throwing
become becomes became become becoming";
        ROWS.lines()
            .map(|line| {
                let forms: Vec<_> = line.split_whitespace().collect();
                Verb {
                    base: forms[0].into(),
                    third: forms[1].into(),
                    past: forms[2].into(),
                    participle: forms[3].into(),
                    gerund: forms[4].into(),
                }
            })
            .collect()
    })
}
pub fn from_base(base: &str) -> Option<Verb> {
    if let Some(v) = irregular().iter().find(|v| v.base == base) {
        return Some(v.clone());
    }
    if spelling::flags(base) & 4 == 0 && !(spelling::known(base) && predicate(base)) {
        return None;
    }
    let consonant_y = base.ends_with('y')
        && base
            .as_bytes()
            .get(base.len().saturating_sub(2))
            .is_some_and(|c| !b"aeiou".contains(c));
    let third = if consonant_y {
        format!("{}ies", &base[..base.len() - 1])
    } else if ["s", "sh", "ch", "x", "z", "o"]
        .iter()
        .any(|s| base.ends_with(s))
    {
        format!("{base}es")
    } else {
        format!("{base}s")
    };
    let mut past = if base.ends_with('e') {
        format!("{base}d")
    } else if consonant_y {
        format!("{}ied", &base[..base.len() - 1])
    } else {
        format!("{base}ed")
    };
    if !spelling::known(&past)
        && let Some(c) = base.chars().last()
    {
        let doubled = format!("{base}{c}ed");
        if spelling::known(&doubled) {
            past = doubled;
        }
    }
    let mut gerund = if let Some(stem) = base.strip_suffix("ie") {
        format!("{stem}ying")
    } else if base.ends_with('e') && !base.ends_with("ee") {
        format!("{}ing", &base[..base.len() - 1])
    } else {
        format!("{base}ing")
    };
    if !spelling::known(&gerund)
        && let Some(c) = base.chars().last()
    {
        let doubled = format!("{base}{c}ing");
        if spelling::known(&doubled) {
            gerund = doubled;
        }
    }
    Some(Verb {
        base: base.into(),
        third,
        participle: past.clone(),
        past,
        gerund,
    })
}
pub fn verb(word: &str) -> Option<Verb> {
    if ["am", "are", "were"].contains(&word) {
        return from_base("be");
    }
    if let Some(v) = irregular()
        .iter()
        .find(|v| [v.base.as_str(), &v.third, &v.past, &v.participle, &v.gerund].contains(&word))
    {
        return Some(v.clone());
    }
    if !word.is_ascii() {
        return None;
    }
    let mut bases = Vec::new();
    if let Some(stem) = word.strip_suffix("ies") {
        bases.push(format!("{stem}y"));
    }
    if let Some(stem) = word.strip_suffix("ied") {
        bases.push(format!("{stem}y"));
    }
    for suffix in ["ing", "ed", "es", "s"] {
        if let Some(stem) = word.strip_suffix(suffix) {
            bases.push(stem.to_string());
            bases.push(format!("{stem}e"));
            if stem.len() > 2 && stem.as_bytes()[stem.len() - 1] == stem.as_bytes()[stem.len() - 2]
            {
                bases.push(stem[..stem.len() - 1].to_string());
            }
        }
    }
    for base in bases {
        if let Some(v) = from_base(&base)
            && [&v.third, &v.past, &v.participle, &v.gerund].contains(&&word.to_string())
        {
            return Some(v);
        }
    }
    from_base(word)
}
pub fn common(word: &str) -> bool {
    if spelling::flags(word) & 1 != 0 {
        return true;
    }
    if let Some(v) = verb(word)
        && spelling::flags(&v.base) & 1 != 0
    {
        return true;
    }
    word.strip_suffix('s')
        .is_some_and(|s| spelling::flags(s) & 1 != 0)
}
pub fn predicate(base: &str) -> bool {
    irregular().iter().any(|v| v.base == base)
        || [
            "accept", "add", "agree", "allow", "appear", "approve", "arrive", "ask", "attach",
            "attend", "believe", "call", "change", "check", "close", "collect", "compare",
            "complete", "confirm", "contain", "continue", "decide", "delay", "delete", "deliver",
            "depend", "describe", "design", "discuss", "enjoy", "explain", "expect", "fail",
            "finish", "follow", "handle", "happen", "hate", "help", "hope", "improve", "include",
            "invite", "join", "learn", "like", "listen", "live", "look", "love", "manage", "move",
            "need", "offer", "open", "order", "organize", "plan", "play", "prefer", "prepare",
            "print", "protect", "provide", "publish", "receive", "remember", "remove", "repair",
            "reply", "report", "request", "require", "return", "review", "revise", "save", "seem",
            "share", "start", "stay", "stop", "store", "study", "suggest", "suppose", "thank",
            "travel", "try", "update", "use", "visit", "wait", "walk", "want", "watch", "work",
            "worry",
        ]
        .contains(&base)
}
