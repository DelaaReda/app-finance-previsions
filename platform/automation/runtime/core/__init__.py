"""Canonical shared runtime-core package."""

from .availability import build_runtime_capabilities
from .compat import BaseModel, ConfigDict, Field, PYDANTIC_ENABLED
from .contracts import (
    CapabilityResult,
    CapabilityTask,
    DeliveryProof,
    OrchestrationEvent,
    PlannerDecision,
    PlannerGraphState,
    RuntimeCheck,
    ScrumAdvice,
)

__all__ = [
    "BaseModel",
    "CapabilityResult",
    "CapabilityTask",
    "ConfigDict",
    "DeliveryProof",
    "Field",
    "OrchestrationEvent",
    "PYDANTIC_ENABLED",
    "PlannerDecision",
    "PlannerGraphState",
    "RuntimeCheck",
    "ScrumAdvice",
    "build_runtime_capabilities",
]
