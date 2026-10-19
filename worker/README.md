# Parzr suggestion reports

A Cloudflare Worker and D1 database that receive Parzr's anonymous wrong-suggestion reports, and a script that
turns a week of them into the fix queue. What is sent and kept, for writers: [docs/privacy.md](../docs/privacy.md)
(also https://parzr.app/privacy).

```
src/index.ts                 POST /v1/reports, GET|HEAD /v1/health, GET|HEAD / (plain-text note), daily clean-up
src/validate.ts              strict schema, size limits, server-side privacy check
src/fixqueue.ts              grouping and ranking for the weekly fix queue
scripts/export-fix-queue.ts  D1 -> dist/fix-queue/<week>.jsonl and .md
migrations/                  D1 schema, additive only (see "Migrations")
wrangler.toml                bindings, limits, cron, vars
test/                        node --test, no network or Cloudflare account needed
test-d1/                     vitest in workerd against a real local D1 (vitest.config.ts)
```

## What a report holds

The app (mac/Sources/ParzrCore/Reports.swift) sends a report only when the writer clicks "Report wrong suggestion"
(a card's More menu, or Report in the Review list). Ignoring a suggestion sends nothing, accepted suggestions are
never sent, and nothing is sent from apps on the exclusion list, from fields the host rules or sensitive-field
keywords block, from secure fields, or when the text was read by copying. The Worker accepts only
`"action": "reported"`; `dismissed` (sent by app versions before 2026-10-19) and `accepted` are refused, and a D1
trigger refuses them too.

```json
{"reports": [{
  "sentence": "Thanks [name], I has [number] questions about [link].",
  "suggestion": {"start": 17, "end": 20, "original": "has", "replacement": "have"},
  "rule": "grammar.i_agreement",
  "model": "rules",
  "action": "reported",
  "app": "com.tinyspeck.slackmacgap",
  "version": "0.5.0"
}]}
```

- `sentence` is the text around the suggestion: its sentence, cut to at most about 240 characters on each side of
  the suggestion (at a space, so no word is cut in half). It, `original` and `replacement` are redacted on the Mac
  before they are queued (mac/Sources/ParzrCore/Redaction.swift): names Parzr recognises (the writer's own, learned
  and Contacts names, names in the document, names macOS knows, Apple's tagger, capitalized words mid-sentence,
  words after a greeting, words the English lexicon does not know, @handles and #hashtags), email addresses
  (including "name at host dot com"), links, phone numbers, every other number (digits and three or more number
  words in a row), and keys and tokens become `[name]`, `[email]`, `[link]`, `[phone]`, `[number]`, `[key]`. A
  suggestion that touches a redacted span is redacted on both sides. A report that still mentions a few health terms
  is not sent. Health and other sensitive content in ordinary words cannot be detected reliably, and the rest of the
  text is sent as written.
- `model` is `rules`, `gector`, or `qwen` (`qwen:<tone>` for a tone rewrite). `start`/`end` are UTF-16 offsets.
- The request carries an `Idempotency-Key` header: a random UUID per batch, reused for that batch's retries, kept 14
  days so a retry is stored once. The app drops reports it has held for 14 days.

The Worker accepts exactly these keys (anything extra drops the report), checks the limits in `src/validate.ts`
(well-formed UTF-16, no control, bidirectional or invisible format characters, offsets on character boundaries), and
refuses any report that still contains a digit, an email address (also spelled out), a domain or link, an `@handle` or
`#hashtag`, a key-like string, or three number words in a row (case-insensitive). A stored row adds only
`received_day` (the UTC date). The Worker never stores or logs the IP address or any other header. A salted hash of
the IPv4 address or IPv6 /64 and the UTC day (the salt is a secret, and the day makes the hash change daily) keys
Cloudflare's rate-limit counter and the per-client row count in `client_counts`, which holds only the day, that hash
and a number, is never joined to a report, and is deleted the day after next. Workers observability is off. Rows are deleted after `RETENTION_DAYS` (180). Cloudflare runs the Worker and database as
Parzr's processor. Rows hold nothing that links them to a person, so a single sent report cannot be found and
deleted on request.

## Limits

- 4 requests a minute per client (IPv4 address or IPv6 /64), at most 25 reports and 64 KB a request.
- `CLIENT_DAILY_ROW_CAP` (200) report rows a UTC day per client (IPv4 address or IPv6 /64, by its salted daily hash):
  a `client_counts` row is raised in the same D1 transaction as the reports, and its `CHECK (rows <= cap)` rolls back
  a batch that would pass the quota. Past it that client alone is answered `429 {"error":"daily quota reached"}` with
  `Retry-After` until midnight UTC; other clients are unaffected.
- `DAILY_ROW_CAP` (100,000) report rows a UTC day across every client, a backstop only distributed traffic (at least
  500 networks at the quota) can reach: a `daily_counts` row is raised in the same transaction, and past it the Worker
  answers `503` with `Retry-After` until midnight UTC.
- `limits.cpu_ms = 50`. Every validation pattern is bounded.
- Without its rate-limit binding or `RATE_LIMIT_SALT` the Worker answers `503` and stores nothing.
- Without a usable `CF-Connecting-IP` (Cloudflare always sets it on the custom domain) the Worker answers `503` when
  it is missing and `400` when it is not an address, rather than pooling such requests into one shared client. Local
  development and tests can set `ALLOW_MISSING_CLIENT_IP=1` (in `.dev.vars` or test bindings, never in `wrangler.toml`).

Responses: `202` stored (`{"stored": n, "dropped": m}`), `200` duplicate batch (decided by reading `batches` again,
not by the error text), `400/413/415` refused for good, `429/503` retry later with `Retry-After`. The app drops a
batch on any 4xx except 408 and 429, retries the rest with exponential backoff (up to 6 hours), refuses redirects,
and keeps at most 500 reports on disk (mode 0600, excluded from backups) while offline.

## Health

`GET /v1/health` (and `HEAD`) answers `{"ok": true, "version": "<deployed version id>", "database": "ok",
"oldest": "<band>", "last_prune_ok": "<UTC day>", "prune": "ok"|"stale"}` after one indexed D1 read, or `503` when
the database cannot be read. `oldest` is a band (`empty`, `under-8-days`, `under-31-days`, `under-91-days`,
`under-181-days`, `over-retention`), never a date. The daily clean-up (cron `17 3 * * *`) deletes old reports, batch
keys and day counters, and per-client counters from before yesterday, and then writes `last_prune_ok` to the `meta` table; it is awaited, so a failure fails the
cron run, and `prune` reads `stale` once it has not succeeded for two days or rows outlive retention.

`GET /` answers a short plain-text note (no scripts, `default-src 'none'`) pointing to the privacy page and the
health check; every other path is `404`.

## Tests

```sh
cd worker
npm ci
npm test            # node --test (Node 22.18+ runs the TypeScript directly)
npm run typecheck   # tsc (src, test, scripts, and test-d1 with the pool's types)
npm run test:d1     # vitest + @cloudflare/vitest-pool-workers: real local D1 from migrations/, in workerd
npm run check       # wrangler deploy --dry-run: bundles and lists bindings, no account needed
```

The D1 tests cover the migrations, CHECK constraints and trigger, duplicate batches (including a retry that races
its first attempt), the per-client quota (one network stopped, another still storing, and the CHECK rolling back a
batch that raced past the pre-check), the daily cap, refusing a request without `CF-Connecting-IP`, the IPv6 /64 rate
limit, retention and health. The pool's workerd is older than
`compatibility_date`, so vitest.config.ts runs them at 2026-08-15.

Local end to end, without an account:

```sh
npx wrangler d1 migrations apply parzr-reports --local
printf 'RATE_LIMIT_SALT=dev\nALLOW_MISSING_CLIENT_IP=1\n' > .dev.vars
npx wrangler dev --local --port 8799
curl -X POST localhost:8799/v1/reports -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: 0f8fad5b-d9cb-469f-a165-70867728950e' \
  -d '{"reports":[{"sentence":"I has [number] dogs.","suggestion":{"start":2,"end":5,"original":"has","replacement":"have"},"rule":"grammar.i_agreement","model":"rules","action":"reported","app":"com.apple.mail","version":"0.5.0"}]}'
npm run fix-queue -- --week 2026-W43 --local
```

## Migrations

Migrations are additive: new tables, columns with defaults, new indexes and triggers, dropping an index nothing
uses. Never rename or drop a column or table, tighten a CHECK, or change what an existing column means. The deploy
applies them before the new code is live and a rollback restores only code, so the version serving at either moment
must work against the new schema. A data-only migration (0003 deletes rows stored for Ignore before 2026-10-19) is
allowed when it is safe for both versions. Before migrating, the deploy writes a D1 Time Travel bookmark to the job
summary; `npx wrangler d1 time-travel restore parzr-reports --bookmark=<bookmark>` returns the database to it.

## Automatic deploys

`.github/workflows/worker.yml` has two jobs. `test` runs on every push and pull request touching `worker/**`, with
no secrets: `npm ci`, unit tests, type-check, D1 tests and the dry-run bundle. `deploy` runs only for main (push or
manual run), after `test`, in the GitHub environment `reports-production`, which holds the secret
`REPORTS_CLOUDFLARE_API_TOKEN` (Workers Scripts edit, D1 edit, Workers Routes edit on parzr.app; nothing else); the
repository variable `CLOUDFLARE_ACCOUNT_ID` names the account. The token is set only on the steps that call
Cloudflare. Missing credentials fail the job. Steps: record the D1 bookmark and the live version, apply migrations,
create `RATE_LIMIT_SALT` once (failing, not recreating, if the secret list cannot be read), `wrangler deploy`, then a
health check that the new version id is the one answering with a working database; if it fails, `wrangler rollback`
returns to the version recorded before the deploy. Live since 2026-10-19: D1 `parzr-reports`
(01da2683-fd5d-4948-8850-05750a027744).

## Deploy (owner) (manual, first time only)

1. `cd worker && npm ci && npx wrangler login` (or export `CLOUDFLARE_API_TOKEN` with Workers Scripts:Edit,
   D1:Edit and Zone:Workers Routes on parzr.app, plus `CLOUDFLARE_ACCOUNT_ID`).
2. `npx wrangler d1 create parzr-reports` and put the printed `database_id` in `wrangler.toml`.
3. Set `namespace_id` under `[[ratelimits]]` to any integer not used by another rate limit in the account.
4. `npx wrangler secret put RATE_LIMIT_SALT` with a long random value (`openssl rand -hex 32`).
5. `npm run migrate` (applies migrations/ to the remote database).
6. `npm run deploy`. This also binds the custom domain `reports.parzr.app` (parzr.app is a zone in the account).
7. `curl https://reports.parzr.app/v1/health` should answer `{"ok":true, ...}`.
8. The app names the endpoint in resources/Info.plist (`ParzrReportsURL`). Builds without that key show no reports
   switch and send nothing.

## Fix-queue format

`npm run fix-queue [-- --week 2026-W42]` (default: the last complete ISO week) writes `dist/fix-queue/<week>.jsonl`
and `<week>.md`. Only `reported` rows count (older `dismissed` rows are skipped). Each JSONL line is one suggestion
(same `rule`, `original` and `replacement`). The score counts distinct sentences per day, at most 3 a day, summed over
the week, so one sentence sent many times, or a burst from one place on one day, cannot top the queue; ties go to
more days, then more distinct sentences.

```json
{"id": "2026-W42-001", "week": "2026-W42", "rule": "grammar.i_agreement", "model": "rules",
 "original": "has", "replacement": "have",
 "counts": {"reported": 9, "sentences": 6, "days": 4}, "score": 6,
 "apps": {"com.apple.mail": 6, "com.tinyspeck.slackmacgap": 3}, "versions": {"0.6.0": 9},
 "examples": [{"text": "I has [number] dogs.", "start": 2, "end": 5, "app": "com.apple.mail", "version": "0.6.0"}],
 "item": {"id": "fq-2026-W42-001", "text": "I has [number] dogs.", "expected": null, "note": "..."}}
```

`examples` holds up to five distinct sentences. `item` is a regression item for scripts/everyday-batch.py: fill in
`expected` (the text Parzr should produce) and add it to a batch. The Markdown file is the same queue as a table for
triage. `app` and `version` are what the client claimed; they are not verified.
