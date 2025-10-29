# phase5_fusion.py

Phase 5 — Fusion, Scoring Global & Orchestration

Assemble les sorties des Phases 1→4 pour produire:
- Score global (0..100)
- Scores par pilier: Fondamental / Technique / Macro / Sentiment
- Ajustement de risque (volatilité, VaR, bêta, DD)
- Recommandation (Acheter / Neutre / Vendre) + drivers + flags
- Paquet "prêt UI": dictionnaire + DataFrames optionnels

Licence: MIT (adapter à votre projet)

## Class: `PillarScores`

### Method: `PillarScores.as_dict`

Signature: `def as_dict(...)->Dict[str, float]`

Inputs:
- (none)
Returns: `Dict[str, float]`

## Class: `RiskMetrics`

### Method: `RiskMetrics.risk_malus`

Signature: `def risk_malus(...)->float`

Convertit le profil de risque en malus (-20..0).
- Volatilité élevée, VaR négative importante, DD profond, bêta > 1.3 ⇒ baisse de score

Inputs:
- (none)
Returns: `float`

### Method: `RiskMetrics.flags`

Signature: `def flags(...)->List[str]`

Inputs:
- (none)
Returns: `List[str]`

## Class: `FusionOutput`

### Method: `FusionOutput.to_json`

Signature: `def to_json(...)->str`

Inputs:
- `compact`: bool = True
Returns: `str`

## Function: `fuse_fundamental`

Signature: `def fuse_fundamental(...)->Tuple[float, List[str], Dict[str, Any]]`

Agrège un score fondamental sur 0..100.
Attend en entrée la sortie de phase2_factor_models (ou dict similaire):
  - ratios (ROE, marge nette, leverage, growth EPS/Rev)
  - valuation (PE, EV/EBITDA, P/S) vs. pairs / secteur
  - qualité (FCF, marge, stabilité)

Inputs:
- `p2_payload`: Optional[Dict[str, Any]]
Returns: `Tuple[float, List[str], Dict[str, Any]]`

## Function: `fuse_technical`

Signature: `def fuse_technical(...)->Tuple[float, List[str], Dict[str, Any]]`

Utilise les signaux CT/MT déjà présents dans ton app (RSI/MACD/SMA/Breakout…).
p1_payload attend:
  - short_sig: {"score": -1..+1, "signals": {...}}
  - med_sig:   {"score": -1..+1, "signals": {...}}
  - regime: "Bull/Bear/Range"

Inputs:
- `p1_payload`: Dict[str, Any]
Returns: `Tuple[float, List[str], Dict[str, Any]]`

## Function: `fuse_macro`

Signature: `def fuse_macro(...)->Tuple[float, List[str], Dict[str, Any]]`

Convertit l’état macro en score 0..100.
p3_payload attendu (phase3_macro):
  - regime: {"label": "Goldilocks/Slowflation/Stagflation/Overheat", "zscore": ...}
  - factor_tailwinds: {"inflation": +/-, "rates": +/-, "usd": +/-, ...} sur -1..+1
  - sector_fit: score -1..+1 à +1 pro-secteur
  - nowcasts / surprises optionnels

Inputs:
- `p3_payload`: Optional[Dict[str, Any]]
Returns: `Tuple[float, List[str], Dict[str, Any]]`

## Function: `fuse_sentiment`

Signature: `def fuse_sentiment(...)->Tuple[float, List[str], Dict[str, Any], Optional[pd.DataFrame], Optional[pd.DataFrame]]`

Convertit la vue sentiment/news (phase4) en score 0..100.
Utilise mean_sent_7d / 30d + shock/drift + risk flags.

Inputs:
- `p4_view`: Optional[Dict[str, Any]]
Returns: `Tuple[float, List[str], Dict[str, Any], Optional[pd.DataFrame], Optional[pd.DataFrame]]`

## Function: `combine_scores`

Signature: `def combine_scores(...)->Tuple[float, List[str]]`

Combine les scores par pilier + malus risque pour produire total (0..100).

Inputs:
- `pillars`: PillarScores
- `risk`: RiskMetrics
- `weights`: Dict[str, float] = None
Returns: `Tuple[float, List[str]]`

## Function: `make_recommendation`

Signature: `def make_recommendation(...)->str`

Règle simple — adapte à tes préférences.

Inputs:
- `total_score`: float
- `horizon`: str = '6–12m'
Returns: `str`

## Function: `run_fusion`

Signature: `def run_fusion(...)->FusionOutput`

Assemble les 4 piliers + risque => score global & reco.
Si compute_missing_with_phases=True et que certains payloads manquent,
tente de les calculer via P1..P4 (si importés).

Inputs:
- `ticker`: str
- `p1_payload`: Optional[Dict[str, Any]] = None
- `p2_payload`: Optional[Dict[str, Any]] = None
- `p3_payload`: Optional[Dict[str, Any]] = None
- `p4_view`: Optional[Dict[str, Any]] = None
- `compute_missing_with_phases`: bool = False
- `horizon_label`: str = '6–12m'
Returns: `FusionOutput`
