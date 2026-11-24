#!/usr/bin/env python3
"""Non-destructive installed-source checks for Moses 5.47 against 5.46."""
import argparse,hashlib,json,sys
from pathlib import Path

def check(root,manifest,phase):
    expected=json.loads(Path(manifest).read_text())['files']
    errors=[]
    for name,hashes in expected.items():
        file=Path(root)/name
        actual=hashlib.sha256(file.read_bytes()).hexdigest() if file.is_file() else 'MISSING'
        if actual!=hashes[phase]:errors.append(name+': contents differ or missing')
    if errors:
        print('STOP: Moses 5.47 '+phase+' compatibility failed')
        for e in errors:print('  '+e)
        return False
    print('PASS: Moses 5.47 '+phase+' file compatibility; no data changed')
    return True

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',default='.')
    parser.add_argument('--phase',choices=('before','after'),required=True)
    parser.add_argument('--manifest',default=None)
    opts=parser.parse_args()
    manifest=opts.manifest or (Path(__file__).parent/'moses_547_manifest.json')
    sys.exit(0 if check(opts.root,manifest,opts.phase) else 1)
