"""Emoja session: routing, commands, consent, and integration.

Every turn follows the same order:

    SUNO -> DRISHTI pre-check -> MUDRA/RANG/BINDU (parallel in intent)
         -> KATHA (opt-in or distress > 0.5) -> DRISHTI veto -> SETU

SUNO is the sole input to the other agents. DRISHTI's pre-check consumes
SUNO's typed safety flags, not raw text, so the trust boundary is explicit.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .agents import (
    Bindu,
    BinduOutput,
    Drishti,
    DrishtiVerdict,
    EmojaTurn,
    Katha,
    KathaOutput,
    Mudra,
    MudraOutput,
    Rang,
    RangOutput,
    Setu,
    Suno,
    SunoReading,
    make_audit,
)
from .storage import CardStore

_GROUNDING = (
    "Feet on the floor. One slow breath. Name one thing you can see, one you "
    "can hear, one you can feel. That's enough for now."
)

_HELP = """Emoja commands
  /card            reprint the latest Emoja Card
  /save [path]     opt-in export of the latest Card (JSON)
  /drop            delete the latest Card immediately
  /pause           toggle plain listening, no Card
  /resume          leave plain listening
  /ground          run the integration rung now
  /crisis          trigger the crisis protocol now
  /mas on|off      show all agent outputs (teaching/debug)
  /katha on|off    opt in or out of the Jataka resilience beat
  /consent         state consent for this session
  /help            show this list
  /quit or /exit   close the session (always grounded)"""


@dataclass
class EmojaCommand:
    text: str
    card: None = None


class EmojaSession:
    def __init__(
        self,
        *,
        consent: bool = False,
        mas: bool = False,
        katha_opt_in: bool = False,
        store: Optional[str] = None,
        trace_path: Optional[str] = None,
        deep: bool = False,
    ) -> None:
        self.consent = consent
        self.mas = mas
        self.katha_opt_in = katha_opt_in
        self.deep = deep
        self.store = CardStore(store)
        self.trace_path = Path(trace_path) if trace_path else None
        self.traces: List[Dict[str, Any]] = []
        self.turn_index = 0
        self.last_turn: Optional[EmojaTurn] = None
        self.last_card = None
        self.paused = False
        self.integration_pending = False
        self._previous_intensity: Optional[float] = None

        self.suno = Suno()
        self.drishti = Drishti()
        self.mudra = Mudra()
        self.rang = Rang()
        self.bindu = Bindu()
        self.katha = Katha()
        self.setu = Setu()

    # --------------------------------------------------------------- turns
    def reflect(self, text: str) -> EmojaTurn:
        words = " ".join((text or "").strip().split())
        if not words:
            return self._empty_turn()

        reading = self.suno.listen(words)

        if self.paused:
            turn = self.setu.paused_turn(reading)
            self.last_turn = turn
            return turn

        verdict = self.drishti.precheck(
            reading, self.consent, self.katha_opt_in, self.deep
        )

        if not self.consent:
            turn = self.setu.consent_prompt(reading)
            self.last_turn = turn
            return turn

        if reading.crisis:
            turn = self.setu.crisis(reading)
            # Crisis: retain nothing. No card, no trace, no ledger write.
            self.last_turn = turn
            return turn

        mudra: Optional[MudraOutput] = None
        rang: Optional[RangOutput] = None
        bindu: Optional[BinduOutput] = None
        if not verdict.veto_aesthetics:
            mudra = self.mudra.render(reading)
            rang = self.rang.render(reading)
            bindu = self.bindu.render(
                reading, self.turn_index, self._previous_intensity
            )

        katha: Optional[KathaOutput] = self.katha.maybe_offer(
            reading, self.katha_opt_in
        )

        composed = ["SUNO", "DRISHTI"]
        for name, value in (
            ("MUDRA", mudra), ("RANG", rang), ("BINDU", bindu), ("KATHA", katha)
        ):
            if value is not None:
                composed.append(name)
        composed.append("SETU")

        audit = make_audit(
            reading, composed,
            self.setu.sentence(reading, verdict) + "|" + verdict.shatkona_flag,
        )
        turn = self.setu.assemble(
            reading, verdict, mudra=mudra, rang=rang, bindu=bindu, katha=katha,
            audit=audit["trace_id"], turn_index=self.turn_index, mas=self.mas,
        )
        self.traces.append(audit)
        self._write_trace(audit)

        if turn.card is not None:
            self.store.put(turn.card)
            self.last_card = turn.card
        self.last_turn = turn
        self.integration_pending = True
        self.turn_index += 1
        self._previous_intensity = (
            bindu.intensity if bindu is not None else reading.distress
        )
        return turn

    def handle(self, line: str) -> Union[EmojaTurn, EmojaCommand]:
        line = (line or "").strip()
        if not line:
            return EmojaCommand("Say a few words when you are ready.")

        if not line.startswith("/"):
            return self.reflect(line)

        command, _, argument = line.partition(" ")
        command = command.lower()
        argument = argument.strip()

        if command in {"/quit", "/exit"}:
            self.close()
            return EmojaCommand("Session closed grounded.")
        if command == "/help":
            return EmojaCommand(_HELP)
        if command == "/consent":
            self.consent = True
            return EmojaCommand(
                "Consent recorded for this session. You can pause, correct, "
                "or delete anything."
            )
        if command == "/pause":
            self.paused = not self.paused
            if self.paused:
                return EmojaCommand(
                    "Plain listening is on. No card will be made until /resume."
                )
            return EmojaCommand("Plain listening is off; cards are on again.")
        if command == "/resume":
            self.paused = False
            return EmojaCommand("Plain listening is off; cards are on again.")
        if command == "/mas":
            state = argument.lower()
            if state not in {"on", "off"}:
                return EmojaCommand("Use /mas on or /mas off.")
            self.mas = state == "on"
            return EmojaCommand(f"/mas {state}.")
        if command == "/katha":
            state = argument.lower()
            if state not in {"on", "off"}:
                return EmojaCommand("Use /katha on or /katha off.")
            self.katha_opt_in = state == "on"
            return EmojaCommand(f"Jataka beat opt-in is {state}.")
        if command == "/card":
            if self.last_card is None:
                return EmojaCommand("No card yet. Say something when you are ready.")
            return EmojaCommand(self.last_card.render())
        if command == "/save":
            if self.last_card is None:
                return EmojaCommand("No card to save yet.")
            path = argument or "emoja-card.json"
            saved = self.store.export(self.last_card, path)
            return EmojaCommand(f"Card saved to {saved} (opt-in export).")
        if command == "/drop":
            card = self.last_card or self.store.latest()
            if card is None:
                return EmojaCommand("No card to delete.")
            self.store.drop(card.emoja_id)
            if self.last_card is not None and self.last_card.emoja_id == card.emoja_id:
                self.last_card = None
            return EmojaCommand(
                f"Card {card.emoja_id} deleted. Deleted means gone."
            )
        if command == "/ground":
            return EmojaCommand(self.ground())
        if command == "/crisis":
            self.last_turn = self.setu.crisis_now()
            return self.last_turn
        return EmojaCommand(f"Unknown command: {command}. Try /help.")

    # ------------------------------------------------------------ lifecycle
    def ground(self) -> str:
        self.integration_pending = False
        if self.last_card is not None and self.last_card.integration != "done":
            self.last_card.integration = "done"
            self.store.update(self.last_card)
        return _GROUNDING

    def close(self) -> str:
        if self.integration_pending:
            self.ground()
        return "integration: done"

    # --------------------------------------------------------------- helper
    def _write_trace(self, trace: Dict[str, Any]) -> None:
        if self.trace_path is None:
            return
        self.trace_path.parent.mkdir(parents=True, exist_ok=True)
        with self.trace_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(trace, ensure_ascii=False) + "\n")

    def _empty_turn(self) -> EmojaTurn:
        sentence = "Say a few words when you are ready; I will reflect only those."
        return EmojaTurn(
            text=sentence, card=None, sentence=sentence, plain=True,
            crisis=False, consent=self.consent, paused=self.paused,
            distress=0.0, max_rung="ground", max_agent_rung="ground",
            shatkona=Setu._flat_shatkona(), skews=(),
        )
