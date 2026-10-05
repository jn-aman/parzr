# Parzr website

Static marketing site for parzr.app. No build step, no dependencies, no third-party requests.

```
public/
  index.html      single page (hero, try it, how it works, names, privacy, bento, real app, compatibility, open source, finale)
  styles.css      tokens from mac/Sources/Parzr/Design.swift
  main.js         vanilla motion engine (requestAnimationFrame, IntersectionObserver, CSS custom properties)
  404.html        not found page
  _headers        CSP and cache policy (Cloudflare static assets)
  assets/         WebP renders of the real app, favicon.svg, og-image.png
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
