# Security policy

Parzr reads text in other apps through macOS Accessibility, so we take security reports seriously.

## Reporting a vulnerability

Please report privately through GitHub: open the repository's **Security** tab and choose **Report a vulnerability**. Do not open a public issue for security problems.

Include the Parzr version, macOS version, Mac model, and steps to reproduce. Do not include private writing; a synthetic example is enough.

## Scope

In scope: the macOS app, the Rust engine, the browser and VS Code extensions, the language server, the release pipeline, and parzr.app. Parzr makes no network requests while checking text (its only request is the daily, optional update check to GitHub), so reports of any unexpected network traffic, text persistence, or edits outside the selected range are especially welcome.

## Supported versions

Only the latest release receives fixes.
