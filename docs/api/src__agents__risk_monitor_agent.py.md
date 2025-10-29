# risk_monitor_agent.py

Risk Monitor Agent — computes a simple composite risk score using FRED series:
- Yield curve inversion magnitude (DGS10 - DGS2, bp)
- High Yield spread (BAMLH0A0HYM2)
- Chicago NFCI (NFCI)

Writes data/risk/dt=YYYYMMDD/risk.json with normalized components and composite.

## Function: `run`

Signature: `def run(...)->Path`

Inputs:
- (none)
Returns: `Path`
