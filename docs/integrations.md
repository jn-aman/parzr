# Editor integrations

Parzr targets writing wherever it happens: native text fields, chat composers, browser rich text, prose in code editors, and editors with an LSP client. Integrations share the local grammar engine and bundled model. A route is implemented when the adapter exists; a particular application is verified only after its text, formatting, selection and Undo pass a fixture test.

## Native macOS editors and desktop chat

Install the Apple Silicon app in Applications, allow Accessibility, and start writing. Automatic checks examine the focused paragraph after 120 ms of idle time. Click an underline for a compact correction; select a passage for Fix all or use the global shortcut. Change Option+Space in **General → Global shortcut**. Pause or disable individual apps in Settings.

The adapter resolves an editable field from the focused element or its nearest accessible ancestors. It uses Electron's documented `AXManualAccessibility` switch to expose supported desktop composers, without app-specific selectors. It observes only the focused field, excludes secure fields and code/terminal applications, and never submits a message. This is a shared route for desktop Teams, Slack, WhatsApp, Discord, Telegram, mail clients and other applications when their accessibility capabilities permit it. Those named hosts have not all been tested.

Before applying, Parzr rechecks the host, focused field, selection and original text. It patches individual UTF-16 ranges and confirms the result. Links and attachments are protected when exposed as attributed text. TextEdit's real capture, typing, underlines, inline acceptance, formatting, caret restoration and Undo have been exercised using authored RTF fixtures.

A host must expose text, selection, range bounds and safe range replacement for the complete inline experience. If replacement is unavailable, Copy remains available. Explicit paste fallback is off by default because it can change complex formatting and mentions. It restores supported clipboard types only when the clipboard has not changed again. macOS Accessibility permission requires the user's system approval; an app cannot grant it to itself.

## Browser writing fields and web chat

The shared extension supports Chrome 121+, Edge, Brave, Chromium, and Firefox 140+. Browser installation and an installed native-host connection are separate from DOM adapter verification. Safari currently uses the native accessibility route; a Safari extension wrapper is not shipped.

For Chromium browsers, load `extensions/browser` unpacked from the browser's extensions page and copy its extension ID. Register the native host for that identity:

```sh
python3 scripts/connect-browser.py --browser chrome --extension-id YOUR_EXTENSION_ID
```

Use `--browser edge`, `brave`, or `chromium` for the corresponding browser. For Firefox, temporarily load the same manifest through `about:debugging` and register its fixed identity:

```sh
python3 scripts/connect-browser.py --browser firefox --extension-id parzr@parzr.app
```

Temporary Firefox installation lasts until browser restart. Persistent Firefox distribution requires Mozilla add-on signing; Developer ID signing of the macOS app does not sign the add-on. A development app can be selected with `--app /absolute/path/to/Parzr.app`.

Activate Parzr once on the current HTTP(S) page using its toolbar button or Alt+Shift+P. It checks writing as you type in focused text inputs, textareas and editable rich-text composers. Underlines open a 260 px correction card. Selected passages open a 300 px review with a visible Fix all button and writing styles. Escape dismisses the current check; typing starts a fresh check. Page navigation requires activation again. Browser shortcut settings control the browser shortcut separately.

The adapter handles empty and plaintext-only `contenteditable` attributes, nested editor nodes, paragraphs, line breaks, and open shadow-root editors. It injects into frames accessible under the activated page's permissions. Cross-origin frames without permission and closed shadow roots are not accessible through this route. It preserves links, code, mentions, readonly islands, emoji and paragraph boundaries. Highlight overlays live outside the host editor; they do not modify its document model. IME composition defers checks until the input is committed. Changing drafts invalidate pending results and existing correction cards.

Automatic grammar checks use the fast engine; selection reviews you start and writing styles use the bundled model between grammar passes. Model refinement that cannot preserve a protected element is withheld. Fix still returns safe grammar edits with an explicit context-refinement warning; style failures are reported without applying anything. Editor `beforeinput` refusals are respected, and original text is checked between patches. Native editing commands preserve the host's Undo behavior; a rich-text Fix all may need multiple Undo steps.

The extension requests `activeTab`, `scripting`, and `nativeMessaging`, with no blanket website access. Password, OTP, readonly, disabled and private fields are excluded. Text goes only to the native process on this Mac. Firefox's consent declaration includes website content and personal communications because its policy covers transfer to a native application, even locally. No HTTP writing service, remote model, account or text telemetry is involved. One persistent native-host process serves browser frames with bounded, coalesced queues.

Teams web, Slack web, Gmail, Outlook web, WhatsApp web, Discord web, support consoles, CMS editors and form composers can use this common DOM route when they expose those capabilities. Their actual production sites are not established by a synthetic composer test. Canvas editors, custom document models, framework refusals and Google Docs' document canvas can require a dedicated host adapter; Copy and the native capability probe remain available.

## VS Code and compatible forks

The local extension automatically underlines grammar in plaintext, Markdown, MDX and commit messages after 180 ms of idle time. Use the editor's quick-fix/lightbulb menu to accept a correction, including linked multi-part corrections, or choose **Parzr: Fix all grammar**. Corrections are atomic editor edits with Undo stops. Document versions and source text are checked again before applying. Disable automatic checks with `parzr.automatic`.

For passage styles, select text and run **Parzr: Improve selected text**. The extension previews a diff before Apply or Copy. Alt+Space can be changed in Keyboard Shortcuts. The engine defaults to `/Applications/Parzr.app/Contents/MacOS/parzr-engine`; `parzr.enginePath` is a machine setting. Local untitled documents are supported. Remote and virtual workspaces do not use this local macOS engine. Code is not automatically submitted; explicit code selections require prose confirmation.

VS Code-compatible forks such as Cursor can install the same extension where their APIs permit it; individual fork UI behavior requires verification. Package a VSIX from `extensions/vscode`:

```sh
npx @vscode/vsce package --no-dependencies --allow-missing-repository --out ../../dist/parzr-0.1.0.vsix
```

Marketplace publication requires a configured publisher account.

## Other editors through LSP

Configure an editor's LSP client to launch `/Applications/Parzr.app/Contents/MacOS/parzr-lsp` for plaintext and Markdown using local stdio, UTF-16 positions and full document synchronization. It publishes automatic grammar diagnostics, correction quick fixes and selected-passage style actions. Returned edits include the analyzed document version. Surrounding Markdown code is protected even for passage selections.

Neovim, Emacs, Zed, Helix and Sublime can use this route through compatible LSP clients. Protocol tests establish framing, Unicode, versioning, protection and linked corrections; each editor's configuration, UI and Undo still need validation. Analysis is capped at 64 KB, storage at 256 KB per document and 32 open documents. No network socket or runtime account is required.

## Compatibility evidence

| Editor family / example | Implemented route | Evidence / remaining verification |
|---|---|---|
| TextEdit | Native AX | Authored RTF typing, inline application, formatting, caret and Undo tests |
| Native text views; Notes, Mail, Pages, Word | Focus ancestry + AX capability probe | Native core tests; individual application fixtures required |
| Teams, Slack, WhatsApp and other desktop chat | Native AX; supported Electron accessibility activation | Adapter implemented; actual named desktop hosts unverified |
| Text input / textarea | Automatic browser underlines and inline corrections | Real Chromium DOM, engine, focus, single-correction Undo and stale-draft tests |
| Teams/Slack-shaped rich composer | Shared rich-text browser adapter | Synthetic nested composer, mention, emoji, formatting, paragraphs and Undo tests; actual services unverified |
| Gmail, Outlook, WhatsApp web, Discord web, CMS editors | Same DOM route | Implemented capability route; individual sites require tests |
| Paragraph/BR and open shadow-root editors | Shared browser adapter | Chromium DOM range, protection and end-insertion tests |
| Accessible embedded frames | Browser frame injection | Injection/queue tests; installed-browser frame smoke tests pending |
| Chrome / Edge / Brave / Chromium | Extension + native host | Shared DOM and messaging protocol tested; full installed-browser smoke tests pending |
| Firefox 140+ | Shared MV3 extension + native host | Manifest and registration implemented; Firefox DOM/native-host acceptance pending |
| Safari | Native AX | Native route; no Safari extension wrapper |
| VS Code | Automatic diagnostics, inline code actions, passage styles | Engine/API harness checks stale versions, linked fixes, Undo transactions and local prose restrictions; actual extension-host UI acceptance pending |
| Cursor and other VS Code forks | Same extension | Individual fork acceptance pending |
| Neovim / Emacs / Zed / Helix / Sublime | Bundled LSP | Protocol tests; individual clients need setup/UI acceptance |
| Google Docs canvas / closed shadow DOM / custom document models | Native probe, dedicated adapter where available, Copy fallback | Automatic formatting-safe editing not verified |

Sources for adapter behavior: [Electron accessibility activation](https://github.com/electron/electron/blob/main/docs/tutorial/accessibility.md), [Chrome activeTab](https://developer.chrome.com/docs/extensions/develop/concepts/activeTab), [cross-browser MV3 background scripts](https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/manifest.json/background), and [Firefox native data consent](https://extensionworkshop.com/documentation/develop/best-practices-for-collecting-user-data-consents/).

## Canvas editors (Google Docs)

Google Docs draws text on a canvas, so macOS Accessibility exposes no document text or selection there. The explicit check shortcut falls back to copying the selection: Parzr sends Cmd+C, reads the text, and restores the previous clipboard. Applying re-copies to confirm the selection is unchanged, then pastes the corrected text over it and restores the clipboard again. Automatic underlines are not available in canvas editors.
