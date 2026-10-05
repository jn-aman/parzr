/* Parzr site: a small vanilla motion engine. No dependencies, no network requests. */
(() => {
'use strict';

// All repo and release URLs live here. Change them once, the whole page follows.
const LINKS = {
  repo: 'https://github.com/jn-aman/parzr',
  release: 'https://github.com/jn-aman/parzr/releases/latest',
};
LINKS.docs = LINKS.repo + '/blob/main/docs/integrations.md';
LINKS.license = LINKS.repo + '/blob/main/LICENSE';

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
const smooth = (a, b, v) => { const t = clamp((v - a) / (b - a)); return t * t * (3 - 2 * t); };
const lerp = (a, b, t) => a + (b - a) * t;
const sleep = ms => new Promise(r => setTimeout(r, ms));
const root = document.documentElement;
const RM = matchMedia('(prefers-reduced-motion: reduce)').matches;
const COARSE = matchMedia('(pointer: coarse)').matches;
root.classList.add('js');
if (RM) root.classList.add('rm');
if (COARSE) root.classList.add('coarse');
matchMedia('(prefers-reduced-motion: reduce)').addEventListener('change', () => location.reload());

$$('[data-link]').forEach(a => { if (LINKS[a.dataset.link]) a.href = LINKS[a.dataset.link]; });

function rng(seed) { // mulberry32, so the fragment layout is identical on every load
  return () => { seed |= 0; seed = seed + 0x6D2B79F5 | 0; let t = Math.imul(seed ^ seed >>> 15, 1 | seed); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };
}

/* ---------- Kinetic correction: underline, strike, scramble, mint wash, settle ---------- */
const UP = 'ABCDEFGHJKLMNPQRSTUVWXYZ', LOW = 'abcdefghjkmnpqrstuvwxyz';
function scramble(node, final, dur, onEnd) {
  if (node._stop) node._stop();
  const start = performance.now(), L = final.length;
  let raf = 0, last = 0, dead = false;
  node._stop = () => { dead = true; cancelAnimationFrame(raf); };
  const tick = now => {
    if (dead) return;
    const t = clamp((now - start) / dur);
    if (now - last > 36 || t === 1) {
      last = now;
      const lock = Math.floor(t * L);
      let s = '';
      for (let i = 0; i < L; i++) {
        const c = final[i];
        if (i < lock || !/[A-Za-z]/.test(c)) s += c;
        else { const set = c === c.toUpperCase() ? UP : LOW; s += set[Math.floor(Math.random() * set.length)]; }
      }
      node.textContent = s;
    }
    if (t < 1) raf = requestAnimationFrame(tick); else { node.textContent = final; node._stop = null; onEnd && onEnd(); }
  };
  raf = requestAnimationFrame(tick);
}

function fxInit(el) {
  if (el._fx) return;
  const right = el.textContent, wrong = el.dataset.wrong;
  el.textContent = '';
  if (el.hasAttribute('data-fixed')) {
    const s = document.createElement('span');
    s.className = 'fx-s'; s.setAttribute('aria-hidden', 'true');
    s.textContent = right.length >= wrong.length ? right : wrong;
    el.append(s);
  }
  const t = document.createElement('span');
  t.className = 'fx-t'; t.textContent = right;
  el.append(t);
  el._fx = { t, wrong, right, tok: 0 };
}
function fxSet(el, state, underline) {
  const f = el._fx; f.tok++;
  if (f.t._stop) f.t._stop();
  f.t.textContent = state === 'wrong' ? f.wrong : f.right;
  el.classList.remove('strike', 'wash', 'done', 'ok');
  el.classList.toggle('u', state === 'wrong' && !!underline);
  if (state === 'right') el.classList.add('ok');
}
async function fxPlay(el, o = {}) {
  const f = el._fx, tok = ++f.tok, live = () => f.tok === tok;
  const { strike = true, hold = 520, dur = 560, settle = false } = o;
  if (f.t._stop) f.t._stop();
  f.t.textContent = f.wrong;
  el.classList.remove('done', 'ok', 'strike', 'wash');
  el.classList.add('u');
  if (strike) {
    await sleep(hold); if (!live()) return;
    el.classList.add('strike');
    await sleep(340); if (!live()) return;
  }
  el.classList.remove('strike');
  el.classList.add('wash', 'done');
  scramble(f.t, f.right, dur);
  await sleep(dur + 40); if (!live()) return;
  el.classList.add('ok');
  await sleep(300); if (!live()) return;
  el.classList.remove('wash');
  if (settle) { await sleep(1000); if (live()) el.classList.remove('done'); }
}

/* ---------- Floating struck fragments: quiet, in the gutters, never on text ---------- */
const PAIRS = [['teh', 'the'], ['recieved', 'received'], ['definately', 'definitely'], ['alot', 'a lot'], ['seperate', 'separate'], ['mesage', 'message'], ['chek', 'check'], ['wich', 'which'], ['thier', 'their'], ['untill', 'until'], ['occured', 'occurred'], ['becuase', 'because'], ['freind', 'friend'], ['wierd', 'weird'], ['goverment', 'government'], ['tommorow', 'tomorrow']];
const BITS = ['teh', 'e', 'ing', 'ed', 'th', 'ie', 'ei', 'ss', 'wich', 'tion', 'ae', 'ph', 'alot', 'nd'];
const SMALL = () => innerWidth < 761;
// Text is measured tightly (per line box); visual boxes are measured whole.
const TEXT_SEL = 'h1,h2,h3,p,li,dt,dd,summary,pre,figcaption,.eyebrow,.step,.rowlab span';
const BOX_SEL = '.btn,.chip,.mchip,.card,.win,.mstage,.tile,.code,.shot,.gdocs,.build-box,.marquee,.scroll-cue';
function obstacles(host, pad) {
  const scope = host.closest('.pin') || host.parentElement, H = host.getBoundingClientRect(), out = [];
  const add = (r, p) => { if (r.width > 1 && r.height > 1) out.push({ l: r.left - H.left - p, t: r.top - H.top - p, r: r.right - H.left + p, b: r.bottom - H.top + p }); };
  scope.querySelectorAll(TEXT_SEL).forEach(el => {
    if (el.closest('.layer, .sr-only') || el.classList.contains('sr-only')) return;
    const rg = document.createRange(); rg.selectNodeContents(el);
    Array.from(rg.getClientRects()).forEach(r => add(r, pad));
  });
  scope.querySelectorAll(BOX_SEL).forEach(el => { if (!el.closest('.layer')) add(el.getBoundingClientRect(), pad); });
  const av = host.dataset.avoid; // "x0,x1" in percent of host width, for scenes whose art moves while scrolling
  if (av) { const [x0, x1] = av.split(',').map(Number); out.push({ l: H.width * x0 / 100, t: -1e4, r: H.width * x1 / 100, b: 1e5 }); }
  return out;
}
function frags(host, count, seed, pairs) {
  const r = rng(seed), small = SMALL(), n = Math.min(count, small ? 8 : 18), out = [];
  const sec = host.closest('section'), cv = sec.style.contentVisibility;
  sec.style.contentVisibility = 'visible'; // sections that skip rendering must be laid out to be measured
  const W = host.clientWidth, Hh = host.clientHeight, PAD = 24, MOVE = 40; // MOVE: drift and parallax travel
  const obs = obstacles(host, PAD + MOVE), placed = [];
  sec.style.contentVisibility = cv;
  const hit = (b, list) => list.some(o => b.l < o.r && b.r > o.l && b.t < o.b && b.b > o.t);
  for (let i = 0; i < n; i++) {
    const far = r() < .4;
    const size = far ? 14 + r() * 4 : 17 + r() * 5;
    const pool = small ? PAIRS.filter(p => p[0].length < 6) : PAIRS, bit = BITS[Math.floor(r() * BITS.length)];
    const pair = pairs ? pool[i % pool.length] : [bit, bit];
    const w = Math.max(pair[0].length, pair[1].length) * size * .56 + 6, h = size * 1.3;
    let spot = null;
    for (let k = 0; k < 40 && !spot; k++) {
      const side = r() < .65;
      let x = side ? (r() < .5 ? 6 + r() * (W * .14 - w) : W * .86 + r() * (W * .14 - w - 8)) : 12 + r() * (W - w - 24);
      const y = 84 + r() * Math.max(1, Hh - h - 100); // 84px clears the fixed nav
      x = Math.max(6, Math.min(W - w - 6, x));
      const b = { l: x - MOVE, t: y - MOVE, r: x + w + MOVE, b: y + h + MOVE };
      if (!hit(b, obs) && !hit({ l: x, t: y, r: x + w, b: y + h }, placed.map(p => ({ l: p.l - 16, t: p.t - 12, r: p.r + 16, b: p.b + 12 })))) spot = { x, y, l: x, t: y, r: x + w, b: y + h };
    }
    if (!spot) continue;
    placed.push(spot);
    const el = document.createElement('span');
    el.className = 'frag';
    const set = (k, v) => el.style.setProperty(k, v);
    set('--x', (spot.x / W * 100).toFixed(2) + '%'); set('--y', (spot.y / Hh * 100).toFixed(2) + '%'); set('--s', size.toFixed(0) + 'px');
    set('--o', (.12 + r() * .2).toFixed(2));
    set('--d', ((far ? 6 : 12) * (r() < .5 ? -1 : 1) * (.6 + r() * .8)).toFixed(0));
    set('--sy', (-(far ? 18 : 40) * (.5 + r() * .5)).toFixed(0));
    set('--t', (8 + r() * 8).toFixed(1) + 's'); set('--dl', (-r() * 8).toFixed(1) + 's');
    set('--dx', ((r() - .5) * 20).toFixed(0) + 'px'); set('--dy', ((r() - .5) * 24).toFixed(0) + 'px');
    set('--r0', ((r() - .5) * 6).toFixed(1) + 'deg'); set('--r1', ((r() - .5) * 8).toFixed(1) + 'deg');
    const inner = document.createElement('span');
    inner.className = 'fi';
    const a = document.createElement('span'); a.className = 'a'; a.textContent = pair[0];
    inner.append(a);
    if (pairs) { const b = document.createElement('span'); b.className = 'b'; b.textContent = pair[1]; inner.append(b); }
    el.append(inner); host.append(el);
    out.push(el);
  }
  return out;
}

/* ---------- Scene engine: scroll progress as --p, only for scenes in view ---------- */
const scenes = [];
let ticking = false;
const io = new IntersectionObserver(entries => {
  entries.forEach(e => {
    const s = scenes.find(s => s.el === e.target);
    if (!s) return;
    s.vis = e.isIntersecting;
    e.target.classList.toggle('in-view', e.isIntersecting);
    if (e.isIntersecting) schedule();
  });
}, { rootMargin: '15% 0px' });
function register(el, mod) {
  const s = { el, mod, vis: false, p: -1, pinned: el.classList.contains('pinned') };
  scenes.push(s); io.observe(el); return s;
}
function measure(s) {
  const r = s.el.getBoundingClientRect(), vh = innerHeight;
  const span = r.height - vh;
  return s.pinned && span > 0 ? clamp(-r.top / span) : clamp((vh - r.top) / (vh + r.height));
}
function frame() {
  ticking = false;
  for (const s of scenes) {
    if (!s.vis && s.p >= 0) continue;
    const p = measure(s);
    if (Math.abs(p - s.p) < .0004) continue;
    s.p = p;
    s.el.style.setProperty('--p', p.toFixed(4));
    s.mod.update && s.mod.update(p);
  }
}
function schedule() { if (!ticking) { ticking = true; requestAnimationFrame(frame); } }

function jumpTo(s, p) { // scroll so that scene s reaches progress p
  const r = s.el.getBoundingClientRect();
  scrollTo({ top: scrollY + r.top + p * (r.height - innerHeight), behavior: RM ? 'auto' : 'smooth' });
}

/* ---------- 1. Hero ---------- */
function hero(el) {
  const h1 = $('.hero-h', el), words = $$('.fx', h1), host = $('#frags', el);
  words.forEach(fxInit);
  const fr = frags(host, 14, 7, true);
  const thr = fr.map((_, i) => .08 + i * (.4 / fr.length));
  let third = false;
  const fixThird = () => { if (third) return; third = true; fxPlay(words[2], { hold: 380 }); };
  if (RM) {
    words.forEach(w => { fxSet(w, 'right'); w.classList.add('done'); }); h1.classList.add('ready');
    fr.forEach(f => f.classList.add('fixed'));
    return { update() {} };
  }
  words.forEach(w => fxSet(w, 'wrong'));
  h1.classList.add('ready');
  words.forEach((w, i) => setTimeout(() => w.classList.add('u'), 250 + i * 160));
  setTimeout(() => fxPlay(words[0], { hold: 250 }), 1100);
  setTimeout(() => fxPlay(words[1], { hold: 250 }), 1700);
  setTimeout(fixThird, 6500);
  if (!COARSE) { // pointer parallax, eased, only while the hero is on screen
    let tx = 0, ty = 0, cx = 0, cy = 0, run = false;
    const loop = () => {
      cx = lerp(cx, tx, .08); cy = lerp(cy, ty, .08);
      el.style.setProperty('--mx', cx.toFixed(3)); el.style.setProperty('--my', cy.toFixed(3));
      if (Math.abs(cx - tx) + Math.abs(cy - ty) > .002) requestAnimationFrame(loop); else run = false;
    };
    addEventListener('pointermove', e => { tx = e.clientX / innerWidth * 2 - 1; ty = e.clientY / innerHeight * 2 - 1; if (!run && el.classList.contains('in-view')) { run = true; requestAnimationFrame(loop); } }, { passive: true });
  }
  return {
    update(p) {
      if (p > .1) fixThird();
      el.style.setProperty('--exit', smooth(.58, .97, p).toFixed(3));
      fr.forEach((f, i) => f.classList.toggle('fixed', p > thr[i]));
    }
  };
}

/* ---------- 2. Demo: scroll-scrubbed product demo ---------- */
function demo(el) {
  const win = $('#win'), ed = $('#ed'), card = $('#card'), cursor = $('#cursor'), sent = $('#sent');
  const words = $$('.w', ed), steps = $$('.step', el), status = $('#status'), fixbtn = $('#fixbtn');
  words.forEach(fxInit);
  const FIX_AT = [.80, .835, .87, .905], U_AT = [.09, .13, .17, .21];
  const state = { fixed: words.map(() => false), clicked: false, pressed: false, step: -1 };
  let g = null;

  function rel(node, anc, s) { // position of node inside anc, undoing any scale
    const a = anc.getBoundingClientRect(), b = node.getBoundingClientRect();
    return { x: (b.left - a.left) / s, y: (b.top - a.top) / s, w: b.width / s, h: b.height / s };
  }
  function layout() {
    const ent = win.classList.contains('in');
    win.style.transition = 'none'; win.classList.add('in');
    // measure the sentence in its uncorrected state so geometry matches what the viewer sees
    const saved = words.map(w => w._fx.t.textContent);
    words.forEach(w => { w._fx.t.textContent = w._fx.wrong; });
    const s = win.getBoundingClientRect().width / win.offsetWidth || 1;
    const W = ed.offsetWidth, H = ed.offsetHeight;
    const you = rel(words[1], ed, s);
    const cw = card.offsetWidth, ch = card.offsetHeight;
    const left = clamp(you.x - 26, 8, Math.max(8, W - cw - 8));
    const top = Math.min(you.y + you.h + 12, Math.max(8, H - ch - 8));
    card.style.left = left + 'px'; card.style.top = top + 'px';
    card.style.setProperty('--ox', clamp(you.x + you.w / 2 - left, 0, cw) + 'px');
    const fb = rel(fixbtn, ed, s);
    g = {
      W, H,
      start: { x: W * .84, y: H * .9 },
      word: { x: you.x + you.w * .5, y: you.y + you.h * .78 },
      btn: { x: fb.x + fb.w * .62, y: fb.y + fb.h * .6 },
      end: { x: W * .9, y: H * .96 },
    };
    words.forEach((w, i) => { w._fx.t.textContent = saved[i]; });
    if (!ent) win.classList.remove('in');
    void win.offsetWidth; win.style.transition = '';
    state.laid = true;
  }
  function path(p) {
    const A = g.start, B = g.word, C = g.btn, D = g.end;
    let a, b, t;
    if (p < .36) { a = A; b = A; t = 0; }
    else if (p < .49) { a = A; b = B; t = smooth(.36, .49, p); }
    else if (p < .66) { a = B; b = B; t = 0; }
    else if (p < .755) { a = B; b = C; t = smooth(.66, .755, p); }
    else if (p < .82) { a = C; b = C; t = 0; }
    else { a = C; b = D; t = smooth(.82, .97, p); }
    const x = lerp(a.x, b.x, t), y = lerp(a.y, b.y, t);
    // a gentle arc so the cursor feels hand-driven
    const arc = Math.sin(t * Math.PI) * -14;
    return { x, y: y + arc };
  }
  function render(p) {
    if (!g) layout();
    // underlines draw in
    words.forEach((w, i) => w.style.setProperty('--u', clamp((p - U_AT[i]) / .06).toFixed(3)));
    sent.classList.toggle('tint', p > .27 && p < .8);
    words[1].classList.toggle('hov', p > .45 && p < .8);
    // card
    const c = smooth(.49, .56, p) * (1 - smooth(.785, .84, p));
    card.style.setProperty('--c', c.toFixed(3));
    // cursor
    const pt = path(p);
    cursor.style.transform = `translate3d(${(pt.x - 3).toFixed(1)}px,${(pt.y - 2).toFixed(1)}px,0)`;
    cursor.style.setProperty('--cur', (smooth(.3, .35, p) * (1 - smooth(.93, .985, p))).toFixed(2));
    const clicked = p > .485;
    if (clicked !== state.clicked) { state.clicked = clicked; if (clicked) { cursor.classList.remove('click'); void cursor.offsetWidth; cursor.classList.add('click'); } }
    const pressed = p > .762;
    if (pressed !== state.pressed) { state.pressed = pressed; fixbtn.classList.toggle('press', pressed); if (pressed) { cursor.classList.remove('click'); void cursor.offsetWidth; cursor.classList.add('click'); } }
    // editor words correct themselves one by one
    words.forEach((w, i) => {
      const f = p > FIX_AT[i];
      if (f !== state.fixed[i]) {
        state.fixed[i] = f;
        if (f) fxPlay(w, { strike: false, dur: 420, settle: true }); else fxSet(w, 'wrong');
        if (!f) w.classList.add('u');
      }
    });
    status.textContent = p > .93 ? '0 suggestions' : p > .1 ? '4 suggestions' : '0 suggestions';
    const step = p < .3 ? 0 : p < .54 ? 1 : p < .77 ? 2 : 3;
    if (step !== state.step) { state.step = step; steps.forEach((s, i) => s.classList.toggle('on', i === step)); }
  }
  new IntersectionObserver(es => { if (es[0].isIntersecting) win.classList.add('in'); }, { threshold: .25 }).observe(win);
  addEventListener('resize', () => { g = null; if (state.laid) render(el._p ?? 0); });
  if (RM) {
    steps.forEach(s => s.classList.add('on')); win.classList.add('in');
    words.forEach(w => { fxSet(w, 'wrong', true); w.style.setProperty('--u', 1); });
    sent.classList.add('tint'); words[1].classList.add('hov');
    card.style.setProperty('--c', 1); cursor.style.setProperty('--cur', 0);
    const lay = () => { g = null; layout(); };
    addEventListener('load', lay); if (document.readyState === 'complete') lay();
    return { update() {} };
  }
  win.classList.remove('in');
  words.forEach(w => fxSet(w, 'wrong'));
  return { update(p) { el._p = p; render(p); } };
}

/* ---------- 3. Privacy: manifesto lights up word by word ---------- */
function privacy(el) {
  const h = $('[data-manifesto]', el), spans = [];
  // Split into per-word spans but keep the authored <br> and .nw phrase wrappers, so phrase pairs never split.
  const split = (node, into) => Array.from(node.childNodes).forEach(c => {
    if (c.nodeType === 3) {
      c.textContent.split(/(\s+)/).forEach(t => {
        if (!t) return;
        if (/^\s+$/.test(t)) { into.append(t); return; }
        const s = document.createElement('span');
        s.className = 'mw' + (t === 'No' ? ' hl' : ''); s.textContent = t;
        into.append(s); spans.push(s);
      });
    } else if (c.nodeType === 1 && c.classList.contains('nw')) {
      const w = document.createElement('span'); w.className = 'nw'; split(c, w); into.append(w);
    } else into.append(c.cloneNode(true));
  });
  const tmp = document.createElement('div'); split(h, tmp);
  h.replaceChildren(...tmp.childNodes);
  if (RM) return { update() {} };
  const n = spans.length;
  return {
    update(p) {
      const q = clamp((p - .06) / .78) * (n + 2);
      spans.forEach((s, i) => s.style.setProperty('--l', clamp((q - i) / 2).toFixed(3)));
    }
  };
}
function stats() {
  const tiles = $$('.tile');
  const run = n => {
    const target = +n.dataset.count;
    if (RM) { n.textContent = target; return; }
    const t0 = performance.now(), dur = 1500;
    const step = now => {
      const t = clamp((now - t0) / dur);
      if (n.dataset.kind === 'scramble') n.textContent = t < 1 ? String(Math.floor(Math.random() * 9000) + 100).slice(0, Math.max(1, 4 - Math.floor(t * 3.4))) : '0';
      else n.textContent = Math.round(target * (1 - Math.pow(2, -10 * t)) / (1 - Math.pow(2, -10)));
      if (t < 1) requestAnimationFrame(step); else n.textContent = target;
    };
    requestAnimationFrame(step);
  };
  const o = new IntersectionObserver(es => es.forEach(e => {
    if (!e.isIntersecting) return;
    e.target.classList.add('in'); run($('.num', e.target)); o.unobserve(e.target);
  }), { threshold: .35 });
  tiles.forEach(t => { if (RM) t.classList.add('in'); else { $('.num', t).textContent = '0'; o.observe(t); } });
}

/* ---------- 4. Modes: the sentence rewrites itself with a kinetic diff ---------- */
const MODES = [
  { n: 'Original', d: 'Grammar, spelling and punctuation run in every mode.', t: 'hi john, i was wondering if maybe you could possibly send me that report whenever you get a chance, thanks alot' },
  { n: 'Fix', d: 'Small fixes. Same voice.', t: 'Hi John, I was wondering if maybe you could possibly send me that report whenever you get a chance. Thanks a lot.' },
  { n: 'Professional', d: 'Clear, composed, considered.', t: 'Hello John, could you please send me that report at your earliest convenience? Thank you.' },
  { n: 'Friendly', d: 'A little warmer. Still you.', t: 'Hi John! Could you send me that report when you get a chance? Thanks so much!' },
  { n: 'Concise', d: 'Fewer words. Full meaning.', t: 'Hi John, could you send me that report when you can? Thanks.' },
  { n: 'Direct', d: 'Get straight to the point.', t: 'John, please send me that report. Thanks.' },
];
function diffWords(a, b) { // word-level LCS; removals come before insertions in each change
  const A = a.split(' '), B = b.split(' '), n = A.length, m = B.length;
  const L = Array.from({ length: n + 1 }, () => new Array(m + 1).fill(0));
  for (let i = n - 1; i >= 0; i--) for (let j = m - 1; j >= 0; j--) L[i][j] = A[i] === B[j] ? L[i + 1][j + 1] + 1 : Math.max(L[i + 1][j], L[i][j + 1]);
  const out = []; let i = 0, j = 0;
  while (i < n || j < m) {
    if (i < n && j < m && A[i] === B[j]) { out.push({ k: 'keep', w: A[i] }); i++; j++; }
    else {
      const dels = [], ins = [];
      while ((i < n || j < m) && !(i < n && j < m && A[i] === B[j])) {
        if (j >= m || (i < n && L[i + 1][j] >= L[i][j + 1])) dels.push(A[i++]); else ins.push(B[j++]);
      }
      dels.forEach(w => out.push({ k: 'del', w })); ins.forEach(w => out.push({ k: 'ins', w }));
    }
  }
  return out;
}
function modes(el, scene) {
  const stage = $('#mstage'), text = $('#mtext'), label = $('#mlabel'), detail = $('#mdetail'), chips = $$('.mchip', el);
  const SEG = (1 - .08) / 5;
  const segStart = i => .08 + (i - 1) * SEG;
  chips.forEach(c => c.addEventListener('click', () => jumpTo(scene.s, segStart(+c.dataset.i) + SEG * .72)));
  if (RM) return { update() {} };
  let built = -1, lastStage = -1;
  function build(idx) {
    built = idx; text.textContent = ''; lastStage = -1;
    const toks = idx === 0 ? MODES[0].t.split(' ').map(w => ({ k: 'keep', w })) : diffWords(MODES[idx - 1].t, MODES[idx].t);
    toks.forEach((t, i) => {
      const s = document.createElement('span'); s.className = 'tk ' + t.k;
      const inner = document.createElement('i'); inner.textContent = t.w + (i < toks.length - 1 ? ' ' : '');
      inner._final = inner.textContent;
      s.append(inner); text.append(s);
    });
    stage.classList.toggle('errs', idx === 1);
    label.textContent = MODES[idx].n;
    detail.textContent = MODES[idx].d;
    chips.forEach(c => c.classList.toggle('on', +c.dataset.i === idx));
  }
  build(0); stage.dataset.s = '3';
  return {
    update(p) {
      let idx = 0, s = 3;
      if (p >= .08) {
        idx = Math.min(5, 1 + Math.floor((p - .08) / SEG));
        const t = (p - segStart(idx)) / SEG;
        s = t < .1 ? 0 : t < .3 ? 1 : t < .52 ? 2 : 3;
      }
      if (idx !== built) build(idx);
      if (s !== lastStage) {
        const enter2 = s === 2 && lastStage !== -1 && lastStage < 2;
        lastStage = s; stage.dataset.s = String(s);
        if (enter2) $$('.tk.ins i', text).forEach(i => scramble(i, i._final, 520));
      }
    }
  };
}

/* ---------- 5. Showcase: stacked screenshots fan out in 3D ---------- */
function showcase(el) {
  if (RM) return { update() {} };
  return { update(p) { const f = smooth(.12, .62, p); el.style.setProperty('--f', f.toFixed(4)); } };
}

/* ---------- 6. Compatibility marquees ---------- */
function marquees() {
  if (RM) return;
  $$('.track').forEach(t => Array.from(t.children).forEach(c => { const k = c.cloneNode(true); k.setAttribute('aria-hidden', 'true'); t.append(k); }));
}

/* ---------- 7. Open source: typed code and copy ---------- */
const FILES = [
  { path: 'engine/rules/grammar.json', lang: 'json', text: String.raw`{
  "id": "grammar.your_doing",
  "pattern": "(?i)\\b(?:I hope|hope|I think) (?P<target>your)(?: doing (?:well|great)| having a)",
  "replacement": "you're",
  "category": "Grammar",
  "confidence": 0.98,
  "reason": "Use you're (you are) before this predicate.",
  "provenance": "parzr original rule",
  "positive": "I hope your doing well.",
  "negative": "Thank you for your doing this manually."
}` },
  { path: 'engine/src/lib.rs', lang: 'rust', text: `pub fn rewrite(req: &Request) -> Result<RewriteResult, String> {
    #[cfg(feature = "local-model")]
    if req.tokens.is_empty() && !req.text.is_empty() {
        if req.text.len() > MAX_TEXT_BYTES {
            return Err("Select at most 64 KB of text.".into());
        }
        let mut enriched = req.clone();
        enriched.tokens = model::linguistic_hints(&req.text)?;
        return pipeline::rewrite(&enriched);
    }
    pipeline::rewrite(req)
}` },
];
function highlight(src, lang) {
  const esc = src.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const re = lang === 'json'
    ? /("(?:[^"\\]|\\.)*")(\s*:)?|\b(\d+\.?\d*)\b|([{}[\],])/g
    : /(\/\/.*)|("(?:[^"\\]|\\.)*")|\b(pub|fn|let|mut|if|return|impl|struct)\b|\b(Request|RewriteResult|String|Result|Err)\b|(#\[[^\]]*\])/g;
  return esc.replace(re, (m, a, b, c, d, e) => {
    if (lang === 'json') return a ? (b ? `<span class="tk-k">${a}</span>${b}` : `<span class="tk-s">${a}</span>`) : c ? `<span class="tk-n">${c}</span>` : `<span class="tk-p">${d}</span>`;
    return a ? `<span class="tk-c">${a}</span>` : b ? `<span class="tk-s">${b}</span>` : c ? `<span class="tk-k">${c}</span>` : d ? `<span class="tk-t">${d}</span>` : `<span class="tk-p">${e}</span>`;
  });
}
function openSource() {
  const out = $('#code-out'), pathEl = $('#code-path'), tabs = $$('.tabs button'), box = $('#code');
  let raf = 0, cur = 0, started = false;
  const show = (i, n) => { out.innerHTML = highlight(FILES[i].text.slice(0, n), FILES[i].lang); };
  function type(i) {
    cancelAnimationFrame(raf); cur = i;
    pathEl.textContent = FILES[i].path;
    tabs.forEach((t, k) => t.setAttribute('aria-selected', String(k === i)));
    const full = FILES[i].text;
    if (RM) { show(i, full.length); return; }
    let n = 0, last = performance.now();
    const tick = now => {
      n = Math.min(full.length, n + Math.max(1, Math.round((now - last) / 11))); last = now;
      show(i, n);
      if (n < full.length) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
  }
  tabs.forEach((t, k) => t.addEventListener('click', () => type(k)));
  show(0, FILES[0].text.length);
  const sr = document.createElement('pre'); sr.className = 'sr-only'; sr.textContent = FILES.map(f => f.path + '\n' + f.text).join('\n\n');
  box.append(sr); $('.code-pre', box).setAttribute('aria-hidden', 'true');
  if (!RM) {
    out.textContent = '';
    new IntersectionObserver((es, o) => { if (es[0].isIntersecting && !started) { started = true; type(0); o.disconnect(); } }, { threshold: .4 }).observe(box);
  }
  // copy build commands
  const btn = $('#copy'), label = $('#copy-t'), live = $('#copy-live');
  btn.addEventListener('click', async () => {
    const pre = $('#build-cmds'), txt = pre.textContent;
    let ok = false;
    try { await navigator.clipboard.writeText(txt); ok = true; } catch (_) {
      const r = document.createRange(); r.selectNodeContents(pre);
      const s = getSelection(); s.removeAllRanges(); s.addRange(r);
      try { ok = document.execCommand('copy'); } catch (_) { ok = false; }
      s.removeAllRanges();
    }
    label.textContent = ok ? 'Copied' : 'Press Cmd+C'; live.textContent = ok ? 'Build commands copied.' : 'Select the commands and press Command C.';
    btn.classList.toggle('ok', ok);
    setTimeout(() => { label.textContent = 'Copy'; btn.classList.remove('ok'); }, 1800);
  });
}

/* ---------- 8. Final CTA ---------- */
function final(el) {
  const w = $('.fx', el); fxInit(w);
  if (RM) { fxSet(w, 'right'); w.classList.add('done'); return { update() {} }; }
  fxSet(w, 'wrong'); let st = 0;
  return {
    update(p) {
      const s = p > .3 ? 2 : p > .06 ? 1 : 0;
      if (s === st) return;
      st = s;
      if (s === 2) fxPlay(w, { hold: 380, settle: false });
      else if (s === 1) { fxSet(w, 'wrong'); w.classList.add('u'); } else fxSet(w, 'wrong');
    }
  };
}

/* ---------- Nav ---------- */
function nav() {
  const t = $('.nav-toggle'), l = $('#nav-links');
  t.addEventListener('click', () => { const o = l.classList.toggle('open'); t.setAttribute('aria-expanded', String(o)); });
  l.addEventListener('click', e => { if (e.target.closest('a')) { l.classList.remove('open'); t.setAttribute('aria-expanded', 'false'); } });
  addEventListener('keydown', e => { if (e.key === 'Escape' && l.classList.contains('open')) { l.classList.remove('open'); t.setAttribute('aria-expanded', 'false'); t.focus(); } });
}

/* ---------- 404 ---------- */
function notFound() {
  const el = $('.nf .fx'); if (!el) return;
  fxInit(el);
  if (RM) { fxSet(el, 'right'); el.classList.add('done'); return; }
  fxSet(el, 'wrong');
  setTimeout(() => el.classList.add('u'), 300);
  setTimeout(() => fxPlay(el, { hold: 300 }), 1000);
}

/* ---------- Boot ---------- */
function boot() {
  if ($('.nav-toggle')) nav();
  notFound();
  const mods = {
    hero, demo, privacy, modes: el => modes(el, mods._s), showcase, final,
  };
  $$('.fg').forEach((h, i) => { if (!RM) frags(h, +h.dataset.n || 8, 100 + i * 13, false); });
  $$('[data-scene]').forEach(el => {
    const name = el.dataset.scene, holder = {};
    mods._s = holder;
    const mod = mods[name] ? mods[name](el) : { update() {} };
    holder.s = register(el, mod);
  });
  // non-pinned sections only need parallax progress
  $$('.works, .open').forEach(el => register(el, { update() {} }));
  if ($('.tiles')) { stats(); marquees(); openSource(); }
  if (!RM) { addEventListener('scroll', schedule, { passive: true }); addEventListener('resize', () => { scenes.forEach(s => s.p = -1); schedule(); }); }
  frame();
}
if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();
