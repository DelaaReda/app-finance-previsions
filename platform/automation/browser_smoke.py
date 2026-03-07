#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _slug(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in str(value or "").strip())
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-") or "browser-smoke"


def _run_browser(args: list[str], *, timeout_seconds: int = 30, parse_json: bool = True) -> tuple[int, Any, str]:
    proc = subprocess.run(
        ["openclaw", "browser", "--json", *args],
        text=True,
        capture_output=True,
        check=False,
        timeout=max(5, timeout_seconds),
    )
    stdout = (proc.stdout or "").strip()
    stderr = (proc.stderr or "").strip()
    if not parse_json:
        return proc.returncode, stdout, stderr
    if stdout:
        try:
            return proc.returncode, json.loads(stdout), stderr
        except Exception:
            return proc.returncode, {"raw": stdout}, stderr
    return proc.returncode, {}, stderr


def _ensure_browser_ready(timeout_seconds: int) -> dict[str, Any]:
    _run_browser(["start"], timeout_seconds=timeout_seconds)
    rc, payload, stderr = _run_browser(["status"], timeout_seconds=timeout_seconds)
    if rc != 0:
        raise RuntimeError(stderr or "browser_status_failed")
    if not bool(payload.get("running")) or not bool(payload.get("cdpReady")):
        raise RuntimeError("browser_not_ready")
    return payload if isinstance(payload, dict) else {}


def run_browser_smoke(
    *,
    url: str,
    root: Path,
    label: str,
    wait_text: str = "",
    wait_url: str = "",
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    output_dir = root / "logs-codex-runs" / "browser-smoke"
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base = f"{stamp}-{_slug(label)}"
    proof_path = output_dir / f"{base}.json"
    screenshot_copy = output_dir / f"{base}.png"

    status = _ensure_browser_ready(timeout_seconds)
    open_rc, open_payload, open_err = _run_browser(["open", url], timeout_seconds=timeout_seconds)
    if open_rc != 0:
        raise RuntimeError(open_err or "browser_open_failed")
    target_id = str((open_payload or {}).get("targetId", "")).strip()

    wait_args = ["wait", "--load", "domcontentloaded", "--timeout-ms", str(max(5000, timeout_seconds * 1000))]
    if target_id:
        wait_args.extend(["--target-id", target_id])
    wait_rc, wait_payload, wait_err = _run_browser(wait_args, timeout_seconds=timeout_seconds)
    if wait_rc != 0:
        raise RuntimeError(wait_err or json.dumps(wait_payload, ensure_ascii=True))

    if wait_text:
        extra_wait = ["wait", "--text", wait_text, "--timeout-ms", str(max(5000, timeout_seconds * 1000))]
        if target_id:
            extra_wait.extend(["--target-id", target_id])
        wait_rc, wait_payload, wait_err = _run_browser(extra_wait, timeout_seconds=timeout_seconds)
        if wait_rc != 0:
            raise RuntimeError(wait_err or json.dumps(wait_payload, ensure_ascii=True))
    if wait_url:
        extra_wait = ["wait", "--url", wait_url, "--timeout-ms", str(max(5000, timeout_seconds * 1000))]
        if target_id:
            extra_wait.extend(["--target-id", target_id])
        wait_rc, wait_payload, wait_err = _run_browser(extra_wait, timeout_seconds=timeout_seconds)
        if wait_rc != 0:
            raise RuntimeError(wait_err or json.dumps(wait_payload, ensure_ascii=True))

    snapshot_args = ["snapshot", "--labels", "--limit", "200"]
    if target_id:
        snapshot_args.extend(["--target-id", target_id])
    _, snapshot_payload, _ = _run_browser(snapshot_args, timeout_seconds=timeout_seconds)

    console_args = ["console", "--level", "error"]
    if target_id:
        console_args.extend(["--target-id", target_id])
    _, console_payload, _ = _run_browser(console_args, timeout_seconds=timeout_seconds)

    errors_args = ["errors"]
    if target_id:
        errors_args.extend(["--target-id", target_id])
    _, errors_payload, _ = _run_browser(errors_args, timeout_seconds=timeout_seconds)

    screenshot_args = ["screenshot", "--full-page"]
    if target_id:
        screenshot_args.append(target_id)
    _, screenshot_payload, _ = _run_browser(screenshot_args, timeout_seconds=max(timeout_seconds, 45))
    screenshot_path = Path(str((screenshot_payload or {}).get("path", "")).strip()) if isinstance(screenshot_payload, dict) else Path("")
    if screenshot_path and screenshot_path.exists():
        shutil.copy2(screenshot_path, screenshot_copy)

    close_args = ["close"]
    if target_id:
        close_args.append(target_id)
    _run_browser(close_args, timeout_seconds=timeout_seconds)

    proof = {
        "ok": True,
        "generated_at": _iso(),
        "label": label,
        "url": url,
        "target_id": target_id,
        "browser_status": status,
        "snapshot": snapshot_payload,
        "console": console_payload,
        "errors": errors_payload,
        "screenshot_source": str(screenshot_path) if screenshot_path else "",
        "screenshot_copy": str(screenshot_copy) if screenshot_copy.exists() else "",
        "proof_kind": "openclaw_browser_smoke",
    }
    proof_path.write_text(json.dumps(proof, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    proof["proof_path"] = str(proof_path)
    return proof


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Capture OpenClaw browser smoke proof for UI-affecting work.")
    parser.add_argument("--url", required=True)
    parser.add_argument("--label", default="browser-smoke")
    parser.add_argument("--root", default="")
    parser.add_argument("--wait-text", default="")
    parser.add_argument("--wait-url", default="")
    parser.add_argument("--timeout-seconds", type=int, default=30)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = Path(args.root).expanduser().resolve() if args.root else Path(__file__).resolve().parents[2]
    payload = run_browser_smoke(
        url=str(args.url).strip(),
        root=root,
        label=str(args.label).strip() or "browser-smoke",
        wait_text=str(args.wait_text).strip(),
        wait_url=str(args.wait_url).strip(),
        timeout_seconds=max(5, int(args.timeout_seconds)),
    )
    print(json.dumps(payload, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
