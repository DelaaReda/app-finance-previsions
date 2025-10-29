# investment_memo_agent.py

Investment Memo Agent — per‑ticker concise memo via LLM ensemble (text‑only).

Writes data/memos/dt=YYYYMMDD/<ticker>.json with:
- answer (markdown), parsed (if JSON tail parsed), and metadata

## Function: `memo_for_ticker`

Signature: `def memo_for_ticker(...)->Path`

Inputs:
- `ticker`: str
- `locale`: str = 'fr-FR'
- `top_n`: int = 3
Returns: `Path`

## Function: `run_all`

Signature: `def run_all(...)->List[str]`

Inputs:
- `watchlist`: Optional[List[str]] = None
- `locale`: str = 'fr-FR'
- `top_n`: int = 3
Returns: `List[str]`
