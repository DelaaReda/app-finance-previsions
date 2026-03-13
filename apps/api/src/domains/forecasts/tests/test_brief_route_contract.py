from domains.forecasts.api import brief as brief_api


def test_brief_daily_contract_prefers_canonical_fields_and_keeps_aliases_synced(monkeypatch):
    snapshots = {
        "brief_daily": {
            "data": {
                "daily": {
                    "title": "Brief quotidien",
                    "summary": "mot " * 250,
                    "market_regime": "RISK_ON",
                    "market_sentiment": "MIXED",
                    "top_opportunities": [{"ticker": "NVDA", "thesis": "AI demand"}],
                    "top_signals": [{"ticker": "LEGACY", "thesis": "should_not_win"}],
                    "picks": [{"ticker": "OLD", "thesis": "should_not_win"}],
                    "top_risks": [{"ticker": "CPI", "thesis": "macro print"}],
                    "suppressed_risks": [
                        {
                            "ticker": "NVDA",
                            "suppression_reason": "fatigue_window_duplicate",
                            "duplicate_count": 2,
                        }
                    ],
                    "alerting_metadata": {
                        "suppression_window_minutes": 15,
                        "fatigue_threshold": 2,
                        "urgent_bypass_enabled": True,
                    },
                    "macro_signals": [
                        {"topic": "Fed", "state": "neutral", "score": 0.1, "confidence": 0.8},
                    ],
                    "sector_rotation": {
                        "top": [{"sector": "or", "momentum": 0.7, "direction": "up"}],
                        "bottom": [{"sector": "energie", "momentum": -0.4, "direction": "down"}],
                    },
                    "sources": ["tests_canonical"],
                    "source": ["legacy_fixture"],
                    "generated_at": "2026-03-01T10:00:00Z",
                    "freshness": "fresh",
                    "generation_metadata": {
                        "schedule_mode": "refreshable_script",
                        "target_local_time": "06:30",
                        "target_timezone": "America/New_York",
                        "artifact_key": "brief_daily",
                        "artifact_path": "runtime/data/brief_daily.json",
                        "refreshed_by": "scripts/generate_brief.py",
                        "refreshed_at": "2026-03-01T10:00:00Z",
                    },
                }
            }
        },
        "brief_weekly": None,
    }

    monkeypatch.setattr(brief_api.storage_io, "load_json", lambda key: snapshots.get(key))

    payload = brief_api.get_daily_brief()
    assert payload.get("ok") is True

    data = payload.get("data") or {}
    assert isinstance(data.get("macro_signals"), list)
    assert isinstance(data.get("sector_rotation"), dict)
    assert isinstance(data["sector_rotation"].get("top"), list)
    assert isinstance(data["sector_rotation"].get("bottom"), list)
    assert data["market_regime"] == "RISK_ON"
    assert data["market_sentiment"] == "RISK_ON"
    assert data["regime"] == "RISK_ON"
    assert data["top_opportunities"] == [{"ticker": "NVDA", "thesis": "AI demand"}]
    assert data["top_signals"] == data["top_opportunities"]
    assert data["top_risks"] == [{"ticker": "CPI", "thesis": "macro print"}]
    assert data["suppressed_risks"] == [
        {
            "ticker": "NVDA",
            "suppression_reason": "fatigue_window_duplicate",
            "duplicate_count": 2,
        }
    ]
    assert data["alerting_metadata"] == {
        "suppression_window_minutes": 15,
        "fatigue_threshold": 2,
        "urgent_bypass_enabled": True,
    }
    assert data["sources"] == ["tests_canonical"]
    assert data["source"] == ["tests_canonical"]
    assert data["freshness"] == "fresh"
    assert data["generation_metadata"] == {
        "schedule_mode": "refreshable_script",
        "target_local_time": "06:30",
        "target_timezone": "America/New_York",
        "artifact_key": "brief_daily",
        "artifact_path": "runtime/data/brief_daily.json",
        "refreshed_by": "scripts/generate_brief.py",
        "refreshed_at": "2026-03-01T10:00:00Z",
        "freshness": "fresh",
    }
    assert data["degraded"] is False
    assert data["degraded_reason"] is None

    summary_words = len(str(data.get("summary", "")).split())
    assert summary_words <= 200


def test_brief_daily_contract_marks_weekly_fallback_as_degraded(monkeypatch):
    snapshots = {
        "brief_daily": None,
        "brief_weekly": {
            "data": {
                "weekly": {
                    "summary": "Weekly fallback summary",
                    "market_sentiment": "DEFENSIVE",
                    "picks": [{"ticker": "XLV", "thesis": "defensive rotation"}],
                    "top_risks": [{"ticker": "RATES", "thesis": "yields rising"}],
                    "sources": ["weekly_fixture"],
                    "generated_at": "2026-03-02T09:00:00Z",
                    "freshness": "2026-03-02T09:00:00Z",
                }
            }
        },
    }

    monkeypatch.setattr(brief_api.storage_io, "load_json", lambda key: snapshots.get(key))

    data = (brief_api.get_daily_brief().get("data") or {})
    assert data["summary"] == "Weekly fallback summary"
    assert data["market_regime"] == "DEFENSIVE"
    assert data["market_sentiment"] == "DEFENSIVE"
    assert data["top_opportunities"] == [{"ticker": "XLV", "thesis": "defensive rotation"}]
    assert data["top_signals"] == data["top_opportunities"]
    assert data["sources"] == ["weekly_fixture"]
    assert data["generation_metadata"] == {
        "artifact_key": "brief_weekly",
        "artifact_path": "runtime/data/brief_weekly.json",
        "refreshed_at": "2026-03-02T09:00:00Z",
        "freshness": "2026-03-02T09:00:00Z",
        "schedule_mode": "snapshot",
    }
    assert data["degraded"] is True
    assert data["degraded_reason"] == "daily_snapshot_missing_using_weekly"


def test_brief_daily_contract_marks_empty_fallback_as_degraded(monkeypatch):
    monkeypatch.setattr(brief_api.storage_io, "load_json", lambda _key: None)

    data = (brief_api.get_daily_brief().get("data") or {})
    assert data["summary"] == "No daily brief available yet."
    assert data["market_regime"] == "UNKNOWN"
    assert data["top_opportunities"] == []
    assert data["top_risks"] == []
    assert data["suppressed_risks"] == []
    assert data["alerting_metadata"] == {}
    assert data["sources"] == ["fallback_empty"]
    assert data["source"] == ["fallback_empty"]
    assert data["freshness"] == data["generated_at"]
    assert data["generation_metadata"] == {
        "artifact_key": "fallback_empty",
        "artifact_path": "runtime/data/fallback_empty.json",
        "refreshed_at": data["generated_at"],
        "freshness": data["generated_at"],
        "schedule_mode": "fallback",
    }
    assert data["degraded"] is True
    assert data["degraded_reason"] == "daily_snapshot_missing"
