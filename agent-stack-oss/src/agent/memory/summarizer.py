
from __future__ import annotations
from ..models.router import get_llm, as_messages
from ..config import AgentConfig
def summarize_long(messages: list[dict], keep_last: int = 4, cfg: AgentConfig | None = None) -> list[dict]:
    if len(messages) <= keep_last: return messages
    head, tail = messages[:-keep_last], messages[-keep_last:]
    llm = get_llm("summarize", cfg)
    memo = llm.invoke(as_messages(f"Résume fidèlement ces messages pour mémoire long-terme: {head}"))
    return [{"role":"system","content":f"[MEMO] {memo.content}"}] + tail
