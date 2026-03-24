"""Lazy import helpers for the OpenAI Agents SDK."""

from __future__ import annotations

from typing import Any


def require_agents_sdk() -> dict[str, Any]:
    """Load the Agents SDK lazily so the scaffold stays inert until used."""
    try:
        from agents import Agent, Runner, function_tool, handoff
        from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
    except Exception as exc:  # pragma: no cover - runtime-only path
        raise RuntimeError(
            "openai-agents is required for platform.agents_sdk runners. "
            "Install it with `pip install openai-agents` before wiring this scaffold."
        ) from exc

    return {
        "Agent": Agent,
        "Runner": Runner,
        "function_tool": function_tool,
        "handoff": handoff,
        "RECOMMENDED_PROMPT_PREFIX": RECOMMENDED_PROMPT_PREFIX,
    }
