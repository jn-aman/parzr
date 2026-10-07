#![cfg(not(feature = "local-model"))] // Rule path only: the model path needs the bundled model.
//! Verb groups, word order and determiners: each class corrects its error and leaves the nearby
//! correct English alone. Sentences are written for these tests, not taken from any corpus.
use parzr_engine::{Mode, Request, rewrite};

fn fix(text: &str) -> String {
    rewrite(&Request {
        text: text.into(),
        mode: Mode::Fix,
        ..Request::default()
    })
    .unwrap_or_else(|e| panic!("{text}: {e}"))
    .text
}
fn check(cases: &[(&str, &str)]) {
    let wrong: Vec<String> = cases
        .iter()
        .filter_map(|(input, want)| {
            let got = fix(input);
            (got != *want).then(|| format!("{input:?}\n   want {want:?}\n   got  {got:?}"))
        })
        .collect();
    assert!(wrong.is_empty(), "{}", wrong.join("\n"));
}
fn unchanged(texts: &[&str]) {
    check(&texts.iter().map(|t| (*t, *t)).collect::<Vec<_>>());
}

#[test]
fn finished_past_times_take_the_simple_past() {
    check(&[
        (
            "He have went to Rome last summer.",
            "He went to Rome last summer.",
        ),
        (
            "We have been in Lisbon in 2021.",
            "We were in Lisbon in 2021.",
        ),
        (
            "They've seen the play two weeks ago.",
            "They saw the play two weeks ago.",
        ),
        (
            "Our team is at the venue all day yesterday.",
            "Our team was at the venue all day yesterday.",
        ),
        (
            "Her train gets delayed yesterday.",
            "Her train got delayed yesterday.",
        ),
    ]);
    unchanged(&[
        "She has lived in Oslo since 2020.",
        "We have never been to Rome.",
        "Have you seen the play?",
        "They have already eaten.",
        "I had seen the play the week before.",
        "Sorry, I meant to call yesterday.",
        "I didn't sleep last night.",
    ]);
}

#[test]
fn participles_follow_have_and_be() {
    check(&[
        ("She's went to the gym.", "She's gone to the gym."),
        (
            "The lake was froze by December.",
            "The lake was frozen by December.",
        ),
        ("He catched the early bus.", "He caught the early bus."),
        ("We buyed new chairs.", "We bought new chairs."),
        ("Mia brung cookies.", "Mia brought cookies."),
    ]);
    unchanged(&[
        "He's broke this month.",
        "She's left already.",
        "It's done.",
    ]);
}

#[test]
fn inverted_questions_keep_the_base_verb_and_agree() {
    check(&[
        ("Did the courier arrived?", "Did the courier arrive?"),
        ("Didn't she called you?", "Didn't she call you?"),
        ("Why doesn't the page loads?", "Why doesn't the page load?"),
        ("Does they know?", "Do they know?"),
        ("Has we met?", "Have we met?"),
        ("Was they late?", "Were they late?"),
    ]);
    unchanged(&[
        "Didn't she tell you?",
        "How you do it matters.",
        "Does he know?",
        "Were you there?",
    ]);
}

#[test]
fn questions_put_the_auxiliary_first() {
    check(&[
        ("Where she is?", "Where is she?"),
        ("When they will arrive?", "When will they arrive?"),
        ("How old your sister is?", "How old is your sister?"),
        ("Why he didn't call?", "Why didn't he call?"),
        ("What you doing tonight?", "What are you doing tonight?"),
        ("What you want for lunch?", "What do you want for lunch?"),
        (
            "Do you know where is the station?",
            "Do you know where the station is?",
        ),
        (
            "Can you tell me when will the shop open?",
            "Can you tell me when the shop will open?",
        ),
        (
            "She asked me where was I going.",
            "She asked me where I was going.",
        ),
    ]);
    unchanged(&[
        "Where is she?",
        "When you get home, call me.",
        "What you need is sleep.",
        "Do you know where the station is?",
        "I know what you mean.",
    ]);
}

#[test]
fn frequency_adverbs_sit_before_the_verb() {
    check(&[
        ("I drink always tea at noon.", "I always drink tea at noon."),
        ("They eat rarely meat.", "They rarely eat meat."),
        (
            "We have finished already the draft.",
            "We have already finished the draft.",
        ),
        ("I can't still find it.", "I still can't find it."),
    ]);
    unchanged(&[
        "I go there often.",
        "We usually walk to work.",
        "I still can't find it.",
    ]);
}

#[test]
fn dropped_and_stray_helping_words() {
    check(&[
        ("She waiting outside.", "She is waiting outside."),
        ("They been busy all week.", "They have been busy all week."),
        ("He not coming today.", "He isn't coming today."),
        ("There a typo on page two.", "There's a typo on page two."),
        ("Who coming to lunch?", "Who is coming to lunch?"),
        ("What time the train?", "What time is the train?"),
        ("It's hard tell from here.", "It's hard to tell from here."),
        ("I'll be send it tonight.", "I'll send it tonight."),
        ("Let's to start now.", "Let's start now."),
        ("You ought ask her.", "You ought to ask her."),
        ("I can able to help.", "I can help."),
        ("We use to live here.", "We used to live here."),
        (
            "If we would have left, we'd have made it.",
            "If we had left, we'd have made it.",
        ),
        (
            "She works there since May.",
            "She has worked there since May.",
        ),
        (
            "I am studying since noon.",
            "I have been studying since noon.",
        ),
        ("They are needing more time.", "They need more time."),
        (
            "Because it rained, so we stayed in.",
            "Because it rained, we stayed in.",
        ),
        ("Please call call me back.", "Please call me back."),
    ]);
    unchanged(&[
        "The meeting got moved to Monday.",
        "I saw them leaving early.",
        "The tools we use to clean the floor are new.",
        "I said that that was fine.",
        "He had had enough.",
        "Walla Walla is a city.",
        "Since it rained, we stayed in.",
        "I have been studying since noon.",
    ]);
}

#[test]
fn determiners_follow_sound_and_number() {
    check(&[
        ("It was a odd choice.", "It was an odd choice."),
        ("She has a honest face.", "She has an honest face."),
        ("He made an huge pot.", "He made a huge pot."),
        ("We need an USB cable.", "We need a USB cable."),
        ("She has a MBA.", "She has an MBA."),
        ("He is an expert in tax.", "He is an expert in tax."),
        (
            "She is an artists from Lima.",
            "She is an artist from Lima.",
        ),
        ("The car don't start.", "The car doesn't start."),
        ("They likes jazz.", "They like jazz."),
        (
            "Please sign this forms today.",
            "Please sign these forms today.",
        ),
        ("These equipment is new.", "This equipment is new."),
        ("Those man is my uncle.", "That man is my uncle."),
        (
            "We had less visitors today.",
            "We had fewer visitors today.",
        ),
        ("There's four chairs left.", "There are four chairs left."),
        (
            "There are a leak in the roof.",
            "There is a leak in the roof.",
        ),
        ("Is there any seats left?", "Are there any seats left?"),
        ("Here's the keys.", "Here are the keys."),
        ("I want an another slice.", "I want another slice."),
    ]);
    unchanged(&[
        "It was a one-time offer.",
        "She studies at a university.",
        "It took an hour.",
        "We need a URL.",
        "Plan a is fine.",
        "We have a sports car.",
        "It is a means to an end.",
        "This costs a lot.",
        "I think this works.",
        "I know that kids love it.",
        "Those who left missed it.",
        "These days are busy.",
        "How much does it cost?",
        "There is a lot of noise.",
        "There are a few seats left.",
        "The data was clear.",
        "My parents don't mind.",
    ]);
}
