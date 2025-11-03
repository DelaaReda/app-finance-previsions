# src/core/duck.py
from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Any
import duckdb

def query_parquet(sql: str, params: Dict[str, Any] | None = None) -> list[dict]:
    """
    Exécute une requête DuckDB et renvoie une liste de dicts (UI-ready).
    Exemple:
      SELECT * FROM read_parquet('data/features/table=prices_features_daily/dt=*/final.parquet')
      WHERE symbol IN ('AAPL','NVDA') AND date >= '2024-01-01';
    """
    con = duckdb.connect()
    try:
        if params:
            res = con.execute(sql, params).fetchall()
            cols = [d[0] for d in con.description]
        else:
            res = con.execute(sql).fetchall()
            cols = [d[0] for d in con.description]
        out = [dict(zip(cols, row)) for row in res]
        return out
    finally:
        con.close()

def parquet_glob(*parts: str) -> str:
    """Construit un pattern glob pour read_parquet de DuckDB"""
    return str(Path(*parts))