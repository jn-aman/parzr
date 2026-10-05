const {test}=require('node:test');const assert=require('node:assert/strict');const {spawnSync}=require('node:child_process');
const fs=require('node:fs'),os=require('node:os'),path=require('node:path');
function ask(request,home){
 const body=Buffer.from(JSON.stringify(request)),header=Buffer.alloc(4);header.writeUInt32LE(body.length);
 const p=spawnSync('engine/target/release/parzr-native-host',[],{input:Buffer.concat([header,body]),timeout:180000,env:{...process.env,HOME:home}});
 assert.equal(p.status,0,p.stderr?.toString());return JSON.parse(p.stdout.subarray(4,4+p.stdout.readUInt32LE(0)).toString());
}
function homeWith(contents){
 const home=fs.mkdtempSync(path.join(os.tmpdir(),'parzr-home-'));
 if(contents!==undefined){fs.mkdirSync(path.join(home,'Library/Application Support/Parzr'),{recursive:true});fs.writeFileSync(path.join(home,'Library/Application Support/Parzr/known-words.json'),contents);}
 return home;
}
const request={text:'Ask mesage about it.',mode:'fix'};
test('native host merges names from known-words.json into every request',()=>{
 const withFile=homeWith(JSON.stringify({version:1,dictionary:['Zorblax'],names:['mesage']})),without=homeWith();
 try{
  assert.ok(ask(request,without).edits.some(e=>e.original==='mesage'));
  assert.ok(!ask(request,withFile).edits.some(e=>e.original==='mesage'));
 }finally{fs.rmSync(withFile,{recursive:true,force:true});fs.rmSync(without,{recursive:true,force:true});}
});
test('native host ignores an invalid known-words.json',()=>{
 const home=homeWith('{not json');try{assert.ok(ask(request,home).edits.some(e=>e.original==='mesage'));}finally{fs.rmSync(home,{recursive:true,force:true});}
});
