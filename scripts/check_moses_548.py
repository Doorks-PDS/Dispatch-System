#!/usr/bin/env python3
"""Fail-closed source compatibility check; does not read or change production records."""
import argparse,hashlib,json,sys
from pathlib import Path

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',default='.');p.add_argument('--phase',choices=('before','after'),required=True);p.add_argument('--manifest',default=str(Path(__file__).with_name('moses_548_manifest.json')))
    args=p.parse_args();entries=json.loads(Path(args.manifest).read_text())['files'];issues=[]
    for name,checks in entries.items():
        target=Path(args.root)/name
        got=hashlib.sha256(target.read_bytes()).hexdigest() if target.is_file() else None
        if got!=checks[args.phase]:issues.append(name)
    if issues:
        print('STOP: 5.48 '+args.phase+' check failed; do not overwrite changed files: '+', '.join(issues));sys.exit(1)
    print('PASS: Moses 5.48 '+args.phase+' source hashes verified; production data untouched')
