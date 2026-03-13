from services import brief_generator


def test_build_daily_brief_snapshot_wraps_brief_in_canonical_daily_shape():
    brief = {
        "summary": "Ouverture constructive.",
        "headline": "Brief Marche",
        "freshness": "2026-03-13T10:00:00Z",
        "generated_at": "2026-03-13T10:00:00Z",
        "source": ["brief_generator", "live_data"],
        "sources": ["brief_generator", "live_data"],
        "warnings": [],
        "degraded": False,
        "degraded_reason": None,
        "top_actions": [
            {"ticker": "NVDA", "action": "BUY", "confidence": 0.75, "horizon": "1w"}
        ],
        "main_risks": [
            {"type": "macro_risk", "ticker": "SPY", "confidence": 0.8, "severity": "high"}
        ],
        "generation_metadata": {
            "schedule_mode": "refreshable_script",
            "artifact_key": "brief_daily",
            "artifact_path": "runtime/data/brief_daily.json",
            "refreshed_at": "2026-03-13T10:00:00Z",
            "action_metadata": {
                "actions_available": True,
                "risks_available": True,
            }
        },
    }

    payload = brief_generator.build_daily_brief_snapshot(brief)

    # Canonical shape
    assert payload["data"]["daily"]["summary"] == "Ouverture constructive."
    assert payload["data"]["daily"]["generation_metadata"]["artifact_key"] == "brief_daily"
    assert payload["generation_metadata"]["artifact_path"] == "runtime/data/brief_daily.json"
    assert payload["freshness"] == "2026-03-13T10:00:00Z"

    # DEV-02: action-oriented fields preserved
    assert "top_actions" in payload["data"]["daily"]
    assert "main_risks" in payload["data"]["daily"]
    assert payload["data"]["daily"]["top_actions"][0]["ticker"] == "NVDA"
    assert payload["data"]["daily"]["main_risks"][0]["ticker"] == "SPY"
    assert payload["data"]["daily"]["generation_metadata"]["action_metadata"]["actions_available"] is True


def test_extract_top_actions_returns_high_confidence_forecasts():
    forecasts = [
        {"ticker": "NVDA", "direction": "up", "confidence": 0.8, "horizon": "1w"},
        {"ticker": "TSLA", "direction": "down", "confidence": 0.7, "horizon": "1m"},
        {"ticker": "AAPL", "direction": "up", "confidence": 0.4, "horizon": "1w"},  # Below threshold
    ]

    actions = brief_generator._extract_top_actions(forecasts, limit=5)

    assert len(actions) == 2
    assert actions[0]["ticker"] == "NVDA"
    assert actions[0]["action"] == "BUY"
    assert actions[0]["confidence"] == 0.8
    assert actions[1]["ticker"] == "TSLA"
    assert actions[1]["action"] == "SELL"


def test_extract_main_risks_aggregates_sources():
    forecasts = [{"ticker": "AAPL", "direction": "down", "confidence": 0.6}]
    news = [{"sentiment": "negative"}]
    macro = {"indicators": {"vix": 25, "dxy": 106}}

    risks = brief_generator._extract_main_risks(forecasts, news, macro, limit=5)

    assert len(risks) >= 2
    assert any(r["type"] == "forecast_risk" for r in risks)
    assert any(r["type"] == "macro_risk" and "VIX" in r["description"] for r in risks)
    assert all("confidence" in r for r in risks)
    assert all("severity" in r for r in risks)


def test_generate_daily_brief_enriches_actions_and_risks_from_judge_snapshot(monkeypatch):
    monkeypatch.setattr(
        brief_generator,
        "get_forecasts_from_storage",
        lambda limit=50: {"rows": []},
    )
    monkeypatch.setattr(
        brief_generator,
        "get_news_feed",
        lambda limit=50: {"articles": []},
    )
    monkeypatch.setattr(brief_generator, "get_macro_indicators", lambda: {"indicators": {}})
    monkeypatch.setattr(
        brief_generator,
        "get_market_intelligence_snapshot",
        lambda use_cache=True, persist=False: {
            "insights": {
                "opportunities": [
                    {
                        "ticker": "MSFT",
                        "action": "BUY",
                        "confidence": 0.83,
                        "horizon": "1w",
                        "summary": "BUY MSFT 83% 1w",
                        "reasoning": "MSFT breakout with strong momentum",
                    }
                ],
                "risks": [
                    {
                        "type": "market_risk",
                        "ticker": "CPI",
                        "label": "CPI",
                        "severity": "high",
                        "confidence": 0.72,
                        "description": "Headline inflation surprise risk",
                    }
                ],
            }
        },
    )

    brief = brief_generator.generate_daily_brief()

    assert brief["degraded"] is False
    assert brief["source"] == ["brief_generator", "live_data", "judge_intelligence"]
    assert brief["top_actions"] == [
        {
            "ticker": "MSFT",
            "action": "BUY",
            "confidence": 0.83,
            "horizon": "1w",
            "label": "MSFT",
            "summary": "BUY MSFT 83% 1w",
            "rationale": "MSFT breakout with strong momentum",
            "source": "judge",
        }
    ]
    assert brief["main_risks"] == [
        {
            "type": "MARKET_RISK",
            "ticker": "CPI",
            "label": "CPI",
            "priority": "HIGH",
            "summary": "Headline inflation surprise risk",
            "description": "Headline inflation surprise risk",
            "confidence": 0.72,
            "severity": "high",
            "source": "judge",
        }
    ]
