# Parzr suggestion reports

A Cloudflare Worker and D1 database that receive Parzr's anonymous wrong-suggestion reports, and a script that
turns a week of them into the fix queue.

```
src/index.ts                 POST /v1/reports, GET /v1/health, daily retention clean-up
src/validate.ts              strict schema, size limits, server-side privacy check
src/fixqueue.ts              grouping and ranking for the weekly fix queue
scripts/export-fix-queue.ts  D1 -> dist/fix-queue/<week>.jsonl and .md
migrations/0001_reports.sql  D1 schema
wrangler.toml                bindings (placeholders marked REPLACE_...)
test/                        node --test, no network or Cloudflare account needed
```

## What a report holds

The app (mac/Sources/ParzrCore/Reports.swift) sends a report only when the writer turns a suggestion down: Ignore
(`dismissed`) or "Report wrong suggestion" in a card's More menu or the Review list (`reported`). Accepted suggestions
are never sent, and the Worker refuses `"action": "accepted"`.

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

- `sentence`, `original`, `replacement` are redacted on the Mac before they are queued
  (mac/Sources/ParzrCore/Redaction.swift): names (known names, Apple's tagger, capitalized words mid-sentence, @handles),
  email addresses, links, phone numbers and every other number become `[name]`, `[email]`, `[link]`, `[phone]`,
  `[number]`. A suggestion that touches a redacted span is redacted on both sides.
- `model` is `rules`, `gector`, or `qwen` (`qwen:<tone>` for a tone rewrite). `start`/`end` are UTF-16 offsets.
- The request carries an `Idempotency-Key` header: a random UUID per batch, reused for that batch's retries, kept 14
  days so a retry is stored once.

The Worker accepts exactly these keys (anything extra drops the report), checks the limits in `src/validate.ts`, and
refuses any report that still contains a digit, an email address or a link. A stored row adds only `received_day`
(the UTC date). The Worker never stores or logs the IP address or any other header; rate limiting uses a salted,
daily hash of the address that only Cloudflare's rate-limit counter sees. Workers observability is off.
Rows are deleted after `RETENTION_DAYS` (180).

Responses: `202` stored (`{"stored": n, "dropped": m}`), `200` duplicate batch, `400/413/415` refused for good
(the app drops the batch), `429/503` retry later with `Retry-After` (the app backs off exponentially, up to 6 hours,
and keeps at most 500 reports on disk while offline).

## Tests

```sh
cd worker
npm ci
npm test            # node --test (Node 22.18+ runs the TypeScript directly)
npm run typecheck   # tsc
npm run check       # wrangler deploy --dry-run: bundles and lists bindings, no account needed
```

Local end to end, without an account:

```sh
npx wrangler d1 migrations apply parzr-reports --local
npx wrangler dev --local --port 8799
curl -X POST localhost:8799/v1/reports -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: 0f8fad5b-d9cb-469f-a165-70867728950e' \
  -d '{"reports":[{"sentence":"I has [number] dogs.","suggestion":{"start":2,"end":5,"original":"has","replacement":"have"},"rule":"grammar.i_agreement","model":"rules","action":"reported","app":"com.apple.mail","version":"0.5.0"}]}'
npm run fix-queue -- --week 2026-W43 --local
```

## Deploy (owner)

1. `cd worker && npm ci && npx wrangler login` (or export `CLOUDFLARE_API_TOKEN` with Workers Scripts:Edit,
   D1:Edit and Zone:Workers Routes on parzr.app, plus `CLOUDFLARE_ACCOUNT_ID`).
2. `npx wrangler d1 create parzr-reports` and put the printed `database_id` in `wrangler.toml`.
3. Set `namespace_id` under `[[ratelimits]]` to any integer not used by another rate limit in the account.
4. `npx wrangler secret put RATE_LIMIT_SALT` with a long random value (`openssl rand -hex 32`).
5. `npm run migrate` (applies migrations/ to the remote database).
6. `npm run deploy`. It serves on the account's workers.dev address (live: `https://parzr-reports.amanjain.workers.dev`); for a custom domain see the note in wrangler.toml.
7. `curl https://parzr-reports.amanjain.workers.dev/v1/health` should answer `{"ok":true}`.
8. Turn reports on in the app: add `<key>ParzrReportsURL</key><string>https://parzr-reports.amanjain.workers.dev/v1/reports</string>`
   to resources/Info.plist (change it and `routes` here if you use another host), restore the reports wording on the
   website and in README, and release. Builds without that key show no reports switch and send nothing.

## Fix-queue format

`npm run fix-queue [-- --week 2026-W42]` (default: the last complete ISO week) writes `dist/fix-queue/<week>.jsonl`
and `<week>.md`. Each JSONL line is one suggestion (same `rule`, `original` and `replacement`), ranked by
`score = 3 x reported + dismissed` (an explicit "wrong" weighs three Ignores).

```json
{"id": "2026-W42-001", "week": "2026-W42", "rule": "grammar.i_agreement", "model": "rules",
 "original": "has", "replacement": "have",
 "counts": {"reported": 3, "dismissed": 5}, "score": 14,
 "apps": {"com.apple.mail": 6, "com.tinyspeck.slackmacgap": 3}, "versions": {"0.5.0": 9},
 "examples": [{"text": "I has [number] dogs.", "start": 2, "end": 5, "action": "reported", "app": "com.apple.mail", "version": "0.5.0"}],
 "item": {"id": "fq-2026-W42-001", "text": "I has [number] dogs.", "expected": null, "note": "..."}}
```

`examples` holds up to five distinct sentences, reported ones first. `item` is a regression item for
scripts/everyday-batch.py: fill in `expected` (the text Parzr should produce) and add it to a batch. The Markdown file
is the same queue as a table for triage.
