"""Preflight must fail closed and must never edit the checkout."""
import hashlib
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from moses_preflight import inspect_checkout, BASELINE


def test_preflight_blocks_modified_application_files(tmp_path):
    (tmp_path / 'static').mkdir()
    (tmp_path / 'main.py').write_text('newer code')
    (tmp_path / 'static/app.js').write_text('newer code')
    subprocess.run(['git', 'init', '-q', '-b', 'main'], cwd=tmp_path, check=True)
    subprocess.run(['git', 'add', '.'], cwd=tmp_path, check=True)
    subprocess.run(['git', '-c', 'user.name=Test', '-c', 'user.email=test@example.com', 'commit', '-qm', 'initial'], cwd=tmp_path, check=True)
    original = (tmp_path / 'main.py').read_bytes()
    report = inspect_checkout(tmp_path)
    assert report['safe_to_copy_snapshot_based_files'] is False
    assert report['files']['main.py']['status'] == 'changed_since_source_snapshot'
    assert (tmp_path / 'main.py').read_bytes() == original


def test_preflight_blocks_dirty_checkout(tmp_path, monkeypatch):
    (tmp_path / 'static').mkdir()
    (tmp_path / 'main.py').write_bytes(b'baseline-main')
    (tmp_path / 'static/app.js').write_bytes(b'baseline-js')
    monkeypatch.setitem(BASELINE, 'main.py', hashlib.sha256(b'baseline-main').hexdigest())
    monkeypatch.setitem(BASELINE, 'static/app.js', hashlib.sha256(b'baseline-js').hexdigest())
    subprocess.run(['git', 'init', '-q', '-b', 'main'], cwd=tmp_path, check=True)
    subprocess.run(['git', 'add', '.'], cwd=tmp_path, check=True)
    subprocess.run(['git', '-c', 'user.name=Test', '-c', 'user.email=test@example.com', 'commit', '-qm', 'initial'], cwd=tmp_path, check=True)
    assert inspect_checkout(tmp_path)['safe_to_copy_snapshot_based_files'] is True
    (tmp_path / 'other.txt').write_text('uncommitted')
    assert inspect_checkout(tmp_path)['safe_to_copy_snapshot_based_files'] is False


def test_preflight_blocks_subdirectory_even_with_matching_files(tmp_path, monkeypatch):
    (tmp_path / 'nested/static').mkdir(parents=True)
    (tmp_path / 'nested/main.py').write_bytes(b'baseline-main')
    (tmp_path / 'nested/static/app.js').write_bytes(b'baseline-js')
    monkeypatch.setitem(BASELINE, 'main.py', hashlib.sha256(b'baseline-main').hexdigest())
    monkeypatch.setitem(BASELINE, 'static/app.js', hashlib.sha256(b'baseline-js').hexdigest())
    subprocess.run(['git', 'init', '-q', '-b', 'main'], cwd=tmp_path, check=True)
    subprocess.run(['git', 'add', '.'], cwd=tmp_path, check=True)
    subprocess.run(['git', '-c', 'user.name=Test', '-c', 'user.email=test@example.com', 'commit', '-qm', 'initial'], cwd=tmp_path, check=True)
    result = inspect_checkout(tmp_path / 'nested')
    assert result['checkout_root_matches'] is False
    assert result['safe_to_copy_snapshot_based_files'] is False


def test_preflight_blocks_symlink_source_files(tmp_path, monkeypatch):
    (tmp_path / 'static').mkdir()
    (tmp_path / 'real_main.py').write_bytes(b'baseline-main')
    (tmp_path / 'main.py').symlink_to('real_main.py')
    (tmp_path / 'static/app.js').write_bytes(b'baseline-js')
    monkeypatch.setitem(BASELINE, 'main.py', hashlib.sha256(b'baseline-main').hexdigest())
    monkeypatch.setitem(BASELINE, 'static/app.js', hashlib.sha256(b'baseline-js').hexdigest())
    subprocess.run(['git', 'init', '-q', '-b', 'main'], cwd=tmp_path, check=True)
    subprocess.run(['git', 'add', '.'], cwd=tmp_path, check=True)
    subprocess.run(['git', '-c', 'user.name=Test', '-c', 'user.email=test@example.com', 'commit', '-qm', 'initial'], cwd=tmp_path, check=True)
    result = inspect_checkout(tmp_path)
    assert result['files']['main.py']['status'] == 'symlink_not_allowed'
    assert result['safe_to_copy_snapshot_based_files'] is False


def test_preflight_allows_only_its_own_untracked_script(tmp_path, monkeypatch):
    (tmp_path / 'static').mkdir()
    (tmp_path / 'main.py').write_bytes(b'baseline-main')
    (tmp_path / 'static/app.js').write_bytes(b'baseline-js')
    monkeypatch.setitem(BASELINE, 'main.py', hashlib.sha256(b'baseline-main').hexdigest())
    monkeypatch.setitem(BASELINE, 'static/app.js', hashlib.sha256(b'baseline-js').hexdigest())
    subprocess.run(['git', 'init', '-q', '-b', 'main'], cwd=tmp_path, check=True)
    subprocess.run(['git', 'add', 'main.py', 'static/app.js'], cwd=tmp_path, check=True)
    subprocess.run(['git', '-c', 'user.name=Test', '-c', 'user.email=test@example.com', 'commit', '-qm', 'initial'], cwd=tmp_path, check=True)
    (tmp_path / 'moses_preflight.py').write_text('# temporary preflight copy')
    assert inspect_checkout(tmp_path)['safe_to_copy_snapshot_based_files'] is True
    (tmp_path / 'unrelated.txt').write_text('unexpected')
    assert inspect_checkout(tmp_path)['safe_to_copy_snapshot_based_files'] is False


def test_preflight_blocks_modified_tracked_preflight(tmp_path, monkeypatch):
    (tmp_path / 'static').mkdir()
    (tmp_path / 'main.py').write_bytes(b'baseline-main')
    (tmp_path / 'static/app.js').write_bytes(b'baseline-js')
    (tmp_path / 'moses_preflight.py').write_text('tracked original')
    monkeypatch.setitem(BASELINE, 'main.py', hashlib.sha256(b'baseline-main').hexdigest())
    monkeypatch.setitem(BASELINE, 'static/app.js', hashlib.sha256(b'baseline-js').hexdigest())
    subprocess.run(['git', 'init', '-q', '-b', 'main'], cwd=tmp_path, check=True)
    subprocess.run(['git', 'add', '.'], cwd=tmp_path, check=True)
    subprocess.run(['git', '-c', 'user.name=Test', '-c', 'user.email=test@example.com', 'commit', '-qm', 'initial'], cwd=tmp_path, check=True)
    (tmp_path / 'moses_preflight.py').write_text('modified tracked file')
    assert inspect_checkout(tmp_path)['safe_to_copy_snapshot_based_files'] is False
