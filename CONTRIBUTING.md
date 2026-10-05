# Contributing

Parzr is Apache-2.0. Keep contributions focused and include enough evidence to review behavior and safety.

For a grammar rule, include its source/provenance, an error fixture, valid counterexamples, expected corrections and intent-preservation checks. Add independent corpus cases where practical. Do not copy licensed rules or data without preserving attribution. Keep grammar/spelling/punctuation active in all modes.

For an editor adapter, prove source/version revalidation, UTF-16 boundaries, formatting retention, Undo, protected content and secure-field exclusion using synthetic documents. Clearly label unverified hosts.

Run the checks in [README](README.md) and the [public-content audit](scripts/audit-public-repo.py). Keep credentials, personal data, local screenshots of real documents, generated reports, editor settings and private planning inputs out of patches. Public screenshots must show synthetic product fixtures. Generated packages and reports belong in dist/.

Use the existing native Graphite components, keyboard conventions and reduced-motion behavior. Explain the problem, resulting behavior and relevant verification in the pull request. Include a current synthetic screenshot when a visual change needs review.
