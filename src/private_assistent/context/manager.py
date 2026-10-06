from __future__ import annotations

from pathlib import Path

from private_assistent.config import get_settings
from private_assistent.context.models import ContextBuildResult, ContextConfig, StoredMessage
from private_assistent.context.store import SQLiteContextStore


def default_context_db_path() -> Path:
    settings = get_settings()
    return settings.working_dir / "data" / "sessions" / "context.db"


class ContextManager:
    """Small Scroll-style context manager for durable live chat history."""

    def __init__(
        self,
        store: SQLiteContextStore | None = None,
        *,
        config: ContextConfig | None = None,
    ) -> None:
        self.store = store or SQLiteContextStore(default_context_db_path())
        self.config = config or ContextConfig()

    def append_user_message(self, session_id: str, content: str) -> StoredMessage:
        return self.store.append_message(session_id, "user", content)

    def append_assistant_message(
        self,
        session_id: str,
        content: str,
        *,
        provider_id: str | None = None,
        model: str | None = None,
    ) -> StoredMessage:
        return self.store.append_message(
            session_id,
            "assistant",
            content,
            provider_id=provider_id,
            model=model,
        )

    def build_context(self, session_id: str) -> ContextBuildResult:
        messages = self.store.list_messages(session_id)
        selected = messages[-self.config.max_messages :]
        selected = self._trim_to_char_budget(selected)
        return ContextBuildResult(
            session_id=session_id.strip() or "default",
            messages=[message.to_provider_message() for message in selected],
            total_messages=len(messages),
            included_messages=len(selected),
            truncated=len(selected) < len(messages),
        )

    def list_sessions(self, *, limit: int = 50):
        return self.store.list_sessions(limit=limit)

    def list_messages(self, session_id: str):
        return self.store.list_messages(session_id)

    def clear_session(self, session_id: str) -> None:
        self.store.ensure_session(session_id)
        self.store.clear_session(session_id)

    def _trim_to_char_budget(self, messages: list[StoredMessage]) -> list[StoredMessage]:
        budget = max(1, int(self.config.max_chars))
        kept: list[StoredMessage] = []
        total = 0
        for message in reversed(messages):
            size = len(message.content)
            if kept and total + size > budget:
                break
            kept.append(message)
            total += size
            if total >= budget:
                break
        return list(reversed(kept))

