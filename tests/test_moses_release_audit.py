"""Read-only release gate tests (no user's repository or server touched)."""
import subprocess
import zipfile
from pathlib import Path
from scripts.moses_release_audit import audit


def run(*args):
    subprocess.run(args, check=True, capture_output=True)


def checkout(tmp_path):
    root = tmp_path/'repo'
    root.mkdir()
    run('git', '-C', str(root), 'init', '-q', '-b', 'main')
    run('git', '-C', str(root), 'config', 'user.email', 'test@example.com')
    run('git', '-C', str(root), 'config', 'user.name', 'Test')
    (root/'app.py').write_text('original')
    run('git', '-C', str(root), 'add', '.')
    run('git', '-C', str(root), 'commit', '-qm', 'baseline')
    return root


def package(tmp_path, **files):
    path = tmp_path/'patch.zip'
    with zipfile.ZipFile(path, 'w') as z:
        for name, content in files.items():
            z.writestr(name, content)
    return path


def test_clean_repo_reports_conflict_and_never_authorizes(tmp_path):
    root = checkout(tmp_path)
    result = audit(root, package(tmp_path, **{'app.py': 'newer'}))
    assert result['status'] == 'REVIEW_REQUIRED'
    assert result['deploy_authorized'] is False
    assert result['overlapping_files'] == ['app.py']
    assert (root/'app.py').read_text() == 'original'


def test_clean_repo_new_file_no_overlap(tmp_path):
    root = checkout(tmp_path)
    result = audit(root, package(tmp_path, **{'feature.py': 'safe'}))
    assert result['status'] == 'REVIEW_REQUIRED'
    assert not result['overlapping_files']
    assert not (root/'feature.py').exists()


def test_dirty_worktree_blocked(tmp_path):
    root = checkout(tmp_path)
    (root/'app.py').write_text('uncommitted')
    result = audit(root, package(tmp_path, **{'feature.py': 'safe'}))
    assert result['status'] == 'STOP'
    assert 'not clean' in ' '.join(result['issues'])


def test_non_main_blocked(tmp_path):
    root = checkout(tmp_path)
    run('git', '-C', str(root), 'checkout', '-qb', 'feature')
    result = audit(root, package(tmp_path, **{'feature.py': 'safe'}))
    assert result['status'] == 'STOP'


def test_traversal_blocked(tmp_path):
    root = checkout(tmp_path)
    result = audit(root, package(tmp_path, **{'../bad.py': 'oops'}))
    assert result['status'] == 'STOP'
    assert not (tmp_path/'bad.py').exists()


def test_zip_duplicate_rejected(tmp_path):
    root = checkout(tmp_path)
    path = tmp_path/'duplicate.zip'
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', UserWarning)
        with zipfile.ZipFile(path, 'w') as z:
            z.writestr('a.py', 'one')
            z.writestr('a.py', 'two')
    assert audit(root, path)['status'] == 'STOP'
