from __future__ import annotations

import logging
import time

from apscheduler.schedulers.background import BackgroundScheduler


def _job():
    # Lazy import so module is lightweight if APS not installed in some contexts
    try:
        from src.agents.llm.run_once import main as run_once
    except Exception:  # path fallback if executed as module with PYTHONPATH=src
        from agents.llm.run_once import main as run_once  # type: ignore
    logging.getLogger(__name__).info("[scheduler] Running llm summary job...")
    try:
        run_once()
    except Exception as e:
        logging.getLogger(__name__).exception("[scheduler] job failed: %s", e)


def start_scheduler() -> BackgroundScheduler:
    sch = BackgroundScheduler()
    # Run at minute 0 of every hour
    sch.add_job(_job, "cron", minute="0")
    sch.start()
    return sch


def main():
    logging.basicConfig(level=logging.INFO)
    sch = start_scheduler()
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        sch.shutdown(wait=False)


if __name__ == "__main__":
    main()

