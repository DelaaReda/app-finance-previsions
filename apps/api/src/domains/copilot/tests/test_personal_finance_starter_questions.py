from domains.copilot.application import copilot_service


def test_scope_tickers_shape_starter_question():
    entry_points = copilot_service._build_copilot_entry_points(
        scope={"tickers": ["AAPL", "MSFT"]},
    )

    ask_entry = next((ep for ep in entry_points if ep.get("id") == "ask_copilot"), None)

    assert ask_entry is not None
    assert ask_entry.get("prefill", {}).get("question") == (
        "Que dois-je surveiller aujourd'hui sur AAPL, MSFT ?"
    )


def test_brief_risk_shapes_default_starter_question():
    entry_points = copilot_service._build_copilot_entry_points(
        scope=None,
        daily_brief={
            "top_risks": [
                {"name": "CPI release", "signal": "watch"},
            ]
        },
    )

    ask_entry = next((ep for ep in entry_points if ep.get("id") == "ask_copilot"), None)

    assert ask_entry is not None
    assert ask_entry.get("prefill", {}).get("question") == (
        "Quel est l'impact de CPI release sur ma journée de trading ?"
    )
