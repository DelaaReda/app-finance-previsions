#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "cleanup_stale_role_locks.sh"


class CleanupStaleRoleLocksTests(unittest.TestCase):
    def test_cleans_legacy_scrum_master_lock_without_live_holder(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            state_dir = base / "state"
            runtime_lock_dir = base / "runtime-locks"
            state_dir.mkdir(parents=True, exist_ok=True)
            runtime_lock_dir.mkdir(parents=True, exist_ok=True)

            lock = state_dir / "scrum_master.lock"
            meta = state_dir / "scrum_master.lock.meta"
            lock.write_text("", encoding="utf-8")
            old_ts = int(__import__("time").time()) - 7200
            meta.write_text(
                f"pid=999999 host=test start_epoch={old_ts} start_utc=2026-03-06T00:00:00Z role=scrum_master layer=run\n",
                encoding="utf-8",
            )
            os.utime(lock, (old_ts, old_ts))
            os.utime(meta, (old_ts, old_ts))

            env = os.environ.copy()
            env["FC_ROLE_STATE_DIR"] = str(state_dir)
            env["FC_RUNTIME_LOCK_DIR"] = str(runtime_lock_dir)
            env["FC_STALE_LOCK_MINUTES"] = "1"
            env["FC_STALE_LOCK_LOG"] = str(base / "cleanup.log")
            cp = subprocess.run(
                ["bash", str(SCRIPT)],
                cwd=str(ROOT),
                text=True,
                capture_output=True,
                check=False,
                env=env,
            )
            self.assertEqual(cp.returncode, 0, msg=cp.stderr)
            self.assertFalse(lock.exists(), msg="legacy scrum_master.lock should be removed")
            self.assertFalse(meta.exists(), msg="legacy scrum_master.lock.meta should be removed")


if __name__ == "__main__":
    unittest.main()
