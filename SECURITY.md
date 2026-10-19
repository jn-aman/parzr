# Security policy

Parzr reads text in other apps through macOS Accessibility, so we take security reports seriously.

## Reporting a vulnerability

Please report privately through GitHub: open the repository's **Security** tab and choose **Report a vulnerability**. Do not open a public issue for security problems.

Include the Parzr version, macOS version, Mac model, and steps to reproduce. Do not include private writing; a synthetic example is enough.

## Scope

In scope: the macOS app, the Rust engine, the browser and VS Code extensions, the language server, the release pipeline (`.github/workflows`, `scripts/`), the model packs, the reports Worker at reports.parzr.app, and parzr.app. While checking text Parzr makes no network requests; its only requests are the optional hourly update check and the one-time download of its pinned, hash-checked model packs (both from this repository's GitHub releases) and, unless switched off in Settings, Privacy, anonymous redacted reports of suggestions the writer ignores or marks wrong (see worker/README.md). Reports of any other network traffic, text persistence, or edits outside the selected range are especially welcome.

## Verifying a download

Every release is built and signed by GitHub Actions from a commit on `main` (docs/releases.md):

- The DMG and app are signed with Parzr's Developer ID and notarized by Apple: `spctl -a -t open --context context:primary-signature -v Parzr-X.Y.Z.dmg`.
- `SHA256SUMS` lists every release file: `shasum -a 256 -c SHA256SUMS --ignore-missing`.
- Every file in `SHA256SUMS` has a build provenance attestation: `gh attestation verify Parzr-X.Y.Z.dmg --repo jn-aman/parzr`. The release also carries an SPDX SBOM (`parzr-vX.Y.Z.spdx.json`).
- Automatic updates are accepted only with a valid EdDSA signature from Parzr's update key (public key in the app's `SUPublicEDKey`); check a release's feed with `python3 scripts/make-appcast.py verify --appcast https://github.com/jn-aman/parzr/releases/download/vX.Y.Z/appcast.xml`.

Published releases are immutable, and release and model tags cannot be moved or deleted.

## Supported versions

Only the latest release receives fixes. A security fix ships as a critical update, which installed copies take promptly and cannot skip.
