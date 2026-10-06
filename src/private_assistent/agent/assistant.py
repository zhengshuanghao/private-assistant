from __future__ import annotations

from dataclasses import dataclass

from private_assistent.context import ContextManager
from private_assistent.providers import ProviderManager
from private_assistent.providers.models import ProviderRuntimeError


@dataclass(frozen=True)
class AssistantTurnResult:
    session_id: str
    reply: str
    context_messages: int
    context_truncated: bool


@dataclass
class LocalAssistant:
    """Minimal assistant facade backed by context and provider managers."""

    name: str = "private-assistent"

    def reply(self, message: str) -> str:
        return self.reply_in_session("default", message).reply

    def reply_in_session(self, session_id: str, message: str) -> AssistantTurnResult:
        manager = ProviderManager()
        context = ContextManager()
        clean_session_id = session_id.strip() or "default"
        context.append_user_message(clean_session_id, message)
        built = context.build_context(clean_session_id)
        active = manager.get_active_model()
        provider = manager.get_active_provider()
        try:
            reply = manager.generate_messages_sync(built.messages)
        except ProviderRuntimeError as exc:
            reply = (
                f"[{self.name}] provider call failed: {exc}\n"
                f"model={provider.id}/{active.model}\n"
                f"provider_type={provider.type}\n"
                f"provider_protocol={provider.protocol}"
            )
        context.append_assistant_message(
            clean_session_id,
            reply,
            provider_id=provider.id,
            model=active.model,
        )
        return AssistantTurnResult(
            session_id=clean_session_id,
            reply=reply,
            context_messages=built.included_messages,
            context_truncated=built.truncated,
        )
