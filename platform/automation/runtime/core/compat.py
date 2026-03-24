from __future__ import annotations

from copy import deepcopy
from typing import Any

try:  # pragma: no cover - exercised on dependency-enabled runtimes
    from pydantic import BaseModel as PydanticBaseModel
    from pydantic import Field, ConfigDict

    BaseModel = PydanticBaseModel
    PYDANTIC_ENABLED = True
except Exception:  # pragma: no cover - lightweight fallback for shells/tests
    PYDANTIC_ENABLED = False
    ConfigDict = dict

    def Field(*, default: Any = None, default_factory: Any = None, **_: Any) -> Any:
        if default_factory is not None:
            return default_factory()
        return default

    class BaseModel:
        model_config: dict[str, Any] = {}

        def __init__(self, **data: Any) -> None:
            annotations: dict[str, Any] = {}
            for base in reversed(self.__class__.__mro__):
                annotations.update(getattr(base, "__annotations__", {}))
            extra_behavior = {}
            if isinstance(getattr(self, "model_config", {}), dict):
                extra_behavior = getattr(self, "model_config", {})
            extras = {key: value for key, value in data.items() if key not in annotations}
            if extras and extra_behavior.get("extra") != "allow":
                unknown = ", ".join(sorted(extras))
                raise TypeError(f"{self.__class__.__name__} got unexpected fields: {unknown}")
            for field_name in annotations:
                if field_name in data:
                    value = data[field_name]
                elif hasattr(self.__class__, field_name):
                    value = deepcopy(getattr(self.__class__, field_name))
                else:
                    value = None
                setattr(self, field_name, value)
            for field_name, value in extras.items():
                setattr(self, field_name, value)

        @classmethod
        def model_validate(cls, payload: Any) -> "BaseModel":
            if isinstance(payload, cls):
                return payload
            if not isinstance(payload, dict):
                raise TypeError(f"{cls.__name__}.model_validate expects a dict payload")
            return cls(**payload)

        def model_dump(self, **_: Any) -> dict[str, Any]:
            annotations: dict[str, Any] = {}
            for base in reversed(self.__class__.__mro__):
                annotations.update(getattr(base, "__annotations__", {}))
            return {name: _dump_value(getattr(self, name, None)) for name in annotations}


def _dump_value(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump()
    if isinstance(value, list):
        return [_dump_value(item) for item in value]
    if isinstance(value, tuple):
        return [_dump_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _dump_value(item) for key, item in value.items()}
    return value
