#!/bin/bash
# MAX Meeting Development Server Startup Script
# Usage: ./scripts/dev.sh [backend|frontend|all]

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

echo_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

echo_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if .env exists
check_env() {
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        echo_warn ".env file not found. Creating from .env.example..."
        cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
        echo_info "Please edit .env with your actual values before running again."
        exit 1
    fi
}

# Start backend
start_backend() {
    echo_info "Starting backend server..."
    cd "$PROJECT_ROOT/backend"

    # Activate virtual environment
    if [ ! -d "venv" ]; then
        echo_info "Creating virtual environment..."
        python3 -m venv venv
        source venv/bin/activate
        pip install --upgrade pip
        pip install -r requirements.txt
    else
        source venv/bin/activate
    fi

    # Load environment variables
    set -a
    source "$PROJECT_ROOT/.env"
    set +a

    echo_info "Backend running at http://localhost:8000"
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
}

# Start frontend
start_frontend() {
    echo_info "Starting frontend server..."
    cd "$PROJECT_ROOT/frontend"

    # Install dependencies if needed
    if [ ! -d "node_modules" ]; then
        echo_info "Installing frontend dependencies..."
        npm install
    fi

    echo_info "Frontend running at http://localhost:5173"
    npm run dev
}

# Start both
start_all() {
    check_env
    echo_info "Starting all services..."

    # Start backend in background
    start_backend &
    BACKEND_PID=$!

    # Wait for backend to be ready
    sleep 3

    # Start frontend
    start_frontend &
    FRONTEND_PID=$!

    # Trap to kill both on exit
    trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT

    wait
}

# Main
case "${1:-all}" in
    backend)
        check_env
        start_backend
        ;;
    frontend)
        start_frontend
        ;;
    all)
        start_all
        ;;
    *)
        echo "Usage: $0 [backend|frontend|all]"
        exit 1
        ;;
esac
