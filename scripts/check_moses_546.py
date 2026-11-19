#!/usr/bin/env python3
"""Doorks/Moses 5.46 exact-file safety check; NEVER changes any project file."""
import argparse,hashlib,json
from pathlib import Path

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--phase',choices=('before','after'),required=True)
    args=parser.parse_args()
    manifest=json.loads((Path(__file__).resolve().parent/'moses_546_manifest.json').read_text(encoding='utf-8'))
    failures=[]
    for relative,hashes in manifest['files'].items():
        target=args.root/relative
        expected=hashes[args.phase]
        if expected is None:
            if target.exists():failures.append(f'{relative}: unexpected preexisting file')
        elif not target.is_file():failures.append(f'{relative}: missing file')
        elif hashlib.sha256(target.read_bytes()).hexdigest()!=expected:
            failures.append(f'{relative}: contents differ; stop and reconcile, do not overwrite')
    if failures:
        print(f'STOP: Doorks/Moses 5.46 {args.phase} compatibility failed')
        for issue in failures:print(' ',issue)
        raise SystemExit(1)
    print(f'PASS: Doorks/Moses 5.46 {args.phase} compatibility. No data changed.')

if __name__=='__main__':main()
