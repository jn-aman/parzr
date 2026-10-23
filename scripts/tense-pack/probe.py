"""Run sentences through a parzr-engine binary (one JSON request per line)."""
import json, os, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run(sentences, binary=None):
    """[(sentence, corrected text or None, [(rule id, original, replacement), ...])]; the model runtime and models
    folder come from PARZR_MODEL_RUNTIME and PARZR_MODELS_DIR."""
    binary = binary or os.path.join(ROOT, 'engine/target/release/parzr-engine')
    p = subprocess.Popen([binary], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    out = []
    for s in sentences:
        p.stdin.write(json.dumps({'text': s, 'mode': 'fix'}) + '\n')
        p.stdin.flush()
        r = json.loads(p.stdout.readline())
        if 'error' in r:
            out.append((s, None, []))
            continue
        out.append((s, r.get('text'), [(e['rule_id'], e['original'], e['replacement']) for e in r.get('edits', [])]))
    p.stdin.close()
    p.wait()
    return out
