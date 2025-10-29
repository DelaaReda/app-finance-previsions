# g4f_model_watcher.py

G4F Model Watcher — keeps a local working list of high‑quality g4f models.

- Selects SOTA verified models (using src.runners.sanity_runner_ia_chat if network allows)
- Tests a handful with short prompts via g4f, measures latency
- Writes: data/llm/models/working.json

Use:
  python -m src.agents.g4f_model_watcher --refresh --limit 8

## Class: `ModelProbe`

## Function: `refresh`

Signature: `def refresh(...)->Path`

Inputs:
- `limit`: int = 8
- `refresh_verified`: bool = True
Returns: `Path`

## Function: `load_working_models`

Signature: `def load_working_models(...)->List[str]`

Inputs:
- `max_age_hours`: int = 24
Returns: `List[str]`

## Function: `merge_from_working_txt`

Signature: `def merge_from_working_txt(...)->Path`

Merge provider|model|media_type lines into working.json, marking them ok.

Lines format: provider|model|media_type
Unknown latency/pass_rate will be left as None.

Inputs:
- `txt_path`: Path
Returns: `Path`

## Function: `main`

Signature: `def main(...)->int`

Inputs:
- `argv`: Optional[List[str]] = None
Returns: `int`
