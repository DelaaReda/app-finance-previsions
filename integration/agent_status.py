from __future__ import annotations

from pathlib import Path
import json
from typing import Optional, List, Dict


def _latest_dt(base: Path, pattern: str) -> Optional[str]:
    files = sorted(base.glob(pattern))
    if not files:
        return None
    # Expect parent folder dt=YYYYMMDD*
    p = files[-1]
    for parent in [p.parent, p.parent.parent]:
        if parent.name.startswith("dt="):
            return parent.name.split("=", 1)[1]
    return None


def _status_from_dt(dt_str: Optional[str]) -> str:
    return "OK" if dt_str else "MISSING"


def get_agent_status_data() -> List[Dict]:
    base = Path("data")
    rows: List[Dict] = []

    # Quality freshness
    q_dt = _latest_dt(base / "quality", "dt=*/freshness.json")
    rows.append({"name": "UpdateMonitor", "status": _status_from_dt(q_dt), "latest_dt": q_dt or "—"})

    # Equity forecasts aggregated
    f_dt = _latest_dt(base / "forecast", "dt=*/final.parquet")
    rows.append({"name": "ForecastAggregate", "status": _status_from_dt(f_dt), "latest_dt": f_dt or "—"})

    # Macro forecast
    m_dt = _latest_dt(base / "macro" / "forecast", "dt=*/macro_forecast.*")
    rows.append({"name": "MacroForecast", "status": _status_from_dt(m_dt), "latest_dt": m_dt or "—"})

    # LLM summary
    l_dt = _latest_dt(base / "llm_summary", "dt=*/summary.json")
    rows.append({"name": "LLMSummary", "status": _status_from_dt(l_dt), "latest_dt": l_dt or "—"})

    return rows


if __name__ == "__main__":
    print(json.dumps(get_agent_status_data(), ensure_ascii=False, indent=2))
