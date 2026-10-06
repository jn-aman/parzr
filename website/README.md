# Parzr website

Static marketing site for parzr.app. No build step, no dependencies. The only third-party request is the self-hosted Rybbit analytics script (see "Analytics events"); the Parzr app sends no writing anywhere (its only network request is the optional daily update check).

```
public/
  index.html      single page (hero, try it, how it works, names, privacy, bento, real app, compatibility, open source, finale)
  styles.css      tokens from mac/Sources/Parzr/Design.swift
  main.js         vanilla motion engine (requestAnimationFrame, IntersectionObserver, CSS custom properties)
  404.html        not found page
  _headers        CSP and cache policy (Cloudflare static assets)
  assets/         WebP renders of the real app, favicon.svg, icon-192.png, icon-512.png, og-image.png
  favicon.ico     16, 32 and 48 px PNGs (the icon services, such as DuckDuckGo's, ask for /favicon.ico)
  apple-touch-icon.png, site.webmanifest   home screen icons and web app manifest
  sitemap.xml, robots.txt                  search engine files
wrangler.jsonc    Cloudflare Workers static assets config
```

## Preview locally

```sh
python3 -m http.server -d website/public 8080   # then open http://localhost:8080
# or, to exercise _headers and the 404 handling the way Cloudflare does:
cd website && npx wrangler dev
```

`python3 -m http.server` does not apply `_headers`, so the CSP is not enforced there. Use `wrangler dev` to check it.

## Deploy

```sh
cd website && npx wrangler deploy
```

This publishes `public/` as Workers static assets and binds the custom domain `parzr.app` (see `wrangler.jsonc`). Deployment needs a Cloudflare account that owns the zone.

## Changing links

Repo and release URLs are one constant at the top of `public/main.js` (`LINKS`). Anchors in `index.html` carry `data-link="repo|release|docs|license"` and the script sets their `href` from that constant. The `href` values in the HTML are only the no-JavaScript fallback, so update both when the repository moves.

## How the motion works

- Pinned scenes (hero, how it works, privacy, finale) are a tall `section` with a `position: sticky` child. `main.js` measures the section against the viewport and writes `--p` (0 to 1) on it. Only that value is eased (a lerp), so the page scrolls natively and keyboard scrolling is untouched. CSS and scene modules read `--p`.
- Issue marks match the app: a solid, rounded, thick underline with a soft tint, red (`--red`) for spelling, grammar and punctuation, blue (`--blue`) for style and tone, deeper on hover. Mint is only for the accepted fix. The kinetic correction (`fxPlay`) underlines in red, strikes the word, scrambles the right one in on a mint wash, then settles.
- The hero editor is a live loop (type, underline, card, Fix sentence) over an aurora of drifting blooms (transform and opacity only), with pointer parallax. The how-it-works window tilts flat as its scene pins; scenes open with a circular iris (`clip-path`).
- "Try it" is a small client-side checker (`RULES` and `NAMES` in `main.js`, a dozen hand-written rules). It never touches the network and it never underlines a word from the name list.
- Backdrop blur is used only on the hero editor, where it sits over the moving aurora. Other windows are opaque gradients to keep scrolling cheap.
- `prefers-reduced-motion: reduce` adds `.rm` to `<html>`: scenes stop pinning, nothing scrubs, every state is shown statically. `(pointer: coarse)` drops pointer parallax, blur, magnetic buttons and the aurora animation.

## Content rules

Claims are limited to what `README.md`, `PRODUCT.md`, `DESIGN.md`, `docs/integrations.md`, `docs/architecture.md` and `benchmarks/README.md` support. The modes demo is labeled as an illustrative example, the try-it panel as a tiny in-page sample, and the name figure carries its benchmark footnote (Measured on Parzr's open name benchmark; synthetic sentences). No testimonials, no invented numbers, no accuracy claims.

## Analytics events

The site loads one script, `https://rybbit.aman.wiki/api/script.js` (self-hosted Rybbit, cookieless), in the `<head>` of `index.html` and `404.html`. `_headers` allows it with `script-src` and `connect-src` for `https://rybbit.aman.wiki`; the script posts to `/api/track` and fetches `/api/site/tracking-config/<siteId>` on that host, and needs nothing under `img-src`. The footer says so in plain words.

Tracking never changes behavior: `track(name, props)` in `main.js` is a no-op when the script is blocked, queues events for about 8 seconds while the script loads (it defines `window.rybbit` only after its config fetch), and swallows errors. Plain links use `data-rybbit-event` and `data-rybbit-prop-*` attributes instead of JS. Event names are plain English, properties are strings or numbers.

| Event | Properties | Fires when |
| --- | --- | --- |
| Download clicked | placement: Nav, Hero, Download section, Footer | a releases/latest link is clicked (data attributes) |
| GitHub opened | placement: Nav, Hero, Open source section, Download section, Footer | a repo link is clicked (data attributes) |
| Docs opened | page: Integrations | the "Read the full evidence table" link is clicked |
| License opened | none | the Apache-2.0 license link in the footer is clicked |
| Release notes opened | none | the footer "Releases" link (/releases, not latest) is clicked |
| Section link clicked | section: Try it, How it works, Names, Privacy, Open source | an in-page link is clicked (nav, footer, "Read the code") |
| Mobile menu opened | none | the nav Menu button opens the menu (not on close) |
| Try it: started typing | none | first input in the demo textarea, once per page load |
| Try it: sample picked | sample: Typos, Style or Names | a sample chip is clicked |
| Try it: suggestion opened | kind: Mistake or Style; word: flagged text, max 40 chars | the user clicks an underlined word (not "Next suggestion") |
| Try it: sentence fixed | none | Fix sentence on the card |
| Try it: word fixed | none | This word on the card |
| Try it: suggestion ignored | none | Ignore on the card |
| Try it: next suggestion | none | Next suggestion button |
| Try it: fix all | count: number of marks fixed | Apply all button |
| Try it: all clear | none | the user's own typing or fixes bring suggestions to 0 (once per page load) |
| Writing mode viewed | mode: Fix, Professional, Friendly, Concise or Direct | a mode chip is clicked (autoplay is not tracked) |
| Code tab picked | tab: grammar.json or lib.rs | a tab in the source excerpt is clicked |
| Build commands copied | none | the Copy button in "Build from source" succeeds |
| Section viewed | section: Hero, Try it, How it works, Names, Privacy, Features, Showcase, Compatibility, Open source, Download, Footer | once per page view, when half of the section (or half of the screen, for tall ones) is visible |
| Page not found | path: location.pathname | the 404 page loads |

Notes for the Rybbit dashboard:

- Rybbit's own autocapture runs next to these events. This site's config has "Track Outbound Links" on, so a click on any GitHub link logs an `outbound` event as well as the named event above. Switch it off in the Rybbit site settings to avoid double counting. Button clicks, copy, form and error capture are off by default and are not needed.
- In-page jumps use `History.prototype.pushState` directly (see `anchors()` in `main.js`) so Rybbit's SPA tracking does not count each section jump as a new pageview.
- To test without sending real data, block the script in DevTools and stub `window.rybbit = {event: (n, p) => console.log(n, p)}`. Local runs otherwise send real pageviews.
