"""Read-only compatibility/installed-file checker for Moses 5.41."""
import argparse, hashlib, json
from pathlib import Path

def run(root, phase):
    manifest=json.loads((Path(__file__).parent/'moses_541_manifest.json').read_text())
    expected=manifest['before' if phase=='before' else 'after']
    errors=[]
    for rel,digest in expected.items():
        path=Path(root)/rel
        current=hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        if current != digest:errors.append(rel)
    for rel in manifest['after']:
        if rel not in expected and (Path(root)/rel).exists():errors.append('New file already exists: '+rel)
    if errors:
        for rel in errors:print('BLOCK:',rel)
        raise SystemExit('STOP: source differs, do not overwrite or push')
    print('PASS: Moses 5.41 '+phase+' compatibility; no application or data changed')

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',required=True)
    parser.add_argument('--phase',choices=['before','after'],required=True)
    args=parser.parse_args()
    run(args.root,args.phase)
