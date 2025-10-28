import pandas as pd
from src.dash_app.logic.deep_dive_logic import filter_prices


def test_filter_prices_basic():
    d = pd.date_range("2025-01-01", periods=4, freq="D")
    a = pd.DataFrame({"date": d, "close": [1.0, 1.2, 1.1, 1.3]})
    b = pd.DataFrame({"date": d, "close": [3.0, 2.8, 2.9, 3.1]})
    frames = {"AAA": a, "BBB": b}
    out = filter_prices(frames, ["AAA", "BBB"], "2025-01-02", None, "close")
    assert set(out["ticker"]) == {"AAA", "BBB"}
    # filtered start
    assert out["date"].min() >= pd.to_datetime("2025-01-02")

