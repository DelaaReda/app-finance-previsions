from __future__ import annotations
from typing import TypedDict, List, Optional
from ..models.router import get_llm, as_messages
from ..tools.git_tools import current_branch
from ..config import AgentConfig
from ..tools.git_tools import _run


class ArchitectureState(TypedDict):
    goal: str
    plan: dict
    context_docs: List[str]
    patch: dict
    tests: dict
    result: dict
    retrieval_error: Optional[str]
    architecture_plan: Optional[dict]
    sprint_plan: Optional[dict]
    priorities: Optional[List[str]]
    recent_commits: Optional[List[dict]]


def node_architecture_planner(state: ArchitectureState) -> ArchitectureState:
    """
    Plan architecture and integration documentation to help developers stay on the vision path.
    """
    llm = get_llm("plan")
    
    # Get recent commits to understand current state
    recent_commits_info = _get_recent_commits_info()
    
    prompt = (
        f"Plan d'architecture et documentation pour l'objectif: {state['goal']}\n"
        f"Branche actuelle: {current_branch()}\n"
        f"Commits récents: {recent_commits_info}\n"
        "Réponds en JSON avec {\n"
        "  \"architecture\": {\"components\":[...], \"interfaces\":[...], \"dataflow\":[...]},\n"
        "  \"integration_plan\": {\"phases\":[...], \"risks\":[...], \"timeline\":[...]},\n"
        "  \"documentation\": {\"files\":[...], \"sections\":[...]}\n"
        "}\n"
        "Concentre-toi sur aider les développeurs à rester alignés avec la vision globale.\n"
        "Assure-toi que le plan est réalisable avec les ressources actuelles."
    )
    
    out = llm.invoke(as_messages(prompt))
    architecture_plan: dict = {}
    
    try:
        import json
        raw = getattr(out, "content", "")
        content = raw if isinstance(raw, str) else ""
        architecture_plan = json.loads(content)
    except Exception:
        architecture_plan = {"error": "Failed to parse architecture plan"}
    
    state["architecture_plan"] = architecture_plan
    return state


def node_priority_definer(state: ArchitectureState) -> ArchitectureState:
    """
    Define priorities based on the goal, architecture plan, and recent commits.
    """
    llm = get_llm("plan")
    
    prompt = (
        f"Définis les priorités pour l'objectif: {state['goal']}\n"
        f"Plan d'architecture: {state.get('architecture_plan', {})}\n"
        f"Commits récents: {_get_recent_commits_info()}\n"
        "Réponds en JSON avec {\"priorities\":[...], \"rationale\": \"...\"}\n"
        "Classe par ordre d'importance pour atteindre l'objectif rapidement et sûrement.\n"
        "Considère les dépendances techniques et l'impact sur la vision globale."
    )
    
    out = llm.invoke(as_messages(prompt))
    priorities: dict = {}
    
    try:
        import json
        raw = getattr(out, "content", "")
        content = raw if isinstance(raw, str) else ""
        priorities = json.loads(content)
    except Exception:
        priorities = {"priorities": [], "error": "Failed to parse priorities"}
    
    state["priorities"] = priorities.get("priorities", [])
    return state


def _get_recent_commits_info() -> str:
    """Get information about recent commits on specific branches."""
    try:
        # Check for recent commits on feature/g4f-integration or local-branch
        branches_to_check = ["feature/g4f-integration", "local-branch"]
        current_br = current_branch()
        
        # Always include current branch
        branches_to_check.append(current_br)
        
        commit_infos = []
        for branch in set(branches_to_check):  # Use set to remove duplicates
            try:
                # Get last 3 commits from this branch
                rc, out = _run(f"git log {branch} --oneline -3 --no-merges")
                if rc == 0 and out.strip():
                    commit_infos.append(f"{branch}: {out.strip()}")
            except Exception:
                continue
                
        return "; ".join(commit_infos) if commit_infos else "Aucun commit récent trouvé"
    except Exception:
        return "Impossible de récupérer les commits récents"


def node_sprint_planner(state: ArchitectureState) -> ArchitectureState:
    """
    Create sprint plans based on recent commits and vision alignment.
    """
    llm = get_llm("plan")
    
    prompt = (
        f"Plan de sprint pour l'objectif: {state['goal']}\n"
        f"Priorités: {state.get('priorities', [])}\n"
        f"Plan d'architecture: {state.get('architecture_plan', {})}\n"
        f"Commits récents: {_get_recent_commits_info()}\n"
        "Réponds en JSON avec {\"sprint_tasks\":[...], \"duration_days\": 7, \"milestones\":[...]}\n"
        "Crée un plan réalisable pour une semaine avec des tâches concrètes.\n"
        "Assure-toi que chaque tâche peut être terminée en 1-2 jours maximum.\n"
        "Inclus des critères d'acceptation clairs pour chaque tâche."
    )
    
    out = llm.invoke(as_messages(prompt))
    sprint_plan: dict = {}
    
    try:
        import json
        raw = getattr(out, "content", "")
        content = raw if isinstance(raw, str) else ""
        sprint_plan = json.loads(content)
    except Exception:
        sprint_plan = {"error": "Failed to parse sprint plan"}
    
    state["sprint_plan"] = sprint_plan
    return state