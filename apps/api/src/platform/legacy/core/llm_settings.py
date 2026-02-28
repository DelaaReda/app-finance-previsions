from __future__ import annotations

import os
import json
from pathlib import Path
from dataclasses import dataclass
from functools import lru_cache
from typing import List

try:
    from .env_loader import ensure_env_loaded
except Exception:  # pragma: no cover - env loader optional during import
    ensure_env_loaded = None

if ensure_env_loaded is not None:
    try:
        ensure_env_loaded()
    except Exception:
        pass


DEFAULT_G4F_PROVIDER = "DeepInfra"
DEFAULT_G4F_MODEL = "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"


@dataclass(frozen=True)
class LLMSettings:
    """Centralized LLM defaults used by backend services."""

    g4f_provider: str
    g4f_model: str
    llm_model: str
    llm_summary_model: str
    llm_judge_model: str
    llm_client_models: List[str]
    llm_mode_default: str
    llm_dev_models: List[str]
    llm_fastest_models: List[str]
    llm_dev_timeout_seconds: int
    llm_fastest_timeout_seconds: int
    llm_best_timeout_seconds: int
    llm_dev_max_attempts: int
    llm_fastest_max_attempts: int
    llm_best_max_attempts: int
    econ_agent_mode: str
    econ_agent_models: List[str]


def _env_value(*names: str, default: str = "") -> str:
    for name in names:
        value = os.getenv(name)
        if value is not None and str(value).strip():
            return str(value).strip()
    return default


def _load_model_settings_file() -> dict:
    """Load optional shared JSON config for LLM defaults."""
    custom_path = os.getenv("LLM_SETTINGS_FILE")
    backend_dir = Path(__file__).resolve().parents[2]
    repo_root = backend_dir.parent
    candidate_files = [
        Path(custom_path) if custom_path else None,
        backend_dir / "config" / "llm-models.json",
        repo_root.parent / "configs" / "llm-models.json",
    ]
    for path in candidate_files:
        if path is None or not path.is_file():
            continue
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except Exception:
            continue
    return {}


def _coalesce(value, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, str):
        text = value.strip()
        if text:
            return text
    return default


def _split_csv(value: str) -> List[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _to_int(value: object, default: int) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except Exception:
        return int(default)


def _default_g4f_model() -> str:
    cfg = _load_model_settings_file()
    cfg_g4f = cfg.get("g4f", {}) if isinstance(cfg.get("g4f"), dict) else {}
    cfg_g4f_model = cfg_g4f.get("model")
    return _env_value(
        "G4F_MODEL",
        "LLM_DEFAULT_MODEL",
        "LLM_MODEL",
        "LLM_JUDGE_MODEL",
        default=_coalesce(cfg_g4f_model, DEFAULT_G4F_MODEL),
    )


@lru_cache(maxsize=1)
def get_llm_settings() -> LLMSettings:
    """Return a canonical model configuration snapshot."""
    cfg = _load_model_settings_file()
    cfg_g4f = cfg.get("g4f", {}) if isinstance(cfg.get("g4f"), dict) else {}
    cfg_llm_model = cfg.get("llm_model")
    cfg_summary_model = cfg.get("llm_summary_model")
    cfg_judge_model = cfg.get("llm_judge_model")
    cfg_mode_default = cfg.get("llm_mode_default")
    cfg_dev_models = cfg.get("llm_dev_models")
    cfg_fastest_models = cfg.get("llm_fastest_models")
    cfg_dev_timeout = cfg.get("llm_dev_timeout_seconds")
    cfg_fastest_timeout = cfg.get("llm_fastest_timeout_seconds")
    cfg_best_timeout = cfg.get("llm_best_timeout_seconds")
    cfg_dev_attempts = cfg.get("llm_dev_max_attempts")
    cfg_fastest_attempts = cfg.get("llm_fastest_max_attempts")
    cfg_best_attempts = cfg.get("llm_best_max_attempts")
    cfg_econ_mode = cfg.get("econ_agent_mode")
    cfg_econ_models = cfg.get("econ_agent_models")

    g4f_provider = _env_value(
        "LLM_G4F_PROVIDER",
        "G4F_PROVIDER",
        default=_coalesce(cfg_g4f.get("provider"), DEFAULT_G4F_PROVIDER),
    )
    g4f_model = _default_g4f_model()
    llm_model = _env_value(
        "LLM_MODEL",
        "LLM_DEFAULT_MODEL",
        default=_coalesce(cfg_llm_model, g4f_model),
    )
    llm_summary_model = _env_value(
        "LLM_SUMMARY_MODEL",
        "G4F_DEFAULT_MODEL",
        default=_coalesce(cfg_summary_model, llm_model),
    )
    llm_judge_model = _env_value(
        "LLM_JUDGE_MODEL",
        "LLM_MODEL",
        "LLM_DEFAULT_MODEL",
        default=_coalesce(cfg_judge_model, g4f_model),
    )
    llm_client_models = [
        llm_model,
        g4f_model,
        llm_summary_model,
    ]
    llm_mode_default = _env_value("LLM_MODEL_MODE", default=_coalesce(cfg_mode_default, "best")).lower().strip() or "best"
    llm_dev_models = _split_csv(_env_value("LLM_DEV_MODELS", default=""))
    if not llm_dev_models and isinstance(cfg_dev_models, str):
        llm_dev_models = _split_csv(cfg_dev_models)
    elif not llm_dev_models and isinstance(cfg_dev_models, list):
        llm_dev_models = [str(x).strip() for x in cfg_dev_models if str(x).strip()]
    llm_fastest_models = _split_csv(_env_value("LLM_FASTEST_MODELS", default=""))
    if not llm_fastest_models and isinstance(cfg_fastest_models, str):
        llm_fastest_models = _split_csv(cfg_fastest_models)
    elif not llm_fastest_models and isinstance(cfg_fastest_models, list):
        llm_fastest_models = [str(x).strip() for x in cfg_fastest_models if str(x).strip()]
    llm_dev_timeout_seconds = _to_int(
        _env_value("LLM_DEV_TIMEOUT_SECONDS", default=str(_to_int(cfg_dev_timeout, 20))),
        20,
    )
    llm_fastest_timeout_seconds = _to_int(
        _env_value("LLM_FASTEST_TIMEOUT_SECONDS", default=str(_to_int(cfg_fastest_timeout, 12))),
        12,
    )
    llm_best_timeout_seconds = _to_int(
        _env_value("LLM_BEST_TIMEOUT_SECONDS", default=str(_to_int(cfg_best_timeout, 60))),
        60,
    )
    llm_dev_max_attempts = _to_int(
        _env_value("LLM_DEV_MAX_ATTEMPTS", default=str(_to_int(cfg_dev_attempts, 2))),
        2,
    )
    llm_fastest_max_attempts = _to_int(
        _env_value("LLM_FASTEST_MAX_ATTEMPTS", default=str(_to_int(cfg_fastest_attempts, 2))),
        2,
    )
    llm_best_max_attempts = _to_int(
        _env_value("LLM_BEST_MAX_ATTEMPTS", default=str(_to_int(cfg_best_attempts, 3))),
        3,
    )
    econ_agent_mode = _env_value("ECON_AGENT_MODE", default="prod").lower().strip() or _coalesce(cfg_econ_mode, "prod")
    econ_agent_models = _split_csv(_env_value("ECON_AGENT_MODELS", default=""))
    if not econ_agent_models and isinstance(cfg_econ_models, str):
        econ_agent_models = _split_csv(cfg_econ_models)
    elif not econ_agent_models and isinstance(cfg_econ_models, list):
        econ_agent_models = [str(x).strip() for x in cfg_econ_models if str(x).strip()]

    return LLMSettings(
        g4f_provider=g4f_provider,
        g4f_model=g4f_model,
        llm_model=llm_model,
        llm_summary_model=llm_summary_model,
        llm_judge_model=llm_judge_model,
        llm_client_models=llm_client_models,
        llm_mode_default=llm_mode_default,
        llm_dev_models=llm_dev_models,
        llm_fastest_models=llm_fastest_models,
        llm_dev_timeout_seconds=llm_dev_timeout_seconds,
        llm_fastest_timeout_seconds=llm_fastest_timeout_seconds,
        llm_best_timeout_seconds=llm_best_timeout_seconds,
        llm_dev_max_attempts=llm_dev_max_attempts,
        llm_fastest_max_attempts=llm_fastest_max_attempts,
        llm_best_max_attempts=llm_best_max_attempts,
        econ_agent_mode=econ_agent_mode,
        econ_agent_models=econ_agent_models,
    )
