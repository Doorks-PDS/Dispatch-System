"""Read-only pre/post compatibility gate for Doorks / Moses 5.54.

Run before unzipping the patch into the project. A mismatch must be reconciled;
never silently overwrite newer local changes. No files are modified.
"""
import argparse
import hashlib
import json
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def verify(root, manifest, phase):
    files = json.loads(manifest.read_text(encoding='utf-8'))['files']
    mismatches = []
    for name, phases in files.items():
        wanted = phases.get(phase)
        got = digest(root / name)
        if got != wanted:
            mismatches.append(name)
    if mismatches:
        print('STOP: Moses 5.54 ' + phase + ' check failed. No files changed by this checker.')
        for path in mismatches:
            print('  Different or unexpected file:', path)
        print('Reconcile local modifications before applying the patch.')
        return 1
    print('PASS: Moses 5.54 ' + phase + ' compatibility for ' + str(len(files)) + ' files; business data untouched.')
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True)
    parser.add_argument('--phase', required=True, choices=('before', 'after'))
    parser.add_argument('--manifest', default=None)
    opts = parser.parse_args()
    source = Path(opts.manifest) if opts.manifest else Path(__file__).with_name('moses_554_manifest.json')
    raise SystemExit(verify(Path(opts.root), source, opts.phase))
