#!/usr/bin/env python3
"""Read-only 5.42 patch compatibility and installed-file hash verification."""
import argparse
import hashlib
import json
from pathlib import Path


def verify(root: Path, manifest: dict, phase: str) -> int:
    expected = manifest['before' if phase == 'before' else 'after']
    problems = []
    for rel, checksum in expected.items():
        path = root / rel
        if not path.is_file():
            problems.append(f'MISSING: {rel}')
        elif hashlib.sha256(path.read_bytes()).hexdigest() != checksum:
            problems.append(f'CHANGED: {rel}')
    if phase == 'before':
        for rel in manifest['after']:
            if rel not in expected and (root / rel).exists():
                problems.append(f'ALREADY EXISTS: {rel}')
    if problems:
        for item in problems:
            print('STOP:', item)
        print('Do not install or push until the project version is reconciled.')
        return 1
    print(f'PASS: Moses 5.42 {phase} source compatibility; no data changed')
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--phase', choices=('before', 'after'), required=True)
    parser.add_argument('--manifest', type=Path, default=Path(__file__).with_name('moses_542_manifest.json'))
    opts = parser.parse_args()
    raise SystemExit(verify(opts.root, json.loads(opts.manifest.read_text()), opts.phase))


if __name__ == '__main__':
    main()
