#!/usr/bin/env python3
"""5.44 read-only before/after source compatibility checker. No production files changed."""
import argparse, hashlib, json
from pathlib import Path

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--phase', choices=('before','after'), required=True)
    args=parser.parse_args()
    manifest=json.loads((Path(__file__).resolve().parent/'moses_544_manifest.json').read_text())
    errors=[]
    for relative, phases in manifest['files'].items():
        path=args.root/relative
        expected=phases[args.phase]
        if expected is None:
            if path.exists():errors.append(relative+' unexpected before installation')
            continue
        if not path.is_file():errors.append(relative+' missing');continue
        if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
            errors.append(relative+' differs from expected '+args.phase+' version')
    if errors:
        print('STOP: Moses 5.44 file compatibility failed:')
        for error in errors:print('  '+error)
        raise SystemExit(1)
    print('PASS: Moses 5.44 '+args.phase+' file compatibility; no business data modified')
if __name__=='__main__':main()
