# Writing assistant feature audit

The desktop [Grammarly guide](https://support.grammarly.com/hc/en-us/articles/4412816078349-Grammarly-for-Windows-and-Grammarly-for-Mac-user-guide) describes inline corrections, per-app controls, rewriting prompts and tone feedback. Its [editor guide](https://support.grammarly.com/hc/en-us/articles/360003474732-Grammarly-Editor-user-guide) describes suggestion navigation and adding words to a dictionary. [LanguageTool’s editor](https://help.languagetool.org/hc/en-us/articles/39254517614999-What-is-the-LanguageTool-Editor) combines checking with a dictionary, writing goals and statistics. [ProWritingAid reports](https://prowritingaid.com/features/writing-reports) cover grammar, style, repetition, readability and sentence structure.

Parzr uses those interaction patterns as a checklist, with on-device processing and explicit control over replacements.

| Feature | Parzr implementation | Validation boundary |
|---|---|---|
| Automatic grammar, spelling and punctuation | Fast grammar engine and Apple NaturalLanguage; native range marks, browser overlays and VS Code diagnostics | Authored fixtures and adapter tests; vendor-specific coverage requires actual host tests |
| Word-click correction card | Compact native cards with individual corrections, explanations and a corrected sentence preview | Source, focus and selection are checked again before applying |
| Full selection / full sentence | Visible Fix all for selected passages and Fix sentence in word-click cards; internal review panel and full-passage checking | Native range edits retain formatting where the host exposes them |
| Suggestion list | Review panel with category filters, Apply, Ignore and jumps to draft ranges | Filters affect review presentation; grammar remains enabled |
| Personal dictionary | Writing settings plus Save word in spelling cards and review rows | Local storage; adapters currently accept their own dictionary request configuration |
| Tone rewrites | Five visible mode choices: Fix, Professional, Friendly, Concise and Direct | Bundled local model; wording and meaning still need user review |
| Focus and statistics | Focus writing space, word/character counts and estimated reading time | Reading time uses 200 words per minute; no invented quality score |
| Per-app control | Menu-panel and Apps settings switches | Native source-code/terminal passive checks stay excluded |
| Appearance and motion | Graphite, Paper or System across the studio, menu panel and correction cards; reduced motion | Native text editing, keyboard controls and Undo retained |
| Startup and permissions | Login item, shortcut recording, Accessibility setup and permission refresh | macOS requires the user to grant permission |
| Support and transparency | About, version/build, bundled licenses, capability report and an email issue draft | Reports do not automatically include writing or send email |

Remaining feature work includes evaluated tone detection, calibrated readability feedback, configurable house style, contextual vocabulary alternatives, long-document analysis and independently tested writing-goal controls. These are not labeled as implemented. Adding them requires evidence that they help without changing meaning or adding latency to typing.
