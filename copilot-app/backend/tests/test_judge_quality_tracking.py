from __future__ import annotations

from src.services.judge_quality_tracking import build_tracking_payload


def _report(
    *,
    as_of: str,
    horizon_days: int = 5,
    min_samples: int = 20,
    evaluated_rows: int = 0,
    edge_vs_baseline: float | None = None,
):
    return {
        "as_of": as_of,
        "horizon_days": horizon_days,
        "min_samples": min_samples,
        "coverage": {
            "evaluated_rows": evaluated_rows,
            "total_rows": max(evaluated_rows, 1),
            "with_price_series": evaluated_rows,
        },
        "overall": {
            "edge_vs_baseline": edge_vs_baseline,
            "hit_rate": 0.5,
            "brier": 0.2,
            "calibration_error": 0.1,
            "sample_status": "ok",
        },
        "recommendation": {"status": "neutral"},
    }


def test_tracking_payload_upserts_same_day_scope():
    existing = None
    payload_1 = build_tracking_payload(
        existing=existing,
        report=_report(
            as_of="2026-02-24T01:00:00Z",
            evaluated_rows=12,
            edge_vs_baseline=0.03,
        ),
    )
    assert len(payload_1["points"]) == 1
    assert payload_1["latest"]["evaluated_rows"] == 12

    payload_2 = build_tracking_payload(
        existing=payload_1,
        report=_report(
            as_of="2026-02-24T23:00:00Z",
            evaluated_rows=18,
            edge_vs_baseline=0.07,
        ),
    )
    assert len(payload_2["points"]) == 1
    assert payload_2["latest"]["evaluated_rows"] == 18
    assert payload_2["latest"]["edge_vs_baseline"] == 0.07


def test_tracking_payload_keeps_sorted_history_and_scope_kpis():
    payload = build_tracking_payload(
        existing=None,
        report=_report(
            as_of="2026-02-24T01:00:00Z",
            evaluated_rows=10,
            edge_vs_baseline=0.0,
        ),
    )
    payload = build_tracking_payload(
        existing=payload,
        report=_report(
            as_of="2026-02-25T01:00:00Z",
            evaluated_rows=20,
            edge_vs_baseline=0.1,
        ),
    )

    assert len(payload["points"]) == 2
    assert payload["points"][0]["date"] == "2026-02-24"
    assert payload["points"][1]["date"] == "2026-02-25"
    assert payload["kpis"]["points_in_scope"] == 2
    assert payload["kpis"]["avg_evaluated_rows_last_7"] == 15.0
    assert payload["kpis"]["avg_edge_vs_baseline_last_7"] == 0.05
