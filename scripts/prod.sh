#!/bin/bash
# MAX Meeting Production Deployment Script
# Usage: ./scripts/prod.sh [start|stop|restart|logs|status]

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT/docker"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
echo_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
echo_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check prerequisites
check_prereqs() {
    if ! command -v docker &> /dev/null; then
        echo_error "Docker is not installed."
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        echo_error "Docker Compose is not installed."
        exit 1
    fi

    # Check secrets directory
    if [ ! -d "secrets" ]; then
        echo_warn "Creating secrets directory..."
        mkdir -p secrets
        echo "CHANGE_ME" > secrets/db_password.txt
        echo "CHANGE_ME" > secrets/redis_password.txt
        echo "CHANGE_ME_MIN_32_BYTES_LONG" > secrets/jwt_secret.txt
        echo "CHANGE_ME" > secrets/gemini_api_key.txt
        echo "CHANGE_ME" > secrets/huggingface_token.txt
        chmod 600 secrets/*.txt
        echo_warn "Please edit secrets/*.txt files with actual values before starting."
        exit 1
    fi

    # Check .env file
    if [ ! -f ".env" ]; then
        echo_warn ".env file not found in docker/ directory."
        echo_warn "Creating from parent .env.example..."
        cp "$PROJECT_ROOT/.env.example" .env
        echo_warn "Please edit .env with your actual values."
        exit 1
    fi
}

# Docker compose command (handle both old and new versions)
compose() {
    if docker compose version &> /dev/null; then
        docker compose "$@"
    else
        docker-compose "$@"
    fi
}

start() {
    check_prereqs
    echo_info "Starting MAX Meeting production services..."
    compose up -d
    echo_info "Services started. Run '$0 logs' to view logs."
}

stop() {
    echo_info "Stopping MAX Meeting services..."
    compose down
    echo_info "Services stopped."
}

restart() {
    echo_info "Restarting MAX Meeting services..."
    compose restart
    echo_info "Services restarted."
}

logs() {
    compose logs -f "$@"
}

status() {
    echo_info "Service status:"
    compose ps
    echo ""
    echo_info "Health checks:"
    docker inspect --format='{{.Name}}: {{if .State.Health}}{{.State.Health.Status}}{{else}}no healthcheck{{end}}' \
        $(compose ps -q 2>/dev/null) 2>/dev/null || echo "No running containers"
}

build() {
    echo_info "Building images..."
    compose build "$@"
    echo_info "Build complete."
}

# Main
case "${1:-status}" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    logs)
        shift
        logs "$@"
        ;;
    status)
        status
        ;;
    build)
        shift
        build "$@"
        ;;
    *)
        echo "Usage: $0 [start|stop|restart|logs|status|build]"
        echo ""
        echo "Commands:"
        echo "  start   - Start all services"
        echo "  stop    - Stop all services"
        echo "  restart - Restart all services"
        echo "  logs    - View logs (add service name to filter)"
        echo "  status  - Show service status"
        echo "  build   - Build/rebuild images"
        exit 1
        ;;
esac
