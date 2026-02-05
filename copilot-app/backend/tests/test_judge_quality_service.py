from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.services.judge_quality import build_judge_quality_report_from_data


def _make_price_series(start: datetime, days: int, start_price: float, step: float):
    out = []
    for i in range(days):
        ts = start + timedelta(days=i)
        out.append((ts, start_price + (i * step)))
    return out


def test_judge_quality_report_detects_underperforming_baseline():
    now = datetime(2026, 2, 5, 0, 0, tzinfo=timezone.utc)
    start = now - timedelta(days=70)
    prices = {
        "AAA": _make_price_series(start, 80, 100.0, 1.0),
    }
    rows = [
        {
            "ticker": "AAA",
            "timestamp": (now - timedelta(days=40)).isoformat().replace("+00:00", "Z"),
            "direction": "up",
            "expected_return": 0.02,
            "confidence": 0.70,
        },
        {
            "ticker": "AAA",
            "timestamp": (now - timedelta(days=35)).isoformat().replace("+00:00", "Z"),
            "direction": "down",
            "expected_return": -0.01,
            "confidence": 0.65,
        },
        {
            "ticker": "AAA",
            "timestamp": (now - timedelta(days=30)).isoformat().replace("+00:00", "Z"),
            "direction": "up",
            "expected_return": 0.015,
            "confidence": 0.75,
        },
    ]

    report = build_judge_quality_report_from_data(
        rows=rows,
        prices_by_ticker=prices,
        horizon_days=5,
        window_days=(60,),
        min_samples=2,
        now_utc=now,
    )

    assert report["overall"]["n"] == 3
    assert report["overall"]["hit_rate"] == 0.6667
    assert report["overall"]["baseline_hit_rate"] == 1.0
    assert report["recommendation"]["status"] == "underperforming_baseline"
    assert report["windows"]["60d"]["n"] == 3


def test_judge_quality_report_handles_no_evaluable_rows():
    now = datetime(2026, 2, 5, 0, 0, tzinfo=timezone.utc)
    prices = {"AAA": _make_price_series(now - timedelta(days=10), 8, 100.0, 0.5)}
    rows = [
        {
            "ticker": "AAA",
            "timestamp": (now - timedelta(days=2)).isoformat().replace("+00:00", "Z"),
            "direction": "up",
            "expected_return": 0.01,
            "confidence": 0.6,
        }
    ]
    report = build_judge_quality_report_from_data(
        rows=rows,
        prices_by_ticker=prices,
        horizon_days=10,
        window_days=(30,),
        min_samples=2,
        now_utc=now,
    )

    assert report["overall"]["n"] == 0
    assert report["overall"]["sample_status"] == "insufficient"
    assert report["recommendation"]["status"] == "insufficient_sample"

