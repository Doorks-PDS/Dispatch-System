"""Read-only Moses deployment preflight for the current Git checkout.

Usage: python scripts/moses_release_audit.py /path/to/current/checkout /path/to/cumulative.zip
Exit 0: structural preflight only; manual merge and live tests STILL required.
Exit 2: stop / do not deploy.
"""
from __future__ import annotations
import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path, PurePosixPath


def git(checkout: Path, *args: str) -> str:
    p = subprocess.run(['git', '-C', str(checkout), *args], text=True, capture_output=True, check=False)
    if p.returncode:
        raise ValueError('Git validation failed: ' + ' '.join(args))
    return p.stdout.strip()


def audit(checkout: Path, package: Path) -> dict:
    result = {'status': 'STOP', 'deploy_authorized': False, 'issues': [], 'warnings': [], 'package_files': 0, 'overlapping_files': []}
    if not checkout.is_dir() or not package.is_file():
        result['issues'].append('Checkout folder or cumulative ZIP is missing')
        return result
    try:
        if Path(git(checkout, 'rev-parse', '--show-toplevel')).resolve() != checkout.resolve():
            result['issues'].append('Checkout must be the Git repository root')
        if git(checkout, 'branch', '--show-current') != 'main':
            result['issues'].append('Checkout is not on main')
        result['checkout_sha'] = git(checkout, 'rev-parse', 'HEAD')
        dirty = git(checkout, 'status', '--porcelain', '--untracked-files=normal')
        if dirty:
            result['issues'].append('Git working tree is not clean; preserve local changes before continuing')
        with zipfile.ZipFile(package) as z:
            if z.testzip() is not None:
                result['issues'].append('ZIP CRC check failed')
            infos = [i for i in z.infolist() if not i.is_dir()]
            result['package_files'] = len(infos)
            names = [i.filename for i in infos]
            if len(set(names)) != len(names):
                result['issues'].append('ZIP has duplicate file paths')
            for info in infos:
                part = PurePosixPath(info.filename)
                if (part.is_absolute() or '..' in part.parts or '\\' in info.filename or
                    part.parts[0] == '.' or not part.parts):
                    result['issues'].append('Unsafe ZIP path detected')
                    break
                # ZIP Unix mode symlink flag: do not permit links in a release patch.
                if ((info.external_attr >> 16) & 0o170000) == 0o120000:
                    result['issues'].append('ZIP contains a symbolic link')
                    break
            for name in names:
                target = checkout.joinpath(*PurePosixPath(name).parts)
                if target.is_symlink():
                    result['issues'].append('Checkout has symlink at patch path: ' + name)
                    continue
                if target.is_file():
                    digest_local = hashlib.sha256(target.read_bytes()).hexdigest()
                    digest_patch = hashlib.sha256(z.read(name)).hexdigest()
                    if digest_local != digest_patch:
                        result['overlapping_files'].append(name)
            if result['overlapping_files']:
                result['warnings'].append('Existing files differ from the patch. Review each diff/merge; NEVER blindly overwrite.')
            result['warnings'].append('This preflight cannot verify Render persistence, the running commit, environment secrets, providers, or browser behavior.')
    except (ValueError, OSError, zipfile.BadZipFile, IndexError) as error:
        result['issues'].append(str(error))
    result['status'] = 'STOP' if result['issues'] else 'REVIEW_REQUIRED'
    return result


def main() -> int:
    if len(sys.argv) != 3:
        print('Usage: python scripts/moses_release_audit.py <checkout> <cumulative-zip>', file=sys.stderr)
        return 2
    result = audit(Path(sys.argv[1]), Path(sys.argv[2]))
    print(json.dumps(result, indent=2))
    # By design, never return deployment authorization.
    return 2 if result['issues'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
