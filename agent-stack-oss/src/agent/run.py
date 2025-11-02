
from __future__ import annotations
import argparse
import json
import traceback
from .graph import build_graph
from .memory.episodic_store import EpisodicMemory
def main():
    ap = argparse.ArgumentParser(description="Run OSS Agent (LangGraph)")
    ap.add_argument("--goal", required=True, help="Objective for the agent (e.g., refactor News page)")
    ap.add_argument("--verbose", action="store_true", help="Stream node-by-node execution logs")
    args = ap.parse_args()

    g = build_graph().compile()
    state = {
        "goal": args.goal,
        "plan": {},
        "context_docs": [],
        "patch": {},
        "tests": {},
        "result": {},
    }
    out = None
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
            notes="run via CLI",
        )
        print(out.get("result", {}))
if __name__ == "__main__":
    main()
