# recession_agent.py

Recession Risk Agent — estimates recession probability using macro proxies:
- Yield curve inversion (DGS10 - DGS2, bp)
- Unemployment 6m change (UNRATE)
- NFCI (Chicago Fed index)
- HY spread (BAMLH0A0HYM2)

Outputs: data/macro/recession/dt=YYYYMMDD/recession.json
Fields: asof, inputs, scores (normalized), probability, summary_fr

## Function: `run`

Signature: `def run(...)->Path`

Inputs:
- (none)
Returns: `Path`
