# Emoja enforcement status

This file is deliberately blunt. A rule is a **control** only when code or a
test enforces it. A rule that lives only in a prompt is labelled
**ASPIRATIONAL**. That is the P7 rule applied to this document itself.

Run the evidence:

```bash
pytest tests/emoja -q          # 8 passed: T1-T8
pytest -q                      # full Zoe suite
```

---

## Per-directive table

| Directive | Status | Evidence in code / tests |
|---|---|---|
| **P1 Consent** | **ENFORCED** | `EmojaSession(consent=False)` returns a consent prompt and no card. The CLI treats an explicit `zoe emoja "..."` invocation as consent; MCP accepts a `consent` argument. No sensor API is imported anywhere in `zoe/emoja/`. |
| **P2 Non-harm** | **ENFORCED** | `Drishti.precheck` sets `veto_aesthetics`; `Setu.assemble` only builds MUDRA/RANG/BINDU when the veto is false. T2 covers the high-distress path. |
| **P3 Plain over poetic** | **ENFORCED** | Crisis returns `Setu._CRISIS_TEXT` with no card. High distress suppresses emoji/palette/pattern. T2 and T7. |
| **P4 Integration** | **ENFORCED** | `EmojaSession.close()` calls `ground()` when `integration_pending`; `ground()` marks the card `integration: done`. The CLI calls `close()` on one-shot and REPL exit. |
| **P5 Transparency** | **ENFORCED** | `/card` reprints, `/drop` deletes, `/pause` toggles plain listening. Storage is memory-only unless `--store`/`/save` is used. T8 covers deletion. |
| **P6 No diagnosis** | **PARTIAL** | T6 regex blocks “you are”, “diagnos”, “disorder”, and “I sense that”. Regex catches known patterns only; it is not a semantic classifier. |
| **P7 Enforcement honesty** | **N/A** | This document. |
| **Crisis “retain nothing”** | **ASPIRATIONAL** | The crisis path allocates no card/trace and performs no write; T7 verifies this on a temporary store. Production retention is not independently audited yet, so the stronger claim stays aspirational. |
| **All unlisted prompt rules** | **ASPIRATIONAL** | See the next section. |

---

## What is actually wired

### ENFORCED in code

- **SUNO is the sole raw-text input.** `Drishti.precheck` takes a
  `SunoReading`, and MUDRA/RANG/BINDU/KATHA take the same typed object. There is
  no second `text` parameter on the aesthetic agents.
- **DRISHTI veto blocks assembly.** `Setu.assemble` checks
  `verdict.veto_aesthetics` and leaves the aesthetic fields empty; it does not
  merely ask an LLM to comply.
- **Crisis kills aesthetics.** `EmojaSession.reflect` returns
  `Setu.crisis(reading)` before any aesthetic agent is constructed.
- **High distress kills aesthetics.** `Drishti` returns
  `veto_aesthetics=True` for `distress >= 0.55`; J4 is enforced by the same
  branch.
- **Integration on close.** `close()` calls `ground()`; one-shot CLI mode
  closes before printing so the card shows `integration: done`.
- **`/drop` deletion.** `CardStore.drop()` deletes from memory and rewrites the
  opt-in JSONL file. T8 asserts the id is absent from both.

### PARTIAL

- **Diagnostic-language ban.** T6 is a regex. It catches the named patterns and
  nothing else. A determined paraphrase can pass the regex.
- **Consent in MCP.** The MCP tool defaults `consent=true` for a direct call and
  accepts `consent=false`; a client could ignore the flag. The CLI and Python
  API require the caller to state consent explicitly or use `--consent`.

### ASPIRATIONAL (not enforced)

These appear in the prompt but are not currently controls:

- “No covert monitoring or logging” beyond the Emoja store: the wider Zoe rig
  has its own `KaliLedger`; Emoja does not add to it, but this document does not
  audit the rest of Zoe.
- “No moralising, lecturing, or unsolicited advice” — KATHA is written as an
  offer and is opt-in/threshold-gated, but no runtime classifier blocks every
  possible lecture.
- “No metaphysical claims about Kundalini, chakras, or energy” — the rung is
  named `kundalini_max` for continuity with the prompt and is documented as a
  symbolic depth scale. There is no runtime detector for metaphysical language.
- “No commercializing or flattening Jataka/Buddhist material” — Jataka is
  opt-in, cited as Buddhist canonical literature, and not sold. This is a
  documentation/design commitment, not a code check.
- “Never output a palette over acute pain” — enforced for the Emoja high-distress
  and crisis paths (T2/T7), but not for arbitrary third-party output.
- “Exactly one reflection sentence” — enforced by construction and tested by
  T5, but a future agent change could bypass `Setu.sentence`.
- “No inference from face, voice, body, keystrokes, or biosignals” — there is no
  such input in `zoe/emoja/`; the repository does have separate companion-mode
  screen awareness (L8) behind explicit start. Emoja itself does not call it.

---

## Crisis retention: why the label is aspirational

The current crisis path:

1. `Suno` flags the turn,
2. `Drishti` sets `max_rung="ground"` and vetoes aesthetics,
3. `EmojaSession.reflect` returns `Setu.crisis(...)` **before** `store.put`,
   `make_audit`, or `_write_trace`.

T7 asserts:

- `turn.crisis is True`, `turn.card is None`;
- `session.store.ids() == []`;
- `session.traces == []`;
- the opt-in store file is absent or empty;
- the opt-in trace file is absent;
- the text contains no palette or hex token.

That is strong evidence, but it is a test of the current code path, not an
independent production retention audit. The honest label remains
**ASPIRATIONAL** for the full claim.

---

## Test mapping

| Test | File | What it proves |
|---|---|---|
| T1 inference | `tests/emoja/test_self_check.py` | Output tokens derive from SUNO + fixed scaffolding |
| T2 distress | same | High distress → no aesthetics |
| T3 shatkona | same | Skew > 0.4 named in the sentence |
| T4 rung | same | No agent exceeds `kundalini_max` |
| T5 sentence | same | Exactly one bounded reflection sentence |
| T6 diagnostic | same | Banned diagnostic strings absent |
| T7 crisis | same | No card, no trace, no store write |
| T8 deletion | same | `/drop` removes the card from storage |

---

## Known gaps

- **D1 not done.** `python -m zoe report` still shows M-4.2 Dunce rate at 0.375,
  above the < 0.20 target. No guided-mutation work is claimed.
- **D2 real backend pending.** T1–T8 pass on the deterministic pipeline. A
  logged Ollama run has not been recorded in this repository.
- **D4 interviews not started.** No user interviews with neurodivergent users
  have been conducted, so no design changes are claimed from them.
- **P6 is partial.** Regex is not a semantic safety classifier.
