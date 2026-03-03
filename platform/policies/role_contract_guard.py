#!/usr/bin/env python3
"""Role contract guard — version LEAN.

Vérifie l'essentiel uniquement. 10 checks, zéro overhead.
Remplace l'ancienne version 1091-lignes qui bloquait plus qu'elle n'aidait.
"""
from __future__ import annotations

import json
import re
import sys
import subprocess
from datetime import datetime, timezone
from pathlib import Path

KEYS = ["STATUS", "DELTA", "EVIDENCE", "RISKS", "NEXT", "VERDICT", "BLOCKER_ID", "NEXT_ACTION_UNIQUE"]

READ_ONLY_ROLES = {"planner", "analyst", "architect", "po", "scrum_master", "clawsentinel"}
DELIVERY_ROLES  = {"backend_engineer", "frontend_engineer", "data_analyst", "dev",
                   "tester", "qa", "integrator", "infra_engineer", "admin"}

ALLOWED_TASK_UPDATES = {
    "claim", "complete", "handoff", "blocked",
    "analysis_only", "none_no_ready", "none_no_signal",
}

ARTIFACT_MARKERS = {
    "planner": "planner_artifact",
    "admin": "admin_artifact",
    "analyst": "analyst_artifact",
    "dev": "dev_artifact",
    "backend_engineer": "backend_artifact",
    "frontend_engineer": "frontend_artifact",
    "integrator": "integrator_artifact",
    "data_analyst": "data_artifact",
    "infra_engineer": "infra_artifact",
    "tester": "tester_artifact",
    "qa": "qa_artifact",
    "architect": "architect_artifact",
    "po": "po_artifact",
    "scrum_master": "scrum_artifact",
    "clawsentinel": "sentinel_artifact",
}

ADMIN_RUNTIME_BLOCKER_PREFIXES = (
    "API_",
    "BACKEND_",
    "FRONTEND_",
    "RUNTIME_",
    "CRON_",
    "SESSION_",
    "LOCK_",
    "SERVICE_",
    "PORT_",
    "NETWORK_",
    "DNS_",
    "RATE_LIMIT_",
    "DEPENDENCY_",
)

EMPTY_VALUE_MARKERS = {"", "none", "n/a", "null", "-", "na", "non", "aucun", "aucune"}


def _parse_contract(text: str) -> dict[str, str]:
    values = {k: "" for k in KEYS}
    for raw in text.splitlines():
        line = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", raw).strip()
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip().upper()
        if key in values and not values[key]:
            values[key] = val.strip()
    return values


def _parse_kv(raw: str) -> dict[str, str]:
    kv: dict[str, str] = {}
    for frag in raw.split(";"):
        frag = frag.strip()
        if "=" in frag:
            k, _, v = frag.partition("=")
            kv[k.strip().lower()] = v.strip()
    return kv


def _crontab_agent_jobs() -> int:
    try:
        proc = subprocess.run(
            ["crontab", "-l"],
            check=False,
            capture_output=True,
            text=True,
        )
    except Exception:
        return -1
    if proc.returncode != 0:
        return 0
    text = proc.stdout or ""
    return len(re.findall(r"(fc_agent_tick|cron_tmux_role_runner)", text))


def _recent_admin_cron_log(max_age_minutes: int = 120) -> bool:
    root = Path.cwd()
    log_path = root / "logs-codex-runs" / "fc-ticks" / "admin.cron.log"
    if not log_path.exists():
        return False
    try:
        age_seconds = datetime.now(timezone.utc).timestamp() - log_path.stat().st_mtime
        return age_seconds <= max_age_minutes * 60
    except Exception:
        return False


def _render(values: dict[str, str]) -> str:
    return "\n".join(f"{k}: {values[k]}" for k in KEYS)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _blocked(role: str, source: str, blocker_id: str, reason: str, values: dict[str, str]) -> None:
    slug = re.sub(r"[^a-z0-9_]+", "_", blocker_id.lower()).strip("_")
    ev = (
        f"task_update=blocked; lock_check=ok; "
        f"run_note=contract guard bloque {slug}; "
        f"role_artifact=contract_guard; "
        f"stream_id=none; task_id=none"
    )
    out = {
        "STATUS": "BLOCKED",
        "DELTA": "CONTRACT_GUARD_BLOCK",
        "EVIDENCE": ev,
        "RISKS": reason[:200],
        "NEXT": f"owner={role}; action=corriger le contrat puis relancer",
        "VERDICT": "BLOCKED",
        "BLOCKER_ID": blocker_id,
        "NEXT_ACTION_UNIQUE": f"FIX_{role.upper()}_{_now()}",
    }
    print(_render(out))
    raise SystemExit(0)


def _sanitize_evidence(raw: str) -> str:
    """Strip noisy/debug fragments before persisting into role contracts."""
    if not raw:
        return ""
    cleaned: list[str] = []
    for frag in raw.split(";"):
        frag = frag.strip()
        if not frag:
            continue
        key = frag.split("=", 1)[0].strip().lower()
        if key.startswith("raw_"):
            continue
        if "=" in frag:
            k, v = frag.split("=", 1)
            v = v.strip()
            if len(v) > 180:
                v = v[:180]
            frag = f"{k.strip()}={v}"
        elif len(frag) > 180:
            frag = frag[:180]
        cleaned.append(frag)
    return "; ".join(cleaned)


def _is_admin_runtime_blocker(blocker_id: str) -> bool:
    blocker = (blocker_id or "").strip().upper()
    if blocker in {"", "NONE", "N/A", "NULL"}:
        return False
    return any(blocker.startswith(prefix) for prefix in ADMIN_RUNTIME_BLOCKER_PREFIXES)


def _is_empty_marker(raw: str) -> bool:
    return (raw or "").strip().lower() in EMPTY_VALUE_MARKERS


def _planner_batch_created_ids(raw: str) -> tuple[list[str], list[str]]:
    """
    Parse planner batch_created evidence into:
    - created_top_level_ids: explicit BATCH-XX creations
    - invalid_tokens: malformed tokens
    """
    created_top_level_ids: list[str] = []
    invalid_tokens: list[str] = []
    text = (raw or "").strip()
    if not text or _is_empty_marker(text):
        return created_top_level_ids, invalid_tokens

    tokens = [tok for tok in re.split(r"[|,;\s]+", text) if tok]
    for tok in tokens:
        token = tok.strip().strip("\"'`[](){}<>").strip().rstrip(".,:")
        token = token.upper()
        if not token or _is_empty_marker(token):
            continue
        if token.startswith("BATCH_CREATED="):
            token = token.split("=", 1)[1].strip()
            if not token or _is_empty_marker(token):
                continue
        if re.fullmatch(r"BATCH-\d{2}", token):
            created_top_level_ids.append(token)
            continue
        # Subtask/stream references are tolerated (not considered batch creations).
        if re.fullmatch(r"BATCH-\d{2}[-_][A-Z0-9][A-Z0-9._:-]*", token):
            continue
        # Ignore non-batch free text in this field, but keep strict checks
        # for malformed batch-like tokens.
        if token.startswith("BATCH-"):
            invalid_tokens.append(tok)

    return created_top_level_ids, invalid_tokens


def main() -> int:
    if len(sys.argv) != 9:
        print(
            "usage: role_contract_guard.py <role> <source> <payload_file> "
            "<allow_file_edits:0|1> <workboard_has_work:0|1> "
            "<workboard_has_in_progress:0|1> <queue_version> <workboard_version>",
            file=sys.stderr,
        )
        return 2

    role = sys.argv[1]
    source = sys.argv[2]
    payload_path = Path(sys.argv[3])
    allow_file_edits = sys.argv[4] == "1"
    workboard_has_work = sys.argv[5] == "1"
    workboard_has_in_progress = sys.argv[6] == "1"

    text = payload_path.read_text(encoding="utf-8", errors="ignore")
    values = _parse_contract(text)

    # Payload incomplet → laisser passer (le runner gère le fallback)
    if any(not values[k] for k in KEYS):
        print(text.strip())
        return 0

    ev = _parse_kv(values.get("EVIDENCE", ""))
    task_update = ev.get("task_update", "").strip().lower()
    lock_check  = ev.get("lock_check", "").strip().lower()
    run_note    = ev.get("run_note", "").strip()
    artifact_key = ARTIFACT_MARKERS.get(role, "role_artifact")

    # ── CHECK 1 : BLOCKED doit avoir un BLOCKER_ID non-NONE ──────────────────
    if values["STATUS"].upper() == "BLOCKED" and values["BLOCKER_ID"].upper() in ("", "NONE", "N/A", "NULL"):
        _blocked(role, source, "BLOCKER_ID_MISSING",
                 f"STATUS=BLOCKED mais BLOCKER_ID manquant (role={role})", values)

    # ── CHECK 2 : task_update doit être présent et valide ───────────────────
    if not task_update:
        _blocked(role, source, "TASK_UPDATE_MISSING",
                 f"task_update absent de EVIDENCE (role={role})", values)
    if task_update not in ALLOWED_TASK_UPDATES:
        _blocked(role, source, "TASK_UPDATE_INVALID",
                 f"task_update={task_update} invalide; valeurs: {','.join(sorted(ALLOWED_TASK_UPDATES))}", values)

    # ── CHECK 3 : rôles read-only ne peuvent pas claim/complete/handoff ──────
    if role in READ_ONLY_ROLES and not allow_file_edits and task_update in {"claim", "complete", "handoff"}:
        values["EVIDENCE"] = re.sub(r"task_update=[^;]+", "task_update=analysis_only", values["EVIDENCE"])
        ev["task_update"] = task_update = "analysis_only"

    # ── CHECK 4 : lock_check=ok obligatoire ──────────────────────────────────
    if lock_check != "ok":
        _blocked(role, source, "LOCK_CHECK_MISSING",
                 f"lock_check manquant ou != ok dans EVIDENCE (role={role})", values)

    # ── CHECK 5 : run_note doit avoir ≥ 5 mots ───────────────────────────────
    if len([w for w in run_note.split() if w]) < 5:
        _blocked(role, source, "RUN_NOTE_TOO_SHORT",
                 f"run_note trop court (<5 mots): '{run_note}' (role={role})", values)

    # ── CHECK 6 : artefact rôle obligatoire ──────────────────────────────────
    if not ev.get(artifact_key, "").strip():
        _blocked(role, source, "ROLE_ARTIFACT_MISSING",
                 f"{artifact_key} absent de EVIDENCE (role={role})", values)

    # ── CHECK 7 : claim/handoff → stream_id + task_id ────────────────────────
    if task_update in {"claim", "handoff"}:
        for field in ("stream_id", "task_id"):
            val = ev.get(field, "").strip().lower()
            if not val or val == "none":
                _blocked(role, source, f"CLAIM_{field.upper()}_MISSING",
                         f"{field} requis pour task_update={task_update} (role={role})", values)

    # ── CHECK 8 : complete → cmd présente (tests_run optionnel) ────────────
    if task_update == "complete":
        cmd = ev.get("cmd", "").strip()
        if not cmd:
            _blocked(role, source, "COMPLETE_CMD_MISSING",
                     f"cmd requise pour task_update=complete (role={role})", values)

    # ── CHECK 8b : dev must provide architecture/reuse/qa evidence ──────────
    if role == "dev" and task_update in {"claim", "complete", "handoff"}:
        if task_update == "claim":
            required_dev_fields = (
                "root_cause",
                "architecture_check",
                "vision_alignment",
                "reuse_check",
            )
        else:
            required_dev_fields = (
                "root_cause",
                "fix_applied",
                "verify",
                "reuse_check",
                "architecture_check",
                "vision_alignment",
                "qa_proof",
            )
        missing_dev = [
            field
            for field in required_dev_fields
            if _is_empty_marker(ev.get(field, ""))
        ]
        if missing_dev:
            _blocked(
                role,
                source,
                "DEV_DELIVERY_EVIDENCE_MISSING",
                (
                    "dev evidence incomplet pour delivery; "
                    f"task_update={task_update}; missing={','.join(missing_dev)}"
                ),
                values,
            )

    # ── CHECK 9 : handoff → handoff_to ───────────────────────────────────────
    if task_update == "handoff":
        if not ev.get("handoff_to", "").strip():
            _blocked(role, source, "HANDOFF_TO_MISSING",
                     f"handoff_to requis pour task_update=handoff (role={role})", values)

    # ── CHECK 10 : blocked avec motif permission doit avoir cmd_err_excerpt ──
    if task_update == "blocked":
        blocker_raw = values["BLOCKER_ID"].lower()
        if "permission" in blocker_raw or "read_only" in blocker_raw:
            if not ev.get("cmd_err_excerpt", "").strip():
                _blocked(role, source, "PERMISSION_BLOCKER_NO_PROOF",
                         f"blocker permission/read_only sans cmd_err_excerpt (role={role})", values)

    # ── CHECK 11 : planner batch creation must include architecture details ──
    if role == "planner":
        batch_created = ev.get("batch_created", "").strip()
        if batch_created and not _is_empty_marker(batch_created):
            created_batch_ids, invalid_ids = _planner_batch_created_ids(batch_created)
            if invalid_ids:
                _blocked(
                    role,
                    source,
                    "PLANNER_BATCH_ID_INVALID",
                    f"batch_created contient des IDs invalides: {','.join(invalid_ids)}",
                    values,
                )
            if created_batch_ids:
                required_planner_fields = (
                    "architecture_plan_ref",
                    "implementation_tracks",
                    "integration_reuse",
                    "acceptance_gate",
                )
                missing = [
                    field
                    for field in required_planner_fields
                    if _is_empty_marker(ev.get(field, ""))
                ]
                if missing:
                    _blocked(
                        role,
                        source,
                        "PLANNER_BATCH_ARCH_MISSING",
                        f"creation batch sans details architecture: missing={','.join(missing)}",
                        values,
                    )

    # ── CHECK 11b : planner analysis-mode blocker should not hard-stop lane ─
    if role == "planner" and task_update == "blocked":
        blocker = values["BLOCKER_ID"].strip().upper()
        if blocker == "MODE_ANALYSE_NO_EDITS":
            values["STATUS"] = "WAIT"
            values["DELTA"] = "NO_DELTA"
            values["VERDICT"] = "PASS"
            values["BLOCKER_ID"] = "NONE"
            values["RISKS"] = "mode analyse sans edits converti en attente active"
            values["NEXT"] = (
                "owner=planner; action=surveiller queue/workboard puis basculer delivery uniquement avec item claimable"
            )
            values["NEXT_ACTION_UNIQUE"] = f"WAIT_ANALYSIS_MODE_{_now()}"
            values["EVIDENCE"] = (
                "task_update=none_no_signal; lock_check=ok; "
                "run_note=guard convertit faux blocage mode analyse en attente active; "
                "planner_artifact=platform/policies/role_contract_guard.py; "
                f"original_blocker={blocker}"
            )
            ev = _parse_kv(values["EVIDENCE"])
            task_update = "none_no_signal"

    # ── CHECK 12 : mode delivery strict quand lane active ────────────────────
    # Empêche les sorties passives quand il existe du travail réel sur la lane.
    if role in DELIVERY_ROLES and allow_file_edits and (workboard_has_work or workboard_has_in_progress):
        if task_update in {"analysis_only", "none_no_ready"}:
            _blocked(
                role,
                source,
                "DELIVERY_ACTION_REQUIRED",
                (
                    f"lane active (work={int(workboard_has_work)} in_progress={int(workboard_has_in_progress)}) "
                    f"mais task_update={task_update}; attendu claim/complete/handoff/blocked avec preuve."
                ),
                values,
            )

    # ── CHECK 13 : admin ne doit pas se bloquer sur des dérives non-runtime ─
    if role == "admin" and task_update == "blocked":
        blocker = values["BLOCKER_ID"].strip().upper()
        if blocker != "CRON_SCHEDULE_MISSING" and not _is_admin_runtime_blocker(blocker):
            values["STATUS"] = "IN_PROGRESS"
            values["DELTA"] = "NO_DELTA"
            values["VERDICT"] = "GO_WITH_CAUTION"
            values["BLOCKER_ID"] = "NONE"
            values["RISKS"] = "blocage admin non-runtime converti en supervision continue"
            values["NEXT"] = (
                "owner=admin; action=traiter la derive et pousser une action de debottleneck, sans auto-blocker lane"
            )
            values["NEXT_ACTION_UNIQUE"] = f"CONTINUE_ADMIN_DEBOTTLENECK_{_now()}"
            values["EVIDENCE"] = (
                "task_update=none_no_signal; lock_check=ok; "
                "run_note=guard retire auto-blocker non-runtime et force supervision active; "
                "admin_artifact=platform/policies/role_contract_guard.py; "
                f"original_blocker={blocker}"
            )
            ev = _parse_kv(values["EVIDENCE"])
            task_update = "none_no_signal"

    # ── CHECK 14 : anti-faux-blocker cron admin ──────────────────────────────
    # Cas observé: admin déclare CRON_SCHEDULE_MISSING alors que les ticks existent.
    if role == "admin" and task_update == "blocked" and values["BLOCKER_ID"] == "CRON_SCHEDULE_MISSING":
        jobs = _crontab_agent_jobs()
        recent_log = _recent_admin_cron_log(max_age_minutes=120)
        if jobs > 0 or recent_log:
            values["STATUS"] = "WAIT"
            values["DELTA"] = "NO_DELTA"
            values["VERDICT"] = "WAIT"
            values["BLOCKER_ID"] = "NONE"
            values["RISKS"] = (
                "ancien faux blocage cron neutralisé: crontab/logs indiquent des ticks actifs"
            )
            values["NEXT"] = (
                "owner=admin; action=continuer la supervision runtime et traiter blockers réels"
            )
            values["NEXT_ACTION_UNIQUE"] = f"CONTINUE_ADMIN_RUNTIME_TRUTH_{_now()}"
            values["EVIDENCE"] = (
                "task_update=none_no_signal; lock_check=ok; "
                "run_note=guard valide cron actifs et retire faux blocage; "
                "admin_artifact=scripts/fc_health_check.sh; "
                f"crontab_agent_jobs={jobs}; cron_log_recent={int(recent_log)}"
            )
            ev = _parse_kv(values["EVIDENCE"])
            task_update = "none_no_signal"

    # ── CHECK 15 : anti-faux-blocker delivery ────────────────────────────────
    # Si un rôle delivery se met BLOCKED sans preuve d'exécution du tick courant,
    # on bloque explicitement le contrat au lieu de le convertir en analyse.
    if role in DELIVERY_ROLES and task_update == "blocked" and (workboard_has_work or workboard_has_in_progress):
        cmd_val = ev.get("cmd", "").strip()
        cmd_err = ev.get("cmd_err_excerpt", "").strip()
        stream_val = ev.get("stream_id", "").strip().lower()
        task_val = ev.get("task_id", "").strip().lower()
        has_scope = bool(stream_val and stream_val != "none" and task_val and task_val != "none")
        has_exec_proof = bool(cmd_val or cmd_err)
        if not has_exec_proof or not has_scope:
            _blocked(
                role,
                source,
                "BLOCKED_WITHOUT_FRESH_PROOF",
                (
                    "task_update=blocked sans preuve d'execution du tick courant "
                    "(cmd/cmd_err_excerpt + stream_id/task_id requis)."
                ),
                values,
            )

    values["EVIDENCE"] = _sanitize_evidence(values.get("EVIDENCE", ""))

    # Tout bon → sortie telle quelle
    print(_render(values))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
