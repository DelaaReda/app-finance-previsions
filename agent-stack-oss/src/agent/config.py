
from __future__ import annotations
import os
from dataclasses import dataclass
from dotenv import load_dotenv
load_dotenv(override=True)
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
    safe_paths: list[str] = [p.strip() for p in os.getenv("SAFE_PATHS", "src/**/*.py,webapp/src/**/*.ts,webapp/src/**/*.tsx,docs/**/*.md").split(",")]
