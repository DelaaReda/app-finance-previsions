
from __future__ import annotations
import argparse
import json
import traceback
import time
from datetime import datetime, timezone
from .graph import build_graph
from .memory.episodic_store import EpisodicMemory
from .monitoring_system import EnhancedMentor


def main():
    # Silence noisy Pydantic warnings to keep CLI output clean
    try:
        import warnings
        from pydantic._internal._generate_schema import UnsupportedFieldAttributeWarning
        warnings.filterwarnings("ignore", category=UnsupportedFieldAttributeWarning)
    except Exception:
        pass
    
    ap = argparse.ArgumentParser(description="Run OSS Agent (LangGraph)")
    ap.add_argument("--goal", required=True, help="Objective for the agent (e.g., refactor News page)")
    ap.add_argument("--verbose", action="store_true", help="Stream node-by-node execution logs")
    ap.add_argument("--mentor", action="store_true", help="Enable mentor monitoring and feedback")
    args = ap.parse_args()

    # Create mentor if requested
    mentor = None
    if args.mentor:
        mentor = EnhancedMentor("/Users/venom/Documents/analyse-financiere/agent-stack-oss")
    
    # Generate a session ID
    session_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    
    # Start mentoring session if enabled
    if mentor:
        mentor.monitor_session(session_id, args.goal)
        print(f"[mentor] 🔍 Début de la session de mentorat: {session_id}")

    g = build_graph().compile()
    state = {
        "goal": args.goal,
        "plan": {},
        "context_docs": [],
        "patch": {},
        "tests": {},
        "result": {},
        "session_id": session_id,
        "start_time": time.time(),
    }
    
    out = None
    success = False
    
    try:
        if args.verbose:
            print(f"[agent] starting run: goal=\"{args.goal}\"")
            last = None
            for step in g.stream(state):
                for node, payload in step.items():
                    keys = list(payload.keys())
                    print(f"[agent] node={node} keys={keys}")
                    if "plan" in payload:
                        print(f"[agent] plan: {json.dumps(payload['plan'], ensure_ascii=False)[:500]}")
                    if "context_docs" in payload:
                        print(f"[agent] retrieved docs: {len(payload['context_docs'])}")
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
        out["result"] = result
        
        # Log to episodic memory
        EpisodicMemory().log(
            goal=args.goal,
            plan=out.get("plan", {}),
            diff=out.get("patch", {}).get("diff", ""),
            tests=out.get("tests", {}),
            result=result,
            notes="run via CLI",
        )
        
        # End mentoring session if enabled
        if mentor:
            mentor_report = mentor.end_session(success)
            print("\n" + "="*60)
            print("MENTORSHIP REPORT")
            print("="*60)
            print(mentor_report)
            print("="*60)
        
        print(result)
if __name__ == "__main__":
    main()
