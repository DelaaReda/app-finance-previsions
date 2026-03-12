from __future__ import annotations

import sys
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[3]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from domains.judge.application.judge_pipeline import load_profile


def test_load_profile_uses_canonical_runtime_data_path(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    profile = load_profile("reda_personal_investing")

    assert profile.name == "reda_personal_investing"
    assert profile.horizon == "1m"
    assert profile.focus == "balanced"
    assert "SPY" in profile.tickers
    assert "AAPL" in profile.tickers
    assert "investisseur particulier prudent" in profile.prompt_template


def test_load_profile_supports_supply_chain_commodity_shock_profile(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    profile = load_profile("supply_chain_commodity_shock")

    assert profile.name == "supply_chain_commodity_shock"
    assert profile.horizon == "1m"
    assert profile.focus == "macro"
    assert "XLE" in profile.tickers
    assert "DBA" in profile.tickers
    assert "shock propagation" in profile.prompt_template.lower()


def test_load_profile_supports_rebalancing_optimizer_lite_profile(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    profile = load_profile("rebalancing_optimizer_lite")

    assert profile.name == "rebalancing_optimizer_lite"
    assert profile.horizon == "1m"
    assert profile.focus == "balanced"
    assert "SPY" in profile.tickers
    assert "IEF" in profile.tickers
    assert "portfolio rebalance" in profile.prompt_template.lower()
    assert "portfolio context" in profile.prompt_template.lower()
