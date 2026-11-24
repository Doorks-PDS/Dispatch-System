"""Read-only cumulative 5.50 source compatibility gate; never touches app data or providers."""
from pathlib import Path
import argparse, json, hashlib

def fingerprint(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None

def verify(root, manifest, phase):
    expected=json.loads(manifest.read_text(encoding='utf-8'))['files']
    failures=[name for name,hashes in expected.items() if fingerprint(root/name)!=hashes[phase]]
    if failures:
        print('STOP: Doorks Moses 5.50 '+phase+' source compatibility failed; do not overwrite or push.')
        for name in failures: print('  '+name+': contents differ')
        return 1
    print('PASS: Doorks Moses 5.50 '+phase+' compatibility ('+str(len(expected))+' files); no production data changed')
    return 0

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',required=True)
    parser.add_argument('--phase',choices=('before','after'),required=True)
    parser.add_argument('--manifest',default=None)
    args=parser.parse_args()
    file=Path(args.manifest) if args.manifest else Path(__file__).with_name('moses_550_manifest.json')
    raise SystemExit(verify(Path(args.root),file,args.phase))
