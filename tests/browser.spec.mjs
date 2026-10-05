import {test,expect} from '@playwright/test';
import {readFileSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
const script=readFileSync('extensions/browser/editor.js','utf8')+'\n'+readFileSync('extensions/browser/content.js','utf8');
async function setup(page,html){
 await page.setContent(html);
 await page.exposeFunction('parzrEngine',request=>{
  const response=spawnSync('engine/target/release/parzr-engine',[],{input:JSON.stringify(request)+'\n',encoding:'utf8',timeout:180000});
  if(response.status!==0)throw new Error('Test engine did not run.');return JSON.parse(response.stdout.trim());
 });
 await page.evaluate(()=>{
  window.chrome={runtime:{sendMessage:async ({request})=>{
   window.__parzrCalls=(window.__parzrCalls||0)+1; (window.__parzrRequests ||= []).push(request); return window.parzrEngine(request);
  }}};
  // Test-only access to the otherwise closed shadow root.
  const attach=Element.prototype.attachShadow;
  Element.prototype.attachShadow=function(options){const root=attach.call(this,options);this.__testShadow=root;return root;};
 });
}
async function open(page){await page.evaluate(script);await expect.poll(()=>page.evaluate(()=>document.getElementById('parzr-local-panel')?.__testShadow?.querySelector('[aria-live]')?.textContent)).toMatch(/corrections|No changes needed|Connect/);}
async function click(page,label){await page.evaluate(label=>{const root=document.getElementById('parzr-local-panel').__testShadow;const b=[...root.querySelectorAll('button')].find(x=>x.textContent===label);b.click();},label);}
test('textarea fixes selected text, keeps surrounding text, and supports native undo',async({page})=>{
 await setup(page,'<textarea id="editor">Before. i hope your doing well. After.</textarea>');
 await page.evaluate(()=>{const e=document.querySelector('textarea');e.focus();e.setSelectionRange(8,30);});
 await open(page);await click(page,'Fix all');
 await expect(page.locator('textarea')).toHaveValue("Before. I hope you're doing well. After.");
 await page.evaluate(()=>document.execCommand('undo'));await expect(page.locator('textarea')).toHaveValue('Before. i hope your doing well. After.');
});
test('contenteditable keeps bold, italic, links, and paragraph elements',async({page})=>{
 await setup(page,'<div id="editor" contenteditable="true"><p><b>Hello John</b>, can you <i>chek</i> <a href="https://example.com">teh document</a>?</p><p>Thanks.</p></div>');
 await page.evaluate(()=>{const e=document.querySelector('#editor');e.focus();const r=document.createRange();r.selectNodeContents(e);const s=getSelection();s.removeAllRanges();s.addRange(r);});
 await open(page);await click(page,'Fix all');
 await expect(page.locator('#editor i')).toHaveText('check');await expect(page.locator('#editor b')).toHaveText('Hello John');await expect(page.locator('#editor a')).toHaveText('teh document');await expect(page.locator('#editor p')).toHaveCount(2);
 await expect(page.locator('#parzr-local-panel')).toHaveCount(0);
});
test('stale textarea refuses edits',async({page})=>{
 await setup(page,'<textarea>can you chek this once?</textarea>');await page.evaluate(()=>{const e=document.querySelector('textarea');e.focus();e.select();});await open(page);
 await page.evaluate(()=>document.querySelector('textarea').value='User typed a new message.');await click(page,'Fix all');
 await expect(page.locator('textarea')).toHaveValue('User typed a new message.');
 expect(await page.evaluate(()=>document.getElementById('parzr-local-panel').__testShadow.textContent)).toContain('Your text changed');
});
test('secure inputs are never read or sent to the engine',async({page})=>{
 await setup(page,'<input type="password" value="teh secret">');await page.locator('input').focus();await page.evaluate(script);
 await expect(page.locator('#parzr-local-panel')).toHaveCount(0);expect(await page.evaluate(()=>window.__parzrCalls||0)).toBe(0);
});
test('code and mentions are protected in rich text',async({page})=>{
 await setup(page,'<div id="editor" contenteditable="true">I recieved <code>teh --help</code> from <span contenteditable="false" data-mention="john">mesage</span>.</div>');
 await page.evaluate(()=>{const e=document.querySelector('#editor');e.focus();const r=document.createRange();r.selectNodeContents(e);const s=getSelection();s.removeAllRanges();s.addRange(r);});
 await open(page);await click(page,'Fix all');await expect(page.locator('#editor code')).toHaveText('teh --help');await expect(page.locator('[data-mention]')).toHaveText('mesage');expect(await page.locator('#editor').textContent()).toContain('I received');
});
test('direct tone preserves action formatting and uses a period',async({page})=>{
 await setup(page,'<div id="editor" contenteditable="true">Could you <b>review</b> this?</div>');
 await page.evaluate(()=>{const e=document.querySelector('#editor');e.focus();const r=document.createRange();r.selectNodeContents(e);const s=getSelection();s.removeAllRanges();s.addRange(r);});
 await open(page);await click(page,'Direct');await expect.poll(()=>page.evaluate(()=>document.getElementById('parzr-local-panel').__testShadow.querySelector('pre').textContent)).toBe('Review this.');
 await click(page,'Apply changes'); await expect(page.locator('#editor b')).toHaveText('Review');await expect(page.locator('#editor')).toHaveText('Review this.');
});
test('unavailable native host produces actionable feedback',async({page})=>{
 await setup(page,'<textarea>teh report.</textarea>');await page.evaluate(()=>{const e=document.querySelector('textarea');e.focus();e.select();chrome.runtime.sendMessage=async()=>({error:'Connect the parzr native host first.'});});
 await page.evaluate(script);await expect.poll(()=>page.evaluate(()=>document.getElementById('parzr-local-panel').__testShadow.textContent)).toContain('Connect the parzr native host first.');
});

async function marks(page) {
 await expect.poll(()=>page.evaluate(()=>document.querySelector('#parzr-inline-marks')?.__testShadow?.querySelectorAll('button').length||0)).toBeGreaterThan(0);
}
async function firstMark(page, original='recieved') {
 await marks(page);
 await page.evaluate(original=>{const buttons=[...document.querySelector('#parzr-inline-marks').__testShadow.querySelectorAll('button')];buttons.find(b=>b.getAttribute('aria-label').startsWith(original+':')).click();},original);
}
test('automatic textarea checking highlights without a selection, keeps focus, and applies one correction with Undo',async({page})=>{
 await setup(page,'<textarea style="width:420px;height:100px;font:18px/1.5 sans-serif">I recieved your mesage.</textarea>');
 await page.locator('textarea').focus(); await page.locator('textarea').press('End'); await page.evaluate(script); await marks(page);
 expect(await page.evaluate(()=>document.activeElement.tagName)).toBe('TEXTAREA');
 await expect(page.locator('#parzr-local-panel')).toHaveCount(0);
 expect(await page.evaluate(()=>window.__parzrRequests.every(r=>r.deep===false))).toBe(true);
 await firstMark(page); expect(await page.locator('#parzr-local-panel').evaluate(e=>e.offsetWidth)).toBe(260);
 await expect.poll(()=>page.evaluate(()=>document.getElementById('parzr-local-panel').__testShadow.querySelector('[aria-label="Corrected sentence preview"]').textContent)).toBe('I received your message.');
 await click(page,'Apply suggestion'); await expect(page.locator('textarea')).toHaveValue('I received your mesage.');
 await page.evaluate(()=>document.execCommand('undo')); await expect(page.locator('textarea')).toHaveValue('I recieved your mesage.');
});
test('Teams/Slack-shaped nested chat composer preserves mentions, emoji, paragraphs, action styles, and Undo',async({page})=>{
 await setup(page,'<div role="textbox" aria-label="Message" contenteditable="" style="width:450px;font:18px/1.5 sans-serif"><p>I <b>recieved</b> your mesage <span data-entity-type="mention" contenteditable="false">@Mira</span> 😀.</p><p><a href="https://example.com">teh link</a></p></div><button id="send">Send</button>');
 await page.locator('[role=textbox]').focus(); await page.locator('[role=textbox]').press('Control+End'); await page.evaluate(script); await firstMark(page);
 await click(page,'Apply suggestion'); await expect(page.locator('b')).toHaveText('received'); await expect(page.locator('[data-entity-type]')).toHaveText('@Mira');
 await expect(page.locator('a')).toHaveText('teh link'); await expect(page.locator('p')).toHaveCount(2);
 expect(await page.locator('[role=textbox]').textContent()).toContain('😀');
 await page.evaluate(()=>document.execCommand('undo')); await expect(page.locator('b')).toHaveText('recieved');
 expect(await page.evaluate(()=>window.__sendCount||0)).toBe(0);
});
test('dynamic draft replacement invalidates outstanding automatic results',async({page})=>{
 await setup(page,'<textarea>I recieved your mesage.</textarea>');
 await page.evaluate(()=>{window.__releaseCheck=null;chrome.runtime.sendMessage=({request})=>new Promise(resolve=>{window.__releaseCheck=()=>resolve({text:'I received your mesage.',edits:[{start_utf16:2,end_utf16:10,original:'recieved',replacement:'received'}]});});});
 await page.locator('textarea').focus(); await page.evaluate(script); await expect.poll(()=>page.evaluate(()=>typeof window.__releaseCheck)).toBe('function');
 await page.locator('textarea').fill('A different draft.'); await page.evaluate(()=>window.__releaseCheck());
 await expect(page.locator('textarea')).toHaveValue('A different draft.');
 expect(await page.evaluate(()=>document.querySelector('#parzr-inline-marks').__testShadow.querySelectorAll('button').length)).toBe(0);
});
test('IME composition is not checked until composition ends',async({page})=>{
 await setup(page,'<textarea></textarea>'); await page.locator('textarea').focus(); await page.evaluate(script);
 await page.evaluate(()=>{const e=document.querySelector('textarea');e.dispatchEvent(new CompositionEvent('compositionstart',{bubbles:true}));e.value='I recieved your mesage.';e.dispatchEvent(new InputEvent('input',{bubbles:true,isComposing:true}));});
 await page.waitForTimeout(300); expect(await page.evaluate(()=>window.__parzrCalls||0)).toBe(0);
 await page.evaluate(()=>document.querySelector('textarea').dispatchEvent(new CompositionEvent('compositionend',{bubbles:true}))); await marks(page);
});
test('readonly, OTP, disabled, private, and protected-island fields never reach the engine',async({page})=>{
 await setup(page,'<textarea readonly>teh secret.</textarea><input autocomplete="one-time-code" value="teh code"><textarea disabled>teh value.</textarea><div data-private><textarea>teh private.</textarea></div><div contenteditable="true"><span contenteditable="false" tabindex="0">teh mention</span></div>');
 await page.evaluate(script);
 for(const selector of ['textarea[readonly]','input','[data-private] textarea','span']) { await page.locator(selector).focus(); await page.waitForTimeout(220); }
 expect(await page.evaluate(()=>window.__parzrCalls||0)).toBe(0);
});
test('open shadow-root editor can receive automatic suggestions and apply range edits',async({page})=>{
 await setup(page,'<div id="component"></div>');
 await page.evaluate(()=>{const host=document.querySelector('#component');const shadow=host.attachShadow({mode:'open'});shadow.innerHTML='<div contenteditable="plaintext-only" style="font:18px sans-serif">I recieved your mesage.</div>';const e=shadow.querySelector('div');e.focus();const r=document.createRange();r.selectNodeContents(e);r.collapse(false);shadow.getSelection().removeAllRanges();shadow.getSelection().addRange(r);});
 await page.evaluate(script); await firstMark(page); await click(page,'Apply suggestion');
 await expect(page.locator('#component').locator('[contenteditable]')).toHaveText('I received your mesage.');
});
test('rich editor preserves BR boundaries and supports insertion at the end',async({page})=>{
 await setup(page,'<div contenteditable="true">First line.<br>Second line</div>');
 await page.evaluate(()=>{const e=document.querySelector('[contenteditable]');e.focus();const r=document.createRange();r.selectNodeContents(e);getSelection().removeAllRanges();getSelection().addRange(r);chrome.runtime.sendMessage=async()=>({text:'First line.\nSecond line.',edits:[{start_utf16:23,end_utf16:23,original:'',replacement:'.'}]});});
 await open(page); await click(page,'Fix all'); await expect(page.locator('[contenteditable]')).toHaveText('First line.Second line.'); await expect(page.locator('br')).toHaveCount(1);
});
test('framework beforeinput veto refuses a correction without touching the draft',async({page})=>{
 await setup(page,'<div contenteditable="true">I recieved your mesage.</div>');
 await page.evaluate(()=>{const e=document.querySelector('[contenteditable]');e.focus();const r=document.createRange();r.selectNodeContents(e);getSelection().removeAllRanges();getSelection().addRange(r);e.addEventListener('beforeinput',event=>event.preventDefault());});
 await open(page); await click(page,'Fix all'); await expect(page.locator('[contenteditable]')).toHaveText('I recieved your mesage.');
 expect(await page.evaluate(()=>document.querySelector('#parzr-local-panel').__testShadow.textContent)).toContain('refused replacement');
});
test('activate twice reuses one inline controller and typing removes an old correction card',async({page})=>{
 await setup(page,'<textarea>I recieved your mesage.</textarea>'); await page.locator('textarea').focus(); await page.evaluate(script); await marks(page); await page.evaluate(script); await marks(page);
 await expect(page.locator('#parzr-inline-marks')).toHaveCount(1); await firstMark(page); await page.locator('textarea').fill('New draft.');
 await expect(page.locator('#parzr-local-panel')).toHaveCount(0);
});

test('clicking the actual rich-text word opens a full sentence preview and preserves Undo',async({page})=>{
 await setup(page,'<div contenteditable="true" style="font:20px/1.5 sans-serif;width:600px">This is not how it is suppose to be <span id="word">Done</span>.</div>');
 await page.locator('[contenteditable]').focus(); await page.locator('[contenteditable]').press('Control+End'); await page.evaluate(script); await marks(page);
 await page.locator('#word').click();
 await expect.poll(()=>page.evaluate(()=>document.getElementById('parzr-local-panel')?.__testShadow?.querySelector('[aria-label="Corrected sentence preview"]')?.textContent)).toBe('This is not how it is supposed to be done.');
 await click(page,'Apply suggestion'); await expect(page.locator('[contenteditable]')).toHaveText('This is not how it is suppose to be done.');
 await page.evaluate(()=>document.execCommand('undo')); await expect(page.locator('#word')).toHaveText('Done');
});
