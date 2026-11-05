"""Opt-in card storage for Emoja.

Default: memory only. A card is written to disk only when the caller passes a
store path or invokes ``/save``. Crisis turns are never written, and ``/drop``
removes the card from both memory and the on-disk file.

This is the T8 deletion surface: after ``/drop`` the card id is absent from
``CardStore.ids()`` and from the JSONL file.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from .agents import EmojaCard


class CardStore:
    def __init__(self, path: Optional[str] = None) -> None:
        self.path = Path(path) if path else None
        self._cards: Dict[str, EmojaCard] = {}
        if self.path and self.path.exists():
            self._load()

    def _load(self) -> None:
        assert self.path is not None
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                self._cards.update({data["emoja_id"]: EmojaCard.from_dict(data)})
            except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                continue

    def put(self, card: EmojaCard) -> None:
        self._cards[card.emoja_id] = card
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(card.to_dict(), ensure_ascii=False) + "\n")

    def get(self, emoja_id: str) -> Optional[EmojaCard]:
        return self._cards.get(emoja_id)

    def update(self, card: EmojaCard) -> None:
        if card.emoja_id in self._cards:
            self._cards[card.emoja_id] = card
            self._rewrite()

    def latest(self) -> Optional[EmojaCard]:
        if not self._cards:
            return None
        return next(reversed(self._cards.values()))

    def ids(self) -> List[str]:
        return list(self._cards)

    def all(self) -> Iterable[EmojaCard]:
        return tuple(self._cards.values())

    def drop(self, emoja_id: str) -> bool:
        if emoja_id not in self._cards:
            return False
        del self._cards[emoja_id]
        self._rewrite()
        return True

    def _rewrite(self) -> None:
        if not self.path:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as handle:
            for card in self._cards.values():
                handle.write(json.dumps(card.to_dict(), ensure_ascii=False) + "\n")

    def export(self, card: EmojaCard, path: str) -> str:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(card.to_dict(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return str(target)
