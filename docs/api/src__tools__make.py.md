# make.py

## Function: `run_make`

Signature: `def run_make(...)->Dict`

Run a Makefile target and capture result.

Returns a dict: {"rc": int, "duration_ms": int, "out": str}.

Inputs:
- `target`: str
- `args`: Optional[List[str]] = None
- `timeout`: int = 900
- `cwd`: Optional[str] = None
Returns: `Dict`
