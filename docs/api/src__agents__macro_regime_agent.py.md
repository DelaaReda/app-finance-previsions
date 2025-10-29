# macro_regime_agent.py

Macro Regime Agent — classifies current macro regime with simple heuristics from FRED.

Outputs JSON at data/macro/regime/dt=YYYYMMDD/regime.json with:
- indicators (yoy CPI, yoy GDP, yield_curve_bp, unrate, t10y_ie)
- regime probabilities for: expansion, slowdown, inflation, deflation
- text summary in FR (brief)

## Function: `classify_regime`

Signature: `def classify_regime(...)->Dict[str, float]`

Inputs:
- `ind`: Dict[str, float | None]
Returns: `Dict[str, float]`

## Function: `run`

Signature: `def run(...)->Path`

Inputs:
- (none)
Returns: `Path`
