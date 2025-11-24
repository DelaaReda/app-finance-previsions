"""
Merged judge routes: reuse the canonical implementation from api.routes.judge.
This shim keeps legacy imports working while eliminating duplicate logic.
"""

from ..judge import judge_router, router

__all__ = ["router", "judge_router"]
