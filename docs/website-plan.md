# Parzr.app — after product acceptance

The target domain is parzr.app, managed through Cloudflare. Build and deploy the website only after the desktop product passes its release gates.

The site should make parzr understandable in one screen: a real macOS capture showing selected text, a compact correction panel, and formatting surviving Apply. An authored interactive demo can switch among five modes using a shipped, synthetic fixture. Keep the copy grounded in measured offline behavior; label the demo and its limitations.

Pages: home/download, how it works, verified editor compatibility, installation and permissions, browser/editor integrations, privacy, grammar coverage/contributing rules, releases/changelog, and open-source development. Provide keyboard navigation, reduced motion, responsive layouts, accessible contrast, real download sizes/checksums, and release/signature status. Use actual product imagery and carefully timed motion; no invented testimonials or universal grammar claims.

Prefer a static site built to Cloudflare Pages (or Workers static assets if Pages deployment constraints make it a better fit). A small Worker can serve a cached release manifest fetched from GitHub, with a fixed upstream allowlist and no user text. Downloads should link to immutable signed GitHub release assets and their SHA-256 checksums. Keep desktop runtime wholly independent of the site.

CI: website PR preview deployments and accessibility/performance checks; production deployment after a tagged, verified desktop release updates the manifest. Cloudflare API token stored in CI with only project deployment permissions. Bind parzr.app and www redirect; HTTPS, cache policy, CSP, and no analytics by default.

Prerequisites: approved desktop screenshots, verified signed/notarized release, public repository URL, evidence-backed compatibility table, and release notes. Website design and deployment are deliberately pending the product gate.
