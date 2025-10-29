# econ_llm_agent.py

## Class: `EconomicInput`

## Function: `clean_llm_text`

Signature: `def clean_llm_text(...)->str`

Clean LLM responses by removing repetitions and truncating.

Inputs:
- `txt`: str
- `max_chars`: int = 3000
Returns: `str`

## Class: `EconomicAnalyst`

Agent générique pour analyses économiques & Q/A multi-sources via g4f.
- analyze(...) : essaie plusieurs modèles jusqu'à succès.
- analyze_ensemble(..., top_n=3, force_power=False, adjudicate=False)

### Method: `EconomicAnalyst.analyze`

Signature: `def analyze(...)->Dict[str, Any]`

Inputs:
- `data`: EconomicInput
Returns: `Dict[str, Any]`

### Method: `EconomicAnalyst.analyze_ensemble`

Signature: `def analyze_ensemble(...)->Dict[str, Any]`

Inputs:
- `data`: EconomicInput
- `top_n`: int = 3
- `force_power`: bool = False
- `adjudicate`: bool = False
Returns: `Dict[str, Any]`

## Function: `main`

Signature: `def main(...)->int`

Inputs:
- `argv`: Optional[List[str]] = None
Returns: `int`

## Function: `ask_model`

Signature: `def ask_model(...)->str`

Interface simplifiée pour poser des questions économiques.

Inputs:
- `question`: str
- `context`: dict = None
Returns: `str`

## Function: `arbitre`

Signature: `def arbitre(...)->dict`

Interface arbitre pour les décisions économiques.

Inputs:
- `context`: dict
Returns: `dict`
