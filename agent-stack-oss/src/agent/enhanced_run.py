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
import time
from datetime import datetime, timezone
from .graph import build_graph
from .memory.episodic_store import EpisodicMemory
from .nodes.g4f_model_selector import refresh_working_models_if_needed
from .monitoring_system import EnhancedMentor


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
    ap.add_argument("--mentor", action="store_true", help="Enable mentor monitoring and feedback")
    
    args = ap.parse_args()

    # Create mentor if requested
    mentor = None
    if args.mentor:
        mentor = EnhancedMentor("/Users/venom/Documents/analyse-financiere/agent-stack-oss")
    
    # Generate a session ID
    session_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    
    # Refresh working models if needed
    if not args.no_model_refresh:
        try:
            print("[agent] Checking for updated G4F models...")
            refresh_working_models_if_needed(limit=8)
        except Exception as e:
            if args.verbose:
                print(f"[agent] Warning: Failed to refresh models: {e}")

    # Start mentoring session if enabled
    if mentor:
        mentor.monitor_session(session_id, args.goal, args.mode, args.complexity)
        print(f"[mentor] 🔍 Début de la session de mentorat: {session_id}")

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
        "session_id": session_id,
        "start_time": time.time(),
    }
    
    out = None
    success = False
    
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
        
        success = True
    except Exception:
        if args.verbose:
            traceback.print_exc()
        raise
    finally:
        if out is None:
            out = state
        
        # Calculate duration
        duration = time.time() - state["start_time"]
        
        # Add metrics to result
        result = out.get("result", {})
        result["duration"] = duration
        result["session_id"] = session_id
        result["success"] = success
        result["error_messages"] = result.get("error_messages", [])  # Ensure it exists
        result["output_messages"] = result.get("output_messages", [])  # Ensure it exists
        result["goal"] = state.get("goal", "")
        result["mode"] = args.mode
        result["complexity"] = args.complexity
        out["result"] = result
        
        # Log to episodic memory
        EpisodicMemory().log(
            goal=args.goal,
            plan=out.get("plan", {}),
            diff=out.get("patch", {}).get("diff", ""),
            tests=out.get("tests", {}),
            result=result,
            notes=f"run via CLI, mode={args.mode}",
        )
        
        # End mentoring session if enabled
        if mentor:
            try:
                mentor_report = mentor.end_session(success)
                print("\n" + "="*60)
                print("MENTORSHIP REPORT")
                print("="*60)
                print(mentor_report)
                print("="*60)
            except Exception as e:
                print(f"[mentor] Error in end_session: {e}")
        
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()