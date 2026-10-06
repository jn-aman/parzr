# Parzr

## Platform and purpose

A native macOS 13+ writing assistant for English prose. SwiftUI and AppKit provide the shell; the Rust grammar engine, an on-device GECToR grammar model (Core ML, Neural Engine) and a bundled Qwen3.5-0.8B Q5_K_M model perform local analysis. Release targets are Apple Silicon arm64 only.

Grammar, spelling and punctuation run in every mode. Fix corrects prose; Professional, Friendly, Concise and Direct add deliberate tone changes. Correctness runs again after tone changes. Broad English coverage is an ongoing engineering goal; universal grammar detection is not a verified claim.

## Editor experience

Automatic suggestions are enabled by default after Accessibility is granted. A short idle delay checks the current paragraph. Accurate editor bounds allow clickable inline underlines and a compact correction card; other accessible hosts receive a nearby review marker. Corrections always require explicit acceptance. Pause and per-app controls are available.

Option+Space opens a 340 × 218 point correction popover with one correction at a time, navigation, Ignore, mode selection, Copy and Apply all. Settings allow recording a different global shortcut, resetting it and resolving registration conflicts. Browser adapters automatically underline writing in inputs and rich chat composers; VS Code provides automatic diagnostics and inline quick fixes. A local language server extends coverage to other editors. Compatibility depends on actual host capabilities and test evidence.

## Safety and privacy

Revalidate focus, selection and source before applying minimal UTF-16 range edits. Preserve surviving formatting and host Undo where the editor supports them. Protect code, links, numbers, names, dictionary entries, attachments, quoted replies and signatures. Exclude secure fields and terminal/code contexts from passive observation.

Writing remains transient in memory. Both models and the native runtime ship in the app and DMG. No runtime model download, account, HTTP service, telemetry or writing logs. The only network request is the optional daily update check, which carries nothing about the user or their writing. Clipboard fallback is explicit and disabled by default. Unsupported hosts offer Copy or the playground rather than unsafe replacement.

## Interface

Parzr, an authored geometric P mark, Graphite surfaces and mint correction accents. Native prose typography, one editable writing surface with temporary underlines, 340 × 200 point draft corrections and 340 × 218 point host-editor corrections. Native menu-bar items show pause, automatic highlighting and per-app state. Native buttons provide keyboard and accessibility activation. Opening the app restores its existing window, including when closed or minimized. Motion communicates state changes, responds immediately to input and respects Reduce Motion.

## Open source and distribution

Apache-2.0 with required third-party license notices and source provenance. Keep public content limited to product source, tests, licenses, documentation and automation. Keep credentials, local workspace state, generated artifacts and private planning inputs outside the public repository.

CI verifies versions, repository contents, engine/native/editor checks and local packaging. Tagged releases build arm64 binaries, Developer ID sign, notarize, staple, validate, checksum and publish immutable assets. Signing or notarization failure stops publication. Development DMGs report the actual app signature and remain unnotarized. Reproducible dependency resolution does not imply byte-identical signed artifacts.

## Website

Plan parzr.app on Cloudflare Pages or Workers static assets. Build and deploy only after desktop acceptance and a verified signed release. Use actual screenshots and evidence-backed compatibility and performance claims. See [website plan](docs/website-plan.md).

## Interface and controls

The native app uses a Graphite writing canvas, persistent sidebar navigation, compact inline cards, and an original folded P icon. Settings cover launch at login, Dock visibility, automatic checks, selected-text cards, recorded shortcuts, English variant, default mode, personal dictionary, checking delay, context refinement, Smart grammar, per-app enablement, clipboard fallback, Graphite/Paper/System appearance, reduced motion, highlight tint, draft text size, line spacing, and word count. Font and spacing affect the internal writing space. Browser and VS Code checking behavior is configured through their adapters.

Typing always uses the fast grammar path: the rules plus the Smart grammar model (GECToR, setting on by default), never Qwen. Check passage explicitly reviews the complete draft in the selected mode. Changing writing mode requests a rewrite. Context refinement can be disabled for Fix checks; tone rewrites still use the bundled model. Short success effects use the MIT-licensed Pow library, honor reduced motion, and never animate typing highlights. macOS still requires the user to grant Accessibility; Parzr opens the right settings page and detects the permission change.
