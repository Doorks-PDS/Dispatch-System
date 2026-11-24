"""Read-only source compatibility gate for Doorks / Moses 5.55.

Stop on any unexpected local file difference. Does not change business data.
"""
import argparse
import hashlib
import json
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def verify(root, manifest, phase):
    files=json.loads(manifest.read_text(encoding='utf-8'))['files']
    failures=[]
    for name, checks in files.items():
        expected=checks.get(phase)
        actual=digest(root/name)
        if isinstance(expected,list):
            ok=actual in expected
        else:
            ok=actual==expected
        if not ok:failures.append(name)
    if failures:
        print('STOP: Moses 5.55 '+phase+' compatibility failed. No files changed by this checker.')
        for name in failures:print('  Different / unexpected file:',name)
        print('Reconcile local source changes before installing; do not overwrite them.')
        return 1
    print('PASS: Moses 5.55 '+phase+' compatibility for '+str(len(files))+' files; business data untouched.')
    return 0


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',required=True)
    parser.add_argument('--phase',required=True,choices=['before','after'])
    parser.add_argument('--manifest')
    args=parser.parse_args()
    manifest=Path(args.manifest) if args.manifest else Path(__file__).with_name('moses_555_manifest.json')
    raise SystemExit(verify(Path(args.root),manifest,args.phase))
