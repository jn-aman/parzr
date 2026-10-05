# Parzr website

Static marketing site for parzr.app. No build step, no dependencies, no third-party requests.

```
public/
  index.html      single page (8 scenes)
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

- Each pinned scene is a tall `section` with a `position: sticky` child. `main.js` measures the section against the viewport while it is on screen and writes `--p` (0 to 1) on it. CSS uses `--p` for parallax; scene modules use it for scrubbed state (demo, modes, showcase, privacy manifesto).
- The kinetic correction (`fxPlay`) draws a dotted underline, strikes the wrong word, scrambles the right one in on a mint wash, then settles.
- Only `transform`, `opacity`, `filter` and `clip-path` are animated, apart from two small one-off exceptions: the sentence tint in the demo and the width of changed words in the modes diff.
- `prefers-reduced-motion: reduce` adds `.rm` to `<html>`: scenes stop pinning, nothing scrubs, every state is shown statically (the modes become a list, the screenshots a grid). `(pointer: coarse)` drops pointer parallax, blur and half the particles.

## Content rules

Claims are limited to what `README.md`, `PRODUCT.md`, `DESIGN.md`, `docs/integrations.md`, `docs/architecture.md` and `benchmarks/README.md` support. The modes demo is labeled as an illustrative example. No testimonials, no invented numbers, no accuracy claims.
