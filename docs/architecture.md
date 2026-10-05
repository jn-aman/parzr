# Architecture

The Apple Silicon macOS app calls the bundled Rust library through bounded JSON FFI. Apple NaturalLanguage supplies token and entity hints: the app tags text itself, and the command-line engine, browser native host and LSP use the same macOS tagger through the native library. No adapter starts a network listener.

Three diagrams explain the system at three zoom levels. Their editable sources are in [`docs/diagrams`](diagrams) (open them at excalidraw.com); every label uses a real function, file or attribute name from the code.

## Overview

<p align="center"><img src="media/architecture.png" width="900" alt="Parzr architecture: apps, macOS Accessibility, the Swift app, the Rust engine over a C FFI, the native model runtime, and a real request and response, all inside the Mac."></p>

How to read it, left to right:

1. **Where you write.** Safari, Mail, Chrome, Slack, Word, Firefox and any other app with an accessible text field. Parzr never reads secure fields, and skips Terminal, iTerm, Zed and JetBrains. VS Code and Cursor are checked only after you opt in.
2. **macOS Accessibility.** The only door into other apps. Parzr reads `AXValue`, `AXSelectedTextRange`, `AXBoundsForRange` and listens to `AXValueChanged`, `AXSelectedTextChanged` and `AXFocusedUIElementChanged`. To see inside some apps it sets `AXManualAccessibility` (Electron), falls back to `AXEnhancedUserInterface` (Chromium) or reads the application role (Firefox). Fixes are written back through the settable `AXSelectedText`, or typed as Unicode key events when an editor ignores that write (`AXCompat.swift`).
3. **Parzr.app, in Swift.** `PassiveObserver` and `Hotkey` start work. `SelectionSnapshot` and `AXCompat` read the field safely. `KnownNames` and `SystemLexicon` collect the names the engine must not touch. `WritingEngine` encodes the request and calls the engine. `AppModel` and `InlineSuggestions` validate the result, draw underlines and open the correction card.
4. **Rust engine.** Entry points are `parzr_rewrite_json`, `parzr_string_free` and `parzr_cancel_rewrite`. The pipeline is a tokenizer, a name index (STRONG, MEDIUM, WEAK), 154 phrase rules in one Aho-Corasick automaton, 255 contextual regexes compiled only when a required-literal prefilter finds one of their literals, punctuation and structure checks, spelling (lexicon, deletion index, bigram ranking) and a fixed-point loop. It returns minimal UTF-16 edits.
5. **Native model runtime.** `libparzr_model.dylib` is loaded with `dlopen` and `dlsym`. It holds the NLTagger and NSSpellChecker helpers used by adapters that send no tokens, and llama.cpp with Metal running Qwen3.5-0.8B Q5_K_M (593 MB). Weights load only on the explicit path.
6. **Optional adapters** (dashed, bottom left). The VS Code extension spawns `parzr-engine` over stdio, the browser extension talks to `parzr-native-host` through native messaging, and other editors can run `parzr-lsp`. They reuse the same engine and model runtime, each in its own process.
7. **The wire** (bottom strip). A real request and response from `parzr-engine`, shortened. The response is the contract: `start_utf16` and `end_utf16` ranges into your original text, the `replacement`, a `category` that decides the underline colour (Style and Tone are blue, everything else red) and a `rule_id` that says who wrote the edit.

The dashed green border is the privacy boundary: the app, the engine and the model runtime make no network requests while checking text.

## The typing path

<p align="center"><img src="media/typing-path.png" width="900" alt="The typing path in nine steps: keystroke, 90 ms debounce, capture, names, engine call with no model, validation, underlines, card, and Return to fix the sentence, with measured engine timings of 0.25 ms, 1.9 ms and 10.5 ms."></p>

Automatic checking is a timeline of nine steps. Nothing on it loads the model.

1. **You type or move the caret.** `PassiveObserver` listens with an `AXObserver` on the focused field (`AXValueChanged`, `AXSelectedTextChanged`) and on the app (`AXFocusedUIElementChanged`), plus global `keyDown` and `leftMouseUp` monitors for editors that stay silent after a paste. The text of a key press is never read.
2. **Wait for a pause.** Every event cancels the pending check and restarts the wait. The delay is `Preferences.boundedCheckingDelay`: 90 ms by default, adjustable from 40 to 700 ms.
3. **Read the focused field.** `SelectionSnapshot.capture(passive: true)` finds the focused element or one of its ancestors (up to eight levels, secure fields skipped), reads `AXValue` (up to 256 KB) and `AXSelectedTextRange`, widens the caret to its paragraph (at most 8192 UTF-16 units), asks for `AXBoundsForRange` and reads the attributed string so links and `@mentions` become protected ranges.
4. **Gather the names.** `KnownNames.names(for:request:)` merges your own name, learned names and Contacts (opt-in) with `documentNames` (NLTagger people, places and organizations already in the text) and `NameGate`, which asks `NSSpellChecker`: if it flags `priya` but accepts `Priya`, the lowercase word is a name. The lookup runs on a serial queue with a 2000-word cache, and the request carries at most 2000 names.
5. **Ask the engine, with no model.** `WritingEngine.typing` adds NLTagger hints, encodes the request and calls `parzr_rewrite_json` with mode `fix` and `deep: false`. Measured pipeline time is 0.25 ms for a chat message, 1.9 ms for 1 KB and 10.5 ms for 4 KB, so the wait you notice is the debounce, not the engine.
6. **Check it is still true.** Spelling edits for words you taught macOS are dropped, then `snapshot.validate()` confirms the same app, the same focused field, the same selection and an unchanged `AXValue`. If anything moved, the result is discarded silently.
7. **Draw the underlines.** `InlineSuggestions.show` places up to 32 non-activating floating panels at `AXBoundsForRange`, red for issues and blue for style. They hide at once on scroll and return after 180 ms if the text is unchanged.
8. **Click a word.** The snapshot is validated again and the card opens next to the word. The preview is the sentence (split with `NLTokenizer`) with changed words in mint.
9. **Return fixes the sentence.** `AppModel.applyBest` applies the edits of that sentence from last to first. For each edit Parzr selects the range, sets `AXSelectedText` (or types the replacement with `CGEvent`), re-reads the text to verify, and finally restores the caret. Command+Return fixes every mark in the paragraph.

## The explicit path

<p align="center"><img src="media/explicit-path.png" width="900" alt="The explicit path: Option+Space or a tone, capture, rules first, names masked as placeholders, Qwen3.5-0.8B on Metal with a restore step, guards and a name judge, grammar passes again, one minimal edit list, and the card showing the whole corrected passage."></p>

Option+Space, or choosing Professional, Friendly, Concise or Direct, runs the model. Fix mode runs it too while **Context refinement** is on, which is the default.

1. **You ask.** `GlobalHotkey` opens the card for your selection. `SelectionSnapshot.capture()` reads `AXSelectedText` (up to 64 KB). If the editor hides it, `captureByCopy()` presses Command+C and restores your clipboard, which is how canvas editors such as Google Docs work. The request sets `deep` for tone modes and for Fix while Context refinement is on.
2. **Rules first.** The same Fix-mode rules as when typing run to a fixed point (up to six passes) so the model starts from corrected text. Names stay protected and may only change case.
3. **Hide what must not change.** Links, code, emoji, `@mentions` and every name candidate (`name_guard_ranges`, WEAK or stronger) are replaced by `ZXQPARZRKEEP0QXZ`-style placeholders. Paragraph whitespace stays real text.
4. **Qwen on Metal.** The prompt is a ChatML message with one instruction per mode. `parzr_model_generate` decodes greedily with llama.cpp (context 4096 tokens, a 20 s deadline). `restore()` requires every placeholder to come back exactly once, asks again once with the tokens listed if one is lost, and withholds the suggestion if that fails. `edits()` diffs the answer against your passage into edits with `rule_id` `local-model`.
5. **Guards.** Protected text must be untouched. `keep_names` keeps names, accented words and ALL CAPS words letter for letter. In Fix mode `plausible_edits` keeps only corrections (spacing, case, close spelling, known confusables, the same verb, one function word) and `vetted` additionally keeps curly quotes and dashes and drops added date commas, optional commas and respellings of known words. A failed Fix keeps the rule edits and adds a warning, while a failed tone is an error, never a silent grammar-only result. Beside the guards, the **name judge** asks the model one yes or no question (`parzr_model_name_log_odds`) about a lowercase unknown word that an edit would respell. At `log P(yes) - log P(no) >= -0.9` the word is kept as a name, with at most 12 questions per request.
6. **Grammar passes again, then one edit list.** The judge screens the model's edits, they are applied, the rule passes run again, and `plan()` rebuilds minimal UTF-16 edits against your original. The rebuilt text must equal the composed text or the request fails.
7. **The card.** It shows the whole corrected passage with changed words in mint. Command+Return (Fix all) applies every chosen edit through Accessibility, as when typing; a copied selection is pasted back instead.

**Model lifecycle.** The weights are memory-mapped and loaded on the first call that needs them. One call runs at a time, cancelling the request aborts it, and a timer thread releases the context and model 30 seconds after the last call. On a 70-character message a warm call took 0.2 to 0.6 s, and the first call, which loads the weights, took 0.9 to 15 s depending on the disk cache.

## Guarantees and limits

Automatic typing runs grammar, spelling and punctuation to a bounded fixed point, retaining UTF-16 coordinates and original character anchors. Explicit deep passage checks and all writing styles then use bundled Qwen3.5-0.8B Q5_K_M through llama.cpp/Metal. Another grammar pass follows model output. The composed edit plan must reproduce the returned text exactly.

Protected names, links, code, emoji and editor entities are masked during model inference, restored exactly and checked against the final edits. Paragraph whitespace remains in context. Unsafe contextual Fix output is withheld while safe grammar edits remain available with a warning. A failed style does not silently become a grammar-only style result. Selection boundary metadata prevents new terminal punctuation where the passage continues outside the selection.

The 593 MB model, native runtime, dictionary and reviewed rule/frequency assets ship in the app and DMG with licenses, pinned revisions and hashes. Metal uses one serialized model/context per process, bounded context, two CPU threads and memory-mapped weights. Idle model state unloads after 30 seconds. Fast automatic checks do not load weights. Separate native app/editor processes can each load a context; memory use is not a single allocation shared by every integration.

Native accessibility snapshots resolve the focused text ancestry, exclude secure fields, bind source text to a host process, and validate focus, selection and source before range patching. Inline overlays use host bounds. Supported Electron hosts receive the documented accessibility activation attribute, Chromium browsers fall back to `AXEnhancedUserInterface`, and Firefox starts its accessibility engine when the application role is read. No unrelated document traversal or automatic acceptance is used.

Browser snapshots normalize text nodes, paragraph and BR boundaries, map UTF-16 positions back to DOM ranges, and protect mentions, links and readonly islands. Automatic marks are external overlays; input geometry uses a temporary hidden mirror. Checks follow the focused paragraph, defer during IME composition, invalidate changed drafts, and honor host edit refusals. Accessible frames share a bounded native-host queue. The extension is activated per page, with no blanket host permissions.

VS Code automatic diagnostics and inline fixes bind edits to document versions. Linked corrections apply as one transaction with Undo stops. Only local prose receives automatic diagnostics. Other editors can use the bundled UTF-16, versioned stdio LSP. Host adapters own formatting, Undo and version checks; unavailable capabilities retain Copy as a fallback.

Tests establish authored grammar cases, valid counterexamples, exact edit reconstruction, Unicode, protected structures and editor behavior. Protocol/DOM harnesses and actual installed-app acceptance are distinct evidence. Compatibility and quality claims follow those results, rather than assuming that a shared engine proves every English construction or editor.

## Names

![How Parzr protects and capitalizes names: signals from the request, the macOS tagger and lexicon gate, bundled lists and context cues are graded STRONG, MEDIUM or WEAK; a name may only receive case changes, and a lowercase name gets a blue capitalization suggestion](media/names.png)

A name candidate may only change case. `NameIndex::mark` in `engine/src/names.rs` gives every token a level. STRONG comes from the request's `names` and `dictionary`, the same word capitalized elsewhere in the text, an email local part, or a name hint from the macOS tagger. MEDIUM is a bundled name that is not an ordinary word or a known typo. WEAK is context alone: a greeting with a comma, a title, a sign-off, "looping in", a name list or a surname particle (`spelling::lowercase_name`). The tagger hint also covers lowercase names: `parzr_model_token_hints` in `native/model.mm` marks a word as a name when NSSpellChecker rejects it in lowercase but accepts it Capitalized, and the tokenizer drops that hint when the word is a known typo.

In `engine/src/lib.rs`, MEDIUM and stronger names become guard spans (neighbours such as "aman jain" merge into one), and any edit that overlaps a span must be case-only or it is dropped. WEAK names are never respelled, and WEAK and stronger names are masked from the local model. `never_a_name` overrides every signal for known misspellings, days, months, chat shorthand and one or two lowercase letters, so "Teh" still becomes "the". Hinglish words and surname particles (van, der, de) are never capitalized.

A lowercase name that reaches MEDIUM, or a WEAK word the lexicon lists only as a name ("mumbai"), gets a blue `names.capitalize` suggestion when the Name capitalization preference allows it. Names come from your own name, learned names, Contacts (opt-in) and the document, and Parzr learns more from an undone fix (1), an Ignore (2) and repetition (3 sightings over 2 or more app and day pairs). The benchmark in [benchmarks/names](../benchmarks/names/README.md) checks on every pull request and release that names are not damaged: 0.08% overall, 0.18% in lowercase and 1.40% for held-out names, with 94.44% of real typos still corrected.
