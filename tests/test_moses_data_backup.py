from pathlib import Path
import io
import json
import zipfile
import pytest

from scripts.moses_data_backup import snapshot, verify, MANIFEST


def test_snapshot_verify_isolated_restore(tmp_path):
    src = tmp_path / 'data'; src.mkdir()
    (src / 'pds').mkdir(); (src / 'pds' / 'records.json').write_bytes(b'{"jobs": [1, 2]}')
    (src / 'sdc').mkdir(); (src / 'sdc' / 'legacy.bin').write_bytes(bytes(range(256)))
    out = tmp_path / 'backup' / 'snapshot.zip'
    report = snapshot(src, out)
    assert report['file_count'] == 2
    assert verify(out)['isolated_restore_verified']
    assert (src / 'pds' / 'records.json').read_bytes() == b'{"jobs": [1, 2]}'
    assert not (src / MANIFEST).exists()


def test_no_overwrite_or_source_destination(tmp_path):
    src = tmp_path / 'data'; src.mkdir(); (src / 'a').write_text('x')
    with pytest.raises(ValueError): snapshot(src, src / 'snapshot.zip')
    out = tmp_path / 'a.zip'; snapshot(src, out)
    with pytest.raises(FileExistsError): snapshot(src, out)


def test_reject_symlink(tmp_path):
    src = tmp_path / 'data'; src.mkdir(); (src / 'link').symlink_to(tmp_path)
    with pytest.raises(ValueError, match='Symlink'):
        snapshot(src, tmp_path / 'backup.zip')


def test_detect_archive_tampering(tmp_path):
    src = tmp_path / 'data'; src.mkdir(); (src / 'a.txt').write_text('correct')
    out = tmp_path / 'good.zip'; snapshot(src, out)
    bad = tmp_path / 'bad.zip'
    with zipfile.ZipFile(out) as zin, zipfile.ZipFile(bad, 'w') as zout:
        for name in zin.namelist():
            zout.writestr(name, b'tampered' if name == 'a.txt' else zin.read(name))
    with pytest.raises(ValueError, match='Checksum'):
        verify(bad)


def test_reject_zip_slip(tmp_path):
    out = tmp_path / 'bad.zip'
    with zipfile.ZipFile(out, 'w') as z:
        z.writestr('../escape', b'x')
        z.writestr(MANIFEST, json.dumps({'format':'doorks-data-backup-v1','files':[{'path':'../escape','size':1,'sha256':'x'}]}))
    with pytest.raises(ValueError, match='Unsafe'):
        verify(out)


def test_reject_symlinked_source_directory(tmp_path):
    src = tmp_path / 'real-data'; src.mkdir(); (src / 'records.json').write_text('{}')
    alias = tmp_path / 'alias'; alias.symlink_to(src, target_is_directory=True)
    with pytest.raises(ValueError, match='symlink'):
        snapshot(alias, tmp_path / 'backup.zip')
    assert not (tmp_path / 'backup.zip').exists()


def test_snapshot_rejects_new_files_during_archive_creation(tmp_path, monkeypatch):
    src = tmp_path / 'data'; src.mkdir(); (src / 'records.json').write_text('{}')
    out = tmp_path / 'backup.zip'
    real_inventory = __import__('scripts.moses_data_backup', fromlist=['_source_inventory'])._source_inventory
    calls = {'count': 0}

    def inventory_with_race(source):
        calls['count'] += 1
        if calls['count'] == 2:
            (src / 'new-record.json').write_text('{"created":true}')
        return real_inventory(source)

    monkeypatch.setattr('scripts.moses_data_backup._source_inventory', inventory_with_race)
    with pytest.raises(RuntimeError, match='changed during snapshot'):
        snapshot(src, out)
    assert not out.exists()
    assert (src / 'records.json').read_text() == '{}'


def test_snapshot_rejects_deleted_files_during_verification(tmp_path, monkeypatch):
    src = tmp_path / 'data'; src.mkdir(); (src / 'records.json').write_text('{}')
    out = tmp_path / 'backup.zip'
    real_inventory = __import__('scripts.moses_data_backup', fromlist=['_source_inventory'])._source_inventory
    calls = {'count': 0}

    def inventory_with_race(source):
        calls['count'] += 1
        if calls['count'] == 3:
            (src / 'records.json').unlink()
        return real_inventory(source)

    monkeypatch.setattr('scripts.moses_data_backup._source_inventory', inventory_with_race)
    with pytest.raises(RuntimeError, match='changed during snapshot verification'):
        snapshot(src, out)
    assert not out.exists()
