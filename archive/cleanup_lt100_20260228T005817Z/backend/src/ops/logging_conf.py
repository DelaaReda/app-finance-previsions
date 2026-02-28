import logging
import logging.handlers
import json
import datetime
from pathlib import Path

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True, parents=True)
ACT_FILE = LOG_DIR / "dev_activity.jsonl"


def setup_app_logger(name: str = "app", level=logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if not logger.handlers:
        h = logging.handlers.RotatingFileHandler(LOG_DIR / "app.log", maxBytes=2_000_000, backupCount=5)
        f = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
        h.setFormatter(f)
        logger.addHandler(h)
    return logger


def log_activity(event: str, details: dict):
    rec = {
        "ts": datetime.datetime.utcnow().isoformat() + "Z",
        "event": event,
        "details": details,
    }
    with open(ACT_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

