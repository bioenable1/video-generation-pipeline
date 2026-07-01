#!/usr/bin/env python3
"""Generate content-plan.html from shot-list.json using Jinja2 template."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from utils import ROOT, TEMPLATES, load_shot_list, project_dir, utc_now_iso


def build_chapters(scenes: list[dict]) -> list[dict]:
    if not scenes:
        return [{"title": "Introduction", "summary": "TBD", "duration_sec": 0}]
    chapters = []
    chunk_size = max(2, len(scenes) // 3)
    for i in range(0, len(scenes), chunk_size):
        chunk = scenes[i : i + chunk_size]
        duration = sum(s.get("duration_sec", 0) for s in chunk)
        first = chunk[0].get("id", f"part-{i}")
        chapters.append(
            {
                "title": f"Section {len(chapters) + 1} ({first})",
                "summary": chunk[0].get("narration", "")[:120] + "...",
                "duration_sec": int(duration),
            }
        )
    return chapters


def default_hooks(scenes: list[dict], product: str) -> list[str]:
    if scenes:
        return [
            scenes[0].get("narration", "")[:200],
            f"What if {product} could solve your biggest security challenge?",
            f"Discover how {product} transforms enterprise biometric access.",
        ]
    return [
        f"Introducing {product}",
        f"Meet {product} — built for enterprise teams.",
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate content-plan.html")
    parser.add_argument("--project", required=True)
    parser.add_argument(
        "--executive-summary",
        help="Override executive summary text",
    )
    args = parser.parse_args()

    shot_list_path = project_dir(args.project) / "plan" / "shot-list.json"
    if not shot_list_path.exists():
        print(f"ERROR: {shot_list_path} not found", file=sys.stderr)
        sys.exit(1)

    data = load_shot_list(args.project)
    scenes = data.get("scenes", [])
    product = data.get("product", args.project)

    context = {
        "title": data.get("title", f"{product} Video"),
        "product": product,
        "duration_target_sec": data.get("duration_target_sec", 90),
        "aspect_ratio": data.get("aspect_ratio", "16:9"),
        "tone": data.get("tone", "professional B2B"),
        "generated_at": utc_now_iso(),
        "executive_summary": args.executive_summary
        or f"A {data.get('duration_target_sec', 90)}-second product marketing video for {product}, "
        f"structured across {len(scenes)} scenes with clear benefits and a strong CTA.",
        "hook_options": default_hooks(scenes, product),
        "chapters": build_chapters(scenes),
        "scenes": scenes,
        "cta": data.get("metadata", {}).get("youtube_description", "")[:200]
        or "Visit bioenable.com to learn more and request a demo.",
        "metadata": data.get(
            "metadata",
            {
                "youtube_title": f"{product} — Product Overview",
                "youtube_description": "",
                "tags": [product.lower(), "biometrics", "enterprise"],
            },
        ),
        "acceptance_criteria": data.get("acceptance_criteria", []),
    }

    env = Environment(
        loader=FileSystemLoader(TEMPLATES),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("content-plan.html.j2")
    html = template.render(**context)

    out_path = project_dir(args.project) / "plan" / "content-plan.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"Wrote {out_path}")
    print("Review in browser. Set approved: true in shot-list.json to continue.")


if __name__ == "__main__":
    main()
