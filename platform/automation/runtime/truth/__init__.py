"""Runtime truth canonical surface.

Primary runtime truth remains SQLite/event-store backed. Legacy projections are
secondary compatibility outputs.
"""

from .event_store import EventStore
from .runtime_truth_reader import (
    build_runtime_truth_snapshot,
    load_product_delivery_state,
    persist_product_delivery_state,
    product_delivery_state_path,
)
from .dispatch_snapshot import build_stable_planner_dispatch_snapshot
from .public_proof_runner import persist_public_proof, run_public_proof

__all__ = [
    "EventStore",
    "build_runtime_truth_snapshot",
    "build_stable_planner_dispatch_snapshot",
    "load_product_delivery_state",
    "persist_product_delivery_state",
    "persist_public_proof",
    "product_delivery_state_path",
    "run_public_proof",
]
