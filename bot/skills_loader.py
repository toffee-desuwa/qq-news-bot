"""Thin loader for persona skill packs (JSON template files).

Persona affects wording only. Core logic (polling, dedupe, rate limiting,
storage schema) is never modified by persona selection.
"""

import json
import os
from pathlib import Path
from typing import Dict

_texts: Dict[str, str] = {}
_loaded = False


def _skills_dir() -> Path:
    """Return the skills/ directory at repo root."""
    return Path(__file__).resolve().parent.parent / "skills"


def _load() -> None:
    global _texts, _loaded
    persona = os.environ.get("PERSONA", "neutral").strip().lower()
    path = _skills_dir() / f"persona_{persona}.json"
    if not path.exists():
        # Fall back to neutral if the requested persona file is missing
        path = _skills_dir() / "persona_neutral.json"
    with open(path, encoding="utf-8") as f:
        _texts = json.load(f)
    _loaded = True


def get_text(key: str, **kwargs: object) -> str:
    """Look up a text key from the active persona and format with kwargs.

    Falls back to the key itself if not found (avoids hard crash).
    """
    if not _loaded:
        _load()
    template = _texts.get(key, key)
    if kwargs:
        return template.format(**kwargs)
    return template


def reload() -> None:
    """Force reload (useful for testing)."""
    global _loaded
    _loaded = False
