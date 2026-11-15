from pathlib import Path
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from app.services.moses_storage_readiness import inspect, _mount_info
from app.routers.doorks_assistant import storage_readiness


def test_nonexistent_path_does_not_get_created(tmp_path):
    target = tmp_path / 'no-data'
    result = inspect(str(target), mountinfo_path=str(tmp_path / 'absent'))
    assert not target.exists()
    assert result['directory_exists'] is False
    assert result['durability_verified'] is False
    assert result['deployment_ready'] is False


def test_writable_dir_never_claims_durability(tmp_path):
    result = inspect(str(tmp_path), mountinfo_path=str(tmp_path / 'absent'))
    assert result['directory_exists']
    assert result['durability_verified'] is False


def test_mount_discovery_is_not_durability_proof():
    info = _mount_info(Path('/var/data/jobs'), '11 9 0:1 / / rw - overlay overlay rw\n12 11 0:2 / /var/data rw - ext4 /dev/x rw')
    assert info == {'mount_point': '/var/data', 'dedicated_mount_detected': True}


def test_storage_readiness_requires_admin(tmp_path):
    request = SimpleNamespace(state=SimpleNamespace(auth_user='a', auth_role='technician'),
                              session={'active_platform': 'pds'},
                              app=SimpleNamespace(state=SimpleNamespace(data_dir=str(tmp_path))))
    with pytest.raises(HTTPException) as exc:
        storage_readiness(request)
    assert exc.value.status_code == 403


def test_storage_readiness_is_read_only(tmp_path):
    request = SimpleNamespace(state=SimpleNamespace(auth_user='a', auth_role='office_admin'),
                              session={'active_platform': 'pds'},
                              app=SimpleNamespace(state=SimpleNamespace(data_dir=str(tmp_path))))
    before = list(tmp_path.iterdir())
    result = storage_readiness(request)
    assert result['directory_exists'] and result['durability_verified'] is False
    assert list(tmp_path.iterdir()) == before


def test_expected_disk_mismatch_is_detected_without_mutation(tmp_path):
    expected = tmp_path / 'disk'
    target = tmp_path / 'var' / 'data'
    result = inspect(str(target), mountinfo_path=str(tmp_path / 'absent'), expected_disk_mount=str(expected))
    assert result['disk_path_mismatch'] is True
    assert result['configured_path_under_expected_disk'] is False
    assert not target.exists() and not expected.exists()


def test_existing_disk_child_is_aligned_but_not_durability_proof(tmp_path):
    expected = tmp_path / 'disk'
    target = expected / 'business'
    result = inspect(str(target), mountinfo_path=str(tmp_path / 'absent'), expected_disk_mount=str(expected))
    assert result['configured_path_under_expected_disk'] is True
    assert result['disk_path_mismatch'] is False
    assert result['durability_verified'] is False
    assert not target.exists()


def test_prefix_mimic_is_not_considered_same_disk(tmp_path):
    disk = tmp_path / 'data'
    fake = tmp_path / 'data-backup'
    result = inspect(str(fake), mountinfo_path=str(tmp_path / 'absent'), expected_disk_mount=str(disk))
    assert result['disk_path_mismatch'] is True
