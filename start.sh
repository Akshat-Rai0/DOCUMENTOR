#!/usr/bin/env bash
#
# start.sh — run DocuMentor's full stack (Ollama + backend + frontend) with
# one command instead of three manual terminals.
#
# ASSUMPTIONS (adjust the variables below if your layout differs):
#   - Backend is a FastAPI app run via `uvicorn main:app` from ./backend
#   - Frontend is a Vite/React app run via `npm run dev` from ./frontend
#   - Ollama is installed locally and its CLI is on PATH
#
# Usage:
#   chmod +x start.sh
#   ./start.sh

set -euo pipefail

# ---------------------------------------------------------------------------
# Config — edit these if your folder names / commands differ
# ---------------------------------------------------------------------------
BACKEND_DIR="./backend"
BACKEND_CMD="uvicorn app:app --reload --host 0.0.0.0 --port 8000"

FRONTEND_DIR="./frontend"
FRONTEND_CMD="npm run dev"

OLLAMA_URL="http://localhost:11434"

# ---------------------------------------------------------------------------
# Colors for readable output
# ---------------------------------------------------------------------------
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log()  { echo -e "${GREEN}[start.sh]${NC} $1"; }
warn() { echo -e "${YELLOW}[start.sh]${NC} $1"; }
err()  { echo -e "${RED}[start.sh]${NC} $1"; }

# ---------------------------------------------------------------------------
# Track child PIDs so we can clean everything up on exit (Ctrl+C, error, etc.)
# ---------------------------------------------------------------------------
PIDS=()

cleanup() {
    log "Shutting down..."
    for pid in "${PIDS[@]:-}"; do
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
        fi
    done
    wait 2>/dev/null || true
    log "All processes stopped."
}
trap cleanup EXIT INT TERM

# ---------------------------------------------------------------------------
# 1. Ollama — start if not already running
# ---------------------------------------------------------------------------
if curl -s --max-time 2 "${OLLAMA_URL}/api/tags" > /dev/null 2>&1; then
    log "Ollama already running at ${OLLAMA_URL} — skipping."
else
    if ! command -v ollama >/dev/null 2>&1; then
        err "ollama CLI not found on PATH. Install it or start it manually, then re-run."
        exit 1
    fi
    log "Starting Ollama..."
    ollama serve > /tmp/documentor_ollama.log 2>&1 &
    PIDS+=($!)

    # Wait for it to actually come up before moving on, so the backend
    # doesn't fail its first request against a not-yet-ready Ollama.
    for i in $(seq 1 15); do
        if curl -s --max-time 1 "${OLLAMA_URL}/api/tags" > /dev/null 2>&1; then
            log "Ollama is up."
            break
        fi
        if [ "$i" -eq 15 ]; then
            err "Ollama did not become ready in time. Check /tmp/documentor_ollama.log"
            exit 1
        fi
        sleep 1
    done
fi

# ---------------------------------------------------------------------------
# 2. Backend (FastAPI / uvicorn)
# ---------------------------------------------------------------------------
if [ ! -d "$BACKEND_DIR" ]; then
    err "Backend directory '$BACKEND_DIR' not found. Edit BACKEND_DIR in start.sh."
    exit 1
fi

log "Starting backend (${BACKEND_CMD}) in ${BACKEND_DIR}..."
(
    cd "$BACKEND_DIR"
    exec $BACKEND_CMD
) > /tmp/documentor_backend.log 2>&1 &
PIDS+=($!)

# Give the backend a moment before starting the frontend, so early frontend
# requests don't all fail while uvicorn is still booting.
sleep 2

# ---------------------------------------------------------------------------
# 3. Frontend (Vite/React dev server)
# ---------------------------------------------------------------------------
if [ ! -d "$FRONTEND_DIR" ]; then
    err "Frontend directory '$FRONTEND_DIR' not found. Edit FRONTEND_DIR in start.sh."
    exit 1
fi

log "Starting frontend (${FRONTEND_CMD}) in ${FRONTEND_DIR}..."
(
    cd "$FRONTEND_DIR"
    exec $FRONTEND_CMD
) > /tmp/documentor_frontend.log 2>&1 &
PIDS+=($!)

log "All services starting."
log "  Backend log:  tail -f /tmp/documentor_backend.log"
log "  Frontend log: tail -f /tmp/documentor_frontend.log"
log "  Ollama log:   tail -f /tmp/documentor_ollama.log"
log "Press Ctrl+C to stop everything."

# Wait on all background jobs — if any one dies, this returns and cleanup runs.
wait