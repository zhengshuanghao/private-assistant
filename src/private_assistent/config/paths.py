from __future__ import annotations

import os
from pathlib import Path

import yaml

DEFAULT_WORKING_DIR = Path.home() / ".private-assistent"
RUNTIME_DIRS = (
    "providers",
    "data/workspace",
    "data/memory",
    "data/sessions",
    "logs",
)


def get_working_dir() -> Path:
    raw_working_dir = os.environ.get("PRIVATE_ASSISTENT_WORKING_DIR")
    if raw_working_dir:
        return Path(raw_working_dir).expanduser()
    return DEFAULT_WORKING_DIR


def get_config_path() -> Path:
    raw_config = os.environ.get("PRIVATE_ASSISTENT_CONFIG_PATH")
    if raw_config:
        return Path(raw_config).expanduser()
    return get_working_dir() / "config.yaml"


def bootstrap_runtime_home(
    working_dir: Path | str | None = None,
    config_path: Path | str | None = None,
) -> Path:
    resolved_config_path = Path(config_path).expanduser() if config_path else get_config_path()
    resolved_working_dir = (
        Path(working_dir).expanduser() if working_dir else get_working_dir()
    )

    target_root = resolved_working_dir
    if config_path is not None and working_dir is None:
        target_root = resolved_config_path.parent

    target_root.mkdir(parents=True, exist_ok=True)
    for relative_dir in RUNTIME_DIRS:
        (target_root / relative_dir).mkdir(parents=True, exist_ok=True)

    resolved_config_path.parent.mkdir(parents=True, exist_ok=True)
    if not resolved_config_path.exists():
        from private_assistent.providers.catalog import build_default_config

        resolved_config_path.write_text(
            yaml.safe_dump(
                build_default_config(),
                allow_unicode=True,
                sort_keys=False,
            ),
            encoding="utf-8",
        )
    return resolved_config_path
