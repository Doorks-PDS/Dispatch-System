#!/usr/bin/env python3
"""Read-only 5.45 compatibility verifier, against actual 5.44 files."""
import argparse, hashlib, json
from pathlib import Path

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--phase', choices=('before','after'), required=True)
    args=parser.parse_args()
    manifest=json.loads((Path(__file__).resolve().parent/'moses_545_manifest.json').read_text(encoding='utf-8'))
    errors=[]
    for relative, hashes in manifest['files'].items():
        path=args.root/relative
        expected=hashes[args.phase]
        if expected is None:
            if path.exists():errors.append(relative+': unexpected file exists before patch')
            continue
        if not path.is_file():errors.append(relative+': missing')
        elif hashlib.sha256(path.read_bytes()).hexdigest()!=expected:errors.append(relative+': version differs')
    if errors:
        print('STOP: Doorks/Moses 5.45 '+args.phase+' compatibility failed')
        for message in errors:print('  '+message)
        raise SystemExit(1)
    print('PASS: Doorks/Moses 5.45 '+args.phase+' source compatibility; no data changed')

if __name__=='__main__':main()
