# OpenClaw Config Lock (Model Protection)

## Goal

Prevent non-director agents (cron roles, delivery lanes, etc.) from changing the **OpenClaw global config** (especially model defaults) by making the config file immutable.

This is necessary because all agents run under the same Linux user, so file permissions alone cannot enforce separation.

## What is locked

- `~/.openclaw/openclaw.json`

## Why this works

- `chattr +i` sets the immutable bit on ext4.
- Even the same user cannot edit/rename/delete the file unless the bit is removed.
- Only `sudo` can remove it.

## Commands

### Lock

```bash
scripts/exec_safe.sh --workdir /home/venom/analyse-financiere -- "bash scripts/openclaw_config_lock.sh"
```

### Unlock (for intentional config edits)

```bash
scripts/exec_safe.sh --workdir /home/venom/analyse-financiere -- "bash scripts/openclaw_config_unlock.sh"
```

### Edit flow

1) unlock
2) `openclaw config set ...`
3) lock

## Resume guard integration

`scripts/vm_resume_guard.sh` ensures the lock is present after VM pause/resume.

## Notes

- If a tool tries to write config while locked, you will see a clear error. This is expected.
- The lock should remain on by default to protect the director model configuration.
