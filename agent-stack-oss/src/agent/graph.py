
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
    session_id: Optional[str]
    start_time: Optional[float]
def _log_node_execution(state: AgentState, node_name: str, status: str = "start", details: str = "") -> None:
    """Log node execution for monitoring purposes."""
    session_id = state.get("session_id", "unknown")
    if session_id and session_id != "unknown":
        try:
            from .monitoring_system import AgentMonitor
            monitor = AgentMonitor("/Users/venom/Documents/analyse-financiere/agent-stack-oss")
            monitor.log_event(
                session_id=session_id,
                node=node_name,
                event_type="progress" if status == "start" else "warning" if "warning" in status else "error" if "error" in status else "complete",
                message=f"{node_name} {status}: {details}",
                details={"status": status, "node": node_name}
            )
        except Exception:
            # Silently fail if monitoring is not available
            pass


def node_plan(state: AgentState) -> AgentState:
    # Log node execution
    _log_node_execution(state, "plan", "start", "Starting planning phase")
    
    try:
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
        
        _log_node_execution(state, "plan", "complete", f"Plan created with {len(plan.get('steps', []))} steps")
    except Exception as e:
        _log_node_execution(state, "plan", "error", f"Failed to create plan: {str(e)}")
        state["plan"] = {"steps": [], "files": [], "error": str(e)}
    
    return state
def node_retrieve(state: AgentState) -> AgentState:
    # Log node execution
    _log_node_execution(state, "retrieve", "start", "Starting document retrieval")
    
    try:
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
        
        _log_node_execution(state, "retrieve", "complete", f"Retrieved {len(results)} documents")
    except Exception as e:
        _log_node_execution(state, "retrieve", "error", f"Failed to retrieve documents: {str(e)}")
        state["context_docs"] = []
    
    return state
def node_patch(state: AgentState) -> AgentState:
    # Log node execution
    _log_node_execution(state, "patch", "start", "Starting code patching")
    
    try:
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
                    _log_node_execution(state, "patch", "complete", f"Direct write successful: {written} files")
                    return state
            except Exception as e:
                state["result"] = {"ok": False, "error": f"direct write failed: {e}"}
                _log_node_execution(state, "patch", "error", f"Direct write failed: {str(e)}")
                return state
            state["result"] = {"ok": False, "error": "no files to write"}
            _log_node_execution(state, "patch", "warning", "No files to write")
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
                    _log_node_execution(state, "patch", "complete", f"Fallback direct write successful: {len(safe_items)} files")
                    return state
            except Exception as e:
                _log_node_execution(state, "patch", "error", f"Fallback write failed: {str(e)}")
                pass
            state["result"] = {"ok": False, "error": "apply failed"}
            _log_node_execution(state, "patch", "error", "Patch application failed")
            return state
        state["patch"] = patch
        _log_node_execution(state, "patch", "complete", "Patch applied successfully")
    except Exception as e:
        _log_node_execution(state, "patch", "error", f"Failed to create patch: {str(e)}")
        state["result"] = {"ok": False, "error": str(e)}
    
    return state
def node_qa(state: AgentState) -> AgentState:
    # Log node execution
    _log_node_execution(state, "qa", "start", "Starting quality assurance checks")
    
    try:
        # Run enhanced QA checks including browser QA
        try:
            from .nodes.enhanced_qa import enhanced_qa_check
            tests = enhanced_qa_check()
        except Exception as e:
            # Fallback to standard tests if enhanced QA fails
            lin = run_linters()
            pyt = run_pytests()
            web = build_webapp()
            tests = {"linters": lin, "pytest": pyt, "webapp": web, "error": str(e)}
        
        state["tests"] = tests
        # Check if all critical tests pass
        critical_passed = True
        for test_category, test_result in tests.items():
            if isinstance(test_result, dict) and "ok" in test_result:
                if not test_result.get("ok", True):  # Default to True for non-critical
                    critical_passed = False
                    break
            elif isinstance(test_result, dict) and "linters" in test_result:
                # Handle nested standard tests
                std_tests = test_result
                if not std_tests.get("linters", {}).get("ok", True) or \
                   not std_tests.get("pytest", {}).get("ok", True) or \
                   not std_tests.get("webapp", {}).get("ok", True):
                    critical_passed = False
                    break
        
        if not critical_passed:
            restore_worktree()
            state["result"] = {"ok": False, "error": "qa failed", "tests": tests}
            _log_node_execution(state, "qa", "error", "Quality assurance checks failed")
        else:
            _log_node_execution(state, "qa", "complete", "Quality assurance checks passed")
    except Exception as e:
        state["result"] = {"ok": False, "error": str(e)}
        _log_node_execution(state, "qa", "error", f"Quality assurance failed: {str(e)}")
    
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
