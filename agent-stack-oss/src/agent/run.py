
from __future__ import annotations
import argparse
from .graph import build_graph
from .memory.episodic_store import EpisodicMemory
def main():
    ap = argparse.ArgumentParser(description="Run OSS Agent (LangGraph)")
    ap.add_argument("--goal", required=True, help="Objective for the agent (e.g., refactor News page)")
    args = ap.parse_args()
    g = build_graph().compile()
    state = {"goal": args.goal, "plan": {}, "context_docs": [], "patch": {}, "tests": {}, "result": {}}
    out = g.invoke(state)
    EpisodicMemory().log(goal=args.goal, plan=out.get("plan",{}), diff=out.get("patch",{}).get("diff",""),
                         tests=out.get("tests",{}), result=out.get("result",{}), notes="run via CLI")
    print(out.get("result",{}))
if __name__ == "__main__":
    main()
