"""The backup and restore scripts, run against a pretend ``docker`` so no database is needed.

This checks the scripts' own logic: what they refuse to keep, when they report failure, and that
the scratch database is always removed. The real restore is proven on the server by
``deploy/restore-test.sh`` (see docs/operations.md).
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
BACKUP = ROOT / "deploy" / "backup.sh"
RESTORE = ROOT / "deploy" / "restore-test.sh"

pytestmark = pytest.mark.skipif(shutil.which("bash") is None, reason="bash is required")

FAKE_DOCKER = """#!/bin/bash
echo "docker $*" >> "$MOCK_LOG"
args="$*"
case "$args" in
  *pg_dump*) [ -n "${MOCK_DUMP_FAIL:-}" ] && exit 1; echo "SELECT 1;" ;;
  *"count(*) FROM"*)
      db=$(echo "$args" | sed -n 's/.*-d \\([a-z_]*\\).*/\\1/p')
      if [ "$db" = "restore_check" ]; then
        echo "${MOCK_RESTORED:-5}"
      else
        echo "${MOCK_LIVE:-5}"
      fi ;;
  *" -c "*) : ;;
  *) cat > /dev/null ;;
esac
"""


@pytest.fixture
def env(tmp_path):
    (tmp_path / "bin").mkdir()
    (tmp_path / "project").mkdir()
    (tmp_path / "backups").mkdir()
    docker = tmp_path / "bin" / "docker"
    docker.write_text(FAKE_DOCKER)
    docker.chmod(0o755)
    return {
        **os.environ,
        "PATH": f"{tmp_path / 'bin'}:{os.environ['PATH']}",
        "MAPLE_DIR": str(tmp_path / "project"),
        "MAPLE_BACKUP_DIR": str(tmp_path / "backups"),
        "MOCK_LOG": str(tmp_path / "docker.log"),
    }


def run(script, env, *args):
    return subprocess.run(
        ["bash", str(script), *args],
        env=env,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        timeout=30,
    )


def test_scripts_are_valid_bash():
    for script in (BACKUP, RESTORE):
        assert subprocess.run(["bash", "-n", str(script)]).returncode == 0


def test_backup_writes_a_readable_archive_and_no_temp_file(env, tmp_path):
    result = run(BACKUP, env)
    assert result.returncode == 0, result.stderr
    files = list((tmp_path / "backups").iterdir())
    assert len(files) == 1 and files[0].name.endswith(".sql.gz")
    assert subprocess.run(["gzip", "-t", str(files[0])]).returncode == 0


def test_a_failed_dump_leaves_no_backup_behind(env, tmp_path):
    result = run(BACKUP, {**env, "MOCK_DUMP_FAIL": "1"})
    assert result.returncode != 0
    assert not list((tmp_path / "backups").glob("*.sql.gz"))


def test_old_backups_are_pruned_and_recent_ones_kept(env, tmp_path):
    old, recent = (
        tmp_path / "backups" / "maplemetrics-old.sql.gz",
        tmp_path / "backups" / "maplemetrics-new.sql.gz",
    )
    for path in (old, recent):
        path.write_bytes(b"x")
    forty_days_ago = old.stat().st_mtime - 40 * 86400
    os.utime(old, (forty_days_ago, forty_days_ago))
    assert run(BACKUP, env).returncode == 0
    assert not old.exists() and recent.exists()


def test_restore_passes_when_counts_match(env):
    assert run(BACKUP, env).returncode == 0
    result = run(RESTORE, env)
    assert result.returncode == 0, result.stderr
    assert "PASS: the backup restores and matches" in result.stdout
    assert "warehouse_observation" in result.stdout


def test_restore_reports_differences_without_failing(env):
    assert run(BACKUP, env).returncode == 0
    result = run(RESTORE, {**env, "MOCK_LIVE": "9"})
    assert result.returncode == 0
    assert "PASS WITH DIFFERENCES" in result.stdout


def test_restore_fails_when_the_restored_database_is_empty(env):
    assert run(BACKUP, env).returncode == 0
    result = run(RESTORE, {**env, "MOCK_RESTORED": "0"})
    assert result.returncode == 1
    assert "FAIL" in result.stderr


def test_restore_fails_clearly_with_no_backup(env):
    result = run(RESTORE, env)
    assert result.returncode == 1
    assert "no backup file found" in result.stderr


def test_restore_rejects_a_corrupt_archive(env, tmp_path):
    bad = tmp_path / "backups" / "maplemetrics-2099-01-01.sql.gz"
    bad.write_text("not gzip")
    result = run(RESTORE, env)
    assert result.returncode != 0
    assert "not in gzip format" in result.stderr


def test_scratch_database_is_removed_even_when_the_restore_fails(env):
    assert run(BACKUP, env).returncode == 0
    run(RESTORE, {**env, "MOCK_RESTORED": "0"})
    log = Path(env["MOCK_LOG"]).read_text()
    assert log.count("DROP DATABASE IF EXISTS restore_check") >= 2
    assert log.rstrip().splitlines()[-1].endswith("DROP DATABASE IF EXISTS restore_check")
