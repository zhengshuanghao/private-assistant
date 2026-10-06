from __future__ import annotations

import click
import uvicorn

from .config.settings import get_settings


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
def cli() -> None:
    """Private Assistent command line."""


@cli.command("serve")
@click.option("--host", default=None, help="Bind host.")
@click.option("--port", default=None, type=int, help="Bind port.")
@click.option("--reload", is_flag=True, help="Enable development reload.")
def serve(host: str | None, port: int | None, reload: bool) -> None:
    """Run the local API service."""
    settings = get_settings()
    uvicorn.run(
        "private_assistent.api.app:app",
        host=host or settings.host,
        port=port or settings.port,
        reload=reload,
    )


@cli.command("chat")
@click.argument("message", nargs=-1, required=True)
def chat(message: tuple[str, ...]) -> None:
    """Send one local assistant request through the minimal runtime."""
    from .runtime.session import run_once

    response = run_once(" ".join(message))
    click.echo(response)
