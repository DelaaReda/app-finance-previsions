from __future__ import annotations

import logging
from typing import Any


def bootstrap_runtime() -> dict[str, Any]:
    """Lightweight bootstrap hook.

    Keeps side effects minimal while `platform.main` is being incrementally
    strangled into domain routers and dedicated startup modules.
    """

    logging.getLogger("platform.bootstrap").debug("bootstrap_runtime:ok")
    return {"status": "ok", "module": "platform.bootstrap.runtime"}
