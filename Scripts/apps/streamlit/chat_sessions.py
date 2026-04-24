"""Persistência e estado das conversas (histórico entre recarregamentos da página)."""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _data_dir() -> Path:
    override = os.environ.get("LAB_CHAT_DATA_DIR")
    if override:
        return Path(override)
    return Path(__file__).resolve().parent / "data"


def _sessions_path() -> Path:
    d = _data_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d / "chat_sessions.json"


@dataclass
class Message:
    role: str  # "user" | "assistant"
    content: str
    ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict[str, Any]) -> Message:
        return Message(
            role=d["role"],
            content=d["content"],
            ts=d.get("ts") or datetime.now(timezone.utc).isoformat(),
        )


@dataclass
class Conversation:
    id: str
    title: str
    updated_at: str
    messages: list[Message] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "updated_at": self.updated_at,
            "messages": [m.to_dict() for m in self.messages],
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> Conversation:
        return Conversation(
            id=d["id"],
            title=d.get("title") or "Nova conversa",
            updated_at=d.get("updated_at") or datetime.now(timezone.utc).isoformat(),
            messages=[Message.from_dict(m) for m in d.get("messages") or []],
        )


def load_store() -> tuple[dict[str, Conversation], str | None]:
    path = _sessions_path()
    if not path.exists():
        return {}, None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}, None
    out: dict[str, Conversation] = {}
    for item in raw.get("conversations", []):
        c = Conversation.from_dict(item)
        out[c.id] = c
    current = raw.get("current_id")
    if current and current not in out:
        current = None
    return out, current if isinstance(current, str) else None


def save_store(conversations: dict[str, Conversation], current_id: str | None) -> None:
    path = _sessions_path()
    payload = {
        "current_id": current_id,
        "conversations": [c.to_dict() for c in sorted(conversations.values(), key=lambda x: x.updated_at, reverse=True)],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def new_conversation() -> Conversation:
    now = datetime.now(timezone.utc).isoformat()
    return Conversation(id=str(uuid.uuid4()), title="Nova conversa", updated_at=now, messages=[])


def touch(conv: Conversation) -> None:
    conv.updated_at = datetime.now(timezone.utc).isoformat()


def infer_title_from_messages(conv: Conversation) -> None:
    if conv.title != "Nova conversa":
        return
    for m in conv.messages:
        if m.role == "user" and m.content.strip():
            text = m.content.strip().replace("\n", " ")
            conv.title = text[:48] + ("…" if len(text) > 48 else "")
            return
