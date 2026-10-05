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
const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

// Analytics (Rybbit). The script can be blocked, or still loading: early events wait up to ~8s, and nothing here may throw.
const Q = [];
const track = (name, props) => { try { window.rybbit ? window.rybbit.event(name, props) : Q.length < 50 && Q.push([name, props]); } catch {} };
let tries = 0;
const flush = setInterval(() => {
  if (window.rybbit) Q.splice(0).forEach(e => track(...e));
  if (window.rybbit || ++tries > 20) { clearInterval(flush); Q.length = 0; }
}, 400);

/* A flag per element that says whether it is on screen, so loops can pause themselves. */
const seen = new WeakMap();
const sio = new IntersectionObserver(es => es.forEach(e => seen.set(e.target, e.isIntersecting)), { rootMargin: '10% 0px' });
const watch = el => { sio.observe(el); return () => !!seen.get(el) && !document.hidden; };
async function until(fn) { while (!fn()) await sleep(250); }

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


/* ---------- Scene engine: scroll progress as --p, eased, only for scenes in view ---------- */
// The page itself scrolls natively. Only the progress value that drives transforms is smoothed (a lerp), so motion feels weighty.
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
  scrollFx();
  let moving = false;
  for (const s of scenes) {
    if (!s.vis && s.p >= 0) continue;
    const t = measure(s);
    const p = s.p < 0 ? t : lerp(s.p, t, .2);
    const done = Math.abs(t - p) < .0007;
    if (!done) moving = true;
    const next = done ? t : p;
    if (s.mod.scroll) s.mod.scroll();
    if (Math.abs(next - s.p) < .0003 && s.p >= 0) continue;
    s.p = next;
    s.el.style.setProperty('--p', next.toFixed(4));
    s.mod.update && s.mod.update(next);
  }
  if (moving) schedule();
}
function schedule() { if (!ticking) { ticking = true; requestAnimationFrame(frame); } }

/* ---------- 1. Hero: the headline corrects itself; a glass editor behind it catches mistakes live ---------- */
const HERO_LINES = [
  [{ t: 'Thanks, ' }, { w: ['aman jain', 'Aman Jain'], b: 1 }, { t: '. I ' }, { w: ['recieved', 'received'] }, { t: ' ' }, { w: ['teh', 'the'] }, { t: ' report.' }],
  [{ w: ['Your', "You're"] }, { t: ' doing ' }, { w: ['alot', 'a lot'] }, { t: ' better, ' }, { w: ['priya', 'Priya'], b: 1 }, { t: '.' }],
  [{ t: 'We should ' }, { w: ['utilize', 'use'], b: 1 }, { t: ' it ' }, { w: ['in order to', 'to'], b: 1 }, { t: ' ship.' }],
];
function buildLine(host, spec, diffHost) {
  host.textContent = ''; if (diffHost) diffHost.textContent = '';
  const words = [];
  spec.forEach(p => {
    if (p.t) { host.append(p.t); diffHost && diffHost.append(p.t); }
    else {
      const s = document.createElement('span'); s.className = 'fx w' + (p.b ? ' blue' : ''); s.dataset.wrong = p.w[0]; s.textContent = p.w[1];
      host.append(s); fxInit(s); fxSet(s, 'wrong'); words.push(s);
      if (diffHost) { const d = document.createElement('del'), n = document.createElement('ins'); d.textContent = p.w[0]; n.textContent = p.w[1]; diffHost.append(d, ' ', n); }
    }
  });
  return words;
}
function hero(el) {
  const h1 = $('.hero-h', el), hw = $$('.fx', h1), host = $('#hw-line'), diff = $('#hw-diff'), card = $('#hw-card');
  const status = $('#hw-status'), count = $('#hw-count'), fixbtn = $('#hw-fix'), dot = status.previousElementSibling;
  hw.forEach(fxInit);
  const awake = watch(el);
  const setCount = n => { count.textContent = n + (n === 1 ? ' fix in this sentence' : ' fixes in this sentence'); };
  if (RM) {
    hw.forEach(w => { fxSet(w, 'right'); w.classList.add('done'); }); h1.classList.add('ready');
    const words = buildLine(host, HERO_LINES[0], diff);
    words.forEach(w => fxSet(w, 'wrong', true)); setCount(words.length); card.classList.add('on'); status.textContent = words.length + ' suggestions';
    return { update() {} };
  }
  let third = false;
  const fixThird = () => { if (third) return; third = true; fxPlay(hw[2], { hold: 380 }); };
  hw.forEach(w => fxSet(w, 'wrong'));
  h1.classList.add('ready');
  hw.forEach((w, i) => setTimeout(() => w.classList.add('u'), 250 + i * 160));
  setTimeout(() => fxPlay(hw[0], { hold: 250 }), 1100);
  setTimeout(() => fxPlay(hw[1], { hold: 250 }), 1700);
  setTimeout(fixThird, 6500);
  // the live editor loop: type, underline, show the card, press Fix sentence, resolve
  (async () => {
    await sleep(900);
    for (let i = 0; ; i = (i + 1) % HERO_LINES.length) {
      await until(awake);
      const words = buildLine(host, HERO_LINES[i], diff), n = words.length, chars = host.textContent.length;
      host.classList.remove('out', 'typing'); void host.offsetWidth;
      host.style.setProperty('--tn', chars); host.style.setProperty('--ty', (chars * 38) + 'ms');
      host.classList.add('typing'); status.textContent = '0 suggestions'; dot.parentElement.classList.add('clear');
      await sleep(chars * 38 + 250);
      dot.parentElement.classList.remove('clear'); status.textContent = n + ' suggestions'; setCount(n);
      for (const w of words) { w.classList.add('u'); await sleep(260); }
      await sleep(700); card.classList.add('on'); await sleep(2000);
      fixbtn.classList.remove('press'); void fixbtn.offsetWidth; fixbtn.classList.add('press'); await sleep(260);
      card.classList.remove('on');
      words.forEach((w, k) => setTimeout(() => fxPlay(w, { strike: true, hold: 120, dur: 420 }), k * 300));
      await sleep(words.length * 300 + 1100);
      status.textContent = '0 suggestions'; dot.parentElement.classList.add('clear');
      await sleep(2300); host.classList.add('out'); await sleep(600);
    }
  })();
  if (!COARSE) { // pointer parallax, cursor spotlight and headline tilt, all eased, only while the hero is on screen
    const spot = $('#spot', el);
    let tx = 0, ty = 0, cx = 0, cy = 0, px = innerWidth / 2, py = innerHeight * .4, sx = px, sy = py, run = false;
    const loop = () => {
      cx = lerp(cx, tx, .08); cy = lerp(cy, ty, .08); sx = lerp(sx, px, .12); sy = lerp(sy, py, .12);
      el.style.setProperty('--mx', cx.toFixed(3)); el.style.setProperty('--my', cy.toFixed(3));
      spot.style.transform = `translate3d(${sx.toFixed(1)}px,${sy.toFixed(1)}px,0)`;
      h1.style.transform = `perspective(1100px) rotateX(${(-cy * 4).toFixed(2)}deg) rotateY(${(cx * 4).toFixed(2)}deg)`;
      if (Math.abs(cx - tx) + Math.abs(cy - ty) + Math.abs(sx - px) / 400 + Math.abs(sy - py) / 400 > .002) requestAnimationFrame(loop); else run = false;
    };
    addEventListener('pointermove', e => {
      tx = e.clientX / innerWidth * 2 - 1; ty = e.clientY / innerHeight * 2 - 1; px = e.clientX; py = e.clientY;
      if (!el.classList.contains('in-view')) return;
      spot.classList.add('on');
      if (!run) { run = true; requestAnimationFrame(loop); }
    }, { passive: true });
    root.addEventListener('mouseleave', () => { spot.classList.remove('on'); tx = ty = 0; if (!run) { run = true; requestAnimationFrame(loop); } });
  }
  return {
    update(p) {
      if (p > .1) fixThird();
      el.style.setProperty('--exit', smooth(.1, .46, p).toFixed(3));
    }
  };
}

/* ---------- 2. Try it: a small client-side checker with the app's colours ---------- */
// ponytail: a dozen hand-written rules, no network. The app's engine does far more; this only shows the feel.
// Names are proper nouns: a lowercase one gets a blue capitalisation suggestion, and is never respelled.
const NAMES = new Set('aman jain priya ananya wei mohammed muhammad fatima olu chidi yuki aiko sofia nguyen dmitri ivan anna jose maria ahmed aisha raj kenji hana kwame amara sven liam noah mei li chen kim'.split(' '));
const RULES = [
  [/\bteh\b/gi, 'the', 'r', 'Common misspelling of "the".'],
  [/\brecieve(d|s|r)?\b/gi, 'receive$1', 'r', 'i before e, except after c.'],
  [/\bdefinately\b/gi, 'definitely', 'r', 'Use the standard spelling.'],
  [/\bseperate(d|ly)?\b/gi, 'separate$1', 'r', 'Use the standard spelling.'],
  [/\balot\b/gi, 'a lot', 'r', 'Two words: a lot.'],
  [/\bwich\b/gi, 'which', 'r', 'Use the standard spelling.'],
  [/\bmesage(s)?\b/gi, 'message$1', 'r', 'Use the standard spelling.'],
  [/\buntill\b/gi, 'until', 'r', 'Use the standard spelling.'],
  [/\boccured\b/gi, 'occurred', 'r', 'Double the r in occurred.'],
  [/\bbecuase\b/gi, 'because', 'r', 'Use the standard spelling.'],
  [/\bthier\b/gi, 'their', 'r', 'Use the standard spelling.'],
  [/\btommorow\b/gi, 'tomorrow', 'r', 'Use the standard spelling.'],
  [/\bfreind(s)?\b/gi, 'friend$1', 'r', 'i before e, except after c.'],
  [/\byour(?= (?:doing|going|being|welcome|not|right|wrong|a)\b)/gi, "you're", 'r', "Use you're (you are) before this predicate."],
  [/\bits(?= (?:a|the|going|been|not|so|very|time|too|alot|better|worse|good|great|ready)\b)/gi, "it's", 'r', "Use it's (it is) here."],
  [/\b(could|should|would) of\b/gi, '$1 have', 'r', 'Use "have", not "of".'],
  [/\bi\b(?!')/g, 'I', 'r', 'Capitalize the first-person pronoun.'],
  [/\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|january|february|april|june|july|september|october|november|december)\b/g, w => cap(w), 'r', 'Capitalize days and months.'],
  [/\bin order to\b/gi, 'to', 'b', 'Wordy. "to" says the same, shorter.'],
  [/\bvery unique\b/gi, 'unique', 'b', '"Unique" is already absolute.'],
  [/\butilize\b/gi, 'use', 'b', 'A plainer word.'],
  [/\bat this point in time\b/gi, 'now', 'b', 'Wordy. "now" says the same.'],
  [/\bdue to the fact that\b/gi, 'because', 'b', 'Wordy. "because" says the same.'],
];
const cap = s => s.replace(/(^| )\p{L}/gu, c => c.toUpperCase());
const caseLike = (from, to) => /^[A-Z]/.test(from) && /^[a-z]/.test(to) && from !== 'I' ? to[0].toUpperCase() + to.slice(1) : to;
function analyze(text, ignored) {
  const names = [], marks = [], wre = /[\p{L}'’]+/gu; let m, prev = null;
  while ((m = wre.exec(text))) {
    if (!NAMES.has(m[0].toLowerCase())) { prev = null; continue; }
    if (prev && /^ +$/.test(text.slice(prev.e, m.index))) prev.e = m.index + m[0].length; else { prev = { s: m.index, e: m.index + m[0].length }; names.push(prev); }
  }
  for (const n of names) {
    const from = text.slice(n.s, n.e), to = cap(from);
    if (/(?:^| )\p{Ll}/u.test(from) && !ignored.has(from.toLowerCase() + '|' + to)) marks.push({ s: n.s, e: n.e, from, to, kind: 'b', why: `Capitalize the name "${to}".` });
  }
  for (const [re, to, kind, why] of RULES) {
    re.lastIndex = 0;
    while ((m = re.exec(text))) {
      const s = m.index, e = s + m[0].length;
      if (names.some(n => s < n.e && e > n.s)) continue;
      const rep = typeof to === 'function' ? to(m[0]) : caseLike(m[0], to.replace(/\$(\d)/g, (_, k) => m[k] || ''));
      if (ignored.has(m[0].toLowerCase() + '|' + rep)) continue;
      if (marks.some(k => s < k.e && e > k.s)) continue;
      marks.push({ s, e, from: m[0], to: rep, kind, why });
    }
  }
  return marks.sort((a, b) => a.s - b.s);
}
function tryIt(el) {
  const ta = $('#try-ta'), back = $('#try-back'), body = $('#try-body'), card = $('#tcard'), win = $('#try-win');
  const status = $('#try-status'), allBtn = $('#try-all'), nextBtn = $('#try-next');
  const SAMPLES = [
    'I recieved teh mesage and its alot better than last time. Your doing great, and I will definately reply tommorow.',
    'We should utilize the new process in order to ship faster. At this point in time it is a very unique approach, due to the fact that nobody has tried it.',
    'thanks, priya. aman jain said i recieved the invoice on friday, but ananya and wei have not. Fatima wants it seperate.',
  ];
  const ignored = new Set(); let marks = [], fixed = [], prevKeys = new Set(), active = -1, started = false, timer = 0, typed = false, had = false, cleared = false;
  const fit = () => { ta.style.height = 'auto'; ta.style.height = ta.scrollHeight + 'px'; };
  function render() {
    const text = ta.value; marks = analyze(text, ignored);
    const keys = new Set(), pieces = [];
    marks.forEach((k, i) => pieces.push({ s: k.s, e: k.e, html: `<span class="im${k.kind === 'b' ? ' blue' : ''}${prevKeys.has(k.kind + k.from + k.s) ? '' : ' new'}" data-i="${i}">${esc(k.from)}</span>` }));
    fixed.forEach(f => pieces.push({ s: f[0], e: f[1], html: `<span class="im ok">${esc(text.slice(f[0], f[1]))}</span>` }));
    pieces.sort((a, b) => a.s - b.s);
    let out = '', at = 0;
    pieces.forEach(p => { if (p.s < at) return; out += esc(text.slice(at, p.s)) + p.html; at = p.e; });
    out += esc(text.slice(at)); if (text.endsWith('\n') || !text) out += ' ';
    back.innerHTML = out;
    marks.forEach(k => keys.add(k.kind + k.from + k.s)); prevKeys = keys;
    const n = marks.length;
    if (n) had = true; else if (had && !cleared && ta.value.trim()) { cleared = true; track('Try it: all clear'); } // render only runs after a user action once the first marks are up
    status.textContent = n ? n + (n === 1 ? ' suggestion' : ' suggestions') : 'No suggestions';
    status.parentElement.classList.toggle('clear', !n);
    allBtn.disabled = nextBtn.disabled = !n;
    fit();
  }
  const spans = i => $$(`.im[data-i="${i}"]`, back);
  function sentenceOf(k) {
    const t = ta.value; let s = k.s, e = k.e;
    while (s > 0 && !/[.!?\n]/.test(t[s - 1])) s--;
    while (e < t.length && !/[.!?\n]/.test(t[e])) e++;
    if (e < t.length && /[.!?]/.test(t[e])) e++;
    return { s, e };
  }
  function closeCard() { card.classList.remove('on'); active = -1; $$('.im.hov', back).forEach(x => x.classList.remove('hov')); }
  function openCard(i, focus) {
    const k = marks[i]; if (!k) return;
    active = i;
    const sen = sentenceOf(k), inSen = marks.filter(m => m.s >= sen.s && m.e <= sen.e);
    const t = ta.value; let html = '', at = sen.s;
    inSen.forEach(m => { html += esc(t.slice(at, m.s)) + `<del>${esc(m.from)}</del> <ins${m === k ? ' class="focus"' : ''}>${esc(m.to)}</ins>`; at = m.e; });
    html += esc(t.slice(at, sen.e));
    $('#tc-diff').innerHTML = html.trim();
    $('#tc-why').innerHTML = `<b>${esc(k.from)} → ${esc(k.to)}</b><span>${esc(k.why)}</span>`;
    $('#tc-title').textContent = k.kind === 'b' && inSen.length === 1 ? 'Style suggestion' : inSen.length + (inSen.length === 1 ? ' fix in this sentence' : ' fixes in this sentence');
    card.classList.toggle('blue', k.kind === 'b');
    $('#tc-fix').dataset.s = sen.s + ',' + sen.e;
    $$('.im.hov', back).forEach(x => x.classList.remove('hov')); spans(i).forEach(x => x.classList.add('hov'));
    const b = body.getBoundingClientRect(), r = (spans(i)[0] || back).getBoundingClientRect();
    const cw = card.offsetWidth;
    card.style.left = clamp(r.left - b.left - 26, 8, Math.max(8, b.width - cw - 8)) + 'px';
    card.style.top = (r.bottom - b.top + 12) + 'px';
    card.style.setProperty('--ox', clamp(r.left - b.left + r.width / 2 - parseFloat(card.style.left), 0, cw) + 'px');
    card.classList.add('on');
    if (focus) $('#tc-fix').focus({ preventScroll: true });
  }
  function apply(list) { // replace from the end so offsets stay valid, then flash the fixes mint
    if (!list.length) return;
    let t = ta.value; const out = [];
    [...list].sort((a, b) => b.s - a.s).forEach(k => { t = t.slice(0, k.s) + k.to + t.slice(k.e); });
    let d = 0; [...list].sort((a, b) => a.s - b.s).forEach(k => { out.push([k.s + d, k.s + d + k.to.length]); d += k.to.length - (k.e - k.s); });
    ta.value = t; closeCard(); fixed = out; render(); setTimeout(() => { fixed = []; }, 2200);
  }
  const hit = (x, y) => marks.findIndex((_, i) => spans(i).some(sp => Array.from(sp.getClientRects()).some(r => x >= r.left && x <= r.right && y >= r.top - 4 && y <= r.bottom + 4)));
  ta.addEventListener('pointermove', e => { const i = hit(e.clientX, e.clientY); ta.style.cursor = i < 0 ? '' : 'pointer'; if (!COARSE && active < 0) { $$('.im.hov', back).forEach(x => x.classList.remove('hov')); if (i >= 0) spans(i).forEach(x => x.classList.add('hov')); } });
  ta.addEventListener('pointerleave', () => { if (active < 0) $$('.im.hov', back).forEach(x => x.classList.remove('hov')); });
  ta.addEventListener('click', e => {
    const i = hit(e.clientX, e.clientY);
    if (i >= 0) { openCard(i); track('Try it: suggestion opened', { kind: marks[i].kind === 'b' ? 'Style' : 'Mistake', word: marks[i].from.slice(0, 40) }); } else closeCard();
  });
  ta.addEventListener('input', () => { if (!typed) { typed = true; track('Try it: started typing'); } closeCard(); fixed = []; fit(); clearTimeout(timer); timer = setTimeout(render, 120); });
  win.addEventListener('keydown', e => { if (e.key === 'Escape' && active >= 0) { closeCard(); ta.focus(); } });
  $('#tc-x').addEventListener('click', () => { closeCard(); ta.focus(); });
  $('#tc-fix').addEventListener('click', e => { track('Try it: sentence fixed'); const [s, en] = e.currentTarget.dataset.s.split(',').map(Number); apply(marks.filter(m => m.s >= s && m.e <= en)); ta.focus({ preventScroll: true }); });
  $('#tc-word').addEventListener('click', () => { track('Try it: word fixed'); apply([marks[active]]); ta.focus({ preventScroll: true }); });
  $('#tc-ign').addEventListener('click', () => { track('Try it: suggestion ignored'); const k = marks[active]; ignored.add(k.from.toLowerCase() + '|' + k.to); closeCard(); render(); ta.focus({ preventScroll: true }); });
  allBtn.addEventListener('click', () => { track('Try it: fix all', { count: marks.length }); apply(marks); allBtn.classList.remove('ping'); void allBtn.offsetWidth; allBtn.classList.add('ping'); });
  nextBtn.addEventListener('click', () => { track('Try it: next suggestion'); openCard((active + 1) % marks.length); });
  $$('[data-sample]', el).forEach(b => b.addEventListener('click', () => {
    track('Try it: sample picked', { sample: b.textContent.trim() });
    $$('[data-sample]', el).forEach(x => { x.classList.toggle('on', x === b); x.setAttribute('aria-pressed', String(x === b)); });
    ta.value = SAMPLES[+b.dataset.sample]; ignored.clear(); fixed = []; prevKeys = new Set(); closeCard(); render();
  }));
  addEventListener('resize', () => { fit(); if (active >= 0) closeCard(); });
  ta.value = SAMPLES[0]; fit();
  const start = () => { if (started) return; started = true; render(); };
  if (RM) start(); else new IntersectionObserver((es, o) => { if (es[0].isIntersecting) { start(); o.disconnect(); } }, { threshold: .3 }).observe(win);
  if (!COARSE && !RM) addEventListener('pointermove', e => { const r = win.getBoundingClientRect(); if (r.bottom < 0 || r.top > innerHeight) return; win.style.setProperty('--mx', clamp((e.clientX - r.left - r.width / 2) / innerWidth * 2, -1, 1).toFixed(3)); win.style.setProperty('--my', clamp((e.clientY - r.top - r.height / 2) / innerHeight * 2, -1, 1).toFixed(3)); }, { passive: true });
}

/* ---------- 3. How it works: scroll-scrubbed product demo; the window tilts flat as the scene pins ---------- */
function demo(el) {
  const win = $('#win'), ed = $('#ed'), card = $('#card'), cursor = $('#cursor'), sent = $('#sent');
  const words = $$('.w', ed), steps = $$('.step', el), status = $('#status'), fixbtn = $('#fixbtn');
  words.forEach(fxInit);
  const FIX_AT = [.80, .835, .87, .905], U_AT = [.09, .13, .17, .21];
  const state = { fixed: words.map(() => false), clicked: false, pressed: false, step: -1 };
  let g = null;

  function rel(node, anc) { // position of node inside anc, measured with the 3D tilt switched off
    const a = anc.getBoundingClientRect(), b = node.getBoundingClientRect();
    return { x: b.left - a.left, y: b.top - a.top, w: b.width, h: b.height };
  }
  function layout() {
    win.style.transition = 'none'; win.style.transform = 'none';
    const saved = words.map(w => w._fx.t.textContent);
    words.forEach(w => { w._fx.t.textContent = w._fx.wrong; });
    const W = ed.offsetWidth, H = ed.offsetHeight;
    const you = rel(words[1], ed);
    const cw = card.offsetWidth, ch = card.offsetHeight;
    const left = clamp(you.x - 26, 8, Math.max(8, W - cw - 8));
    const top = Math.min(you.y + you.h + 12, Math.max(8, H - ch - 8));
    card.style.left = left + 'px'; card.style.top = top + 'px';
    card.style.setProperty('--ox', clamp(you.x + you.w / 2 - left, 0, cw) + 'px');
    const fb = rel(fixbtn, ed);
    g = {
      W, H,
      start: { x: W * .84, y: H * .9 },
      word: { x: you.x + you.w * .5, y: you.y + you.h * .78 },
      btn: { x: fb.x + fb.w * .62, y: fb.y + fb.h * .6 },
      end: { x: W * .9, y: H * .96 },
    };
    words.forEach((w, i) => { w._fx.t.textContent = saved[i]; });
    void win.offsetWidth; win.style.transition = ''; win.style.transform = '';
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
    const arc = Math.sin(t * Math.PI) * -14; // a gentle arc so the cursor feels hand-driven
    return { x, y: y + arc };
  }
  function render(p) {
    if (!g) layout();
    words.forEach((w, i) => w.style.setProperty('--u', clamp((p - U_AT[i]) / .06).toFixed(3)));
    sent.classList.toggle('tint', p > .27 && p < .8);
    words[1].classList.toggle('hov', p > .45 && p < .8);
    const c = smooth(.49, .56, p) * (1 - smooth(.785, .84, p));
    card.style.setProperty('--c', c.toFixed(3));
    const pt = path(p);
    cursor.style.transform = `translate3d(${(pt.x - 3).toFixed(1)}px,${(pt.y - 2).toFixed(1)}px,0)`;
    cursor.style.setProperty('--cur', (smooth(.3, .35, p) * (1 - smooth(.93, .985, p))).toFixed(2));
    const clicked = p > .485;
    if (clicked !== state.clicked) { state.clicked = clicked; if (clicked) { cursor.classList.remove('click'); void cursor.offsetWidth; cursor.classList.add('click'); } }
    const pressed = p > .762;
    if (pressed !== state.pressed) { state.pressed = pressed; fixbtn.classList.toggle('press', pressed); if (pressed) { cursor.classList.remove('click'); void cursor.offsetWidth; cursor.classList.add('click'); } }
    words.forEach((w, i) => {
      const f = p > FIX_AT[i];
      if (f !== state.fixed[i]) {
        state.fixed[i] = f;
        if (f) fxPlay(w, { strike: false, dur: 420, settle: true }); else fxSet(w, 'wrong');
        if (!f) w.classList.add('u');
      }
    });
    status.textContent = p > .93 ? '0 suggestions' : p > .1 ? '4 suggestions' : '0 suggestions';
    status.parentElement.classList.toggle('clear', p > .93);
    const step = p < .3 ? 0 : p < .54 ? 1 : p < .77 ? 2 : 3;
    if (step !== state.step) { state.step = step; steps.forEach((s, i) => s.classList.toggle('on', i === step)); }
  }
  addEventListener('resize', () => { g = null; if (state.laid) render(el._p ?? 0); });
  if (RM) {
    steps.forEach(s => s.classList.add('on'));
    words.forEach(w => { fxSet(w, 'wrong', true); w.style.setProperty('--u', 1); });
    sent.classList.add('tint'); words[1].classList.add('hov');
    card.style.setProperty('--c', 1); cursor.style.setProperty('--cur', 0);
    const lay = () => { g = null; layout(); };
    addEventListener('load', lay); if (document.readyState === 'complete') lay();
    return { update() {} };
  }
  words.forEach(w => fxSet(w, 'wrong'));
  return {
    // tilt: two thirds on the way in, the rest as the scene pins
    scroll() {
      const top = el.getBoundingClientRect().top, vh = innerHeight;
      const e = top > 0 ? smooth(0, 1, clamp(1 - top / vh)) * .65 : .65 + smooth(0, .14, el._p ?? 0) * .35;
      win.style.setProperty('--e', e.toFixed(3));
    },
    update(p) { el._p = p; render(p); }
  };
}

/* ---------- 4. Names: a lowercase name gains its capital (blue) while a real typo is fixed (red) ---------- */
function names(el) {
  const fxw = $('#nfx'), nm = $('#nm1'), st = $('#n-status'), fig = $('#fig'), cnt = $('#fig-n'), awake = watch($('#nwin'));
  fxInit(fxw); fxInit(nm);
  if (RM) { fxSet(fxw, 'wrong', true); fxSet(nm, 'wrong', true); fig.classList.add('in'); return; }
  fxSet(fxw, 'wrong'); fxSet(nm, 'wrong');
  new IntersectionObserver((es, o) => {
    if (!es[0].isIntersecting) return;
    fig.classList.add('in'); o.disconnect();
    const t0 = performance.now(), step = now => { const t = clamp((now - t0) / 1600); cnt.textContent = (.08 * (1 - Math.pow(1 - t, 3))).toFixed(2); if (t < 1) requestAnimationFrame(step); };
    cnt.textContent = '0.00'; requestAnimationFrame(step);
  }, { threshold: .5 }).observe(fig);
  (async () => {
    for (;;) {
      await until(awake);
      fxSet(fxw, 'wrong'); fxSet(nm, 'wrong'); st.textContent = '0 suggestions'; st.parentElement.classList.add('clear');
      await sleep(1400);
      st.textContent = '2 suggestions'; st.parentElement.classList.remove('clear'); nm.classList.add('u'); await sleep(300); fxw.classList.add('u'); await sleep(1300);
      fxPlay(nm, { hold: 300 }); fxPlay(fxw, { hold: 300 }); await sleep(1500); st.textContent = '0 suggestions'; st.parentElement.classList.add('clear');
      await sleep(3600);
    }
  })();
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
const MODES = [
  { n: 'Original', d: 'Grammar, spelling and punctuation run in every mode.', t: 'hi john, i was wondering if maybe you could possibly send me that report whenever you get a chance, thanks alot' },
  { n: 'Fix', d: 'Small fixes. Same voice.', t: 'Hi John, I was wondering if maybe you could possibly send me that report whenever you get a chance. Thanks a lot.' },
  { n: 'Professional', d: 'Clear, composed, considered.', t: 'Hello John, could you please send me that report at your earliest convenience? Thank you.' },
  { n: 'Friendly', d: 'A little warmer. Still you.', t: 'Hi John! Could you send me that report when you get a chance? Thanks so much!' },
  { n: 'Concise', d: 'Fewer words. Full meaning.', t: 'Hi John, could you send me that report when you can? Thanks.' },
  { n: 'Direct', d: 'Get straight to the point.', t: 'John, please send me that report. Thanks.' },
];
function bento() {
  const tiles = $$('.bt');
  const run = n => {
    const target = +n.dataset.count;
    if (RM) { n.textContent = target; return; }
    const t0 = performance.now(), dur = 1500;
    const step = now => {
      const t = clamp((now - t0) / dur);
      n.textContent = t < 1 ? String(Math.floor(Math.random() * 9000) + 100).slice(0, Math.max(1, 4 - Math.floor(t * 3.4))) : target;
      if (t < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  };
  const o = new IntersectionObserver(es => es.forEach(e => {
    if (!e.isIntersecting) return;
    e.target.classList.add('in'); const n = $('.num', e.target); if (n) run(n); o.unobserve(e.target);
  }), { threshold: .25 });
  tiles.forEach((t, i) => {
    t.style.transitionDelay = ((i % 2) * 110) + 'ms';
    if (!RM) o.observe(t); else { t.classList.add('in'); const n = $('.num', t); if (n) n.textContent = n.dataset.count; }
    if (!COARSE && !RM) t.addEventListener('pointermove', e => { const r = t.getBoundingClientRect(); t.style.setProperty('--sx', (e.clientX - r.left) + 'px'); t.style.setProperty('--sy', (e.clientY - r.top) + 'px'); });
  });
  // modes tile: the same sentence in five voices
  const chips = $$('.mchip', $('#mchips')), text = $('#mtext'), detail = $('#mdetail'), awake = watch($('#mchips'));
  let cur = 1, touched = false;
  const show = i => {
    cur = i; text.textContent = '';
    MODES[i].t.split(' ').forEach((w, k, a) => { const s = document.createElement('span'); s.className = 'w'; s.style.setProperty('--i', k); s.textContent = w + (k < a.length - 1 ? ' ' : ''); text.append(s); });
    detail.textContent = MODES[i].d;
    chips.forEach(c => { c.classList.toggle('on', +c.dataset.i === i); c.setAttribute('aria-pressed', String(+c.dataset.i === i)); });
  };
  chips.forEach(c => c.addEventListener('click', () => { touched = true; show(+c.dataset.i); track('Writing mode viewed', { mode: c.textContent.trim() }); }));
  show(1);
  if (!RM) setInterval(() => { if (!touched && awake()) show(cur % 5 + 1); }, 3800);
}

/* ---------- 7. The real app: screenshots tilt with scroll (CSS reads --p) ---------- */
function real() { return { update() {} }; }

/* ---------- 6. Compatibility marquees: base drift plus scroll-velocity boost and skew ---------- */
const SV = { raw: 0, t: 0 }; // latest scroll velocity (px per ms) and when it was measured
function marquees() {
  if (RM) return;
  const rows = $$('.marquee').map(m => {
    const t = $('.track', m);
    Array.from(t.children).forEach(c => { const k = c.cloneNode(true); k.setAttribute('aria-hidden', 'true'); t.append(k); });
    return { m, t, dir: +m.dataset.dir || 1, secs: m.hasAttribute('data-slow') ? 64 : 46, x: 0, half: 1, vis: false, hold: false };
  });
  const measure = () => rows.forEach(r => { r.half = r.t.scrollWidth / 2 || 1; if (r.dir < 0 && !r.x) r.x = -r.half; });
  measure(); addEventListener('resize', measure); addEventListener('load', measure);
  const io = new IntersectionObserver(es => es.forEach(e => { const r = rows.find(r => r.m === e.target); r.vis = e.isIntersecting; go(); }), { rootMargin: '10% 0px' });
  rows.forEach(r => {
    io.observe(r.m);
    r.m.addEventListener('pointerenter', () => r.hold = true); r.m.addEventListener('pointerleave', () => r.hold = false);
    r.m.addEventListener('focusin', () => r.hold = true); r.m.addEventListener('focusout', () => r.hold = false);
  });
  let sm = 0, last = 0, on = false;
  const tick = now => {
    const dt = Math.min(48, now - (last || now)); last = now;
    const target = now - SV.t < 120 ? SV.raw : 0; // idle for 120 ms means the scroll has stopped
    sm = lerp(sm, target, target ? .18 : .06); // quick to react, slow to ease back
    const boost = 1 + clamp(Math.abs(sm) / 1.4) * 5.5, skew = clamp(sm / 2.4, -1, 1) * -6;
    let busy = false;
    for (const r of rows) {
      if (!r.vis) continue;
      busy = true;
      if (!r.hold) {
        r.x -= r.dir * (r.half / r.secs) * (dt / 1000) * boost;
        if (r.x <= -r.half) r.x += r.half; else if (r.x > 0) r.x -= r.half;
      }
      r.t.style.transform = `translate3d(${r.x.toFixed(2)}px,0,0) skewX(${skew.toFixed(2)}deg)`;
    }
    if (busy) requestAnimationFrame(tick); else { on = false; last = 0; }
  };
  function go() { if (!on) { on = true; requestAnimationFrame(tick); } }
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
  tabs.forEach((t, k) => t.addEventListener('click', () => { type(k); track('Code tab picked', { tab: t.textContent.trim() }); }));
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
    if (ok) track('Build commands copied');
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

/* ---------- Scroll effects: progress hairline, nav hide/show, iris transitions, velocity ---------- */
const fx = { y: scrollY, t: performance.now(), nav: scrollY, irises: [] };
function scrollFx() {
  const now = performance.now(), y = scrollY, vh = innerHeight;
  const prog = $('#progress');
  if (prog && !RM) prog.style.transform = `scaleX(${clamp(y / Math.max(1, root.scrollHeight - vh)).toFixed(4)})`;
  const dt = now - fx.t;
  if (dt > 0 && y !== fx.y) { SV.raw = (y - fx.y) / dt; SV.t = now; fx.y = y; fx.t = now; }
  const nv = $('#nav');
  if (nv && !RM) {
    const d = y - fx.nav; fx.nav = y;
    const menu = $('#nav-links')?.classList.contains('open');
    if (y < 90 || d < -6 || menu || nv.contains(document.activeElement) && nv.matches(':focus-within')) nv.classList.remove('hide');
    else if (d > 22) nv.classList.add('hide'); // fast scroll down
  }
  for (const z of fx.irises) { // circular iris: the pin opens from the middle of the screen as its section arrives
    const top = z.sec.getBoundingClientRect().top, e = clamp(1 - top / vh);
    if (e >= 1) { if (z.v !== 'none') { z.pin.style.clipPath = 'none'; z.v = 'none'; } continue; }
    // a disc that rises with the section, centred in the visible part of the pin, then blooms to cover the screen
    const fit = e * vh / 2, R = lerp(fit * .8, Math.hypot(innerWidth / 2, vh / 2), Math.pow(e, 3));
    const v = `circle(${R.toFixed(1)}px at 50% ${fit.toFixed(1)}px)`;
    if (v !== z.v) { z.pin.style.clipPath = v; z.v = v; }
  }
}
function irisInit() {
  $$('.pin.iris').forEach(pin => fx.irises.push({ pin, sec: pin.closest('section'), v: '' }));
}

/* ---------- Reveals: H2 lines clip up from below, eyebrows fade and slide in ---------- */
function reveals() {
  if (RM) return;
  const heads = $$('.h2');
  const split = h => {
    const sec = h.closest('section'), cv = sec.style.contentVisibility;
    sec.style.contentVisibility = 'visible'; // sections that skip rendering must be laid out to be measured
    h.classList.remove('split'); h.innerHTML = h._src;
    const units = [], nodes = [];
    Array.from(h.childNodes).forEach(n => {
      if (n.nodeType === 3) n.textContent.split(/\s+/).filter(Boolean).forEach(w => { const u = document.createElement('span'); u.textContent = w; units.push(u); nodes.push(u, ' '); });
      else if (n.nodeType === 1) { nodes.push(n, ' '); if (n.tagName !== 'BR') units.push(n); } // keep the authored <br class="lg"> so measured lines match
    });
    h.replaceChildren(...nodes);
    const lines = [], ys = [];
    units.forEach(u => { const y = Math.round(u.offsetTop / 8); const k = ys.indexOf(y); if (k < 0) { ys.push(y); lines.push([u]); } else lines[k].push(u); });
    h.replaceChildren();
    lines.forEach((l, i) => {
      const ln = document.createElement('span'), inn = document.createElement('span');
      ln.className = 'ln'; inn.className = 'ln-i'; inn.style.setProperty('--i', i);
      l.forEach((u, k) => { if (k) inn.append(' '); inn.append(u); });
      ln.append(inn); h.append(ln, ' ');
    });
    h.classList.add('split'); sec.style.contentVisibility = cv;
  };
  heads.forEach(h => { h._src = h.innerHTML; split(h); });
  let w = innerWidth;
  addEventListener('resize', () => { if (innerWidth === w) return; w = innerWidth; heads.forEach(split); });
  const io = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) { e.target.classList.add('rv'); io.unobserve(e.target); } }), { threshold: .25, rootMargin: '0px 0px -6% 0px' });
  heads.forEach(h => io.observe(h));
  $$('.eyebrow').forEach(e => io.observe(e));
}

/* ---------- Magnetic buttons: a damped spring toward the pointer, 6px at most ---------- */
function magnetic() {
  if (RM || COARSE) return;
  const S = new Map(); let run = false;
  const step = () => {
    let busy = false;
    S.forEach((s, el) => {
      s.vx = (s.vx + (s.tx - s.x) * .2) * .74; s.vy = (s.vy + (s.ty - s.y) * .2) * .74;
      s.x += s.vx; s.y += s.vy;
      const rest = Math.abs(s.tx - s.x) + Math.abs(s.ty - s.y) + Math.abs(s.vx) + Math.abs(s.vy) < .02;
      if (rest && !s.tx && !s.ty) { el.style.translate = ''; S.delete(el); return; }
      el.style.translate = `${s.x.toFixed(2)}px ${s.y.toFixed(2)}px`; busy = true;
    });
    if (busy) requestAnimationFrame(step); else run = false;
  };
  const kick = (el, tx, ty) => {
    const s = S.get(el) || { x: 0, y: 0, vx: 0, vy: 0 }; s.tx = tx; s.ty = ty; S.set(el, s);
    if (!run) { run = true; requestAnimationFrame(step); }
  };
  $$('.btn, .pill').forEach(el => {
    el.addEventListener('pointermove', e => {
      if (e.pointerType === 'touch') return;
      const r = el.getBoundingClientRect();
      kick(el, clamp((e.clientX - r.left - r.width / 2) / (r.width / 2), -1, 1) * 6, clamp((e.clientY - r.top - r.height / 2) / (r.height / 2), -1, 1) * 6);
    });
    el.addEventListener('pointerleave', () => { if (S.has(el)) kick(el, 0, 0); });
  });
}

/* ---------- Anchors: smooth scroll that lands exactly on the section top, below the fixed nav ---------- */
function anchors() {
  addEventListener('click', e => {
    const a = e.target.closest && e.target.closest('a[href^="#"]');
    if (!a || e.defaultPrevented || e.metaKey || e.ctrlKey || e.shiftKey || e.button) return;
    const id = a.getAttribute('href').slice(1), t = id ? document.getElementById(id) : document.body;
    if (!t) return;
    e.preventDefault();
    const go = () => t.getBoundingClientRect().top + scrollY + (t.matches('.pinned,.hero') || !id ? 1 : 0);
    scrollTo({ top: go(), behavior: RM ? 'auto' : 'smooth' });
    // the prototype method skips Rybbit's patched pushState, so an in-page jump is not counted as a new pageview
    if (id) History.prototype.pushState.call(history, null, '', '#' + id);
    // sections that skip rendering change height while we scroll past them, so correct once we arrive
    const fix = () => { const d = go() - scrollY; if (Math.abs(d) > 3) scrollTo({ top: go(), behavior: 'auto' }); };
    if ('onscrollend' in window) addEventListener('scrollend', fix, { once: true }); else setTimeout(fix, 1200);
  });
}

/* ---------- Footer wordmark: types "Prazr", underlines it, then the r and a trade places ---------- */
function wordmark() {
  const m = $('#mk'), inn = $('#mk-in'); if (!m) return;
  const fit = () => { // size the wordmark so it spans the viewport edge to edge, whatever the font
    m.style.setProperty('--mk-fs', '100px');
    const w = inn.offsetWidth; if (w) m.style.setProperty('--mk-fs', (100 * (m.clientWidth - 2 * Math.max(8, innerWidth * .012)) / w).toFixed(2) + 'px');
  };
  fit(); addEventListener('resize', fit);
  if (RM) return;
  const L = $$('.mk-l', inn), order = [0, 2, 1, 3, 4]; // typing order of P r a z r
  L.forEach((l, i) => l.style.setProperty('--ti', order.indexOf(i)));
  const swap = () => { m.style.setProperty('--sa', L[2].offsetWidth + 'px'); m.style.setProperty('--sr', -L[1].offsetWidth + 'px'); };
  swap(); addEventListener('resize', swap);
  m.classList.add('pre', 'typo');
  new IntersectionObserver(async (es, o) => {
    if (!es[0].isIntersecting) return;
    o.disconnect(); swap();
    m.classList.remove('pre'); await sleep(900);
    m.classList.add('u'); await sleep(1300);
    m.classList.add('fix'); await sleep(1100);
    m.classList.remove('typo');
    await sleep(2200); m.classList.remove('fix', 'u');
  }, { threshold: .4 }).observe(m);
}

/* ---------- Nav ---------- */
function nav() {
  const t = $('.nav-toggle'), l = $('#nav-links');
  t.addEventListener('click', () => { const o = l.classList.toggle('open'); t.setAttribute('aria-expanded', String(o)); if (o) track('Mobile menu opened'); });
  l.addEventListener('click', e => { if (e.target.closest('a')) { l.classList.remove('open'); t.setAttribute('aria-expanded', 'false'); } });
  addEventListener('keydown', e => { if (e.key === 'Escape' && l.classList.contains('open')) { l.classList.remove('open'); t.setAttribute('aria-expanded', 'false'); t.focus(); } });
}

/* ---------- Analytics: one "Section viewed" per section per page view ---------- */
const SECTIONS = { top: 'Hero', try: 'Try it', how: 'How it works', names: 'Names', privacy: 'Privacy', features: 'Features', showcase: 'Showcase', works: 'Compatibility', open: 'Open source', download: 'Download', foot: 'Footer' };
function sectionViews() {
  // pinned scenes are several screens tall, so watch their sticky child, and count a section once half the screen is filled by it
  const o = new IntersectionObserver(es => es.forEach(e => {
    if (!e.isIntersecting || e.intersectionRatio < .5 && e.intersectionRect.height < innerHeight * .5) return;
    o.unobserve(e.target); track('Section viewed', { section: SECTIONS[e.target.closest('[id]').id] });
  }), { threshold: [0, .1, .2, .3, .4, .5, .6, .7, .8, .9, 1] });
  Object.keys(SECTIONS).forEach(id => { const el = document.getElementById(id); if (el) o.observe($('.pin', el) || el); });
}

/* ---------- 404 ---------- */
function notFound() {
  const el = $('.nf .fx'); if (!el) return;
  track('Page not found', { path: location.pathname });
  fxInit(el);
  if (RM) { fxSet(el, 'right'); el.classList.add('done'); return; }
  fxSet(el, 'wrong');
  setTimeout(() => el.classList.add('u'), 300);
  setTimeout(() => fxPlay(el, { hold: 300 }), 1000);
}

/* ---------- Boot ---------- */
function boot() {
  if ($('.nav-toggle')) nav();
  reveals(); magnetic(); anchors(); wordmark();
  notFound();
  const mods = { hero, demo, privacy, showcase: real, real, final };
  $$('[data-scene]').forEach(el => {
    const name = el.dataset.scene;
    const mod = mods[name] ? mods[name](el) : { update() {} };
    register(el, mod);
  });
  if ($('#try')) tryIt($('#try'));
  if ($('#names')) names($('#names'));
  if ($('#bento')) { bento(); marquees(); openSource(); sectionViews(); }
  if (!RM) irisInit();
  if (!RM) { addEventListener('scroll', schedule, { passive: true }); addEventListener('resize', () => { scenes.forEach(s => s.p = -1); schedule(); }); }
  frame();
}
if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();
