# Parzr privacy

Parzr checks your writing on your Mac. It has no account and keeps no writing history. This page covers the few
things that leave your Mac. The same text is on the website at <https://parzr.app/privacy>.

## What leaves your Mac

- **Update check.** Hourly, unless you turn it off: a request to GitHub for the latest release. It carries nothing about
  you or your writing.
- **Model download.** Once, when you set Parzr up: the two models are downloaded from GitHub and checked against pinned
  hashes.
- **Suggestion reports.** On by default; you can turn them off. See below.

## Suggestion reports

Parzr sends a report **only when you click "Report wrong suggestion"** (in a suggestion card's More menu, or Report in
the Review list). Ignoring a suggestion sends nothing, and accepting one sends nothing.

A report holds:

- the suggestion: the words it would change and what it would change them to;
- the text around the suggestion, up to about 240 characters on each side, within its sentence;
- the rule or model that made the suggestion, the app's bundle ID (for example `com.apple.mail`) and Parzr's version.

Before a report is queued, Parzr removes on your Mac the names it recognises, email addresses, phone numbers, other
numbers, links and keys, replacing them with `[name]`, `[email]`, `[phone]`, `[number]`, `[link]` and `[key]`. The
rest of the text around the suggestion is sent as written. Parzr cannot reliably recognise every name (a name that is
also an ordinary word, like "Will" or "Rose", is not caught unless Parzr already knows it as a name), and it cannot
recognise health, financial or other personal details written in ordinary words. A report that mentions a few
health terms is not sent at all, but that is not a guarantee. If a sentence is private, don't report it.

Reports are never sent from apps Parzr excludes (terminals and code editors), apps you turned off, password and other
secure fields, fields Parzr treats as sensitive (sign-in, payment, one-time code and address fields, among others), or
text Parzr could only read by copying.

## Where reports go and how long they are kept

Reports go to `reports.parzr.app`, a Cloudflare Worker with a Cloudflare D1 database. Cloudflare runs that service for
Parzr as its processor. Parzr's maintainer decides what is collected and why: to find and fix wrong suggestions.

- No account, device identifier, IP address or time of day is stored. A stored report keeps only the fields above and
  the day it arrived.
- The rate limit uses a salted hash of your IP address (or of its /64 network for IPv6), held only in Cloudflare's
  rate-limit counter for about a minute, never in the database. Request logs are off.
- Reports are deleted after 180 days.
- Because nothing links a report to you, a report that has been sent cannot be found and deleted on request. Turning
  reports off stops sending at once and deletes any reports on your Mac that have not been sent yet.
- A reported sentence, as redacted, may become a test case in Parzr's open-source repository, so the mistake does not
  come back.

## Turning reports off

Settings, Privacy, "Send anonymous suggestion reports" (also in the welcome guide). Off is immediate.

## Contact

Questions or requests: open an issue at <https://github.com/jn-aman/parzr/issues>. Please don't paste the text you
reported into a public issue.
