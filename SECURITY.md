# Security policy

Parzr reads text in other apps through macOS Accessibility, so we take security reports seriously.

## Reporting a vulnerability

Please report privately through GitHub: open the repository's **Security** tab and choose **Report a vulnerability**. Do not open a public issue for security problems.

Include the Parzr version, macOS version, Mac model, and steps to reproduce. Do not include private writing; a synthetic example is enough.

## Scope

In scope: the macOS app, the Rust engine, the browser and VS Code extensions, the language server, the release pipeline, and parzr.app. Parzr makes no network requests while checking text. Its only requests are the hourly update check (`SUScheduledCheckInterval` 3600, a signed feed; it can be turned off) and the one-time download of its pinned, hash-checked model packs, both from GitHub, and anonymous suggestion reports to `reports.parzr.app` while they are on. Release builds ignore every `PARZR_*` development override and carry no QA test modes. Reports of any unexpected network traffic, text persistence, or edits outside the selected range are especially welcome.

## Supported versions

Only the latest release receives fixes.
