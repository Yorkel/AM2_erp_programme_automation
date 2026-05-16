"""
config.py
Loads sources.yml into typed source descriptors used by run.py and try_source.py.

A source descriptor looks like:
    {
        "name": "wonkhe_newsletter",
        "type": "newsletter",
        "ingestion": "disk",          # 'disk' | 'gmail' | None for web/rss
        "scraper": None,              # web sources may name a module here
        "params": { ... }             # passed through to the scraper as kwargs
    }
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

DEFAULT_SOURCES_YML = Path(__file__).resolve().parent / "sources.yml"

VALID_TYPES = {"web", "newsletter", "rss", "google_alert"}


def load_sources(path: Path | None = None) -> list[dict[str, Any]]:
    p = Path(path) if path else DEFAULT_SOURCES_YML
    if not p.exists():
        return []
    data = yaml.safe_load(p.read_text()) or {}
    sources = data.get("sources", []) or []
    out = []
    for s in sources:
        if "name" not in s or "type" not in s:
            raise ValueError(f"source entry missing required field name/type: {s}")
        if s["type"] not in VALID_TYPES:
            raise ValueError(f"source {s['name']}: unknown type '{s['type']}' (allowed: {VALID_TYPES})")
        if s.get("disabled"):
            continue
        out.append(s)
    return out


def get_source(name: str, path: Path | None = None) -> dict[str, Any] | None:
    for s in load_sources(path):
        if s["name"] == name:
            return s
    return None
