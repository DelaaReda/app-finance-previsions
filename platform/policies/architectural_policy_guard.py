#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ACTIVE_DOCS_INDEX = ROOT / "docs" / "ops" / "ACTIVE_DOCS_INDEX.md"
CODE_SUFFIXES = {".py", ".sh", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}
ACTIVE_DOCS_REQUIRED = {
    "docs/ops/CANONICAL_RUNTIME_MODE.md",
    "docs/ops/COMMIT_ONLY_WORKFLOW_POLICY.md",
    "docs/ops/ARCHITECTURAL_BLACKLIST.md",
    "docs/ops/ADR_LANGGRAPH_PYDANTIC_RUNTIME_MIGRATION_2026-03-13.md",
    "docs/ops/LANGGRAPH_PYDANTICAI_ORCHESTRATION_TARGET.md",
    "docs/ops/MONITOR_ARCHITECTURE_SPEC.md",
    "docs/ops/ORCHESTRATION_RELIABILITY_SPEC.md",
    "docs/ops/DOCTOR_JSON_SPEC.md",
    "docs/ops/APP_VS_AGENT_PROVIDER_BOUNDARY.md",
    "docs/ops/PLANE_BACKLOG_INTEGRATION_SPEC.md",
}
RUNTIME_PROJECTION_PATH_ALLOWLIST = {
    "platform/automation/orchestrator_paths.py",
    "platform/automation/runtime/planner/planner_board_runtime.py",
}
LEGACY_BACKLOG_DOCS = {
    "docs/product/planning/tasks.md",
    "docs/product/planning/epics.md",
    "docs/product/planning/stories.md",
    "docs/product/scrum/product-backlog.md",
    "docs/tasks-hub/README.md",
}
LEGACY_RUNTIME_BRIDGES = (
    "planner-subagents-registry.json",
    "planner-subagents-events.jsonl",
    "dynamic-workers-registry.json",
    "dynamic-workers-events.jsonl",
    "agent-message-bus.jsonl",
    "intent-registry.json",
)
LEGACY_BRIDGE_WRITE_ALLOWLIST = {
    "platform/automation/planner_subagent_manager.py",
    "platform/automation/compat/legacy_workers/worker_manager.py",
    "platform/automation/orchestrator_paths.py",
}


def _git_files(mode: str) -> list[str]:
    if mode == "staged":
        cmd = ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"]
    elif mode == "changed":
        cmd = ["git", "diff", "--name-only", "--diff-filter=ACMR", "HEAD", "--"]
    elif mode == "all":
        cmd = ["git", "ls-files"]
    else:
        raise ValueError(f"unsupported mode: {mode}")
    cp = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)
    if cp.returncode != 0:
        raise RuntimeError(cp.stderr.strip() or "git command failed")
    return [line.strip() for line in (cp.stdout or "").splitlines() if line.strip()]


def _read_stdin_files() -> list[str]:
    return [line.strip() for line in sys.stdin.read().splitlines() if line.strip()]


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except Exception:
        return str(path)


def _load_active_docs() -> set[str]:
    text = _read_text(ACTIVE_DOCS_INDEX)
    links = re.findall(r"\[[^\]]+\]\(([^)]+)\)", text)
    docs: set[str] = set()
    for target in links:
        raw = target.split("#", 1)[0].split(":", 1)[0].strip()
        if not raw:
            continue
        candidate = Path(raw)
        if not candidate.is_absolute():
            candidate = (ROOT / candidate).resolve()
        try:
            rel = candidate.relative_to(ROOT)
        except Exception:
            continue
        docs.add(str(rel))
    return docs


def _check_active_docs_index(active_docs: set[str]) -> list[str]:
    violations: list[str] = []
    for required in sorted(ACTIVE_DOCS_REQUIRED):
        if required not in active_docs:
            violations.append(
                f"ARCH_POLICY_FAIL file=docs/ops/ACTIVE_DOCS_INDEX.md rule=active_docs_index_missing detail={required}"
            )
        elif not (ROOT / required).exists():
            violations.append(
                f"ARCH_POLICY_FAIL file=docs/ops/ACTIVE_DOCS_INDEX.md rule=active_doc_missing_on_disk detail={required}"
            )
    return violations


def _check_doc(path: Path, active_docs: set[str]) -> list[str]:
    violations: list[str] = []
    rel = _relative(path)
    if rel.startswith("docs/ops/archive/"):
        return violations

    text = _read_text(path)
    low = text.lower()
    in_index = rel in active_docs
    is_active = "status: active" in low
    is_archived = "status: archived" in low
    is_reference = "status: reference" in low
    has_superseded = "superseded_by:" in low

    if is_active and not in_index:
        violations.append(
            f"ARCH_POLICY_FAIL file={rel} rule=active_doc_not_in_index detail=active docs must be listed in ACTIVE_DOCS_INDEX.md"
        )

    if (not in_index) and not is_archived and not is_reference and not has_superseded:
        violations.append(
            f"ARCH_POLICY_FAIL file={rel} rule=doc_unclassified detail=non-active docs must be archived, reference, or superseded"
        )

    if in_index and ("pull request" in low or "pull requests" in low):
        violations.append(
            f"ARCH_POLICY_FAIL file={rel} rule=pr_workflow_forbidden detail=active docs must not describe PR workflow as canonical"
        )

    if in_index and "openai-agents-python" in low and not has_superseded:
        violations.append(
            f"ARCH_POLICY_FAIL file={rel} rule=second_backbone_in_active_doc detail=openai-agents-python cannot be an active backbone"
        )

    if rel in LEGACY_BACKLOG_DOCS and (is_active or "status: canonical" in low):
        violations.append(
            f"ARCH_POLICY_FAIL file={rel} rule=legacy_backlog_doc_canonical_forbidden detail=legacy backlog docs must remain reference/historical"
        )

    return violations


def _check_platform_code(path: Path) -> list[str]:
    rel = _relative(path)
    if path.suffix not in CODE_SUFFIXES:
        return []
    text = _read_text(path)
    violations: list[str] = []
    if "g4f" in text.lower():
        violations.append(
            f"ARCH_POLICY_FAIL file={rel} rule=app_provider_leak detail=platform runtime code must not own g4f/app-provider logic"
        )
    deleted_legacy_paths = (
        "platform/automation/openclaw_control_plane.py",
        "platform/automation/worker_manager.py",
        "platform/automation/parallel_workstream.py",
        "platform/automation/planner_board_runtime.py",
        "platform/automation/planner_dispatch_metrics.py",
        "platform/automation/orchestration_runtime/",
    )
    if any(marker in text for marker in deleted_legacy_paths):
        violations.append(
            f"ARCH_POLICY_FAIL file={rel} rule=deleted_legacy_path_forbidden detail=use canonical paths under runtime/*, planning/plane/*, operator/openclaw/*, or compat/projections/* instead of deleted legacy shims"
        )
    return violations


def _check_app_code(path: Path) -> list[str]:
    rel = _relative(path)
    if path.suffix not in CODE_SUFFIXES:
        return []
    text = _read_text(path)
    patterns = {
        "agent_runtime_import_forbidden": r"platform(?:/|\.)automation|orchestration_runtime|planner_subagent_manager",
        "agent_provider_import_forbidden": r"openclaw|qwen",
    }
    violations: list[str] = []
    for rule, pattern in patterns.items():
        if re.search(pattern, text, flags=re.IGNORECASE):
            violations.append(
                f"ARCH_POLICY_FAIL file={rel} rule={rule} detail=app plane must not depend on agent runtime or agent providers"
            )
    return violations


def _check_legacy_sdk(path: Path) -> list[str]:
    rel = _relative(path)
    if rel.startswith("platform/agents_sdk/") and path.suffix in CODE_SUFFIXES:
        return [
            f"ARCH_POLICY_FAIL file={rel} rule=legacy_agents_sdk_forbidden detail=platform/agents_sdk is non-canonical and must not grow"
        ]
    return []


def _check_runtime_projection_paths(path: Path) -> list[str]:
    rel = _relative(path)
    if path.suffix not in CODE_SUFFIXES:
        return []
    if rel in RUNTIME_PROJECTION_PATH_ALLOWLIST:
        return []
    if not (
        rel.startswith("platform/automation/")
        or rel.startswith("platform/policies/")
        or rel.startswith("apps/monitor/")
        or rel == "finance-copilot.sh"
    ):
        return []

    text = _read_text(path)
    patterns = (
        r"docs/operations/orchestrator/",
        r"docs/orchestrator-ops/",
        r"[\"']docs[\"']\s*/\s*[\"']operations[\"']\s*/\s*[\"']orchestrator[\"']",
        r"[\"']docs[\"']\s*/\s*[\"']orchestrator-ops[\"']",
    )
    for pattern in patterns:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return [
                f"ARCH_POLICY_FAIL file={rel} rule=runtime_projection_path_forbidden detail=runtime code must use orchestrator path helpers, not hardcoded docs projections"
            ]
    return []


def _check_plane_work_items_only(path: Path) -> list[str]:
    rel = _relative(path)
    if path.suffix not in CODE_SUFFIXES and path.suffix != ".md":
        return []
    if not (
        rel.startswith("platform/automation/")
        or rel.startswith("platform/policies/")
        or rel.startswith("docs/ops/")
        or rel.startswith("docs/product/planning/")
    ):
        return []
    text = _read_text(path)
    low = text.lower()
    if "plane" not in low:
        return []
    if "/issues" in low or " issues endpoint" in low or "plane issues" in low:
        return [
            f"ARCH_POLICY_FAIL file={rel} rule=plane_issues_endpoint_forbidden detail=Plane backlog integrations must use work-items, not issues"
        ]
    return []


def _check_legacy_bridge_primary_reads(path: Path) -> list[str]:
    rel = _relative(path)
    if path.suffix not in CODE_SUFFIXES:
        return []
    protected_prefixes = (
        "platform/automation/runtime/",
        "apps/monitor/services/",
        "apps/monitor/collectors/",
    )
    protected_files = {
        "platform/automation/doctor.py",
        "platform/automation/fc_doctor.py",
        "apps/monitor/server.py",
    }
    if not any(rel.startswith(prefix) for prefix in protected_prefixes) and rel not in protected_files:
        return []
    text = _read_text(path)
    for bridge in LEGACY_RUNTIME_BRIDGES:
        if bridge in text:
            return [
                f"ARCH_POLICY_FAIL file={rel} rule=legacy_bridge_primary_read_forbidden detail=runtime truth, status, and doctor paths must not depend on legacy registry files"
            ]
    return []


def _check_active_script_legacy_backlog_sources(path: Path) -> list[str]:
    rel = _relative(path)
    if path.suffix not in {".py", ".sh"}:
        return []
    if not (rel.startswith("platform/automation/") or rel.startswith("platform/policies/") or rel.startswith("scripts/")):
        return []

    text = _read_text(path)
    legacy_patterns = (
        "docs/product/planning/tasks.md",
        "docs/product/planning/stories.md",
        "docs/product/planning/epics.md",
        "docs/planning/",
    )
    if not any(pattern in text for pattern in legacy_patterns):
        return []

    allowed_negative_markers = (
        "never treat",
        "do not use",
        "must not use",
        "ne traite jamais",
        "forbidden",
        "legacy",
    )
    lowered = text.lower()
    if any(pattern in lowered for pattern in allowed_negative_markers):
        return []
    return [
        f"ARCH_POLICY_FAIL file={rel} rule=legacy_backlog_source_in_active_script detail=active scripts must not treat backlog docs as canonical inputs"
    ]


def _check_parallel_workstream_mutation_usage(path: Path) -> list[str]:
    rel = _relative(path)
    if path.suffix not in {".py", ".sh"}:
        return []
    if rel.startswith("platform/automation/tests/") or rel.startswith("tests/"):
        return []
    if rel == "platform/automation/compat/projections/parallel_workstream.py":
        return []
    if not (rel.startswith("platform/automation/") or rel.startswith("platform/policies/") or rel.startswith("scripts/")):
        return []

    text = _read_text(path)
    if "parallel_workstream.py" not in text:
        return []

    mutation_patterns = (
        "parallel_workstream.py sanitize-dependencies",
        "parallel_workstream.py sync-priority",
        "parallel_workstream.py reconcile-state",
        "parallel_workstream.py planner-autobatch",
        "parallel_workstream.py claim",
        "parallel_workstream.py complete",
        "parallel_workstream.py block",
        "parallel_workstream.py unblock",
        "parallel_workstream.py handoff-ack",
        "parallel_workstream.py handoff-close",
    )
    if not any(pattern in text for pattern in mutation_patterns):
        return []
    return [
        f"ARCH_POLICY_FAIL file={rel} rule=parallel_workstream_mutation_forbidden detail=active scripts must call runtime/planner/planner_runtime_actions.py for planner/workboard mutations"
    ]


def _check_legacy_bridge_primary_writes(path: Path) -> list[str]:
    rel = _relative(path)
    if path.suffix not in CODE_SUFFIXES:
        return []
    if not (rel.startswith("platform/automation/") or rel.startswith("platform/policies/")):
        return []
    if rel in LEGACY_BRIDGE_WRITE_ALLOWLIST:
        return []

    text = _read_text(path)
    if not any(bridge in text for bridge in LEGACY_RUNTIME_BRIDGES):
        return []

    write_markers = (
        "resolve_orchestrator_write_path(",
        "write_text(",
        "_write_json(",
        "_append_jsonl(",
        "json.dump(",
    )
    if any(marker in text for marker in write_markers):
        return [
            f"ARCH_POLICY_FAIL file={rel} rule=legacy_bridge_primary_write_forbidden detail=legacy registries may only be written from explicit compat/runtime bridge owners"
        ]
    return []


def _collect_path_violations(path: Path, active_docs: set[str]) -> list[str]:
    rel = _relative(path)
    violations: list[str] = []
    if rel.startswith("docs/ops/") and path.suffix == ".md":
        violations.extend(_check_doc(path, active_docs))
    if rel.startswith("platform/automation/") or rel.startswith("platform/policies/"):
        violations.extend(_check_platform_code(path))
    if rel.startswith("apps/api/") or rel.startswith("apps/web/"):
        violations.extend(_check_app_code(path))
    violations.extend(_check_legacy_sdk(path))
    violations.extend(_check_runtime_projection_paths(path))
    violations.extend(_check_plane_work_items_only(path))
    violations.extend(_check_legacy_bridge_primary_reads(path))
    violations.extend(_check_legacy_bridge_primary_writes(path))
    violations.extend(_check_active_script_legacy_backlog_sources(path))
    violations.extend(_check_parallel_workstream_mutation_usage(path))
    return violations


def evaluate_repo(root: Path | None = None) -> dict[str, object]:
    workspace_root = (root or ROOT).resolve()
    if workspace_root != ROOT:
        raise ValueError(f"unsupported root: {workspace_root}")

    active_docs = _load_active_docs()
    violations = _check_active_docs_index(active_docs)
    advisories: list[str] = []

    for raw in _git_files("all"):
        path = (ROOT / raw).resolve()
        if not path.exists() or path.is_dir():
            continue
        violations.extend(_collect_path_violations(path, active_docs))

    app_plane_import_violations = 0
    agent_plane_import_violations = 0
    active_docs_outside_index_count = 0
    legacy_projection_ref_count = 0
    for line in violations:
        if "rule=agent_runtime_import_forbidden" in line or "rule=agent_provider_import_forbidden" in line:
            app_plane_import_violations += 1
        if "rule=app_provider_leak" in line or "rule=legacy_agents_sdk_forbidden" in line:
            agent_plane_import_violations += 1
        if "rule=active_doc_not_in_index" in line or "rule=active_docs_index_missing" in line:
            active_docs_outside_index_count += 1
        if "rule=runtime_projection_path_forbidden" in line:
            legacy_projection_ref_count += 1

    critical_violations = len(violations)
    status = "ok" if critical_violations == 0 else "degraded"
    return {
        "status": status,
        "counts": {
            "critical_violations": critical_violations,
            "app_plane_import_violations": app_plane_import_violations,
            "agent_plane_import_violations": agent_plane_import_violations,
            "active_docs_outside_index_count": active_docs_outside_index_count,
            "legacy_projection_ref_count": legacy_projection_ref_count,
        },
        "violations": violations,
        "advisories": advisories,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Architectural policy guard")
    ap.add_argument("--mode", choices=("staged", "changed", "all"), default="changed")
    ap.add_argument("--files-from-stdin", action="store_true")
    ap.add_argument("files", nargs="*")
    args = ap.parse_args()

    if args.files:
        file_list = list(dict.fromkeys(args.files))
    elif args.files_from_stdin:
        file_list = list(dict.fromkeys(_read_stdin_files()))
    else:
        file_list = list(dict.fromkeys(_git_files(args.mode)))

    active_docs = _load_active_docs()
    violations = _check_active_docs_index(active_docs)

    for raw in file_list:
        path = (ROOT / raw).resolve()
        if not path.exists() or path.is_dir():
            continue
        violations.extend(_collect_path_violations(path, active_docs))

    if violations:
        for line in violations:
            print(line)
        return 1

    print(f"ARCH_POLICY_OK files={len(file_list)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
