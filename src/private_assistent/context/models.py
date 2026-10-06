from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

MessageRole = Literal["system", "user", "assistant"]


@dataclass(frozen=True)
class ContextConfig:
    """Window policy for the lightweight live context builder."""

    max_messages: int = 20
    max_chars: int = 12000


@dataclass(frozen=True)
class StoredMessage:
    id: str
    session_id: str
    seq: int
    role: MessageRole
    content: str
    provider_id: str | None = None
    model: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""

    def to_provider_message(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass(frozen=True)
class ChatSession:
    id: str
    title: str
    created_at: str
    updated_at: str
    summary: str | None = None
    message_count: int = 0


@dataclass(frozen=True)
class ContextBuildResult:
    session_id: str
    messages: list[dict[str, str]]
    total_messages: int
    included_messages: int
    truncated: bool
