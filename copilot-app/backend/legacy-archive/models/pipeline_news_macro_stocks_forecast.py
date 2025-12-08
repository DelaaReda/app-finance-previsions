# News-Macro-Stocks Forecast Pipeline (real data edition)
# File: /models/pipeline_news_macro_stocks_forecast.py
# Purpose: Build forecasting features from real news, macro snapshots, and price history

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

try:
    from storage.io import load_json  # type: ignore
except Exception:  # pragma: no cover - optional in some deployments
    load_json = None

try:
    from core.market_data import get_price_history, get_fred_series  # type: ignore
except Exception:  # pragma: no cover - keep stubs so pipeline still runs in degraded mode
    def get_price_history(*_args, **_kwargs):  # type: ignore
        return None

    def get_fred_series(*_args, **_kwargs):  # type: ignore
        return pd.DataFrame()


class NewsMacroStocksForecastPipeline:
    """Pipeline that assembles features from real data sources for the hybrid forecaster."""

    def __init__(self) -> None:
        self.logger = self._get_logger()
        self.pipeline_config = self._load_pipeline_config()
        self.data_dir = Path(__file__).resolve().parents[2] / "data"
        self.cache_dir = self.data_dir / "forecast_pipeline"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.price_cache_hours = int(os.getenv("FORECAST_PRICE_CACHE_HOURS", "6"))

    # ------------------------------------------------------------------
    # Configuration / logging helpers
    # ------------------------------------------------------------------
    def _get_logger(self):  # pragma: no cover - trivial wrapper
        import logging

        return logging.getLogger(__name__)

    def _load_pipeline_config(self) -> Dict[str, List[str]]:
        return {
            "forecast_horizon": ["1d", "5d", "22d"],
            "required_macro_indicators": [
                "VIXCLS",
                "CPIAUCSL",
                "UNRATE",
                "DGS10",
                "DGS2",
                "FEDFUNDS",
            ],
        }

    # ------------------------------------------------------------------
    # Public entrypoints
    # ------------------------------------------------------------------
    def run_pipeline(self, tickers: List[str]) -> Dict[str, pd.DataFrame]:
        self.logger.info("Running forecast pipeline on %s", tickers)

        news_data = self.ingest_news_data(tickers)
        macro_data = self.ingest_macro_data()
        stock_data = self.ingest_stock_data(tickers)

        news_impact_scores = self.calculate_news_impact_score(news_data)
        macro_regime_scores = self.calculate_macro_regime_score(macro_data)
        technical_signals = self.generate_technical_signals(stock_data)

        forecasts = self.combine_signals_for_forecast(
            news_impact_scores,
            macro_regime_scores,
            technical_signals,
            stock_data,
        )

        return forecasts

    # ------------------------------------------------------------------
    # News ingestion ----------------------------------------------------
    # ------------------------------------------------------------------
    def ingest_news_data(self, tickers: List[str]) -> Dict[str, pd.DataFrame]:
        df = self._news_articles_dataframe(tickers)
        if df.empty:
            return {ticker: pd.DataFrame() for ticker in tickers}

        grouped = (
            df.groupby(["ticker", pd.Grouper(key="date", freq="D")])
            .agg(
                sentiment_score=("sentiment_value", "mean"),
                news_volume=("article_id", "count"),
                relevance_score=("score", "mean"),
            )
            .reset_index()
        )

        out: Dict[str, pd.DataFrame] = {}
        for ticker in tickers:
            subset = grouped[grouped["ticker"] == ticker].copy()
            if subset.empty:
                out[ticker] = pd.DataFrame()
            else:
                subset.sort_values("date", inplace=True)
                subset["date"] = subset["date"].dt.tz_localize(None)
                out[ticker] = subset
        return out

    def _news_articles_dataframe(self, tickers: List[str]) -> pd.DataFrame:
        payload = self._load_json_payload("news_feed")
        articles = payload.get("articles") or payload.get("data", {}).get("articles", [])
        if not articles:
            return pd.DataFrame()

        rows = []
        universe = set(tickers)
        for idx, article in enumerate(articles):
            published = (
                article.get("published_at")
                or article.get("pubDate")
                or article.get("timestamp")
                or article.get("date")
            )
            ts = pd.to_datetime(published, errors="coerce")
            if pd.isna(ts):
                continue

            tagged = article.get("tickers") or []
            tagged = [t.strip().upper() for t in tagged if isinstance(t, str)]
            if not tagged:
                text = f"{article.get('title', '')} {article.get('summary', article.get('description', ''))}"
                tagged = [t for t in universe if t in text.upper()]
            if not tagged:
                continue

            sentiment_label = (article.get("sentiment") or "neutral").lower()
            if sentiment_label not in ("positive", "negative", "neutral"):
                sentiment_label = "neutral"
            sentiment_value = {"positive": 1.0, "negative": -1.0, "neutral": 0.0}[sentiment_label]
            score = float(article.get("score") or 50.0)
            score_normalized = score / 100.0

            for ticker in tagged:
                rows.append(
                    {
                        "article_id": article.get("id", f"article_{idx}"),
                        "ticker": ticker,
                        "date": ts,
                        "sentiment_value": sentiment_value * score_normalized,
                        "score": score_normalized,
                    }
                )

        return pd.DataFrame(rows)

    # ------------------------------------------------------------------
    # Macro ingestion ---------------------------------------------------
    # ------------------------------------------------------------------
    def ingest_macro_data(self) -> Dict[str, pd.DataFrame]:
        payload = self._load_json_payload("macro_series")
        series = payload.get("series", {})
        data: Dict[str, pd.DataFrame] = {}

        if series:
            for indicator, info in series.items():
                obs = info.get("observations") or []
                if not obs:
                    continue
                df = pd.DataFrame(obs)
                df["date"] = pd.to_datetime(df["date"], errors="coerce")
                df["value"] = pd.to_numeric(df["value"], errors="coerce")
                df.dropna(subset=["date", "value"], inplace=True)
                df.sort_values("date", inplace=True)
                df["normalized_value"] = self._normalize_series(df["value"])
                data[indicator] = df[["date", "value", "normalized_value"]]
        else:
            for indicator in self.pipeline_config["required_macro_indicators"]:
                df = get_fred_series(indicator)
                if df is None or df.empty:
                    continue
                tmp = df.reset_index().rename(columns={df.columns[0]: "value", "index": "date"})
                tmp["date"] = pd.to_datetime(tmp["date"], errors="coerce")
                tmp.dropna(subset=["date", "value"], inplace=True)
                tmp["normalized_value"] = self._normalize_series(tmp["value"])
                data[indicator] = tmp[["date", "value", "normalized_value"]]

        return data

    # ------------------------------------------------------------------
    # Stock ingestion ---------------------------------------------------
    # ------------------------------------------------------------------
    def ingest_stock_data(self, tickers: List[str]) -> Dict[str, pd.DataFrame]:
        out: Dict[str, pd.DataFrame] = {}
        for ticker in tickers:
            df = self._load_stock_with_technicals(ticker)
            out[ticker] = df
        return out

    def _load_stock_with_technicals(self, ticker: str) -> pd.DataFrame:
        cache_path = self.cache_dir / "prices" / f"{ticker.upper()}.csv"
        cache_path.parent.mkdir(parents=True, exist_ok=True)

        if self._is_cache_fresh(cache_path):
            try:
                df = pd.read_csv(cache_path, parse_dates=["date"])  # type: ignore
                return df
            except Exception:
                pass

        start_date = (datetime.utcnow() - timedelta(days=400)).strftime("%Y-%m-%d")
        raw = get_price_history(ticker, start=start_date, interval="1d")
        if raw is None or raw.empty:
            return pd.DataFrame()

        df = raw.reset_index().rename(columns=str.lower)
        if "adj close" in df.columns and "close" not in df.columns:
            df.rename(columns={"adj close": "close"}, inplace=True)
        df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.tz_localize(None)
        df = df.dropna(subset=["date", "close"]).copy()

        df = self._calculate_technical_indicators(df)

        try:
            df.to_csv(cache_path, index=False)
        except Exception:
            pass
        return df

    # ------------------------------------------------------------------
    # Feature calculations ---------------------------------------------
    # ------------------------------------------------------------------
    def calculate_news_impact_score(self, news_data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        impact: Dict[str, pd.DataFrame] = {}
        for ticker, df in news_data.items():
            if df.empty:
                impact[ticker] = pd.DataFrame()
                continue
            tmp = df.copy()
            tmp.sort_values("date", inplace=True)
            tmp["news_sentiment_rolling"] = tmp["sentiment_score"].rolling(window=5, min_periods=1).mean()
            tmp["news_volume_zscore"] = (tmp["news_volume"] - tmp["news_volume"].mean()) / (tmp["news_volume"].std() or 1.0)
            tmp["news_impact_score"] = tmp["sentiment_score"].fillna(0) * 0.6 + tmp["relevance_score"].fillna(0) * 0.4
            impact[ticker] = tmp[[
                "date",
                "news_impact_score",
                "sentiment_score",
                "relevance_score",
                "news_volume",
                "news_volume_zscore",
            ]]
        return impact

    def calculate_macro_regime_score(self, macro_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        if not macro_data:
            return pd.DataFrame({"date": pd.to_datetime([]), "macro_regime_score": []})

        merged = None
        for name, df in macro_data.items():
            if df.empty:
                continue
            cols = df[["date", "normalized_value"]].rename(columns={"normalized_value": name})
            merged = cols if merged is None else merged.merge(cols, on="date", how="outer")

        if merged is None:
            return pd.DataFrame({"date": pd.to_datetime([]), "macro_regime_score": []})

        merged.sort_values("date", inplace=True)
        merged.fillna(method="ffill", inplace=True)

        weights = {
            "VIXCLS": 0.25,
            "CPIAUCSL": 0.2,
            "UNRATE": 0.15,
            "DGS10": 0.15,
            "DGS2": 0.1,
            "FEDFUNDS": 0.15,
        }
        score = 0
        weight_sum = 0
        for col, weight in weights.items():
            if col in merged:
                score += merged[col] * weight
                weight_sum += weight
        if weight_sum == 0:
            merged["macro_regime_score"] = 0
        else:
            merged["macro_regime_score"] = score / weight_sum

        return merged[["date", "macro_regime_score"]]

    def generate_technical_signals(self, stock_data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        signals: Dict[str, pd.DataFrame] = {}
        for ticker, df in stock_data.items():
            if df.empty:
                signals[ticker] = pd.DataFrame()
                continue
            tmp = df[["date"]].copy()
            tmp["rsi_oversold"] = (df["rsi"] < 30).astype(int)
            tmp["rsi_overbought"] = (df["rsi"] > 70).astype(int)
            tmp["ma_bullish_cross"] = ((df["sma_20"] > df["sma_50"]) & (df["sma_20"].shift(1) <= df["sma_50"].shift(1))).astype(int)
            tmp["ma_bearish_cross"] = ((df["sma_20"] < df["sma_50"]) & (df["sma_20"].shift(1) >= df["sma_50"].shift(1))).astype(int)
            tmp["bb_bullish_breakout"] = (df["close"] > df["bb_upper"]).astype(int)
            tmp["bb_bearish_breakout"] = (df["close"] < df["bb_lower"]).astype(int)
            tmp["macd_bullish_cross"] = ((df["macd"] > df["macd_signal"]) & (df["macd"].shift(1) <= df["macd_signal"].shift(1))).astype(int)
            tmp["macd_bearish_cross"] = ((df["macd"] < df["macd_signal"]) & (df["macd"].shift(1) >= df["macd_signal"].shift(1))).astype(int)
            signals[ticker] = tmp
        return signals

    def combine_signals_for_forecast(
        self,
        news_impact: Dict[str, pd.DataFrame],
        macro_regime: pd.DataFrame,
        technical_signals: Dict[str, pd.DataFrame],
        stock_data: Dict[str, pd.DataFrame],
    ) -> Dict[str, pd.DataFrame]:
        forecasts: Dict[str, pd.DataFrame] = {}
        macro_regime = macro_regime.copy()
        macro_regime.sort_values("date", inplace=True)

        for ticker, price_df in stock_data.items():
            if price_df.empty:
                forecasts[ticker] = pd.DataFrame()
                continue

            df = price_df.copy()
            df = df.merge(macro_regime, on="date", how="left")
            df["macro_regime_score"] = df["macro_regime_score"].fillna(method="ffill").fillna(0)

            news_df = news_impact.get(ticker)
            if news_df is not None and not news_df.empty:
                df = df.merge(news_df, on="date", how="left")
                df["news_impact_score"] = df["news_impact_score"].fillna(0)
                df["sentiment_score"] = df["sentiment_score"].fillna(0)
                df["news_volume"] = df["news_volume"].fillna(0)
                df["news_volume_zscore"] = df["news_volume_zscore"].fillna(0)
            else:
                df["news_impact_score"] = 0
                df["sentiment_score"] = 0
                df["news_volume"] = 0
                df["news_volume_zscore"] = 0

            tech_df = technical_signals.get(ticker)
            if tech_df is not None and not tech_df.empty:
                df = df.merge(tech_df, on="date", how="left")
            else:
                for col in [
                    "rsi_oversold",
                    "rsi_overbought",
                    "ma_bullish_cross",
                    "ma_bearish_cross",
                    "bb_bullish_breakout",
                    "bb_bearish_breakout",
                    "macd_bullish_cross",
                    "macd_bearish_cross",
                ]:
                    df[col] = 0

            df.fillna(0, inplace=True)
            df["composite_signal"] = (
                df["ma_bullish_cross"] * 0.2
                - df["ma_bearish_cross"] * 0.2
                + df["rsi_oversold"] * 0.15
                - df["rsi_overbought"] * 0.15
                + df["macd_bullish_cross"] * 0.15
                - df["macd_bearish_cross"] * 0.15
                + df["news_impact_score"] * 0.2
                + df["macro_regime_score"] * 0.1
            )
            df["forecast_direction"] = np.where(
                df["composite_signal"] > 0.1,
                "up",
                np.where(df["composite_signal"] < -0.1, "down", "neutral"),
            )
            df["confidence"] = np.clip(np.abs(df["composite_signal"]), 0, 1)
            df["expected_return_1d"] = df["composite_signal"] * 0.02
            df["expected_return_5d"] = df["composite_signal"] * 0.05
            df["expected_return_22d"] = df["composite_signal"] * 0.10

            forecasts[ticker] = df

        return forecasts

    # ------------------------------------------------------------------
    # Utilities --------------------------------------------------------
    # ------------------------------------------------------------------
    def _load_json_payload(self, key: str) -> Dict[str, Any]:
        if load_json:
            try:
                data = load_json(key.rstrip(".json"))  # type: ignore[arg-type]
                if data:
                    return data
            except Exception:
                pass
        file_path = self.data_dir / (key if key.endswith(".json") else f"{key}.json")
        if file_path.exists():
            try:
                return json.loads(file_path.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def _normalize_series(self, series: pd.Series) -> pd.Series:
        rolling = series.rolling(window=90, min_periods=10)
        mean = rolling.mean()
        std = rolling.std().replace(0, np.nan)
        normalized = (series - mean) / std
        return normalized.fillna(0)

    def _calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        out["sma_20"] = out["close"].rolling(window=20).mean()
        out["sma_50"] = out["close"].rolling(window=50).mean()

        delta = out["close"].diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = -delta.where(delta < 0, 0).rolling(window=14).mean()
        rs = gain / (loss.replace(0, np.nan))
        out["rsi"] = 100 - (100 / (1 + rs))

        exp1 = out["close"].ewm(span=12, adjust=False).mean()
        exp2 = out["close"].ewm(span=26, adjust=False).mean()
        out["macd"] = exp1 - exp2
        out["macd_signal"] = out["macd"].ewm(span=9, adjust=False).mean()

        out["bb_middle"] = out["close"].rolling(window=20).mean()
        bb_std = out["close"].rolling(window=20).std()
        out["bb_upper"] = out["bb_middle"] + 2 * bb_std
        out["bb_lower"] = out["bb_middle"] - 2 * bb_std

        out["atr"] = (out["high"] - out["low"]).rolling(window=14).mean()
        return out

    def _is_cache_fresh(self, path: Path) -> bool:
        if not path.exists():
            return False
        age = datetime.utcnow() - datetime.utcfromtimestamp(path.stat().st_mtime)
        return age <= timedelta(hours=self.price_cache_hours)
