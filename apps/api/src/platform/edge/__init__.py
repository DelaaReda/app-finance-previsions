"""Edge adapters for critical API contracts.

These helpers provide additive, degraded-safe envelopes for critical endpoints
without breaking the historical `{"ok": bool, "data": ...}` response shape.
"""

from .contracts import (  # noqa: F401
    edge_enabled,
    edge_ok,
    edge_degraded,
    edge_error,
)

