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
VIDEO_TYPES_DIR = TEMPLATES / "video-types"
STOCK_CATALOG_PATH = TEMPLATES / "stock_catalog.json"
BRAND_DEFAULT_PATH = TEMPLATES / "brand.default.json"

ASPECT_DIMENSIONS = {
    "16:9": (1920, 1080),
    "9:16": (1080, 1920),
    "1:1": (1080, 1080),
    "4:5": (1080, 1350),
}

VIDEO_TYPE_IDS = ("product", "explainer", "social", "tutorial")


def load_env() -> None:
    load_dotenv(ROOT / ".env")


def project_dir(slug: str) -> Path:
    return ROOT / "projects" / slug


def ensure_project_dirs(slug: str) -> Path:
    base = project_dir(slug)
    for sub in (
        "research/transcripts",
        "plan",
        "assets/brand",
        "assets/images",
        "assets/stock",
        "assets/vo",
        "assets/clips",
        "assets/music",
        "assets/source",
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


def load_json_file(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_stock_catalog() -> dict:
    if STOCK_CATALOG_PATH.exists():
        return load_json_file(STOCK_CATALOG_PATH)
    return {"videos": {}, "music": {}, "query_fallback": "technology_data"}


def load_brand(slug: str) -> dict:
    path = project_dir(slug) / "brand.json"
    if path.exists():
        brand = load_json_file(path)
    else:
        brand = load_json_file(BRAND_DEFAULT_PATH) if BRAND_DEFAULT_PATH.exists() else {}
    colors = brand.setdefault("colors", {})
    for key, val in {
        "primary": "0x3b82f6",
        "accent": "0x93c5fd",
        "text_muted": "0x8b9cb3",
        "background": "0x0f1a2e",
        "overlay": "black@0.35",
    }.items():
        colors.setdefault(key, val)
    brand.setdefault("font", {})
    brand["font"].setdefault("heading", "C:/Windows/Fonts/arialbd.ttf")
    brand["font"].setdefault("body", "C:/Windows/Fonts/arial.ttf")
    brand.setdefault("tagline", "")
    brand.setdefault("name", slug)
    return brand


def aspect_dimensions(aspect_ratio: str) -> tuple[int, int]:
    return ASPECT_DIMENSIONS.get(aspect_ratio, ASPECT_DIMENSIONS["16:9"])


def load_video_type_preset(video_type: str) -> dict:
    path = VIDEO_TYPES_DIR / f"{video_type}.json"
    if not path.exists():
        raise FileNotFoundError(
            f"Unknown video type '{video_type}'. Choose: {', '.join(VIDEO_TYPE_IDS)}"
        )
    return load_json_file(path)


def substitute_placeholders(obj: dict | list | str, variables: dict[str, str]) -> dict | list | str:
    """Recursively replace {key} placeholders in strings."""
    if isinstance(obj, str):
        out = obj
        for key, val in variables.items():
            out = out.replace("{" + key + "}", val)
        return out
    if isinstance(obj, list):
        return [substitute_placeholders(item, variables) for item in obj]
    if isinstance(obj, dict):
        return {k: substitute_placeholders(v, variables) for k, v in obj.items()}
    return obj


def resolve_logo_path(slug: str, brand: dict | None = None) -> Path:
    brand = brand or load_brand(slug)
    base = project_dir(slug)
    logo_cfg = brand.get("logo", {})
    for key in ("dark", "light"):
        rel = logo_cfg.get(key, "")
        if rel:
            p = base / rel
            if p.exists():
                return p
    for name in ("logo-dark-bg.png", "logo-transparent.png", "logo.png"):
        p = base / "assets" / "brand" / name
        if p.exists():
            return p
    return base / "assets" / "brand" / "logo-transparent.png"


def parse_brief_urls(brief_path: Path) -> list[str]:
    """Extract HTTP(S) URLs from brief.md Reference / Source sections."""
    if not brief_path.exists():
        return []
    text = brief_path.read_text(encoding="utf-8")
    urls: list[str] = []
    in_section = False
    for line in text.splitlines():
        stripped = line.strip()
        lower = stripped.lower()
        if lower.startswith("## ") and any(
            kw in lower for kw in ("reference", "source", "url")
        ):
            in_section = True
            continue
        if in_section and lower.startswith("## "):
            in_section = False
        if in_section and stripped.startswith("- ") and "http" in stripped:
            part = stripped[2:].split(":", 1)[-1].strip() if "http" in stripped[2:] else stripped[2:]
            for token in part.split():
                if token.startswith("http"):
                    urls.append(token.rstrip(")").rstrip("]"))
    if not urls:
        urls = re.findall(r"https?://[^\s\)\]>]+", text)
    return list(dict.fromkeys(urls))
