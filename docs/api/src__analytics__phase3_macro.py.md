# phase3_macro.py

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

## Class: `MacroBundle`

Conteneur de séries macro alignées (mensuelles par défaut).

### Method: `MacroBundle.to_frame`

Signature: `def to_frame(...)->pd.DataFrame`

Inputs:
- (none)
Returns: `pd.DataFrame`

### Method: `MacroBundle.to_dict`

Signature: `def to_dict(...)->Dict[str, Any]`

Inputs:
- (none)
Returns: `Dict[str, Any]`

## Class: `NowcastView`

Indices synthétiques standardisés (z-scores): Growth, Inflation, Policy, USD, Commodities.

### Method: `NowcastView.to_dict`

Signature: `def to_dict(...)->Dict[str, Any]`

Inputs:
- (none)
Returns: `Dict[str, Any]`

## Class: `ExposureReport`

Expositions macro d’un titre (rolling β, OLS multi-facteurs).

### Method: `ExposureReport.to_dict`

Signature: `def to_dict(...)->Dict[str, Any]`

Inputs:
- (none)
Returns: `Dict[str, Any]`

## Class: `MacroRegimeView`

Classification de régime macro agrégée.

### Method: `MacroRegimeView.to_dict`

Signature: `def to_dict(...)->Dict[str, Any]`

Inputs:
- (none)
Returns: `Dict[str, Any]`

## Class: `ScenarioImpact`

Projection d’impact (%) sur le titre pour des chocs macro instantanés.

### Method: `ScenarioImpact.to_dict`

Signature: `def to_dict(...)->Dict[str, Any]`

Inputs:
- (none)
Returns: `Dict[str, Any]`

## Function: `fetch_fred_series`

Signature: `def fetch_fred_series(...)->pd.DataFrame`

Batch FRED (tolérant aux échecs) avec logs de diagnostic par série.

Inputs:
- `series`: List[str]
- `start`: Optional[str] = None
- `sleep`: float = 0.15
Returns: `pd.DataFrame`

## Function: `fetch_market_proxies`

Signature: `def fetch_market_proxies(...)->pd.DataFrame`

Proxies marchés via yfinance (journaliers):
  - DXY: "DX-Y.NYB" (USD Index)
  - Gold: "GC=F"
  - WTI: "CL=F"
  - Copper: "HG=F"
  - US10Y: "^TNX" (rendement 10Y *100, donc /100 pour décimal)

Inputs:
- `period`: str = '10y'
Returns: `pd.DataFrame`

## Function: `resample_align`

Signature: `def resample_align(...)->pd.DataFrame`

Standardise la fréquence (mensuelle par défaut).
method: 'last' (par défaut), 'mean'

Inputs:
- `df`: pd.DataFrame
- `freq`: str = 'ME'
- `method`: str = 'last'
Returns: `pd.DataFrame`

## Function: `pct_chg`

Signature: `def pct_chg(...)->pd.DataFrame`

Inputs:
- `df`: pd.DataFrame
- `periods`: int = 1
Returns: `pd.DataFrame`

## Function: `yoy`

Signature: `def yoy(...)->pd.DataFrame`

Croissance annuelle (YoY) pour données mensuelles/quarterly.

Inputs:
- `df`: pd.DataFrame
Returns: `pd.DataFrame`

## Function: `zscore_df`

Signature: `def zscore_df(...)->pd.DataFrame`

Z-score par colonne, winsorisé pour robustesse.

Inputs:
- `df`: pd.DataFrame
- `winsor`: float = 3.0
Returns: `pd.DataFrame`

## Function: `get_us_macro_bundle`

Signature: `def get_us_macro_bundle(...)->MacroBundle`

Récupère un panier de séries macro US 'core' :
  - Growth: INDPRO, PAYEMS, RETAIL SALES (RSAFS), ISM MANUFACTURING PMI (NAPM)
  - Inflation: CPIAUCSL, CORE CPI (CPILFESL), 5y5y (T5YIFR) proxy: T10YIE (breakeven 10Y)
  - Policy: Fed Funds Rate (FEDFUNDS), 10Y (DGS10), 2Y (DGS2)
  - USD: DTWEXBGS (Dollar broad)
  - Credit/Stress: NFCI
Et proxies marchés (Gold, DXY, WTI, Copper, US10Y).

Inputs:
- `start`: str = '2000-01-01'
- `monthly`: bool = True
Returns: `MacroBundle`

## Function: `macro_nowcast`

Signature: `def macro_nowcast(...)->NowcastView`

Construit des scores synthétiques à partir de YoY (growth, inflation)
et niveaux / spreads (policy), ainsi que proxies (USD, commodities).
Méthode:
  - Growth: z-score moyenne de {INDPRO_yoy, PAYEMS_yoy, RSAFS_yoy, NAPM (demean)}
  - Inflation: z-score moyenne de {CPIAUCSL_yoy, CPILFESL_yoy, T10YIE (demean)}
  - Policy: z-score moyenne de {FEDFUNDS, (DGS10-DGS2) inversé pour restrictive tilt}
  - USD: z-score de DTWEXBGS_yoy (ou DXY si dispo)
  - Commodities: z-score moyenne de {gold_yoy, wti_yoy, copper_yoy}

Inputs:
- `bundle`: MacroBundle
Returns: `NowcastView`

## Function: `build_macro_factors`

Signature: `def build_macro_factors(...)->pd.DataFrame`

Produit un set compact de facteurs (mensuels):
  - GRW: moyenne z de {INDPRO_yoy, PAYEMS_yoy, RSAFS_yoy, NAPM_dev}
  - INF: moyenne z de {CPI_yoy, CORE_yoy, T10YIE_dev}
  - POL: z de FedFunds_dev + (−)slope(10y-2y)
  - USD: z de broad/dxy yoy
  - CMD: z de yoy {gold, wti, copper}
  - RATE10: variation de US10Y (Δ, mensuel)

Inputs:
- `bundle`: MacroBundle
Returns: `pd.DataFrame`

## Function: `rolling_betas`

Signature: `def rolling_betas(...)->pd.DataFrame`

Rolling OLS: ret_t ~ a + b*GRW + b*INF + b*POL + b*USD + b*CMD + b*RATE10
Fallback numpy si statsmodels absent.

Inputs:
- `ret`: pd.Series
- `facs`: pd.DataFrame
- `window`: int = 24
Returns: `pd.DataFrame`

## Function: `factor_model`

Signature: `def factor_model(...)->ExposureReport`

OLS global pour obtenir des loadings 'moyens' + R².
Calcule aussi la stabilité: std(β) / |mean(β)| en rolling.

Inputs:
- `ret`: pd.Series
- `facs`: pd.DataFrame
Returns: `ExposureReport`

## Function: `macro_regime`

Signature: `def macro_regime(...)->MacroRegimeView`

Classification simple par règles sur z-scores:
  - Reflation: Growth>0 & Inflation>0 & Policy accommodante (Policy<0)
  - Goldilocks: Growth>0 & Inflation<0 (désinflation avec croissance)
  - Stagflation: Growth<0 & Inflation>0
  - Désinflation restrictive: Inflation<0 & Policy>0 (resserrement)
  Sinon: 'Transition'

Inputs:
- `nc`: NowcastView
Returns: `MacroRegimeView`

## Function: `scenario_impact`

Signature: `def scenario_impact(...)->ScenarioImpact`

Estime l'impact instantané (%) sur le titre pour des chocs de facteurs.
Convention des deltas:
  - GRW, INF, POL, USD, CMD: variation en 'z' (écarts-types) — si vous donnez des %,
    convertissez-les d'abord en z vs. historique, sinon supposez 1 z ≈ move 'normal'.
  - RATE10: choc en points décimaux de taux (ex: +0.005 = +50 pb)
Exemple:
    {"USD": +1.0, "RATE10": +0.005, "CMD": -0.5}

Inputs:
- `exposure`: ExposureReport
- `deltas`: Dict[str, float]
Returns: `ScenarioImpact`

## Function: `get_macro_features`

Signature: `def get_macro_features(...)->Dict[str, Any]`

Get current macro features using the macro nowcast function.
This is a wrapper function to match the expected signature from app.py.

Returns:
    Dict: Current macro features suitable for conversion to dict

Inputs:
- (none)
Returns: `Dict[str, Any]`

## Function: `build_macro_view`

Signature: `def build_macro_view(...)->Dict[str, Any]`

Pipeline complet:
  1) Récupère macro US (mensuel) + proxies
  2) Nowcast (scores z)
  3) Facteurs agrégés
  4) Aligne rendements mensuels du ticker
  5) Expositions (OLS + rolling β) & R²
  6) Régime macro
Retourne un dict compact (prêt à intégrer dans l’app).

Inputs:
- `ticker`: str
- `start`: str = '2000-01-01'
- `period_stock`: str = '15y'
Returns: `Dict[str, Any]`
