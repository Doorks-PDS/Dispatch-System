from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import Union

ProjectRoot = Union[str, Path]


def _normalize_project_root(project_root: ProjectRoot) -> Path:
    root = Path(project_root)
    return root if root.is_dir() else root.parent


def get_repo_data_dir(project_root: ProjectRoot) -> Path:
    return _normalize_project_root(project_root) / "data"


def _persistent_root_from_env() -> str:
    return (
        os.getenv("DOORKS_DATA_DIR")
        or os.getenv("RENDER_DISK_ROOT")
        or os.getenv("RENDER_DISK_PATH")
        or ""
    ).strip()


def _looks_like_render_mount(path: Path) -> bool:
    try:
        return str(path).startswith('/var/data')
    except Exception:
        return False


def get_writable_data_dir(project_root: ProjectRoot) -> Path:
    repo_dir = get_repo_data_dir(project_root)
    env_root = _persistent_root_from_env()
    if env_root:
        target = Path(env_root)
        target.mkdir(parents=True, exist_ok=True)
        return target

    default_render_dir = Path('/var/data')
    if default_render_dir.exists() and os.access(default_render_dir, os.W_OK):
        default_render_dir.mkdir(parents=True, exist_ok=True)
        return default_render_dir

    repo_dir.mkdir(parents=True, exist_ok=True)
    return repo_dir


def repo_data_path(project_root: ProjectRoot, *parts: str) -> Path:
    return get_repo_data_dir(project_root).joinpath(*parts)


def writable_data_path(project_root: ProjectRoot, *parts: str) -> Path:
    path = get_writable_data_dir(project_root).joinpath(*parts)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def first_existing_data_path(project_root: ProjectRoot, *parts: str) -> Path:
    writable = get_writable_data_dir(project_root).joinpath(*parts)
    if writable.exists():
        return writable
    return repo_data_path(project_root, *parts)


def bootstrap_data_file(project_root: ProjectRoot, *parts: str) -> Path:
    target = writable_data_path(project_root, *parts)
    source = repo_data_path(project_root, *parts)
    if target != source and (not target.exists()) and source.exists() and source.is_file():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    return target


def bootstrap_data_dir(project_root: ProjectRoot, *parts: str) -> Path:
    target = get_writable_data_dir(project_root).joinpath(*parts)
    source = repo_data_path(project_root, *parts)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target != source and (not target.exists()) and source.exists() and source.is_dir():
        shutil.copytree(source, target)
    else:
        target.mkdir(parents=True, exist_ok=True)
    return target


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + '.', suffix='.tmp', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_name, path)
    finally:
        try:
            if os.path.exists(tmp_name):
                os.remove(tmp_name)
        except Exception:
            pass


def atomic_write_json(path: Path, obj) -> None:
    import json
    backup = path.with_suffix(path.suffix + '.bak')
    try:
        if path.exists():
            backup.write_text(path.read_text(encoding='utf-8'), encoding='utf-8')
    except Exception:
        pass
    atomic_write_text(path, json.dumps(obj, indent=2, ensure_ascii=False))
