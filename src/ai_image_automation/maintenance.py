"""Inspect disk use and remove only stale atomic-write files under jobs/."""

from __future__ import annotations

import shutil
import time
from pathlib import Path


def inspect_jobs(root: Path, *, older_than_days: int = 7, apply: bool = False) -> dict:
    if older_than_days < 1:
        raise ValueError("older_than_days must be at least 1")
    root = root.resolve()
    jobs = root / "jobs"
    if not jobs.is_dir() or jobs.is_symlink():
        raise ValueError("Expected a real jobs directory under the project root")
    cutoff = time.time() - older_than_days * 86400
    candidates = []
    for path in jobs.rglob("*"):
        if not path.is_file() or path.is_symlink() or not path.name.endswith(".tmp"):
            continue
        resolved = path.resolve()
        if not resolved.is_relative_to(jobs) or path.stat().st_mtime > cutoff:
            continue
        candidates.append(path)
    candidates.sort()
    entries = [{"path": str(path.relative_to(root)), "bytes": path.stat().st_size} for path in candidates]
    if apply:
        for path in candidates:
            # Recheck immediately before unlinking; never follow a swapped symlink.
            if path.is_symlink() or not path.resolve().is_relative_to(jobs):
                raise ValueError("Cleanup candidate changed during inspection")
            path.unlink()
    usage = shutil.disk_usage(root)
    return {
        "mode": "apply" if apply else "preview",
        "older_than_days": older_than_days,
        "candidate_count": len(entries),
        "candidate_bytes": sum(entry["bytes"] for entry in entries),
        "candidates": entries,
        "disk": {"total_bytes": usage.total, "used_bytes": usage.used, "free_bytes": usage.free},
    }
