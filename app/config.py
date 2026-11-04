"""Reads settings from environment variables, loading a local .env file if present."""

import os
from dataclasses import dataclass
from pathlib import Path

from app.errors import ConfigError

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
REQUIRED = ("OPENROUTER_API_KEY", "OPENROUTER_MODEL")


@dataclass(frozen=True)
class Settings:
    api_key: str
    model: str


def _load_env_file(path: Path = ENV_FILE) -> None:
    """Set variables from .env without overriding ones already in the environment."""
    if not path.exists():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def missing_settings() -> list[str]:
    _load_env_file()
    return [name for name in REQUIRED if not os.environ.get(name)]


def get_settings() -> Settings:
    missing = missing_settings()
    if missing:
        # Name the variable, never print a value.
        raise ConfigError(f"Missing environment variable(s): {', '.join(missing)}. See .env.example.")
    return Settings(api_key=os.environ["OPENROUTER_API_KEY"], model=os.environ["OPENROUTER_MODEL"])
