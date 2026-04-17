from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from browser_smoke import run_browser_smoke
from orchestrator_paths import resolve_orchestrator_read_path, write_orchestrator_json

from runtime.planner.api_wave import (
    api_wave_delivery_contract,
    api_wave_mode_enabled,
    apply_public_proof_result,
    entry_for_batch_id,
    load_api_wave_state,
)

from .public_runtime_probe import probe_public_surface
from .runtime_truth_reader import load_product_delivery_state

DEFAULT_PUBLIC_APP_BASE_URL = "http://3.98.20.77"
DEFAULT_PUBLIC_UI_URL = f"{DEFAULT_PUBLIC_APP_BASE_URL}/"
DEFAULT_API_TIMEOUT_SECONDS = 12.0


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _load_queue_and_board(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    queue = _load_json(resolve_orchestrator_read_path(root, "priority-queue.json"))
    board = _load_json(resolve_orchestrator_read_path(root, "parallel-workstreams.json"))
    return queue, board


def _default_delivery_contract(batch_id: str) -> dict[str, Any]:
    label = str(batch_id or "batch").strip().lower() or "batch"
    return {
        "value_target": batch_id,
        "user_visible_delta": batch_id,
        "api_proof": {
            "kind": "public_api_smoke",
            "base_url": DEFAULT_PUBLIC_APP_BASE_URL,
            "expected_endpoints": ["/api/health"],
            "smoke_ref": "scripts/critical_endpoints_smoke.sh",
        },
        "ui_proof": {
            "kind": "public_ui_smoke",
            "url": DEFAULT_PUBLIC_UI_URL,
            "label": f"{label}-public-ui",
            "smoke_ref": "platform/automation/browser_smoke.py",
        },
        "done_when": "public_proof_status=ok && user_visible_delta_confirmed=true",
    }


def _find_batch_contract(root: Path, batch_id: str) -> tuple[dict[str, Any], str]:
    queue, board = _load_queue_and_board(root)
    batch_token = str(batch_id or "").strip().upper()
    for item in queue.get("items", []):
        if not isinstance(item, dict):
            continue
        if str(item.get("id", "")).strip().upper() != batch_token:
            continue
        contract = item.get("delivery_contract")
        if isinstance(contract, dict):
            return dict(contract), "priority_queue"
    for stream in board.get("streams", []):
        if not isinstance(stream, dict):
            continue
        if str(stream.get("id", "")).strip().upper() != batch_token:
            continue
        contract = stream.get("delivery_contract")
        if isinstance(contract, dict):
            return dict(contract), "parallel_workstreams.stream"
    for task in board.get("tasks", []):
        if not isinstance(task, dict):
            continue
        if str(task.get("stream_id", "")).strip().upper() != batch_token:
            continue
        contract = task.get("delivery_contract")
        if isinstance(contract, dict):
            return dict(contract), "parallel_workstreams.task"
    api_wave_entry, _, _ = entry_for_batch_id(root, batch_token)
    if api_wave_entry is not None:
        return api_wave_delivery_contract(api_wave_entry), "api_wave_manifest"
    return _default_delivery_contract(batch_token), "default"


def _normalize_contract(batch_id: str, contract: dict[str, Any]) -> dict[str, Any]:
    merged = _default_delivery_contract(batch_id)
    if not isinstance(contract, dict):
        return merged
    for key in ("value_target", "user_visible_delta", "done_when"):
        token = str(contract.get(key, "")).strip()
        if token:
            merged[key] = token
    for key in ("api_proof", "ui_proof"):
        raw = contract.get(key)
        if isinstance(raw, dict):
            merged[key].update(raw)
    return merged


def _api_urls(contract: dict[str, Any]) -> list[str]:
    api_proof = contract.get("api_proof")
    api_proof = api_proof if isinstance(api_proof, dict) else {}
    base_url = str(api_proof.get("base_url") or DEFAULT_PUBLIC_APP_BASE_URL).strip() or DEFAULT_PUBLIC_APP_BASE_URL
    endpoints = api_proof.get("expected_endpoints")
    if not isinstance(endpoints, list) or not endpoints:
        endpoints = ["/api/health"]
    urls: list[str] = []
    for endpoint in endpoints:
        token = str(endpoint or "").strip()
        if not token:
            continue
        if token.startswith("http://") or token.startswith("https://"):
            urls.append(token)
        else:
            urls.append(f"{base_url.rstrip('/')}/{token.lstrip('/')}")
    return urls or [f"{DEFAULT_PUBLIC_APP_BASE_URL}/api/health"]


def _run_api_proof(contract: dict[str, Any], timeout_seconds: float) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    maintenance_seen = False
    for url in _api_urls(contract):
        probe = probe_public_surface(url, timeout_s=timeout_seconds, maintenance_check=True)
        checks.append(probe)
        if probe.get("maintenance_active"):
            maintenance_seen = True
    if maintenance_seen:
        status = "maintenance"
    elif checks and all(bool(check.get("http_ok")) for check in checks):
        status = "ok"
    else:
        status = "error"
    return {
        "status": status,
        "checks": checks,
        "public_urls_checked": [str(check.get("url", "")).strip() for check in checks if str(check.get("url", "")).strip()],
    }


def _run_ui_proof(root: Path, batch_id: str, contract: dict[str, Any], timeout_seconds: int) -> dict[str, Any]:
    ui_proof = contract.get("ui_proof")
    ui_proof = ui_proof if isinstance(ui_proof, dict) else {}
    url = str(ui_proof.get("url") or DEFAULT_PUBLIC_UI_URL).strip() or DEFAULT_PUBLIC_UI_URL
    label = str(ui_proof.get("label") or f"{batch_id.lower()}-public-ui").strip() or f"{batch_id.lower()}-public-ui"
    wait_text = str(ui_proof.get("wait_text") or "").strip()
    wait_url = str(ui_proof.get("wait_url") or "").strip()
    try:
        proof = run_browser_smoke(
            url=url,
            root=root,
            label=label,
            wait_text=wait_text,
            wait_url=wait_url,
            timeout_seconds=max(5, int(timeout_seconds)),
        )
        return {
            "status": "ok",
            "url": url,
            "proof_path": str(proof.get("proof_path", "")).strip() or None,
            "screenshot_copy": str(proof.get("screenshot_copy", "")).strip() or None,
            "label": label,
        }
    except Exception as exc:
        return {
            "status": "error",
            "url": url,
            "label": label,
            "error": f"{type(exc).__name__}:{exc}",
        }


def _proof_artifact_relative_path(batch_id: str) -> str:
    token = str(batch_id or "").strip().upper() or "BATCH-UNKNOWN"
    return f"public-proof/{token}.json"


def run_public_proof(
    root: Path,
    *,
    batch_id: str | None = None,
    timeout_seconds: float = DEFAULT_API_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    root = Path(root)
    delivery_state = load_product_delivery_state(root)
    effective_batch_id = str(batch_id or delivery_state.get("active_batch_id") or delivery_state.get("last_completed_batch_id") or "").strip().upper()
    api_wave_state: dict[str, Any] = {}
    if not effective_batch_id and api_wave_mode_enabled(root):
        api_wave_state = load_api_wave_state(root, persist_defaults=True)
        effective_batch_id = str(
            api_wave_state.get("current_owner_task_id")
            or api_wave_state.get("current_endpoint_id")
            or ""
        ).strip().upper()
    if not effective_batch_id:
        return {
            "batch_id": None,
            "status": "skip",
            "reason": "no_canonical_batch",
            "timestamp": _utc_now(),
            "proof_ref": None,
        }

    raw_contract, contract_source = _find_batch_contract(root, effective_batch_id)
    contract = _normalize_contract(effective_batch_id, raw_contract)
    api_result = _run_api_proof(contract, float(timeout_seconds))
    ui_result = _run_ui_proof(root, effective_batch_id, contract, int(max(5, timeout_seconds)))

    if api_result["status"] == "maintenance":
        overall_status = "maintenance"
    elif api_result["status"] == "ok" and ui_result["status"] == "ok":
        overall_status = "ok"
    else:
        overall_status = "error"

    artifact = {
        "batch_id": effective_batch_id,
        "status": overall_status,
        "api_smoke_status": api_result["status"],
        "ui_smoke_status": ui_result["status"],
        "user_visible_delta_confirmed": api_result["status"] == "ok" and ui_result["status"] == "ok",
        "public_urls_checked": list(
            dict.fromkeys(
                [
                    *api_result.get("public_urls_checked", []),
                    str(ui_result.get("url", "")).strip(),
                ]
            )
        ),
        "timestamp": _utc_now(),
        "contract_source": contract_source,
        "contract": contract,
        "api_result": api_result,
        "ui_result": ui_result,
    }
    proof_path = persist_public_proof(root, artifact)
    artifact["proof_ref"] = str(proof_path)
    persist_public_proof(root, artifact)
    if api_wave_mode_enabled(root):
        apply_public_proof_result(root, batch_id=effective_batch_id, artifact=artifact)
    return artifact


def persist_public_proof(root: Path, artifact: dict[str, Any]) -> Path:
    batch_id = str(artifact.get("batch_id") or "").strip().upper()
    if not batch_id:
        raise ValueError("missing batch_id for public proof artifact")
    return write_orchestrator_json(root, _proof_artifact_relative_path(batch_id), artifact, mirror_docs=False)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run batch-aware public API/UI proof and persist a compact proof artifact.")
    parser.add_argument("--root", default="", help="Workspace root; defaults to repo root")
    parser.add_argument("--batch-id", default="", help="Canonical batch id; defaults to active_batch_id")
    parser.add_argument("--timeout-seconds", type=float, default=DEFAULT_API_TIMEOUT_SECONDS)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = Path(args.root).expanduser().resolve() if str(args.root or "").strip() else Path(__file__).resolve().parents[3]
    payload = run_public_proof(
        root,
        batch_id=str(args.batch_id or "").strip() or None,
        timeout_seconds=float(args.timeout_seconds),
    )
    print(json.dumps(payload, indent=2, ensure_ascii=True))
    return 0 if payload.get("status") in {"ok", "maintenance", "skip"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
