"""Read-only safety validation of a Doorks/Moses drop-in ZIP.

The drop-in must not carry a Render Blueprint, runtime data, credentials or
unsafe archive paths. This check does not authorize production deployment.
"""
from __future__ import annotations

import argparse
import json
from pathlib import PurePosixPath
import zipfile

DENIED_ROOTS = {'.env', '.git', 'data', 'venv', '.venv', '__pycache__'}
DENIED_NAMES = {'render.yaml', '.env', '.env.production', 'credentials.json', 'secrets.json'}


def inspect_package(path: str) -> dict:
    errors = []
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            errors.append('Duplicate archive entries')
        for name in names:
            parts = name.split('/')
            if not name or name.startswith('/') or '\\' in name or any(part in ('', '.', '..') for part in parts):
                errors.append(f'Unsafe archive path: {name}')
                continue
            if parts[0] in DENIED_ROOTS or any(part in DENIED_NAMES for part in parts):
                errors.append(f'Forbidden deployment entry: {name}')
            info = archive.getinfo(name)
            mode = info.external_attr >> 16
            if mode and (mode & 0o170000) == 0o120000:
                errors.append(f'Symlink entry: {name}')
        if archive.testzip() is not None:
            errors.append('ZIP CRC check failed')
    return {'safe_for_source_review': not errors, 'production_deploy_authorized': False,
            'file_count': len(names), 'issues': errors}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive')
    args = parser.parse_args()
    result = inspect_package(args.archive)
    print(json.dumps(result, indent=2))
    if result['issues']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
