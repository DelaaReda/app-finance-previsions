#!/usr/bin/env python3
"""
Enhanced Agent Runner - Extended capabilities for architecture planning, QA, and sprint planning.

Usage:
    python -m src.agent.enhanced_run --goal "Prepare architecture documentation for G4F integration" --mode planning
    python -m src.agent.enhanced_run --goal "Generate sprint plan for news integration" --mode sprint
    python -m src.agent.enhanced_run --goal "Implement news feed with scoring" --mode full
"""

from __future__ import annotations
import argparse
import json
import traceback
from .graph import build_graph
from .memory.episodic_store import EpisodicMemory
from .nodes.g4f_model_selector import refresh_working_models_if_needed


def main():
    # Silence noisy Pydantic warnings to keep CLI output clean
    try:
        import warnings
        from pydantic._internal._generate_schema import UnsupportedFieldAttributeWarning
        warnings.filterwarnings("ignore", category=UnsupportedFieldAttributeWarning)
    except Exception:
        pass
    
    ap = argparse.ArgumentParser(description="Run Enhanced OSS Agent (LangGraph)")
    ap.add_argument("--goal", required=True, help="Objective for the agent")
    ap.add_argument("--mode", choices=["planning", "sprint", "qa", "full"], default="full",
                    help="Execution mode: planning (arch/docs), sprint (sprint planning), qa (quality assurance), full (everything)")
    ap.add_argument("--complexity", choices=["simple", "medium", "complex"], default="medium",
                    help="Task complexity for model selection")
    ap.add_argument("--verbose", action="store_true", help="Stream node-by-node execution logs")
    ap.add_argument("--no-model-refresh", action="store_true", help="Skip refreshing G4F working models")
    
    args = ap.parse_args()

    # Refresh working models if needed
    if not args.no_model_refresh:
        try:
            print("[agent] Checking for updated G4F models...")
            refresh_working_models_if_needed(limit=8)
        except Exception as e:
            if args.verbose:
                print(f"[agent] Warning: Failed to refresh models: {e}")

    g = build_graph().compile()
    state = {
        "goal": args.goal,
        "plan": {},
        "context_docs": [],
        "patch": {},
        "tests": {},
        "result": {},
        "architecture_plan": None,
        "sprint_plan": None,
        "priorities": None,
        "recent_commits": None,
    }
    
    out = None
    try:
        if args.verbose:
            print(f"[agent] starting run: goal=\"{args.goal}\" mode={args.mode}")
            last = None
            for step in g.stream(state):
                for node, payload in step.items():
                    keys = list(payload.keys())
                    print(f"[agent] node={node} keys={keys}")
                    if "plan" in payload:
                        print(f"[agent] plan: {json.dumps(payload['plan'], ensure_ascii=False)[:500]}")
                    if "context_docs" in payload:
                        print(f"[agent] retrieved docs: {len(payload['context_docs'])}")
                    if "architecture_plan" in payload and payload["architecture_plan"]:
                        arch = payload["architecture_plan"]
                        if "error" not in arch:
                            print(f"[agent] architecture planned: {len(str(arch))} chars")
                    if "priorities" in payload and payload["priorities"]:
                        print(f"[agent] priorities defined: {len(payload['priorities'])} items")
                    if "sprint_plan" in payload and payload["sprint_plan"]:
                        sprint = payload["sprint_plan"]
                        if "error" not in sprint:
                            print(f"[agent] sprint planned: {len(str(sprint))} chars")
                    if "patch" in payload:
                        diff = payload["patch"].get("diff", "")
                        print(f"[agent] patch: {len(diff.splitlines())} lines")
                    if "tests" in payload:
                        tests = payload["tests"]
                        summary = {k: v.get("ok") for k, v in tests.items() if isinstance(v, dict)}
                        print(f"[agent] tests: {summary}")
                    if "result" in payload:
                        print(f"[agent] result: {payload['result']}")
                last = step
            # After streaming, get final combined state
            out = last[list(last.keys())[-1]] if last else state
        else:
            out = g.invoke(state)
    except Exception:
        if args.verbose:
            traceback.print_exc()
        raise
    finally:
        if out is None:
            out = state
        EpisodicMemory().log(
            goal=args.goal,
            plan=out.get("plan", {}),
            diff=out.get("patch", {}).get("diff", ""),
            tests=out.get("tests", {}),
            result=out.get("result", {}),
            notes=f"run via CLI, mode={args.mode}",
        )
        print(json.dumps(out.get("result", {}), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()