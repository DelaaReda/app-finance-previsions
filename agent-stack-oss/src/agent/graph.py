
from __future__ import annotations
from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from .models.router import get_llm, as_messages
from .tools.git_tools import ensure_safe_branch, apply_patch_text, commit_all, restore_worktree
from .tools.ci_tools import run_pytests, run_linters, build_webapp
from .tools.rag_tools import query_index
class AgentState(TypedDict):
    goal: str
    plan: dict
    context_docs: List[str]
    patch: dict
    tests: dict
    result: dict
def node_plan(state: AgentState) -> AgentState:
    llm = get_llm("plan")
    prompt = (
        f"Plan minimal et safe pour l'objectif: {state['goal']}\n"
        "Reponds en JSON avec {\"steps\":[...], \"files\":[...]}."
    )
    out = llm.invoke(as_messages(prompt))
    plan = {"steps": [], "files": []}
    try:
        import json; plan = json.loads(out.content)
    except Exception: pass
    state["plan"] = plan; return state
def node_retrieve(state: AgentState) -> AgentState:
    hits = query_index(state["goal"], topk=5, data_dir="docs")
    state["context_docs"] = hits
    return state
def node_patch(state: AgentState) -> AgentState:
    llm = get_llm("code")
    prompt = ("Tu es un agent d'edition de code. Reponds STRICTEMENT en JSON: "
              "{\"diff\":\"<unified patch>\", \"touched\":[...]}.\n"
              f"Objectif: {state['goal']}\nContexte: {state.get('context_docs', [])}\n"
              f"Fichiers ciblés: {state.get('plan',{}).get('files', [])}")
    out = llm.invoke(as_messages(prompt))
    patch = {"diff": "", "touched": []}
    try:
        import json; patch = json.loads(out.content)
    except Exception: pass
    ensure_safe_branch()
    ok = apply_patch_text(patch.get("diff",""))
    if not ok:
        state["result"] = {"ok": False, "error": "apply failed"}; return state
    state["patch"] = patch; return state
def node_qa(state: AgentState) -> AgentState:
    lin = run_linters()
    pyt = run_pytests()
    web = build_webapp()
    tests = {"linters": lin, "pytest": pyt, "webapp": web}
    state["tests"] = tests
    if not (lin.get("ok") and pyt.get("ok") and web.get("ok")):
        restore_worktree()
        state["result"] = {"ok": False, "error": "qa failed", "tests": tests}
    return state
def node_commit(state: AgentState) -> AgentState:
    if state.get("result",{}).get("ok") is False:
        return state
    ok = commit_all(f"feat(agent): {state['goal'][:80]}")
    state["result"] = {"ok": ok, "committed": ok}
    return state
def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)
    graph.add_node("plan", node_plan)
    graph.add_node("retrieve", node_retrieve)
    graph.add_node("patch", node_patch)
    graph.add_node("qa", node_qa)
    graph.add_node("commit", node_commit)
    graph.set_entry_point("plan")
    graph.add_edge("plan", "retrieve")
    graph.add_edge("retrieve", "patch")
    graph.add_edge("patch", "qa")
    graph.add_edge("qa", "commit")
    graph.add_edge("commit", END)
    return graph
