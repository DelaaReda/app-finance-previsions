
from __future__ import annotations
import glob, pathlib
from ..config import AgentConfig
def _allowed(path: str, cfg: AgentConfig) -> bool:
    p = pathlib.Path(path)
    return any(p.match(g) for g in cfg.safe_paths)
def list_files(pattern: str, cfg: AgentConfig | None = None) -> list[str]:
    cfg = cfg or AgentConfig()
    return [p for p in glob.glob(pattern, recursive=True) if _allowed(p, cfg)]
def read_file(path: str, cfg: AgentConfig | None = None) -> str:
    cfg = cfg or AgentConfig()
    if not _allowed(path, cfg): raise ValueError("Path not allowed")
    return pathlib.Path(path).read_text(encoding="utf-8")
def write_file(path: str, content: str, cfg: AgentConfig | None = None) -> str:
    cfg = cfg or AgentConfig()
    if not _allowed(path, cfg): raise ValueError("Path not allowed")
    p = pathlib.Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return "ok"
