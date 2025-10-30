#!/bin/bash
# scripts/start_fullstack.sh
# Start both FastAPI backend and React frontend

set -e

echo "🚀 Starting Full-Stack Finance Copilot"
echo "======================================"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${YELLOW}⚠️  Python 3 not found${NC}"
    exit 1
fi

# Check Node
if ! command -v node &> /dev/null; then
    echo -e "${YELLOW}⚠️  Node.js not found${NC}"
    exit 1
fi

echo -e "${BLUE}1. Starting FastAPI Backend (port 8000)...${NC}"
python3 -m src.api.main &
BACKEND_PID=$!
echo -e "${GREEN}   ✓ Backend PID: $BACKEND_PID${NC}"

# Wait for backend
sleep 3

# Health check
if curl -s http://127.0.0.1:8000/api/health > /dev/null; then
    echo -e "${GREEN}   ✓ Backend is healthy${NC}"
else
    echo -e "${YELLOW}   ⚠️  Backend health check failed${NC}"
fi

echo ""
echo -e "${BLUE}2. Starting React Frontend (port 5173)...${NC}"
cd webapp
npm run dev &
FRONTEND_PID=$!
echo -e "${GREEN}   ✓ Frontend PID: $FRONTEND_PID${NC}"

echo ""
echo -e "${GREEN}✅ Full-Stack Started!${NC}"
echo ""
echo "📊 Services:"
echo "   • Backend API:  http://127.0.0.1:8000/api"
echo "   • React UI:     http://127.0.0.1:5173"
echo ""
echo "📝 Logs:"
echo "   • Backend PID:  $BACKEND_PID"
echo "   • Frontend PID: $FRONTEND_PID"
echo ""
echo "🛑 To stop:"
echo "   kill $BACKEND_PID $FRONTEND_PID"
echo ""
echo "Press Ctrl+C to stop both services"

# Trap Ctrl+C
trap "echo ''; echo 'Stopping services...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT

# Keep script running
wait
