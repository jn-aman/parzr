# Architecture

The Apple Silicon macOS app calls the bundled Rust library through bounded JSON FFI. Apple NaturalLanguage supplies token and entity hints; the command-line engine, browser native host and LSP use the same macOS tagger through the native library. No adapter starts a network listener.

Automatic typing runs grammar, spelling and punctuation to a bounded fixed point, retaining UTF-16 coordinates and original character anchors. Explicit deep passage checks and all writing styles then use bundled Qwen3.5-0.8B Q5_K_M through llama.cpp/Metal. Another grammar pass follows model output. The composed edit plan must reproduce the returned text exactly.

Protected names, links, code, emoji and editor entities are masked during model inference, restored exactly and checked against the final edits. Paragraph whitespace remains in context. Unsafe contextual Fix output is withheld while safe grammar edits remain available with a warning. A failed style does not silently become a grammar-only style result. Selection boundary metadata prevents new terminal punctuation where the passage continues outside the selection.

The 593 MB model, native runtime, dictionary and reviewed rule/frequency assets ship in the app and DMG with licenses, pinned revisions and hashes. Metal uses one serialized model/context per process, bounded context, two CPU threads and memory-mapped weights. Idle model state unloads after 30 seconds. Fast automatic checks do not load weights. Separate native app/editor processes can each load a context; memory use is not a single allocation shared by every integration.

Native accessibility snapshots resolve the focused text ancestry, exclude secure fields, bind source text to a host process, and validate focus, selection and source before range patching. Inline overlays use host bounds. Supported Electron hosts receive the documented accessibility activation attribute. No unrelated document traversal or automatic acceptance is used.

Browser snapshots normalize text nodes, paragraph and BR boundaries, map UTF-16 positions back to DOM ranges, and protect mentions, links and readonly islands. Automatic marks are external overlays; input geometry uses a temporary hidden mirror. Checks follow the focused paragraph, defer during IME composition, invalidate changed drafts, and honor host edit refusals. Accessible frames share a bounded native-host queue. The extension is activated per page, with no blanket host permissions.

VS Code automatic diagnostics and inline fixes bind edits to document versions. Linked corrections apply as one transaction with Undo stops. Only local prose receives automatic diagnostics. Other editors can use the bundled UTF-16, versioned stdio LSP. Host adapters own formatting, Undo and version checks; unavailable capabilities retain Copy as a fallback.

Tests establish authored grammar cases, valid counterexamples, exact edit reconstruction, Unicode, protected structures and editor behavior. Protocol/DOM harnesses and actual installed-app acceptance are distinct evidence. Compatibility and quality claims follow those results, rather than assuming that a shared engine proves every English construction or editor.
