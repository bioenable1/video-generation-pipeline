#!/usr/bin/env python3
"""Bootstrap a new video project for any subject, concept, or product."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

from utils import (
    BRAND_DEFAULT_PATH,
    VIDEO_TYPE_IDS,
    ensure_project_dirs,
    load_json_file,
    load_video_type_preset,
    slugify,
    substitute_placeholders,
    utc_now_iso,
)

BRIEF_TEMPLATE = """# {title} — Video Brief

## Subject
{subject}

## Video type
{type_label} (`{video_type}`)

## Audience
{audience}

## Key messages
- 
- 
- 

## Tone
{tone}

## Duration target
{duration} seconds

## Aspect ratio
{aspect_ratio}

## Reference URLs
- 

## Source materials
Drop files into `assets/source/` (PDF brochure, images, screen recordings).
Add product site URLs above for automatic image extraction.

## Brand
Edit `brand.json` for colors, logo paths, tagline, and contact.

## CTA
{cta}

---
Created: {created_at}
"""


def build_shot_list(
    slug: str,
    subject: str,
    video_type: str,
    title: str,
    tone: str,
    duration: int,
    aspect_ratio: str,
    cta: str,
    website: str,
    contact: str,
) -> dict:
    preset = load_video_type_preset(video_type)
    variables = {
        "subject": subject,
        "title": title,
        "cta": cta,
        "website": website or "your-site.com",
        "contact": contact or "",
        "tone": tone,
    }
    scenes = substitute_placeholders(copy.deepcopy(preset["scenes"]), variables)
    defaults = preset.get("defaults", {})
    return {
        "id": slug,
        "title": title,
        "subject": subject,
        "product": subject,
        "video_type": video_type,
        "duration_target_sec": duration or defaults.get("duration_target_sec", 90),
        "aspect_ratio": aspect_ratio or defaults.get("aspect_ratio", "16:9"),
        "tone": tone or defaults.get("tone", "Professional, clear"),
        "approved": False,
        "scenes": scenes,
        "acceptance_criteria": preset.get("acceptance_criteria", []),
        "metadata": {
            "youtube_title": title[:100],
            "youtube_description": "",
            "tags": [],
        },
    }


def build_brand(subject: str, website: str, contact: str, tagline: str) -> dict:
    brand = load_json_file(BRAND_DEFAULT_PATH)
    brand["name"] = subject
    brand["tagline"] = tagline
    brand["website"] = website
    brand["contact"] = contact
    return brand


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a new universal video project")
    parser.add_argument("--slug", help="Project slug (auto-generated from subject if omitted)")
    parser.add_argument("--subject", "--product", dest="subject", required=True,
                        help="Topic, product, or concept name")
    parser.add_argument("--type", choices=list(VIDEO_TYPE_IDS), default="product",
                        help="Video format preset (default: product)")
    parser.add_argument("--title", help="Video title (default: '<subject> Video')")
    parser.add_argument("--audience", default="General audience interested in this topic.")
    parser.add_argument("--tone", help="Narration tone (uses preset default if omitted)")
    parser.add_argument("--duration", type=int, help="Target duration in seconds")
    parser.add_argument("--aspect-ratio", choices=["16:9", "9:16", "1:1", "4:5"],
                        help="Override preset aspect ratio")
    parser.add_argument("--cta", default="Learn more at our website.")
    parser.add_argument("--website", default="", help="URL for CTA and brand.json")
    parser.add_argument("--contact", default="", help="Email or phone for outro")
    parser.add_argument("--tagline", default="", help="Brand tagline for logo slate")
    args = parser.parse_args()

    slug = args.slug or slugify(args.subject)
    preset = load_video_type_preset(args.type)
    title = args.title or f"{args.subject} — {preset['label']}"
    tone = args.tone or preset.get("defaults", {}).get("tone", "Professional, clear")
    duration = args.duration or preset.get("defaults", {}).get("duration_target_sec", 90)
    aspect = args.aspect_ratio or preset.get("defaults", {}).get("aspect_ratio", "16:9")

    base = ensure_project_dirs(slug)

    brief_path = base / "brief.md"
    if not brief_path.exists():
        brief_path.write_text(
            BRIEF_TEMPLATE.format(
                title=title,
                subject=args.subject,
                type_label=preset["label"],
                video_type=args.type,
                audience=args.audience,
                tone=tone,
                duration=duration,
                aspect_ratio=aspect,
                cta=args.cta,
                created_at=utc_now_iso(),
            ),
            encoding="utf-8",
        )
        print(f"Created {brief_path}")

    brand_path = base / "brand.json"
    if not brand_path.exists():
        brand_path.write_text(
            json.dumps(
                build_brand(args.subject, args.website, args.contact, args.tagline),
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"Created {brand_path}")

    shot_list_path = base / "plan" / "shot-list.json"
    if not shot_list_path.exists():
        shot_list = build_shot_list(
            slug, args.subject, args.type, title, tone, duration, aspect,
            args.cta, args.website, args.contact,
        )
        shot_list_path.write_text(json.dumps(shot_list, indent=2) + "\n", encoding="utf-8")
        print(f"Created {shot_list_path} ({len(shot_list['scenes'])} scenes, type={args.type})")

    prod_path = base / "production.json"
    if not prod_path.exists():
        prod_path.write_text(
            json.dumps(
                {
                    "mode": "free",
                    "video_type": args.type,
                    "description": "Set mode to 'paid' for ElevenLabs, VEED, fal.ai",
                    "free": {"tts": "edge-tts", "voice": "en-US-ChristopherNeural", "editor": "ffmpeg"},
                    "paid": {"tts": "elevenlabs", "editor": "veed", "ai_video": "fal.fabric"},
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"Created {prod_path}")

    print(f"\nProject ready: projects/{slug}/")
    desc = preset["description"].encode("ascii", "replace").decode("ascii")
    print(f"  Type: {args.type} - {desc}")
    print("Next:")
    print(f"  1. Edit brief.md and brand.json")
    print(f"  2. Customize plan/shot-list.json (or ask the agent)")
    print(f"  3. python run.py approve --project {slug}")
    print(f"  4. python run.py generate-assets --project {slug}")
    print(f"  5. python run.py render --project {slug} --force")


if __name__ == "__main__":
    main()
