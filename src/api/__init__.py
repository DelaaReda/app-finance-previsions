# src/api/__init__.py
"""
REST API for React frontend.
Exposes all 5 pillars: Macro, Stocks, News, Copilot, Brief + Signals
"""

from .main import create_app, run_server

__all__ = ["create_app", "run_server"]
