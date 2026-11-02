# Project Zoe on Termux (Android)

Zoe runs on a phone. All 11 layers are pure Python + NumPy, and Layer 3 (the
frozen base model) now has interchangeable local engines, so the same rig that
runs on a laptop runs on Termux with **Ollama** or **llama.cpp** doing the
generation.

Nothing is downloaded at runtime, no API keys are needed, and the deterministic
mock engine still works with zero models installed.

```
Termux  ->  python + numpy  ->  Zoe rig (L1..L11)
                                    |
                                    +-- L3 backend: ollama | llama-server
                                                   | llamacpp | llama-cli
                                                   | mock (fallback)
```

## Requirements

| | |
|---|---|
| Termux | installed from **F-Droid** or GitHub, *not* the Play Store build |
| Android | 8.0+ recommended |
| Storage | ~500 MB for Zoe + 0.5B model; ~2 GB for a 1–3B model |
| RAM | 2 GB works with 0.5B models; 4 GB+ for 1–3B |
| Python | 3.10+ (`pkg install python`) |

## Quick install

```bash
pkg install git -y
git clone https://github.com/karun99/zoe.git
cd zoe
bash scripts/termux-install.sh
```

The script installs `python`, `python-numpy`, build tools and Ollama, creates a
virtualenv at `~/.zoe/venv`, writes `~/.zoe/env`, pulls `qwen2.5:0.5b`, and runs
`zoe doctor`.

Then:

```bash
source ~/.zoe/env
zoe doctor
zoe run "build and implement a plan"
```

### Options

```bash
bash scripts/termux-install.sh --model llama3.2:1b     # bigger, slower, better
bash scripts/termux-install.sh --no-ollama             # mock engine only
bash scripts/termux-install.sh --backend llama-cli \
     --model-file ~/models/qwen2.5-0.5b-instruct-q4_k_m.gguf
```

## Choosing a model

Measured on a mid-range ARM phone (8 cores, no GPU). Treat these as orders of
magnitude, not promises.

| model | disk | RAM | speed | use |
|---|---|---|---|---|
| `qwen2.5:0.5b` | ~400 MB | ~1 GB | fast | default; routing/demo/benchmarks |
| `llama3.2:1b` | ~1.3 GB | ~2 GB | ~5–15 tok/s | noticeably better prose |
| `qwen2.5:1.5b` | ~1 GB | ~2 GB | ~4–10 tok/s | best small-model quality |
| `phi3:mini` | ~2.2 GB | ~3.5 GB | slow | only on 6 GB+ devices |

Small models are the point: L1/L2/L4/L9–L11 do the control work, so Zoe's
structure does not depend on the model being large.

## Backends

`ZOE_LLM_BACKEND` selects the engine. `zoe backends` shows what is installed,
`zoe doctor` shows what is actually reachable.

| backend | how it runs | Termux |
|---|---|---|
| `ollama` | HTTP `127.0.0.1:11434/api/chat` | **recommended** — `pkg install ollama` |
| `llama-server` | HTTP `127.0.0.1:8080/v1/chat/completions` | `pkg install llama-cpp` |
| `llama-cli` | subprocess per call | `pkg install llama-cpp`, no server needed |
| `llamacpp` | in-process `llama-cpp-python` | needs clang; slow to build |
| `mock` | deterministic, in-process | always available |
| `auto` | first engine that answers | tries ollama → llama-server → llamacpp → llama-cli |

```bash
zoe --backend ollama --model qwen2.5:0.5b run "help me plan the day"
zoe --backend llama-server run "help me plan the day"
ZOE_LLM_BACKEND=auto zoe doctor
```

If a real engine fails mid-run, Zoe **falls back to mock and says so** — the
result is marked `mock=True` / `degraded=True` instead of pretending. Set
`ZOE_LLM_FALLBACK_MOCK=false` to make failures loud instead.

## Configuration

Every knob is a `ZOE_*` environment variable (`zoe/config.py`).

| variable | default | meaning |
|---|---|---|
| `ZOE_LLM_BACKEND` | `mock` | engine name (see above) |
| `ZOE_OLLAMA_HOST` | `http://127.0.0.1:11434` | Ollama daemon |
| `ZOE_OLLAMA_MODEL` | `qwen2.5:0.5b` | model tag |
| `ZOE_OLLAMA_KEEP_ALIVE` | `5m` | how long Ollama keeps the model in RAM |
| `ZOE_LLAMA_SERVER_URL` | `http://127.0.0.1:8080` | llama-server endpoint |
| `ZOE_LLAMA_CLI_BINARY` | `llama-cli` | CLI binary name/path |
| `ZOE_LLAMA_CLI_ARGS` | *(empty)* | extra CLI flags, shell-quoted |
| `ZOE_GGUF_PATH` | *(empty)* | `.gguf` for `llamacpp` / `llama-cli` |
| `ZOE_LLM_TIMEOUT_S` | `120` | per-completion timeout |
| `ZOE_LLM_PROBE_TIMEOUT_S` | `1.5` | reachability probe timeout |
| `ZOE_LLM_RETRY_AFTER_S` | `30` | cooldown after a failed call |
| `ZOE_LLM_TEMPERATURE` | `0.7` | base sampling temperature |
| `ZOE_LLM_MAX_TOKENS` | `128` | completion cap |
| `ZOE_CONTEXT_TOKENS` | `2048` | context window |
| `ZOE_LEDGER_PATH` | `.kali-ledger/ledger.jsonl` | append-only Kali ledger |

## Day-to-day use

```bash
bash scripts/termux-start.sh run "warn me about the unsafe risk here"
bash scripts/termux-start.sh report
bash scripts/termux-start.sh --stop        # stop engine, release wake lock
```

`termux-start.sh` takes a wake lock (`termux-wake-lock`) so Android does not
freeze the engine when the screen turns off, starts Ollama/llama-server if
needed, then runs Zoe.

### MCP server

```bash
zoe-mcp            # stdio JSON-RPC: zoe_run, zoe_report, zoe_layers, zoe_identity
```

Register it in any MCP client with the environment included:

```json
{
  "mcpServers": {
    "zoe": {
      "command": "/data/data/com.termux/files/home/.zoe/venv/bin/zoe-mcp",
      "env": {
        "ZOE_LLM_BACKEND": "ollama",
        "ZOE_OLLAMA_MODEL": "qwen2.5:0.5b"
      }
    }
  }
}
```

MCP is stdio-only, so the client must run on the same device (opencode in
Termux, for example). To drive Zoe from a laptop, run the client on the phone
over SSH instead of exposing the socket.

## What stays the same on a phone

| layer | on Termux |
|---|---|
| L1 Flybrain reservoir | full NumPy LIF simulation (2 000 neurons by default) |
| L2 Prompt-as-Harness | full routing, 5-line format, growth signal |
| L3 base model | Ollama / llama.cpp / mock |
| L3 LoRA adapter | evolves identically; steers sampling (see below) |
| L4 Kali + Dunce | full |
| L5 MCP + Prompt API | full |
| L6 Avatar | full (text frames; no screen) |
| L7 AI VM | `MockVM` — Firecracker needs KVM, which Android does not expose |
| L8 Companion mode | works, but `mss`/`pytesseract` screen capture is not available |
| L9 Sahaja / L10 Jataka / L11 PIA | full |

### Honest note on the adapter

On a real engine the base weights are frozen inside another process, so the
evolved LoRA adapter cannot be merged into them. Zoe therefore uses the adapter
as a **controller**: its winning salience lane and activation intensity set the
temperature and the tone directive for each call (`LlamaCppModel.steer`). The
accuracy/loss metrics still come from the adapter's own probe, so the evolution
loop measures the same thing it always did. This is a controller, not a weight
merge — it is documented that way in `docs/ARCHITECTURE.md`.

## Performance and battery

* Use `q4_k_m` / `q4_0` quantised models; they are 2–4× faster than `q8_0`.
* `ZOE_OLLAMA_KEEP_ALIVE=30m` avoids a cold reload between turns, at the cost of
  RAM.
* `ZOE_LLM_MAX_TOKENS=64` roughly halves latency for chat-style use.
* Keep the phone plugged in for `zoe report` (200 evolution generations).
* `zoe report` and `zoe train` do **not** call the model — they exercise the
  adapter/benchmark path, so they are cheap even on a phone.

## Troubleshooting

| symptom | fix |
|---|---|
| `numpy` fails to build | `pkg install python-numpy`; do not `pip install numpy` on Termux |
| `ollama: cannot reach …` | `ollama serve` (or `bash scripts/termux-start.sh`) |
| `model_present: false` | `ollama pull qwen2.5:0.5b` |
| generation is very slow | smaller model, `ZOE_LLM_MAX_TOKENS=64`, keep-alive on |
| `zoe doctor` says backend fail | run `zoe backends` to see what is installed |
| app killed in background | `termux-wake-lock`, disable battery optimisation for Termux |
| `pkg` mirror timeouts | `termux-change-repo`, then retry |
| `pkg` cannot find `ollama` / `llama-cpp` | `pkg install tur-repo`, then retry |
| `llama-cli` flag errors | set `ZOE_LLAMA_CLI_ARGS` to your build's flags |

## Uninstall

```bash
bash scripts/termux-start.sh --stop
rm -rf ~/.zoe
pip uninstall zoe        # if installed with --no-venv
```
