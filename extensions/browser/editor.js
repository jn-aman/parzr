/* Shared DOM capabilities. Highlighting never mutates the host's text. */
(() => {
  'use strict';
  const blocked = '[data-private],[data-parzr-ignore],[aria-disabled="true"],[aria-readonly="true"],[autocomplete="current-password"],[autocomplete="new-password"],[autocomplete="one-time-code"]';
  function parent(e) { return e.parentElement || e.getRootNode()?.host; }
  function privateField(element) {
    for (let e = element; e; e = parent(e)) if (e.matches?.(blocked) || e.matches?.('input[type="password"]')) return true;
    return false;
  }
  function find(element) {
    if (!(element instanceof Element) || privateField(element)) return;
    if (element instanceof HTMLTextAreaElement || element instanceof HTMLInputElement && ['text','search'].includes(element.type)) {
      return !element.disabled && !element.readOnly && element.getClientRects().length ? element : undefined;
    }
    let root;
    for (let e = element; e; e = e.parentElement) {
      if (e.hasAttribute('contenteditable')) {
        if (e.getAttribute('contenteditable').toLowerCase() === 'false') return root;
        if (['','true','plaintext-only'].includes(e.getAttribute('contenteditable').toLowerCase())) root = e;
      }
    }
    return root?.isContentEditable && root.getClientRects().length ? root : undefined;
  }
  function active() {
    let e = document.activeElement;
    while (e?.shadowRoot?.activeElement) e = e.shadowRoot.activeElement;
    return find(e);
  }
  function selection(root) { return root.getRootNode().getSelection?.() || window.getSelection(); }
  const protectedSelector = 'a,code,pre,[contenteditable="false"],[data-mention],[data-entity-type="mention"],img';
  const blockSelector = 'p,div,li,blockquote,h1,h2,h3,h4,h5,h6';
  function richModel(root) {
    let text = ''; const segments = [], protectedRanges = [];
    function add(value, node, kind, protect) {
      const start = text.length; text += value; segments.push({start, end: text.length, node, kind});
      if (protect && value.length) protectedRanges.push({start_utf16: start, end_utf16: text.length});
    }
    function walk(node, protect = false) {
      if (node.nodeType === Node.TEXT_NODE) { add(node.data, node, 'text', protect); return; }
      if (node.nodeType !== Node.ELEMENT_NODE) return;
      if (node.matches('script,style,[hidden],[aria-hidden="true"]')) return;
      protect ||= node !== root && node.matches(protectedSelector);
      if (node.tagName === 'BR') { add('\n', node, 'break', true); return; }
      if (node.tagName === 'IMG') { add('\uFFFC', node, 'object', true); return; }
      for (const child of node.childNodes) walk(child, protect);
      if (node !== root && node.matches(blockSelector) && text && !text.endsWith('\n')) add('\n', node, 'block', true);
    }
    walk(root);
    while (segments.at(-1)?.kind === 'block') { text = text.slice(0,-1); segments.pop(); protectedRanges.pop(); }
    function nodeRange(segment) {
      const r = document.createRange();
      if (segment.kind === 'text') r.selectNodeContents(segment.node); else r.selectNode(segment.node);
      return r;
    }
    function point(offset, end = false) {
      if (offset < 0 || offset > text.length) throw new Error('Invalid editor offset.');
      const s = segments.find(s => s.kind === 'text' && (end ? offset > s.start && offset <= s.end : offset >= s.start && offset < s.end));
      if (s) return [s.node, offset - s.start];
      const boundary = segments.find(s => end ? s.end === offset : s.start === offset);
      if (boundary) { const r = nodeRange(boundary); r.collapse(!end); return [r.startContainer, r.startOffset]; }
      if (offset === text.length) return [root, root.childNodes.length];
      if (offset === 0) return [root,0];
      throw new Error('This editor hides its text ranges.');
    }
    function range(start, end) {
      const r = document.createRange(); r.setStart(...point(start));
      if (start === end) r.collapse(true); else r.setEnd(...point(end,true));
      return r;
    }
    function offset(node,index) {
      const direct = segments.find(s => s.kind === 'text' && s.node === node);
      if (direct) return direct.start + index;
      const caret = document.createRange(); caret.setStart(node,index); caret.collapse(true);
      let result = 0;
      for (const segment of segments) {
        const r = nodeRange(segment);
        if (caret.compareBoundaryPoints(Range.START_TO_END,r) >= 0) result = segment.end; else break;
      }
      return result;
    }
    return {text, segments, protectedRanges, range, offset};
  }
  function capture(root, selectedOnly = false) {
    if (!root || find(root) !== root || !root.isConnected) throw new Error('Focus an editable writing field.');
    const input = root instanceof HTMLInputElement || root instanceof HTMLTextAreaElement;
    const model = input ? null : richModel(root), fullText = input ? root.value : model.text;
    if (new TextEncoder().encode(fullText).length > 262144) throw new Error('This draft is too large for inline checking. Select a smaller passage.');
    let a,b;
    if (input) { a = root.selectionStart; b = root.selectionEnd; }
    else {
      const s = selection(root);
      if (s?.rangeCount === 1 && root.contains(s.anchorNode) && root.contains(s.focusNode)) {
        const r = s.getRangeAt(0); a = model.offset(r.startContainer,r.startOffset); b = model.offset(r.endContainer,r.endOffset);
      } else a = b = fullText.length;
    }
    if (!Number.isInteger(a) || !Number.isInteger(b)) throw new Error('This field hides its selection.');
    const caret = a;
    const selected = a !== b;
    if (selectedOnly && !selected) throw new Error('Select the words you want to improve.');
    if (!selected) { a = fullText.lastIndexOf('\n',Math.max(0,a-1)) + 1; b = fullText.indexOf('\n',b); if (b < 0) b = fullText.length; }
    const text = fullText.slice(a,b);
    if (new TextEncoder().encode(text).length > (selected ? 65536 : 8000) || !text.trim()) throw new Error('Select a shorter passage to check.');
    const source = input ? fullText : root.innerHTML;
    const ranges = (model?.protectedRanges || []).filter(r => r.end_utf16 > a && r.start_utf16 < b).map(r => ({start_utf16: Math.max(a,r.start_utf16)-a, end_utf16: Math.min(b,r.end_utf16)-a}));
    const prefix = fullText.slice(0,a).replace(/[ \t]+$/,'');
    function valid() { return root.isConnected && find(root) === root && (input ? root.value : root.innerHTML) === source; }
    function validate(result) {
      if (!Array.isArray(result?.edits) || typeof result.text !== 'string') throw new Error('Invalid edit plan.');
      let end = 0, previous = -1;
      const boundary = n => !(n > 0 && n < text.length && /[\uD800-\uDBFF]/.test(text[n-1]) && /[\uDC00-\uDFFF]/.test(text[n]));
      for (const e of result.edits) {
        if (!Number.isInteger(e.start_utf16) || !Number.isInteger(e.end_utf16) || e.start_utf16 < end || e.start_utf16 === previous || e.end_utf16 < e.start_utf16 || e.end_utf16 > text.length || !boundary(e.start_utf16) || !boundary(e.end_utf16) || typeof e.replacement !== 'string' || text.slice(e.start_utf16,e.end_utf16) !== e.original) throw new Error('Invalid edit range.');
        if (ranges.some(r => e.start_utf16 === e.end_utf16 ? e.start_utf16 > r.start_utf16 && e.start_utf16 < r.end_utf16 : e.start_utf16 < r.end_utf16 && e.end_utf16 > r.start_utf16)) throw new Error('A correction would change protected formatting.');
        end = e.end_utf16; previous = e.start_utf16;
      }
      let output = text; for (const e of [...result.edits].reverse()) output = output.slice(0,e.start_utf16) + e.replacement + output.slice(e.end_utf16);
      if (output !== result.text) throw new Error('Inconsistent edit plan.');
    }
    function apply(result) {
      validate(result);
      if (!valid()) throw new Error('Your text changed. Close Parzr and select it again.');
      root.focus({preventScroll: true}); let expected = fullText;
      if (input) {
        root.setSelectionRange(a,b);
        if (!root.dispatchEvent(new InputEvent('beforeinput',{bubbles:true,composed:true,cancelable:true,inputType:'insertReplacementText',data:result.text}))) throw new Error('The editor refused replacement. Copy the result instead.');
        if (!document.execCommand('insertText',false,result.text)) throw new Error('This editor needs its extension. Copy the result instead.');
        expected = fullText.slice(0,a) + result.text + fullText.slice(b);
        if (root.value !== expected) throw new Error('The editor did not confirm replacement. Use Undo if needed.');
      } else {
        for (const e of [...result.edits].reverse()) {
          const now = richModel(root);
          if (now.text !== expected) throw new Error('The editor changed during replacement. Use Undo to revert earlier changes.');
          const r = now.range(a+e.start_utf16,a+e.end_utf16); let replacement = e.replacement;
          if (r.toString() !== e.original) throw new Error('The editor reports inconsistent ranges. Copy the result instead.');
          if (replacement && r.startContainer === r.endContainer && r.startContainer.nodeType === Node.TEXT_NODE && r.startOffset === 0 && r.startContainer.parentElement !== root) {
            replacement += r.endContainer.data.slice(r.endOffset); r.setEnd(r.endContainer,r.endContainer.length);
          }
          const s = selection(root); s.removeAllRanges(); s.addRange(r);
          if (!root.dispatchEvent(new InputEvent('beforeinput',{bubbles:true,composed:true,cancelable:true,inputType:'insertReplacementText',data:replacement}))) throw new Error('The editor refused replacement. Use Undo to revert earlier changes.');
          if (!document.execCommand(replacement ? 'insertText' : 'delete',false,replacement)) throw new Error('The editor refused a range edit. Use Undo if needed.');
          expected = expected.slice(0,a+e.start_utf16) + e.replacement + expected.slice(a+e.end_utf16);
        }
        if (richModel(root).text !== expected) throw new Error('The editor did not confirm replacement. Use Undo if needed.');
      }
      if (!selected) {
        const original = caret - a; let moved = caret;
        for (const e of result.edits) {
          if (original >= e.end_utf16) moved += e.replacement.length - (e.end_utf16 - e.start_utf16);
          else if (original > e.start_utf16) { moved += e.start_utf16 - original + e.replacement.length; break; }
        }
        moved = Math.max(0,Math.min(moved,expected.length));
        if (input) root.setSelectionRange(moved,moved);
        else { const s = selection(root), r = richModel(root).range(moved,moved); s.removeAllRanges(); s.addRange(r); }
      }
    }
    function rects(start,end) {
      if (!valid()) return [];
      if (start === end) {
        if (start < text.length) end = start + (text.codePointAt(start) > 65535 ? 2 : 1);
        else if (start > 0) start -= /[\uDC00-\uDFFF]/.test(text[start-1]) ? 2 : 1;
      }
      if (!input) return [...model.range(a+start,a+Math.max(start,end)).getClientRects()];
      const box = root.getBoundingClientRect(), css = getComputedStyle(root), mirror = document.createElement('div');
      for (const key of ['fontFamily','fontSize','fontWeight','fontStyle','lineHeight','letterSpacing','wordSpacing','textIndent','textTransform','direction','tabSize','paddingTop','paddingRight','paddingBottom','paddingLeft','borderTopWidth','borderRightWidth','borderBottomWidth','borderLeftWidth','boxSizing']) mirror.style[key] = css[key];
      Object.assign(mirror.style,{position:'fixed',left:`${box.left}px`,top:`${box.top}px`,width:`${root.offsetWidth}px`,visibility:'hidden',pointerEvents:'none',whiteSpace:root instanceof HTMLTextAreaElement ? 'pre-wrap' : 'pre',overflowWrap:'break-word',borderStyle:'solid'});
      const node = document.createTextNode(fullText+'\u200b'); mirror.append(node); document.documentElement.append(mirror);
      const r = document.createRange(); r.setStart(node,a+start); r.setEnd(node,a+Math.max(start+1,end));
      const measured = [...r.getClientRects()].map(r => ({left:r.left-root.scrollLeft,right:r.right-root.scrollLeft,top:r.top-root.scrollTop,bottom:r.bottom-root.scrollTop,width:r.width,height:r.height}));
      mirror.remove(); return measured;
    }
    return {root,text,selected,protectedRanges:ranges,sentenceStart:!prefix || /[.!?\n]$/.test(prefix),sentenceEnd:b === fullText.length || /[.!?\n]\s*$/.test(text),valid,validate,apply,rects};
  }
  globalThis.__parzrEditors = {find,active,capture};
})();
