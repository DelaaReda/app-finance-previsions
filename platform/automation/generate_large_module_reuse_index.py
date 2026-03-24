#!/usr/bin/env python3
"""Generate an index of large backend modules to improve reuse visibility.

This keeps module discovery explicit for agents before they create new files.
"""

from __future__ import annotations

import argparse
import ast
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

CANONICAL_PROJECT_ROOT = Path("/home/venom/analyse-financiere")
PROJECT_ROOT = CANONICAL_PROJECT_ROOT if CANONICAL_PROJECT_ROOT.exists() else Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = PROJECT_ROOT / "docs/ops/LARGE_MODULE_REUSE_INDEX.md"
TARGET_BACKEND = "apps/api/src"
DEFAULT_SCAN_ROOTS = [
    TARGET_BACKEND,
    f"{TARGET_BACKEND}/domains",
    f"{TARGET_BACKEND}/platform",
    f"{TARGET_BACKEND}/legacy",
    f"{TARGET_BACKEND}/services",
    f"{TARGET_BACKEND}/jobs",
    f"{TARGET_BACKEND}/models",
    f"{TARGET_BACKEND}/storage",
]
EXCLUDE_PARTS = {".venv", "__pycache__", "legacy-archive", "tests"}
MAX_SYMBOLS = 8

SPECIAL_REUSE_NOTES = {
    f"{TARGET_BACKEND}/platform/main.py": (
        "FastAPI bootstrap/reference only. Keep orchestration thin, avoid new business logic here."
    ),
    "apps/api/src/domains/judge/application/forecast_decision.py": (
        "Protected Judge template route. Reuse patterns/services around it; do not clone route logic inline."
    ),
    f"{TARGET_BACKEND}/domains/judge/application/judge_service.py": (
        "Protected Judge template route. Reuse patterns/services around it; do not clone route logic inline."
    ),
    f"{TARGET_BACKEND}/platform/legacy/services/g4f_client.py": (
        "Canonical LLM call entrypoint (model mode + fallback handling)."
    ),
    f"{TARGET_BACKEND}/platform/legacy/analytics/econ_llm_agent.py": (
        "Central economic LLM analyst module reused by multiple routes/agents."
    ),
    f"{TARGET_BACKEND}/services/judge_pipeline.py": (
        "Shared verdict computation pipeline; reuse from services, not routes."
    ),
    f"{TARGET_BACKEND}/services/forecast_service.py": (
        "Forecast endpoint orchestration service aligned with Judge template parity."
    ),
}

PRIORITY_REUSE_PATHS = {
    f"{TARGET_BACKEND}/platform/legacy/analytics/econ_llm_agent.py": "LLM economic analyst core.",
    f"{TARGET_BACKEND}/platform/legacy/services/g4f_client.py": "Canonical LLM wrapper (mode + fallback).",
    f"{TARGET_BACKEND}/services/judge_pipeline.py": "Judge-grade verdict pipeline.",
    f"{TARGET_BACKEND}/services/forecast_service.py": "Forecast orchestration service.",
    f"{TARGET_BACKEND}/platform/legacy/analytics/phase1_fundamental.py": "Fundamental forecast block.",
    f"{TARGET_BACKEND}/platform/legacy/analytics/phase2_technical.py": "Technical forecast block.",
    f"{TARGET_BACKEND}/platform/legacy/analytics/phase3_macro.py": "Macro regime/nowcast block.",
    f"{TARGET_BACKEND}/platform/legacy/analytics/phase4_sentiment.py": "Sentiment/news signal block.",
    f"{TARGET_BACKEND}/platform/legacy/analytics/phase5_fusion.py": "Multi-signal fusion block.",
    f"{TARGET_BACKEND}/platform/legacy/analytics/market_intel.py": "Market context pack builder.",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--min-lines",
        type=int,
        default=400,
        help="Minimum number of lines for a module to appear in the index.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help=f"Output markdown file (default: {DEFAULT_OUTPUT}).",
    )
    parser.add_argument(
        "--roots",
        nargs="+",
        default=DEFAULT_SCAN_ROOTS,
        help="Relative roots to scan for python modules.",
    )
    return parser.parse_args()


def should_skip(path: Path) -> bool:
    return any(part in EXCLUDE_PARTS for part in path.parts)


def iter_python_files(roots: Iterable[str]) -> Iterable[Path]:
    seen: set[Path] = set()
    for root in roots:
        root_path = PROJECT_ROOT / root
        if not root_path.exists():
            continue
        for file_path in root_path.rglob("*.py"):
            file_path = file_path.resolve()
            if should_skip(file_path):
                continue
            if file_path in seen:
                continue
            seen.add(file_path)
            yield file_path


def line_count(path: Path) -> int:
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        return sum(1 for _ in handle)


def public_symbols(path: Path) -> list[str]:
    try:
        source = path.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(source)
    except Exception:
        return []

    symbols: list[str] = []
    for node in tree.body:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            name = node.name
            if not name.startswith("_"):
                symbols.append(name)
        if len(symbols) >= MAX_SYMBOLS:
            break
    return symbols


def category_for(rel_path: str) -> str:
    if rel_path.endswith("/platform/main.py"):
        return "api_entrypoint"
    if "/api/routes/" in rel_path:
        return "api_route"
    if "/domains/" in rel_path and "/application/" in rel_path:
        return "api_service_facade"
    if any(segment in rel_path for segment in ("/services/", "/backend/services/", f"/{TARGET_BACKEND}/services/")):
        return "service"
    if "/analytics/" in rel_path:
        return "analytics"
    if "/ingestion/" in rel_path:
        return "ingestion"
    if "/research/" in rel_path:
        return "research"
    if "/core/" in rel_path:
        return "core"
    if "/agents/" in rel_path:
        return "agent"
    if rel_path.startswith("copilot-app/backend/jobs/") or rel_path.startswith(f"{TARGET_BACKEND}/jobs"):
        return "job"
    if rel_path.startswith("copilot-app/backend/models/") or rel_path.startswith(f"{TARGET_BACKEND}/models"):
        return "model"
    if rel_path.startswith("copilot-app/backend/storage/") or rel_path.startswith(f"{TARGET_BACKEND}/storage"):
        return "storage"
    return "module"


def import_hint(rel_path: str) -> str:
    if rel_path.startswith(f"{TARGET_BACKEND}/"):
        module = (
            Path(rel_path)
            .relative_to(TARGET_BACKEND)
            .with_suffix("")
            .as_posix()
            .replace("/", ".")
        )
        return f"from {module} import ..."
    if rel_path.startswith("copilot-app/backend/jobs/"):
        module = (
            Path(rel_path)
            .relative_to("copilot-app/backend/jobs")
            .with_suffix("")
            .as_posix()
            .replace("/", ".")
        )
        return f"from jobs.{module} import ..."
    if rel_path.startswith("copilot-app/backend/models/"):
        module = (
            Path(rel_path)
            .relative_to("copilot-app/backend/models")
            .with_suffix("")
            .as_posix()
            .replace("/", ".")
        )
        return f"from models.{module} import ..."
    if rel_path.startswith("copilot-app/backend/storage/"):
        module = (
            Path(rel_path)
            .relative_to("copilot-app/backend/storage")
            .with_suffix("")
            .as_posix()
            .replace("/", ".")
        )
        return f"from storage.{module} import ..."
    return "n/a"


def default_note(category: str) -> str:
    if category == "api_route":
        return "Reference endpoint. Keep reusable logic in services/core modules."
    if category == "api_entrypoint":
        return "Bootstrap layer only."
    if category == "job":
        return "Scheduler layer. Reuse services/core helpers instead of job-to-job copy."
    if category == "api_service_facade":
        return "Facade layer for routes; good place for thin composition."
    return "Reusable implementation candidate."


def escape_cell(value: str) -> str:
    return value.replace("|", "\\|")


def render_markdown(
    modules: list[dict[str, str | int | list[str]]],
    min_lines: int,
    roots: list[str],
) -> str:
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    lines: list[str] = [
        "# Large Module Reuse Index (Backend)",
        "",
        f"Generated at: `{generated_at}`",
        f"Threshold: `>= {min_lines}` lines",
        "",
        "Purpose: make large modules obvious and reusable before creating new code.",
        "",
        "Regenerate with:",
        "```bash",
        "python3 platform/automation/generate_large_module_reuse_index.py",
        "```",
        "",
        "Scan roots:",
    ]
    for root in roots:
        lines.append(f"- `{root}`")

    lines.extend(["", "## Summary", ""])
    category_counts = Counter(str(module["category"]) for module in modules)
    lines.append(f"- Total modules listed: `{len(modules)}`")
    for category, count in sorted(category_counts.items(), key=lambda item: item[0]):
        lines.append(f"- `{category}`: `{count}`")

    lines.extend(["", "## Priority Reuse Modules", ""])
    priority_modules = [
        module for module in modules if str(module["path"]) in PRIORITY_REUSE_PATHS
    ]
    if priority_modules:
        priority_modules.sort(key=lambda item: str(item["path"]))
        for module in priority_modules:
            rel_path = str(module["path"])
            reason = PRIORITY_REUSE_PATHS.get(rel_path, "Priority reusable module.")
            lines.append(
                "- "
                f"`{rel_path}` "
                f"({module['lines']} lines) -> "
                f"`{module['import_hint']}` "
                f"- {reason}"
            )
    else:
        lines.append("- No priority modules met the threshold in this scan.")

    lines.extend(
        [
            "",
            "## Modules",
            "",
            "| Lines | Module | Category | Import Hint | Public Symbols (sample) | Reuse Note |",
            "|---:|---|---|---|---|---|",
        ]
    )

    for module in modules:
        rel_path = str(module["path"])
        module_lines = int(module["lines"])
        category = str(module["category"])
        hint = str(module["import_hint"])
        symbols = module["symbols"]  # type: ignore[assignment]
        symbols_text = ", ".join(symbols) if symbols else "-"
        note = SPECIAL_REUSE_NOTES.get(rel_path, default_note(category))

        lines.append(
            "| "
            + f"{module_lines} | `{escape_cell(rel_path)}` | `{escape_cell(category)}` | "
            + f"`{escape_cell(hint)}` | `{escape_cell(symbols_text)}` | {escape_cell(note)} |"
        )

    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = PROJECT_ROOT / output_path

    modules: list[dict[str, str | int | list[str]]] = []
    for file_path in iter_python_files(args.roots):
        count = line_count(file_path)
        if count < args.min_lines:
            continue
        rel_path = file_path.relative_to(PROJECT_ROOT).as_posix()
        modules.append(
            {
                "path": rel_path,
                "lines": count,
                "category": category_for(rel_path),
                "import_hint": import_hint(rel_path),
                "symbols": public_symbols(file_path),
            }
        )

    modules.sort(key=lambda item: (-int(item["lines"]), str(item["path"])))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        render_markdown(modules=modules, min_lines=args.min_lines, roots=args.roots),
        encoding="utf-8",
    )
    print(f"Generated {len(modules)} modules -> {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
