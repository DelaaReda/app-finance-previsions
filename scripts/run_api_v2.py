#!/usr/bin/env python3
"""
Launch FastAPI backend server v0.1
"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from api.main_v2 import run_server

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Finance Copilot API Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind")
    parser.add_argument("--port", type=int, default=8050, help="Port to bind")
    
    args = parser.parse_args()
    
    print(f"""
╔══════════════════════════════════════════════════════════╗
║         Finance Copilot API v0.1 - Starting            ║
╠══════════════════════════════════════════════════════════╣
║  Host: {args.host:44s} ║
║  Port: {args.port:<44d} ║
║  Docs: http://{args.host}:{args.port}/api/docs        {'║':>18s}
║  Health: http://{args.host}:{args.port}/api/health    {'║':>16s}
╚══════════════════════════════════════════════════════════╝
    """)
    
    run_server(host=args.host, port=args.port)
