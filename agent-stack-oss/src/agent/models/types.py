
from __future__ import annotations
from typing import TypedDict, Literal
Role = Literal["system","user","assistant"]
class ChatMessage(TypedDict):
    role: Role
    content: str
