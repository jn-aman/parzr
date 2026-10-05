#!/usr/bin/env python3
"""Measure the actual shared production path on authored fixtures, never a rule post-pass."""
import argparse, hashlib, json, os, pathlib, runpy, select, statistics, subprocess, time
ROOT = pathlib.Path(__file__).resolve().parent.parent
validate_edits = runpy.run_path(str(ROOT/'scripts/run-english-benchmark.py'))['validate_edits']
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--engine', type=pathlib.Path, default=ROOT/'engine/target/release/parzr-engine')
parser.add_argument('--model', type=pathlib.Path, required=True)
parser.add_argument('--runtime', type=pathlib.Path, default=ROOT/'dist/model/libparzr_model.dylib')
parser.add_argument('--fixtures', type=pathlib.Path, default=ROOT/'benchmarks/model-smoke.jsonl')
parser.add_argument('--output', type=pathlib.Path, required=True)
parser.add_argument('--idle-memory', action='store_true')
parser.add_argument('--deep', action='store_true', help='Include the context model in grammar checks.')
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
if (args.output/'results.jsonl').exists(): raise SystemExit('Choose a new output directory to preserve previous evidence.')
env = os.environ.copy(); env.update(PARZR_MODEL_PATH=str(args.model.resolve()), PARZR_MODEL_RUNTIME=str(args.runtime.resolve()))
rows=[]
def rss(pid):
    result = subprocess.run(['ps','-o','rss=','-p',str(pid)], capture_output=True, text=True)
    return int(result.stdout.strip() or 0)*1024
def footprint(pid):
    import re
    output = subprocess.run(['/usr/bin/vmmap','-summary',str(pid)],capture_output=True,text=True).stdout
    match = re.search(r'Physical footprint:\s*([\d.]+)([KMG])',output)
    return int(float(match[1])*{'K':1024,'M':1024**2,'G':1024**3}[match[2]]) if match else None
with (args.output/'process.txt').open('w') as errors:
    # Explicitly deny network access throughout inference. No runtime downloads.
    process = subprocess.Popen(['/usr/bin/sandbox-exec','-p','(version 1) (allow default) (deny network*)','/usr/bin/time','-lp',str(args.engine.resolve())], env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=errors, text=True, bufsize=1)
    try:
        fixtures = [json.loads(s) for s in args.fixtures.read_text().splitlines() if s.strip()]
        for i, fixture in enumerate(fixtures):
            mode = fixture.get('mode', fixture['id'] if fixture.get('task') == 'style' else 'fix')
            request = {'text':fixture['input'], 'mode':mode, 'deep':args.deep, **fixture.get('options',{})}
            start = time.perf_counter(); process.stdin.write(json.dumps(request, ensure_ascii=False)+'\n'); process.stdin.flush()
            if not select.select([process.stdout],[],[],25)[0]: raise RuntimeError('Model request timed out')
            response = json.loads(process.stdout.readline())
            if not response.get('error'):
                try:
                    validate_edits(fixture['input'],response)
                except (AssertionError, KeyError, UnicodeError):
                    response['error']='Invalid UTF-16 edit plan.'
            expected = fixture.get('expected')
            row = {**fixture, 'actual':response.get('text'), 'error':response.get('error'), 'seconds':round(time.perf_counter()-start,4), 'exact':response.get('text') == expected if expected is not None else None, 'changed':response.get('text') != fixture['input'] if 'text' in response else None, 'edits':response.get('edits'), 'version':response.get('version')}
            rows.append(row)
            with (args.output/'results.jsonl').open('a') as output: output.write(json.dumps(row,ensure_ascii=False)+'\n')
            if (i+1)%100 == 0: print(f'{i+1}/{len(fixtures)}: {sum(r["exact"] is True for r in rows)} exact',flush=True)
        memory = {}
        # time is the immediate child; ps finds the actual engine PID without recording paths.
        child = subprocess.check_output(['pgrep','-P',str(process.pid)],text=True).strip().splitlines()
        if args.idle_memory and len(child)==1:
            pid=int(child[0]); memory['active_rss_bytes']=rss(pid); memory['active_physical_footprint_bytes']=footprint(pid)
            time.sleep(35)
            memory['idle_after_35s_rss_bytes']=rss(pid)
            memory['idle_after_35s_physical_footprint_bytes']=footprint(pid)
            t=time.perf_counter();process.stdin.write(json.dumps({'text':'this si too bod','mode':'fix','deep':args.deep,'sentence_end':True})+'\n');process.stdin.flush()
            if not select.select([process.stdout],[],[],25)[0]: raise RuntimeError('Idle reload timed out')
            response=json.loads(process.stdout.readline());memory['reload_seconds']=round(time.perf_counter()-t,4);memory['reload_output']=response.get('text');memory['reload_error']=response.get('error')
        process.stdin.close(); process.wait(timeout=25)
        if process.returncode: raise RuntimeError(f'Engine failed at shutdown: {process.returncode}')
    finally:
        if process.poll() is None: process.kill();process.wait()
summary={'deep':args.deep,'model':args.model.name,'model_bytes':args.model.stat().st_size,'network':'denied','rows':len(rows),'errors':sum(bool(r['error']) for r in rows),'cold_seconds':rows[0]['seconds'] if rows else None,'warm_median_seconds':statistics.median(r['seconds'] for r in rows[1:]) if len(rows)>1 else None,'warm_p95_seconds':sorted(r['seconds'] for r in rows[1:])[min(len(rows)-2,int((len(rows)-1)*.95))] if len(rows)>1 else None,'memory':memory,'groups':{task:{'total':len(group:=[r for r in rows if r.get('task','grammar')==task]),'exact':sum(r['exact'] is True for r in group),'changed':sum(r['changed'] is True for r in group),'errors':sum(bool(r['error']) for r in group)} for task in sorted({r.get('task','grammar') for r in rows})}}
import re
peak=re.search(r'(\d+)\s+maximum resident set size',(args.output/'process.txt').read_text())
summary['peak_rss_bytes']=int(peak[1]) if peak else None
def file_sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()
summary['engine_sha256']=file_sha(args.engine)
summary['runtime_sha256']=file_sha(args.runtime)
summary['fixtures_sha256']=file_sha(args.fixtures)
(args.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2),flush=True)
