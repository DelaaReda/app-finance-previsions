#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

AUTOMATION_DIR = Path(__file__).resolve().parent
if str(AUTOMATION_DIR) not in sys.path:
    sys.path.insert(0, str(AUTOMATION_DIR))

from runtime.truth.public_proof_runner import run_public_proof
from runtime.truth.runtime_truth_reader import load_product_delivery_state
from runtime.truth.verifier_governor import (
    load_verifier_state,
    record_verifier_result,
    should_run_verifier,
)


def _emit_contract(
    *,
    status: str,
    delta: str,
    evidence: str,
    risks: str,
    next_step: str,
    verdict: str,
    blocker_id: str,
    next_action_unique: str,
) -> int:
    print(f"STATUS: {status}")
    print(f"DELTA: {delta}")
    print(f"EVIDENCE: {evidence}")
    print(f"RISKS: {risks}")
    print(f"NEXT: {next_step}")
    print(f"VERDICT: {verdict}")
    print(f"BLOCKER_ID: {blocker_id}")
    print(f"NEXT_ACTION_UNIQUE: {next_action_unique}")
    return 0


def _skip_contract(delivery_state: dict[str, object], *, reason: str, batch_id: str) -> int:
    phase = str(delivery_state.get("phase") or "none").strip() or "none"
    public_proof_status = str(delivery_state.get("public_proof_status") or "unknown").strip() or "unknown"
    return _emit_contract(
        status="WAIT",
        delta="NO_DELTA",
        evidence=(
            f"task_update=none_no_signal; stream_id={batch_id or 'none'}; task_id={batch_id or 'none'}; "
            f"run_note=verifier_skip_{reason}; phase={phase}; public_proof_status={public_proof_status}"
        ),
        risks="aucun rerun verifier utile sans changement canonique",
        next_step="owner=planner; action=rerun verifier seulement sur changement ou relance explicite",
        verdict="PASS",
        blocker_id="NONE",
        next_action_unique=f"VERIFIER_SKIP_{reason.upper()}",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the public proof verifier only when canonical delivery state changed.")
    parser.add_argument("--root", default="")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--timeout-seconds", type=float, default=12.0)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = Path(args.root).expanduser().resolve() if str(args.root or "").strip() else Path(__file__).resolve().parents[1]
    delivery_state = load_product_delivery_state(root)
    verifier_state = load_verifier_state(root)
    decision = should_run_verifier(delivery_state, verifier_state, force=bool(args.force))
    batch_id = str(decision.get("batch_id") or "").strip().upper()
    if not bool(decision.get("should_run")):
        return _skip_contract(delivery_state, reason=str(decision.get("reason") or "no_change"), batch_id=batch_id)

    artifact = run_public_proof(
        root,
        batch_id=batch_id or None,
        timeout_seconds=float(args.timeout_seconds),
    )
    record_verifier_result(root, delivery_state, artifact, decision_reason=str(decision.get("reason") or "state_changed"))

    artifact_status = str(artifact.get("status") or "unknown").strip().lower() or "unknown"
    api_status = str(artifact.get("api_smoke_status") or "unknown").strip() or "unknown"
    ui_status = str(artifact.get("ui_smoke_status") or "unknown").strip() or "unknown"
    proof_ref = str(artifact.get("proof_ref") or "none").strip() or "none"
    visible_delta = "1" if bool(artifact.get("user_visible_delta_confirmed")) else "0"
    evidence = (
        f"task_update=verify; stream_id={batch_id or 'none'}; task_id={batch_id or 'none'}; "
        f"run_note=verifier_run_{artifact_status}; trigger_reason={str(decision.get('reason') or 'state_changed')}; "
        f"api_smoke_status={api_status}; ui_smoke_status={ui_status}; "
        f"user_visible_delta_confirmed={visible_delta}; proof_ref={proof_ref}"
    )
    if artifact_status == "ok":
        return _emit_contract(
            status="DONE",
            delta="PUBLIC_PROOF_OK",
            evidence=evidence,
            risks="none",
            next_step="owner=planner; action=consume public proof and close batch if canonical guard stays green",
            verdict="GO_WITH_CAUTION",
            blocker_id="NONE",
            next_action_unique=f"VERIFIER_PROOF_OK_{batch_id or 'NONE'}",
        )
    if artifact_status == "maintenance":
        return _emit_contract(
            status="WAIT",
            delta="PUBLIC_PROOF_MAINTENANCE",
            evidence=evidence,
            risks="publication en maintenance transitoire",
            next_step="owner=planner; action=relance explicite verifier apres maintenance",
            verdict="WAIT",
            blocker_id="NONE",
            next_action_unique=f"VERIFIER_MAINTENANCE_{batch_id or 'NONE'}",
        )
    return _emit_contract(
        status="IN_PROGRESS",
        delta="PUBLIC_PROOF_ERROR",
        evidence=evidence,
        risks="preuve publique rouge; batch non clos",
        next_step="owner=planner; action=consommer erreur proof puis corriger le delta public avant rerun",
        verdict="GO_WITH_CAUTION",
        blocker_id="PUBLIC_PROOF_ERROR",
        next_action_unique=f"VERIFIER_PROOF_ERROR_{batch_id or 'NONE'}",
    )


if __name__ == "__main__":
    raise SystemExit(main())
