from unittest import mock

from platform.legacy.jobs import forecasts_simple as fs


def test_generate_forecast_uses_previous_close_when_history_unavailable():
    """No history: confidence is derived from quote previous_close, not mock change_percent."""

    with mock.patch.object(
        fs,
        "_fetch_real_change_pct",
        return_value=0.0,
    ):
        forecast = fs.generate_forecast(
            "AAPL",
            {
                "price": 110.0,
                "previous_close": 100.0,
                "change_percent": 0.01,
            },
        )

    assert forecast["direction"] == "up"
    assert forecast["confidence"] >= 0.6


def test_generate_forecast_preserves_down_signal_with_quote_fallback():
    with mock.patch.object(
        fs,
        "_fetch_real_change_pct",
        return_value=0.0,
    ):
        forecast = fs.generate_forecast(
            "TSLA",
            {
                "price": 90.0,
                "previous_close": 100.0,
                "change_percent": 12.0,
            },
        )

    assert forecast["direction"] == "down"
    assert forecast["confidence"] <= 1.0
    assert forecast["confidence"] >= 0.2
