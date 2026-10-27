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
become becomes became become becoming
freeze freezes froze frozen freezing
steal steals stole stolen stealing
forgive forgives forgave forgiven forgiving
swear swears swore sworn swearing
seek seeks sought sought seeking
sweep sweeps swept swept sweeping
dig digs dug dug digging
weep weeps wept wept weeping
bleed bleeds bled bled bleeding
feed feeds fed fed feeding
breed breeds bred bred breeding
speed speeds sped sped speeding
flee flees fled fled fleeing";

// Further irregular verbs and their prefixed forms. These feed form checks only: the verbs
// that are also common nouns (set, ring, wind) stay out of `predicate`. A verb with two
// accepted forms (learned/learnt, dived/dove, proved/proven) is left to the regular rule.
const MORE: &str = "arise arises arose arisen arising
awake awakes awoke awoken awaking
bear bears bore borne bearing
beat beats beat beaten beating
bend bends bent bent bending
bet bets bet bet betting
bid bids bid bid bidding
bind binds bound bound binding
bite bites bit bitten biting
blow blows blew blown blowing
burst bursts burst burst bursting
cast casts cast cast casting
cling clings clung clung clinging
cost costs cost cost costing
creep creeps crept crept creeping
deal deals dealt dealt dealing
fling flings flung flung flinging
forbid forbids forbade forbidden forbidding
forgo forgoes forwent forgone forgoing
forsake forsakes forsook forsaken forsaking
grind grinds ground ground grinding
hit hits hit hit hitting
hurt hurts hurt hurt hurting
mean means meant meant meaning
quit quits quit quit quitting
rid rids rid rid ridding
ring rings rang rung ringing
set sets set set setting
shed sheds shed shed shedding
shoot shoots shot shot shooting
shrink shrinks shrank shrunk shrinking
shut shuts shut shut shutting
sink sinks sank sunk sinking
slay slays slew slain slaying
slide slides slid slid sliding
sling slings slung slung slinging
slit slits slit slit slitting
spin spins spun spun spinning
spit spits spat spat spitting
split splits split split splitting
spread spreads spread spread spreading
spring springs sprang sprung springing
stick sticks stuck stuck sticking
sting stings stung stung stinging
stink stinks stank stunk stinking
stride strides strode stridden striding
strike strikes struck struck striking
string strings strung strung stringing
strive strives strove striven striving
swing swings swung swung swinging
tear tears tore torn tearing
thrust thrusts thrust thrust thrusting
tread treads trod trodden treading
wake wakes woke woken waking
weave weaves wove woven weaving
wind winds wound wound winding
wring wrings wrung wrung wringing
beget begets begot begotten begetting
befall befalls befell befallen befalling
beset besets beset beset besetting
behold beholds beheld beheld beholding
broadcast broadcasts broadcast broadcast broadcasting
forecast forecasts forecast forecast forecasting
recast recasts recast recast recasting
offset offsets offset offset offsetting
undercut undercuts undercut undercut undercutting
upset upsets upset upset upsetting
uphold upholds upheld upheld upholding
undo undoes undid undone undoing
redo redoes redid redone redoing
overdo overdoes overdid overdone overdoing
outdo outdoes outdid outdone outdoing
undergo undergoes underwent undergone undergoing
foresee foresees foresaw foreseen foreseeing
oversee oversees oversaw overseen overseeing
foretell foretells foretold foretold foretelling
retell retells retold retold retelling
mistake mistakes mistook mistaken mistaking
partake partakes partook partaken partaking
retake retakes retook retaken retaking
overtake overtakes overtook overtaken overtaking
undertake undertakes undertook undertaken undertaking
overcome overcomes overcame overcome overcoming
withdraw withdraws withdrew withdrawn withdrawing
redraw redraws redrew redrawn redrawing
overdraw overdraws overdrew overdrawn overdrawing
withhold withholds withheld withheld withholding
withstand withstands withstood withstood withstanding
misunderstand misunderstands misunderstood misunderstood misunderstanding
overthrow overthrows overthrew overthrown overthrowing
override overrides overrode overridden overriding
outgrow outgrows outgrew outgrown outgrowing
rewrite rewrites rewrote rewritten rewriting
overwrite overwrites overwrote overwritten overwriting
reread rereads reread reread rereading
misread misreads misread misread misreading
proofread proofreads proofread proofread proofreading
rebuild rebuilds rebuilt rebuilt rebuilding
resend resends resent resent resending
rethink rethinks rethought rethought rethinking
repay repays repaid repaid repaying
overpay overpays overpaid overpaid overpaying
resell resells resold resold reselling
outsell outsells outsold outsold outselling
rerun reruns reran rerun rerunning
overrun overruns overran overrun overrunning
outrun outruns outran outrun outrunning
overhear overhears overheard overheard overhearing
overeat overeats overate overeaten overeating
oversleep oversleeps overslept overslept oversleeping
overspend overspends overspent overspent overspending
overshoot overshoots overshot overshot overshooting
overlay overlays overlaid overlaid overlaying
mislead misleads misled misled misleading
mislay mislays mislaid mislaid mislaying
remake remakes remade remade remaking
reset resets reset reset resetting
rewind rewinds rewound rewound rewinding
unwind unwinds unwound unwound unwinding
babysit babysits babysat babysat babysitting
outbid outbids outbid outbid outbidding
overgrow overgrows overgrew overgrown overgrowing
regrow regrows regrew regrown regrowing
misdo misdoes misdid misdone misdoing
underpay underpays underpaid underpaid underpaying
prepay prepays prepaid prepaid prepaying
underwrite underwrites underwrote underwritten underwriting
overbuild overbuilds overbuilt overbuilt overbuilding
mishear mishears misheard misheard mishearing
outspend outspends outspent outspent outspending
misspend misspends misspent misspent misspending
reshoot reshoots reshot reshot reshooting
preset presets preset preset presetting
miscast miscasts miscast miscast miscasting
typecast typecasts typecast typecast typecasting
sublet sublets sublet sublet subletting
unbind unbinds unbound unbound unbinding
forswear forswears forswore forsworn forswearing
bespeak bespeaks bespoke bespoken bespeaking
overfly overflies overflew overflown overflying
overfeed overfeeds overfed overfed overfeeding
underfeed underfeeds underfed underfed underfeeding
unfreeze unfreezes unfroze unfrozen unfreezing
refreeze refreezes refroze refrozen refreezing
unstick unsticks unstuck unstuck unsticking
resit resits resat resat resitting
undersell undersells undersold undersold underselling";
/// The first verbs of the table: the ones `predicate` accepts.
fn core_len() -> usize {
    ROWS.lines().count()
}
/// A verb of the table's further rows (set, bet, ring, wind, mean...): many are also plain nouns or
/// adjectives, so a heuristic that reads a past form as a verb should not trust them as it does
/// the first rows.
pub fn extra(base: &str) -> bool {
    irregular().iter().skip(core_len()).any(|v| v.base == base)
}
fn irregular() -> &'static [Verb] {
    static VERBS: OnceLock<Vec<Verb>> = OnceLock::new();
    VERBS.get_or_init(|| {
        ROWS.lines()
            .chain(MORE.lines())
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
/// A modal auxiliary has no paradigm: "will" is not a verb with the past "willed", and "can" is not
/// one with "caned". Callers that inflect a word never see these as verbs.
pub fn modal(word: &str) -> bool {
    [
        "will", "would", "can", "could", "shall", "should", "may", "might", "must", "ought",
        "cannot",
    ]
    .contains(&word)
}
/// A one-syllable verb that ends in consonant, vowel, consonant doubles the last letter before an
/// ending that starts with a vowel ("plan" gives "planned", "hop" gives "hopped").
fn doubles(base: &str) -> bool {
    let b = base.as_bytes();
    let vowel = |c: u8| b"aeiou".contains(&c);
    let groups = b
        .iter()
        .enumerate()
        .filter(|&(i, &c)| vowel(c) && (i == 0 || !vowel(b[i - 1])))
        .count();
    b.len() >= 3
        && groups == 1
        && !vowel(b[b.len() - 1])
        && !b"wxy".contains(&b[b.len() - 1])
        && vowel(b[b.len() - 2])
        && !vowel(b[b.len() - 3])
}
/// The paradigm of an irregular verb from its base form ("buy" gives "bought"); None for regular verbs.
pub fn irregular_base(base: &str) -> Option<Verb> {
    irregular()
        .iter()
        .find(|v| v.base == base && v.past != format!("{base}ed") && v.past != format!("{base}d"))
        .cloned()
}
pub fn from_base(base: &str) -> Option<Verb> {
    if modal(base) {
        return None;
    }
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
    if (!spelling::known(&past) || doubles(base))
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
    if (!spelling::known(&gerund) || doubles(base))
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
/// A past or participle form that is also the base of another verb: "lay" (of "lie", and "lay off"),
/// "saw", "found", "wound", "ground", "bound", "fell". After a modal such a word is that other
/// verb in its base form, so it is already right.
pub fn also_base(word: &str) -> bool {
    [
        "lay", "saw", "found", "wound", "ground", "bound", "fell", "bore",
    ]
    .contains(&word)
        && verb(word).is_some_and(|v| v.base != word)
}
pub fn verb(word: &str) -> Option<Verb> {
    if modal(word) {
        return None;
    }
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
        // "sting" is not the "-ing" form of "st", "swing" not that of "sw".
        if base.len() < 3 {
            continue;
        }
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
    irregular().iter().take(core_len()).any(|v| v.base == base)
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
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn the_table_is_well_formed() {
        let mut seen = std::collections::HashSet::new();
        for line in ROWS.lines().chain(MORE.lines()) {
            let f: Vec<_> = line.split_whitespace().collect();
            assert_eq!(f.len(), 5, "{line}");
            assert!(seen.insert(f[0]), "{} listed twice", f[0]);
            assert!(f[4].ends_with("ing"), "{line}");
        }
    }
    #[test]
    fn standard_irregular_verbs_have_their_standard_forms() {
        // (base, past, participle): the common irregular verbs, with their prefixed relatives.
        for (base, past, participle) in [
            ("arise", "arose", "arisen"),
            ("bear", "bore", "borne"),
            ("beat", "beat", "beaten"),
            ("bind", "bound", "bound"),
            ("bite", "bit", "bitten"),
            ("blow", "blew", "blown"),
            ("cling", "clung", "clung"),
            ("creep", "crept", "crept"),
            ("deal", "dealt", "dealt"),
            ("forbid", "forbade", "forbidden"),
            ("grind", "ground", "ground"),
            ("mean", "meant", "meant"),
            ("ring", "rang", "rung"),
            ("shoot", "shot", "shot"),
            ("shrink", "shrank", "shrunk"),
            ("sink", "sank", "sunk"),
            ("slay", "slew", "slain"),
            ("spin", "spun", "spun"),
            ("spring", "sprang", "sprung"),
            ("stick", "stuck", "stuck"),
            ("sting", "stung", "stung"),
            ("stink", "stank", "stunk"),
            ("strike", "struck", "struck"),
            ("swing", "swung", "swung"),
            ("tear", "tore", "torn"),
            ("tread", "trod", "trodden"),
            ("wake", "woke", "woken"),
            ("weave", "wove", "woven"),
            ("wind", "wound", "wound"),
            ("retake", "retook", "retaken"),
            ("undo", "undid", "undone"),
            ("redo", "redid", "redone"),
            ("overthrow", "overthrew", "overthrown"),
            ("withdraw", "withdrew", "withdrawn"),
            ("withhold", "withheld", "withheld"),
            ("withstand", "withstood", "withstood"),
            ("forgive", "forgave", "forgiven"),
            ("foresee", "foresaw", "foreseen"),
            ("overcome", "overcame", "overcome"),
            ("undertake", "undertook", "undertaken"),
            ("mistake", "mistook", "mistaken"),
            ("rebuild", "rebuilt", "rebuilt"),
            ("rewrite", "rewrote", "rewritten"),
            ("mislead", "misled", "misled"),
            ("understand", "understood", "understood"),
        ] {
            for form in [base, past, participle] {
                let v = verb(form).unwrap_or_else(|| panic!("{form} is no verb form"));
                assert_eq!(v.base, base, "{form}");
                assert_eq!(
                    (v.past.as_str(), v.participle.as_str()),
                    (past, participle),
                    "{form}"
                );
            }
        }
    }
    #[test]
    fn a_modal_is_not_a_verb_with_a_paradigm() {
        for w in [
            "will", "would", "can", "could", "shall", "should", "may", "might", "must",
        ] {
            assert!(verb(w).is_none(), "{w}");
            assert!(from_base(w).is_none(), "{w}");
        }
    }
    #[test]
    fn short_verbs_double_their_last_letter_and_gerunds_are_not_stems() {
        assert_eq!(from_base("plan").unwrap().past, "planned");
        assert_eq!(from_base("plan").unwrap().gerund, "planning");
        assert_eq!(from_base("plane").unwrap().past, "planed");
        assert_eq!(from_base("range").unwrap().past, "ranged");
        assert_eq!(from_base("hop").unwrap().past, "hopped");
        assert_eq!(from_base("hope").unwrap().past, "hoped");
        assert_eq!(from_base("stay").unwrap().past, "stayed");
        // "sting" is a verb of its own, not the "-ing" form of "st".
        assert_eq!(verb("sting").unwrap().base, "sting");
        assert_eq!(verb("swing").unwrap().base, "swing");
    }
    #[test]
    fn words_that_are_also_the_base_of_another_verb_are_marked() {
        for w in [
            "lay", "saw", "found", "wound", "ground", "bound", "fell", "bore",
        ] {
            assert!(also_base(w), "{w}");
        }
        for w in ["went", "took", "sat", "lie", "ate"] {
            assert!(!also_base(w), "{w}");
        }
    }
}
