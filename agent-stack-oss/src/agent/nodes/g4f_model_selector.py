from __future__ import annotations
import json
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from ..config import AgentConfig


def get_best_g4f_model(cfg: Optional[AgentConfig] = None) -> str:
    """
    Get the best available G4F model based on working models list.
    Falls back to predefined models if no working models are available.
    """
    cfg = cfg or AgentConfig()
    
    # Try to load working models from the watcher
    working_models = _load_working_models()
    
    if working_models:
        # Return the best model from working models
        return working_models[0]
    
    # Fallback to predefined models in order of preference
    fallback_models = cfg.g4f_models if cfg.g4f_models else [
        "deepseek-ai/DeepSeek-R1-0528",
        "deepseek-ai/DeepSeek-V3-0324-Turbo",
        "deepseek-ai/DeepSeek-V3",
        "Qwen/Qwen3-235B-A22B-Thinking-2507",
        "Qwen/Qwen3-235B-A22B-Instruct-2507",
        "Qwen/Qwen3-Next-80B-A3B-Instruct",
        "zai-org/GLM-4.5",
        "meta-llama/Llama-3.3-70B-Instruct-Turbo",
        "openai/gpt-oss-120b",
    ]
    
    return fallback_models[0] if fallback_models else "gpt-4o-mini"


def _load_working_models(max_age_hours: int = 24) -> List[str]:
    """Load working models from the G4F model watcher output."""
    try:
        working_path = Path("data/llm/models/working.json")
        if not working_path.exists():
            return []
            
        content = working_path.read_text(encoding="utf-8")
        obj = json.loads(content)
        
        # Check if file is too old
        try:
            asof = obj.get("asof")
            if asof:
                from datetime import datetime, timezone
                dt = datetime.fromisoformat(asof.replace("Z","+00:00"))
                age_h = (datetime.now(timezone.utc) - dt).total_seconds()/3600.0
                if age_h > max_age_hours:
                    return []
        except Exception:
            pass
            
        rows = obj.get("models") or []
        # Sort by ok desc, pass_rate desc, latency asc
        rows.sort(key=lambda r: (
            not bool(r.get("ok")), 
            -(r.get("pass_rate") or 0.0), 
            (r.get("latency_s") or 9999.0)
        ))
        
        return [r.get("model") for r in rows if r.get("ok")]
    except Exception:
        return []


def refresh_working_models_if_needed(limit: int = 8) -> bool:
    """
    Refresh working models if they are outdated or don't exist.
    Returns True if refresh was performed.
    """
    try:
        working_path = Path("data/llm/models/working.json")
        
        # Check if refresh is needed
        need_refresh = not working_path.exists()
        
        if not need_refresh:
            try:
                # Check file age
                import time
                stat = working_path.stat()
                age_hours = (time.time() - stat.st_mtime) / 3600.0
                need_refresh = age_hours > 24  # Refresh if older than 24 hours
            except Exception:
                need_refresh = True
        
        if need_refresh:
            # Run the model watcher to refresh working models
            from subprocess import run, PIPE
            import sys
            
            # Change to the correct directory where the model watcher script is located
            cmd = [
                sys.executable, "-m", "src.agents.g4f_model_watcher",
                "--refresh", "--limit", str(limit)
            ]
            
            # Run from the parent directory where the agents module is located
            result = run(cmd, cwd="../../../", stdout=PIPE, stderr=PIPE, text=True, timeout=300)
            return result.returncode == 0
            
        return False
    except Exception as e:
        print(f"[model_selector] Warning: Failed to refresh models: {e}")
        return False


def get_model_performance_stats(model_name: str) -> Dict[str, Any]:
    """Get performance statistics for a specific model."""
    try:
        working_path = Path("data/llm/models/working.json")
        if not working_path.exists():
            return {}
            
        content = working_path.read_text(encoding="utf-8")
        obj = json.loads(content)
        
        rows = obj.get("models") or []
        for row in rows:
            if row.get("model") == model_name:
                return {
                    "ok": row.get("ok", False),
                    "latency_s": row.get("latency_s"),
                    "pass_rate": row.get("pass_rate"),
                    "provider": row.get("provider"),
                    "tested_at": row.get("tested_at")
                }
        return {}
    except Exception as e:
        print(f"[model_selector] Warning: Failed to get model stats for {model_name}: {e}")
        return {}


def select_model_for_task(task_complexity: str = "medium") -> str:
    """
    Select the most appropriate model based on task complexity.
    
    Args:
        task_complexity: "simple", "medium", or "complex"
    """
    working_models = _load_working_models()
    
    if not working_models:
        # If no working models, use fallback
        return get_best_g4f_model()
    
    if task_complexity == "simple":
        # For simple tasks, use fastest model
        # Sort by latency (ascending)
        models_with_stats = []
        for model in working_models:
            stats = get_model_performance_stats(model)
            latency = stats.get("latency_s", 9999)
            models_with_stats.append((model, latency))
        
        models_with_stats.sort(key=lambda x: x[1])
        return models_with_stats[0][0] if models_with_stats else working_models[0]
    
    elif task_complexity == "complex":
        # For complex tasks, use model with highest pass rate
        models_with_stats = []
        for model in working_models:
            stats = get_model_performance_stats(model)
            pass_rate = stats.get("pass_rate", 0) or 0
            models_with_stats.append((model, pass_rate))
        
        models_with_stats.sort(key=lambda x: x[1], reverse=True)
        return models_with_stats[0][0] if models_with_stats else working_models[0]
    
    else:  # medium complexity
        # For medium tasks, use the best overall model (already sorted)
        return working_models[0]