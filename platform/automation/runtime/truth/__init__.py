"""Runtime truth canonical surface.

Primary runtime truth remains SQLite/event-store backed. Legacy projections are
secondary compatibility outputs.
"""

from .event_store import EventStore
from .runtime_truth_reader import build_runtime_truth_snapshot
from .dispatch_snapshot import build_stable_planner_dispatch_snapshot

__all__ = [
    "EventStore",
    "build_runtime_truth_snapshot",
    "build_stable_planner_dispatch_snapshot",
]
