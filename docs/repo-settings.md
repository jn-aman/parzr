# Repository settings

The workflows in `.github/workflows` assume the GitHub settings below. Settings are not in the repository, so a
pull request cannot change them; apply them once with the GitHub CLI signed in as the owner (`gh auth status`),
in the order given, and re-run the checks at the end after any change. Every command is idempotent unless noted.

```sh
R=jn-aman/parzr
OWNER_ID=$(gh api user --jq .id)   # the owner's numeric user id (reviewer of the release environments)
```

Current state when this was written (2026-10-19): one branch ruleset (`main: verify must pass`, id 24617377) that
requires `verify` and lets deploy keys and admins bypass it; no tag rulesets; immutable releases off; the `release`
environment (tag `v*`) holds every signing secret, including the Sparkle key, with no reviewer or wait timer;
`release-push` (branch `main`) holds `RELEASE_PUSH_KEY`; `CLOUDFLARE_API_TOKEN` and `REPORTS_CLOUDFLARE_API_TOKEN`
are repository-level secrets; fork pull requests need approval only from first-time contributors; Dependabot
security updates, non-provider secret patterns and CodeQL are off; Actions allows any action without SHA pinning.

## 1. Actions: SHA pinning, read-only token, fork approval

Every `uses:` in this repository is pinned to a full commit SHA; make GitHub refuse anything else, allow only
GitHub's own actions plus the two third-party ones the workflows use, and default `GITHUB_TOKEN` to read-only
(each workflow asks for what it needs).

```sh
gh api -X PUT repos/$R/actions/permissions --input - <<'JSON'
{"enabled": true, "allowed_actions": "selected", "sha_pinning_required": true}
JSON
gh api -X PUT repos/$R/actions/permissions/selected-actions --input - <<'JSON'
{"github_owned_allowed": true, "verified_allowed": false,
 "patterns_allowed": ["dtolnay/rust-toolchain@*", "anchore/sbom-action@*"]}
JSON
gh api -X PUT repos/$R/actions/permissions/workflow --input - <<'JSON'
{"default_workflow_permissions": "read", "can_approve_pull_request_reviews": false}
JSON
# Workflows from every outside contributor's pull request wait for approval (not only first-time contributors).
gh api -X PUT repos/$R/actions/permissions/fork-pr-contributor-approval -f approval_policy=all_external_contributors
```

A new third-party action needs its `owner/repo@*` pattern added to `patterns_allowed` before its first run.

## 2. Branch rulesets for main

Keep the existing ruleset and make the new `dependencies` job a required check too, plus code owner review for
pull requests (`.github/CODEOWNERS`). The Release workflow's deploy key and admins keep their bypass, so the version
bump and the owner's own pushes still land directly (and still run `verify`).

```sh
gh api -X PUT repos/$R/rulesets/24617377 --input - <<'JSON'
{
  "name": "main: verify must pass",
  "target": "branch",
  "enforcement": "active",
  "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
  "bypass_actors": [
    {"actor_type": "DeployKey", "bypass_mode": "always"},
    {"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always"}
  ],
  "rules": [
    {"type": "required_status_checks", "parameters": {
      "strict_required_status_checks_policy": false, "do_not_enforce_on_create": false,
      "required_status_checks": [{"context": "verify", "integration_id": 15368}, {"context": "dependencies", "integration_id": 15368}]}},
    {"type": "pull_request", "parameters": {
      "required_approving_review_count": 0, "require_code_owner_review": true, "dismiss_stale_reviews_on_push": true,
      "require_last_push_approval": false, "required_review_thread_resolution": false, "allowed_merge_methods": ["merge", "squash", "rebase"]}}
  ]
}
JSON
```

With a single maintainer, code owner review binds outside contributors only: the owner (admin bypass) merges
their own pull requests, and so does any agent using the owner's token. The `Flag workflow, release and policy
changes` step of `ci-release.yml` lists such files on every pull request either way.

A second ruleset with **no bypass at all**: nobody (not the owner, not the deploy key) can force-push or delete main.

```sh
gh api -X POST repos/$R/rulesets --input - <<'JSON'
{
  "name": "main: history is permanent",
  "target": "branch",
  "enforcement": "active",
  "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
  "bypass_actors": [],
  "rules": [{"type": "deletion"}, {"type": "non_fast_forward"}]
}
JSON
```

## 3. Tag rulesets

Release tags (`v*`), model pack tags (`models-*`) and the GECToR source tag (`gector-*`) can never be moved or
deleted, by anyone:

```sh
gh api -X POST repos/$R/rulesets --input - <<'JSON'
{
  "name": "tags: release and model tags are permanent",
  "target": "tag",
  "enforcement": "active",
  "conditions": {"ref_name": {"include": ["refs/tags/v*", "refs/tags/models-*", "refs/tags/gector-*"], "exclude": []}},
  "bypass_actors": [],
  "rules": [{"type": "update"}, {"type": "deletion"}, {"type": "non_fast_forward"}]
}
JSON
```

Only the Release workflow's deploy key (`RELEASE_PUSH_KEY`, deploy key 165613668) may create a `v*` tag. Rulesets
can name deploy keys only as a group ("DeployKey"), so keep that key the repository's only write deploy key
(`gh api repos/$R/keys --jq '.[] | select(.read_only == false) | .title'` must list just it).

```sh
gh api -X POST repos/$R/rulesets --input - <<'JSON'
{
  "name": "tags: only the Release workflow creates v*",
  "target": "tag",
  "enforcement": "active",
  "conditions": {"ref_name": {"include": ["refs/tags/v*"], "exclude": []}},
  "bypass_actors": [{"actor_type": "DeployKey", "bypass_mode": "always"}],
  "rules": [{"type": "creation"}]
}
JSON
```

Model pack tags are created by `scripts/model-pack.py publish` (`gh release create models-N`, run by the owner, see
releases.md), so their creation is limited to admins rather than the deploy key. If model packs move to a workflow
that pushes with the deploy key, add `refs/tags/models-*` and `refs/tags/gector-*` to the ruleset above and drop this one.

```sh
gh api -X POST repos/$R/rulesets --input - <<'JSON'
{
  "name": "tags: only the owner creates model tags",
  "target": "tag",
  "enforcement": "active",
  "conditions": {"ref_name": {"include": ["refs/tags/models-*", "refs/tags/gector-*"], "exclude": []}},
  "bypass_actors": [{"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always"}],
  "rules": [{"type": "creation"}]
}
JSON
```

## 4. Immutable releases

A published release's assets and tag can no longer change, so neither a leaked token nor a mistake can swap the DMG,
the update zip or a model file under an existing version. `ci-release.yml` uploads everything to a draft, verifies
the draft, then publishes, which is the order immutable releases need. Existing releases are not affected.

```sh
gh api -X PUT repos/$R/immutable-releases
gh api repos/$R/immutable-releases   # {"enabled":true,...}
```

## 5. Environments

Each environment accepts only its ref and admins cannot skip its protection rules. No existing secret moves:
GitHub cannot copy a secret's value, so the signing secrets stay where they are and the workflow limits who sees them
instead.

**`release`** (all release signing secrets, already there: the Developer ID certificate, the notarization key and
`SPARKLE_ED_PRIVATE_KEY`): tag `v*` only (already set). Two jobs use it, `release-build` and `release-sparkle`, on
separate runners, and each secret is mapped only into the `env` of the one step that uses it: the certificate and
notary secrets into `release-build`'s keychain and signing steps (after every unsigned build and package step), the
Sparkle key into `release-sparkle`'s feed-signing step. `release-build` never references the Sparkle key and
`release-sparkle` never references the Developer ID secrets. Nothing maps a secret at job or workflow level.

Add a wait timer, and optionally the owner as required reviewer. A reviewer approves each job that reaches the
environment, so a release then needs two approvals (`release-build` at the start, `release-sparkle` about 30 minutes
later); leave `reviewers` out to keep releases fully automatic with only the wait timer as a window to cancel.

```sh
# Fully automatic: a 5 minute window to cancel each signing job, no approval.
gh api -X PUT repos/$R/environments/release --input - <<'JSON'
{"wait_timer": 5, "can_admins_bypass": false,
 "deployment_branch_policy": {"protected_branches": false, "custom_branch_policies": true}}
JSON
# Or with the owner's approval of both signing jobs:
gh api -X PUT repos/$R/environments/release --input - <<JSON
{"wait_timer": 5, "prevent_self_review": false, "can_admins_bypass": false,
 "reviewers": [{"type": "User", "id": $OWNER_ID}],
 "deployment_branch_policy": {"protected_branches": false, "custom_branch_policies": true}}
JSON
gh api repos/$R/environments/release/deployment-branch-policies --jq '.branch_policies[] | "\(.type) \(.name)"'   # tag v*
```

```sh
gh api -X PUT repos/$R/environments/release --input - <<JSON
{"wait_timer": 5, "prevent_self_review": false, "can_admins_bypass": false,
 "reviewers": [{"type": "User", "id": $OWNER_ID}],
 "deployment_branch_policy": {"protected_branches": false, "custom_branch_policies": true}}
JSON
gh api repos/$R/environments/release/deployment-branch-policies --jq '.branch_policies[] | "\(.type) \(.name)"'   # tag v*
```

**`release-push`** (`RELEASE_PUSH_KEY`; the Release workflow): branch `main` only (already set); admins cannot bypass.

```sh
gh api -X PUT repos/$R/environments/release-push --input - <<'JSON'
{"wait_timer": 0, "can_admins_bypass": false,
 "deployment_branch_policy": {"protected_branches": false, "custom_branch_policies": true}}
JSON
```

**`website-production`** (new; `CLOUDFLARE_API_TOKEN`; `website.yml`): branch `main` only. The coordinating agent
sets the token in this environment itself (a Cloudflare token with Workers Scripts edit on the account, scoped to the
parzr.app zone); no one re-enters it by hand. Until it is set, `website.yml` skips with a notice. Delete the
repository-level copy once the environment's copy exists.

```sh
gh api -X PUT repos/$R/environments/website-production --input - <<'JSON'
{"wait_timer": 0, "can_admins_bypass": false,
 "deployment_branch_policy": {"protected_branches": false, "custom_branch_policies": true}}
JSON
gh api -X POST repos/$R/environments/website-production/deployment-branch-policies -f name=main -f type=branch
gh secret set CLOUDFLARE_API_TOKEN --env website-production -R $R   # set by the coordinating agent
gh secret delete CLOUDFLARE_API_TOKEN -R $R                         # then drop the repository-level copy
```

**`reports-production`** (new; `REPORTS_CLOUDFLARE_API_TOKEN`; `worker.yml`): branch `main` only. The coordinating
agent sets the token here itself (Workers Scripts edit, D1 edit, Workers Routes and zone read on parzr.app).
`worker.yml`'s deploy job must name `environment: reports-production` (changed on the `reports-hardening` branch); set
the secret before that change merges, and delete the repository-level secret only after it has.

```sh
gh api -X PUT repos/$R/environments/reports-production --input - <<'JSON'
{"wait_timer": 0, "can_admins_bypass": false,
 "deployment_branch_policy": {"protected_branches": false, "custom_branch_policies": true}}
JSON
gh api -X POST repos/$R/environments/reports-production/deployment-branch-policies -f name=main -f type=branch
gh secret set REPORTS_CLOUDFLARE_API_TOKEN --env reports-production -R $R   # set by the coordinating agent
gh secret delete REPORTS_CLOUDFLARE_API_TOKEN -R $R                         # after worker.yml uses the environment
```

`CLOUDFLARE_ACCOUNT_ID` stays a repository variable (not a secret).

## 6. Dependabot, CodeQL and secret scanning

```sh
gh api -X PUT repos/$R/vulnerability-alerts          # Dependabot alerts
gh api -X PUT repos/$R/automated-security-fixes      # Dependabot security updates (version updates: .github/dependabot.yml)
gh api -X PATCH repos/$R/code-scanning/default-setup --input - <<'JSON'
{"state": "configured", "query_suite": "default", "languages": ["actions", "javascript-typescript", "python", "rust"]}
JSON
gh api -X PATCH repos/$R --input - <<'JSON'
{"security_and_analysis": {
  "secret_scanning": {"status": "enabled"},
  "secret_scanning_push_protection": {"status": "enabled"},
  "secret_scanning_non_provider_patterns": {"status": "enabled"},
  "secret_scanning_validity_checks": {"status": "enabled"}}}
JSON
```

Swift is left out of CodeQL default setup: it needs a macOS runner and a build, which default setup's autobuild
does not do for this Swift package.

## Check

```sh
gh api repos/$R/actions/permissions
gh api repos/$R/actions/permissions/fork-pr-contributor-approval
gh api repos/$R/rulesets --jq '.[] | "\(.id) \(.target) \(.enforcement) \(.name)"'
gh api repos/$R/immutable-releases
gh api repos/$R/environments --jq '.environments[] | {name, rules: [.protection_rules[].type], can_admins_bypass}'
for e in release release-push website-production reports-production; do echo "== $e"; gh secret list --env $e -R $R; done
gh secret list -R $R            # no repository-level secrets left
gh api repos/$R --jq .security_and_analysis
gh api repos/$R/code-scanning/default-setup --jq '{state, languages}'
```

Then run the Release workflow once and confirm that the signing jobs wait for the timer (and approval, if set), that
the draft is verified before it is published, and that `website.yml` runs on main after `release-publish`.
