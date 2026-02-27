#!/usr/bin/env python3
"""Shared intent registry for multi-agent pre-announcements.

Purpose:
- Record delivery intents before claim/edit actions.
- Detect overlapping planned file scopes between active intents.
- Emit deterministic references that can be copied into EVIDENCE.
"""

from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "docs" / "orchestrator-ops" / "intent-registry.json"
DEFAULT_CHAT = ROOT / "docs" / "ops" / "ADMIN_TEAM_CHAT.md"
DEFAULT_MEMORY_DIR = ROOT / "memory"
DEFAULT_SHARED_LOCK_DIR = Path(os.environ.get("OPENCLAW_LOCK_DIR", "/tmp/openclaw-shared-locks"))
ACTIVE_STATUSES = {"active"}


def now_utc_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def now_local_est_display() -> str:
    return dt.datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d %H:%M:%S %Z")


def parse_files(raw: str) -> List[str]:
    out: List[str] = []
    for part in raw.split(","):
        item = part.strip()
        if not item:
            continue
        out.append(item)
    # Stable dedupe preserving order.
    seen = set()
    uniq: List[str] = []
    for item in out:
        if item in seen:
            continue
        seen.add(item)
        uniq.append(item)
    return uniq


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def load_registry(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"version": 1, "updatedAtUtc": now_utc_iso(), "intents": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"version": 1, "updatedAtUtc": now_utc_iso(), "intents": []}
    if not isinstance(data, dict):
        return {"version": 1, "updatedAtUtc": now_utc_iso(), "intents": []}
    if "intents" not in data or not isinstance(data["intents"], list):
        data["intents"] = []
    if "version" not in data:
        data["version"] = 1
    return data


def write_registry(path: Path, payload: Dict[str, Any]) -> None:
    ensure_parent(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def memory_file_for_today(memory_dir: Path) -> Path:
    today = dt.datetime.now().strftime("%Y-%m-%d")
    return memory_dir / f"{today}.md"


def lock_path_for(registry_path: Path) -> Path:
    # Shared lock location avoids write failures on repo lock files in mixed runtimes.
    digest = hashlib.sha256(str(registry_path.resolve(strict=False)).encode("utf-8")).hexdigest()[:20]
    return DEFAULT_SHARED_LOCK_DIR / f"intent-registry-{digest}.lock"


def append_line(path: Path, line: str) -> int:
    ensure_parent(path)
    if not path.exists():
        path.write_text("", encoding="utf-8")
    with path.open("a+", encoding="utf-8") as fh:
        fh.write(line + "\n")
        fh.flush()
        fh.seek(0)
        line_count = sum(1 for _ in fh)
    return line_count


def active_conflicts(intents: List[Dict[str, Any]], files: List[str], intent_id: str) -> List[Dict[str, Any]]:
    target = set(files)
    conflicts: List[Dict[str, Any]] = []
    for entry in intents:
        if not isinstance(entry, dict):
            continue
        if entry.get("intent_id") == intent_id:
            continue
        status = str(entry.get("status", "")).strip().lower()
        if status not in ACTIVE_STATUSES:
            continue
        entry_files = entry.get("planned_files", [])
        if not isinstance(entry_files, list):
            continue
        overlap = sorted(target.intersection({str(x) for x in entry_files}))
        if not overlap:
            continue
        conflicts.append(
            {
                "intent_id": str(entry.get("intent_id", "unknown")),
                "role": str(entry.get("role", "unknown")),
                "overlap_files": overlap,
                "created_at_utc": str(entry.get("created_at_utc", "")),
            }
        )
    return conflicts


def make_intent_id(role: str) -> str:
    role_token = re.sub(r"[^a-zA-Z0-9]+", "_", role.strip().upper()) or "ROLE"
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"INTENT_{role_token}_{stamp}"


def cmd_preannounce(args: argparse.Namespace) -> int:
    role = args.role.strip()
    scope = args.scope.strip()
    files = parse_files(args.files)
    if not role:
        print("ERROR: role is required", file=sys.stderr)
        return 2
    if not scope:
        print("ERROR: scope is required", file=sys.stderr)
        return 2
    if not files:
        print("ERROR: files must contain at least one path", file=sys.stderr)
        return 2
    if args.eta_minutes <= 0:
        print("ERROR: eta-minutes must be > 0", file=sys.stderr)
        return 2

    registry_path = Path(args.registry).resolve()
    chat_path = Path(args.chat_file).resolve()
    memory_path = Path(args.memory_file).resolve() if args.memory_file else memory_file_for_today(Path(args.memory_dir).resolve())
    intent_id = args.intent_id.strip() if args.intent_id else make_intent_id(role)
    now_utc = now_utc_iso()
    now_local = now_local_est_display()
    lock_file = lock_path_for(registry_path)
    ensure_parent(lock_file)

    with lock_file.open("a+", encoding="utf-8") as lock_fh:
        fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX)
        registry = load_registry(registry_path)
        intents = registry.get("intents", [])
        conflicts = active_conflicts(intents, files, intent_id)
        if conflicts and not args.allow_overlap:
            conflict_short = ",".join(
                f"{c['intent_id']}:{'|'.join(c['overlap_files'])}" for c in conflicts
            )
            print("STATUS: BLOCKED")
            print("DELTA: intent_overlap_conflict")
            print(f"EVIDENCE: intent_id={intent_id}; conflicts={conflict_short}")
            print("RISKS: co-edition concurente detectee, risque d ecrasement")
            print("NEXT: coordonner handoff/merge ou reduire planned_files puis relancer preannounce")
            print("VERDICT: BLOCKED")
            print("BLOCKER_ID: INTENT_OVERLAP_CONFLICT")
            print(f"NEXT_ACTION_UNIQUE: PREANNOUNCE_BLOCKED_{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%d%H%M%S')}")
            return 2

        entry = {
            "intent_id": intent_id,
            "role": role,
            "scope": scope,
            "planned_files": files,
            "eta_minutes": int(args.eta_minutes),
            "status": "active",
            "created_at_utc": now_utc,
            "created_at_local": now_local,
            "owner_note": args.note.strip() if args.note else "",
            "chat_ref": "",
            "memory_ref": "",
        }
        intents.append(entry)
        registry["intents"] = intents
        registry["updatedAtUtc"] = now_utc

        # Append chat + memory and capture line refs.
        files_csv = ",".join(files)
        chat_line = (
            f"- [{now_local}] [{role}] TYPE: INTENT MSG: intent_id={intent_id} "
            f"planned_files={files_csv} edit_scope={scope} eta_minutes={args.eta_minutes} "
            f"status=active. NEXT: claim puis patch scope strict."
        )
        chat_lineno = append_line(chat_path, chat_line)
        chat_ref = f"{chat_path}:{chat_lineno}"

        memory_line = (
            f"- [{now_utc}] PREANNOUNCE intent_id={intent_id} role={role} scope={scope} "
            f"files={files_csv} eta_minutes={args.eta_minutes} status=active"
        )
        memory_lineno = append_line(memory_path, memory_line)
        memory_ref = f"{memory_path}:{memory_lineno}"

        entry["chat_ref"] = chat_ref
        entry["memory_ref"] = memory_ref
        write_registry(registry_path, registry)

    registry_ref = f"{registry_path}#intent_id={intent_id}"
    print("STATUS: OK")
    print("DELTA: preannounce_recorded")
    print(
        "EVIDENCE: "
        f"intent_id={intent_id}; intent_chat_ref={chat_ref}; intent_memory_ref={memory_ref}; "
        f"intent_registry_ref={registry_ref}; edit_scope={scope}"
    )
    print("RISKS: none")
    print("NEXT: executer claim puis edition dans le scope annonce")
    print("VERDICT: PASS")
    print("BLOCKER_ID: NONE")
    print(f"NEXT_ACTION_UNIQUE: PREANNOUNCE_{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%d%H%M%S')}")
    return 0


def cmd_close(args: argparse.Namespace) -> int:
    intent_id = args.intent_id.strip()
    if not intent_id:
        print("ERROR: intent-id is required", file=sys.stderr)
        return 2
    status = args.status.strip().lower()
    if status not in {"done", "cancelled", "blocked"}:
        print("ERROR: status must be one of done|cancelled|blocked", file=sys.stderr)
        return 2

    registry_path = Path(args.registry).resolve()
    chat_path = Path(args.chat_file).resolve()
    memory_path = Path(args.memory_file).resolve() if args.memory_file else memory_file_for_today(Path(args.memory_dir).resolve())
    now_utc = now_utc_iso()
    now_local = now_local_est_display()
    lock_file = lock_path_for(registry_path)
    ensure_parent(lock_file)

    with lock_file.open("a+", encoding="utf-8") as lock_fh:
        fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX)
        registry = load_registry(registry_path)
        intents = registry.get("intents", [])
        target = None
        for entry in intents:
            if isinstance(entry, dict) and str(entry.get("intent_id", "")) == intent_id:
                target = entry
                break
        if target is None:
            print("STATUS: BLOCKED")
            print("DELTA: intent_not_found")
            print(f"EVIDENCE: intent_id={intent_id}; registry={registry_path}")
            print("RISKS: impossible de fermer un intent absent")
            print("NEXT: verifier intent_id puis relancer")
            print("VERDICT: BLOCKED")
            print("BLOCKER_ID: INTENT_NOT_FOUND")
            print(f"NEXT_ACTION_UNIQUE: INTENT_CLOSE_BLOCKED_{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%d%H%M%S')}")
            return 2

        target["status"] = status
        target["closed_at_utc"] = now_utc
        target["close_note"] = args.note.strip() if args.note else ""
        registry["updatedAtUtc"] = now_utc

        role = str(target.get("role", args.role or "codex"))
        close_msg = (
            f"- [{now_local}] [{role}] TYPE: DONE MSG: intent_id={intent_id} "
            f"status={status}. NEXT: scope libere pour autres agents."
        )
        chat_lineno = append_line(chat_path, close_msg)
        memory_line = (
            f"- [{now_utc}] PREANNOUNCE_CLOSE intent_id={intent_id} role={role} status={status}"
        )
        memory_lineno = append_line(memory_path, memory_line)
        target["close_chat_ref"] = f"{chat_path}:{chat_lineno}"
        target["close_memory_ref"] = f"{memory_path}:{memory_lineno}"
        write_registry(registry_path, registry)

    print("STATUS: OK")
    print("DELTA: intent_closed")
    print(
        "EVIDENCE: "
        f"intent_id={intent_id}; status={status}; "
        f"chat_ref={target.get('close_chat_ref','')}; memory_ref={target.get('close_memory_ref','')}"
    )
    print("RISKS: none")
    print("NEXT: poursuivre workflow normal")
    print("VERDICT: PASS")
    print("BLOCKER_ID: NONE")
    print(f"NEXT_ACTION_UNIQUE: INTENT_CLOSE_{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%d%H%M%S')}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    registry_path = Path(args.registry).resolve()
    data = load_registry(registry_path)
    intents = data.get("intents", [])
    active = [x for x in intents if isinstance(x, dict) and str(x.get("status", "")).lower() in ACTIVE_STATUSES]
    if args.json:
        print(json.dumps({"registry": str(registry_path), "active": active}, ensure_ascii=True, indent=2))
        return 0
    if not active:
        print("ACTIVE_INTENTS none")
        return 0
    print(f"ACTIVE_INTENTS total={len(active)} registry={registry_path}")
    for entry in active:
        files = "|".join(entry.get("planned_files", []))
        print(
            " - "
            f"{entry.get('intent_id','?')} role={entry.get('role','?')} "
            f"scope={entry.get('scope','?')} files={files} created_at={entry.get('created_at_utc','?')}"
        )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Intent registry helper for multi-agent orchestration")
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY), help="Path to intent registry JSON")
    parser.add_argument("--chat-file", default=str(DEFAULT_CHAT), help="Path to shared admin chat markdown")
    parser.add_argument("--memory-dir", default=str(DEFAULT_MEMORY_DIR), help="Memory directory root (for today's file)")
    parser.add_argument("--memory-file", default="", help="Override memory file path")

    sub = parser.add_subparsers(dest="command", required=True)

    p_pre = sub.add_parser("preannounce", help="Register and publish a new intent")
    p_pre.add_argument("--role", required=True)
    p_pre.add_argument("--scope", required=True)
    p_pre.add_argument("--files", required=True, help="Comma-separated planned files")
    p_pre.add_argument("--eta-minutes", type=int, default=30)
    p_pre.add_argument("--intent-id", default="")
    p_pre.add_argument("--note", default="")
    p_pre.add_argument("--allow-overlap", action="store_true")
    p_pre.set_defaults(func=cmd_preannounce)

    p_close = sub.add_parser("close", help="Close an existing intent")
    p_close.add_argument("--intent-id", required=True)
    p_close.add_argument("--status", default="done")
    p_close.add_argument("--note", default="")
    p_close.add_argument("--role", default="")
    p_close.set_defaults(func=cmd_close)

    p_list = sub.add_parser("list", help="List active intents")
    p_list.add_argument("--json", action="store_true")
    p_list.set_defaults(func=cmd_list)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
