"""Read-only cumulative 5.51 source compatibility gate: no provider or data writes."""
from pathlib import Path
import argparse
import hashlib
import json


def fingerprint(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def verify(root, manifest, phase):
    expected=json.loads(manifest.read_text(encoding='utf-8'))['files']
    failures=[name for name, hashes in expected.items() if fingerprint(root/name)!=hashes[phase]]
    if failures:
        print('STOP: Doorks Moses 5.51 '+phase+' compatibility failed; do not overwrite or push.')
        for name in failures: print('  '+name+': contents differ')
        return 1
    print('PASS: Doorks Moses 5.51 '+phase+' compatibility ('+str(len(expected))+' files); no production data changed')
    return 0


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',required=True)
    parser.add_argument('--phase',choices=('before','after'),required=True)
    parser.add_argument('--manifest',default=None)
    args=parser.parse_args()
    location=Path(args.manifest) if args.manifest else Path(__file__).with_name('moses_551_manifest.json')
    raise SystemExit(verify(Path(args.root),location,args.phase))
