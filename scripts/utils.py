"""Shared utilities for the video generation pipeline."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "templates"
SCHEMA_PATH = TEMPLATES / "shot-list.schema.json"


def load_env() -> None:
    load_dotenv(ROOT / ".env")


def project_dir(slug: str) -> Path:
    return ROOT / "projects" / slug


def ensure_project_dirs(slug: str) -> Path:
    base = project_dir(slug)
    for sub in (
        "research/transcripts",
        "plan",
        "assets/images",
        "assets/stock",
        "assets/vo",
        "assets/clips",
        "renders/frames",
        "publish",
    ):
        (base / sub).mkdir(parents=True, exist_ok=True)
    return base


def load_shot_list(slug: str) -> dict:
    path = project_dir(slug) / "plan" / "shot-list.json"
    if not path.exists():
        raise FileNotFoundError(f"Shot list not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")[:64]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def extract_youtube_id(url: str) -> str | None:
    patterns = [
        r"(?:v=|/v/|youtu\.be/|/embed/)([a-zA-Z0-9_-]{11})",
        r"^([a-zA-Z0-9_-]{11})$",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def load_production_config(slug: str) -> dict:
    """Load project production.json; default mode is free."""
    path = project_dir(slug) / "production.json"
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
    else:
        data = {"mode": "free"}
    load_env()
    env_mode = os.environ.get("PRODUCTION_MODE", "").lower()
    if env_mode in ("free", "paid"):
        data["mode"] = env_mode
    return data


def is_paid_mode(slug: str) -> bool:
    return load_production_config(slug).get("mode", "free") == "paid"
