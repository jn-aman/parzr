# English grammar evidence

This catalog separates descriptions of English grammar, evaluation data, reusable resources and measured parzr behavior. External research establishes what to cover and how to test it. It does not establish parzr's accuracy. No external corpus listed here has been imported into the runtime. BEA-2019 dev, CoNLL-2014 and JFLEG have been used for evaluation only (the files are not in the repository); those results are in [model evaluation](model-evaluation.md). The other sources have not been evaluated against parzr as part of this catalog.

## Grammar inventories and explanations

| Primary source | Evidence | Use and limits |
|---|---|---|
| [English Grammar Profile research](https://www.birmingham.ac.uk/documents/college-artslaw/corpus/conference-archives/2017/general/paper300.pdf) | Over 1,200 corpus-derived competency statements across A1 to C2 | A broad coverage inventory. Competency statements describe language use, not executable correction rules. Consult applicable database terms before copying content. |
| [Cambridge English Grammar Today](https://dictionary.cambridge.org/grammar/british-grammar/) | Over 500 topics, corpus-based examples, spelling, punctuation, word formation and spoken/written usage | Reference for independently authored rules and explanations. Copyrighted reference material; do not bulk copy examples or prose. |
| [British Council advanced grammar](https://learnenglish.britishcouncil.org/free-resources/grammar/c1) | Advanced constructions including clefts, inversion and auxiliaries | Counterexamples to simplistic word-order corrections. Reference material, not a correction benchmark or an unrestricted data license. |
| [Purdue punctuation resources](https://owl.purdue.edu/owl/general_writing/punctuation/index.html) | Clause punctuation, commas, apostrophes, quotations and hyphens | Reference for independently authored punctuation tests. The page carries an explicit copyright and redistribution notice. |
| [Universal Dependencies English guidelines](https://universaldependencies.org/en/index.html) | English tokenization, morphology, POS and dependency relations | A structural annotation framework for agreement, auxiliaries, clauses and relations. Syntax annotation is not an error-correction oracle. |

## Annotated benchmarks and counterexamples

| Primary source | What it measures | Scale / verified terms |
|---|---|---|
| [CTSEG paper](https://aclanthology.org/2025.acl-long.1026/) and [official dataset](https://github.com/SDS-NLP/CTSEG) | Correction by individual grammar construction and proficiency level | 1,578 sentences covering 263 CEFR-J items, A1 to B2. Research purposes only; redistribution prohibited. No corpus files in the public repo. |
| [BLiMP](https://github.com/alexwarstadt/blimp) | Grammatical versus ungrammatical minimal pairs spanning syntax, morphology and semantics | 67 sets of 1,000 pairs, 67,000 pairs total. CC BY 4.0. Its original metric compares language-model probabilities; a rule engine needs an explicitly labeled detection/false-positive evaluation rather than claiming the original score. |
| [BEA-2019 / W&I+LOCNESS](https://www.cl.cam.ac.uk/research/nl/bea2019st/) | Human correction of learner and native-student writing; error-type precision, recall and F0.5 | 43,169 sentences in the organizer's full dataset table. Separate train/dev/test. Organizer states non-commercial restrictions for its listed corpora. No automatic public redistribution. |
| [CoNLL-2014](https://www.comp.nus.edu.sg/~nlp/conll14st.html) | Standard annotated correction task with an official scorer | Useful for comparable correction metrics. NUCLE access requires a signed license and request; check the test archive's own terms separately. |
| [JFLEG](https://github.com/keisks/jfleg) | Fluency-oriented corrections with multiple acceptable rewrites | 754 development and 747 test sentences, four references each. CC BY-NC-SA 4.0. A fluency score alone does not prove minimal-edit correctness or intent preservation. |
| [CWEB](https://github.com/SimonHFL/CWEB) | Correction of lower-error-density website prose | 13,574 sentences from 1,078 websites across the corpus. CC BY-NC-SA 4.0 in the official README. Particularly relevant to measuring unwanted edits on everyday prose; keep restricted data external. |
| [ErAConD](https://github.com/yuanxun-yx/eracond) | Fine-grained corrections in learner conversation | Official repository supplies data and an MIT license. Preserve attribution when importing; conversational expectations differ from essay prose. |
| [RobustGEC](https://github.com/HillZhang1999/RobustGEC) and [paper](https://aclanthology.org/2023.emnlp-main.1043/) | Whether irrelevant context changes alter correction behavior | 5,000 cases with five variants per original. Repository has MIT code terms, but the paper discusses underlying CoNLL/BEA/TEM-8 data and research-only use. Do not infer unrestricted corpus rights from the code license. |
| [GMEG](https://github.com/grammarly/GMEG) | Multi-reference corrections and human ratings across FCE, Wikipedia and Yahoo domains | Includes human references and negative controls. Yahoo data requires separate research access. Check each domain's underlying terms; do not treat a paper or unrelated repository's license as permission for all data. |

Counts describe each source's stated corpus or evaluation release, not additive independent examples. Several datasets overlap or reuse underlying sources. Keep split definitions and duplication checks explicit.

## Evaluation tooling and reusable resources

| Primary source | Evidence and possible use | Terms / limitation |
|---|---|---|
| [ERRANT](https://github.com/chrisjbryant/errant) and [license](https://github.com/chrisjbryant/errant/blob/main/LICENSE.md) | Extracts and classifies correction edits; reports TP/FP/FN, precision, recall and F0.5 overall and by error family | MIT toolkit. Pin versions, tokenization and annotation models. BEA historical comparison uses ERRANT 2.0.0; newer versions can change scores. |
| [LanguageTool core](https://github.com/languagetool-org/languagetool), [rule format](https://dev.languagetool.org/development-overview.html) and [robust-rule guidance](https://dev.languagetool.org/developing-robust-rules.html) | Existing token/POS rule patterns and correct/incorrect examples; guidance on avoiding false positives | LGPL-2.1-or-later core with resource-specific licenses. Not an Apache-licensed rule dump. Any reuse needs explicit source/version tracking and license compliance. |
| [CMUdict](https://github.com/cmusphinx/cmudict) and [license](https://github.com/cmusphinx/cmudict/blob/master/LICENSE) | Pronunciations can inform vowel-sound versus consonant-sound article candidates | BSD-style redistribution conditions. Pronunciation variants, unknown words and dialect still require guards. This is an implementation inference, not a verified parzr capability. |
| [WordNet documentation](https://wordnet.princeton.edu/documentation) and [license](https://wordnet.princeton.edu/license-and-commercial-use) | Lexical relations and morphological resources can inform contextual candidates | Princeton license requires retained notices. Lexical membership does not determine intended sense or grammatical correctness. |
| [UD English EWT](https://github.com/UniversalDependencies/UD_English-EWT) | Annotated morphology and dependency structure for web genres including email and reviews | Annotations/database rights CC BY-SA 4.0; README separately notes underlying text rights. Preserve source-specific conditions. |
| [GEC survey](https://aclanthology.org/2023.cl-3.4/) | Peer-reviewed synthesis of datasets, linguistic challenges, correction methods and evaluation | Research navigation and methodological context. No claim that one listed dataset or model covers all English. |

## Coverage map

This is an engineering interpretation of the sources, not a claim of complete coverage or a copied grammar syllabus.

| Coverage family | Evidence to consult | Current parzr gap requiring measurement |
|---|---|---|
| Determiners, articles, countability, quantifiers | Cambridge, EGP, CTSEG, BLiMP | Mostly reviewed local patterns; phonetic and wider countability context remain limited. |
| Subject/verb and determiner/noun agreement | UD English, BLiMP, CTSEG | Nested clauses, intervening nouns, coordination and collective nouns need structural tests. |
| Tense, aspect, participles, auxiliaries, modality, voice | Cambridge, CTSEG, British Council | More than isolated local verb-form substitutions; tense and voice require clause context. |
| Pronoun case, binding, reference and possessives | Cambridge, BLiMP, UD English | Real-word confusions and reference resolution need ambiguity-aware tests. |
| Complements, prepositions, collocations and phrasal verbs | Cambridge, EGP, CWEB, GMEG | Lexical sense and permitted alternative constructions remain difficult. |
| Questions, imperatives, inversion and negation | CTSEG, British Council, BLiMP | Current local rules do not establish broad construction coverage. |
| Coordination, subordination, relatives, conditionals and ellipsis | Cambridge, EGP, CTSEG, BLiMP | Structural analysis and discourse context exceed current regex coverage. |
| Clause punctuation, apostrophes, quotations and hyphenation | Purdue, Cambridge, ERRANT-tagged corpora | Current punctuation correction mainly concerns spacing. |
| Spelling, morphology, capitalization and token boundaries | ERRANT, UD English, lexical resources | Contextual real-word errors and ambiguous spellings remain limited. |
| Valid variants, register, conversational fragments and dialect | Cambridge, ErAConD, CWEB, GMEG | Avoid treating optional style preferences or valid dialect as grammar errors. |

## What counts as parzr evidence

Keep authored regressions separate from an independently frozen evaluation set. Record engine commit/build identifier, pack hashes, corpus release/hash, split, scorer version, tokenization, dialect and analysis settings. Report precision, recall, F0.5, no-change/false-positive behavior on valid prose, results by error family and domain, and latency separately. For Fix, evaluate minimal corrections; tone modes additionally need intent and correctness checks.

For BLiMP, report a clearly named detection adaptation, including unchanged grammatical sentences and detected bad examples by phenomenon. Do not report language-model likelihood accuracy for this deterministic engine. Multiple-reference corpora need their supported scorer; exact-string matching against a single reference can penalize a valid alternative.

Passing the existing 317 authored corpus cases establishes those cases. It is not a score on these external benchmarks. Finding a source, writing a rule, executing a pipeline and demonstrating useful real-world coverage are distinct evidence steps. No finite benchmark establishes universal handling of every English construction and context.
