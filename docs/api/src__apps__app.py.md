# app.py

## Function: `log_exc`

Signature: `def log_exc(...)->Any`

Inputs:
- `where`: str
- `exc`: BaseException
Returns: `Any`

## Function: `log_debug`

Signature: `def log_debug(...)->Any`

Inputs:
- `msg`: str
Returns: `Any`

## Function: `trace_call`

Signature: `def trace_call(...)->Any`

Decorator (or wrapper) to log enter/exit/duration/errors.

Usage:
  @trace_call("func_name")
  def f(...): ...

  # or wrap dynamically
  f_wrapped = trace_call("func_name", f)

Inputs:
- `name`: str
- `fn`: Any = None
Returns: `Any`

## Function: `safe_import`

Signature: `def safe_import(...)->Any`

Import robuste : retourne (objet|None, erreur|None) ET logue timing + fichier.

Inputs:
- `path`: str
- `attr`: Optional[str] = None
Returns: `Any`

## Function: `expand_label`

Signature: `def expand_label(...)->str`

Inputs:
- `label`: str
Returns: `str`

## Function: `expand_columns`

Signature: `def expand_columns(...)->Optional[pd.DataFrame]`

Inputs:
- `df`: Optional[pd.DataFrame]
Returns: `Optional[pd.DataFrame]`

## Function: `to_mapping`

Signature: `def to_mapping(...)->Any`

Transforme proprement en dict pour affichage (supporte objets news custom).

Inputs:
- `obj`: Any
Returns: `Any`

## Function: `show_full`

Signature: `def show_full(...)->Any`

Affiche tout, sans cacher : DataFrame -> tableau; dict/list -> JSON; autre -> texte.

Inputs:
- `name`: str
- `data`: Any
Returns: `Any`

## Function: `render_macro_summary_block`

Signature: `def render_macro_summary_block(...)->Any`

Inputs:
- `macro_feats`: dict
Returns: `Any`

## Function: `main`

Signature: `def main(...)->Any`

Inputs:
- (none)
Returns: `Any`
