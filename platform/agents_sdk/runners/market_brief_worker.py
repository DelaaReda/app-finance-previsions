"""Bounded worker scaffold for the brief-generation flow."""

from __future__ import annotations

from typing import Any

from ..adapters.workboard_adapter import context_from_request, evidence_from_run_result
from ..availability import require_agents_sdk
from ..schemas import WorkerEvidence, WorkerRunRequest
from ..tools import build_market_brief_tools


def build_market_brief_worker(model: str | None = None) -> Any:
    sdk = require_agents_sdk()
    Agent = sdk["Agent"]
    function_tool = sdk["function_tool"]
    handoff = sdk["handoff"]
    prompt_prefix = sdk["RECOMMENDED_PROMPT_PREFIX"]

    tools = build_market_brief_tools(function_tool)

    risk_agent = Agent(
        name="Brief Risk Prioritizer",
        instructions=(
            f"{prompt_prefix}\n"
            "You specialize in ranking risks for one bounded brief-generation task. "
            "Prefer evidence already present in the prompt and tool outputs. "
            "Return only compact planner-safe reasoning."
        ),
        model=model,
    )

    synthesis_agent = Agent(
        name="Brief Evidence Synthesizer",
        instructions=(
            f"{prompt_prefix}\n"
            "You synthesize one planner-compatible delivery payload. "
            "End with canonical evidence fields and keep verify, architecture_check, "
            "and vision_alignment in key-value format."
        ),
        model=model,
        tools=tools,
        output_type=WorkerEvidence,
    )

    return Agent(
        name="BATCH-25 Brief Delivery Manager",
        instructions=(
            f"{prompt_prefix}\n"
            "You are a bounded worker for the brief-generation flow. "
            "Use handoffs only inside this run. "
            "Do not invent runtime state outside the provided context. "
            "Always finish with planner-compatible evidence."
        ),
        model=model,
        handoffs=[
            handoff(risk_agent, tool_name_override="delegate_risk_prioritization"),
            handoff(synthesis_agent, tool_name_override="delegate_brief_synthesis"),
        ],
        tools=tools,
        output_type=WorkerEvidence,
    )


def run_market_brief_worker(request: WorkerRunRequest) -> WorkerEvidence:
    sdk = require_agents_sdk()
    Runner = sdk["Runner"]
    context = context_from_request(request)
    agent = build_market_brief_worker(model=request.model)
    prompt = (
        "Execute one bounded brief-generation worker run.\n"
        f"Context: {context.to_prompt_block()}\n"
        f"Objective: {request.objective}\n"
        "Return planner-compatible evidence."
    )
    result = Runner.run_sync(agent, prompt, context=context)
    return evidence_from_run_result(result)
