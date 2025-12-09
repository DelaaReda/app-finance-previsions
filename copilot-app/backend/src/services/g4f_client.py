import os
import json
import logging
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    from g4f.client import Client as G4FClient  # type: ignore
except Exception:
    G4FClient = None


def call_g4f(
    messages: List[Dict[str, Any]],
    model: str = None,
    provider: str = None,
    timeout: int = 60,
) -> Dict[str, Any]:
    """
    Fallback g4f (no-auth) provider call.
    Requires g4f installed. Uses provider/model from args or env.
    """
    if G4FClient is None:
        return {"ok": False, "error": "g4f_not_installed", "answer": ""}

    # Choix du modèle: priorité aux arguments explicites, puis .env,
    # puis tested_g4f_models_ok.json (ou tested_g4f_models.json) triés par latence,
    # avec préférence pour la catégorie "forecast" si dispo.
    tested_model = _fastest_tested_model(category_preference="forecast")
    model_name = (
        model
        or os.environ.get("G4F_MODEL")
        or (tested_model[1] if tested_model else None)
        or "meta-llama/Llama-3.3-70B-Instruct"
    )
    provider_name = (
        provider
        or os.environ.get("G4F_PROVIDER")
        or (tested_model[0] if tested_model else None)
        or "DeepInfra"
    )

    try:
        client = G4FClient()
        res = client.chat.completions.create(
            model=model_name,
            provider=provider_name,
            messages=messages,
            timeout=timeout,
        )
        content = (
            res.choices[0].message.content
            if res and hasattr(res, "choices") and res.choices
            else ""
        )
        return {
            "ok": True,
            "answer": content,
            "model": model_name,
            "provider": provider_name,
            "raw": json.loads(res.model_dump_json()) if hasattr(res, "model_dump_json") else res,
        }
    except Exception as e:
        return {"ok": False, "error": f"g4f_error: {e}", "answer": ""}


@lru_cache(maxsize=1)
def _fastest_tested_model(category_preference: Optional[str] = None) -> Optional[Tuple[str, str]]:
    """
    Lit src/tested_g4f_models_ok.json (puis fallback tested_g4f_models.json)
    et retourne (provider, model) avec latence la plus faible parmi les ok=True.
    Si category_preference est fourni, on filtre d'abord sur cette catégorie si dispo.
    """
    try:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        ok_path = os.path.join(base_dir, "tested_g4f_models_ok.json")
        full_path = os.path.join(base_dir, "tested_g4f_models.json")

        data = None
        if os.path.exists(ok_path):
            with open(ok_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        elif os.path.exists(full_path):
            with open(full_path, "r", encoding="utf-8") as f:
                data = json.load(f)

        if not isinstance(data, list):
            return None

        ok_models = [
            r
            for r in data
            if r.get("ok")
            and r.get("model")
            and r.get("provider")
            and (r.get("answer") or "").strip()  # éviter les réponses vides
        ]
        if not ok_models:
            return None
        # Priorité à la catégorie demandée si présente
        if category_preference:
            cat_models = [
                r for r in ok_models if (r.get("category") or "").lower() == category_preference.lower()
            ]
            if cat_models:
                ok_models = cat_models
        ok_models = sorted(ok_models, key=lambda r: r.get("ms", 1e9))
        best = ok_models[0]
        logger.info(
            "g4f_selected_tested_model",
            extra={
                "provider": best.get("provider"),
                "model": best.get("model"),
                "ms": best.get("ms"),
            },
        )
        return best.get("provider"), best.get("model")
    except Exception as e:
        logger.warning("g4f_load_tested_models_failed", extra={"error": str(e)})
        return None
