---
name: zoe
description: A bio-inspired AI companion built on a fruit-fly connectome reservoir with 11 layers. MCP server by Sai Karun Nandipati. Use when a task needs connectome capabilities.
---

# Project Zoe

A bio-inspired AI companion built on a fruit-fly connectome reservoir with 11 layers.

Project Zoe is an MCP (Model Context Protocol) server by Sai Karun Nandipati. It is built by the author, not yet published to a registry.

## What it does

- Runs text through an 11-layer reservoir-computing model inspired by a Drosophila connectome.
- Optionally evolves the reservoir for N generations to raise novelty (controlled, bounded).
- Reports what happened and exposes the role of each of the 11 layers.
- Carries a persistent identity card so the companion stays stable across sessions.
- Ships **Emoja**, a consented, non-diagnostic reflection layer that turns the user's own words into an emoji sequence, a hex palette, a blended pattern, and one plain sentence.

## Emoja (reflection layer)

Emoja is a module of Zoe, not a second project. It is text-only: no face, voice,
body, keystroke, or biosignal input. It is not therapy, emotion detection, or a
diagnostic tool. The trust boundary is explicit — SUNO is the only agent that
sees the raw turn; DRISHTI holds an enforced veto over aesthetic output.

```bash
zoe emoja "I felt tired after the meeting but I am steady now"
zoe emoja --json "I feel a little sad."
zoe emoja --mas "I feel a little sad."       # show every agent
zoe emoja                                     # interactive session
zoe-emoja "I am overwhelmed"                  # same entry point
```

Commands: `/card`, `/save`, `/drop`, `/pause`, `/resume`, `/ground`, `/crisis`,
`/mas on|off`, `/katha on|off`, `/consent`, `/help`, `/quit`.

Self-check tests T1–T8 live in `tests/emoja/` (`pytest tests/emoja -q` → 8
passed). The honest per-directive enforcement table is in `docs/ENFORCEMENT.md`.
D1 guided mutation (Dunce < 0.20), D2's real-Ollama run, and D4 interviews are
**not** claimed as complete.

## Tools it exposes

- **zoe_run** — Feed input text; optional novelty in [0,1] and generations (default 200).
- **zoe_report** — Get a report of the run (optional generations).
- **zoe_layers** — List the eleven Zoe layers, their roles, and the Emoja module.
- **zoe_identity** — Return Zoe's persistent identity card.
- **emoja_reflect** — Reflect the user's own words as a consented Emoja Card (text-only; no diagnosis).
- **emoja_card** — Reprint the latest Emoja Card.
- **emoja_drop** — Delete the latest Emoja Card (deleted means gone).

## How to use it

**Install**
```
pip install zoe
```

**Command line**
```
zoe
```

**Run the MCP server**
```
zoe-mcp
```

**Add to an MCP client** (claude_desktop_config.json, .mcp.json, etc.)
```json
{ "mcpServers": { "zoe": { "command": "zoe-mcp" } } }
```

**On a phone (Termux)**
```bash
pkg install git -y && git clone https://github.com/karun99/zoe.git && cd zoe
bash scripts/termux-install.sh      # python-numpy + Ollama + qwen2.5:0.5b
source ~/.zoe/env
zoe run "build and implement a plan"
```

Layer 3 (the base model) is pluggable via `ZOE_LLM_BACKEND`:
`ollama` (default on Termux), `llama-server`, `llamacpp`, `llama-cli`, `auto`,
or `mock`. Check the device with `zoe doctor`; list engines with `zoe backends`.
All 11 layers are unchanged — only the generation engine moves.
See `docs/TERMUX.md` for model sizes, wake locks and troubleshooting.

## Links

- Repository: https://github.com/karun99/zoe
- Author: https://karun99.github.io

## Notes

Paste this file into any AI tool (Claude, ChatGPT, Cursor, opencode) as context and the tool can drive Project Zoe.
Verify tool availability at run time — pending servers may not be reachable until published.
