#!/usr/bin/env bash
# Project Zoe - Termux launcher.
#
# Starts the local engine (Ollama or llama-server), holds a wake lock, then runs
# Zoe with whatever arguments you pass.
#
#   bash scripts/termux-start.sh                    # interactive help
#   bash scripts/termux-start.sh run "hello"
#   bash scripts/termux-start.sh report
#   bash scripts/termux-start.sh --stop             # stop the engine we started
#
# Set ZOE_KEEP_AWAKE=1 to keep the wake lock after Zoe exits (long-running use).
set -euo pipefail

ZOE_HOME="${ZOE_HOME:-$HOME/.zoe}"
PIDFILE="$ZOE_HOME/engine.pid"

say()  { printf '\033[1;36m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[!]\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31m[x]\033[0m %s\n' "$*" >&2; exit 1; }

# Load the installer environment first: it also sets PATH to the venv and may
# override the engine URLs.
# shellcheck disable=SC1091
[ -f "$ZOE_HOME/env" ] && . "$ZOE_HOME/env"

OLLAMA_HOST="${ZOE_OLLAMA_HOST:-http://127.0.0.1:11434}"
LLAMA_URL="${ZOE_LLAMA_SERVER_URL:-http://127.0.0.1:8080}"
WAIT_S="${ZOE_START_WAIT_S:-40}"
BACKEND="${ZOE_LLM_BACKEND:-mock}"

if [ -x "$ZOE_HOME/venv/bin/python" ]; then
  PY="$ZOE_HOME/venv/bin/python"
else
  PY="$(command -v python3 || true)"
fi
[ -n "$PY" ] || die "python3 not found; run scripts/termux-install.sh"

have_wake_lock() { command -v termux-wake-lock >/dev/null 2>&1; }
wake_lock()   { have_wake_lock && termux-wake-lock    || true; }
wake_unlock() { have_wake_lock && termux-wake-unlock  || true; }

# Probe with Python so the launcher works even when curl is not installed.
engine_up() {
  "$PY" - "$1" <<'PY'
import sys
import urllib.request

base = sys.argv[1].rstrip("/")
for path in ("/api/tags", "/health", "/v1/models"):
    try:
        with urllib.request.urlopen(base + path, timeout=2) as response:
            if response.status < 500:
                sys.exit(0)
    except Exception:
        pass
sys.exit(1)
PY
}

wait_for() {
  local url="$1" _
  for _ in $(seq 1 "$WAIT_S"); do
    engine_up "$url" && return 0
    sleep 1
  done
  return 1
}

start_engine() {
  local log="$1"
  shift
  mkdir -p "$ZOE_HOME"
  nohup "$@" > "$log" 2>&1 &
  echo $! > "$PIDFILE"
}

log_tail() {
  local log="$1"
  [ -f "$log" ] && tail -n 5 "$log" >&2 || true
}

stop_engine() {
  say "stopping the Zoe engine started by this script"
  local pid=""
  if [ -f "$PIDFILE" ]; then
    pid="$(cat "$PIDFILE" 2>/dev/null || true)"
  fi
  if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
    kill "$pid" 2>/dev/null || true
    sleep 1
    kill -9 "$pid" 2>/dev/null || true
    say "stopped pid $pid"
  else
    warn "no engine pid recorded at $PIDFILE (leaving other processes alone)"
  fi
  rm -f "$PIDFILE"
  wake_unlock
  say "stopped"
  exit 0
}

if [ "${1:-}" = "--stop" ]; then
  stop_engine
fi

case "$BACKEND" in
  ollama)
    if engine_up "$OLLAMA_HOST"; then
      say "Ollama already running at $OLLAMA_HOST"
    else
      command -v ollama >/dev/null 2>&1 \
        || die "ollama not installed: pkg install ollama"
      say "starting Ollama"
      mkdir -p "$ZOE_HOME"
      start_engine "$ZOE_HOME/ollama.log" ollama serve
      wait_for "$OLLAMA_HOST" \
        || { log_tail "$ZOE_HOME/ollama.log"; die "Ollama did not come up"; }
      say "Ollama ready at $OLLAMA_HOST"
    fi
    ;;
  llama-server)
    if engine_up "$LLAMA_URL"; then
      say "llama-server already running at $LLAMA_URL"
    else
      command -v llama-server >/dev/null 2>&1 \
        || die "llama-server not installed: pkg install llama-cpp"
      [ -n "${ZOE_GGUF_PATH:-}" ] \
        || die "set ZOE_GGUF_PATH to a .gguf file first"
      PORT="${LLAMA_URL##*:}"
      PORT="${PORT%%/*}"
      say "starting llama-server on $LLAMA_URL"
      start_engine "$ZOE_HOME/llama-server.log" \
        llama-server -m "$ZOE_GGUF_PATH" -c "${ZOE_CONTEXT_TOKENS:-2048}" \
        --host 127.0.0.1 --port "$PORT"
      wait_for "$LLAMA_URL" \
        || { log_tail "$ZOE_HOME/llama-server.log"; die "llama-server did not come up"; }
      say "llama-server ready at $LLAMA_URL"
    fi
    ;;
  auto)
    if engine_up "$OLLAMA_HOST"; then
      say "auto: Ollama already running"
    elif command -v ollama >/dev/null 2>&1; then
      say "auto: starting Ollama"
      start_engine "$ZOE_HOME/ollama.log" ollama serve
      if wait_for "$OLLAMA_HOST"; then
        say "auto: Ollama ready"
      else
        warn "auto: Ollama did not start; trying the next engine"
        rm -f "$PIDFILE"
      fi
    fi
    if ! engine_up "$OLLAMA_HOST" && engine_up "$LLAMA_URL"; then
      say "auto: llama-server already running"
    elif ! engine_up "$OLLAMA_HOST" && command -v llama-server >/dev/null 2>&1 \
         && [ -n "${ZOE_GGUF_PATH:-}" ] && [ ! -f "$PIDFILE" ]; then
      PORT="${LLAMA_URL##*:}"
      PORT="${PORT%%/*}"
      say "auto: starting llama-server"
      start_engine "$ZOE_HOME/llama-server.log" \
        llama-server -m "$ZOE_GGUF_PATH" -c "${ZOE_CONTEXT_TOKENS:-2048}" \
        --host 127.0.0.1 --port "$PORT"
      wait_for "$LLAMA_URL" || warn "auto: llama-server did not start"
    fi
    if ! engine_up "$OLLAMA_HOST" && ! engine_up "$LLAMA_URL"; then
      warn "auto: no engine is reachable; Zoe will use the mock fallback"
    fi
    ;;
  mock)
    say "mock backend: no engine needed"
    ;;
  llamacpp|llama-cli)
    [ -n "${ZOE_GGUF_PATH:-}" ] \
      || warn "ZOE_GGUF_PATH is unset; set it so $BACKEND can load a model"
    say "$BACKEND backend: no daemon to start"
    ;;
  *)
    warn "backend '$BACKEND' is managed outside this script"
    ;;
esac

wake_lock
cleanup() {
  if [ "${ZOE_KEEP_AWAKE:-0}" != "1" ]; then
    wake_unlock
  fi
}
trap cleanup EXIT INT TERM

"$PY" -m zoe "$@"
