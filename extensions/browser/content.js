(() => {
  'use strict';
  if (globalThis.__parzrInline) { globalThis.__parzrInline.invoke(); return; }
  const editors = globalThis.__parzrEditors;
  if (!editors) return;
  let timer, generation = 0, composing = false, session, panel, panelRoot, paused = false, watched, wordClick;
  const mutations = new MutationObserver(() => schedule(watched));
  const listeners = new AbortController();
  const marks = document.createElement('div'); marks.id = 'parzr-inline-marks';
  marks.style.cssText = 'position:fixed;inset:0;z-index:2147483646;pointer-events:none';
  const marksShadow = marks.attachShadow({mode:'closed'});
  const markStyle = document.createElement('style'); markStyle.textContent = '.mark{position:absolute;padding:0;border:0;border-bottom:2px dotted #24754d;background:transparent;pointer-events:auto;cursor:pointer;border-radius:1px}.mark:hover,.mark:focus-visible{border-color:#24754d;outline:2px solid #a8ecc455;outline-offset:1px}@media(prefers-color-scheme:dark){.mark,.mark:hover,.mark:focus-visible{border-color:#a8ecc4}}'; marksShadow.append(markStyle);
  document.documentElement.append(marks);
  const css = `
:host{color-scheme:light dark;--ink:#233029;--muted:#65756d;--card:#f8f9f6;--well:#fff;--line:#22302820;--accent:#24754d;--on-accent:#fff;--hover:#2030290b;--error:#8c601d}
*{box-sizing:border-box}section{font:13px/1.45 -apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;color:var(--ink);background:var(--card);border:1px solid var(--line);border-radius:12px;box-shadow:0 8px 28px #0003;padding:12px}
header,footer{display:flex;align-items:center;justify-content:space-between;gap:8px}header{margin-bottom:10px}strong{font-size:14px;letter-spacing:-.3px}small,.notice{font-size:11px;color:var(--muted)}
button{font:inherit;border:0;background:transparent;color:inherit;border-radius:6px;padding:6px 8px;cursor:pointer;transition:background 120ms,transform 120ms cubic-bezier(.23,1,.32,1)}button:hover{background:var(--hover)}button:active{transform:scale(.97)}button:focus-visible{outline:2px solid var(--accent);outline-offset:2px}button:disabled{opacity:.45;cursor:default}.apply,button[aria-pressed=true]{background:var(--accent);color:var(--on-accent);font-weight:600}.apply:hover{filter:brightness(1.08)}
nav{display:flex;flex-wrap:wrap;gap:2px;margin-bottom:10px}nav button{font-size:11px;padding:5px 7px}pre{font:14px/1.45 -apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;white-space:pre-wrap;overflow:auto;max-height:115px;margin:8px 0 10px;padding:10px;background:var(--well);border-radius:7px}.sentence{font-size:12px;max-height:88px}
footer{margin-top:10px;padding-top:9px;border-top:1px solid var(--line)}.error{color:var(--error)}.replacement{font-size:17px;color:var(--accent);overflow-wrap:anywhere;margin:8px 0}.original{font-size:12px;color:var(--muted);text-decoration:line-through;overflow-wrap:anywhere}.reason{font-size:11px;color:var(--muted);margin:8px 0}details{font-size:11px;color:var(--muted)}ul{padding-left:15px;max-height:90px;overflow:auto}
@media(prefers-color-scheme:dark){:host{--ink:#edf3ef;--muted:#aebbb5;--card:#24292b;--well:#1e2325;--line:#ffffff1b;--accent:#a8ecc4;--on-accent:#172b21;--hover:#ffffff10;--error:#e5bc77}}
@media(prefers-reduced-motion:reduce){button{transition:none;transform:none}}`
  function button(text,action) { const b = document.createElement('button'); b.type = 'button'; b.textContent = text; b.addEventListener('click',action); return b; }
  function closePanel() { panel?.remove(); panel = undefined; panelRoot = undefined; }
  function clear() { generation++; clearTimeout(timer); session = undefined; marksShadow.querySelectorAll('button').forEach(b => b.remove()); closePanel(); }
  function mount(snapshot,width = 300,anchor) {
    closePanel();
    const host = document.createElement('div'); host.id = 'parzr-local-panel'; host.style.cssText = `position:fixed;z-index:2147483647;width:${width}px;max-width:calc(100vw - 16px)`;
    const shadow = host.attachShadow({mode:'closed'}), style = document.createElement('style'); style.textContent = css; shadow.append(style);
    const section = document.createElement('section'); section.setAttribute('role','dialog'); section.setAttribute('aria-label','Parzr writing suggestions');
    const header = document.createElement('header'), brand = document.createElement('strong'); brand.textContent = 'Parzr';
    const local = document.createElement('small'); local.textContent = 'On your Mac';
    header.append(brand,local,button('Close',closePanel)); section.append(header); shadow.append(section);
    host.addEventListener('keydown',e => { if (e.key === 'Escape') { e.stopPropagation(); closePanel(); snapshot?.root.focus({preventScroll:true}); } });
    document.documentElement.append(host); panel = host; panelRoot = snapshot?.root;
    const box = anchor || snapshot?.root.getBoundingClientRect() || {left:innerWidth-width-16,bottom:16,top:16};
    function place() {
      host.style.left = `${Math.max(8,Math.min(box.left,innerWidth-host.offsetWidth-8))}px`;
      host.style.top = `${Math.max(8,Math.min(box.bottom+5,innerHeight-host.offsetHeight-8))}px`;
    }
    place(); return {host,section,place};
  }
  async function request(snapshot,mode = 'fix',deep = false) {
    const result = await (globalThis.browser || chrome).runtime.sendMessage({type:'parzr-rewrite',request:{text:snapshot.text,mode,deep,dictionary:['Parzr'],protected_ranges:snapshot.protectedRanges,sentence_start:snapshot.sentenceStart,sentence_end:snapshot.sentenceEnd}});
    if (result?.error) throw new Error(result.error);
    snapshot.validate(result); return result;
  }
  function feedback(section,error) {
    const status = section.querySelector('[aria-live]') || document.createElement('div'); status.setAttribute('aria-live','polite'); status.className = 'error'; status.textContent = error.message; section.append(status);
  }
  function selectedPanel(snapshot) {
    const {host,section,place} = mount(snapshot);
    const nav = document.createElement('nav'); nav.setAttribute('aria-label','Writing style');
    const preview = document.createElement('pre'); preview.textContent = snapshot.text;
    const status = document.createElement('div'); status.setAttribute('aria-live','polite');
    const details = document.createElement('details'), summary = document.createElement('summary'), reasons = document.createElement('ul'); summary.textContent = 'Changes'; details.append(summary,reasons);
    const footer = document.createElement('footer');
    const copy = button('Copy result',async () => { try { await navigator.clipboard.writeText(preview.textContent); status.textContent = 'Copied'; } catch { status.textContent = 'Select and copy the preview.'; } });
    let result,run = 0;
    const apply = button('Fix all',() => { try { if (result) snapshot.apply(result); clear(); schedule(snapshot.root); } catch (error) { apply.disabled = true; feedback(section,error); place(); } }); apply.className = 'apply'; apply.disabled = true;
    footer.append(copy,apply); section.append(nav,preview,status,details,footer);
    async function analyze(mode) {
      const current = ++run; result = undefined; apply.disabled = true; status.className = ''; status.textContent = 'Checking locally…'; reasons.replaceChildren();
      for (const b of nav.children) b.setAttribute('aria-pressed',b.textContent.toLowerCase() === mode ? 'true' : 'false');
      apply.textContent = mode === 'fix' ? 'Fix all' : 'Apply changes'; place();
      try {
        const response = await request(snapshot,mode,true);
        if (panel !== host || run !== current) return;
        result = response; preview.textContent = result.text;
        status.textContent = result.edits.length ? `${result.edits.length} corrections` : 'No changes needed.';
        if (result.warnings?.length) status.textContent += ` · ${result.warnings.join(' ')}`;
        for (const edit of result.edits) { const li = document.createElement('li'); li.textContent = `${edit.original || 'Insert'} → ${edit.replacement || 'Remove'} · ${edit.explanation || 'Correction'}`; reasons.append(li); }
        apply.disabled = !result.edits.length;
      } catch (error) { if (panel === host && run === current) feedback(section,error); }
      place();
    }
    for (const mode of ['Fix','Professional','Friendly','Concise','Direct']) nav.append(button(mode,() => analyze(mode.toLowerCase())));
    analyze('fix');
  }
  function groupFor(result,edit) {
    return edit.group_id ? result.edits.filter(e => e.group_id === edit.group_id) : [edit];
  }
  function sentenceFor(result, edit) {
    const shift = result.edits.filter(e => e !== edit && e.end_utf16 <= edit.start_utf16).reduce((n,e) => n + e.replacement.length - (e.end_utf16 - e.start_utf16),0);
    const offset = Math.max(0,Math.min(result.text.length - 1,edit.start_utf16 + shift));
    if (typeof Intl.Segmenter !== 'function') return result.text;
    const sentences = [...new Intl.Segmenter('en',{granularity:'sentence'}).segment(result.text)];
    return (sentences.find(s => offset >= s.index && offset < s.index+s.segment.length)?.segment || result.text).trim();
  }
  function correction(snapshot,result,edit,anchor) {
    const {section,place} = mount(snapshot,260,anchor);
    const original = document.createElement('div'); original.className = 'original'; original.textContent = edit.original || 'Missing punctuation';
    const replacement = document.createElement('div'); replacement.className = 'replacement'; replacement.textContent = edit.replacement || 'Remove';
    const reason = document.createElement('p'); reason.className = 'reason'; reason.textContent = edit.explanation || 'Suggested correction';
    const sentence = document.createElement('pre'); sentence.className = 'sentence'; sentence.setAttribute('aria-label','Corrected sentence preview'); sentence.textContent = sentenceFor(result,edit);
    const footer = document.createElement('footer');
    footer.append(button('Fix all',() => selectedPanel(snapshot)),button('Apply suggestion',() => {
      try {
        const edits = groupFor(result,edit); let text = snapshot.text;
        for (const e of [...edits].reverse()) text = text.slice(0,e.start_utf16) + e.replacement + text.slice(e.end_utf16);
        snapshot.apply({text,edits}); clear(); schedule(snapshot.root);
      } catch (error) { feedback(section,error); place(); }
    })); footer.lastChild.className = 'apply'; section.append(original,replacement,reason,sentence,footer); place();
  }
  function draw() {
    marksShadow.querySelectorAll('button').forEach(b => b.remove());
    if (!session || !session.snapshot.valid() || document.hidden) return;
    const {snapshot,result} = session, bounds = snapshot.root.getBoundingClientRect(); let count = 0;
    for (const edit of result.edits) {
      for (const r of snapshot.rects(edit.start_utf16,edit.end_utf16)) {
        if (++count > 80) return;
        const left = Math.max(r.left,bounds.left,0), right = Math.min(r.right,bounds.right,innerWidth), bottom = Math.min(r.bottom,bounds.bottom,innerHeight);
        if (right <= left || r.bottom < bounds.top || r.top > bounds.bottom || r.bottom > innerHeight || r.bottom < 0) continue;
        const mark = button('',() => correction(snapshot,result,edit,r)); mark.className = 'mark';
        mark.setAttribute('aria-label',`${edit.original || 'Missing punctuation'}: ${edit.replacement || 'Remove'}`); mark.title = mark.getAttribute('aria-label');
        mark.style.cssText = `left:${left}px;top:${bottom-5}px;width:${Math.max(3,right-left)}px;height:7px`;
        mark.addEventListener('pointerdown',e => e.preventDefault()); marksShadow.append(mark);
      }
    }
  }
  function schedule(root = editors.active()) {
    if (watched !== root) {
      mutations.disconnect(); watched = root;
      if (root) mutations.observe(root,{subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:['contenteditable','readonly','disabled','aria-readonly','aria-disabled','data-private','data-parzr-ignore']});
    }
    clear(); if (paused || composing || document.hidden || !root) return;
    const current = generation;
    timer = setTimeout(async () => {
      let snapshot;
      try {
        snapshot = editors.capture(root);
        if (snapshot.selected) { if (current === generation) selectedPanel(snapshot); return; }
        const result = await request(snapshot);
        if (current !== generation || !snapshot.valid() || composing || document.hidden || editors.active() !== root) return;
        session = {snapshot,result}; draw();
      } catch (error) {
        if (snapshot && current === generation && snapshot.valid() && editors.active() === root) {
          const {section,place} = mount(snapshot,260); feedback(section,error); section.append(button('Retry',() => schedule(root))); place();
        }
      }
    },90);
  }
  function invoke() {
    paused = false;
    const root = editors.active(); if (!root) return;
    try { const snapshot = editors.capture(root); if (snapshot.selected) { clear(); selectedPanel(snapshot); } else schedule(root); }
    catch { schedule(root); }
  }
  function on(type,action,options = {}) { document.addEventListener(type,action,{...options,signal:listeners.signal}); }
  on('pointerdown',event => {
    wordClick = undefined;
    if (event.button !== 0 || !session || editors.find(event.composedPath()[0]) !== session.snapshot.root) return;
    const {snapshot,result} = session;
    for (const edit of result.edits) {
      const rect = snapshot.rects(edit.start_utf16,edit.end_utf16).find(r => event.clientX >= r.left && event.clientX <= r.right && event.clientY >= r.top && event.clientY <= r.bottom);
      if (rect) { wordClick = {snapshot,result,edit,rect}; break; }
    }
  },{capture:true});
  on('pointerup',event => {
    const clicked = wordClick; wordClick = undefined;
    if (event.button !== 0 || !clicked || composing || document.hidden) return;
    const {snapshot,result,edit,rect} = clicked;
    if (!snapshot.valid() || editors.active() !== snapshot.root) return;
    clear(); correction(snapshot,result,edit,rect);
  },{capture:true});
  on('input',event => { if (!event.composedPath().includes(panel)) { paused = false; schedule(editors.find(event.composedPath()[0])); } },{capture:true});
  on('focusin',event => { if (!event.composedPath().includes(panel)) schedule(editors.find(event.composedPath()[0])); },{capture:true});
  on('compositionstart',() => { composing = true; clear(); },{capture:true});
  on('compositionend',event => { composing = false; schedule(editors.find(event.composedPath()[0])); },{capture:true});
  on('selectionchange',() => { if (!panel) schedule(); });
  on('scroll',() => { closePanel(); draw(); },{capture:true,passive:true});
  on('visibilitychange',() => { if (document.hidden) clear(); else schedule(); });
  on('keydown',e => { if (e.key === 'Escape') { const root = panelRoot || editors.active(); clear(); paused = true; root?.focus({preventScroll:true}); } },{capture:true});
  window.addEventListener('resize',() => { closePanel(); draw(); },{signal:listeners.signal});
  window.addEventListener('pagehide',() => { clear(); listeners.abort(); mutations.disconnect(); marks.remove(); delete globalThis.__parzrInline; },{once:true});
  globalThis.__parzrInline = {invoke}; invoke();
})();
