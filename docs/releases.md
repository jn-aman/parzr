# Releases

The workflow in [.github/workflows/ci-release.yml](../.github/workflows/ci-release.yml) verifies pull requests (except changes that only touch `website/**`, `docs/**` or Markdown), builds a development DMG, and runs the distribution job for version tags. It also runs on demand; a manual run on a branch verifies only. Plain pushes to the default branch do not run it. The [Release workflow](../.github/workflows/release.yml) bumps versions, tags and starts that distribution job. The [website workflow](../.github/workflows/website.yml) deploys `website/` to Cloudflare Workers when it changes on the default branch. Remote execution requires a GitHub repository with Actions enabled.

![How a release ships and the site deploys: the owner-only Release workflow bumps, tags and pushes atomically, ci-release verifies then signs, notarizes and publishes the DMG, the extension files, the update zip, deltas and a signed appcast.xml, re-checks the live feed and drafts the release if it fails, and website.yml deploys parzr.app](media/release.png)

The diagram reads top to bottom; the release job has two rows (sign and package, then the update feed, publish and the post-publish feed check). Only the owner can start a release: `release.yml` runs only for the repository owner on the default branch, and the signing job in `ci-release.yml` runs only for a `v*` tag started by the owner or by `github-actions[bot]`, inside the `release` environment that holds the signing secrets. Pull requests run the `verify` job and nothing else.

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
| SPARKLE_ED_PRIVATE_KEY | Sparkle EdDSA private key (the base64 text `generate_keys -x` writes), used only to sign update files; see [Update signing key](#update-signing-key) |

Optional variable PARZR_BUNDLE_ID defaults to app.parzr.desktop. Keep credentials in the CI secret store or local keychain; never in source files, release notes or attachments.

The signing helper imports credentials into an ephemeral keychain, masks its generated password and omits secret command arguments from error logs. Cleanup runs even when a job fails. Fork pull requests never receive release secrets.

## Publishing a version

A release is one click. The [Release workflow](../.github/workflows/release.yml) does everything a maintainer used to do by hand, then starts the signed build.

From the terminal (GitHub CLI, authenticated for the repository):

```sh
gh workflow run release.yml -f bump=patch
```

Use `-f bump=minor` or `-f bump=major` for larger bumps, or `-f version=X.Y.Z` to set an exact version (it overrides `bump`). Two optional inputs shape the in-app update: `-f critical=true` (see [Critical updates](#critical-updates)) and `-f notes='First point | Second point'` (the short list users see; if empty, the commit subjects since the previous tag are used, so write real notes for anything users should read). From the browser: Actions, Release, Run workflow, pick `bump` (default patch) or type an exact version, then Run workflow. Run it from the default branch.

The workflow runs on a cheap Linux runner with no signing credentials and does the following:

1. Checks out the default branch with full history and tags, and requires a clean working tree.
2. Runs `scripts/bump-version.py`, which computes the next version from `engine/Cargo.toml` and rewrites the version in `engine/Cargo.toml`, the `parzr-engine` entry in `engine/Cargo.lock`, `resources/Info.plist` (CFBundleShortVersionString, and CFBundleVersion as an incrementing build number), `extensions/browser/manifest.json` and `extensions/vscode/package.json`. It refuses to go backwards or reuse an existing tag, and finishes by running `scripts/check-release-version.py`.
3. Commits "Release vX.Y.Z" as the person who started the workflow (no co-author or bot trailers), creates the annotated tag `vX.Y.Z`, and pushes the commit and tag together.
4. Starts [ci-release.yml](../.github/workflows/ci-release.yml) on the new tag with `gh workflow run` (passing `critical` and `notes` through), and links the run in the job summary. Pushes made with the built-in token do not trigger other workflows, but a manual dispatch is allowed, so the build is started explicitly.

On the tag, ci-release.yml verifies, builds the Apple Silicon app, signs and notarizes the app and DMG, staples, runs Gatekeeper checks, then builds and verifies the update feed (below), and only then publishes the DMG, SHA-256 checksums, licenses, update zip, deltas, `appcast.xml` and the optional extension files as one release. The extension files come from `scripts/package-extensions.py` (the same script runs on every pull request, so a packaging break shows before a tag): `parzr-vscode-X.Y.Z.vsix` is built with the pinned `@vscode/vsce` 4.0.0 on Node 22, and `parzr-browser-extension-X.Y.Z.zip` is the contents of `extensions/browser` with fixed timestamps. Both versions come from the manifests that `check-release-version.py` already tied to the tag, and both are appended to `SHA256SUMS`. An existing release is not overwritten. Dispatching on a tag makes `github.ref` equal `refs/tags/vX.Y.Z`, so the release job condition and the `release` environment tag rule (`v*`) both apply as they do for a tag push.

Preview a bump locally without writing anything:

```sh
python3 scripts/bump-version.py patch --dry-run
```

Do not run it without `--dry-run` and push by hand unless the workflow is unavailable; if you do, commit all five edited files, create the matching annotated tag and push it.

If the signed build fails after the tag is pushed, fix the problem on the default branch and release the next version. Delete a failed tag only if no release was published for it.

If the default branch is protected against direct pushes, allow the GitHub Actions app to bypass that rule for this workflow; otherwise the push step fails and nothing is released (the push is atomic, so no tag is left behind).

Interactive TextEdit, installed-browser and editor UI checks require a real desktop session and are not established by headless CI alone. Track compatibility evidence in [integrations](integrations.md). Required hosted checks and a protected release environment should enforce the final acceptance gate.

## Automatic updates

From 0.3 the app updates itself with Sparkle 2.9.5. Installs of 0.2.x have no updater, so they install 0.3 by hand once. Its only network request is the update check: a plain GET of the feed from GitHub every 24 hours (`SUScheduledCheckInterval` 86400, started only after the welcome guide is finished), sending nothing about the user or their writing (`SUEnableSystemProfiling` is off; GitHub sees an IP address and the app version, like any download).

**What the user sees.** The defaults are on (`SUEnableAutomaticChecks`, `SUAutomaticallyUpdate`): a new version downloads quietly in the background and installs when the user quits Parzr, or after five minutes without keyboard or mouse use and with no Parzr window or card open (15 seconds for a critical update), after a 10 second countdown that any input cancels (the next attempt waits 30 minutes). A scheduled update panel waits for a 4 second pause in typing so it never lands mid-sentence. Settings, General, Updates has two switches: **Check for updates automatically** and **Download and install automatically** (unavailable while checks are off). With only checking on, Parzr offers the update in its own panel and the user installs it. Every state of that panel has a way out: checking and downloading offer **Hide** (the panel goes, the update carries on) and **Cancel**, preparing and installing offer **Hide** only (Sparkle cannot cancel an extraction), and About and the status popover keep showing the progress line while the panel is hidden. The panel can be dragged by its background and keeps the spot the user chose while it changes state; the next time it appears after being hidden it is back under the menu-bar icon. When a delta cannot be applied to the installed copy (a locally built or modified Parzr with the same build number as a release), Sparkle falls back to the full zip: the panel then reads "Downloading the full update" with the real size and progress, and Cancel works, instead of sitting on "Preparing". The welcome guide has the same check switch, and **Check for Updates** in the menu bar, the status popover and About works at any time. After an update the updater installed (on quit, on restart, or after the countdown), a short "Updated to X" note appears once. It never appears after a manual install (a DMG dragged to Applications): Parzr records the version Sparkle is about to install in the `updateInstalledVersion` default and the next launch shows the note only if it is the running version, then clears the record.

**The feed.** The app's `SUFeedURL` is `https://github.com/jn-aman/parzr/releases/latest/download/appcast.xml`. Every app release carries an `appcast.xml` asset with exactly one item: that release. GitHub resolves `latest` to the newest published, non-draft, non-prerelease release, so the feed is always the newest release's own file, and deleting or drafting a bad release makes the feed fall back to the previous release by itself. No server, no separate publishing step.

**What a release uploads** (one `gh release create`, so the feed never exists without its files):

| Asset | What it is |
|---|---|
| `Parzr-X.Y.Z.dmg`, `SHA256SUMS`, licenses | The download for new installs, unchanged. `SHA256SUMS` also lists the two extension files below |
| `parzr-vscode-X.Y.Z.vsix`, `parzr-browser-extension-X.Y.Z.zip` | The optional VS Code and browser extensions, for [manual install](integrations.md#install-the-optional-extensions). Not part of the update feed; their lower-case names keep them out of the `Parzr-*.zip` update globs |
| `Parzr-X.Y.Z.zip` | The update archive: the notarized, stapled `Parzr.app` made with `ditto -c -k --sequesterRsrc --keepParent` |
| `Parzr-X.Y.Z-from-A.B.C.delta` | Binary delta from each of the up to 3 previous releases that have an update zip (small next to the zip, because the bundled models are identical between releases; the 0.2.2 DMG is 731 MB) |
| `appcast.xml` | One item: `sparkle:version` is the build number (CFBundleVersion, which `bump-version.py` increments), `sparkle:shortVersionString` is X.Y.Z, minimum macOS 13.0, arm64 only, the zip and delta enclosures with EdDSA signatures and lengths, the notes, and either `phasedRolloutInterval` or `criticalUpdate` |

**Notes format.** The item's `<description sparkle:format="markdown">` holds a CDATA Markdown bullet list (`- first point`, `- second point`, at most 6 lines of 160 characters). Sparkle exposes it as `itemDescription` with `itemDescriptionFormat == "markdown"`.

**Phased rollout.** Normal releases carry `sparkle:phasedRolloutInterval` 43200 (12 hours): automatic checks open the update to a new seventh of users every 12 hours from the item's publication date, so it spreads over about 3.5 days. A user who clicks Check for Updates gets it at once. This is also the safety net: yank a bad release (below) within the first day and most users never see it.

**What CI verifies.** [scripts/make-appcast.py](../scripts/make-appcast.py) `build` refuses an app that is not stapled and Gatekeeper-approved, lacks `Sparkle.framework`, or whose `SUPublicEDKey` is not the pinned public key. It signs the zip and deltas, writes the appcast, and then re-reads its own output: XML shape (one item, versions, URLs under the release's download path, lengths on disk), every EdDSA signature checked against the public key with a stdlib Ed25519 verifier (independent of Sparkle's tools), the zip extracted and compared with the app, and every delta applied to the previous app and compared with the new app byte for byte. Sparkle's `BinaryDelta` and `sign_update` come from the pinned Sparkle 2.9.5 tarball, checked against its SHA-256 before use. After publishing, `make-appcast.py verify` downloads the live `appcast.xml` and every file it points to, re-verifies lengths and signatures, and checks that `releases/latest/download/appcast.xml` is byte-identical. If that fails, the workflow drafts the release (so the feed falls back) and goes red.

Run the same checks by hand against any published release (no key needed):

```sh
python3 scripts/make-appcast.py verify --appcast https://github.com/jn-aman/parzr/releases/download/vX.Y.Z/appcast.xml
```

The first updater release (0.3.0) has no previous update zips, so it ships without deltas; each later release adds them.

## Critical updates

For a security or data-loss fix, run the release with `critical=true`:

```sh
gh workflow run release.yml -f bump=patch -f critical=true -f notes='Fixes a crash that could lose text | Please update now'
```

The item then carries `<sparkle:criticalUpdate>` instead of a phased rollout: every user sees it on their next check and Sparkle will not let them skip it.

## Yanking a bad release

Do this as soon as a release is found to be bad, before fixing anything:

```sh
gh release edit vX.Y.Z --draft      # or: gh release delete vX.Y.Z (keeps the tag; add --cleanup-tag to drop it)
```

`releases/latest` then points at the previous release, whose `appcast.xml` offers only that older version. Effects to know:

- Users who have not updated yet stop being offered the bad version immediately. Within the 3.5 day phased window that is most of them.
- Users who already installed it are not downgraded (Sparkle never installs an older build). They need a newer fix: ship the next version with `critical=true` if it is serious. Version numbers only go up; do not reuse the yanked one.
- A draft keeps the assets for inspection; the DMG link on the site and README (`releases/latest`) also falls back to the previous DMG.
- Check the result: `python3 scripts/make-appcast.py verify --appcast https://github.com/jn-aman/parzr/releases/latest/download/appcast.xml` should now report the previous version.

## Update signing key

Sparkle accepts an update only if its EdDSA signature verifies against `SUPublicEDKey` (`j0Fo7VqKBmJXHWEzVHZX0KeGWCPpTng6tW8jmcoEVo0=`, in `resources/Info.plist` and pinned in `scripts/make-appcast.py`). Whoever holds the private key can sign updates for every install, so it is the most sensitive secret in the project after the Developer ID certificate.

Where it lives:

- The owner's login keychain, account `app.parzr.desktop` (item "Private key for signing Sparkle updates").
- The GitHub `release` environment secret `SPARKLE_ED_PRIVATE_KEY`, the base64 text that `generate_keys --account app.parzr.desktop -x FILE` writes. The workflow gives it to `sign_update` on stdin; it is never written to disk or printed, and only the signing step of the release job receives it.
- Back it up in a password manager as a secure note. Export, store, then delete the file:

```sh
generate_keys --account app.parzr.desktop -x /tmp/parzr-ed.key
# copy the contents into the password manager, then
rm -P /tmp/parzr-ed.key
```

Use a throwaway account (for example `--account parzr-update-test`) for any experiment, never `app.parzr.desktop`.

If the key is lost or leaked, rotate it with an update (Sparkle's "Rotating signing keys"): Sparkle accepts a release that changes the EdDSA key as long as it keeps the same Apple Developer ID signing identity (it allows changing the certificate or the EdDSA key in one release, never both).

1. Generate a new key: `generate_keys --account app.parzr.desktop-2`, export it with `-x`, and note the new public key.
2. In one commit set the new `SUPublicEDKey` in `resources/Info.plist` and `PUBLIC_KEY` in `scripts/make-appcast.py`, and replace the `SPARKLE_ED_PRIVATE_KEY` environment secret with the new private key.
3. Release normally. The update zip, deltas and appcast are signed with the new key; existing installs, which still hold the old public key, accept it because the app is signed with the unchanged Developer ID identity, and from then on trust the new key. Do not change the Developer ID certificate in this release.
4. If the app ever enables `SUVerifyUpdateBeforeExtraction`, Sparkle only allows an EdDSA rotation through a Developer ID signed DMG update archive; this repository does not enable it.
5. A leaked key (as opposed to a lost one) also needs the old key treated as hostile: yank releases signed after the leak, and rotate before the attacker can also control the feed (the feed is only the owner's GitHub releases, so the attacker needs that too). Once everyone has updated past the rotation, delete the old key from the keychain and password manager.

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
