# phase3_macro.py
# -*- coding: utf-8 -*-
"""
Phase 3 — Macro & Nowcasting pour actions US/CA

Gratuit et robuste:
- FRED: téléchargement CSV public (sans clé) via fredgraph.csv
- yfinance: proxies marchés (USD, Or, WTI, Copper, 10Y)

Fonctions clés:
- fetch_fred_series(), get_us_macro_bundle()
- resample_align(), macro_nowcast()
- build_macro_factors(), rolling_betas(), factor_model()
- macro_regime(), scenario_impact()

Dépendances:
    pip install pandas numpy yfinance
    (optionnel) pip install statsmodels

Auteur: toi + IA (2025) — Licence MIT (à adapter)
"""
from __future__ import annotations

import io
import math
import time
import urllib.request
import warnings
import logging
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple, Any
import sys
sys.modules[__name__] = sys.modules[__name__]

import numpy as np
import pandas as pd
import yfinance as yf

logger = logging.getLogger("macroapp")
logger.propagate = False  # <<< Prevent propagation to root logger

def _warn_and_log(msg: str):
    # Émet un vrai UserWarning (pour pytest.warns) + log WARNING
    warnings.warn(msg, UserWarning)
    logger.warning(msg)

def _isfinite(x):
    return isinstance(x, (int, float)) and math.isfinite(x)

def _clean_non_finite(d, path="root", missing=None):
    """
    Remplace NaN/Inf par None et enregistre le chemin.
    Ne droppe rien silencieusement.
    """
    if missing is None:
        missing = []
    if d is None:
        return None, missing
    if isinstance(d, (int, float)):
        if not _isfinite(d):
            missing.append(f"{path}:non-finite")
            return None, missing
        return d, missing
    if isinstance(d, str):
        if not d.strip():
            missing.append(f"{path}:empty-str")
            return None, missing
        return d, missing
    if isinstance(d, dict):
        out = {}
        for k, v in d.items():
            cv, missing = _clean_non_finite(v, f"{path}.{k}", missing)
            out[k] = cv
        return out, missing
    if isinstance(d, (list, tuple)):
        out = []
        for i, v in enumerate(d):
            cv, missing = _clean_non_finite(v, f"{path}[{i}]", missing)
            out.append(cv)
        return out, missing
    return d, missing

# statsmodels (optionnel)
try:
    import statsmodels.api as sm  # type: ignore
    HAS_SM = True
except Exception:
    HAS_SM = False

TRADING_DAYS = 252

# ----------------------------- Dataclasses ---------------------------------- #

@dataclass
class MacroBundle:
    """Conteneur de séries macro alignées (mensuelles par défaut)."""
    data: pd.DataFrame
    meta: Dict[str, Any]

    def to_frame(self) -> pd.DataFrame:
        return self.data

    def to_dict(self) -> Dict[str, Any]:
        m = dict(self.meta)
        m["columns"] = list(self.data.columns)
        m["rows"] = int(len(self.data))
        return m


@dataclass
class NowcastView:
    """
    Indices synthétiques standardisés (z-scores): Growth, Inflation, Policy, USD, Commodities.
    """
    scores: Dict[str, float]
    components: Dict[str, float]

    def to_dict(self) -> Dict[str, Any]:
        # Round scores and components to 4 decimal places for readability
        scores = {k: round(float(v), 4) if v is not None and np.isfinite(v) else v for k, v in self.scores.items()}
        components = {k: round(float(v), 4) if v is not None and np.isfinite(v) else v for k, v in self.components.items()}
        return {"scores": scores, "components": components}


@dataclass
class ExposureReport:
    """Expositions macro d’un titre (rolling β, OLS multi-facteurs)."""
    rolling_betas: pd.DataFrame
    ols_loadings: Dict[str, float]
    r2: float
    stability: Dict[str, float]  # ex: std(β) / |mean(β)|

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ols_loadings": {k: float(v) for k, v in self.ols_loadings.items()},
            "r2": float(self.r2),
            "stability": {k: float(v) for k, v in self.stability.items()},
            "rolling_beta_cols": list(self.rolling_betas.columns),
        }


@dataclass
class MacroRegimeView:
    """Classification de régime macro agrégée."""
    label: str
    growth_z: float
    inflation_z: float
    policy_z: float
    extra: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["growth_z"] = float(self.growth_z)
        d["inflation_z"] = float(self.inflation_z)
        d["policy_z"] = float(self.policy_z)
        return d


@dataclass
class ScenarioImpact:
    """Projection d’impact (%) sur le titre pour des chocs macro instantanés."""
    deltas: Dict[str, float]   # choc (ex: {"USD": +0.05, "10Y": +0.005})
    expected_return_pct: float
    detail: Dict[str, float]   # contribution par facteur (%)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deltas": {k: float(v) for k, v in self.deltas.items()},
            "expected_return_pct": float(self.expected_return_pct),
            "detail": {k: float(v) for k, v in self.detail.items()},
        }

# ---------------------------- Utils & Fetchers ------------------------------- #

def _fred_csv(series_id: str, start: Optional[str] = None) -> pd.Series:
    """
    Télécharge une série FRED via CSV public (fredgraph) avec traitements robustes.
    - UA explicite
    - Variantes d'entêtes (DATE/observation_date)
    - Colonne valeur alternative (VALUE/value ou 2e colonne)
    - Nettoyage '.' → NaN
    """
    # Try official JSON API first if FRED_API_KEY is configured
    import os
    api_key = os.getenv("FRED_API_KEY", "").strip()
    if not api_key:
        # Fallback to secrets_local.get_key (centralized local secrets)
        _get_key = None
        try:
            from src.secrets_local import get_key as _get_key  # type: ignore
        except Exception:
            try:
                from secrets_local import get_key as _get_key  # type: ignore
            except Exception:
                _get_key = None
        if _get_key:
            api_key = (_get_key("FRED_API_KEY") or "").strip()
    api_key = api_key or None
    if api_key:
        import requests
        params = {
            "series_id": series_id,
            "api_key": api_key,
            "file_type": "json",
        }
        if start:
            params["observation_start"] = start
        r = None
        try:
            r = requests.get(
                "https://api.stlouisfed.org/fred/series/observations",
                params=params,
                headers={"User-Agent": "AF/1.0 (+macro_phase3)"},
                timeout=20,
            )
        except Exception as e:
            # Key is present: treat network failure as fatal to surface the issue
            raise RuntimeError(f"FRED API request failed for {series_id}: {type(e).__name__}: {e}") from e

        # If HTTP error, inspect body for a benign "series does not exist" case
        if r.status_code != 200:
            body = (r.text or "").strip()
            if "series does not exist" in body.lower():
                logger.warning(f"fred_series_missing {series_id} (FRED 400)")
                return pd.Series(dtype=float)
            # Otherwise, consider it fatal (likely invalid key or quota)
            raise RuntimeError(f"FRED API returned HTTP {r.status_code} for {series_id}: {body[:200]}")

        # Parse JSON
        try:
            js = r.json()
        except Exception as e:
            raise RuntimeError(f"FRED API invalid JSON for {series_id}: {e}") from e

        # Known error format from FRED
        if isinstance(js, dict) and ("error_code" in js or "error_message" in js):
            code = js.get("error_code", "?")
            msg = js.get("error_message", "")
            if isinstance(msg, str) and "series does not exist" in msg.lower():
                logger.warning(f"fred_series_missing {series_id} (FRED error {code})")
                return pd.Series(dtype=float)
            # Invalid API key or other auth issues → fatal
            raise RuntimeError(f"FRED API error for {series_id}: {code} {msg}")

        obs = js.get("observations", []) if isinstance(js, dict) else []
        if not obs:
            # No points for this specific series — treat as missing (not a key failure)
            logger.warning(f"fred_series_empty_json {series_id}")
            return pd.Series(dtype=float)

        dates = pd.to_datetime([o.get("date") for o in obs], errors="coerce")
        vals = pd.to_numeric([o.get("value") for o in obs], errors="coerce")
        out = pd.Series(vals, index=dates, name=series_id).sort_index().dropna()
        if out.empty:
            logger.warning(f"fred_series_all_nan {series_id}")
            return pd.Series(dtype=float)
        logger.info(
            "fred_ok_json %s rows=%d min=%s max=%s",
            series_id, len(out), out.index.min().date(), out.index.max().date()
        )
        return out

    base = "https://fred.stlouisfed.org/graph/fredgraph.csv"
    url = f"{base}?id={series_id}"
    if start:
        url += f"&startdate={start}"

    txt = None
    # 1) Try requests with User-Agent (plus fiable derrière certains proxies)
    try:
        import requests
        r = requests.get(url, headers={"User-Agent": "AF/1.0 (+macro_phase3)"}, timeout=20)
        if r.status_code == 200 and r.text and not r.text.lstrip().startswith("<"):
            txt = r.text
    except Exception:
        txt = None

    # 2) Fallback urllib
    if txt is None:
        try:
            with urllib.request.urlopen(url, timeout=20) as resp:
                raw = resp.read()
            txt = raw.decode("utf-8", errors="ignore")
        except Exception:
            txt = None

    if not txt:
        logger.warning(f"FRED fetch failed {series_id}: empty response")
        return pd.Series(dtype=float)

    try:
        # Some responses might include stray BOM or leading whitespace
        txt = txt.lstrip("\ufeff")
        df = pd.read_csv(io.StringIO(txt))
    except Exception:
        logger.warning(f"FRED parse failed {series_id}: invalid CSV")
        return pd.Series(dtype=float)

    # Identify date column
    date_col = None
    for cand in ("observation_date", "DATE", "date"):
        if cand in df.columns:
            date_col = cand
            break
    if date_col is None:
        logger.warning(f"FRED {series_id}: missing date column")
        return pd.Series(dtype=float)

    # Identify value column
    val_col = None
    if series_id in df.columns:
        val_col = series_id
    elif "VALUE" in df.columns:
        val_col = "VALUE"
    elif "value" in df.columns:
        val_col = "value"
    else:
        # choose the first non-date column if exactly 2 columns
        non_date = [c for c in df.columns if c != date_col]
        if len(non_date) == 1:
            val_col = non_date[0]

    if val_col is None:
        logger.warning(f"FRED {series_id}: missing value column")
        return pd.Series(dtype=float)

    try:
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        vals = pd.to_numeric(df[val_col].replace(".", np.nan), errors="coerce")
        out = pd.Series(vals.values, index=df[date_col], name=series_id).sort_index()
        out = out.dropna()
        # Log basic stats for diagnostics
        if not out.empty:
            logger.info(
                "fred_ok %s rows=%d min=%s max=%s",
                series_id, len(out),
                out.index.min().date() if hasattr(out.index.min(), 'date') else str(out.index.min()),
                out.index.max().date() if hasattr(out.index.max(), 'date') else str(out.index.max()),
            )
        else:
            logger.warning(f"fred_empty {series_id}")
        return out
    except Exception as e:
        logger.warning(f"FRED {series_id}: error building series: {e}")
        return pd.Series(dtype=float)


def fetch_fred_series(series: List[str], start: Optional[str] = None, sleep: float = 0.15) -> pd.DataFrame:
    """Batch FRED (tolérant aux échecs) avec logs de diagnostic par série."""
    data = {}
    for sid in series:
        s = _fred_csv(sid, start=start)
        if not s.empty:
            data[sid] = s
        else:
            logger.warning(f"fred_series_empty {sid}")
        # small politeness delay
        time.sleep(sleep)
    if not data:
        return pd.DataFrame()
    return pd.DataFrame(data)


def fetch_market_proxies(period: str = "10y") -> pd.DataFrame:
    """
    Proxies marchés via yfinance (journaliers):
      - DXY: "DX-Y.NYB" (USD Index)
      - Gold: "GC=F"
      - WTI: "CL=F"
      - Copper: "HG=F"
      - US10Y: "^TNX" (rendement 10Y *100, donc /100 pour décimal)
    """
    tickers = ["DX-Y.NYB", "GC=F", "CL=F", "HG=F", "^TNX"]
    frames = []
    for t in tickers:
        try:
            h = yf.Ticker(t).history(period=period, auto_adjust=True)
            if getattr(h.index, "tz", None) is not None:
                h.index = h.index.tz_localize(None)
            if not h.empty:
                col = "Close"
                if t == "^TNX":
                    # ^TNX = yield * 100
                    frames.append(h[[col]].rename(columns={col: "US10Y"}).assign(US10Y=lambda x: x["US10Y"] / 100.0))
                else:
                    frames.append(h[[col]].rename(columns={col: t}))
        except Exception:
            pass
        time.sleep(0.1)
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, axis=1).dropna(how="all")
    return df


def resample_align(df: pd.DataFrame, freq: str = "ME", method: str = "last") -> pd.DataFrame:
    """
    Standardise la fréquence (mensuelle par défaut).
    method: 'last' (par défaut), 'mean'
    """
    if df.empty:
        return df
    if method == "mean":
        out = df.resample(freq).mean()
    else:
        out = df.resample(freq).last()
    # supprime colonnes full-NaN
    return out.dropna(how="all")


def pct_chg(df: pd.DataFrame, periods: int = 1) -> pd.DataFrame:
    return df.pct_change(periods=periods, fill_method=None)


def yoy(df: pd.DataFrame) -> pd.DataFrame:
    """Croissance annuelle (YoY) pour données mensuelles/quarterly."""
    return df.pct_change(12, fill_method=None)


def _safe_pct_yoy(series):
    """Safe percentage change calculation with proper error handling."""
    if series is None or series.empty:
        return None
    try:
        v = series.pct_change(12).iloc[-1]
        return None if (v is None or not np.isfinite(v)) else float(v)
    except Exception:
        return None


def _safe_delta(series):
    """Safe delta calculation with proper error handling."""
    if series is None or series.empty:
        return None
    try:
        # Calculate deviation from rolling mean
        rolling_mean = series.rolling(24, min_periods=12).mean()
        if rolling_mean.empty or rolling_mean.iloc[-1] is None:
            return None
        v = series.iloc[-1] - rolling_mean.iloc[-1]
        return None if not np.isfinite(v) else float(v)
    except Exception:
        return None


def zscore_df(df: pd.DataFrame, winsor: float = 3.0) -> pd.DataFrame:
    """Z-score par colonne, winsorisé pour robustesse."""
    x = df.copy()
    mu = x.rolling(24, min_periods=12).mean()
    sd = x.rolling(24, min_periods=12).std()
    z = (x - mu) / sd.replace(0, np.nan)
    z = z.clip(lower=-winsor, upper=winsor)
    return z

# ----------------------------- Macro bundle US ------------------------------- #

def get_us_macro_bundle(start: str = "2000-01-01",
                        monthly: bool = True) -> MacroBundle:
    """
    Récupère un panier de séries macro US 'core' :
      - Growth: INDPRO, PAYEMS, RETAIL SALES (RSAFS), ISM MANUFACTURING PMI (NAPM)
      - Inflation: CPIAUCSL, CORE CPI (CPILFESL), 5y5y (T5YIFR) proxy: T10YIE (breakeven 10Y)
      - Policy: Fed Funds Rate (FEDFUNDS), 10Y (DGS10), 2Y (DGS2)
      - USD: DTWEXBGS (Dollar broad)
      - Credit/Stress: NFCI
    Et proxies marchés (Gold, DXY, WTI, Copper, US10Y).
    """
    fred_ids = [
        # Growth
        "INDPRO", "PAYEMS", "RSAFS", "NAPM",
        # Inflation
        "CPIAUCSL", "CPILFESL", "T10YIE",
        # Policy & rates
        "FEDFUNDS", "DGS10", "DGS2",
        # USD broad
        "DTWEXBGS",
        # Stress
        "NFCI"
    ]
    fred = fetch_fred_series(fred_ids, start=start)
    # markets daily
    mkt = fetch_market_proxies(period="max")
    # resample
    if monthly:
        fred_m = resample_align(fred, "ME", "last")
        mkt_m = resample_align(mkt, "ME", "last")
    else:
        fred_m = resample_align(fred, "W", "last")
        mkt_m = resample_align(mkt, "W", "last")

    # Handle concatenation with empty DataFrames
    if fred_m.empty:
        data = mkt_m
    elif mkt_m.empty:
        data = fred_m
    else:
        data = pd.concat([fred_m, mkt_m], axis=1)
    data = data.dropna(how="all")
    meta = {"country": "US", "freq": "M" if monthly else "W", "source": "FRED+yfinance"}
    return MacroBundle(data=data, meta=meta)

# ------------------------------- Nowcasting ---------------------------------- #

def macro_nowcast(bundle: MacroBundle) -> NowcastView:
    """
    Construit des scores synthétiques à partir de YoY (growth, inflation)
    et niveaux / spreads (policy), ainsi que proxies (USD, commodities).
    Méthode:
      - Growth: z-score moyenne de {INDPRO_yoy, PAYEMS_yoy, RSAFS_yoy, NAPM (demean)}
      - Inflation: z-score moyenne de {CPIAUCSL_yoy, CPILFESL_yoy, T10YIE (demean)}
      - Policy: z-score moyenne de {FEDFUNDS, (DGS10-DGS2) inversé pour restrictive tilt}
      - USD: z-score de DTWEXBGS_yoy (ou DXY si dispo)
      - Commodities: z-score moyenne de {gold_yoy, wti_yoy, copper_yoy}
    """
    df = bundle.data.copy()

    # YoY calculable pour séries > 12 mois
    yoy_cols = {}
    def _safe_yoy(col):
        if col in df.columns:
            return df[[col]].pct_change(12, fill_method=None).rename(columns={col: col + "_YoY"})
        return pd.DataFrame()

    # Build growth components - filter out empty DataFrames
    parts = []
    for c in ["INDPRO", "PAYEMS", "RSAFS"]:
        yoy_df = _safe_yoy(c)
        if not yoy_df.empty:
            parts.append(yoy_df)
    if "NAPM" in df.columns and not df["NAPM"].empty:
        napm_df = (df[["NAPM"]] - df["NAPM"].rolling(24, min_periods=12).mean()).rename(columns={"NAPM": "NAPM_dev"})
        if not napm_df.empty:
            parts.append(napm_df)
    growth = pd.concat(parts, axis=1) if parts else pd.DataFrame()

    # Build inflation components - filter out empty DataFrames
    infl_parts = []
    for c in ["CPIAUCSL", "CPILFESL"]:
        yoy_df = _safe_yoy(c)
        if not yoy_df.empty:
            infl_parts.append(yoy_df)
    # T10YIE (niveau, recentré)
    if "T10YIE" in df.columns and not df["T10YIE"].empty:
        t10yie_df = (df[["T10YIE"]] - df["T10YIE"].rolling(24, min_periods=12).mean()).rename(columns={"T10YIE": "T10YIE_dev"})
        if not t10yie_df.empty:
            infl_parts.append(t10yie_df)
    inflation = pd.concat(infl_parts, axis=1) if infl_parts else pd.DataFrame()

    # Policy: FedFunds (niveau recentré) + slope yield (2s10s) inversé (plus inversé → plus restrictif)
    pol_parts = []
    if "FEDFUNDS" in df.columns and not df["FEDFUNDS"].empty:
        fedfunds_df = (df[["FEDFUNDS"]] - df["FEDFUNDS"].rolling(24, min_periods=12).mean()).rename(columns={"FEDFUNDS": "FEDFUNDS_dev"})
        if not fedfunds_df.empty:
            pol_parts.append(fedfunds_df)
    if "DGS10" in df.columns and "DGS2" in df.columns and not df["DGS10"].empty and not df["DGS2"].empty:
        slope = (df["DGS10"] - df["DGS2"]).to_frame("Slope_10y_2y")
        slope_df = (-slope).rename(columns={"Slope_10y_2y": "Policy_Tightness"})
        if not slope_df.empty:
            pol_parts.append(slope_df)
    policy = pd.concat(pol_parts, axis=1) if pol_parts else pd.DataFrame()

    # USD
    usd_parts = []
    if "DTWEXBGS" in df.columns and not df["DTWEXBGS"].empty:
        usd_df = df[["DTWEXBGS"]].pct_change(12, fill_method=None).rename(columns={"DTWEXBGS": "DTWEXBGS_YoY"})
        if not usd_df.empty:
            usd_parts.append(usd_df)
    if "DX-Y.NYB" in df.columns and not df["DX-Y.NYB"].empty:
        dxy_df = df[["DX-Y.NYB"]].pct_change(12, fill_method=None).rename(columns={"DX-Y.NYB": "DXY_YoY"})
        if not dxy_df.empty:
            usd_parts.append(dxy_df)
    usd = pd.concat(usd_parts, axis=1) if usd_parts else pd.DataFrame()

    # Commodities
    com_parts = []
    for col, out in [("GC=F", "Gold_YoY"), ("CL=F", "WTI_YoY"), ("HG=F", "Copper_YoY")]:
        if col in df.columns and not df[col].empty:
            com_df = df[[col]].pct_change(12, fill_method=None).rename(columns={col: out})
            if not com_df.empty:
                com_parts.append(com_df)
    commodities = pd.concat(com_parts, axis=1) if com_parts else pd.DataFrame()

    # z-scores
    growth_z = zscore_df(growth).mean(axis=1)
    infl_z = zscore_df(inflation).mean(axis=1)
    policy_z = zscore_df(policy).mean(axis=1)
    usd_z = zscore_df(usd).mean(axis=1)
    com_z = zscore_df(commodities).mean(axis=1)

    latest_df = pd.concat([
        growth_z.rename("GrowthZ"),
        infl_z.rename("InflationZ"),
        policy_z.rename("PolicyZ"),
        usd_z.rename("USDZ"),
        com_z.rename("CommoditiesZ")
    ], axis=1).dropna()

    if latest_df.empty:
        latest = pd.Series(dtype=float, index=["GrowthZ", "InflationZ", "PolicyZ", "USDZ", "CommoditiesZ"])
    else:
        latest = latest_df.iloc[-1]

    # composants (derniers dispo)
    def _safe_extract_last(series: pd.DataFrame):
        """Return the last non-NaN scalar across the column(s), ignoring trailing NaNs.

        This avoids NULLs when the global index includes a newer date from market
        proxies where FRED columns are still NaN.
        """
        try:
            if series is None or not isinstance(series, pd.DataFrame) or series.empty:
                return np.nan
            # keep only rows where at least one value is not NaN
            s = series.dropna(how="all")
            if s.empty:
                return np.nan
            # take last row with any data
            last_row = s.iloc[-1]
            # if single column, coerce to float
            if isinstance(last_row, pd.Series):
                # pick the first non-NaN value
                v = last_row.dropna()
                if v.empty:
                    return np.nan
                val = v.iloc[0]
            else:
                val = last_row
            if val is None or (isinstance(val, float) and not np.isfinite(val)):
                return np.nan
            return float(val)
        except Exception:
            return np.nan

    comps = {
        "INDPRO_YoY": _safe_extract_last(growth.filter(like="INDPRO")) if not growth.empty and growth.filter(like="INDPRO").shape[1] else np.nan,
        "PAYEMS_YoY": _safe_extract_last(growth.filter(like="PAYEMS")) if growth.filter(like="PAYEMS").shape[1] else np.nan,
        "CPI_YoY": _safe_extract_last(inflation.filter(like="CPIAUCSL")) if inflation.filter(like="CPIAUCSL").shape[1] else np.nan,
        "CoreCPI_YoY": _safe_extract_last(inflation.filter(like="CPILFESL")) if inflation.filter(like="CPILFESL").shape[1] else np.nan,
        "Breakeven_dev": _safe_extract_last(inflation.filter(like="T10YIE_dev")) if inflation.filter(like="T10YIE_dev").shape[1] else np.nan,
        "FedFunds_dev": _safe_extract_last(policy.filter(like="FEDFUNDS_dev")) if policy.filter(like="FEDFUNDS_dev").shape[1] else np.nan,
        "YieldSlope_Tight": _safe_extract_last(policy.filter(like="Policy_Tightness")) if policy.filter(like="Policy_Tightness").shape[1] else np.nan,
        "USD_YoY": float(usd.mean(axis=1).iloc[-1]) if not usd.empty else np.nan,
        "Commodities_YoY": float(commodities.mean(axis=1).iloc[-1]) if not commodities.empty else np.nan
    }

    scores = {
        "Growth": float(latest["GrowthZ"]) if "GrowthZ" in latest else np.nan,
        "Inflation": float(latest["InflationZ"]) if "InflationZ" in latest else np.nan,
        "Policy": float(latest["PolicyZ"]) if "PolicyZ" in latest else np.nan,
        "USD": float(latest["USDZ"]) if "USDZ" in latest else np.nan,
        "Commodities": float(latest["CommoditiesZ"]) if "CommoditiesZ" in latest else np.nan,
    }
    return NowcastView(scores=scores, components=comps)

# --------------------------- Facteurs & Expositions -------------------------- #

def build_macro_factors(bundle: MacroBundle) -> pd.DataFrame:
    """
    Produit un set compact de facteurs (mensuels):
      - GRW: moyenne z de {INDPRO_yoy, PAYEMS_yoy, RSAFS_yoy, NAPM_dev}
      - INF: moyenne z de {CPI_yoy, CORE_yoy, T10YIE_dev}
      - POL: z de FedFunds_dev + (−)slope(10y-2y)
      - USD: z de broad/dxy yoy
      - CMD: z de yoy {gold, wti, copper}
      - RATE10: variation de US10Y (Δ, mensuel)
    """
    df = bundle.data.copy()

    # Growth block - filter out empty series
    g_parts = []
    for c in ["INDPRO", "PAYEMS", "RSAFS"]:
        if c in df.columns and not df[c].empty:
            g_series = df[[c]].pct_change(12, fill_method=None).rename(columns={c: c + "_YoY"})
            if not g_series.empty:
                g_parts.append(g_series)
    if "NAPM" in df.columns and not df["NAPM"].empty:
        napm_series = (df[["NAPM"]] - df["NAPM"].rolling(24, min_periods=12).mean()).rename(columns={"NAPM": "NAPM_dev"})
        if not napm_series.empty:
            g_parts.append(napm_series)
    G = zscore_df(pd.concat(g_parts, axis=1)).mean(axis=1).rename("GRW") if g_parts else pd.Series(dtype=float)

    # Inflation block - filter out empty series
    i_parts = []
    for c in ["CPIAUCSL", "CPILFESL"]:
        if c in df.columns and not df[c].empty:
            i_series = df[[c]].pct_change(12, fill_method=None).rename(columns={c: c + "_YoY"})
            if not i_series.empty:
                i_parts.append(i_series)
    if "T10YIE" in df.columns and not df["T10YIE"].empty:
        t10yie_series = (df[["T10YIE"]] - df["T10YIE"].rolling(24, min_periods=12).mean()).rename(columns={"T10YIE": "T10YIE_dev"})
        if not t10yie_series.empty:
            i_parts.append(t10yie_series)
    I = zscore_df(pd.concat(i_parts, axis=1)).mean(axis=1).rename("INF") if i_parts else pd.Series(dtype=float)

    # Policy block - filter out empty series
    p_parts = []
    if "FEDFUNDS" in df.columns and not df["FEDFUNDS"].empty:
        fedfunds_series = (df[["FEDFUNDS"]] - df["FEDFUNDS"].rolling(24, min_periods=12).mean()).rename(columns={"FEDFUNDS": "FEDFUNDS_dev"})
        if not fedfunds_series.empty:
            p_parts.append(fedfunds_series)
    if "DGS10" in df.columns and "DGS2" in df.columns and not df["DGS10"].empty and not df["DGS2"].empty:
        slope_series = (-(df["DGS10"] - df["DGS2"])).to_frame("Policy_Tight")
        if not slope_series.empty:
            p_parts.append(slope_series)
    P = zscore_df(pd.concat(p_parts, axis=1)).mean(axis=1).rename("POL") if p_parts else pd.Series(dtype=float)

    # USD - filter out empty series
    u_parts = []
    if "DTWEXBGS" in df.columns and not df["DTWEXBGS"].empty:
        usd_series = df[["DTWEXBGS"]].pct_change(12, fill_method=None).rename(columns={"DTWEXBGS": "DTWEXBGS_YoY"})
        if not usd_series.empty:
            u_parts.append(usd_series)
    if "DX-Y.NYB" in df.columns and not df["DX-Y.NYB"].empty:
        dxy_series = df[["DX-Y.NYB"]].pct_change(12, fill_method=None).rename(columns={"DX-Y.NYB": "DXY_YoY"})
        if not dxy_series.empty:
            u_parts.append(dxy_series)
    U = zscore_df(pd.concat(u_parts, axis=1)).mean(axis=1).rename("USD") if u_parts else pd.Series(dtype=float)

    # Commodities - filter out empty series
    c_parts = []
    for col in ["GC=F", "CL=F", "HG=F"]:
        if col in df.columns and not df[col].empty:
            c_series = df[[col]].pct_change(12, fill_method=None).rename(columns={col: col + "_YoY"})
            if not c_series.empty:
                c_parts.append(c_series)
    C = zscore_df(pd.concat(c_parts, axis=1)).mean(axis=1).rename("CMD") if c_parts else pd.Series(dtype=float)

    # Rate10 delta (niveau → Δ mensuel)
    RATE10 = None
    if "US10Y" in df.columns and not df["US10Y"].empty:
        RATE10 = df["US10Y"].diff().rename("RATE10")
    elif "DGS10" in df.columns and not df["DGS10"].empty:
        RATE10 = (df["DGS10"] / 100.0).diff().rename("RATE10")

    # Combine all factors, handling cases where some series might be empty
    factor_series = []
    factor_dict = {"G": G, "I": I, "P": P, "U": U, "C": C}

    for key, series in factor_dict.items():
        if not series.empty:
            factor_series.append(series)

    # Add RATE10 if it exists and is not empty
    if RATE10 is not None and not RATE10.empty:
        factor_series.append(RATE10)

    if not factor_series:
        return pd.DataFrame()

    if len(factor_series) == 1:
        facs = factor_series[0].to_frame()
    else:
        facs = pd.concat(factor_series, axis=1)

    return facs.dropna(how="all")


def _align_stock_factors(ticker: str,
                         factors: pd.DataFrame,
                         period: str = "10y") -> Tuple[pd.Series, pd.DataFrame]:
    """
    Aligne les rendements mensuels (ou hebdo) du ticker sur le dataframe de facteurs.
    """
    px = yf.Ticker(ticker).history(period=period, auto_adjust=True)
    if getattr(px.index, "tz", None) is not None:
        px.index = px.index.tz_localize(None)
    if px.empty:
        return pd.Series(dtype=float), pd.DataFrame()
    # Mensualisation
    pr_m = px["Close"].resample("ME").last()
    ret_m = pr_m.pct_change().dropna()
    fac_m = factors.copy()
    common = ret_m.index.intersection(fac_m.index)
    return ret_m.loc[common], fac_m.loc[common]


def rolling_betas(ret: pd.Series, facs: pd.DataFrame, window: int = 24) -> pd.DataFrame:
    """
    Rolling OLS: ret_t ~ a + b*GRW + b*INF + b*POL + b*USD + b*CMD + b*RATE10
    Fallback numpy si statsmodels absent.
    """
    cols = [c for c in ["GRW", "INF", "POL", "USD", "CMD", "RATE10"] if c in facs.columns]
    X = facs[cols].copy()
    Y = ret.copy()
    out = pd.DataFrame(index=Y.index, columns=cols, dtype=float)

    for i in range(window, len(Y)+1):
        yi = Y.iloc[i-window:i]
        xi = X.iloc[i-window:i]
        xi = xi.dropna()
        yi = yi.loc[xi.index]
        if len(xi) < window * 0.8:
            continue
        # OLS
        if HAS_SM:
            xx = sm.add_constant(xi.values)
            model = sm.OLS(yi.values, xx, missing="drop").fit()
            betas = model.params[1:]  # sans constante
        else:
            xx = np.c_[np.ones(len(xi)), xi.values]
            try:
                betas = np.linalg.lstsq(xx, yi.values, rcond=None)[0][1:]
            except Exception:
                continue
        out.loc[yi.index[-1], cols] = betas
    return out


def factor_model(ret: pd.Series, facs: pd.DataFrame) -> ExposureReport:
    """
    OLS global pour obtenir des loadings 'moyens' + R².
    Calcule aussi la stabilité: std(β) / |mean(β)| en rolling.
    """
    cols = [c for c in ["GRW", "INF", "POL", "USD", "CMD", "RATE10"] if c in facs.columns]
    X = facs[cols].dropna()
    Y = ret.loc[X.index]
    if len(Y) < 24:
        return ExposureReport(pd.DataFrame(), {}, np.nan, {})

    # OLS global
    if HAS_SM:
        Xc = sm.add_constant(X.values)
        model = sm.OLS(Y.values, Xc).fit()
        load = dict(zip(cols, model.params[1:].tolist()))
        r2 = float(model.rsquared)
    else:
        Xc = np.c_[np.ones(len(X)), X.values]
        params = np.linalg.lstsq(Xc, Y.values, rcond=None)[0]
        load = dict(zip(cols, params[1:].tolist()))
        # R2
        yhat = Xc @ params
        ssr = np.sum((Y.values - yhat) ** 2)
        sst = np.sum((Y.values - Y.values.mean()) ** 2)
        r2 = 1.0 - ssr / sst if sst > 0 else np.nan

    # Rolling betas pour stabilité
    rb = rolling_betas(Y, X, window=24)
    stability = {}
    for c in cols:
        if c in rb and rb[c].dropna().size:
            m = rb[c].mean()
            s = rb[c].std()
            stability[c] = float(s / abs(m)) if m not in (0, np.nan) and abs(m) > 1e-9 else np.inf

    return ExposureReport(rolling_betas=rb, ols_loadings=load, r2=r2, stability=stability)

# --------------------------- Macro Regime Classifier ------------------------- #

def macro_regime(nc: NowcastView) -> MacroRegimeView:
    """
    Classification simple par règles sur z-scores:
      - Reflation: Growth>0 & Inflation>0 & Policy accommodante (Policy<0)
      - Goldilocks: Growth>0 & Inflation<0 (désinflation avec croissance)
      - Stagflation: Growth<0 & Inflation>0
      - Désinflation restrictive: Inflation<0 & Policy>0 (resserrement)
      Sinon: 'Transition'
    """
    g = nc.scores.get("Growth", np.nan)
    i = nc.scores.get("Inflation", np.nan)
    p = nc.scores.get("Policy", np.nan)

    if np.isfinite(g) and np.isfinite(i) and np.isfinite(p):
        if g > 0 and i > 0 and p < 0:
            lab = "Reflation"
        elif g > 0 and i < 0:
            lab = "Goldilocks"
        elif g < 0 and i > 0:
            lab = "Stagflation"
        elif i < 0 and p > 0:
            lab = "Désinflation restrictive"
        else:
            lab = "Transition"
    else:
        lab = "Inconnu"

    extra = {"USD": nc.scores.get("USD"), "Commodities": nc.scores.get("Commodities")}
    return MacroRegimeView(label=lab, growth_z=g, inflation_z=i, policy_z=p, extra=extra)

# ------------------------------- Scénarios ----------------------------------- #

def scenario_impact(exposure: ExposureReport,
                    deltas: Dict[str, float]) -> ScenarioImpact:
    """
    Estime l'impact instantané (%) sur le titre pour des chocs de facteurs.
    Convention des deltas:
      - GRW, INF, POL, USD, CMD: variation en 'z' (écarts-types) — si vous donnez des %,
        convertissez-les d'abord en z vs. historique, sinon supposez 1 z ≈ move 'normal'.
      - RATE10: choc en points décimaux de taux (ex: +0.005 = +50 pb)
    Exemple:
        {"USD": +1.0, "RATE10": +0.005, "CMD": -0.5}
    """
    if not exposure.ols_loadings:
        return ScenarioImpact(deltas=deltas, expected_return_pct=np.nan, detail={})

    load = exposure.ols_loadings
    detail: Dict[str, float] = {}
    ret = 0.0
    for k, dv in deltas.items():
        if k in load:
            contrib = load[k] * dv * 100.0  # en %
            detail[k] = float(contrib)
            ret += contrib
        else:
            # facteur absent → contribution nulle
            detail[k] = 0.0
    return ScenarioImpact(deltas=deltas, expected_return_pct=float(ret), detail=detail)

# --------------------------- API "haut niveau" --------------------------------#

def get_macro_features() -> Dict[str, Any]:
    """
    Get current macro features using the macro nowcast function.
    This is a wrapper function to match the expected signature from app.py.

    Returns:
        Dict: Current macro features suitable for conversion to dict
    """
    try:
        # Get the US macro bundle
        bundle = get_us_macro_bundle(start="2000-01-01", monthly=True)

        # Generate the macro nowcast
        nowcast = macro_nowcast(bundle)

        ts = None
        if not bundle.data.empty:
            try:
                ts = pd.Timestamp(bundle.data.index[-1]).strftime("%Y-%m-%d")
            except Exception:
                ts = str(bundle.data.index[-1])
        # Build last update dates for key FRED series (YYYY-MM)
        def _last_date_col(df: pd.DataFrame, col: str) -> Optional[str]:
            if col not in df.columns:
                return None
            s = df[[col]].dropna().iloc[-1:] if not df[[col]].dropna().empty else None
            if s is None or s.empty:
                return None
            try:
                d = s.index[-1]
                return pd.Timestamp(d).strftime("%Y-%m")
            except Exception:
                return None

        last_dates = {}
        base_df = bundle.data
        for c in ["INDPRO","PAYEMS","CPIAUCSL","CPILFESL","T10YIE","FEDFUNDS","DGS10","DGS2","DTWEXBGS"]:
            v = _last_date_col(base_df, c)
            if v:
                last_dates[c] = v

        macro_features = {
            "macro_nowcast": nowcast.to_dict(),
            "timestamp": ts,
            "meta": {**bundle.meta, "last_dates": last_dates}
        }

        clean, missing = _clean_non_finite(macro_features, "macro_features")
        if missing:
            logger.warning("sanitize(macro_features) normalized %d field(s): %s", len(missing), ", ".join(missing))
            # expose dans meta pour la transparence I/O
            clean.setdefault("meta", {}).setdefault("missing_fields", []).extend(missing)
        return clean

    except Exception as e:
        # Return error dict
        macro_features = {
            "error": f"Failed to get macro features: {str(e)}",
            "macro_nowcast": {
                "scores": {},
                "components": {}
            },
            "meta": {}
        }

        clean, missing = _clean_non_finite(macro_features, "macro_features")
        if missing:
            logger.warning("sanitize(error_macro_features) normalized %d field(s): %s", len(missing), ", ".join(missing))
            clean.setdefault("meta", {}).setdefault("missing_fields", []).extend(missing)
        return clean


def build_macro_view(ticker: str,
                     start: str = "2000-01-01",
                     period_stock: str = "15y") -> Dict[str, Any]:
    """
    Pipeline complet:
      1) Récupère macro US (mensuel) + proxies
      2) Nowcast (scores z)
      3) Facteurs agrégés
      4) Aligne rendements mensuels du ticker
      5) Expositions (OLS + rolling β) & R²
      6) Régime macro
    Retourne un dict compact (prêt à intégrer dans l’app).
    """
    bundle = get_us_macro_bundle(start=start, monthly=True)
    nc = macro_nowcast(bundle)
    facs = build_macro_factors(bundle)
    ret_m, facs_m = _align_stock_factors(ticker, facs, period=period_stock)
    expo = factor_model(ret_m, facs_m)
    reg = macro_regime(nc)

    # Résumé "drivers"
    drivers = sorted(expo.ols_loadings.items(), key=lambda kv: abs(kv[1]), reverse=True) if expo.ols_loadings else []
    top_drivers = [f"{k}:{v:+.2f}" for k, v in drivers[:4]]

    return {
        "ticker": ticker,
        "macro_meta": bundle.meta,
        "nowcast": nc.to_dict(),
        "regime": reg.to_dict(),
        "exposure": expo.to_dict(),
        "top_drivers": top_drivers
    }

# --------------------------------- Exemple ----------------------------------- #

if __name__ == "__main__":
    import json

    TICKER = "AEM.TO"   # exemple Canada (or)
    view = build_macro_view(TICKER, start="2003-01-01", period_stock="20y")
    print("=== MACRO VIEW ===")
    print(json.dumps(view, indent=2))

    # Scénario: USD +1 écart-type, 10Y +50 pb, Commodities -0.5 z
    # (interprétation: choc restrictif, dollar fort, matières premières en repli)
    # → Utilise les loadings OLS estimés
    from pprint import pprint
    bundle = get_us_macro_bundle(start="2003-01-01", monthly=True)
    facs = build_macro_factors(bundle)
    ret_m, facs_m = _align_stock_factors(TICKER, facs, period="20y")
    expo = factor_model(ret_m, facs_m)

    scen = scenario_impact(expo, {"USD": +1.0, "RATE10": +0.005, "CMD": -0.5})
    print("\n=== SCENARIO IMPACT (instantané %) ===")
    pprint(scen.to_dict())
