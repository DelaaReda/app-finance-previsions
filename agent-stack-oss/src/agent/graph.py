
from __future__ import annotations
from typing import TypedDict, List, Optional
from langgraph.graph import StateGraph, END
from .models.router import get_llm, as_messages
from .tools.git_tools import ensure_safe_branch, apply_patch_text, commit_all, restore_worktree
from .tools.ci_tools import run_pytests, run_linters, build_webapp
from .tools.rag_tools import query_index
from .config import AgentConfig
from .tools.fs_tools import write_file
class AgentState(TypedDict):
    goal: str
    plan: dict
    context_docs: List[str]
    patch: dict
    tests: dict
    result: dict
    retrieval_error: Optional[str]
def node_plan(state: AgentState) -> AgentState:
    llm = get_llm("plan")
    prompt = (
        f"Plan minimal et safe pour l'objectif: {state['goal']}\n"
        "Reponds en JSON avec {\"steps\":[...], \"files\":[...]}."
    )
    out = llm.invoke(as_messages(prompt))
    plan: dict = {"steps": [], "files": []}
    try:
        import json
        raw = getattr(out, "content", "")
        content = raw if isinstance(raw, str) else ""
        plan = json.loads(content)
    except Exception:
        plan = {"steps": [], "files": []}
    # Infer files from goal if missing (e.g., "docs/dev/ARCHITECTURE_INTEGRATION_PLAN.md")
    if not plan.get("files") and isinstance(state.get("goal"), str):
        import re
        m = re.search(r"(docs/[\w\-/]+\.md)", state["goal"])  # only allow under docs/
        if m:
            plan["files"] = [m.group(1)]
    state["plan"] = plan
    return state
def node_retrieve(state: AgentState) -> AgentState:
    from pathlib import Path
    topk = 5
    results: list[str] = []
    # 1) Agent docs
    try:
        hits_agent = query_index(state["goal"], topk=topk, data_dir="docs") or []
        results.extend(hits_agent)
    except Exception as e:
        state["retrieval_error"] = f"agent_docs: {e}"
    # 2) Root repo docs
    try:
        root_docs = str((Path.cwd() / ".." / "docs").resolve())
        hits_root = query_index(state["goal"], topk=topk, data_dir=root_docs) or []
        if hits_root:
            seen = set(results)
            for t in hits_root:
                if t not in seen:
                    results.append(t)
                    seen.add(t)
    except Exception as e:
        prev = state.get("retrieval_error")
        state["retrieval_error"] = (prev + f"; root_docs: {e}") if prev else f"root_docs: {e}"
    state["context_docs"] = results[:topk]
    return state
def node_patch(state: AgentState) -> AgentState:
    cfg = AgentConfig()
    llm = get_llm("code")
    target_files = state.get('plan',{}).get('files', [])
    if cfg.allow_direct_write:
        prompt = (
            "Tu es un agent d'édition de code. Réponds STRICTEMENT en JSON: "
            "{\"files\":[{\"path\":\"<relpath>\",\"content\":\"<full file content>\"}]}\n"
            f"Objectif: {state['goal']}\n"
            f"Contexte (docs): {state.get('context_docs', [])[:2]}\n"
            f"Fichiers ciblés (SAFE_PATHS): {target_files}\n"
            "Règles: chemins relatifs, pas de balises de code, pas de diff; inclure le contenu ENTIER des fichiers."
        )
    else:
        prompt = (
            "Tu es un agent d'édition de code. Réponds STRICTEMENT en JSON: "
            "{\"diff\":\"<unified patch>\", \"touched\":[...]}.\n"
            "Règles pour diff: format patch unifié git, chemins relatifs à la racine du repo, pas de commentaire.\n"
            "Exemple: \n"
            "--- a/docs/dev/FILE.md\n"
            "+++ b/docs/dev/FILE.md\n"
            "@@\n-ancienne ligne\n+nouvelle ligne\n\n"
            f"Objectif: {state['goal']}\n"
            f"Contexte (docs): {state.get('context_docs', [])[:2]}\n"
            f"Fichiers ciblés: {target_files}"
        )
    out = llm.invoke(as_messages(prompt))
    patch: dict = {"diff": "", "touched": []}
    import json
    raw = getattr(out, "content", "")
    content = raw if isinstance(raw, str) else ""
    try:
        patch = json.loads(content)
    except Exception:
        # tolerate fenced JSON or noisy wrappers
        import re
        m = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", content)
        if m:
            try:
                patch = json.loads(m.group(1))
            except Exception:
                pass
        else:
            start = content.find("{")
            end = content.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    patch = json.loads(content[start:end+1])
                except Exception:
                    pass
    if cfg.allow_direct_write:
        written = 0
        try:
            candidates = []
            for key in ("files", "direct", "write", "documents"):
                v = patch.get(key)
                if isinstance(v, list):
                    candidates.extend(v)
            if not candidates and all(k in patch for k in ("path", "content")):
                candidates = [patch]
            safe_items = []
            for item in candidates:
                if isinstance(item, dict) and "path" in item and "content" in item:
                    safe_items.append({"path": str(item["path"]), "content": str(item["content"])})
            for it in safe_items:
                write_file(it["path"], it["content"], cfg)
                written += 1
            if written > 0:
                state["patch"] = patch
                state["result"] = {"ok": True, "direct_write": True, "written": written}
                return state
        except Exception as e:
            state["result"] = {"ok": False, "error": f"direct write failed: {e}"}
            return state
        state["result"] = {"ok": False, "error": "no files to write"}
        return state

    ensure_safe_branch()
    diff: str = str(patch.get("diff", ""))
    ok = apply_patch_text(diff)
    if not ok:
        # Fallback: attempt direct write if the LLM returned structured files
        written = False
        try:
            # Accept several shapes: {files:[{path,content}]}, {direct:[...]}, {write:[...]}
            candidates = []
            for key in ("files", "direct", "write", "documents"):
                v = patch.get(key)
                if isinstance(v, list):
                    candidates.extend(v)
            # Also accept single {path, content} at top-level
            if not candidates and all(k in patch for k in ("path", "content")):
                candidates = [patch]
            # Ensure candidate dicts
            safe_items = []
            for item in candidates:
                if isinstance(item, dict) and "path" in item and "content" in item:
                    safe_items.append({"path": str(item["path"]), "content": str(item["content"])})
            for it in safe_items:
                # Only allow writing within repo docs/ by default for safety
                p = it["path"]
                if p.startswith("docs/") or p.startswith("./docs/") or "/docs/" in p:
                    write_file(p, it["content"])  # will enforce SAFE_PATHS internally
                    written = True
            if written:
                state["patch"] = patch
                state["result"] = {"ok": True, "direct_write": True, "written": len(safe_items)}
                return state
        except Exception:
            pass
        state["result"] = {"ok": False, "error": "apply failed"}
        return state
    state["patch"] = patch
    return state
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
    cfg = AgentConfig()
    if state.get("result",{}).get("ok") is False:
        return state
    if cfg.allow_direct_write:
        state["result"] = {"ok": True, "committed": False}
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
