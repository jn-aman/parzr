# Parzr privacy

Parzr checks your writing on your Mac. It has no account and keeps no writing history. This page covers the few
things that leave your Mac. The same text is on the website at <https://parzr.app/privacy>.

## What leaves your Mac

- **Update check.** Hourly, unless you turn it off: a request to GitHub for the latest release's signed update feed. It
  carries nothing about you or your writing, and Parzr installs only an update whose signature verifies.
- **Model downloads.** From GitHub, once each: the Smart grammar and rewriting models (727 MB) when you set Parzr up,
  then the Slip check (84 MB) and Tone check (23 MB) models while those checks are on (both are by default). Every file
  is checked against a pinned SHA-256 before use. The downloads carry nothing about you or your writing.
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
also an ordinary word, like "Will" or "Rose", is not caught unless Parzr already knows it as a name, and even then
not when it is written in lowercase), and it cannot recognise health, financial or other personal details written in
ordinary words. A report that mentions a few
health terms is not sent at all, but that is not a guarantee. If a sentence is private, don't report it.

Reports are never sent from apps Parzr excludes (terminals and code editors), apps you turned off, password and other
secure fields, fields Parzr treats as sensitive (sign-in, payment, one-time code and address fields, among others), or
text Parzr could only read by copying.

## Where reports go and how long they are kept

Reports go to `reports.parzr.app`, a Cloudflare Worker with a Cloudflare D1 database. Cloudflare runs that service for
Parzr as its processor. Parzr's maintainer decides what is collected and why: to find and fix wrong suggestions.

- No account, device identifier, IP address or time of day is stored. A stored report keeps only the fields above and
  the day it arrived.
- The rate limit and a daily per-network quota use a salted hash of your IP address (or of its /64 network for IPv6)
  and the day, so it changes every day. The hash is held in Cloudflare's rate-limit counter for about a minute, and in
  the database only next to a count of reports stored that day, never with a report, and deleted within two days.
  Your IP address itself is never stored. Request logs are off.
- Reports are deleted after 180 days.
- Because nothing links a report to you, a report that has been sent cannot be found and deleted on request. Turning
  reports off stops sending at once and deletes any reports on your Mac that have not been sent yet.
- A reported sentence, as redacted, may become a test case in Parzr's open-source repository, so the mistake does not
  come back.

## Turning reports off

Settings, Privacy, "Send anonymous suggestion reports" (also in the welcome guide). Off is immediate.

## What stays on your Mac

Your dictionary, learned names and words, muted suggestions, preferences and, if you keep it, a private weekly summary
of your fixes (Settings, Learning) are saved on this Mac only. Settings, Privacy, "Erase all Parzr data" removes them,
along with any reports not yet sent. Downloaded models stay until you remove them in Settings, Models.

## Contact

Questions or requests: open an issue at <https://github.com/jn-aman/parzr/issues>. Please don't paste the text you
reported into a public issue.
