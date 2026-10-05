# Releases

The workflow in [.github/workflows/ci-release.yml](../.github/workflows/ci-release.yml) verifies pull requests and branch pushes, builds a development DMG, and runs the distribution job for version tags. Remote execution requires a GitHub repository with Actions enabled.

## Repository setup

Protect the default branch and the release environment. Limit release credentials to trusted maintainers and approved tags. Keep workflow changes under review. Third-party Actions are pinned to commits. Verification runs with read-only repository permissions; the release job receives contents write access to publish assets.

Set the release environment secrets:

| Secret | Value |
|---|---|
| PARZR_CERTIFICATE_BASE64 | Base64-encoded Developer ID Application certificate and private key exported as PKCS#12 |
| PARZR_CERTIFICATE_PASSWORD | Export password |
| PARZR_SIGNING_IDENTITY | Full Developer ID Application identity from the signing keychain |
| PARZR_NOTARY_KEY_BASE64 | Base64-encoded App Store Connect notarization API private key |
| PARZR_NOTARY_KEY_ID | API key identifier |
| PARZR_NOTARY_ISSUER | API issuer identifier |

Optional variable PARZR_BUNDLE_ID defaults to app.parzr.desktop. Keep credentials in the CI secret store or local keychain; never in source files, release notes or attachments.

The signing helper imports credentials into an ephemeral keychain, masks its generated password and omits secret command arguments from error logs. Cleanup runs even when a job fails. Fork pull requests never receive release secrets.

## Publishing a version

Update the engine, app plist and both extension versions together. Run all checks and interactive editor acceptance before creating a matching vX.Y.Z tag. The tag triggers verification, Apple Silicon arm64 compilation, hardened-runtime signing, app notarization, DMG signing and notarization, stapling and Gatekeeper checks. Only a successful job publishes the immutable DMG, SHA-256 checksums and licenses. An existing release is not overwritten.

Interactive TextEdit, installed-browser and editor UI checks require a real desktop session and are not established by headless CI alone. Track compatibility evidence in [integrations](integrations.md). Required hosted checks and a protected release environment should enforce the final acceptance gate.

## Local packaging

```sh
python3 scripts/build.py
python3 scripts/package.py
```

These create an ad-hoc signed, unnotarized development app and DMG in dist/. For a distribution build, install a valid Developer ID Application identity in the local keychain and create a notarytool credential profile. Set PARZR_SIGNING_IDENTITY and PARZR_NOTARY_PROFILE in the environment, then run:

```sh
python3 scripts/build.py --sign
python3 scripts/package.py --release
```

Release packaging refuses missing credentials, invalid signing and rejected notarization. Build and notarization reports remain generated artifacts in dist/. Configure credentials before claiming a signed release; automation source alone is not evidence that a hosted release has passed.

## Personal releases from this Mac

Create a Developer ID Application certificate once in Xcode Settings → Accounts → your team → Manage Certificates → +. Xcode installs its private key and certificate in the local keychain. Use an Apple app-specific password or notarization API credentials in the secure interactive setup:

```sh
python3 scripts/release-local.py --setup-notary
python3 scripts/release-local.py --check
python3 scripts/release-local.py
```

The helper detects a single valid Developer ID Application identity, validates the keychain notarization profile, checks public contents and versions, then builds/signs/notarizes/staples/verifies the Apple Silicon DMG. If multiple identities are installed, choose one through PARZR_SIGNING_IDENTITY. Credentials remain in the keychain; no account identity or password is written into source.

The complete runtime dictionary and correction packs are embedded in the engine and shipped in the DMG. Evaluation corpora are development inputs rather than runtime dependencies. The build explicitly copies application code, resources and integrations, so unrelated private files are not packaged.
