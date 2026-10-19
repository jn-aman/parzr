# Releases

The workflow in [.github/workflows/ci-release.yml](../.github/workflows/ci-release.yml) verifies pull requests and pushes to the default branch (except changes that only touch `website/**`, `docs/**` or Markdown), builds a development DMG, and runs the distribution job for version tags. It also runs on demand; a manual run on a branch verifies only. The [Release workflow](../.github/workflows/release.yml) bumps versions, tags and starts that distribution job. The [website workflow](../.github/workflows/website.yml) deploys `website/` to Cloudflare Workers after each published release, and on demand (see [Website](#website)). Remote execution requires a GitHub repository with Actions enabled. The GitHub settings these workflows rely on (rulesets, environments, immutable releases, Actions policy, Dependabot, CodeQL, secret scanning) are in [repo-settings.md](repo-settings.md).

![How a release ships and the site deploys: the owner-only Release workflow bumps, tags and pushes atomically, ci-release verifies then signs, notarizes and publishes the DMG, the extension files, the update zip, deltas and a signed appcast.xml, re-checks the live feed and drafts the release if it fails, and website.yml deploys parzr.app](media/release.png)

The diagram reads top to bottom (it predates the split of the release job; the steps are the same, now in the four jobs described below). Only the owner can start a release: `release.yml` runs only for the repository owner on the default branch, and the release jobs in `ci-release.yml` run only for a `v*` tag started by the owner or by `github-actions[bot]`, whose commit must already be on `main`. Pull requests and pushes to the default branch run `verify` and `dependencies` and nothing else. A ruleset on the default branch makes both required checks, so a pull request cannot merge while one fails; a pull request that only touches docs, the website or Markdown reports them as skipped, which counts as passed. The owner and the Release workflow's deploy key may push to the default branch directly, and those pushes run the checks too; nobody can force-push or delete it.

The release runs in four jobs, each holding only what it needs:

| Job | Environment and secrets | What it does |
|---|---|---|
| `release-build` | `release`; maps only the Developer ID and notarization secrets, in the keychain and signing steps | Checks the tag's commit is on `main`, builds the engine, the model runtime and the app unsigned and packages both extensions while no credential exists on the runner, then creates the signing keychain, signs (`build.py --sign --skip-build`: no compiler runs), notarizes, staples and deletes the keychain. Hands the DMG, the extensions, `SHA256SUMS` and the stapled app on as an artifact, with every file's SHA-256 as a job output |
| `release-sparkle` | `release`, on its own runner; maps only `SPARKLE_ED_PRIVATE_KEY`, in its feed-signing step | Checks the hand-off against those hashes, builds and signs the update zip, deltas and `appcast.xml`, and hands them on the same way |
| `release-publish` | none; contents, id-token and attestations write | Checks both hand-offs, makes the SBOM and provenance attestations, creates a draft release, downloads it back and verifies it, publishes it, then re-checks the live feed |
| `website` | none; actions write | Starts `website.yml` on `main` |

## Repository setup

[repo-settings.md](repo-settings.md) has the exact commands. In short: rulesets keep `main` and every `v*`, `models-*` and `gector-*` tag permanent (no force-push, move or deletion, with no bypass), only the Release workflow's deploy key creates `v*` tags, releases are immutable once published, every environment accepts only its own ref and admins cannot skip it, Actions must be pinned to commit SHAs, and workflows from outside contributors' pull requests wait for approval. `.github/CODEOWNERS` names the owner for CI, release scripts, the model manifest, the app's identity and entitlements and the Worker, and every pull request that touches those files gets a warning listing them (a pull request runs its own copy of the workflows, so read those changes line by line).

Every job's token is read-only unless it says otherwise: only `release-publish` may write contents (to publish) and mint attestations, and the `website` job and the Release workflow may start workflows (actions write). The Release workflow holds no signing secrets and its token is read-only for contents: it pushes the version commit and tag with `RELEASE_PUSH_KEY`, a write deploy key kept in the `release-push` environment, which only the default branch can use; that key and the owner are the only actors the default branch ruleset lets push without passing checks.

Set the `release` environment secrets. Two jobs use the environment, each on its own runner, and each secret is mapped only into the step that uses it: the first six into `release-build`'s keychain and signing steps, `SPARKLE_ED_PRIVATE_KEY` into `release-sparkle`'s feed-signing step. Nothing maps a secret at job level.

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

The signing helper (`scripts/ci-signing.py`) imports credentials into an ephemeral keychain only after every build and package step has run, lets only `codesign` and `security` use the private key (`-T`, never `-A`), sets the keychain to lock itself after 40 idle minutes, masks its generated password and omits secret command arguments from error logs. The job deletes the keychain as soon as notarization is done, and also when anything fails. Fork pull requests never receive release secrets.

## Publishing a version

A release is one click. The [Release workflow](../.github/workflows/release.yml) does everything a maintainer used to do by hand, then starts the signed build.

From the terminal (GitHub CLI, authenticated for the repository):

```sh
gh workflow run release.yml -f bump=patch
```

Use `-f bump=minor` or `-f bump=major` for larger bumps, or `-f version=X.Y.Z` to set an exact version (it overrides `bump`). Two optional inputs shape the in-app update: `-f critical=true` (see [Critical updates](#critical-updates)) and `-f notes='First point | Second point'` (the short list users see in the app, and the Highlights at the top of the GitHub release; if empty, the app shows the user-facing commit subjects since the previous tag, so write real notes for anything users should read). From the browser: Actions, Release, Run workflow, pick `bump` (default patch) or type an exact version, then Run workflow. Run it from the default branch.

The workflow runs on a cheap Linux runner with no signing credentials and does the following:

1. Checks out the default branch with full history and tags, and requires a clean working tree.
2. Runs `scripts/bump-version.py`, which computes the next version from `engine/Cargo.toml` and rewrites the version in `engine/Cargo.toml`, the `parzr-engine` entry in `engine/Cargo.lock`, `resources/Info.plist` (CFBundleShortVersionString, and CFBundleVersion as an incrementing build number), `extensions/browser/manifest.json` and `extensions/vscode/package.json`. It refuses to go backwards or reuse an existing tag, and finishes by running `scripts/check-release-version.py`.
3. Commits "Release vX.Y.Z" as the person who started the workflow (no co-author or bot trailers), creates the annotated tag `vX.Y.Z`, and pushes the commit and tag together.
4. Starts [ci-release.yml](../.github/workflows/ci-release.yml) on the new tag with `gh workflow run` (passing `critical` and `notes` through), and links the run in the job summary. The version commit carries `[skip ci]`, so the deploy key push starts no workflow of its own and this dispatch is the one signed build.

On the tag, ci-release.yml verifies, builds the Apple Silicon app, signs and notarizes the app and DMG, staples, runs Gatekeeper checks, then builds and verifies the update feed (below). It uploads the DMG, SHA-256 checksums, licenses, update zip, deltas, `appcast.xml`, the optional extension files and an SBOM to a **draft** release, downloads every asset back from GitHub and verifies it (below), and only then publishes. The extension files come from `scripts/package-extensions.py` (the same script runs on every pull request, so a packaging break shows before a tag): `parzr-vscode-X.Y.Z.vsix` is built with `@vscode/vsce` 4.0.0, a pinned devDependency of `extensions/vscode` installed from its committed `package-lock.json` with `npm ci --ignore-scripts` and run from `node_modules/.bin` (never `npx --yes`), and `parzr-browser-extension-X.Y.Z.zip` is the contents of `extensions/browser` with fixed timestamps. Both versions come from the manifests that `check-release-version.py` already tied to the tag (it also checks the version in `extensions/vscode/package-lock.json`, which `bump-version.py` updates), and both are listed in `SHA256SUMS`. The DMG and both extension files are also published under fixed names (`Parzr.dmg`, `parzr-vscode.vsix`, `parzr-browser-extension.zip`, also in `SHA256SUMS`), so `releases/latest/download/<name>` is a direct download of the newest release: the website, README and integration guide link there. After publishing, the job downloads each through `releases/latest` and compares it with the file it uploaded.

**Publishing order and checks.**

1. `gh release create --draft`: the draft is invisible to `releases/latest`, so the update feed and the download links do not move.
2. `gh release download` of the draft into an empty folder, then: the same file names as uploaded; `shasum -a 256 -c SHA256SUMS` (it lists every DMG, extension, update zip, delta, `appcast.xml` and the SBOM); `make-appcast.py verify` on the downloaded `appcast.xml` and files (signatures against the pinned public key, lengths, versions); `xcrun stapler validate` and `spctl -a -t open --context context:primary-signature` on both downloaded DMGs. A failure leaves the draft unpublished and the run red.
3. `gh release edit --draft=false --latest`.
4. The live feed check: `make-appcast.py verify` against the public URL, `releases/latest/download/appcast.xml` byte-identical to the tag's, and each fixed-name download identical to the uploaded file. A failure turns the release back into a draft (or says to delete it, if GitHub refuses) and goes red.

**Provenance and SBOM.** `release-publish` attests every file listed in `SHA256SUMS` with `actions/attest-build-provenance` (Sigstore, tied to the workflow run, the commit and the tag) and attaches `parzr-vX.Y.Z.spdx.json`, an SPDX SBOM of the tagged sources' locked dependencies (`engine/Cargo.lock`, `mac/Package.resolved`, the npm lockfiles; made by syft through `anchore/sbom-action`, both pinned). Check a download with `gh attestation verify Parzr-X.Y.Z.dmg --repo jn-aman/parzr`.

**A draft left behind** (the draft check failed): read the run's log, then delete the draft (`gh release delete vX.Y.Z --yes`; the tag stays) and release the next version once fixed. A draft never reaches users.

**Release notes.** `scripts/release_notes.py` writes the release body (also shown in the run's summary): the `notes` input as Highlights, then What's new from the commit subjects since the previous tag, with subjects whose area is internal (CI, Tests, Self tests, Docs, README, Website and similar; `INTERNAL` in the script) folded into a collapsed Under the hood list, then a download table with sizes and requirements, install and update steps, the checksums and the compare link. Write subjects as `Area: what changed for the user`; the area becomes the bold label. Subjects are rendered as plain text (`plain()` in the script): links keep only their text, URLs, HTML tags, `@` mentions and Markdown markup are removed, so a commit message cannot put a link, image or formatting into the release page or the update panel. `make-appcast.py` uses the same test and the same cleaning, so the in-app notes skip internal commits too. Preview with `python3 scripts/release_notes.py --version X.Y.Z --git-range vA.B.C..HEAD`. An existing release is not overwritten. Dispatching on a tag makes `github.ref` equal `refs/tags/vX.Y.Z`, so the release job condition and the `release` environment tag rule (`v*`) both apply as they do for a tag push.

Preview a bump locally without writing anything:

```sh
python3 scripts/bump-version.py patch --dry-run
```

Do not run it without `--dry-run` and push by hand unless the workflow is unavailable; if you do, commit all five edited files, create the matching annotated tag and push it.

If the signed build fails after the tag is pushed, fix the problem on the default branch and release the next version. Delete a failed tag only if no release was published for it.

The default branch ruleset lets the `RELEASE_PUSH_KEY` deploy key push without passing checks, and the tag ruleset lets only that key create `v*` tags ([repo-settings.md](repo-settings.md)); without those bypasses the push step fails and nothing is released (the push is atomic, so no tag is left behind). The version commit is not signed: it is made on a GitHub runner and pushed with the deploy key, and the tag is annotated, not signed.

The QA modes exist only in debug builds and QA builds (`python3 scripts/build.py --qa`, see [QA](qa/README.md)); a release build has none of their flags, and `scripts/audit-bundle.py` fails a release bundle whose code carries one. The fixture-editor tests (`--paste-test`, `--typing-test`, `--grammar-typing-test`, `--integration-test`) need Accessibility but show nothing on screen and take no focus; installed-browser and editor UI checks require a real desktop session and are not established by headless CI alone. Track compatibility evidence in [integrations](integrations.md). Required hosted checks and a protected release environment should enforce the final acceptance gate.

## Model packs

The app ships no model weights. It downloads the pack pinned in [`engine/models.json`](../engine/models.json) (name, version, URL, SHA-256, size, license and purpose of every file) on first use; see [architecture](architecture.md#models). The files are assets of a dedicated GitHub release per pack version, `models-1` for the current `essential` pack (Qwen3.5-0.8B Q5_K_M and GECToR, 12 files, 727 MB). That release is a pre-release and never "latest", so `releases/latest` (the update feed and the download links) keeps pointing at the newest app release, and app releases stay small.

**Publish `models-1`** (once, before the first app release built without bundled models: until it exists, that app works with the rules and retries the download every hour). With the GitHub CLI signed in as the owner:

```sh
git switch main && git pull
# Stage the 12 assets in dist/model-pack, each checked against the pinned size and SHA-256.
# Either from an installed Parzr that still bundles the models (0.4.12 or older):
python3 scripts/model-pack.py stage --from-app /Applications/Parzr.app
# or rebuilt from the pinned upstream sources (Qwen3.5 Q8_0 GGUF from Hugging Face, quantized with llama.cpp, and the gector-v1 zip; needs CMake):
python3 scripts/model-pack.py stage --derive
python3 scripts/model-pack.py publish --dry-run     # shows the gh command
python3 scripts/model-pack.py publish               # gh release create models-1 --prerelease --latest=false, with notes listing every file
python3 scripts/model-pack.py fetch --models-dir "$(mktemp -d)" --verify   # downloads it back from GitHub and checks every hash
```

`publish` refuses to touch a tag that exists: a published pack is immutable (immutable releases and the tag ruleset in [repo-settings.md](repo-settings.md) also enforce it on GitHub's side). Besides the model files it attaches `NOTICE-<pack>-<version>.txt` (the `THIRD_PARTY_NOTICES` paragraphs for the pack's models and training data; publishing fails if one is missing) and the full licence texts (`LICENSE-Apache-2.0.txt`, and for `essential` also `LICENSE-Qwen3.5.txt` and `LICENSE-GECToR-Grammarly-Apache-2.0.txt`), and the release notes carry the same attribution. These extra assets are not in `engine/models.json`; the app never downloads them. `PACK_NOTICES` in `scripts/model-pack.py` maps each pack to its paragraphs and licence files: a new pack needs an entry there. Check that `https://github.com/jn-aman/parzr/releases/latest` still shows the app release.

**A new pack version** (Phase 2's fine-tuned Qwen3.5-2B, the slip detector, the tone classifier): put the files in a new pack version in `engine/models.json` (new `version`, URLs under a new tag such as `models-2`, hashes, sizes, licenses, purposes, and `provides` naming what the engine looks up), stage them with `--from-dir`, publish, and only then release the app that pins them. On their first launch, updated apps download the new version beside the old one and delete the old one only after the new one verifies. Never re-upload an asset under an existing tag.

**Publish `models-slips-1`** (the optional slip-check pack, 8 files, 84 MB; before the first app release that pins it). Its Core ML model is compiled by the local toolchain, so the pinned hashes are those of the converted files on the machine that made them: publish exactly those files (`dist/slips-build` on that machine), or convert again and re-pin `engine/models.json` before publishing.

```sh
# Only to rebuild the files (a venv with torch, coremltools 9, safetensors; transformers for the parity check):
venv/bin/python -I scripts/convert-slips.py --download --out dist/slips-build/slips   # then update the slips entries in engine/models.json
python3 scripts/model-pack.py stage --pack slips --from-dir dist/slips-build      # checks every pinned size and SHA-256
python3 scripts/model-pack.py publish --pack slips --dry-run
python3 scripts/model-pack.py publish --pack slips          # gh release create models-slips-1 --prerelease --latest=false
python3 scripts/model-pack.py fetch --pack slips --models-dir "$(mktemp -d)" --verify
```

Until it is published the app reports it as not available yet and retries hourly, with the typing-time slip check off (Option+Space still checks word choice with Qwen), and CI fails: `fetch` (with or without `--derive-fallback`, which rebuilds only the essential pack, and only on pull requests) stops at a pinned pack whose release is missing, so publish the pack before the change that pins it. The Slip check is on by default (Settings, Writing); switched off, the app neither downloads the pack on its own nor lets typing checks use it.

**Publish `models-tone-2`** (the optional tone-check pack, 6 files, 23 MB; before the first app release that pins it). Like the slip pack, its Core ML model is compiled locally, so publish exactly the staged files that match the pins: `dist/tone-pack-v2/release-assets` on the machine that converted it (from `dist/tone-pack-v2/tone-build`), or retrain and convert again and re-pin with `scripts/tone-check/pack_manifest.py`. Version 1 (`models-tone-1`) was never published: it was trained with ParaDetox (OpenRAIL++), and version 2 leaves that corpus out.

```sh
python3 scripts/model-pack.py stage --pack tone --from-dir dist/tone-pack-v2/tone-build --out dist/tone-pack-v2/release-assets   # checks every pinned size and SHA-256
python3 scripts/model-pack.py publish --pack tone --assets dist/tone-pack-v2/release-assets --dry-run
python3 scripts/model-pack.py publish --pack tone --assets dist/tone-pack-v2/release-assets   # gh release create models-tone-2 --prerelease --latest=false
python3 scripts/model-pack.py fetch --pack tone --models-dir "$(mktemp -d)" --verify
```

Tone check is on by default, so publish `models-tone-2` before the app release that pins it. Until it is published, the app reports the tone model as not available yet and retries hourly. No flags appear until then, and nothing else changes.

**CI** downloads the pinned pack into `dist/models` (cached by the hash of `engine/models.json`; `fetch --verify` re-hashes a restored cache against the pinned SHA-256s instead of trusting file sizes, and downloads again on a mismatch) and runs every model test against it through `PARZR_MODELS_DIR`; before the pack's release exists it rebuilds the pack from the pinned upstream sources with the same hash checks. The bundle audit (`scripts/audit-bundle.py`) fails the build if any model file (by name, format or pinned hash) is in the app, or if the app is over 100 MB.

**Check the download end to end** in a QA build (a release build has no `--models-test` and ignores `PARZR_*` variables), without the release:

```sh
python3 scripts/build.py --qa                                               # dist/Parzr-QA.app
python3 scripts/model-pack.py stage --from-app /Applications/Parzr.app      # or --from-dir dist/models/essential/1
PARZR_MODELS_DIR="$(mktemp -d)" PARZR_MODELS_BASE_URL="file://$PWD/dist/model-pack/" dist/Parzr-QA.app/Contents/MacOS/parzr --models-test dist/qa/models
```

It checks with the rules first (and expects "Smart grammar is downloading"), downloads and verifies the pack, then requires a Smart grammar correction while typing and a Qwen tone rewrite on Option+Space, and writes `dist/qa/models/models-test.json`. Leave out `PARZR_MODELS_BASE_URL` to test against the published release.

## Automatic updates

From 0.3 the app updates itself with Sparkle 2.9.6. Installs of 0.2.x have no updater, so they install 0.3 by hand once. Apart from the one-time model download ([Model packs](#model-packs)) and suggestion reports to `reports.parzr.app` while they are on, its only network request is the update check: a plain GET of the feed from GitHub every hour (`SUScheduledCheckInterval` 3600, started only after the welcome guide is finished), sending nothing about the user or their writing (`SUEnableSystemProfiling` is off; GitHub sees an IP address and the app version, like any download).

**What the user sees.** The defaults are on (`SUEnableAutomaticChecks`, `SUAutomaticallyUpdate`): a new version downloads quietly in the background and installs when the user quits Parzr, or after five minutes without keyboard or mouse use and with no Parzr window or card open (15 seconds for a critical update), after a 10 second countdown that any input cancels (the next attempt waits 30 minutes). A scheduled update panel waits for a 4 second pause in typing so it never lands mid-sentence. Settings, General, Updates has two switches: **Check for updates automatically** and **Download and install automatically** (unavailable while checks are off). With only checking on, Parzr offers the update in its own panel and the user installs it. Every state of that panel has a way out: checking and downloading offer **Hide** (the panel goes, the update carries on) and **Cancel**, preparing and installing offer **Hide** only (Sparkle cannot cancel an extraction), and About and the status popover keep showing the progress line while the panel is hidden. The panel can be dragged by its background and keeps the spot the user chose while it changes state; the next time it appears after being hidden it is back under the menu-bar icon. When a delta cannot be applied to the installed copy (a locally built or modified Parzr with the same build number as a release), Sparkle falls back to the full zip: the panel then reads "Downloading the full update" with the real size and progress, and Cancel works, instead of sitting on "Preparing". The welcome guide has the same check switch, and **Check for Updates** in the menu bar, the status popover and About works at any time. After an update the updater installed (on quit, on restart, or after the countdown), a short "Updated to X" note appears once. It never appears after a manual install (a DMG dragged to Applications): Parzr records the version Sparkle is about to install in the `updateInstalledVersion` default and the next launch shows the note only if it is the running version, then clears the record.

**The feed.** The app's `SUFeedURL` is `https://github.com/jn-aman/parzr/releases/latest/download/appcast.xml`. Every app release carries an `appcast.xml` asset with exactly one item: that release. GitHub resolves `latest` to the newest published, non-draft, non-prerelease release, so the feed is always the newest release's own file, and deleting or drafting a bad release makes the feed fall back to the previous release by itself. No server, no separate publishing step.

**What a release uploads** (one draft `gh release create`, verified, then published, so the feed never exists without its files):

| Asset | What it is |
|---|---|
| `Parzr-X.Y.Z.dmg`, `SHA256SUMS`, licenses | The download for new installs, unchanged. `SHA256SUMS` also lists the extension files and fixed-name copies below |
| `Parzr.dmg`, `parzr-vscode.vsix`, `parzr-browser-extension.zip` | Fixed-name copies of the DMG and extensions for direct links through `releases/latest/download/` (website, README, docs) |
| `parzr-vscode-X.Y.Z.vsix`, `parzr-browser-extension-X.Y.Z.zip` | The optional VS Code and browser extensions, for [manual install](integrations.md#install-the-optional-extensions). Not part of the update feed; their lower-case names keep them out of the `Parzr-*.zip` update globs |
| `Parzr-X.Y.Z.zip` | The update archive: the notarized, stapled `Parzr.app` made with `ditto -c -k --sequesterRsrc --keepParent` |
| `Parzr-X.Y.Z-from-A.B.C.delta` | Binary delta from each of the up to 8 previous releases that have an update zip (small next to the zip; since the models moved out of the app, the app itself is about 80 MB instead of 773 MB, and the first release without them deltas to a removal) |
| `parzr-vX.Y.Z.spdx.json` | SPDX SBOM of the tagged sources' locked dependencies; every file in `SHA256SUMS` also has a provenance attestation (`gh attestation verify FILE --repo jn-aman/parzr`) |
| `appcast.xml` | One item: `sparkle:version` is the build number (CFBundleVersion, which `bump-version.py` increments), `sparkle:shortVersionString` is X.Y.Z, minimum macOS 13.0, arm64 only, the zip and delta enclosures with EdDSA signatures and lengths, the notes, and either `phasedRolloutInterval` or `criticalUpdate` |

**Notes format.** The item's `<description sparkle:format="markdown">` holds a CDATA Markdown bullet list (`- first point`, `- second point`, at most 6 lines of 160 characters). Sparkle exposes it as `itemDescription` with `itemDescriptionFormat == "markdown"`.

**Phased rollout.** Normal releases carry `sparkle:phasedRolloutInterval` 43200 (12 hours): automatic checks open the update to a new seventh of users every 12 hours from the item's publication date, so it spreads over about 3.5 days. A user who clicks Check for Updates gets it at once. This is also the safety net: yank a bad release (below) within the first day and most users never see it.

**What CI verifies.** [scripts/make-appcast.py](../scripts/make-appcast.py) `build` refuses an app that is not stapled and Gatekeeper-approved, lacks `Sparkle.framework`, or whose `SUPublicEDKey` is not the pinned public key. It signs the zip and deltas, writes the appcast, signs the feed itself with `sign_update` (the signature is a trailing comment over the file's bytes; the app sets `SURequireSignedFeed` and `SUVerifyUpdateBeforeExtraction`, so an unsigned or altered feed is refused), and then re-reads its own output: the feed signature, XML shape (one item, versions, URLs under the release's download path, lengths on disk), every EdDSA signature checked against the public key with a stdlib Ed25519 verifier (independent of Sparkle's tools), the zip extracted and compared with the app, and every delta applied to the previous app and compared with the new app byte for byte. Sparkle's `BinaryDelta` and `sign_update` come from the pinned Sparkle 2.9.6 tarball: on every run the tarball (downloaded once per runner) is re-hashed against its pinned SHA-256 and the two tools are extracted from those exact bytes into a fresh private folder, so the tool the private key is piped to is never a cached copy. This runs in `release-sparkle`, the only job that maps the key, which receives the notarized app from `release-build` and checks it against that job's hashes first. Before publishing, `make-appcast.py verify` checks the draft's downloaded `appcast.xml` and files; after publishing, it downloads the live `appcast.xml` and every file it points to, re-verifies the feed signature, lengths and signatures, and checks that `releases/latest/download/appcast.xml` is byte-identical. If that fails, the workflow drafts the release (so the feed falls back) and goes red.

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
gh release edit vX.Y.Z --draft=true   # if GitHub refuses (immutable release): gh release delete vX.Y.Z --yes
```

With immutable releases on, a published release's assets and tag cannot change, and the tag ruleset blocks moving or deleting `v*` tags: `gh release delete` removes the release but keeps the tag (never pass `--cleanup-tag`), and that version number is spent. Either way `releases/latest` falls back.

`releases/latest` then points at the previous release, whose `appcast.xml` offers only that older version. Effects to know:

- Users who have not updated yet stop being offered the bad version immediately. Within the 3.5 day phased window that is most of them.
- Users who already installed it are not downgraded (Sparkle never installs an older build). They need a newer fix: ship the next version with `critical=true` if it is serious. Version numbers only go up; do not reuse the yanked one.
- A draft keeps the assets for inspection; the download links on the site and README (`releases/latest/download/Parzr.dmg` and the extension files) also fall back to the previous release's files.
- Check the result: `python3 scripts/make-appcast.py verify --appcast https://github.com/jn-aman/parzr/releases/latest/download/appcast.xml` should now report the previous version.

## Update signing key

Sparkle accepts an update only if its EdDSA signature verifies against `SUPublicEDKey` (`j0Fo7VqKBmJXHWEzVHZX0KeGWCPpTng6tW8jmcoEVo0=`, in `resources/Info.plist` and pinned in `scripts/make-appcast.py`). Whoever holds the private key can sign updates for every install, so it is the most sensitive secret in the project after the Developer ID certificate.

Where it lives:

- The owner's login keychain, account `app.parzr.desktop` (item "Private key for signing Sparkle updates").
- The GitHub `release` environment secret `SPARKLE_ED_PRIVATE_KEY`, the base64 text that `generate_keys --account app.parzr.desktop -x FILE` writes. The environment accepts only `v*` tags, and only the feed-signing step of the `release-sparkle` job maps the key (`release-build`, the other job in the environment, never references it); the workflow gives it to `sign_update` on stdin, and it is never written to disk or printed.
- Back it up in a password manager as a secure note. Export, store, then delete the file:

```sh
generate_keys --account app.parzr.desktop -x /tmp/parzr-ed.key
# copy the contents into the password manager, then
rm -P /tmp/parzr-ed.key
```

Use a throwaway account (for example `--account parzr-update-test`) for any experiment, never `app.parzr.desktop`.

If the key is lost or leaked, rotate it with an update (Sparkle's "Rotating signing keys"): Sparkle accepts a release that changes the EdDSA key as long as it keeps the same Apple Developer ID signing identity (it allows changing the certificate or the EdDSA key in one release, never both).

1. Generate a new key: `generate_keys --account app.parzr.desktop-2`, export it with `-x`, and note the new public key.
2. In one commit set the new `SUPublicEDKey` in `resources/Info.plist` and `PUBLIC_KEY` in `scripts/make-appcast.py`, and replace the `SPARKLE_ED_PRIVATE_KEY` secret of the `release` environment with the new private key.
3. Release normally. The update zip, deltas and appcast are signed with the new key; existing installs, which still hold the old public key, accept it because the app is signed with the unchanged Developer ID identity, and from then on trust the new key. Do not change the Developer ID certificate in this release.
4. If the app ever enables `SUVerifyUpdateBeforeExtraction`, Sparkle only allows an EdDSA rotation through a Developer ID signed DMG update archive; this repository does not enable it.
5. A leaked key (as opposed to a lost one) also needs the old key treated as hostile: yank releases signed after the leak, and rotate before the attacker can also control the feed (the feed is only the owner's GitHub releases, so the attacker needs that too). Once everyone has updated past the rotation, delete the old key from the keychain and password manager.

## Website

`website.yml` deploys `website/` (Cloudflare Workers static assets) with wrangler pinned in `website/package.json` and locked in `website/package-lock.json`, installed with `npm ci --ignore-scripts`; only the deploy step sees `CLOUDFLARE_API_TOKEN`, a secret of the `website-production` environment, which only `main` can deploy to. It has no push trigger:

- After a release, the `website` job of `ci-release.yml` starts it on `main` once `release-publish` has published and verified the release, so the site's download buttons (`releases/latest/download/...`) never point ahead of the release.
- For website-only changes between releases, merge them to `main` and start it by hand: Actions, Deploy parzr.app, Run workflow (branch `main`), or `gh workflow run website.yml --ref main`.

## Dependency checks

The `dependencies` job (pull requests and `main`; a required check) fails on:

- a pull request that adds a dependency with a high or critical advisory (`actions/dependency-review-action`);
- any vulnerable, unsound, yanked or unmaintained crate, a licence outside the allowlist, a banned crate (network or TLS stacks) or a crate from outside crates.io in the engine's shipped graphs, the default one and the app's (`--features external-tables`): `cargo deny` with [engine/deny.toml](../engine/deny.toml);
- a vulnerable, unsound or yanked crate in those graphs per `cargo audit` ([scripts/cargo-audit-shipped.py](../scripts/cargo-audit-shipped.py) filters cargo-audit's lockfile-wide report to the crates `cargo tree` lists for them, and prints the rest as notes);
- a high or critical npm advisory in the runtime dependencies of the repository root and `worker/` (`npm audit --omit=dev --audit-level=high`), and in the full trees of `website/` and `extensions/vscode/`, whose dev dependencies are the deploy and packaging tools that run with secrets or produce release files.

The maintainer-only `baseline-harper` feature (harper-core and about 500 crates behind the `parzr-export-lexicon` tool that regenerates engine data) never ships and is checked by neither tool; on 2026-10-19 its graph carried advisories for ammonia, bincode, lru, paste, rustls and zip. Run that tool only on a trusted machine. Dependabot (`.github/dependabot.yml`) proposes weekly updates for Actions, Cargo, npm (root, `worker/`, `extensions/vscode/`, `website/`) and Swift, minor and patch grouped, each waiting out a 14-day cooldown after the upstream release; security updates skip the cooldown and come as soon as an advisory is published. `python3 scripts/audit-public-repo.py` (run by `verify`) also looks for Cloudflare, AWS, Slack, Hugging Face, npm and GitHub tokens and `.dev.vars` files; `--history` scans every commit on every ref (`git log -p --all`), worth running before publishing a branch with old experiments.

## Toolchains

| Tool | Pinned in | Version |
|---|---|---|
| Rust | `rust-toolchain.toml` and `dtolnay/rust-toolchain` (`toolchain: '1.91.0'`) in `ci-release.yml` | 1.91.0 |
| Node | `NODE_VERSION` in `ci-release.yml`, `node-version` in `website.yml` | 22.23.3 |
| Xcode | `XCODE_DEVELOPER_DIR` in `ci-release.yml` (exported as `DEVELOPER_DIR`; the job fails if the runner image lacks it) | 26.6 on `macos-26` |
| Sparkle tools | `SPARKLE_VERSION`/`SPARKLE_SHA256` in `scripts/make-appcast.py` | 2.9.6 |
| @vscode/vsce, wrangler | `extensions/vscode/package-lock.json`, `website/package-lock.json` | 4.0.0, 4.149.0 |

Bump a pin in all of its places in one pull request. When GitHub drops Xcode 26.6 from the `macos-26` image, the macOS jobs fail at "Pin Xcode" with the path to update (list the installed ones in a run with `ls /Applications | grep Xcode`). The macOS jobs set `SOURCE_DATE_EPOCH` to the commit time for tools that honour it; the browser extension zip uses fixed timestamps already.

## Local packaging

```sh
python3 scripts/build.py
python3 scripts/package.py
```

These create an ad-hoc signed, unnotarized development app and DMG in dist/. The app is a release build: no QA modes, no `PARZR_*` overrides (its engine is built without the `dev-overrides` feature). `python3 scripts/build.py --qa` builds `dist/Parzr-QA.app` with both, for local end-to-end runs; it is never signed for release and `scripts/package.py` never packages it. For a distribution build, install a valid Developer ID Application identity in the local keychain and create a notarytool credential profile. Set PARZR_SIGNING_IDENTITY and PARZR_NOTARY_PROFILE in the environment, then run:

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
