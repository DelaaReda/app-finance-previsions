#!/bin/bash
# scripts/start_fullstack.sh
# Quick start script for full stack (backend + frontend)

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║      Finance Copilot - Full Stack Launcher v0.1        ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 not found${NC}"
    exit 1
fi

# Check Node
if ! command -v npm &> /dev/null; then
    echo -e "${RED}❌ npm not found${NC}"
    exit 1
fi

# Check if API dependencies installed
echo -e "${YELLOW}🔍 Checking dependencies...${NC}"
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  FastAPI not installed. Installing...${NC}"
    cd "$PROJECT_ROOT"
    pip install -r requirements-api-v2.txt
fi

# Check if webapp dependencies installed
if [ ! -d "$PROJECT_ROOT/webapp/node_modules" ]; then
    echo -e "${YELLOW}⚠️  React dependencies not installed. Installing...${NC}"
    cd "$PROJECT_ROOT/webapp"
    npm install
fi

echo -e "${GREEN}✅ Dependencies OK${NC}"
echo ""

# Kill existing processes on ports 8050 and 5173
echo -e "${YELLOW}🧹 Cleaning up existing processes...${NC}"
lsof -ti:8050 | xargs kill -9 2>/dev/null || true
lsof -ti:5173 | xargs kill -9 2>/dev/null || true
echo -e "${GREEN}✅ Ports cleared${NC}"
echo ""

# Start backend
echo -e "${BLUE}🚀 Starting FastAPI backend on port 8050...${NC}"
cd "$PROJECT_ROOT"
python3 scripts/run_api_v2.py --port 8050 > logs/api.log 2>&1 &
API_PID=$!
echo -e "${GREEN}✅ Backend started (PID: $API_PID)${NC}"
echo ""

# Wait for backend to be ready
echo -e "${YELLOW}⏳ Waiting for backend to be ready...${NC}"
for i in {1..30}; do
    if curl -s http://localhost:8050/api/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Backend is ready!${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}❌ Backend failed to start. Check logs/api.log${NC}"
        kill $API_PID 2>/dev/null || true
        exit 1
    fi
    sleep 1
    echo -n "."
done
echo ""

# Start frontend
echo -e "${BLUE}🚀 Starting React frontend on port 5173...${NC}"
cd "$PROJECT_ROOT/webapp"
npm run dev > ../logs/webapp.log 2>&1 &
WEBAPP_PID=$!
echo -e "${GREEN}✅ Frontend started (PID: $WEBAPP_PID)${NC}"
echo ""

# Wait for frontend to be ready
echo -e "${YELLOW}⏳ Waiting for frontend to be ready...${NC}"
for i in {1..30}; do
    if curl -s http://localhost:5173 > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Frontend is ready!${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}❌ Frontend failed to start. Check logs/webapp.log${NC}"
        kill $API_PID $WEBAPP_PID 2>/dev/null || true
        exit 1
    fi
    sleep 1
    echo -n "."
done
echo ""

# Success message
echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                  🎉 All systems GO! 🎉                 ║${NC}"
echo -e "${GREEN}╠══════════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║                                                          ║${NC}"
echo -e "${GREEN}║  Frontend:  http://localhost:5173                       ║${NC}"
echo -e "${GREEN}║  Backend:   http://localhost:8050                       ║${NC}"
echo -e "${GREEN}║  API Docs:  http://localhost:8050/api/docs              ║${NC}"
echo -e "${GREEN}║                                                          ║${NC}"
echo -e "${GREEN}║  Logs:                                                   ║${NC}"
echo -e "${GREEN}║    - Backend:  logs/api.log                             ║${NC}"
echo -e "${GREEN}║    - Frontend: logs/webapp.log                          ║${NC}"
echo -e "${GREEN}║                                                          ║${NC}"
echo -e "${GREEN}║  PIDs:                                                   ║${NC}"
echo -e "${GREEN}║    - Backend:  $API_PID${NC}                              "
echo -e "${GREEN}║    - Frontend: $WEBAPP_PID${NC}                           "
echo -e "${GREEN}║                                                          ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop both servers${NC}"
echo ""

# Save PIDs to file for easy cleanup
echo "$API_PID" > "$PROJECT_ROOT/.fullstack_pids"
echo "$WEBAPP_PID" >> "$PROJECT_ROOT/.fullstack_pids"

# Trap to cleanup on exit
trap cleanup EXIT

cleanup() {
    echo ""
    echo -e "${YELLOW}🛑 Shutting down...${NC}"
    kill $API_PID $WEBAPP_PID 2>/dev/null || true
    rm -f "$PROJECT_ROOT/.fullstack_pids"
    echo -e "${GREEN}✅ Shutdown complete${NC}"
}

# Keep script running
wait
