from pathlib import Path
from scripts.pds_storage_preflight import inspect_storage


def test_read_only_accurate_file_listing(tmp_path):
    (tmp_path/'calendar').mkdir()
    (tmp_path/'calendar'/'jobs.json').write_bytes(b'abc')
    (tmp_path/'calendar'/'old.bak').write_bytes(b'123456')
    (tmp_path/'receipts').mkdir()
    (tmp_path/'receipts'/'r.pdf').write_bytes(b'xy')
    before = {p.relative_to(tmp_path).as_posix(): p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    report = inspect_storage(tmp_path, top_n=2, warning_percent=0)
    assert report['directory_bytes']['calendar'] == 9
    assert report['directory_bytes']['receipts'] == 2
    assert [x['path'] for x in report['largest_files']] == ['calendar/old.bak', 'calendar/jobs.json']
    assert report['read_only'] is True
    assert report['disk_warning'] is True
    assert before == {p.relative_to(tmp_path).as_posix(): p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}


def test_symlinks_outside_storage_not_traversed(tmp_path):
    data=tmp_path/'data'; data.mkdir()
    external=tmp_path/'external'; external.mkdir()
    (external/'secret.txt').write_text('private')
    (data/'other').symlink_to(external, target_is_directory=True)
    (data/'file').symlink_to(external/'secret.txt')
    report=inspect_storage(data)
    assert report['files_counted']==0
    assert report['largest_files']==[]


def test_missing_directory_rejected(tmp_path):
    import pytest
    with pytest.raises(FileNotFoundError):
        inspect_storage(tmp_path/'missing')


def test_calendar_breakdown_and_bounded_largest(tmp_path):
    (tmp_path / 'calendar' / 'uploads').mkdir(parents=True)
    (tmp_path / 'calendar' / 'snapshots').mkdir()
    for i in range(150):
        (tmp_path / 'calendar' / 'uploads' / f'{i}.bin').write_bytes(b'a' * (i + 1))
    (tmp_path / 'calendar' / 'snapshots' / 'old.json').write_bytes(b'z' * 4)
    result = inspect_storage(tmp_path, top_n=3)
    assert result['files_counted'] == 151
    assert result['calendar_breakdown_bytes']['uploads'] == sum(range(1, 151))
    assert result['calendar_breakdown_bytes']['snapshots'] == 4
    assert [x['bytes'] for x in result['largest_files']] == [150, 149, 148]
    assert inspect_storage(tmp_path, top_n=0)['largest_files'] == []
