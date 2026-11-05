# Emoja — the reflection layer of Zoe

**Emoja is the reflection layer of Zoe: Zoe's reservoir/LoRA layers evolve
underneath, Emoja reflects safely on top. It is not therapy, not emotion
detection, and not a diagnostic tool.**

Emoja reflects a user's own words back to them as:

- a 3–5 emoji mini-narrative with one anchor emoji,
- a 3–5 token hex palette blended in OKLCH,
- a pattern described in words (band width = time, saturation = intensity,
  alpha = confidence, direction = sequence order), and
- one plain reflection sentence.

It is a mirror, not a mind-reader. It never claims to know what someone feels —
only what their words point to.

---

## What it is not

- Not therapy, counselling, or a clinical instrument.
- Not face, voice, body, keystroke, or biosignal emotion recognition.
- Not a diagnosis. It does not use "you are X"; it uses "this reads as X" and
  "your words point to X".
- Not a second project. Emoja is a **module of Zoe** (the companion-mode
  front-end), not a split product.
- Not an aesthetic layer over acute pain. When distress is high, the colour,
  emoji, and pattern are dropped and the response is plain.

---

## Status

| Surface | Status |
|---|---|
| Text-only agent pipeline (SUNO → DRISHTI → representation → SETU) | Implemented |
| Emoja Card schema (including `audit`) | Implemented |
| Consent, crisis, `/pause`, `/card`, `/drop`, `/ground` | Implemented |
| Self-check tests T1–T8 | Implemented — `pytest tests/emoja -q` → 8 passed |
| Audit trace input → agents → output | Implemented (opt-in `--trace`) |
| Real Ollama end-to-end run | Pending |
| D1 guided mutation / Dunce rate < 0.20 | Not implemented |
| D4 interviews with neurodivergent users | Not started |

See [`ENFORCEMENT.md`](ENFORCEMENT.md) for the honest per-directive table.

---

## Quick start

```bash
# one reflection
python -m zoe emoja "I felt tired after the meeting but I am steady now"

# machine-readable card
python -m zoe emoja --json "I feel a little sad."

# teaching / debug: show every agent
python -m zoe emoja --mas "I feel a little sad."

# interactive session
python -m zoe emoja

# opt in to a Jataka beat and an audit trace
python -m zoe emoja --katha --trace emoja-trace.jsonl "I am overwhelmed"
```

`zoe-emoja` is the same entry point as `zoe emoja`.

The first turn prints the disclosure once:

> This reflects your own words as color and glyph — it isn't therapy or emotion
> detection. You can pause, correct, or delete anything. Emoja is the reflection
> layer of Zoe; Zoe evolves underneath, Emoja reflects on top.

---

## Commands

| Command | What it does |
|---|---|
| `/card` | Reprint the latest Emoja Card |
| `/save [path]` | Opt-in JSON export of the latest Card |
| `/drop` | Delete the latest Card immediately (deleted means gone) |
| `/pause` | Toggle plain listening; no Card is made |
| `/resume` | Leave plain listening |
| `/ground` | Run the integration rung now |
| `/crisis` | Trigger the crisis protocol now |
| `/mas on\|off` | Show or hide all agent outputs |
| `/katha on\|off` | Opt in or out of the Jataka resilience beat |
| `/consent` | State consent for this session |
| `/help` | List commands |
| `/quit`, `/exit` | Close the session (always grounded) |

Default mode is **single voice**: only SETU speaks. `/mas on` is for teaching
and debugging; it prints every agent output and is not the user-facing default.

---

## The card

```text
Emoja Card · em-4ddcb0a4
words: "I feel a little sad."
cluster: sad
emoji: 🌧️ 💧 🫂 🌱   anchor: 💧
palette: #005d94 / #4f9ee4 / #004d58 / #f8ece0   contrast: PASS
pattern: a narrow band, low saturation, high confidence | intensity 0.20 | steady
shatkona: ground 0.50 ↔ aspire 0.50 | hold 0.50 ↔ release 0.50 | see 0.00 ↔ feel 1.00 → mostly feeling, little seeing
kundalini_max: will   integration: done
jataka: not-run
audit: emoja-13d93ece2aae
sentence: "This reads as sad, mostly feeling, little seeing."
```

### Schema

| Field | Meaning |
|---|---|
| `emoja_id` | Short card id |
| `timestamp` | ISO timestamp |
| `consent` | `yes` in a card; consent is required before a card exists |
| `words` | Verbatim user phrasing |
| `cluster` | 1–3 everyday words taken from the user's own language |
| `emoji` | 3–5 emoji sequence; `anchor` is one of them |
| `palette` | 3–5 hex tokens; `contrast` is `PASS` or `FLAG` |
| `pattern` | Movement in words; `intensity` is 0–1; `direction` is steady/rising/fading |
| `shatkona` | Three axis pairs, each 0–1, plus a flag |
| `kundalini_max` | The symbolic depth rung the turn was allowed to reach |
| `integration` | `done` or `pending` |
| `jataka` | `offered`, `accepted`, `declined`, or `not-run` |
| `audit` | Trace id linking input → agents composed → output |
| `sentence` | Exactly one plain sentence |

When distress is high, `emoji`, `palette`, and `pattern` are empty and the card
carries `aesthetics: suppressed (plain mode over acute pain)`.

---

## Agents and trust boundary

```
SUNO (perception) → DRISHTI (policy) → MUDRA/RANG/BINDU (representation)
                  → KATHA (optional) → SETU (orchestrator)
```

| Agent | Input | Output |
|---|---|---|
| **SUNO** | Raw user text | Typed `SunoReading`: verbatim words, tokens, cluster, categories, distress, crisis flag |
| **DRISHTI** | `SunoReading` + consent | Consent/crisis/rung decision, Shatkona scores, skew, veto |
| **MUDRA** | `SunoReading` | 3–5 emoji + anchor |
| **RANG** | `SunoReading` | 3–5 hex tokens, OKLCH blend, contrast check, optional Five Elements tag |
| **BINDU** | `SunoReading` | Pattern movement, intensity 0–1, direction |
| **KATHA** | `SunoReading` + opt-in/distress | One Jataka resilience beat, offered never instructed |
| **SETU** | All typed outputs | Card, one sentence, named skew, audit trace |

**SUNO is the sole input to every other agent.** Raw text never reaches the
aesthetic agents. DRISHTI's pre-check consumes SUNO's typed safety flags, not a
second raw-text path, so the boundary is explicit in code.

**DRISHTI's veto is enforced.** If DRISHTI vetoes aesthetics, SETU does not
assemble MUDRA/RANG/BINDU output at all. This is not an advisory prompt rule.

---

## Routing

1. SUNO mirrors the user's words and produces the typed reading.
2. DRISHTI pre-checks consent, crisis, and distress, sets the Kundalini max rung,
   scores Shatkona, and may veto.
3. MUDRA, RANG, and BINDU run on SUNO's cluster (not raw text).
4. KATHA runs only if opted in or distress > 0.5, and never in crisis.
5. DRISHTI's veto is applied before SETU assembles the card.
6. SETU merges the card, one sentence, and the named skew.
7. On session close, the integration rung runs. It is not optional.

---

## Shatkona balance check

Each axis pair is scored 0–1 from the user's own words:

| Pair | Grounded in |
|---|---|
| `ground ↔ aspire` | stability/rest vs. growth/future language |
| `hold ↔ release` | containment/control vs. letting-go language |
| `see ↔ feel` | cognition/observation vs. affect language |

If a pair differs by more than **0.4**, the skew is flagged and named in the
sentence, e.g. **“mostly feeling, little seeing.”** The scores describe the
balance of the language, not a diagnosis of the person.

---

## Kundalini depth ladder

Symbolic permission, not energy and not a metaphysical claim:

```
ground → feel → will → compassion → voice → insight
```

- The max rung is set each turn from consent and distress.
- No agent may exceed the max rung.
- Higher rung means more interpretive depth, not more drama.
- Crisis and high distress cap the turn at `ground`/`feel`.
- Integration (return to ground) always runs before close.

---

## Jataka guardrails

Jataka is Buddhist canonical literature; it is cited as such, kept opt-in, and
never commercialised.

| Rule | Behaviour |
|---|---|
| J1 non-harm | Never sharpen a negative state for aesthetic effect |
| J2 no moralising | KATHA offers, never instructs; one beat max |
| J3 long view | Impermanence only when the user's words allow it |
| J4 drop aesthetics | High distress kills colour/emoji/pattern; plain and warm |
| J5 attribution | Cite Jataka as Buddhist canonical literature; opt-in only |
| J6 integration | End grounded, always |
| J7 reversibility | `/drop` deletes the card; deleted means gone |

KATHA is skipped entirely in crisis.

---

## Crisis protocol

**Trigger:** self-harm, harm to others, or acute distress.

- All aesthetic agents (MUDRA, RANG, BINDU, KATHA) are killed. **Enforced.**
- No card, no palette, no emoji. **Enforced.**
- The response is plain, warm, and brief; it acknowledges specifically.
- No lecture, no diagnosis.
- One gentle suggestion to reach a trusted person or a local emergency service.
- The session offers to stay in plain listening mode.
- The crisis path writes no card, no trace, and no ledger entry.

> **Honest label:** “retain nothing” is **ASPIRATIONAL** until the T8 deletion
> test passes in production with a user-controlled store. In the current code
> path the crisis turn allocates no card/trace and performs no write, and T8
> verifies `/drop` removal in a temporary store.

---

## Self-check as tests

`pytest tests/emoja -q` runs exactly these eight checks:

| Test | Check |
|---|---|
| **T1** inference | Output tokens are derived from SUNO's reading (plus fixed scaffolding) |
| **T2** distress | High-distress fixture → zero aesthetic agents |
| **T3** shatkona | Skew > 0.4 is named in the sentence |
| **T4** rung | `kundalini_max` is never exceeded across fixtures |
| **T5** sentence | Exactly one reflection sentence, bounded length |
| **T6** diagnostic | Regex bans “you are”, “diagnos”, “disorder”, “I sense that” |
| **T7** crisis | Crisis fixture → plain output, zero card, zero trace/log |
| **T8** deletion | `/drop` removes the card from storage (verified absent) |

The tests run on the deterministic, text-only pipeline; they do not require
Ollama or a GPU.

To run one real-backend demo and log a trace:

```bash
ZOE_LLM_BACKEND=ollama python -m zoe emoja --trace emoja-trace.jsonl \
  "I felt tired after the meeting but I am steady now"
```

---

## Fellowship roadmap (honest status)

| Deliverable | Check | Status |
|---|---|---|
| **D1** Guided mutation reduces Dunce rate 0.375 → < 0.20 | `python -m zoe report` → M-4.2 PASS | **Not implemented.** M-4.2 still fails at 0.375; guided mutation is future work. |
| **D2** Emoja self-check as tests T1–T8 on the real Ollama backend | `pytest tests/emoja -q` → 8 passed; one logged `zoe report --backend ollama` run | **Tests implemented (8 passed).** Real-backend run still pending. |
| **D3** Audit trace records input → agents composed → output | Sample trace file from one demo-mode run | **Implemented.** `--trace PATH` writes JSONL; the card carries the trace id. |
| **D4** 3 user interviews with neurodivergent users | Written notes + which design choices changed | **Not started.** |

D1 is deliberately not claimed as done. The prompt's P7 rule applies: a
directive that exists only as a prompt rule is labelled **ASPIRATIONAL**.

---

## Scope boundary

Emoja is a **module of Zoe**, not a second project:

- **Zoe** = reservoir / LoRA / evolution underneath.
- **Emoja** = consented reflection on top.
- One application. One primary user: neurodivergent users seeking a
  predictable, non-diagnostic reflection tool.
- Emoja is the hypothesis; interviews validate it.

**One-sentence application statement:**

> Zoe is a local-first companion with brain-inspired layers; Emoja is its
> consented, non-diagnostic reflection layer, initially aimed at neurodivergent
> users — the fellowship goal is to implement Emoja's self-check as tests and
> validate that audience through interviews.

---

## Code map

| Path | Responsibility |
|---|---|
| `zoe/emoja/lexicon.py` | Text-only word lists, distress salience, crisis patterns |
| `zoe/emoja/agents.py` | SUNO, DRISHTI, MUDRA, RANG, BINDU, KATHA, SETU, card, audit |
| `zoe/emoja/session.py` | Routing, commands, consent, integration, storage hooks |
| `zoe/emoja/storage.py` | Opt-in JSONL store; `/drop` deletion |
| `zoe/emoja/cli.py` | `zoe emoja` / `zoe-emoja` |
| `tests/emoja/test_self_check.py` | T1–T8 |
| `docs/ENFORCEMENT.md` | Per-directive honesty table |

---

## Related

- [Zoe README](../README.md)
- [Architecture](ARCHITECTURE.md)
- [Enforcement status](ENFORCEMENT.md)
- [Termux guide](TERMUX.md)
