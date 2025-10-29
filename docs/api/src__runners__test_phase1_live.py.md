# test_phase1_live.py

Test live de la Phase 1 (fondamentaux) — sans mock.
- Log les appels et tailles de jeux de données
- Détecte et appelle automatiquement les fonctions de phase1_fundamental si présentes
- Fallback sur yfinance pour vérifier la connectivité et la disponibilité des états financiers
- Sauvegarde des artefacts (JSON/CSV) par ticker

Usage:
  python test_phase1_live.py --ticker NGD.TO --log DEBUG

## Function: `setup_logging`

Signature: `def setup_logging(...)->None`

Inputs:
- `level`: str = 'INFO'
Returns: `None`

## Function: `log_env`

Signature: `def log_env(...)->Any`

Inputs:
- (none)
Returns: `Any`

## Function: `ensure_dir`

Signature: `def ensure_dir(...)->None`

Inputs:
- `path`: str
Returns: `None`

## Function: `dump_json`

Signature: `def dump_json(...)->None`

Inputs:
- `obj`: Any
- `path`: str
Returns: `None`

## Function: `dump_df`

Signature: `def dump_df(...)->None`

Inputs:
- `df`: Any
- `path_csv`: str
Returns: `None`

## Function: `import_phase1`

Signature: `def import_phase1(...)->Optional[Any]`

Inputs:
- (none)
Returns: `Optional[Any]`

## Function: `list_funcs`

Signature: `def list_funcs(...)->List[str]`

Inputs:
- `P1`: Any
Returns: `List[str]`

## Function: `try_call`

Signature: `def try_call(...)->Any`

Appelle P1.func_name si dispo. Retourne (ok, result/None).

Inputs:
- `P1`: Any
- `func_name`: str
- `*args`: Any
- `**kwargs`: Any
Returns: `Any`

## Function: `clean_peers_df`

Signature: `def clean_peers_df(...)->Any`

Supprime les tickers obviously invalides et les lignes sans métriques utilisables.

Inputs:
- `peers_df`: Any
- `subject_ticker`: str
Returns: `Any`

## Function: `save_any`

Signature: `def save_any(...)->None`

Sauve intelligemment dict/df/liste.

Inputs:
- `name`: str
- `outdir`: str
- `obj`: Any
Returns: `None`

## Function: `probe_yfinance`

Signature: `def probe_yfinance(...)->Dict[str, Any]`

Récupère des blocs essentiels avec yfinance pour s'assurer que:
 - le réseau fonctionne
 - les états financiers sont récupérables

Inputs:
- `ticker`: str
- `outdir`: str
Returns: `Dict[str, Any]`

## Function: `run_phase1_live_for_ticker`

Signature: `def run_phase1_live_for_ticker(...)->int`

Inputs:
- `ticker`: str
- `root_out`: str
- `P1`: Any
Returns: `int`

## Function: `main`

Signature: `def main(...)->Any`

Inputs:
- (none)
Returns: `Any`
