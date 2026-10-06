from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from private_assistent.context.models import ChatSession, MessageRole, StoredMessage

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    summary TEXT
);
CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    seq INTEGER NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    provider_id TEXT,
    model TEXT,
    metadata TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    UNIQUE(session_id, seq)
);
CREATE INDEX IF NOT EXISTS idx_messages_session_seq ON messages(session_id, seq);
CREATE INDEX IF NOT EXISTS idx_sessions_updated_at ON sessions(updated_at);
"""


class SQLiteContextStore:
    """Durable session/message store for lightweight Scroll-style context."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def _init_schema(self) -> None:
        with self._lock, self._connect() as conn:
            conn.executescript(_SCHEMA)

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _title_from_content(content: str) -> str:
        title = " ".join(content.split())[:60]
        return title or "新的对话"

    @staticmethod
    def _message_from_row(row: sqlite3.Row) -> StoredMessage:
        raw_metadata = row["metadata"]
        metadata: dict[str, Any] = {}
        if raw_metadata:
            try:
                parsed = json.loads(raw_metadata)
                if isinstance(parsed, dict):
                    metadata = parsed
            except json.JSONDecodeError:
                metadata = {}
        return StoredMessage(
            id=row["id"],
            session_id=row["session_id"],
            seq=int(row["seq"]),
            role=row["role"],
            content=row["content"],
            provider_id=row["provider_id"],
            model=row["model"],
            metadata=metadata,
            created_at=row["created_at"],
        )

    @staticmethod
    def _session_from_row(row: sqlite3.Row) -> ChatSession:
        return ChatSession(
            id=row["id"],
            title=row["title"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            summary=row["summary"],
            message_count=int(row["message_count"] or 0),
        )

    def ensure_session(self, session_id: str, *, title: str | None = None) -> ChatSession:
        now = self._now()
        clean_id = session_id.strip() or "default"
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT s.*, COUNT(m.id) AS message_count "
                "FROM sessions s LEFT JOIN messages m ON m.session_id = s.id "
                "WHERE s.id = ? GROUP BY s.id",
                (clean_id,),
            ).fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO sessions(id, title, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?)",
                    (clean_id, title or "新的对话", now, now),
                )
                row = conn.execute(
                    "SELECT s.*, 0 AS message_count FROM sessions s WHERE s.id = ?",
                    (clean_id,),
                ).fetchone()
            return self._session_from_row(row)

    def list_sessions(self, *, limit: int = 50) -> list[ChatSession]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT s.*, COUNT(m.id) AS message_count "
                "FROM sessions s LEFT JOIN messages m ON m.session_id = s.id "
                "GROUP BY s.id ORDER BY s.updated_at DESC LIMIT ?",
                (max(1, int(limit)),),
            ).fetchall()
            return [self._session_from_row(row) for row in rows]

    def append_message(
        self,
        session_id: str,
        role: MessageRole,
        content: str,
        *,
        provider_id: str | None = None,
        model: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> StoredMessage:
        clean_content = content.strip()
        if not clean_content:
            raise ValueError("message content must not be empty")
        if role not in ("system", "user", "assistant"):
            raise ValueError(f"unsupported message role: {role}")

        now = self._now()
        clean_id = session_id.strip() or "default"
        message_id = uuid.uuid4().hex
        encoded_metadata = json.dumps(metadata or {}, ensure_ascii=False, sort_keys=True)
        with self._lock, self._connect() as conn:
            session = conn.execute("SELECT id FROM sessions WHERE id = ?", (clean_id,)).fetchone()
            if session is None:
                conn.execute(
                    "INSERT INTO sessions(id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                    (clean_id, self._title_from_content(clean_content), now, now),
                )
            seq = int(
                conn.execute(
                    "SELECT COALESCE(MAX(seq), 0) + 1 AS next_seq FROM messages WHERE session_id = ?",
                    (clean_id,),
                ).fetchone()["next_seq"]
            )
            conn.execute(
                "INSERT INTO messages(id, session_id, seq, role, content, provider_id, model, metadata, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    message_id,
                    clean_id,
                    seq,
                    role,
                    clean_content,
                    provider_id,
                    model,
                    encoded_metadata,
                    now,
                ),
            )
            conn.execute(
                "UPDATE sessions SET updated_at = ? WHERE id = ?",
                (now, clean_id),
            )
            row = conn.execute("SELECT * FROM messages WHERE id = ?", (message_id,)).fetchone()
            return self._message_from_row(row)

    def list_messages(self, session_id: str, *, limit: int | None = None) -> list[StoredMessage]:
        clean_id = session_id.strip() or "default"
        sql = "SELECT * FROM messages WHERE session_id = ? ORDER BY seq ASC"
        params: tuple[Any, ...] = (clean_id,)
        if limit is not None:
            sql += " LIMIT ?"
            params = (clean_id, max(1, int(limit)))
        with self._lock, self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [self._message_from_row(row) for row in rows]

    def clear_session(self, session_id: str) -> None:
        clean_id = session_id.strip() or "default"
        now = self._now()
        with self._lock, self._connect() as conn:
            conn.execute("DELETE FROM messages WHERE session_id = ?", (clean_id,))
            conn.execute(
                "UPDATE sessions SET summary = NULL, updated_at = ? WHERE id = ?",
                (now, clean_id),
            )
