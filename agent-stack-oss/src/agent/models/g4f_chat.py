from __future__ import annotations

from typing import Any, Dict, List, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.callbacks import CallbackManagerForLLMRun
from pydantic import Field

_g4f_import_error: Optional[Exception] = None
try:  # pragma: no cover - optional dependency at runtime
    from g4f.client import Client as G4FClient  # type: ignore[import-untyped]
except Exception as exc:  # noqa: BLE001
    G4FClient = None  # type: ignore
    _g4f_import_error = exc
else:
    _g4f_import_error = None


def _convert_role(message: BaseMessage) -> Dict[str, str]:
    role_map = {
        "human": "user",
        "ai": "assistant",
        "system": "system",
        "function": "function",
        "tool": "tool",
    }
    role = role_map.get(message.type, "user")
    content = message.content
    if isinstance(content, list):
        content = " ".join(str(part) for part in content)
    return {"role": role, "content": str(content)}


class G4FChat(BaseChatModel):
    """LangChain chat wrapper around g4f with model fallbacks and tuning."""

    model: str = Field(default="gpt-4o-mini")
    models: Optional[List[str]] = Field(
        default=None, description="Ordered list of model candidates to try"
    )
    temperature: float = Field(default=0.1)
    max_tokens: int = Field(default=2048)
    timeout: int = Field(default=60)
    retries: int = Field(default=1)

    @property
    def _llm_type(self) -> str:
        return "g4f"

    def _call_with_client(self, messages: List[Dict[str, str]]) -> str:
        if G4FClient is None:
            raise RuntimeError(
                "g4f library is not available. Install it via `pip install g4f` "
                f"(import error: {_g4f_import_error})"
            )
        client = G4FClient()
        candidates = self.models or [self.model]
        last_err: Optional[Exception] = None
        for model in candidates:
            for _ in range(max(1, self.retries)):
                try:
                    response = client.chat.completions.create(
                        model=model,
                        messages=messages,
                        temperature=self.temperature,
                        max_tokens=self.max_tokens,
                        timeout=self.timeout,
                    )
                    choice = response.choices[0]
                    return choice.message.content
                except Exception as e:  # noqa: BLE001
                    last_err = e
                    continue
        raise RuntimeError(f"All g4f candidates failed: {last_err}")

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        payload = [_convert_role(m) for m in messages]
        if stop:
            # g4f does not support stop sequences; best effort by appending instruction
            payload.append({"role": "system", "content": f"Stop when encountering any of: {stop}"})
        content = self._call_with_client(payload)
        ai_message = AIMessage(content=content)
        generation = ChatGeneration(message=ai_message)
        return ChatResult(generations=[generation])
