"""Planner runtime canonical surface.

Keep exports lazy to avoid circular imports with runtime truth helpers.
"""

__all__ = ["PlannerGraphRuntime", "planner_board_snapshot", "build_planner_dispatch_metrics"]


def __getattr__(name: str):
    if name == "PlannerGraphRuntime":
        from .planner_graph_runtime import PlannerGraphRuntime

        return PlannerGraphRuntime
    if name == "planner_board_snapshot":
        from .planner_board_runtime import snapshot as planner_board_snapshot

        return planner_board_snapshot
    if name == "build_planner_dispatch_metrics":
        from .planner_dispatch_metrics import build_planner_dispatch_metrics

        return build_planner_dispatch_metrics
    raise AttributeError(name)
