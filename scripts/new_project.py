#!/usr/bin/env python3
"""Bootstrap a new video project."""

from __future__ import annotations

import argparse
from pathlib import Path

from utils import ensure_project_dirs, slugify, utc_now_iso

BRIEF_TEMPLATE = """# {product} — Video Brief

## Product
{product}

## Audience
B2B decision-makers, IT/security teams evaluating biometric solutions.

## Key messages
- 
- 
- 

## Tone
Professional, confident, clear. Avoid hype.

## Duration target
90 seconds

## Aspect ratio
16:9

## Reference URLs
- 

## Existing copy / talking points
(Paste product page copy, datasheet bullets, etc.)

## CTA
Visit bioenable.com or contact sales.

---
Created: {created_at}
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a new video project")
    parser.add_argument("--slug", help="Project slug (auto-generated from product if omitted)")
    parser.add_argument("--product", required=True, help="Product name")
    args = parser.parse_args()

    slug = args.slug or slugify(args.product)
    base = ensure_project_dirs(slug)

    brief_path = base / "brief.md"
    if brief_path.exists():
        print(f"Project already exists: {base}")
    else:
        brief_path.write_text(
            BRIEF_TEMPLATE.format(
                product=args.product,
                created_at=utc_now_iso(),
            ),
            encoding="utf-8",
        )
        print(f"Created {brief_path}")

    shot_list_path = base / "plan" / "shot-list.json"
    if not shot_list_path.exists():
        shot_list_path.write_text(
            """{
  "id": "%s",
  "title": "%s Product Video",
  "product": "%s",
  "duration_target_sec": 90,
  "aspect_ratio": "16:9",
  "tone": "professional B2B",
  "approved": false,
  "scenes": [],
  "acceptance_criteria": [
    "Product name appears in first 5 seconds",
    "Key benefits clearly communicated",
    "Professional visual quality throughout",
    "Clear CTA in final 10 seconds"
  ],
  "metadata": {
    "youtube_title": "",
    "youtube_description": "",
    "tags": []
  }
}
"""
            % (slug, args.product, args.product),
            encoding="utf-8",
        )
        print(f"Created {shot_list_path}")

    print(f"\nProject ready: projects/{slug}/")
    print("Next: edit brief.md, then run research.py")


if __name__ == "__main__":
    main()
