# src/research/brief_renderer.py
from __future__ import annotations
from typing import Dict, Any, List
from html import escape

def _signals_html(items: List[Dict[str, Any]], title: str) -> str:
    rows = "\n".join(
        f"<li><strong>{escape(i['label'])}</strong> — {i['value']:.2f} "
        f"<em>({escape(i.get('reason',''))})</em></li>"
        for i in (items or [])
    )
    return f"<h3>{escape(title)}</h3><ul>{rows}</ul>"

def render_brief_html(brief_payload: Dict[str, Any]) -> str:
    brief = brief_payload.get("brief", {})
    gen_at = brief_payload.get("generatedAt", "")
    parts = [
        f"<h2>Market Brief</h2>",
        f"<p><small>Generated at: {escape(gen_at)}</small></p>",
        _signals_html(brief.get("topSignals", []), "Top Signals"),
        _signals_html(brief.get("topRisks", []), "Top Risks"),
        "<h3>Picks</h3>",
        "<ul>" + "\n".join(
            f"<li><strong>{escape(p['ticker'])}</strong> — score {p['score']:.2f} "
            f"<em>({escape(p.get('rationale',''))})</em></li>"
            for p in (brief.get("picks", []) or [])
        ) + "</ul>",
    ]
    return "\n".join(parts)

def render_brief_md(brief_payload: Dict[str, Any]) -> str:
    brief = brief_payload.get("brief", {})
    gen_at = brief_payload.get("generatedAt", "")
    md = [f"# Market Brief", f"_Generated at: {gen_at}_", ""]
    def _mk_section(title: str, arr: List[Dict[str, Any]]):
        md.append(f"## {title}")
        if not arr:
            md.append("- _(empty)_")
            return
        for i in arr:
            md.append(f"- **{i['label']}** — {i['value']:.2f} _( {i.get('reason','')} )_")
        md.append("")
    _mk_section("Top Signals", brief.get("topSignals", []))
    _mk_section("Top Risks", brief.get("topRisks", []))
    md.append("## Picks")
    for p in (brief.get("picks", []) or []):
        md.append(f"- **{p['ticker']}** — score {p['score']:.2f} _( {p.get('rationale','')} )_")
    md.append("")
    return "\n".join(md)