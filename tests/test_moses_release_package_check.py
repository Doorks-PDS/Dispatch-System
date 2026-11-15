"""No infrastructure or runtime data may be hidden in the drop-in archive."""
import zipfile
from scripts.moses_release_package_check import inspect_package


def _zip(tmp_path, names):
    p = tmp_path / 'source.zip'
    with zipfile.ZipFile(p, 'w') as archive:
        for name in names:
            archive.writestr(name, 'test')
    return str(p)


def test_safe_code_patch(tmp_path):
    result = inspect_package(_zip(tmp_path, ['app/services/moses_agent.py', 'static/sdc_software.html']))
    assert result['safe_for_source_review'] is True
    assert result['production_deploy_authorized'] is False


def test_reject_blueprint_and_runtime_data(tmp_path):
    result = inspect_package(_zip(tmp_path, ['render.yaml', 'data/customers.json', 'app/main.py']))
    assert not result['safe_for_source_review']
    assert len(result['issues']) == 2


def test_reject_unsafe_and_secret_paths(tmp_path):
    result = inspect_package(_zip(tmp_path, ['../data.json', '.env', 'app/../../secrets.json']))
    assert not result['safe_for_source_review']
    assert len(result['issues']) == 3
