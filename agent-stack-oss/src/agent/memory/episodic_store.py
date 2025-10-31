
from __future__ import annotations
import duckdb, os, time, json
from ..config import AgentConfig
class EpisodicMemory:
    def __init__(self, cfg: AgentConfig | None = None):
        self.cfg = cfg or AgentConfig()
        os.makedirs(os.path.dirname(self.cfg.duckdb_path), exist_ok=True)
        self.con = duckdb.connect(self.cfg.duckdb_path)
        self.con.execute('''
        CREATE TABLE IF NOT EXISTS runs(
          ts BIGINT,
          goal TEXT,
          plan JSON,
          diff TEXT,
          tests JSON,
          result JSON,
          notes TEXT
        )''')
    def log(self, goal: str, plan: dict, diff: str, tests: dict, result: dict, notes: str = ""):
        self.con.execute("INSERT INTO runs VALUES (?, ?, ?, ?, ?, ?, ?)",
                         [int(time.time()*1000), goal, json.dumps(plan), diff, json.dumps(tests), json.dumps(result), notes])
