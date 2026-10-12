#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MCP_HOST="${MCP_HOST:-127.0.0.1}"
MCP_PORT="${MCP_PORT:-7001}"
AGENT_HOST="${AGENT_HOST:-127.0.0.1}"
AGENT_PORT="${AGENT_PORT:-8000}"
MCP_SERVER_URL="${MCP_SERVER_URL:-http://${MCP_HOST}:${MCP_PORT}}"
OTEL_TRACING_ENABLED="${OTEL_TRACING_ENABLED:-false}"

MCP_PID=""
AGENT_PID=""

cleanup() {
  echo
  echo "Stopping services..."
  if [[ -n "${AGENT_PID}" ]] && kill -0 "${AGENT_PID}" 2>/dev/null; then
    kill "${AGENT_PID}" 2>/dev/null || true
  fi
  if [[ -n "${MCP_PID}" ]] && kill -0 "${MCP_PID}" 2>/dev/null; then
    kill "${MCP_PID}" 2>/dev/null || true
  fi
  wait 2>/dev/null || true
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

ensure_port_free() {
  local port="$1"
  if lsof -nP -iTCP:"${port}" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "Port ${port} is already in use. Stop that process or choose another port." >&2
    echo "Example: MCP_PORT=7002 AGENT_PORT=8003 ./scripts/dev.sh" >&2
    exit 1
  fi
}

trap cleanup EXIT INT TERM

cd "${ROOT_DIR}"
require_command uv
require_command lsof
ensure_port_free "${MCP_PORT}"
ensure_port_free "${AGENT_PORT}"

if [[ ! -f ".env" ]]; then
  echo "Warning: .env was not found. GEMINI_API_KEY must still be available in your environment." >&2
fi

echo "Starting MCP tool server on http://${MCP_HOST}:${MCP_PORT}"
uv run uvicorn src.mcp_server.server:app --host "${MCP_HOST}" --port "${MCP_PORT}" &
MCP_PID="$!"

echo "Starting Agent API on http://${AGENT_HOST}:${AGENT_PORT}"
MCP_SERVER_URL="${MCP_SERVER_URL}" \
OTEL_TRACING_ENABLED="${OTEL_TRACING_ENABLED}" \
uv run uvicorn src.agent_api.main:app --host "${AGENT_HOST}" --port "${AGENT_PORT}" &
AGENT_PID="$!"

echo
echo "Services started."
echo "MCP docs:   http://${MCP_HOST}:${MCP_PORT}/docs"
echo "Agent docs: http://${AGENT_HOST}:${AGENT_PORT}/docs"
echo "Press Ctrl-C to stop both services."
echo

wait
