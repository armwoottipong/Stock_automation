import os
import time

from ai_image_automation.maintenance import inspect_jobs


def test_cleanup_previews_then_removes_only_stale_job_temps(tmp_path):
    jobs = tmp_path / "jobs" / "abc"
    jobs.mkdir(parents=True)
    stale = jobs / "report.json.tmp"
    stale.write_bytes(b"stale")
    old = time.time() - 9 * 86400
    os.utime(stale, (old, old))
    recent = jobs / "active.json.tmp"
    recent.write_bytes(b"recent")
    output = jobs / "result.png"
    output.write_bytes(b"image")
    outside = tmp_path / "outside.tmp"
    outside.write_bytes(b"private")

    preview = inspect_jobs(tmp_path)
    assert preview["candidate_count"] == 1
    assert preview["candidate_bytes"] == 5
    assert stale.is_file()
    assert preview["disk"]["free_bytes"] > 0
    applied = inspect_jobs(tmp_path, apply=True)
    assert applied["candidate_count"] == 1
    assert not stale.exists()
    assert recent.is_file() and output.is_file() and outside.is_file()
