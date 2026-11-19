#!/usr/bin/env python3
"""Read-only source compatibility check for Moses 5.43 incremental patch."""
import argparse,hashlib,json
from pathlib import Path

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--phase',choices=['before','after'],required=True)
    a=p.parse_args()
    manifest=json.loads((Path(__file__).resolve().parent/'moses_543_manifest.json').read_text())
    failed=[]
    for rel,hashes in manifest['files'].items():
        path=a.root/rel
        want=hashes[a.phase]
        if want is None:
            if path.exists():failed.append(rel+' should not exist before patch')
            continue
        if not path.is_file():failed.append(rel+' missing');continue
        got=hashlib.sha256(path.read_bytes()).hexdigest()
        if got!=want:failed.append(rel+' changed from expected '+a.phase+' version')
    if failed:
        print('STOP: Moses 5.43 compatibility check failed:')
        for item in failed:print('  '+item)
        raise SystemExit(1)
    print('PASS: Moses 5.43 '+a.phase+' — '+str(len(manifest['files']))+' application/test files verified; no data changed')
if __name__=='__main__':main()
