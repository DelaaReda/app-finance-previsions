from __future__ import annotations

import json
import os
import shlex
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_AWS_APP_HOST = "3.98.20.77"
DEFAULT_AWS_APP_USER = "ubuntu"
DEFAULT_AWS_APP_DIR = f"/home/{DEFAULT_AWS_APP_USER}/analyse-financiere"
DEFAULT_MAINTENANCE_MAX_AGE_S = 300


def resolve_aws_ssh_key(explicit: str | None = None) -> str | None:
    candidates = [
        explicit or "",
        os.environ.get("AWS_APP_SSH_KEY", ""),
        os.environ.get("AWS_SYNC_KEY", ""),
        os.path.join(Path.home(), ".ssh", "id_aws_lightsail"),
        "/home/venom/.ssh/id_aws_lightsail",
        "/Users/venom/.ssh/id_aws_lightsail",
    ]
    for candidate in candidates:
        token = str(candidate or "").strip()
        if token and Path(token).is_file():
            return token
    return None


def _runtime_lock_meta_path(app_dir: str) -> str:
    base = str(app_dir or DEFAULT_AWS_APP_DIR).rstrip("/")
    return f"{base}/logs-codex-runs/finance-copilot-runtime.lock.meta"


def _parse_runtime_lock_meta(raw: str) -> dict[str, Any]:
    text = str(raw or "").strip()
    if not text:
        return {}
    values: dict[str, Any] = {}
    for token in text.split():
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        values[key.strip()] = value.strip()
    if "start_epoch" in values:
        try:
            values["start_epoch"] = int(str(values["start_epoch"]).strip())
        except (TypeError, ValueError):
            values["start_epoch"] = None
    return values


def probe_remote_runtime_maintenance(
    *,
    host: str | None = None,
    user: str | None = None,
    app_dir: str | None = None,
    key_path: str | None = None,
    max_age_s: int = DEFAULT_MAINTENANCE_MAX_AGE_S,
    ssh_timeout_s: float = 5.0,
) -> dict[str, Any]:
    host = str(host or os.environ.get("AWS_APP_HOST") or DEFAULT_AWS_APP_HOST).strip() or DEFAULT_AWS_APP_HOST
    user = str(user or os.environ.get("AWS_APP_USER") or DEFAULT_AWS_APP_USER).strip() or DEFAULT_AWS_APP_USER
    app_dir = str(app_dir or os.environ.get("AWS_APP_DIR") or DEFAULT_AWS_APP_DIR).strip() or DEFAULT_AWS_APP_DIR
    key = resolve_aws_ssh_key(key_path)
    meta_path = _runtime_lock_meta_path(app_dir)
    base_payload: dict[str, Any] = {
        "maintenance_active": False,
        "maintenance_reason": "none",
        "maintenance_source": "remote_runtime_lock_meta",
        "maintenance_command": "",
        "maintenance_pid": "",
        "maintenance_host": "",
        "maintenance_age_s": None,
        "maintenance_meta_path": meta_path,
        "maintenance_probe_error": "",
    }
    local_meta_path = Path(meta_path)
    if local_meta_path.is_file():
        try:
            raw = local_meta_path.read_text(encoding="utf-8", errors="replace").strip()
        except Exception as exc:
            base_payload["maintenance_probe_error"] = f"local_meta_read_error:{type(exc).__name__}"
            raw = ""
        meta = _parse_runtime_lock_meta(raw)
        if meta:
            start_epoch = meta.get("start_epoch")
            age_s: int | None = None
            if isinstance(start_epoch, int) and start_epoch > 0:
                age_s = max(0, int(time.time()) - start_epoch)
            maintenance_active = bool(meta) and (age_s is None or age_s <= max(1, int(max_age_s)))
            base_payload.update(
                {
                    "maintenance_active": maintenance_active,
                    "maintenance_reason": "runtime_restart_in_progress" if maintenance_active else "stale_runtime_lock_meta",
                    "maintenance_source": "local_runtime_lock_meta",
                    "maintenance_command": str(meta.get("command") or "").strip(),
                    "maintenance_pid": str(meta.get("pid") or "").strip(),
                    "maintenance_host": str(meta.get("host") or "").strip(),
                    "maintenance_age_s": age_s,
                }
            )
            return base_payload
    if not key:
        base_payload["maintenance_probe_error"] = "ssh_key_not_found"
        return base_payload

    ssh_cmd = [
        "ssh",
        "-i",
        key,
        "-o",
        "StrictHostKeyChecking=accept-new",
        "-o",
        "ServerAliveInterval=30",
        "-o",
        "ServerAliveCountMax=3",
        f"{user}@{host}",
        f"if [ -f {shlex.quote(meta_path)} ]; then cat {shlex.quote(meta_path)}; fi",
    ]
    try:
        cp = subprocess.run(
            ssh_cmd,
            text=True,
            capture_output=True,
            check=False,
            timeout=max(1.0, float(ssh_timeout_s)),
        )
    except Exception as exc:
        base_payload["maintenance_probe_error"] = f"ssh_error:{type(exc).__name__}"
        return base_payload

    raw = str(cp.stdout or "").strip()
    if cp.returncode not in {0, 1} and not raw:
        stderr = str(cp.stderr or "").strip()
        base_payload["maintenance_probe_error"] = f"ssh_rc_{cp.returncode}:{stderr[:120]}"
        return base_payload

    meta = _parse_runtime_lock_meta(raw)
    if not meta:
        return base_payload

    start_epoch = meta.get("start_epoch")
    age_s: int | None = None
    if isinstance(start_epoch, int) and start_epoch > 0:
        age_s = max(0, int(time.time()) - start_epoch)

    maintenance_active = bool(meta) and (age_s is None or age_s <= max(1, int(max_age_s)))
    base_payload.update(
        {
            "maintenance_active": maintenance_active,
            "maintenance_reason": "runtime_restart_in_progress" if maintenance_active else "stale_runtime_lock_meta",
            "maintenance_command": str(meta.get("command") or "").strip(),
            "maintenance_pid": str(meta.get("pid") or "").strip(),
            "maintenance_host": str(meta.get("host") or "").strip(),
            "maintenance_age_s": age_s,
        }
    )
    return base_payload


def probe_public_surface(
    url: str,
    *,
    timeout_s: float = 1.5,
    maintenance_max_age_s: int = DEFAULT_MAINTENANCE_MAX_AGE_S,
    maintenance_check: bool = True,
) -> dict[str, Any]:
    target = str(url or "").strip()
    payload: dict[str, Any] = {
        "url": target,
        "http_ok": False,
        "http_status": 0,
        "effective_state": "error",
        "body_excerpt": "",
        "error": "",
        "maintenance_active": False,
        "maintenance_reason": "none",
        "maintenance_source": "none",
        "maintenance_command": "",
        "maintenance_age_s": None,
        "maintenance_pid": "",
        "maintenance_host": "",
        "maintenance_meta_path": "",
        "maintenance_probe_error": "",
    }
    try:
        request = urllib.request.Request(target, headers={"Accept": "application/json,text/html"})
        with urllib.request.urlopen(request, timeout=max(0.2, float(timeout_s))) as response:
            status = int(getattr(response, "status", 0) or 0)
            excerpt = response.read(2048).decode("utf-8", errors="replace")
            payload.update(
                {
                    "http_ok": 200 <= status < 300,
                    "http_status": status,
                    "body_excerpt": excerpt,
                    "effective_state": "ok" if 200 <= status < 300 else "error",
                }
            )
            if payload["http_ok"]:
                return payload
    except urllib.error.HTTPError as exc:
        body_excerpt = ""
        try:
            body_excerpt = exc.read(2048).decode("utf-8", errors="replace")
        except Exception:
            body_excerpt = ""
        payload.update(
            {
                "http_status": int(getattr(exc, "code", 0) or 0),
                "body_excerpt": body_excerpt,
                "error": f"HTTPError:{int(getattr(exc, 'code', 0) or 0)}",
            }
        )
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
        payload["error"] = type(exc).__name__
    except Exception as exc:  # pragma: no cover - defensive path
        payload["error"] = type(exc).__name__

    host = urllib.parse.urlsplit(target).hostname or ""
    canonical_host = str(os.environ.get("AWS_APP_HOST") or DEFAULT_AWS_APP_HOST).strip() or DEFAULT_AWS_APP_HOST
    if maintenance_check and host in {canonical_host, "ec2-3-98-20-77.ca-central-1.compute.amazonaws.com"}:
        maintenance = probe_remote_runtime_maintenance(max_age_s=maintenance_max_age_s)
        payload.update(maintenance)
        if maintenance.get("maintenance_active"):
            payload["effective_state"] = "maintenance"
            return payload
    return payload


def maintenance_summary(probe: dict[str, Any]) -> str:
    if not isinstance(probe, dict) or not probe.get("maintenance_active"):
        return "maintenance=none"
    command = str(probe.get("maintenance_command") or "unknown").strip() or "unknown"
    age = probe.get("maintenance_age_s")
    if isinstance(age, int):
        return f"maintenance=runtime_restart_in_progress command={command} age_s={age}"
    return f"maintenance=runtime_restart_in_progress command={command}"


def as_json(probe: dict[str, Any], *, pretty: bool = False) -> str:
    if pretty:
        return json.dumps(probe, indent=2, sort_keys=True)
    return json.dumps(probe, separators=(",", ":"), sort_keys=True)
