
from __future__ import annotations
import os
from dataclasses import dataclass, field
from dotenv import load_dotenv
load_dotenv(override=True)


def _default_safe_paths() -> list[str]:
    raw = os.getenv(
        "SAFE_PATHS",
        "src/**/*.py,webapp/src/**/*.ts,webapp/src/**/*.tsx,docs/**/*.md",
    )
    return [p.strip() for p in raw.split(",") if p.strip()]

@dataclass
class AgentConfig:
    provider: str = os.getenv("LLM_PROVIDER", "openai")
    model: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    openai_base_url: str | None = os.getenv("OPENAI_BASE_URL")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.1")
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    vector_path: str = os.getenv("VECTOR_PATH", "./data/agent/vector")
    duckdb_path: str = os.getenv("DUCKDB_PATH", "./data/agent/episodic.duckdb")
    safe_branch_prefix: str = os.getenv("SAFE_BRANCH_PREFIX", "feature/")
    safe_paths: list[str] = field(default_factory=_default_safe_paths)
    # G4F advanced options
    g4f_models: list[str] = field(
        default_factory=lambda: [
            m.strip()
            for m in os.getenv(
                "G4F_MODELS",
                ",".join(
                    [
                        "deepseek-ai/DeepSeek-R1-0528",
                        "deepseek-ai/DeepSeek-V3-0324-Turbo",
                        "deepseek-ai/DeepSeek-V3",
                        "Qwen/Qwen3-235B-A22B-Thinking-2507",
                        "Qwen/Qwen3-235B-A22B-Instruct-2507",
                        "Qwen/Qwen3-Next-80B-A3B-Instruct",
                        "zai-org/GLM-4.5",
                        "meta-llama/Llama-3.3-70B-Instruct-Turbo",
                        "openai/gpt-oss-120b",
                    ]
                ),
            ).split(",")
            if m.strip()
        ]
    )
    g4f_max_tokens: int = int(os.getenv("G4F_MAX_TOKENS", "2048"))
    g4f_temperature: float = float(os.getenv("G4F_TEMPERATURE", "0.2"))
    g4f_timeout: int = int(os.getenv("G4F_TIMEOUT", "60"))
    g4f_retries: int = int(os.getenv("G4F_RETRIES", "1"))
