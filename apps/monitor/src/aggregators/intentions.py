from __future__ import annotations

from pathlib import Path
from typing import Any


def _read_contract(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return out
    for line in lines:
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        k = key.strip().upper()
        if not k:
            continue
        out[k] = value.strip()
    return out


def collect_role_intentions(state_dir: Path, roles: tuple[str, ...] = ("planner", "dev", "admin", "scrum_master")) -> dict[str, Any]:
    intentions: dict[str, dict[str, str]] = {}
    quality: dict[str, dict[str, Any]] = {}
    for role in roles:
        contract = _read_contract(state_dir / f"{role}.last_contract")
        next_action = str(contract.get("NEXT") or contract.get("NEXT_ACTION_UNIQUE") or "").strip()
        evidence = str(contract.get("EVIDENCE") or "").strip()
        missing = []
        evidence_low = evidence.lower()
        for key in ("root_cause=", "fix_applied=", "verify="):
            if key not in evidence_low:
                missing.append(key[:-1])
        score = max(0, 100 - len(missing) * 20)
        intentions[role] = {
            "next": next_action,
            "status": str(contract.get("STATUS") or "UNKNOWN").strip(),
            "delta": str(contract.get("DELTA") or "").strip(),
            "verdict": str(contract.get("VERDICT") or "UNKNOWN").strip(),
            "blocker": str(contract.get("BLOCKER_ID") or "NONE").strip(),
        }
        quality[role] = {
            "score": score,
            "missing_fields": missing,
        }
    return {
        "intentions": intentions,
        "decision_trace_quality": quality,
    }
