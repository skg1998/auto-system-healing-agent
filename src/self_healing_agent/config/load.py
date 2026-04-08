from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from self_healing_agent.config.models import AppConfig


def load_config(path: Path | str) -> AppConfig:
    """Load and validate YAML config from disk."""
    p = Path(path)
    raw = p.read_text(encoding="utf-8")
    data: Any = yaml.safe_load(raw)
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ValueError("Config root must be a mapping")
    return AppConfig.model_validate(data)


def default_config() -> AppConfig:
    """In-memory defaults (no file)."""
    return AppConfig()
