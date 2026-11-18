"""Read-only checks of installed Doorks/Moses 5.38 source files.

Does not contact providers, use credentials, write application data, or deploy.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path


def verify(root: Path, manifest: dict, check_sends: bool = True) -> list[str]:
    root = root.expanduser().resolve()
    errors = []
    for rel, expected in sorted(manifest['files'].items()):
        path = root / rel
        if path.is_symlink() or not path.resolve().is_relative_to(root) or not path.is_file():
            errors.append(f'Missing or unsafe installed file: {rel}')
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            errors.append(f'File differs from release: {rel}')
    if check_sends:
        for key in ('PDS_SMS_SEND_ENABLED', 'PDS_SCHEDULE_EMAIL_SEND_ENABLED'):
            if os.environ.get(key, '').strip().lower() == 'true':
                errors.append(f'{key}=true in this process: keep customer sends disabled for first rollout')
    return errors


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', required=True, type=Path)
    p.add_argument('--manifest', type=Path, default=Path(__file__).with_name('release_538_payload.json'))
    p.add_argument('--ignore-send-flags', action='store_true', help='Only verify files; do not inspect current process send flags')
    args = p.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
    errors = verify(args.root, manifest, not args.ignore_send_flags)
    if errors:
        for error in errors:
            print('FAIL:', error)
        print('STOP: do not push. Restore/reconcile and reverify.')
        return 1
    print(f'PASS: {len(manifest["files"])} installed source files match Doorks/Moses 5.38 exactly.')
    print('This check is NOT live provider, production backup, or browser acceptance.')
    return 0

if __name__ == '__main__':
    sys.exit(main())
