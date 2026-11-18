"""Check Doorks 5.38 -> 5.40 compatibility, without writing or deleting data."""
import argparse, hashlib, json
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--root', type=Path, required=True)
p.add_argument('--phase', choices=['before', 'after'], required=True)
args = p.parse_args()
manifest = json.loads((Path(__file__).parent/'moses_540_manifest.json').read_text())
expected = manifest[args.phase]
errors = []
for rel, wanted in expected.items():
    f = args.root / rel
    current = hashlib.sha256(f.read_bytes()).hexdigest() if f.is_file() else None
    if current != wanted:
        errors.append(rel)
if args.phase == 'before':
    for rel in manifest['after']:
        if rel not in expected and (args.root/rel).exists():
            errors.append(rel+' (new-file collision)')
if errors:
    for rel in errors: print('STOP: incompatible:', rel)
    raise SystemExit(1)
print('PASS: Moses 5.40', args.phase, 'file compatibility; no data changed')
