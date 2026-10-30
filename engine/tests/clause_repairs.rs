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

#[test]
fn its_and_its_contraction_follow_the_words_around_them() {
    check(&[
        ("The app lost it's settings.", "The app lost its settings."),
        (
            "The cat can open the door on it's own.",
            "The cat can open the door on its own.",
        ),
        ("It's name is Rex.", "Its name is Rex."),
        (
            "In it's place stands a tree.",
            "In its place stands a tree.",
        ),
        (
            "The firm has it's offices in Leeds.",
            "The firm has its offices in Leeds.",
        ),
        ("Its blocking the deploy.", "It's blocking the deploy."),
        (
            "I think its possible to fix.",
            "I think it's possible to fix.",
        ),
        ("Its working now.", "It's working now."),
        (
            "This is more trouble than its worth.",
            "This is more trouble than it's worth.",
        ),
    ]);
    unchanged(&[
        "Hold on, it's fine.",
        "It's time to go.",
        "It's a good name.",
        "The town is proud of its history.",
        "The museum reopened after its opening the next day was delayed.",
        "Despite its being the largest city, it is quiet.",
        "The robot raised its hard metal arm.",
        "The bird spread its wings.",
        "It's raining again.",
    ]);
}

#[test]
fn doubled_words_lose_the_slip_and_keep_the_meant_copy() {
    check(&[
        ("I went to the the store.", "I went to the store."),
        (
            "He trained at the The Actors Center.",
            "He trained at The Actors Center.",
        ),
        (
            "They said that that people were angry.",
            "They said that people were angry.",
        ),
        ("It is is made of clay.", "It is made of clay."),
        ("I think we we're late.", "I think we're late."),
        ("You should shouldn't worry.", "You shouldn't worry."),
        (
            "It is a for for-profit company.",
            "It is a for-profit company.",
        ),
    ]);
    unchanged(&[
        "I know that that is true.",
        "What it is is a mess.",
        "She had had enough.",
        "They play in the home arena Arena Mexico.",
        "It can carry troops as well as AS units.",
        "I know that that's true.",
    ]);
}

#[test]
fn verb_forms_after_be_modals_and_to() {
    check(&[
        (
            "The house was build in 1900.",
            "The house was built in 1900.",
        ),
        (
            "The file is generate by the script.",
            "The file is generated by the script.",
        ),
        (
            "The issues have not been resolves.",
            "The issues have not been resolved.",
        ),
        ("It is believe to be older.", "It is believed to be older."),
        (
            "The bridge, also know as the Iron Bridge, is old.",
            "The bridge, also known as the Iron Bridge, is old.",
        ),
        (
            "He is best know for his films.",
            "He is best known for his films.",
        ),
        (
            "You should starting this sport.",
            "You should start this sport.",
        ),
        (
            "We need to calculated the size.",
            "We need to calculate the size.",
        ),
        ("He was play with the dog.", "He was playing with the dog."),
    ]);
    unchanged(&[
        "All we need to do is build a wall.",
        "There is need for reform.",
        "Is use of force allowed?",
        "Should smoking be banned?",
        "There might be attributes in both files.",
        "We also know as much.",
        "They switched to paid plans.",
        "He sells his free will.",
        "The task is complete.",
        "The door is open now.",
    ]);
}

#[test]
fn nouns_take_the_number_of_their_quantifier() {
    check(&[
        (
            "There are many problem with this.",
            "There are many problems with this.",
        ),
        ("I have two car.", "I have two cars."),
        ("Each students has a book.", "Each student has a book."),
        (
            "He is one of the best player in the team.",
            "He is one of the best players in the team.",
        ),
        (
            "We sell all kind of things.",
            "We sell all kinds of things.",
        ),
        ("I saw him two year ago.", "I saw him two years ago."),
    ]);
    unchanged(&[
        "Nine crew members were on board.",
        "They sold two dollar bills.",
        "She is one of the family.",
        "We watch a different type of film.",
        "Phase one of the project is done.",
        "It reminds one of the sea.",
        "Many people came.",
        "Both music and art matter.",
        "The two form a bond.",
        "It was a top ten hit.",
        "Every clothes shop was closed.",
    ]);
}

#[test]
fn clear_subjects_agree_and_word_forms_fit_their_slot() {
    check(&[
        ("My teacher have a car.", "My teacher has a car."),
        (
            "Everyone have a right to vote.",
            "Everyone has a right to vote.",
        ),
        ("There is problems with it.", "There are problems with it."),
        (
            "It is depends on the weather.",
            "It depends on the weather.",
        ),
        (
            "He is dependant on his parents.",
            "He is dependent on his parents.",
        ),
        (
            "She is a world renown chef.",
            "She is a world renowned chef.",
        ),
        ("I am interesting in art.", "I am interested in art."),
        ("You can easy find it.", "You can easily find it."),
        (
            "Each of the reports need a review.",
            "Each of the reports needs a review.",
        ),
    ]);
    unchanged(&[
        "My father and my mother have a car.",
        "The team have won the cup.",
        "The following have been released.",
        "The singer, whose renown grew, sang.",
        "It would be easy talking to her.",
        "She would gain renown for her films.",
        "It requires that an organization have proper tools.",
        "You are boring with that story.",
    ]);
}

#[test]
fn everyday_slips_take_the_word_the_clause_needs() {
    check(&[
        ("Just put in in the model.", "Just put it in the model."),
        (
            "Please let me no your thoughts.",
            "Please let me know your thoughts.",
        ),
        ("The meeting is of today.", "The meeting is off today."),
        ("Can you borrow me your pen?", "Can you lend me your pen?"),
        (
            "I'm not sure what you mean by that that.",
            "I'm not sure what you mean by that.",
        ),
        (
            "It's important that that we finish.",
            "It's important that we finish.",
        ),
        ("It just the part I need.", "It's just the part I need."),
        (
            "Worse case scenario, we wait.",
            "Worst case scenario, we wait.",
        ),
    ]);
    unchanged(&[
        "The box should be put in the car.",
        "Let me no longer wait.",
        "The idea is of great value.",
        "We may as well go home.",
        "This is a worse case than last year.",
    ]);
}

#[test]
fn a_pronoun_subject_is_not_said_twice() {
    check(&[
        (
            "We all of us already have the code.",
            "We all already have the code.",
        ),
        ("I think we all of us agree.", "I think we all agree."),
        ("They both of them came late.", "They both came late."),
    ]);
    unchanged(&[
        "We, all of us, already have it.",
        "Thank you all of you for coming.",
        "All of us already have the code.",
        "Tell them all of them are welcome.",
    ]);
}

#[test]
fn a_compound_subject_keeps_its_plural_helping_verb() {
    unchanged(&[
        "Tom and the dog don't agree.",
        "My brother and the cat don't get along.",
        "Tom, the dog and my sister don't agree.",
        "Jerry and that guy don't agree.",
    ]);
    check(&[
        ("The dog don't bark.", "The dog doesn't bark."),
        ("The dogs doesn't bark.", "The dogs don't bark."),
        (
            "Here is a list and the boy don't know.",
            "Here is a list and the boy doesn't know.",
        ),
    ]);
}

#[test]
fn there_with_a_quantity_noun_takes_the_number_of_what_follows() {
    unchanged(&[
        "There are a large number of reasons.",
        "There are a good number of reasons.",
        "There are a wide range of options.",
        "There are a handful of reasons.",
        "There are a great many reasons.",
        "There are a good few reasons.",
        "There are a few of them left.",
        "There is a lot of water.",
    ]);
    check(&[("There are a problem.", "There is a problem.")]);
}

#[test]
fn a_demonstrative_pronoun_or_compound_head_is_not_a_number_error() {
    unchanged(&[
        "Those left behind were sad.",
        "Those given a seat were happy.",
        "These library subject guides are useful.",
        "These car keys are mine.",
        "Assist those dealing with stress.",
        "This is for those outside the movement.",
        "Cover these in a series of posts.",
        "Having these non-slip mats keeps people safe.",
        "Results revealed that participants did better.",
        "It is clear that genes play a part.",
        "We recommend that students attend.",
        "Any of this requires work and attention.",
        "These thin irregular electron density layers are old.",
        "These four studies show it.",
        "I like these new books.",
        "These news are good.",
        "We plan to deal with these new and dangerous threats.",
        "In addition, these children receive less attention.",
        "These costs are high.",
        "These results show it.",
        "These mean you have to wait.",
        "These show you care.",
        "These include informed consent and anonymity.",
        "These range from small to large.",
        "Make sure they keep up with those higher costs.",
    ]);
    check(&[
        ("Print this pages.", "Print these pages."),
        (
            "Please print this pages for him.",
            "Please print these pages for him.",
        ),
        (
            "What are this stains on the rug?",
            "What are these stains on the rug?",
        ),
        ("How much are that shoes?", "How much are those shoes?"),
        (
            "Did you see this messages from Ben?",
            "Did you see these messages from Ben?",
        ),
        ("I like these guy.", "I like these guys."),
        ("He found those book.", "He found those books."),
        ("Check these file.", "Check these files."),
        ("Those guy is late.", "That guy is late."),
        ("I like these new book.", "I like these new books."),
        ("I saw those big house.", "I saw those big houses."),
        (
            "Those library on Main is closed.",
            "That library on Main is closed.",
        ),
        (
            "These furniture came with the flat.",
            "This furniture came with the flat.",
        ),
        // A verb-first "-s" word after the noun is the verb, not a plural head: with no plural to
        // give the noun ("equipment"), or a singular verb after it, the demonstrative changes.
        (
            "These equipment needs servicing.",
            "This equipment needs servicing.",
        ),
        ("Those guy needs help.", "That guy needs help."),
        (
            "Those guy at the front desk is so helpful.",
            "That guy at the front desk is so helpful.",
        ),
        (
            "Those cat on the fence is mine.",
            "That cat on the fence is mine.",
        ),
        ("Is these seat taken?", "Is this seat taken?"),
        (
            "We need those document signed today.",
            "We need those documents signed today.",
        ),
        (
            "We need those document today.",
            "We need those documents today.",
        ),
        // A reduced relative clause between the noun and its verb.
        (
            "Those movie we saw was great.",
            "That movie we saw was great.",
        ),
        (
            "Those jacket you bought looks warm.",
            "That jacket you bought looks warm.",
        ),
        (
            "Those book you lent me were great.",
            "Those books you lent me were great.",
        ),
    ]);
}

#[test]
fn very_less_takes_few_not_fewer() {
    check(&[
        ("There are very less cats.", "There are very few cats."),
        (
            "There are very less messages.",
            "There are very few messages.",
        ),
        ("It was too less people.", "It was too few people."),
        ("We have less people.", "We have fewer people."),
    ]);
    unchanged(&[
        "There is very little information.",
        "There are far fewer cats.",
    ]);
}

#[test]
fn a_clock_time_before_a_time_adverb_is_not_counted() {
    unchanged(&["I came at nine yesterday.", "We met at two today."]);
    check(&[("I have two car.", "I have two cars.")]);
}

#[test]
fn agreement_and_apostrophe_fixes_do_not_undo_each_other() {
    check(&[
        ("The cats has arrived.", "The cats have arrived."),
        ("Jeans has arrived.", "Jeans have arrived."),
        ("My sisters has arrived.", "My sisters have arrived."),
    ]);
    unchanged(&[
        "These phenomena are rare.",
        "Two people's lives were changed.",
        "Three children's coats were lost.",
        "They were all Kelly's fans.",
        "Many Hawking's papers are online.",
    ]);
    check(&[
        ("The Smith's are coming.", "The Smiths are coming."),
        ("Two cat's are here.", "Two cats are here."),
    ]);
}

#[test]
fn an_adverb_after_a_modal_or_auxiliary_is_already_in_place() {
    unchanged(&[
        // Modals.
        "I will never miss a day.",
        "I would never give up.",
        "She could always call me.",
        "They should usually ask first.",
        "We can sometimes help.",
        "He might never know.",
        // Perfect, progressive and be.
        "I have never been there.",
        "She has always known.",
        "We had rarely seen it.",
        "I am always late.",
        "He is often wrong.",
        "They were seldom home.",
        // Negated auxiliaries, with "still" or "ever".
        "I haven't ever been there.",
        "The pot isn't still boiling.",
        "They aren't still waiting.",
        "I don't still live there.",
        "She doesn't always agree.",
        "I won't still be there.",
        // The adverb belongs to what follows the verb.
        "I promise never to lie.",
        "I decided never to go back.",
        "I want always to be kind.",
        "He said never mind.",
        "I hate always being late.",
        "She vowed never again to quit.",
        "I wonder sometimes what happens next.",
        // A plural noun after "you" or "we" says who the pronoun means.
        "You people never answer your phones.",
        "You guys always arrive late.",
        "We students often meet there.",
    ]);
    check(&[
        ("I go always to the gym.", "I always go to the gym."),
        ("They watch rarely films.", "They rarely watch films."),
        ("I couldn't still reach him.", "I still couldn't reach him."),
        (
            "They go often swimming in the lake.",
            "They often go swimming in the lake.",
        ),
    ]);
}

#[test]
fn a_perfect_keeps_its_tense_when_the_past_time_is_in_a_later_clause() {
    unchanged(&[
        "I have read the email you sent yesterday.",
        "She has found the file that Priya sent last week.",
        "We have reviewed the plan my manager wrote yesterday.",
        "I have met the man who called you last week.",
        "They have finished what we started in 2019.",
    ]);
    check(&[
        (
            "I have read the email yesterday.",
            "I read the email yesterday.",
        ),
        ("She has met him last week.", "She met him last week."),
        ("I have seen you yesterday.", "I saw you yesterday."),
    ]);
}

#[test]
fn a_past_time_governs_irregular_verbs_but_not_modals_or_reported_clauses() {
    check(&[
        ("I wake up late yesterday.", "I woke up late yesterday."),
        (
            "We plan the trip yesterday.",
            "We planned the trip yesterday.",
        ),
        ("They sting him last week.", "They stung him last week."),
        (
            "He slay the dragon last night.",
            "He slew the dragon last night.",
        ),
        ("We drive home yesterday.", "We drove home yesterday."),
        ("I buy it yesterday.", "I bought it yesterday."),
    ]);
    unchanged(&[
        "We will start tomorrow.",
        "I can swim in the sea.",
        "I think yesterday we lost.",
        "I know yesterday was hard.",
        "I mean yesterday was a mistake.",
        "I lose the book that you gave me yesterday.",
    ]);
}

#[test]
fn a_time_word_in_another_clause_or_phrase_does_not_change_the_verb() {
    unchanged(&[
        "I am writing about a concert last month.",
        "I am in my last year of college.",
        "He called me yesterday and told me that he loves me.",
        "I received your letter last week in which you say that you want to help.",
        "I agree that five years ago this might have been true.",
        "The storm last night has damaged the roof.",
        "What are HID lights?",
    ]);
    check(&[
        ("I go to the gym last week.", "I went to the gym last week."),
        (
            "She told me that I go there yesterday.",
            "She told me that I went there yesterday.",
        ),
        // "from yesterday" runs up to now: the perfect stays, and "since" replaces "from".
        (
            "Ravi has been absent from yesterday.",
            "Ravi has been absent since yesterday.",
        ),
    ]);
}

#[test]
fn a_modal_before_its_subject_or_a_noun_will_is_not_a_modal_with_a_form_error() {
    unchanged(&[
        "Should hackers be denied access?",
        "Given the risk, should hackers be denied access?",
        "Courses must be approved, as must exams.",
        "Adding hay will help, as will adding oats.",
        "In this story, strength of will is important.",
        "She had like a mohawk on her head.",
    ]);
    check(&[
        ("She doesn't realized it.", "She doesn't realize it."),
        ("They will went home.", "They will go home."),
    ]);
}

#[test]
fn rules_that_undid_each_other_now_settle() {
    // Each of these used to end in "Corrections did not stabilize".
    unchanged(&[
        "These phenomena are rare.",
        "The phenomena are rare.",
        "I like these phenomena a lot.",
        "I told each of the boys they were late.",
        "One of the books they were reading was good.",
        "One of the issues we were late.",
        "She has seasonal affective disorder.",
        // A name or an irregular plural with "'s" after a quantifier is a possessive.
        "They were all Kelly's fans.",
        "We saw other people's stuff.",
        "Many Alzheimer's drugs are in trials.",
        // ", including ..." is no second sentence (a comma splice rule and the fragment rule
        // used to take turns on it).
        "McCoy finished the season with 1,309 yards, including 6 games of over 100 yards.",
        "The bill bans digital locks, including locks on the Internet.",
    ]);
    check(&[
        ("So many photo's were lost.", "So many photos were lost."),
        (
            "The Patel's are coming over.",
            "The Patels are coming over.",
        ),
        (
            "I like this phenomena a lot.",
            "I like these phenomena a lot.",
        ),
        ("Each of the boys were late.", "Each of the boys was late."),
        (
            "One of the children were late.",
            "One of the children was late.",
        ),
    ]);
}
