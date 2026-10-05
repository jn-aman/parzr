#!/usr/bin/env python3
"""Create a searchable, offline report from actual benchmark records."""
import argparse
import json
import pathlib

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('directory', type=pathlib.Path)
args = parser.parse_args()
rows = [json.loads(line) for line in (args.directory / 'results.jsonl').read_text().splitlines() if line.strip()]
summary = json.loads((args.directory / 'summary.json').read_text())
if len(rows) != summary['rows']:
    raise SystemExit('Incomplete benchmark records; no report generated.')
payload = json.dumps({'summary': summary, 'rows': rows}, ensure_ascii=False).replace('<', '\\u003c')
page = r'''<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Parzr · Grammar results</title>
<style>
:root{color-scheme:dark;font:15px/1.6 -apple-system,BlinkMacSystemFont,sans-serif;color:#eaf0eb;background:#202629}body{max-width:1100px;margin:0 auto;padding:40px 24px}h1{font-size:36px;letter-spacing:-1.2px;margin:0}p{color:#a7b4ae}a{color:#a8ecc4}.metrics{display:flex;gap:36px;flex-wrap:wrap;margin:28px 0}.metrics strong{display:block;font-size:24px;color:#a8ecc4}.metrics span{color:#a7b4ae}nav{display:flex;gap:8px;flex-wrap:wrap;position:sticky;top:0;background:#202629;padding:16px 0}input,button{font:inherit;border:1px solid #48534e;border-radius:8px;background:#292f32;color:inherit;padding:8px 12px}input{flex:1;min-width:160px}button{cursor:pointer}button[aria-pressed=true]{background:#a8ecc4;color:#153c28}button:focus-visible,input:focus-visible{outline:2px solid #a8ecc4;outline-offset:2px}button:disabled{opacity:.4;cursor:default}article{border-top:1px solid #394144;padding:24px 0}h2{font-size:15px;margin:0 0 14px}h2 small{color:#a7b4ae;font-weight:400}.comparison{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}.comparison div{background:#191f22;padding:14px;border-radius:8px;white-space:pre-wrap;overflow-wrap:anywhere}.comparison b{display:block;color:#a7b4ae;font-size:11px;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px}.pass{color:#a8ecc4}.fail{color:#e6c28b}footer{display:flex;align-items:center;justify-content:space-between;gap:12px}details{color:#a7b4ae;font-size:12px;overflow-wrap:anywhere;margin:24px 0}@media(max-width:700px){.comparison{grid-template-columns:1fr}body{padding:24px 16px}}
</style>
<h1>Parzr grammar results</h1>
<p>Actual production engine outputs, with network access denied. These synthetic development fixtures cover 20 grammar families; they do not establish complete English coverage or independent benchmark accuracy.</p>
<div class="metrics" id="metrics"></div>
<nav aria-label="Filter results"><input id="search" aria-label="Search cases" placeholder="Search sentences, rules or case IDs"><button data-filter="all" aria-pressed="true">All</button><button data-filter="fail" aria-pressed="false">Failures</button><button data-filter="clean" aria-pressed="false">Clean controls</button></nav>
<p id="count" role="status"></p><main id="cases"></main>
<footer><button id="previous">Previous</button><span id="page"></span><button id="next">Next</button></footer>
<details><summary>Runtime evidence</summary><pre id="metadata"></pre></details>
<script id="data" type="application/json">PAYLOAD</script>
<script>
const {rows,summary}=JSON.parse(document.getElementById('data').textContent);
let filter='all',page=0,matching=rows;const size=50;
const el=(tag,text)=>{const node=document.createElement(tag);node.textContent=text;return node;};
for(const [label,value] of Object.entries(summary.groups)){const node=el('div','');node.append(el('strong',`${value.exact}/${value.total}`),el('span',label==='clean'?'Clean controls unchanged':'Exact corrected paragraphs'));document.getElementById('metrics').append(node);}
const timing=el('div','');timing.append(el('strong',`${Math.round(summary.warm_median_seconds*1000)} ms`),el('span',summary.deep?'Warm passage median':'Warm fast-check median'));document.getElementById('metrics').append(timing);
document.getElementById('metadata').textContent=JSON.stringify(summary,null,2);
function render(){const main=document.getElementById('cases');main.replaceChildren();for(const r of matching.slice(page*size,(page+1)*size)){const article=el('article',''),title=el('h2',r.id+' · '),status=el('span',r.error?'Engine error':r.exact?'Exact match':'Mismatch');status.className=r.exact?'pass':'fail';title.append(status,el('small',` · ${(r.seconds*1000).toFixed(1)} ms · ${r.family||r.task}`));article.append(title);const comparison=el('div','');comparison.className='comparison';for(const [label,value] of [['Input',r.input],['Expected',r.expected],['Actual',r.error||r.actual||'']]){const cell=el('div','');cell.append(el('b',label),document.createTextNode(value));comparison.append(cell);}article.append(comparison);main.append(article);}document.getElementById('count').textContent=`${matching.length} matching cases · ${summary.errors} engine errors`;document.getElementById('page').textContent=`Page ${matching.length?page+1:0} of ${Math.ceil(matching.length/size)}`;document.getElementById('previous').disabled=page===0;document.getElementById('next').disabled=(page+1)*size>=matching.length;}
function apply(){const query=document.getElementById('search').value.toLowerCase();matching=rows.filter(r=>(filter!=='fail'||!r.exact)&&(filter!=='clean'||r.task==='clean')&&[r.id,r.input,r.expected,r.actual,...(r.edits||[]).map(e=>e.rule_id)].join(' ').toLowerCase().includes(query));page=0;render();}
document.getElementById('search').addEventListener('input',apply);
for(const b of document.querySelectorAll('[data-filter]'))b.addEventListener('click',()=>{filter=b.dataset.filter;for(const item of document.querySelectorAll('[data-filter]'))item.setAttribute('aria-pressed',String(item===b));apply();});
document.getElementById('previous').addEventListener('click',()=>{page--;render();window.scrollTo(0,0);});document.getElementById('next').addEventListener('click',()=>{page++;render();window.scrollTo(0,0);});render();
</script></html>'''
target = args.directory / 'report.html'
target.write_text(page.replace('PAYLOAD', payload))
print(f'Created {target} ({len(rows)} actual records).')
