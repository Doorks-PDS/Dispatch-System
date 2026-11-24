"""Read-only source compatibility check. Never writes files or accesses provider data."""
from __future__ import annotations
from pathlib import Path
import argparse, json, hashlib, sys

def fingerprint(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None

def verify(root: Path, manifest: Path, phase: str) -> int:
    data=json.loads(manifest.read_text(encoding='utf-8'))
    failed=[]
    for name,expected in data['files'].items():
        actual=fingerprint(root/name)
        if actual!=expected[phase]:
            failed.append(name)
    if failed:
        print('STOP: Moses 5.49 '+phase+' compatibility failed; do not overwrite/push.')
        for path in failed: print('  '+path+' — contents differ')
        return 1
    print(f'PASS: Moses 5.49 {phase} source compatibility ({len(data["files"])} files); no data changed')
    return 0

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',required=True)
    parser.add_argument('--phase',choices=('before','after'),required=True)
    parser.add_argument('--manifest',default=None)
    args=parser.parse_args()
    manifest=Path(args.manifest) if args.manifest else Path(__file__).with_name('moses_549_manifest.json')
    raise SystemExit(verify(Path(args.root),manifest,args.phase))
