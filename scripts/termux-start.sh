#!/usr/bin/env bash
# Project Zoe - Termux launcher.
#
# Starts the local engine (Ollama or llama-server), holds a wake lock, then runs
# Zoe with whatever arguments you pass.
#
#   bash scripts/termux-start.sh                    # interactive help
#   bash scripts/termux-start.sh run "hello"
#   bash scripts/termux-start.sh report
#   bash scripts/termux-start.sh --stop             # stop engine + release lock
set -euo pipefail

ZOE_HOME="${ZOE_HOME:-$HOME/.zoe}"
OLLAMA_HOST="${ZOE_OLLAMA_HOST:-http://127.0.0.1:11434}"
LLAMA_URL="${ZOE_LLAMA_SERVER_URL:-http://127.0.0.1:8080}"
WAIT_S="${ZOE_START_WAIT_S:-40}"

say()  { printf '\033[1;36m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[!]\033[0m %s\n' "$*"; }

# shellcheck disable=SC1091
[ -f "$ZOE_HOME/env" ] && . "$ZOE_HOME/env"

if [ -x "$ZOE_HOME/venv/bin/python" ]; then
  PY="$ZOE_HOME/venv/bin/python"
else
  PY="$(command -v python3)"
fi

have_wake_lock() { command -v termux-wake-lock >/dev/null 2>&1; }
wake_lock()   { have_wake_lock && termux-wake-lock    || true; }
wake_unlock() { have_wake_lock && termux-wake-unlock  || true; }

engine_up() {
  curl -fsS --max-time 2 "${1%/}/api/tags" >/dev/null 2>&1 \
    || curl -fsS --max-time 2 "${1%/}/health" >/dev/null 2>&1
}

wait_for() {
  local url="$1" i
  for i in $(seq 1 "$WAIT_S"); do
    engine_up "$url" && return 0
    sleep 1
  done
  return 1
}

stop_engine() {
  say "stopping Zoe engines"
  pkill -f "ollama serve" 2>/dev/null || true
  pkill -f "llama-server" 2>/dev/null || true
  wake_unlock
  say "stopped"
  exit 0
}

if [ "${1:-}" = "--stop" ]; then
  stop_engine
fi

BACKEND="${ZOE_LLM_BACKEND:-mock}"
wake_lock

case "$BACKEND" in
  ollama)
    if ! engine_up "$OLLAMA_HOST"; then
      command -v ollama >/dev/null 2>&1 \
        || { warn "ollama not installed: pkg install ollama"; exit 1; }
      say "starting Ollama"
      mkdir -p "$ZOE_HOME"
      nohup ollama serve > "$ZOE_HOME/ollama.log" 2>&1 &
      wait_for "$OLLAMA_HOST" \
        || { warn "Ollama did not come up; see $ZOE_HOME/ollama.log"; exit 1; }
      say "Ollama ready at $OLLAMA_HOST"
    fi
    ;;
  llama-server)
    if ! engine_up "$LLAMA_URL"; then
      command -v llama-server >/dev/null 2>&1 \
        || { warn "llama-server not installed: pkg install llama-cpp"; exit 1; }
      [ -n "${ZOE_GGUF_PATH:-}" ] \
        || { warn "set ZOE_GGUF_PATH to a .gguf file first"; exit 1; }
      say "starting llama-server on $LLAMA_URL"
      mkdir -p "$ZOE_HOME"
      nohup llama-server -m "$ZOE_GGUF_PATH" -c "${ZOE_CONTEXT_TOKENS:-2048}" \
        --host 127.0.0.1 --port "${LLAMA_URL##*:}" \
        > "$ZOE_HOME/llama-server.log" 2>&1 &
      wait_for "$LLAMA_URL" \
        || { warn "llama-server did not come up; see $ZOE_HOME/llama-server.log"; exit 1; }
      say "llama-server ready at $LLAMA_URL"
    fi
    ;;
  mock)
    say "mock backend: no engine needed"
    ;;
  *)
    warn "backend '$BACKEND' is managed outside this script"
    ;;
esac

exec "$PY" -m zoe "$@"
