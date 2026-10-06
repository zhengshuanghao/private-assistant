from __future__ import annotations

from private_assistent.agent.assistant import AssistantTurnResult, LocalAssistant


def run_once(message: str) -> str:
    """Run a single assistant turn in the default session."""
    assistant = LocalAssistant()
    return assistant.reply(message)


def run_turn(message: str, *, session_id: str = "default") -> AssistantTurnResult:
    """Run one contextual assistant turn and persist it to the session."""
    assistant = LocalAssistant()
    return assistant.reply_in_session(session_id, message)
