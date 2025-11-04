from pathlib import Path
import json, time

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DATA_DIR.mkdir(exist_ok=True)

def _path(key:str) -> Path:
    return DATA_DIR / f"{key}.json"

def save_json(key:str, payload:dict, source:list|None=None):
    now = int(time.time())
    doc = {
        "last_update": now,
        "source": source or [],
        "version": 1,
        "payload": payload
    }
    _path(key).write_text(json.dumps(doc, ensure_ascii=False))
    return doc

def load_json(key:str) -> dict|None:
    p = _path(key)
    if not p.exists(): return None
    return json.loads(p.read_text())

def last_updates_info():
    info = {}
    for name in ["news_feed","forecasts","brief_weekly","backtests"]:
        d = load_json(name)
        if d: info[name] = d.get("last_update")
    return info