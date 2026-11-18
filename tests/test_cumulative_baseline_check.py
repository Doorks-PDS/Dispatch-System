import hashlib
import importlib.util
import pathlib

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / 'scripts/check_cumulative_baseline.py'
spec = importlib.util.spec_from_file_location('cumulative_baseline', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_baseline_matches(tmp_path):
    (tmp_path/'app').mkdir()
    (tmp_path/'app/a.py').write_bytes(b'baseline')
    data={'paths': {'app/a.py': {'baseline_sha256': hashlib.sha256(b'baseline').hexdigest()}, 'app/new.py': {'baseline_sha256': None}}}
    assert module.inspect(tmp_path, data) == []


def test_changed_file_blocks_overwrite(tmp_path):
    (tmp_path/'a.py').write_bytes(b'newer local content')
    data={'paths': {'a.py': {'baseline_sha256': hashlib.sha256(b'older').hexdigest()}}}
    assert 'LOCAL FILE CHANGED: a.py' in module.inspect(tmp_path, data)


def test_added_file_conflict_and_missing_baseline(tmp_path):
    (tmp_path/'existing.py').write_bytes(b'custom')
    data={'paths': {'existing.py': {'baseline_sha256': None}, 'missing.py': {'baseline_sha256': 'abc'}}}
    result = module.inspect(tmp_path, data)
    assert 'NEW FILE CONFLICT: existing.py' in result
    assert 'MISSING BASELINE FILE: missing.py' in result


def test_symlink_is_rejected(tmp_path):
    (tmp_path/'link').symlink_to(tmp_path.parent)
    data={'paths': {'link': {'baseline_sha256': None}}}
    assert module.inspect(tmp_path,data)
