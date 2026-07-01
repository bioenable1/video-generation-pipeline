#!/usr/bin/env python3
"""Generate YouTube thumbnail using brand logo on dark background."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils import load_shot_list, project_dir


def generate_thumbnail_png(out: Path, title: str, product: str, logo: Path) -> None:
    run_ffmpeg = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=c=0x0f1a2e:s=1280x720:d=1",
    ]
    if logo.exists():
        title_e = title.replace(":", "\\:").replace("'", "\\'")[:70]
        run_ffmpeg.extend([
            "-i", str(logo),
            "-filter_complex",
            (
                "[1]format=rgba,scale=400:-1[lg];"
                "[0][lg]overlay=(main_w-overlay_w)/2:120[v];"
                f"[v]drawtext=fontfile=C\\\\:/Windows/Fonts/arialbd.ttf:text='{title_e}':"
                f"fontsize=36:fontcolor=white:x=(w-text_w)/2:y=520[out]"
            ),
            "-map", "[out]", "-frames:v", "1",
        ])
    else:
        run_ffmpeg.extend(["-frames:v", "1"])
    run_ffmpeg.append(str(out))

    import subprocess
    subprocess.run(run_ffmpeg, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate YouTube thumbnail")
    parser.add_argument("--project", required=True)
    parser.add_argument("--format", choices=["svg", "json", "png"], default="png")
    args = parser.parse_args()

    shot_list = load_shot_list(args.project)
    meta = shot_list.get("metadata", {})
    title = meta.get("youtube_title") or shot_list.get("title", args.project)
    product = shot_list.get("product", args.project)
    base = project_dir(args.project)
    publish_dir = base / "publish"
    publish_dir.mkdir(parents=True, exist_ok=True)
    logo = base / "assets" / "brand" / "logo-dark-bg.png"
    if not logo.exists():
        logo = base / "assets" / "brand" / "logo-transparent.png"

    if args.format == "png":
        out = publish_dir / "thumbnail.png"
        generate_thumbnail_png(out, title, product, logo)
        print(f"Wrote {out}")
    elif args.format == "json":
        import json
        spec = {
            "title": title,
            "product": product,
            "dimensions": "1280x720",
            "prompt": f"Professional YouTube thumbnail for {product}, STQC certified dual iris scanner, BioEnable branding",
        }
        spec_path = publish_dir / "thumbnail-spec.json"
        spec_path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {spec_path}")
    else:
        # legacy svg
        from generate_thumbnail import generate_placeholder_thumbnail  # noqa: F401
        out = publish_dir / "thumbnail.svg"
        svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720">
  <rect width="1280" height="720" fill="#0f1a2e"/>
  <text x="640" y="360" font-family="sans-serif" font-size="36" fill="white" text-anchor="middle">{title[:60]}</text>
</svg>"""
        out.write_text(svg, encoding="utf-8")
        print(f"Wrote {out}")


if __name__ == "__main__":
    main()
