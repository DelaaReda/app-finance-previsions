# sanity_runner_ia_chat.py

## Function: `load_verified_from_cache`

Signature: `def load_verified_from_cache(...)->Optional[dict]`

Inputs:
- `max_age_sec`: Any = 3600
Returns: `Optional[dict]`

## Function: `save_verified_to_cache`

Signature: `def save_verified_to_cache(...)->Any`

Inputs:
- `data`: dict
Returns: `Any`

## Function: `parse_models_txt`

Signature: `def parse_models_txt(...)->List[dict]`

Inputs:
- `text`: str
Returns: `List[dict]`

## Function: `load_verified_models`

Signature: `def load_verified_models(...)->dict`

Inputs:
- `refresh`: Any = False
Returns: `dict`

## Function: `select_verified_models`

Signature: `def select_verified_models(...)->List[dict]`

Inputs:
- `caps_need`: Any = ('text',)
- `min_pass`: Any = 0.3
- `only_sota`: Any = True
- `limit`: Any = 30
- `refresh`: Any = False
Returns: `List[dict]`

## Function: `provider_candidates_for`

Signature: `def provider_candidates_for(...)->List[str]`

Inputs:
- `model_name`: str
- `hint`: Optional[str]
Returns: `List[str]`

## Function: `g4f_chat_once`

Signature: `def g4f_chat_once(...)->Optional[str]`

Appel simple g4f → renvoie str ou None si échec.
NB: suivant la version g4f, la signature peut varier (client.ChatCompletion.create vs client.chat.completions.create).
Adapte si besoin à ta version exacte.

Inputs:
- `provider`: str
- `prompt`: str
- `model`: Optional[str] = None
- `system`: Optional[str] = None
- `temperature`: float = 0.2
- `max_tokens`: int = 2048
- `timeout`: int = 45
Returns: `Optional[str]`

## Function: `llm_ask`

Signature: `def llm_ask(...)->dict`

Sélectionne un modèle 'verified' et tente des providers en cascade.
Retourne {model, provider, pass_rate, text} (ou text=None si tout a échoué).

Inputs:
- `prompt`: str
- `system`: Optional[str] = None
- `caps`: Any = 'text'
- `min_pass`: Any = 0.3
- `only_sota`: Any = True
- `refresh`: Any = False
- `temperature`: Any = 0.2
- `max_tokens`: Any = 2048
- `tries_per_model`: Any = 2
- `providers_per_model`: Any = 4
Returns: `dict`

## Function: `ask_with_specific_model`

Signature: `def ask_with_specific_model(...)->dict`

Force l’usage d’un modèle précis, avec cascade de providers.

Inputs:
- `model_name`: str
- `prompt`: str
- `system`: str = None
- `temperature`: float = 0.2
- `max_tokens`: int = 1024
- `providers_per_model`: int = 4
- `tries_per_model`: int = 2
- `timeout`: int = 45
Returns: `dict`

## Function: `run_top5_tests`

Signature: `def run_top5_tests(...)->Any`

Inputs:
- `refresh`: Any = False
- `min_pass`: Any = 0.3
- `only_sota`: Any = True
Returns: `Any`
