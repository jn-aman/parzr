# Editor integrations

Parzr targets writing wherever it happens: native text fields, chat composers, browser rich text, prose in code editors, and editors with an LSP client. Integrations share the local grammar engine and bundled model. Smart grammar (the on-device GECToR model) is a setting of the Mac app: the browser extension, VS Code and language-server routes run the rules engine without it. A route is implemented when the adapter exists; a particular application is verified only after its text, formatting, selection and Undo pass a fixture test.

## No extension needed

Parzr works through macOS Accessibility, so no browser or editor extension is required. Safari, Chrome, Brave, Edge, Arc and Firefox work natively, as do TextEdit, Mail, Microsoft Word and (after one switch in Docs) Google Docs. The browser extension, the VS Code extension and the language server are optional: [Install the optional extensions](#install-the-optional-extensions) says when each is worth having and how to set it up.

What has been checked, and how (macOS accessibility probes, not full acceptance suites):

- **Verified by probes:** TextEdit, Safari, Chrome, Brave and Firefox with default settings (text fields, textareas and contenteditable): focus, text, selection and replacement.
- **Read verified:** Microsoft Word 16 reads text and selection (replacement uses the typed path below); Mail compose reads text, selection, word bounds and attributed text through WebKit text markers. Typed replacement in Mail and Word was not exercised live.
- **Verified end to end:** Google Docs in Chrome, with Docs' screen reader and braille support on (see [Google Docs](#google-docs-chrome-edge-brave-arc)).
- **Unit-tested only:** Electron re-activation, the VS Code and Cursor opt-in, Xcode comment and string filtering, and the Firefox hint.
- **Untested:** Slack, Teams and Notion were not installed for testing.

## Install the optional extensions

Parzr needs no extension anywhere. These three adapters exist for the places where macOS Accessibility cannot do the job. Each one runs the local engine from your installed Parzr: the rules while you type, the bundled Qwen model for tones and selection reviews, no Smart grammar, no network, no account, so **Parzr must be in /Applications** first. They also read the app's dictionary and learned names (`~/Library/Application Support/Parzr/known-words.json`, which the app keeps up to date), so a name you taught the app is not respelled in them either.

| You write in | Why you might want an extension | Install |
| --- | --- | --- |
| VS Code, Cursor | The app cannot underline words there (VS Code exposes no word positions): it only shows a review marker. The extension gives real squiggles, the Problems panel and quick fixes in Markdown, plain text and commit messages. | [VS Code and Cursor](#vs-code-and-cursor-extension) |
| A web editor Accessibility cannot read or edit (a rich composer, a custom editor) in Chrome, Edge, Brave, Chromium or Firefox | The extension works on the page's own DOM and keeps its formatting and Undo. Google Docs does not need it: see [Google Docs](#google-docs-chrome-edge-brave-arc). | [Browser](#browser-extension-chrome-edge-brave-chromium-firefox) |
| Neovim, Helix, Emacs, Zed, Sublime, a terminal editor | The app skips Terminal, iTerm, Zed and JetBrains. Any editor with an LSP client can use the bundled language server instead. | [Other editors](#other-editors-language-server) |

**Where the files come from.** Each release carries `parzr-vscode-X.Y.Z.vsix` and `parzr-browser-extension-X.Y.Z.zip` beside the DMG, listed in `SHA256SUMS`; check a download with `shasum -a 256 -c SHA256SUMS --ignore-missing` in the folder that holds both files. The app also carries an unpacked copy of the browser extension, the VS Code extension sources and the registration script in `Parzr.app/Contents/Resources/Integrations` (**Settings, Integrations, Open integrations** opens that folder). Use the same version as your app.

### VS Code and Cursor extension

1. Download `parzr-vscode-X.Y.Z.vsix` from the [latest release](https://github.com/jn-aman/parzr/releases/latest).
2. In VS Code open the Extensions view (Cmd+Shift+X), choose the **...** menu at the top of the panel, then **Install from VSIX...** and pick the file. Or in a terminal: `code --install-extension ~/Downloads/parzr-vscode-X.Y.Z.vsix` (VS Code's Command Palette has **Shell Command: Install 'code' command in PATH** if `code` is missing). Cursor has the same menu (not tested here).
3. Open a Markdown or plain text file (or set an untitled file's language to Markdown) and write. After 180 ms of idle time issues are underlined (Information severity, listed in the Problems panel). Press Cmd+. on one for **Change to ...**, or choose **Parzr: Fix all grammar** from the same menu. Select a passage and press Alt+Space (or run **Parzr: Improve selected text**) for Fix, Professional, Friendly, Concise or Direct with a diff to review.
4. If Parzr is not in /Applications, set `parzr.enginePath` (a machine setting) to `.../Parzr.app/Contents/MacOS/parzr-engine`. A `Parzr` warning in the status bar means the engine could not start; hover it for the reason.
5. Leave **Settings, Apps, Check prose in VS Code and Cursor** off in the app while you use the extension, otherwise both check the same files.

Settings: `parzr.automatic` (on), `parzr.dictionary`, `parzr.names`, `parzr.enginePath`. Only local files and untitled documents are checked; remote and virtual workspaces are not.

### Browser extension (Chrome, Edge, Brave, Chromium, Firefox)

A browser extension cannot start programs by itself, so there are two parts: the extension, and a small file that tells the browser where Parzr's native host lives. **Parzr.app never writes into a browser's folders; you run the registration script once.**

1. Get the extension folder. Either open **Settings, Integrations, Open integrations** in Parzr and use `extensions/browser`, or download `parzr-browser-extension-X.Y.Z.zip` from the release and unzip it (Finder makes a folder with `manifest.json` inside). Keep the folder where it is: the browser loads it from there each time.
2. Open `chrome://extensions` (`edge://extensions`, `brave://extensions`), switch on **Developer mode**, choose **Load unpacked** and select the folder that contains `manifest.json`. The extension always gets the same ID (`hhfnplahgjogkpcbjekcbmlhgjmngdjd`), because its manifest carries a fixed public key, wherever the folder is.
3. Register the host, in Terminal, with your browser (`chrome`, `edge`, `brave` or `chromium`):

   ```sh
   python3 /Applications/Parzr.app/Contents/Resources/Integrations/connect-browser.py --browser chrome
   ```

   It writes `dev.parzr.engine.json` into that browser's `NativeMessagingHosts` folder under `~/Library/Application Support` (Google/Chrome, Microsoft Edge, BraveSoftware/Brave-Browser or Chromium). The file names `Parzr.app/Contents/MacOS/parzr-native-host` and allows only the extension's fixed ID to start it (pass `--extension-id` only for a fork or a store build with a different ID). Use `--app /path/to/Parzr.app` if Parzr is elsewhere. The script needs `python3`; on a Mac without developer tools, macOS offers to install them the first time. No browser restart is needed.
4. Pin the extension (the puzzle piece menu), open a page with a text field and click the Parzr button or press Alt+Shift+P (change it at `chrome://extensions/shortcuts`). The extension checks only the page you activated; activate it again after navigating. A `!` on the button means the browser does not allow extensions on that page (for example `chrome://` pages).

If the card says "Connect the Parzr native host first", step 3 is missing, or it named a different browser than the one you loaded the extension into. Moving or reloading the folder does not change the ID, so step 3 is needed only once per browser. Check the ID under the extension's name on the extensions page if in doubt.

**Firefox 140 or newer.** Open `about:debugging#/runtime/this-firefox`, choose **Load Temporary Add-on** and select `manifest.json` in the folder, then run the script; it already knows the add-on's fixed ID (`parzr@parzr.app`):

```sh
python3 /Applications/Parzr.app/Contents/Resources/Integrations/connect-browser.py --browser firefox
```

A temporary add-on disappears when Firefox quits (a permanent one needs Mozilla's signing, which Parzr does not have). Arc has no `--browser` option and Safari has no extension; both work through the native Accessibility route without one.

To remove it, delete the extension in the browser and delete `dev.parzr.engine.json` from the `NativeMessagingHosts` folder the script printed.

### Other editors (language server)

Any editor with an LSP client can launch `/Applications/Parzr.app/Contents/MacOS/parzr-lsp` with no arguments over stdio. It handles `plaintext` and `markdown` documents only, sends diagnostics and quick fixes, and takes optional `initializationOptions` `{"names": [...], "dictionary": [...]}`. In Neovim 0.11 or newer:

```lua
vim.lsp.config('parzr', {
  cmd = { '/Applications/Parzr.app/Contents/MacOS/parzr-lsp' },
  filetypes = { 'markdown', 'text' },
  get_language_id = function(_, ft) return ft == 'text' and 'plaintext' or ft end,  -- the server only accepts plaintext and markdown
})
vim.lsp.enable('parzr')
```

Other clients need the same three facts: the command, the file types, and the language IDs `plaintext` and `markdown`.

### From source

For development, or to test a change, build the two files yourself. Node 22 or newer is required.

```sh
python3 scripts/package-extensions.py      # writes dist/extensions/parzr-vscode-X.Y.Z.vsix and parzr-browser-extension-X.Y.Z.zip
code --install-extension dist/extensions/parzr-vscode-X.Y.Z.vsix
```

The browser extension needs no build: load `extensions/browser` unpacked as above. Use `--app dist/Parzr.app` with the registration script for a development build, and `parzr.enginePath` for VS Code. CI builds the same files from the tagged sources and attaches them to each release.

### What was tested

Checked on this Mac with throwaway profiles (nothing was installed into a real browser or VS Code):

- The VSIX builds, and installs with `code --install-extension` into a separate user-data and extensions directory. The engine process the extension starts answered the extension's request with corrections.
- The browser ZIP, unpacked, loads in Chromium (Chrome for Testing) with a fresh profile and shows the fixed ID. Before registering, the extension's connection fails with "Specified native messaging host not found". After `connect-browser.py`, the same browser (still running) started `parzr-native-host` and got corrections back ("I recieved teh mesage" became "I received the message").
- `parzr-lsp` answered an initialize request, published diagnostics for a Markdown document and returned a quick fix, over stdio.

Not checked: the toolbar click and Alt+Shift+P (Chrome only grants a page to the extension on a real click), Firefox, Edge, Brave, Cursor, and the Neovim snippet above (no Neovim here). The extension's page adapter is covered by the Playwright suite, which talks to the engine through a test bridge rather than native messaging.

## Native macOS editors and desktop chat

Install the Apple Silicon app in Applications, allow Accessibility, and start writing. Automatic checks examine the focused paragraph after a short pause (35 ms at the default Checking delay of 90 ms, at once after a space or punctuation key; the setting runs from 40 to 700 ms). Click an underline for a compact correction; select a passage for Fix all or use the global shortcut. Change Option+Space in **Settings, General, Your shortcut**. Pause or disable individual apps in Settings.

The adapter resolves an editable field from the focused element or its nearest accessible ancestors. It uses Electron's documented `AXManualAccessibility` switch to expose supported desktop composers, without app-specific selectors. The switch is set again on every app activation and focus change (at most once per 2 seconds per app), because the first set builds the tree and a second one makes the editor switch modes. When an app answers the per-app focus query with an error, the system-wide focused element is used if it belongs to the same process. It observes only the focused field, excludes secure fields, JetBrains, Zed and terminals, and never submits a message. This is a shared route for desktop Teams, Slack, WhatsApp, Discord, Telegram, mail clients and other applications when their accessibility capabilities permit it. Those named hosts have not all been tested.

Before applying, Parzr rechecks the host, focused field, selection and original text. It patches individual UTF-16 ranges and confirms the result by reading the text back. Word, VS Code in screen-reader mode and Chrome textareas accept an `AXSelectedText` write and change nothing, so when the read-back shows no change Parzr selects the range and types the replacement as Unicode keyboard events posted to that app (20 UTF-16 units per event, no clipboard), then verifies again. It types only while the app is frontmost and the same field is still focused, and never when the text changed unexpectedly. A settable selection range is enough for this route. Links and attachments are protected when exposed as attributed text. Editable web areas without AXValue (Mail compose and other WebKit editors) are read through accessibility text markers: text, selection, word bounds and attributed text, with replacement by selecting the markers and typing. Xcode is checked in comments, documentation and string literals only: every other run of the file's semantic types is protected. TextEdit's real capture, typing, underlines, inline acceptance, formatting, caret restoration and Undo have been exercised using authored RTF fixtures.

A host must expose text, selection, range bounds and safe range replacement for the complete inline experience. If replacement is unavailable, Copy remains available. Explicit paste fallback is off by default because it can change complex formatting and mentions. It restores supported clipboard types only when the clipboard has not changed again. macOS Accessibility permission requires the user's system approval; an app cannot grant it to itself.

### Firefox, Chromium and Electron

Firefox 121+ starts its accessibility engine when Parzr reads the application role, so default Firefox needs nothing. If a user has turned on "Prevent accessibility services from accessing your browser" (Settings, Privacy & Security, Permissions), Firefox exposes no text; after several keystrokes with no field found, the menu-bar panel shows a one-time dismissible hint explaining how to turn that off. Parzr never edits Firefox's profile. Chromium browsers also get `AXEnhancedUserInterface`, which Chrome needs to report word bounds for underlines. The first focus query after activation can see only the menu bar, so Parzr looks once more after 1.5 seconds.

### VS Code and Cursor (opt-in)

Off by default. Turn on **Settings, Apps, Check prose in VS Code and Cursor** to check Markdown and plain text files (.md, .markdown, .txt, .mdx, .rst, judged from the window title) in VS Code and Cursor without the extension. This enables VS Code's screen-reader mode, which shows a notice in the editor. VS Code exposes no word geometry in this mode (all bounds are 0x0), so there are no underlines: a review marker appears at the top right of the editor and opens the normal card, and corrections are typed in. Source files are never checked automatically.

## Browser writing fields and web chat (optional extension)

The shared extension supports Chrome 121+, Edge, Brave, Chromium, and Firefox 140+. Browser installation and an installed native-host connection are separate from DOM adapter verification. Safari currently uses the native accessibility route; a Safari extension wrapper is not shipped.

Install steps, for Chromium browsers and Firefox, are in [Install the optional extensions](#browser-extension-chrome-edge-brave-chromium-firefox). The short version: load `extensions/browser` unpacked, then run `connect-browser.py` once for your browser (the extension's ID is fixed) so the browser may start `parzr-native-host`. Persistent Firefox distribution requires Mozilla add-on signing; Developer ID signing of the macOS app does not sign the add-on.

Activate Parzr once on the current HTTP(S) page using its toolbar button or Alt+Shift+P. It checks writing as you type in focused text inputs, textareas and editable rich-text composers. Underlines open a 260 px correction card. Selected passages open a 300 px review with a visible Fix all button and writing styles. Escape dismisses the current check; typing starts a fresh check. Page navigation requires activation again. Browser shortcut settings control the browser shortcut separately.

The adapter handles empty and plaintext-only `contenteditable` attributes, nested editor nodes, paragraphs, line breaks, and open shadow-root editors. It injects into frames accessible under the activated page's permissions. Cross-origin frames without permission and closed shadow roots are not accessible through this route. It preserves links, code, mentions, readonly islands, emoji and paragraph boundaries. Highlight overlays live outside the host editor; they do not modify its document model. IME composition defers checks until the input is committed. Changing drafts invalidate pending results and existing correction cards.

Automatic grammar checks use the fast engine; selection reviews you start and writing styles use the bundled model between grammar passes. Model refinement that cannot preserve a protected element is withheld. Fix still returns safe grammar edits with an explicit context-refinement warning; style failures are reported without applying anything. Editor `beforeinput` refusals are respected, and original text is checked between patches. Native editing commands preserve the host's Undo behavior; a rich-text Fix all may need multiple Undo steps.

The extension requests `activeTab`, `scripting`, and `nativeMessaging`, with no blanket website access. Password, OTP, readonly, disabled and private fields are excluded. Text goes only to the native process on this Mac. Firefox's consent declaration includes website content and personal communications because its policy covers transfer to a native application, even locally. No HTTP writing service, remote model, account or text telemetry is involved. One persistent native-host process serves browser frames with bounded, coalesced queues.

Teams web, Slack web, Gmail, Outlook web, WhatsApp web, Discord web, support consoles, CMS editors and form composers can use this common DOM route when they expose those capabilities. Their actual production sites are not established by a synthetic composer test. Canvas editors, custom document models, framework refusals and Google Docs' document canvas can require a dedicated host adapter; Copy and the native capability probe remain available.

## VS Code and compatible forks (optional extension)

The local extension automatically underlines grammar in plaintext, Markdown, MDX and commit messages after 180 ms of idle time. Use the editor's quick-fix/lightbulb menu to accept a correction, including linked multi-part corrections, or choose **Parzr: Fix all grammar**. Corrections are atomic editor edits with Undo stops. Document versions and source text are checked again before applying. Disable automatic checks with `parzr.automatic`.

For passage styles, select text and run **Parzr: Improve selected text**. The extension previews a diff before Apply or Copy. Alt+Space can be changed in Keyboard Shortcuts. The engine defaults to `/Applications/Parzr.app/Contents/MacOS/parzr-engine`; `parzr.enginePath` is a machine setting. Local untitled documents are supported. Remote and virtual workspaces do not use this local macOS engine. Code is not automatically submitted; explicit code selections require prose confirmation.

VS Code-compatible forks such as Cursor can install the same extension where their APIs permit it; individual fork UI behavior requires verification. Each release attaches the VSIX (`parzr-vscode-X.Y.Z.vsix`); [Install the optional extensions](#vs-code-and-cursor-extension) has the steps, and `python3 scripts/package-extensions.py` builds it from source. Marketplace publication requires a configured publisher account and is not set up.

## Other editors through LSP

Configure an editor's LSP client ([example](#other-editors-language-server)) to launch `/Applications/Parzr.app/Contents/MacOS/parzr-lsp` for plaintext and Markdown using local stdio, UTF-16 positions and full document synchronization. It publishes automatic grammar diagnostics, correction quick fixes and selected-passage style actions. Returned edits include the analyzed document version. Surrounding Markdown code is protected even for passage selections.

Neovim, Emacs, Zed, Helix and Sublime can use this route through compatible LSP clients. Protocol tests establish framing, Unicode, versioning, protection and linked corrections; each editor's configuration, UI and Undo still need validation. Analysis is capped at 64 KB, storage at 256 KB per document and 32 open documents. No network socket or runtime account is required.

## Compatibility evidence

| Editor family / example | Implemented route | Evidence / remaining verification |
|---|---|---|
| TextEdit | Native AX | Verified earlier on TextEdit itself; the automated typing, paste, inline application, formatting, caret and Undo tests now drive a fixture AppKit text view (same text system), never TextEdit |
| Mail compose | AX text markers (WebKit) | Read, selection, word bounds and attributed text verified live on a fixture compose; typed replacement not exercised |
| Microsoft Word | Native AX, typed replacement | Text and selection read verified; replacement unverified |
| Xcode | Native AX, comments and strings only | Semantic-type filtering unit-tested; works as a text editor today |
| Native text views; Notes, Pages | Focus ancestry + AX capability probe | Native core tests; individual application fixtures required |
| Teams, Slack, WhatsApp and other desktop chat | Native AX; supported Electron accessibility activation | Adapter implemented; actual named desktop hosts unverified |
| Text input / textarea | Automatic browser underlines and inline corrections | Real Chromium DOM, engine, focus, single-correction Undo and stale-draft tests |
| Teams/Slack-shaped rich composer | Shared rich-text browser adapter | Synthetic nested composer, mention, emoji, formatting, paragraphs and Undo tests; actual services unverified |
| Gmail, Outlook, WhatsApp web, Discord web, CMS editors | Same DOM route | Implemented capability route; individual sites require tests |
| Paragraph/BR and open shadow-root editors | Shared browser adapter | Chromium DOM range, protection and end-insertion tests |
| Accessible embedded frames | Browser frame injection | Injection/queue tests; installed-browser frame smoke tests pending |
| Chrome / Edge / Brave / Chromium | Extension + native host | Shared DOM and messaging protocol tested. The release ZIP loaded unpacked in a throwaway Chromium profile and, after `connect-browser.py`, a running browser reached `parzr-native-host` and got corrections; toolbar activation, Edge and Brave not run |
| Firefox 140+ | Shared MV3 extension + native host | Manifest and registration implemented; Firefox DOM/native-host acceptance pending |
| Safari / Chrome / Brave / Firefox (default settings) | Native AX, no extension | Verified by accessibility probes: focus, text, selection and replacement; Edge and Arc share the Chromium route and are unprobed |
| VS Code and Cursor without the extension | Native AX, opt-in, prose files only, review marker | Focus, Electron switch and typed replacement probed in VS Code; Cursor and the review marker unit-tested only |
| VS Code (extension) | Automatic diagnostics, inline code actions, passage styles | Engine/API harness checks stale versions, linked fixes, Undo transactions and local prose restrictions; the VSIX builds and installs into a throwaway VS Code profile; extension-host UI acceptance pending |
| Cursor and other VS Code forks | Same extension | Individual fork acceptance pending |
| Neovim / Emacs / Zed / Helix / Sublime | Bundled LSP | Protocol tests, plus a stdio session (initialize, diagnostics, quick fix) against the built server; individual clients need setup/UI acceptance |
| Google Docs (screen reader and braille support on) | Native, no extension: hidden text area plus caret geometry, typed replacement | Verified in Chrome: underlines, card, apply, Undo |
| Google Docs with the support off, other canvas editors, custom document models | Copy fallback | Automatic formatting-safe editing not verified |

Sources for adapter behavior: [Electron accessibility activation](https://github.com/electron/electron/blob/main/docs/tutorial/accessibility.md), [Chrome activeTab](https://developer.chrome.com/docs/extensions/develop/concepts/activeTab), [cross-browser MV3 background scripts](https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/manifest.json/background), and [Firefox native data consent](https://extensionworkshop.com/documentation/develop/best-practices-for-collecting-user-data-consents/).

## Google Docs (Chrome, Edge, Brave, Arc)

Google Docs draws its page on a canvas, so by default macOS Accessibility sees no text there. Docs has a screen reader mode that publishes the text, and Parzr reads it natively, with no browser extension.

**One-time setup, once per Google account.** In Docs choose Tools, Accessibility, then turn on "Turn on screen reader support" and "Turn on braille support". Parzr never toggles these for you. Until they are on, Parzr sees only zero-width characters in Docs; after eight keystrokes with nothing readable it shows a hint in the menu-bar popover ("Don't show again" is remembered), and Option+Space keeps working through the copy and paste fallback.

**What works with it on**

- Automatic underlines while you type, for the paragraph the caret is in.
- Click an underline to open the correction card, anchored under the word; apply one fix or the whole sentence.
- Option+Space on a selection reads it through Accessibility (no clipboard) and applies the same way.
- Applying selects the range and types the replacement, because Docs accepts a write to the selected text and ignores it. The text is read back to confirm, and one Cmd+Z in Docs restores the original word. The caret is put back where you were typing.

**How the positions are found.** Docs' text area has no word geometry. Parzr combines two things Docs does expose: a hidden copy of the paragraph text with true horizontal positions, and the caret's position on screen (the origin of its text-event frame). A word's place is the caret plus its offset in the hidden copy; the hidden copy's lines are about 4 percent taller than the real ones, which Parzr corrects with a measured factor. Docs also counts selection offsets without paragraph breaks, so Parzr converts those, and decides which side of a paragraph break the caret is on from its horizontal position.

**Limits**

- Marks follow the caret: they show only while the caret is on screen, and they hide while you scroll and return when it settles. A document with a selection has no visible caret element, so only the card anchors there, not word underlines.
- The text Docs exposes is the part of the document around the caret, not always all of it.
- Line spacing, zoom (100 and 150 percent measured) and font sizes (11 and 16 point measured) are handled; a caret on a blank line has no hidden text to anchor on, so no marks appear until it moves.
- Replacements are typed, so Docs' own auto-substitutions (smart quotes, auto-capitalization) can alter a replacement; Parzr reads the text back and reports a mismatch instead of continuing.
- Only `docs.google.com/document` pages are handled; Sheets and Slides are not.
- Chrome is the browser this was measured in. Edge, Brave and Arc share its engine and the same detection (the text area, not the browser, is matched), but were not run here. Safari was not tested.

Without the setup, or in any other canvas editor, the explicit check shortcut falls back to copying the selection: Parzr sends Cmd+C, reads the text, and restores the previous clipboard. Applying re-copies to confirm the selection is unchanged, then pastes the corrected text over it and restores the clipboard again. Automatic underlines are not available there.
