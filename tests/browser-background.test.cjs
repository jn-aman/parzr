const {test}=require('node:test');
const assert=require('node:assert/strict');
const {readFileSync}=require('node:fs');
const vm=require('node:vm');
test('the manifest key yields the extension ID that connect-browser.py registers by default',()=>{
 const der=Buffer.from(JSON.parse(readFileSync('extensions/browser/manifest.json','utf8')).key,'base64');
 const id=[...require('node:crypto').createHash('sha256').update(der).digest('hex').slice(0,32)].map(c=>String.fromCharCode(97+parseInt(c,16))).join('');
 assert.ok(readFileSync('scripts/connect-browser.py','utf8').includes(`CHROMIUM_ID = '${id}'`));
});
function event(){const callbacks=[];return {addListener:fn=>callbacks.push(fn),emit:(...args)=>callbacks.map(fn=>fn(...args))};}
function background(){
 const sent=[], timers=[], port={onMessage:event(),onDisconnect:event(),postMessage:r=>sent.push(r),disconnect:()=>{}};
 const api={runtime:{id:'local-extension',onMessage:event(),connectNative:()=>port},action:{onClicked:event(),setBadgeText:()=>{},setTitle:()=>{}},commands:{onCommand:event()},tabs:{query:async()=>[]},scripting:{executeScript:async request=>{api.injection=request;}}};
 vm.runInNewContext(readFileSync('extensions/browser/background.js','utf8'),{browser:api,TextEncoder,setTimeout:fn=>{timers.push(fn);return timers.length;},clearTimeout:()=>{}});
 const sender=frame=>({id:api.runtime.id,tab:{id:1},frameId:frame,url:'https://example.com/chat'});
 return {api,sent,port,request:(frame,request,respond)=>api.runtime.onMessage.emit({type:'parzr-rewrite',request},sender(frame),respond),sender};
}
test('browser activation injects shared adapters into accessible frames',async()=>{
 const {api}=background();await api.action.onClicked.emit({id:1,url:'https://example.com/chat'})[0];
 assert.equal(api.injection.target.allFrames,true);assert.deepEqual([...api.injection.files],['editor.js','content.js']);
});
test('automatic checks stay on fast engine and separate frames keep their pending requests',()=>{
 const {request,port,sent}=background(), replies=[];
 request(0,{text:'First.',mode:'fix',deep:false},r=>replies.push(['first',r]));
 request(1,{text:'Second.',mode:'fix',deep:false},r=>replies.push(['old',r]));
 request(2,{text:'Other composer.',mode:'fix',deep:false},r=>replies.push(['other',r]));
 request(1,{text:'Latest draft.',mode:'fix',deep:false},r=>replies.push(['new',r]));
 assert.equal(sent.length,1);assert.equal(sent[0].deep,false);assert.equal(replies[0][0],'old');assert.match(replies[0][1].error,/newer/i);
 port.onMessage.emit({text:'First.',edits:[]});assert.equal(sent[1].text,'Other composer.');
 port.onMessage.emit({text:'Other composer.',edits:[]});assert.equal(sent[2].text,'Latest draft.');
 port.onMessage.emit({text:'Latest draft.',edits:[]});assert.deepEqual(replies.map(r=>r[0]),['old','first','other','new']);
});
test('untrusted callers and oversized writing metadata cannot start inference',()=>{
 const {api,sender,sent,request}=background();let result;
 api.runtime.onMessage.emit({type:'parzr-rewrite',request:{text:'Private.',mode:'fix'}},{...sender(0),id:'other'},r=>result=r);
 assert.equal(result,undefined);assert.equal(sent.length,0);
 request(0,{text:'text',mode:'fix',protected_ranges:new Array(4097).fill({})},r=>result=r);
 assert.match(result.error,/metadata/);assert.equal(sent.length,0);
});
test('dictionary and names are forwarded unchanged and names are never capitalized unless asked',()=>{
 const {request,sent}=background();
 request(0,{text:'Hi aman jain.',mode:'fix',dictionary:['Parzr','Zorblax'],names:['aman jain']},()=>{});
 assert.deepEqual([...sent[0].dictionary],['Parzr','Zorblax']);assert.deepEqual([...sent[0].names],['aman jain']);assert.equal(sent[0].capitalize_names,false);
});
test('missing vocabulary defaults safely and malformed vocabulary is rejected',()=>{
 const {request,sent}=background();let result;
 request(0,{text:'Plain.',mode:'fix'},()=>{});
 assert.deepEqual([...sent[0].dictionary],['Parzr']);assert.deepEqual([...sent[0].names],[]);
 request(1,{text:'Bad.',mode:'fix',names:[1]},r=>result=r);assert.match(result.error,/metadata/);
 request(2,{text:'Big.',mode:'fix',names:new Array(2001).fill('a')},r=>result=r);assert.match(result.error,/metadata/);
 assert.equal(sent.length,1);
});
