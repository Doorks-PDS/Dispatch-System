"""Read-only, fail-closed compatibility audit for a known checkout snapshot.

A checkout whose fingerprints are not registered must NEVER be called safe for
copying snapshot-based files.  This helper makes no changes to disk.
"""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

# No verified baseline fingerprints have been recorded for the user's current
# checkout.  A missing fingerprint is deliberately treated as unsafe, rather
# than silently trusting the current contents.
BASELINE: dict[str, str] = {"main.py": "", "static/app.js": ""}


def inspect_checkout(path: str | Path) -> dict:
    root = Path(path).expanduser().absolute()
    report = {"checkout_root_matches": False, "safe_to_copy_snapshot_based_files": False,
              "files": {}, "git_clean": False}
    try:
        top = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=root,
                             capture_output=True, text=True, check=True).stdout.strip()
        report["checkout_root_matches"] = Path(top).resolve() == root.resolve()
        status = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"],
                                cwd=root, capture_output=True, text=True, check=True).stdout.splitlines()
        # The one permitted untracked file is an optional temporary copy of this helper.
        dirty = [line for line in status if not (line.startswith("?? ") and
                                                  line[3:].strip() == "moses_preflight.py")]
        report["git_clean"] = not bool(dirty)
        for name, digest in BASELINE.items():
            file = root / name
            if file.is_symlink():
                state = "symlink_not_allowed"
            elif not file.is_file():
                state = "missing"
            elif not digest or hashlib.sha256(file.read_bytes()).hexdigest() != digest:
                state = "changed_since_source_snapshot"
            else:
                state = "matches_source_snapshot"
            report["files"][name] = {"status": state}
        report["safe_to_copy_snapshot_based_files"] = (report["checkout_root_matches"]
            and report["git_clean"] and all(f["status"] == "matches_source_snapshot"
                                        for f in report["files"].values()))
    except (OSError, subprocess.SubprocessError):
        pass
    return report
