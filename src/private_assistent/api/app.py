from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from private_assistent import __version__
from private_assistent.config import get_settings
from private_assistent.context import ContextManager
from private_assistent.providers import (
    ModelSlot,
    ProviderConfigError,
    load_model_registry,
    save_default_model,
)
from private_assistent.runtime.session import run_turn

WEB_DIR = Path(__file__).resolve().parents[1] / "web"

app = FastAPI(title="Private Assistent", version=__version__)
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    session_id: str = "default"


class ChatResponse(BaseModel):
    reply: str
    session_id: str = "default"
    context_messages: int = 0
    context_truncated: bool = False


class SessionResponse(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    summary: str | None = None
    message_count: int = 0


class MessageResponse(BaseModel):
    id: str
    session_id: str
    seq: int
    role: str
    content: str
    provider_id: str | None = None
    model: str | None = None
    metadata: dict[str, Any] = {}
    created_at: str


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/api/health")
def health() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "ok",
        "version": __version__,
        "working_dir": str(settings.working_dir),
        "config_path": str(settings.config_path),
    }


@app.get("/api/providers")
def list_providers() -> dict:
    try:
        registry = load_model_registry()
    except ProviderConfigError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return registry.model_dump()


@app.get("/api/models/default", response_model=ModelSlot)
def get_default_model() -> ModelSlot:
    try:
        return load_model_registry().default_model
    except ProviderConfigError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.put("/api/models/default", response_model=ModelSlot)
def put_default_model(slot: ModelSlot) -> ModelSlot:
    try:
        return save_default_model(slot).default_model
    except ProviderConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/sessions", response_model=list[SessionResponse])
def list_sessions() -> list[SessionResponse]:
    context = ContextManager()
    return [SessionResponse(**session.__dict__) for session in context.list_sessions()]


@app.get("/api/sessions/{session_id}/messages", response_model=list[MessageResponse])
def list_session_messages(session_id: str) -> list[MessageResponse]:
    context = ContextManager()
    return [MessageResponse(**message.__dict__) for message in context.list_messages(session_id)]


@app.delete("/api/sessions/{session_id}/messages")
def clear_session_messages(session_id: str) -> dict[str, str]:
    context = ContextManager()
    context.clear_session(session_id)
    return {"status": "cleared", "session_id": session_id}


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    result = run_turn(request.message, session_id=request.session_id)
    return ChatResponse(
        reply=result.reply,
        session_id=result.session_id,
        context_messages=result.context_messages,
        context_truncated=result.context_truncated,
    )

