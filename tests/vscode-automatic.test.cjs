const {test}=require('node:test');const assert=require('node:assert/strict');
const vm=require('node:vm');const fs=require('node:fs');const path=require('node:path');
const wait=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function until(predicate){for(let i=0;i<100;i++){if(predicate())return;await wait(20);}assert.fail('Automatic editor check did not finish.');}
function harness(initial,languageId='plaintext'){
 const events={},commands={},diagnostics=new Map(),statuses=[],requests=[],messages=[];
 const disposable=()=>({dispose(){}}), hook=name=>fn=>{events[name]=fn;return disposable();};
 const uri={scheme:'file',toString:()=> 'file:///synthetic-parzr.txt'};
 const doc={uri,languageId,version:1,isClosed:false,text:initial,getText:()=>doc.text,positionAt:offset=>({line:0,character:offset}),offsetAt:p=>p.character};
 class Range{constructor(start,end){this.start=start;this.end=end;}intersection(r){return this.start.character<=r.end.character&&this.end.character>=r.start.character?this:undefined;}}
 const undo=[];
 const editor={document:doc,edit:async build=>{const replacements=[];build({replace:(range,text)=>replacements.push({range,text})});undo.push(doc.text);for(const {range,text} of replacements.sort((a,b)=>b.range.start.character-a.range.start.character)){doc.text=doc.text.slice(0,range.start.character)+text+doc.text.slice(range.end.character);}doc.version++;events.change?.({document:doc});return true;}};
 const kind=value=>({value,append:suffix=>kind(value+'.'+suffix)});
 const api={env:{remoteName:undefined},Range,Diagnostic:class{constructor(range,message){this.range=range;this.message=message;}},DiagnosticSeverity:{Information:2},CodeAction:class{constructor(title,kind){this.title=title;this.kind=kind;}},CodeActionKind:{QuickFix:kind('quickfix'),SourceFixAll:kind('source.fixAll')},StatusBarAlignment:{Right:1},
  workspace:{getConfiguration:()=>({get:(key,fallback)=>key==='enginePath'?path.resolve('engine/target/release/parzr-engine'):fallback}),onDidChangeTextDocument:hook('change'),onDidChangeConfiguration:hook('configuration'),onDidCloseTextDocument:hook('close'),registerTextDocumentContentProvider:disposable},
  window:{activeTextEditor:editor,onDidChangeActiveTextEditor:hook('editor'),createStatusBarItem:()=>{const status={hide(){this.visible=false;},show(){this.visible=true;},dispose(){}};statuses.push(status);return status;},showTextDocument:async()=>editor,showInformationMessage:text=>messages.push(text),showErrorMessage:text=>messages.push(text)},
  languages:{createDiagnosticCollection:()=>({set:(u,ds)=>diagnostics.set(u.toString(),ds),delete:u=>diagnostics.delete(u.toString()),dispose:()=>{}}),registerCodeActionsProvider:(_,provider)=>{api.provider=provider;return disposable();}},
  commands:{registerCommand:(name,fn)=>{commands[name]=fn;return disposable();}}};
 const module={exports:{}},subscriptions=[];
 vm.runInNewContext(fs.readFileSync('extensions/vscode/extension.cjs','utf8'),{require:name=>name==='vscode'?api:name==='node:child_process'?{spawn:(...args)=>{const child=require('node:child_process').spawn(...args);const write=child.stdin.write.bind(child.stdin);child.stdin.write=data=>{requests.push(JSON.parse(data));return write(data);};return child;}}:require(name),module,exports:module.exports,Buffer,setTimeout,clearTimeout});
 module.exports.activate({subscriptions});
 return {api,doc,events,commands,diagnostics,requests,messages,undo,dispose:()=>{for(const item of subscriptions)item.dispose();module.exports.deactivate();}};
}
test('VS Code automatically diagnoses Unicode prose and applies a linked inline action with one Undo transaction',async()=>{
 const h=harness('Not only Mira did help.');try{
  await until(()=>h.diagnostics.has(h.doc.uri.toString()));assert.ok(h.requests.every(r=>r.deep===false));
  const actions=h.api.provider.provideCodeActions(h.doc,new h.api.Range({line:0,character:8},{line:0,character:8}));const quick=actions.find(a=>a.kind.value==='quickfix');assert.ok(quick);
  await h.commands[quick.command.command](...quick.command.arguments);
  assert.equal(h.doc.text,'Not only did Mira help.');assert.deepEqual(h.undo,['Not only Mira did help.']);
 }finally{h.dispose();}
});
test('VS Code invalidates stale inline actions before a changed draft can be edited',async()=>{
 const h=harness('😀 I recieved your mesage.');try{
  await until(()=>h.diagnostics.has(h.doc.uri.toString()));assert.ok(h.diagnostics.get(h.doc.uri.toString()).some(d=>d.range.start.character===5));
  const actions=h.api.provider.provideCodeActions(h.doc,new h.api.Range({line:0,character:0},{line:0,character:50}));const all=actions.find(a=>a.kind.value==='source.fixAll.parzr');assert.ok(all);
  h.doc.text='My newer draft.';h.doc.version++;h.events.change({document:h.doc});
  await h.commands[all.command.command](...all.command.arguments);assert.equal(h.doc.text,'My newer draft.');assert.equal(h.undo.length,0);assert.match(h.messages[0],/draft changed/);
 }finally{h.dispose();}
});
test('VS Code never automatically submits source code or remote documents',async()=>{
 const h=harness('teh mesage','rust');try{await wait(250);assert.equal(h.requests.length,0);h.doc.languageId='plaintext';h.api.env.remoteName='ssh-remote';h.events.editor();await wait(250);assert.equal(h.requests.length,0);}finally{h.dispose();}
});
