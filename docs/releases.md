# Releases

The workflow in [.github/workflows/ci-release.yml](../.github/workflows/ci-release.yml) verifies pull requests and branch pushes, builds a development DMG, and runs the distribution job for version tags. The [Release workflow](../.github/workflows/release.yml) bumps versions, tags and starts that distribution job. Remote execution requires a GitHub repository with Actions enabled.

## Repository setup

Protect the default branch and the release environment. Limit release credentials to trusted maintainers and approved tags. Keep workflow changes under review. Third-party Actions are pinned to commits. Verification runs with read-only repository permissions; the release job receives contents write access to publish assets. The Release workflow needs contents write (to push the commit and tag) and actions write (to start the build), and holds no signing secrets.

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

A release is one click. The [Release workflow](../.github/workflows/release.yml) does everything a maintainer used to do by hand, then starts the signed build.

From the terminal (GitHub CLI, authenticated for the repository):

```sh
gh workflow run release.yml -f bump=patch
```

Use `-f bump=minor` or `-f bump=major` for larger bumps, or `-f version=X.Y.Z` to set an exact version (it overrides `bump`). From the browser: Actions, Release, Run workflow, pick `bump` (default patch) or type an exact version, then Run workflow. Run it from the default branch.

The workflow runs on a cheap Linux runner with no signing credentials and does the following:

1. Checks out the default branch with full history and tags, and requires a clean working tree.
2. Runs `scripts/bump-version.py`, which computes the next version from `engine/Cargo.toml` and rewrites the version in `engine/Cargo.toml`, the `parzr-engine` entry in `engine/Cargo.lock`, `resources/Info.plist` (CFBundleShortVersionString, and CFBundleVersion as an incrementing build number), `extensions/browser/manifest.json` and `extensions/vscode/package.json`. It refuses to go backwards or reuse an existing tag, and finishes by running `scripts/check-release-version.py`.
3. Commits "Release vX.Y.Z" as the person who started the workflow (no co-author or bot trailers), creates the annotated tag `vX.Y.Z`, and pushes the commit and tag together.
4. Starts [ci-release.yml](../.github/workflows/ci-release.yml) on the new tag with `gh workflow run`, and links the run in the job summary. Pushes made with the built-in token do not trigger other workflows, but a manual dispatch is allowed, so the build is started explicitly.

On the tag, ci-release.yml verifies, builds the Apple Silicon app, signs and notarizes the app and DMG, staples, runs Gatekeeper checks, and only then publishes the immutable DMG, SHA-256 checksums and licenses. An existing release is not overwritten. Dispatching on a tag makes `github.ref` equal `refs/tags/vX.Y.Z`, so the release job condition and the `release` environment tag rule (`v*`) both apply as they do for a tag push.

Preview a bump locally without writing anything:

```sh
python3 scripts/bump-version.py patch --dry-run
```

Do not run it without `--dry-run` and push by hand unless the workflow is unavailable; if you do, commit all five edited files, create the matching annotated tag and push it.

If the signed build fails after the tag is pushed, fix the problem on the default branch and release the next version. Delete a failed tag only if no release was published for it.

If the default branch is protected against direct pushes, allow the GitHub Actions app to bypass that rule for this workflow; otherwise the push step fails and nothing is released (the push is atomic, so no tag is left behind).

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
