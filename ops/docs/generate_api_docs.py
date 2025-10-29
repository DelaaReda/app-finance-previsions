#!/usr/bin/env python3
from __future__ import annotations

import ast
import os
from pathlib import Path
from typing import List, Optional

ROOT = Path(__file__).resolve().parents[2]
SRC_DIRS = [ROOT / "src" / p for p in ("core", "tools", "agents", "analytics")]
OUT_BASE = ROOT / "docs" / "api"


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _ann_to_str(node: Optional[ast.AST]) -> str:
    if node is None:
        return ""
    try:
        return ast.unparse(node)
    except Exception:
        return ""


def _default_to_str(node: Optional[ast.AST]) -> str:
    if node is None:
        return ""
    try:
        return ast.unparse(node)
    except Exception:
        return ""


def _params_details(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> List[str]:
    a = fn.args
    details: List[str] = []
    # positional-only (py3.8+)
    posonly = getattr(a, "posonlyargs", [])
    all_pos = list(posonly) + list(a.args)

    # defaults align to the last N positional args
    pos_defaults = a.defaults or []
    defaults_map = {}
    if pos_defaults:
        for i, d in enumerate(pos_defaults, start=len(all_pos) - len(pos_defaults)):
            defaults_map[i] = d

    for i, arg in enumerate(all_pos):
        if arg.arg in ("self", "cls"):
            continue
        ann = _ann_to_str(arg.annotation)
        default = _default_to_str(defaults_map.get(i)) if defaults_map else ""
        details.append(f"- `{arg.arg}`: {ann or 'Any'}" + (f" = {default}" if default else ""))

    if a.vararg is not None:
        details.append(f"- `*{a.vararg.arg}`: { _ann_to_str(a.vararg.annotation) or 'Any' }")

    # kwonly
    for kwarg, kwdef in zip(a.kwonlyargs, a.kw_defaults or []):
        ann = _ann_to_str(kwarg.annotation)
        default = _default_to_str(kwdef) if kwdef is not None else ""
        details.append(f"- `{kwarg.arg}` (kwonly): {ann or 'Any'}" + (f" = {default}" if default else ""))

    if a.kwarg is not None:
        details.append(f"- `**{a.kwarg.arg}`: { _ann_to_str(a.kwarg.annotation) or 'Any' }")

    return details


def _fn_sig(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    try:
        return f"def {fn.name}(...)->{_ann_to_str(fn.returns) or 'Any'}"
    except Exception:
        return f"def {fn.name}(...)"


def _doc_title(path: Path) -> str:
    rel = path.relative_to(ROOT)
    return str(rel)


def document_file(py_path: Path) -> Optional[str]:
    src = _read(py_path)
    if not src:
        return None
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return None

    mod_doc = ast.get_docstring(tree) or ""

    out: List[str] = []
    out.append(f"# {py_path.name}\n")
    if mod_doc:
        out.append(mod_doc.strip() + "\n")

    # Collect top-level functions and classes
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # skip private/dunder helpers
            if node.name.startswith("_"):
                continue
            out.append(f"## Function: `{node.name}`\n")
            out.append(f"Signature: `{_fn_sig(node)}`\n")
            ds = ast.get_docstring(node) or ""
            if ds:
                out.append(ds.strip() + "\n")
            out.append("Inputs:")
            pd = _params_details(node)
            if pd:
                out.extend(pd)
            else:
                out.append("- (none)")
            out.append(f"Returns: `{_ann_to_str(node.returns) or 'Any'}`\n")

        elif isinstance(node, ast.ClassDef):
            if node.name.startswith("_"):
                continue
            out.append(f"## Class: `{node.name}`\n")
            cds = ast.get_docstring(node) or ""
            if cds:
                out.append(cds.strip() + "\n")
            # methods
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and not item.name.startswith("_"):
                    out.append(f"### Method: `{node.name}.{item.name}`\n")
                    out.append(f"Signature: `{_fn_sig(item)}`\n")
                    ids = ast.get_docstring(item) or ""
                    if ids:
                        out.append(ids.strip() + "\n")
                    out.append("Inputs:")
                    pd = _params_details(item)
                    out.extend(pd if pd else ["- (none)"])
                    out.append(f"Returns: `{_ann_to_str(item.returns) or 'Any'}`\n")

    return "\n".join(out)


def main() -> int:
    OUT_BASE.mkdir(parents=True, exist_ok=True)
    index_lines: List[str] = ["# API Reference\n", "Modules documented here (auto-generated):\n"]
    for base in SRC_DIRS:
        for py in base.rglob("*.py"):
            # skip __init__ and UI pages
            if py.name == "__init__.py":
                continue
            rel = py.relative_to(ROOT)
            out_path = OUT_BASE / (str(rel).replace(os.sep, "__") + ".md")
            md = document_file(py)
            if not md:
                continue
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(md, encoding="utf-8")
            index_lines.append(f"- {rel}")

    (OUT_BASE / "README.md").write_text("\n".join(index_lines) + "\n", encoding="utf-8")
    print(f"[api-docs] written under {OUT_BASE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

