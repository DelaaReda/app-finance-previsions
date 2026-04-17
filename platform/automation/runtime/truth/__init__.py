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
from .lane_backoff import (
    CONTINUOUS_LANES,
    clear_lane_backoff,
    load_active_lane_backoffs,
    load_all_lane_backoffs,
    load_lane_backoff,
    persist_lane_backoff,
    record_lane_tick,
    write_lane_backoff,
)
from .public_proof_runner import persist_public_proof, run_public_proof
from .verifier_governor import (
    build_verifier_trigger_fingerprint,
    load_verifier_state,
    persist_verifier_state,
    record_verifier_result,
    should_run_verifier,
)

__all__ = [
    "CONTINUOUS_LANES",
    "EventStore",
    "build_runtime_truth_snapshot",
    "build_stable_planner_dispatch_snapshot",
    "build_verifier_trigger_fingerprint",
    "clear_lane_backoff",
    "load_active_lane_backoffs",
    "load_all_lane_backoffs",
    "load_lane_backoff",
    "load_product_delivery_state",
    "load_verifier_state",
    "persist_lane_backoff",
    "persist_product_delivery_state",
    "persist_public_proof",
    "persist_verifier_state",
    "product_delivery_state_path",
    "record_lane_tick",
    "record_verifier_result",
    "run_public_proof",
    "should_run_verifier",
    "write_lane_backoff",
]
